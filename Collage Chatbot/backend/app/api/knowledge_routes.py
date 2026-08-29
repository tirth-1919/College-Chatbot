from datetime import datetime, UTC
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.entities import (
    KnowledgeSource, KnowledgeDocument, KnowledgeChunk, KnowledgeConflict, Notice, AuditLog, Fee, Course, PendingKnowledgeUpdate
)
from backend.app.schemas.schemas import KnowledgeConflictSchema, ResolveConflictRequest, NoticeSchema, RejectKnowledgeRequest
from backend.app.security.auth import require_role, get_current_user
from backend.app.services.knowledge_sync_service import KnowledgeSyncService
from rag.crawlers.ait.crawler import AITWebsiteCrawler
from rag.chunkers.chunker import DocumentChunker

router = APIRouter(prefix="/knowledge", tags=["Knowledge Center & Conflicts"])

crawler = AITWebsiteCrawler()
chunker = DocumentChunker()

# ----------------- Notices -----------------
@router.get("/notices")
def get_notices(category: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Notice).filter(Notice.is_active == True)
    if category:
        query = query.filter(Notice.category == category)
    notices = query.order_by(Notice.publish_date.desc()).all()
    return [
        {
            "id": n.id,
            "title": n.title,
            "category": n.category,
            "department": n.department,
            "content": n.content,
            "publish_date": n.publish_date.isoformat() if n.publish_date else "",
            "source_url": n.source_url,
            "academic_year": n.academic_year
        }
        for n in notices
    ]

# ----------------- Knowledge Sources & Documents -----------------
@router.get("/sources")
def get_sources(db: Session = Depends(get_db)):
    sources = db.query(KnowledgeSource).all()
    return [
        {
            "id": s.id,
            "title": s.title,
            "source_type": s.source_type,
            "source_url": s.source_url,
            "source_page": s.source_page,
            "authority_score": s.authority_score,
            "verification_status": s.verification_status,
            "documents_count": len(s.documents),
            "retrieved_at": s.retrieved_at.isoformat()
        }
        for s in sources
    ]

@router.post("/sync/website", dependencies=[Depends(require_role(["ADMIN", "SUPER_ADMIN"]))])
async def trigger_website_sync(
    background_tasks: BackgroundTasks,
    current_user: Optional[Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = KnowledgeSyncService(db)
    actor_id = current_user.id if current_user else "ADMIN"
    report = await service.sync_official_website(actor_id=actor_id)
    return {
        "success": True,
        "message": f"Synchronized AIT official portal: {report['new_pending']} new pending, {report['modified_pending']} modified, {report['unchanged']} unchanged.",
        "report": report
    }

@router.get("/pending", dependencies=[Depends(require_role(["ADMIN", "SUPER_ADMIN"]))])
def get_pending_updates(db: Session = Depends(get_db)):
    updates = db.query(PendingKnowledgeUpdate).filter(PendingKnowledgeUpdate.approval_status == "PENDING").all()
    return [
        {
            "id": u.id,
            "source_id": u.source_id,
            "source_url": u.source_url,
            "title": u.title,
            "category": u.category,
            "source_type": u.source_type,
            "old_value": u.old_value,
            "new_value": u.new_value,
            "change_type": u.change_type,
            "change_summary": u.change_summary,
            "content_hash": u.content_hash,
            "approval_status": u.approval_status,
            "detected_at": u.detected_at.isoformat() if u.detected_at else ""
        }
        for u in updates
    ]

@router.post("/{update_id}/approve", dependencies=[Depends(require_role(["ADMIN", "SUPER_ADMIN"]))])
def approve_update(update_id: str, current_user: Optional[Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    service = KnowledgeSyncService(db)
    approved_by = current_user.email if current_user else "ADMIN"
    return service.approve_pending_update(update_id, approved_by=approved_by)

@router.post("/{update_id}/reject", dependencies=[Depends(require_role(["ADMIN", "SUPER_ADMIN"]))])
def reject_update(update_id: str, payload: Optional[RejectKnowledgeRequest] = None, current_user: Optional[Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    service = KnowledgeSyncService(db)
    rejected_by = current_user.email if current_user else "ADMIN"
    return service.reject_pending_update(update_id, rejected_by=rejected_by, reason=payload.reason if payload else None)

@router.post("/rag/reindex", dependencies=[Depends(require_role(["ADMIN", "SUPER_ADMIN"]))])
def reindex_rag(current_user: Optional[Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    service = KnowledgeSyncService(db)
    actor_id = current_user.email if current_user else "ADMIN"
    return service.reindex_all_approved_knowledge(actor_id=actor_id)

# ----------------- Knowledge Conflicts -----------------
@router.get("/conflicts")
def list_conflicts(status: Optional[str] = "OPEN", db: Session = Depends(get_db)):
    query = db.query(KnowledgeConflict)
    if status:
        query = query.filter(KnowledgeConflict.status == status)
    conflicts = query.order_by(KnowledgeConflict.created_at.desc()).all()
    return [
        {
            "id": c.id,
            "topic": c.topic,
            "source_a_type": c.source_a_type,
            "source_a_value": c.source_a_value,
            "source_a_ref": c.source_a_ref,
            "source_b_type": c.source_b_type,
            "source_b_value": c.source_b_value,
            "source_b_ref": c.source_b_ref,
            "status": c.status,
            "resolution_choice": c.resolution_choice,
            "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
            "created_at": c.created_at.isoformat()
        }
        for c in conflicts
    ]

@router.post("/conflicts/resolve", dependencies=[Depends(require_role(["ADMIN", "SUPER_ADMIN"]))])
def resolve_conflict(payload: ResolveConflictRequest, db: Session = Depends(get_db)):
    conflict = db.query(KnowledgeConflict).filter(KnowledgeConflict.id == payload.conflict_id).first()
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")

    conflict.status = "RESOLVED"
    conflict.resolution_choice = payload.resolution_choice
    conflict.resolution_notes = payload.resolution_notes
    conflict.resolved_at = datetime.now(UTC)

    # If conflict resolution chose custom override or keeping database, sync database
    if payload.custom_value and "BCA Fee" in conflict.topic:
        course = db.query(Course).filter(Course.code == "BCA").first()
        if course:
            val_clean = float(payload.custom_value.replace("₹", "").replace(",", "").strip())
            fee = db.query(Fee).filter(Fee.course_id == course.id, Fee.academic_year == "2026-27").first()
            if fee:
                fee.tuition_fee = val_clean
                fee.total_fee = val_clean + fee.exam_fee + fee.other_charges
                fee.version += 1

    audit = AuditLog(
        actor_role="ADMIN",
        action="RESOLVE_KNOWLEDGE_CONFLICT",
        target_entity="KnowledgeConflict",
        details={
            "conflict_id": conflict.id,
            "topic": conflict.topic,
            "resolution": payload.resolution_choice
        }
    )
    db.add(audit)
    db.commit()

    return {
        "success": True,
        "message": f"Conflict for '{conflict.topic}' resolved successfully",
        "conflict_id": conflict.id,
        "resolution": payload.resolution_choice
    }

@router.post("/conflicts/reopen", dependencies=[Depends(require_role(["ADMIN", "SUPER_ADMIN"]))])
def reopen_conflict(conflict_id: str, db: Session = Depends(get_db)):
    conflict = db.query(KnowledgeConflict).filter(KnowledgeConflict.id == conflict_id).first()
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")

    conflict.status = "OPEN"
    conflict.resolved_at = None
    audit = AuditLog(
        actor_role="ADMIN",
        action="REOPEN_KNOWLEDGE_CONFLICT",
        target_entity="KnowledgeConflict",
        details={"conflict_id": conflict.id, "topic": conflict.topic}
    )
    db.add(audit)
    db.commit()
    return {"success": True, "message": f"Conflict for '{conflict.topic}' reopened for review"}