import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime, UTC
from backend.app.config import settings

logger = logging.getLogger(__name__)

class BaseSMSProvider(ABC):
    @abstractmethod
    async def send_sms(
        self,
        to_number: str,
        message: str,
        notification_type: str = "GENERAL"
    ) -> Dict[str, Any]:
        pass

class TwilioSMSProvider(BaseSMSProvider):
    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_number: Optional[str] = None
    ):
        self.account_sid = account_sid or settings.TWILIO_ACCOUNT_SID
        self.auth_token = auth_token or settings.TWILIO_AUTH_TOKEN
        self.from_number = from_number or settings.TWILIO_FROM_NUMBER

    async def send_sms(
        self,
        to_number: str,
        message: str,
        notification_type: str = "GENERAL"
    ) -> Dict[str, Any]:
        if not settings.SMS_ENABLED or not self.account_sid or not self.auth_token:
            logger.info(f"[TwilioSMSProvider] Twilio credentials not configured. SMS to {to_number} skipped gracefully.")
            return {
                "success": False,
                "status": "SKIPPED_UNCONFIGURED",
                "to": to_number,
                "message": message,
                "notification_type": notification_type,
                "timestamp": datetime.now(UTC).isoformat(),
                "error": "SMS gateway not configured or disabled in environment"
            }

        try:
            from twilio.rest import Client
            client = Client(self.account_sid, self.auth_token)
            sent = client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_number
            )
            return {
                "success": True,
                "status": "DELIVERED",
                "sid": sent.sid,
                "to": to_number,
                "notification_type": notification_type,
                "timestamp": datetime.now(UTC).isoformat()
            }
        except Exception as e:
            logger.error(f"[TwilioSMSProvider] SMS dispatch failed: {e}")
            return {
                "success": False,
                "status": "FAILED",
                "to": to_number,
                "notification_type": notification_type,
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            }

class MockSMSProvider(BaseSMSProvider):
    def __init__(self):
        self.sent_sms: List[Dict[str, Any]] = []

    async def send_sms(
        self,
        to_number: str,
        message: str,
        notification_type: str = "GENERAL"
    ) -> Dict[str, Any]:
        record = {
            "success": True,
            "status": "DELIVERED_MOCK",
            "to": to_number,
            "message": message,
            "notification_type": notification_type,
            "timestamp": datetime.now(UTC).isoformat()
        }
        self.sent_sms.append(record)
        return record
