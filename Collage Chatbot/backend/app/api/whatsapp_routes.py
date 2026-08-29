import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, Depends, Header, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.services.whatsapp.whatsapp_client import MetaWhatsAppClient
from ai.router.intent_router import AIRouter
from backend.app.models.entities import AuditLog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Bot Bridge"])
whatsapp_client = MetaWhatsAppClient()
ai_router = AIRouter()

@router.get("/webhook")
async def verify_whatsapp_webhook(
    request: Request,
    hub_mode: Optional[str] = None,
    hub_challenge: Optional[str] = None,
    hub_verify_token: Optional[str] = None
):
    """
    Meta WhatsApp Cloud API Webhook Verification Challenge Handshake.
    Supports both query parameter formats (hub.mode and hub_mode).
    """
    mode = request.query_params.get("hub.mode") or hub_mode
    token = request.query_params.get("hub.verify_token") or hub_verify_token
    challenge = request.query_params.get("hub.challenge") or hub_challenge

    verified_challenge = whatsapp_client.verify_webhook_token(mode, token, challenge)
    if verified_challenge:
        return PlainTextResponse(content=verified_challenge, status_code=200)

    logger.warning(f"[WhatsApp] Verification token mismatch. Received token: {token}")
    raise HTTPException(status_code=403, detail="Verification token mismatch")

@router.post("/webhook")
async def handle_whatsapp_inbound_message(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Inbound WhatsApp Message Webhook.
    Directly routes user messages through deterministic AIRouter without bypassing official hierarchy.
    """
    raw_body = await request.body()
    if not whatsapp_client.verify_signature(raw_body, x_hub_signature_256):
        logger.error("[WhatsApp] Invalid HMAC signature on inbound webhook")
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    logger.info(f"[WhatsApp] Inbound payload received: {payload}")

    # Parse Meta Cloud API structure
    entries = payload.get("entry", [])
    for entry in entries:
        changes = entry.get("changes", [])
        for change in changes:
            value = change.get("value", {})
            messages = value.get("messages", [])
            for msg in messages:
                msg_type = msg.get("type")
                from_number = msg.get("from")
                msg_id = msg.get("id")

                text_body = ""
                if msg_type == "text":
                    text_body = msg.get("text", {}).get("body", "")

                if text_body and from_number:
                    logger.info(f"[WhatsApp] Processing query from {from_number}: '{text_body}'")

                    # Route through deterministic AI router
                    ai_response = await ai_router.route_and_respond(
                        db=db,
                        query=text_body,
                        role="PUBLIC",
                        mode="TEXT"
                    )

                    reply_text = ai_response["answer"]
                    # If sources exist, append official citation
                    if ai_response.get("sources"):
                        src = ai_response["sources"][0]
                        if src.get("source_url"):
                            reply_text += f"\n\nSource: {src['source_url']}"

                    # Dispatch response via WhatsApp
                    await whatsapp_client.send_text_message(from_number, reply_text)

                    # Audit WhatsApp Interaction
                    audit = AuditLog(
                        actor_role="WHATSAPP_USER",
                        action="WHATSAPP_QUERY",
                        target_entity="AIRouter",
                        details={
                            "phone": from_number,
                            "query": text_body,
                            "intent": ai_response.get("intent"),
                            "selected_source": ai_response.get("selected_source")
                        }
                    )
                    db.add(audit)
                    db.commit()

    return {"status": "EVENT_RECEIVED"}
