import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, UTC
from sqlalchemy.orm import Session
from backend.app.services.notifications.email_provider import BaseEmailProvider, SMTPNotificationProvider, MockEmailProvider
from backend.app.services.notifications.sms_provider import BaseSMSProvider, TwilioSMSProvider, MockSMSProvider
from backend.app.models.entities import AuditLog

logger = logging.getLogger(__name__)

class NotificationService:
    """
    Unified Notification Orchestrator for Ahmedabad Institute of Technology AI Assistant.
    Coordinates Email, SMS, and Admin Audit Logging across all institutional events.
    """
    def __init__(
        self,
        email_provider: Optional[BaseEmailProvider] = None,
        sms_provider: Optional[BaseSMSProvider] = None
    ):
        self.email_provider = email_provider or SMTPNotificationProvider()
        self.sms_provider = sms_provider or TwilioSMSProvider()

    async def notify_exam_schedule(
        self,
        db: Session,
        student_email: str,
        student_phone: Optional[str],
        course_code: str,
        subject_name: str,
        exam_date: str,
        hall: str
    ) -> Dict[str, Any]:
        subject = f"AIT Exam Schedule Notification — {subject_name} ({course_code})"
        body = (
            f"Dear Student,\n\n"
            f"Your scheduled GTU / AIT examination details are as follows:\n"
            f"Subject: {subject_name} ({course_code})\n"
            f"Date: {exam_date}\n"
            f"Venue / Hall: {hall}\n\n"
            f"Best regards,\n"
            f"Examination Cell, Ahmedabad Institute of Technology (aitindia.in)"
        )

        email_res = await self.email_provider.send_email(
            to_email=student_email,
            subject=subject,
            body_text=body,
            notification_type="ACADEMIC_EXAM"
        )

        sms_res = None
        if student_phone:
            sms_msg = f"AIT Exam Alert: {subject_name} on {exam_date} at Hall {hall}. Details at aitindia.in"
            sms_res = await self.sms_provider.send_sms(to_number=student_phone, message=sms_msg, notification_type="ACADEMIC_EXAM")

        # Audit
        audit = AuditLog(
            actor_role="SYSTEM",
            action="DISPATCH_NOTIFICATION",
            target_entity="Notification",
            details={
                "type": "ACADEMIC_EXAM",
                "email_status": email_res.get("status"),
                "recipient": student_email
            }
        )
        db.add(audit)
        db.commit()

        return {
            "success": True,
            "email": email_res,
            "sms": sms_res,
            "timestamp": datetime.now(UTC).isoformat()
        }

    async def notify_knowledge_conflict(
        self,
        db: Session,
        admin_email: str,
        topic: str,
        source_a: str,
        source_b: str
    ) -> Dict[str, Any]:
        subject = f"[AIT AI Alert] Knowledge Conflict Detected: {topic}"
        body = (
            f"An authoritative conflict was detected in the AIT Assistant knowledge base:\n"
            f"Topic: {topic}\n"
            f"Portal Value: {source_a}\n"
            f"Admin Database Value: {source_b}\n\n"
            f"Please visit the Admin Knowledge Conflict Center to resolve."
        )
        return await self.email_provider.send_email(
            to_email=admin_email,
            subject=subject,
            body_text=body,
            notification_type="KNOWLEDGE_CONFLICT"
        )
