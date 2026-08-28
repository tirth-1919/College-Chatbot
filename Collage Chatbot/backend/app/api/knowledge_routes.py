from datetime import datetime, UTC
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.entities import (
    KnowledgeSource, KnowledgeDocument, KnowledgeChunk, KnowledgeConflict, Notice, AuditLog, Fee, Course
)
from backend.app.schemas.schemas import KnowledgeConflictSchema, ResolveConflictRequest, NoticeSchema
from backend.app.security.auth import require_role
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
async def trigger_website_sync(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Trigger AIT portal sync
    seed_urls = crawler.get_seed_urls()

    # Run sync on seed pages
    synced_pages = 0
    for url in seed_urls[:5]: # Quick sync high-value pages
        page_data = await crawler.crawl_page(url)
        if page_data:
            synced_pages += 1
            # Update or create source
            src = db.query(KnowledgeSource).filter(KnowledgeSource.source_url == url).first()
            if not src:
                src = KnowledgeSource(
                    source_type="WEBSITE_CRAWL",
                    source_url=url,
                    source_page=page_data["title"],
                    title=page_data["title"],
                    content_hash=page_data["content_hash"]
                )
                db.add(src)
                db.flush()

            # Create document & chunks
            doc = KnowledgeDocument(
                source_id=src.id,
                title=page_data["title"],
                doc_type="HTML",
                raw_content=page_data["raw_html"],
                clean_text=page_data["clean_text"]
            )
            db.add(doc)
            db.flush()

            chunks = chunker.chunk_text(page_data["clean_text"], {"source_url": url, "title": page_data["title"]})
            for ch in chunks:
                k_chunk = KnowledgeChunk(
                    document_id=doc.id,
                    chunk_index=ch["chunk_index"],
                    content=ch["content"],
                    keywords=ch.get("keywords", ""),
                    section_title=page_data["title"]
                )
                db.add(k_chunk)

    db.commit()
    return {
        "success": True,
        "message": f"Successfully synchronized {synced_pages} pages from AIT official portal (https://www.aitindia.in)",
        "timestamp": datetime.now(UTC).isoformat()
    }

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
