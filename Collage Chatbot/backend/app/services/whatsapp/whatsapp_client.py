import hmac
import hashlib
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, UTC
import httpx
from backend.app.config import settings

logger = logging.getLogger(__name__)

class MetaWhatsAppClient:
    """
    Client for Meta WhatsApp Business Cloud API.
    Handles webhook validation, HMAC-SHA256 signature verification, and outbound message dispatch.
    """
    def __init__(
        self,
        phone_number_id: Optional[str] = None,
        access_token: Optional[str] = None,
        verify_token: Optional[str] = None,
        webhook_secret: Optional[str] = None
    ):
        self.phone_number_id = phone_number_id or settings.WHATSAPP_PHONE_NUMBER_ID
        self.access_token = access_token or settings.WHATSAPP_ACCESS_TOKEN
        self.verify_token = verify_token or settings.WHATSAPP_VERIFY_TOKEN
        self.webhook_secret = webhook_secret or settings.WHATSAPP_WEBHOOK_SECRET
        self.base_url = f"https://graph.facebook.com/v19.0/{self.phone_number_id}/messages"

    def verify_webhook_token(self, mode: Optional[str], token: Optional[str], challenge: Optional[str]) -> Optional[str]:
        """Validates Meta Webhook handshake challenge"""
        if mode == "subscribe" and token == self.verify_token:
            logger.info("[WhatsApp] Webhook subscription handshake verified successfully")
            return challenge
        return None

    def verify_signature(self, payload_bytes: bytes, signature_header: Optional[str]) -> bool:
        """Verifies X-Hub-Signature-256 HMAC header from Meta"""
        if not self.webhook_secret:
            # In development/unconfigured mode, allow unsigned webhook for testing
            return True
        if not signature_header or not signature_header.startswith("sha256="):
            return False

        expected_sig = hmac.new(
            self.webhook_secret.encode(),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        actual_sig = signature_header.split("sha256=")[1]
        return hmac.compare_digest(expected_sig, actual_sig)

    async def send_text_message(self, recipient_phone: str, text: str) -> Dict[str, Any]:
        """Dispatches outbound WhatsApp text message to user"""
        if not settings.WHATSAPP_ENABLED or not self.access_token or not self.phone_number_id:
            logger.info(f"[WhatsApp] WhatsApp not configured/enabled. Outbound message to {recipient_phone} skipped gracefully.")
            return {
                "success": False,
                "status": "SKIPPED_UNCONFIGURED",
                "to": recipient_phone,
                "timestamp": datetime.now(UTC).isoformat()
            }

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_phone,
            "type": "text",
            "text": {"preview_url": True, "body": text}
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(self.base_url, headers=headers, json=payload)
                if res.status_code in [200, 201]:
                    return {"success": True, "status": "DELIVERED", "data": res.json()}
                else:
                    logger.error(f"[WhatsApp] Meta API error {res.status_code}: {res.text}")
                    return {"success": False, "status": "FAILED", "error": res.text}
        except Exception as e:
            logger.error(f"[WhatsApp] Outbound send failed: {e}")
            return {"success": False, "status": "FAILED", "error": str(e)}

class MockWhatsAppClient(MetaWhatsAppClient):
    def __init__(self):
        super().__init__()
        self.sent_messages: List[Dict[str, Any]] = []

    async def send_text_message(self, recipient_phone: str, text: str) -> Dict[str, Any]:
        record = {
            "success": True,
            "status": "DELIVERED_MOCK",
            "to": recipient_phone,
            "body": text,
            "timestamp": datetime.now(UTC).isoformat()
        }
        self.sent_messages.append(record)
        return record
