import smtplib
import logging
from abc import ABC, abstractmethod
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional, List
from datetime import datetime, UTC
from backend.app.config import settings

logger = logging.getLogger(__name__)

class BaseEmailProvider(ABC):
    @abstractmethod
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        notification_type: str = "GENERAL"
    ) -> Dict[str, Any]:
        pass

class SMTPNotificationProvider(BaseEmailProvider):
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: Optional[bool] = None,
        sender_email: Optional[str] = None,
        timeout: int = 10
    ):
        self.host = host or settings.SMTP_HOST
        self.port = port or settings.SMTP_PORT
        self.user = user or settings.SMTP_USER
        self.password = password or settings.SMTP_PASSWORD
        self.use_tls = use_tls if use_tls is not None else settings.SMTP_USE_TLS
        self.sender_email = sender_email or settings.SMTP_SENDER_EMAIL
        self.timeout = timeout

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        notification_type: str = "GENERAL"
    ) -> Dict[str, Any]:
        if not settings.SMTP_ENABLED or not self.user or not self.password:
            logger.info(f"[SMTPProvider] SMTP not configured/enabled. Email to {to_email} skipped gracefully.")
            return {
                "success": False,
                "status": "SKIPPED_UNCONFIGURED",
                "to": to_email,
                "subject": subject,
                "notification_type": notification_type,
                "timestamp": datetime.now(UTC).isoformat(),
                "error": "SMTP server not configured or disabled in environment"
            }

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{settings.SMTP_SENDER_NAME} <{self.sender_email}>"
            msg["To"] = to_email

            part1 = MIMEText(body_text, "plain")
            msg.attach(part1)

            if body_html:
                part2 = MIMEText(body_html, "html")
                msg.attach(part2)

            server = smtplib.SMTP(self.host, self.port, timeout=self.timeout)
            if self.use_tls:
                server.starttls()
            server.login(self.user, self.password)
            server.sendmail(self.sender_email, to_email, msg.as_string())
            server.quit()

            return {
                "success": True,
                "status": "DELIVERED",
                "to": to_email,
                "subject": subject,
                "notification_type": notification_type,
                "timestamp": datetime.now(UTC).isoformat()
            }
        except Exception as e:
            logger.error(f"[SMTPProvider] Failed to dispatch email to {to_email}: {e}")
            return {
                "success": False,
                "status": "FAILED",
                "to": to_email,
                "subject": subject,
                "notification_type": notification_type,
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            }

class MockEmailProvider(BaseEmailProvider):
    def __init__(self):
        self.sent_emails: List[Dict[str, Any]] = []

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        notification_type: str = "GENERAL"
    ) -> Dict[str, Any]:
        record = {
            "success": True,
            "status": "DELIVERED_MOCK",
            "to": to_email,
            "subject": subject,
            "body_text": body_text,
            "body_html": body_html,
            "notification_type": notification_type,
            "timestamp": datetime.now(UTC).isoformat()
        }
        self.sent_emails.append(record)
        return record
