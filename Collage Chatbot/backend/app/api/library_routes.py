import os
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, Request
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.entities import Attachment, Conversation, User, Project
from backend.app.security.auth import require_authenticated_user
from backend.app.security.file_validator import FileSecurityValidator
from backend.app.services.attachment_service import AttachmentService, SAFE_ERROR
router = APIRouter(prefix="/library", tags=["Student Library"])
service = AttachmentService()


def public_attachment(item: Attachment) -> dict:
    return {"id": item.id, "filename": item.filename, "type": item.file_type,
            "size": item.size, "upload_date": item.created_at.isoformat(),
            "processing_status": item.processing_status,
            "extraction_status": item.extraction_status}

@router.post("/upload")
async def upload_attachment(file: UploadFile = File(...), conversation_id: Optional[str] = Query(None), project_id: Optional[str] = Query(None),
                            db: Session = Depends(get_db), current_user: User = Depends(require_authenticated_user)):
    validator = FileSecurityValidator()
    valid, error, safe_name = validator.validate_file(file)
    if not valid:
        raise HTTPException(status_code=400, detail="This file could not be accepted. Please check the file type and size.")
    if conversation_id:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id,
                                                       Conversation.user_id == current_user.id).first()
        if not conversation or (project_id and conversation.project_id != project_id):
            raise HTTPException(status_code=404, detail="Conversation not found")
    if project_id:
        project = db.query(Project).filter(Project.id == project_id, Project.owner_id == current_user.id, Project.is_archived.is_(False)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
    content = await file.read()
    try:
        storage_path, digest, metadata = service.save(safe_name, content, file.content_type or "application/octet-stream")
        item = Attachment(user_id=current_user.id, conversation_id=conversation_id, project_id=project_id, filename=safe_name,
                          file_type=file.content_type or "application/octet-stream", size=len(content),
                          storage_path=storage_path, source_hash=digest, processing_status="READY",
                          extraction_status="READY", index_status="NOT_INDEXED", metadata_json=metadata,
                          extracted_text=metadata.pop("extracted_text", ""))
        db.add(item)
        db.commit()
        db.refresh(item)
        return {**public_attachment(item), "metadata": item.metadata_json}
    except Exception:
        db.rollback()
        if 'storage_path' in locals():
            service.delete_storage(storage_path)
        raise HTTPException(status_code=422, detail=SAFE_ERROR)

@router.get("")
def list_library(search: Optional[str] = Query(None, max_length=100), file_type: Optional[str] = Query(None, max_length=120),
                page: int = Query(1, ge=1, le=100000), page_size: int = Query(25, ge=1, le=100),
                db: Session = Depends(get_db), current_user: User = Depends(require_authenticated_user)):
    query = db.query(Attachment).filter(Attachment.user_id == current_user.id, Attachment.deleted_at.is_(None))
    if search:
        query = query.filter(Attachment.filename.ilike(f"%{search}%"))
    if file_type:
        query = query.filter(Attachment.file_type == file_type)
    total = query.count()
    items = query.order_by(Attachment.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [public_attachment(item) for item in items], "page": page, "page_size": page_size, "total": total}

@router.get("/{attachment_id}")
def get_attachment(attachment_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_authenticated_user)):
    item = db.query(Attachment).filter(Attachment.id == attachment_id, Attachment.user_id == current_user.id,
                                       Attachment.deleted_at.is_(None)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return {**public_attachment(item), "metadata": item.metadata_json, "content": item.extracted_text or ""}

@router.delete("/{attachment_id}")
def delete_attachment(attachment_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_authenticated_user)):
    item = db.query(Attachment).filter(Attachment.id == attachment_id, Attachment.user_id == current_user.id,
                                       Attachment.deleted_at.is_(None)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Attachment not found")
    service.delete_storage(item.storage_path)
    item.deleted_at = datetime.now(UTC)
    item.processing_status = "DELETED"
    item.extracted_text = None
    item.metadata_json = {}
    item.index_status = "DELETED"
    db.commit()
    return {"success": True, "id": attachment_id, "processing_status": "DELETED"}
