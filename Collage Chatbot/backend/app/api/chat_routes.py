import os
import json
from datetime import datetime, UTC
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.entities import User, Conversation, Message, VoiceAsset
from backend.app.schemas.schemas import ChatRequest, ChatResponse, FeedbackRequest
from backend.app.security.auth import get_current_user
from backend.app.security.sanitizer import sanitize_user_input, check_prompt_injection
from ai.router.intent_router import AIRouter
from voice.stt.stt_engine import SpeechToTextEngine
from voice.tts.tts_engine import TextToSpeechEngine

router = APIRouter(prefix="/chat", tags=["Chat & Voice"])

ai_router = AIRouter()
stt_engine = SpeechToTextEngine()
tts_engine = TextToSpeechEngine()

@router.post("", response_model=ChatResponse)
@router.post("/", response_model=ChatResponse)
@router.post("/send", response_model=ChatResponse)
async def send_message(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    sanitized = sanitize_user_input(payload.message)
    if not sanitized:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    is_injection, note = check_prompt_injection(sanitized)
    if is_injection:
        return {
            "conversation_id": payload.conversation_id or "conv-default",
            "message_id": f"msg-{int(datetime.now(UTC).timestamp())}",
            "answer": "Your request contains safety policy violations and cannot be processed.",
            "intent": "POLICY_VIOLATION",
            "entities": {},
            "selected_source": "SAFETY_GUARD",
            "confidence": 1.0,
            "sources": [],
            "images": [],
            "suggested_followups": [],
            "voice_asset_id": None,
            "is_general_knowledge": False,
            "timestamp": datetime.now(UTC).isoformat()
        }

    # Find or create conversation
    conv = None
    if payload.conversation_id:
        conv = db.query(Conversation).filter(Conversation.id == payload.conversation_id).first()
    if not conv:
        conv = Conversation(
            user_id=current_user.id if current_user else None,
            title=sanitized[:40] + ("..." if len(sanitized) > 40 else ""),
            mode=payload.mode
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

    # Persist user message
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=sanitized,
        language=payload.language or "en"
    )
    db.add(user_msg)
    db.commit()

    # Route and respond via AI Router
    role = "STUDENT" if current_user else "PUBLIC"
    response_data = await ai_router.route_and_respond(
        db=db,
        query=sanitized,
        user_id=current_user.id if current_user else None,
        role=role,
        mode=payload.mode,
        conversation_id=conv.id
    )

    # Persist assistant message
    asst_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=response_data["answer"],
        language=payload.language or "en",
        intent=response_data["intent"],
        entities=response_data["entities"],
        selected_source=response_data["selected_source"],
        source_metadata={"sources": response_data["sources"]},
        images_json=response_data["images"],
        voice_asset_id=response_data["voice_asset_id"],
        confidence_score=response_data["confidence"]
    )
    db.add(asst_msg)
    db.commit()

    response_data["message_id"] = asst_msg.id
    return response_data

@router.post("/voice")
async def handle_voice_chat(
    file: Optional[UploadFile] = File(None),
    transcript: Optional[str] = Form(None),
    conversation_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    final_text = transcript or ""
    detected_lang = "en"
    if file:
        audio_bytes = await file.read()
        stt_result = stt_engine.transcribe_audio_bytes(audio_bytes)
        final_text = stt_result.get("transcript", "")
        detected_lang = stt_result.get("language", "en")

    if not final_text:
        raise HTTPException(status_code=400, detail="No speech or transcript detected")

    chat_payload = ChatRequest(
        conversation_id=conversation_id,
        message=final_text,
        language=detected_lang,
        mode="VOICE"
    )
    res = await send_message(chat_payload, db=db, current_user=current_user)
    return {
        "user_transcript": final_text,
        "language": detected_lang,
        "chat_response": res
    }

@router.get("/voice-asset/{asset_id}")
def get_voice_audio(asset_id: str, db: Session = Depends(get_db)):
    asset = db.query(VoiceAsset).filter(VoiceAsset.id == asset_id).first()
    if not asset or not os.path.exists(asset.file_path):
        raise HTTPException(status_code=404, detail="Voice audio asset not found")
    return FileResponse(asset.file_path, media_type="audio/wav")

@router.get("/conversations")
def list_conversations(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    if not current_user:
        return []
    convs = db.query(Conversation).filter(
        Conversation.user_id == current_user.id
    ).order_by(Conversation.updated_at.desc()).all()

    return [
        {
            "id": c.id,
            "title": c.title,
            "mode": c.mode,
            "is_pinned": c.is_pinned,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat()
        }
        for c in convs
    ]

@router.get("/conversations/{conv_id}")
def get_conversation_details(
    conv_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = []
    for m in conv.messages:
        messages.append({
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "language": m.language,
            "intent": m.intent,
            "selected_source": m.selected_source,
            "sources": m.source_metadata.get("sources", []) if m.source_metadata else [],
            "images": m.images_json or [],
            "voice_asset_id": m.voice_asset_id,
            "confidence": m.confidence_score,
            "feedback": m.feedback,
            "created_at": m.created_at.isoformat()
        })

    return {
        "id": conv.id,
        "title": conv.title,
        "mode": conv.mode,
        "messages": messages
    }

@router.post("/feedback")
def submit_feedback(payload: FeedbackRequest, db: Session = Depends(get_db)):
    msg = db.query(Message).filter(Message.id == payload.message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    msg.feedback = payload.feedback
    db.commit()
    return {"success": True, "message_id": msg.id, "feedback": payload.feedback}
