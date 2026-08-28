from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.entities import KnowledgeConflict, Fee, Course

class KnowledgeConflictDetector:
    """Detects discrepancies across website, documents, and admin database records"""

    @staticmethod
    def check_fee_conflict(
        db: Session,
        course_code: str,
        academic_year: str,
        website_stated_fee: float,
        source_url: str
    ) -> Optional[KnowledgeConflict]:
        course = db.query(Course).filter(Course.code == course_code.upper()).first()
        if not course:
            return None

        db_fee_record = db.query(Fee).filter(
            Fee.course_id == course.id,
            Fee.academic_year == academic_year,
            Fee.verification_status == "VERIFIED"
        ).first()

        if db_fee_record and abs(db_fee_record.tuition_fee - website_stated_fee) > 0.01:
            # Conflict detected!
            conflict = KnowledgeConflict(
                topic=f"{course_code.upper()} Fee for {academic_year}",
                source_a_type="OFFICIAL_WEBSITE",
                source_a_value=f"₹{website_stated_fee:,.2f}",
                source_a_ref=source_url,
                source_b_type="ADMIN_DATABASE",
                source_b_value=f"₹{db_fee_record.tuition_fee:,.2f}",
                source_b_ref=f"Fee Record ID: {db_fee_record.id}",
                status="OPEN"
            )
            db.add(conflict)
            db.commit()
            db.refresh(conflict)
            return conflict

        return None
