import hashlib
import ipaddress
import secrets
import socket
from datetime import datetime, timedelta, UTC
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.entities import User, Role, KnowledgeSource, KnowledgeVersion, KnowledgeGapEvent, AuditLog, AdminSession
from backend.app.security.auth import verify_password, require_role
from backend.app.security.sanitizer import sanitize_user_input
from backend.app.config import settings
from backend.app.services.knowledge_sync_service import KnowledgeSyncService
router = APIRouter(prefix="/admin-center", tags=["Admin Knowledge Center"])
MAX_DOCUMENT_BYTES = 15 * 1024 * 1024
ALLOWED_DOCUMENTS = {".pdf", ".txt", ".md", ".docx"}

class KnowledgeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    category: str = Field(default="General", max_length=100)
    content: str = Field(min_length=1, max_length=2_000_000)
    source: str = Field(default="ADMIN_DATABASE", max_length=100)
    status: str = Field(default="DRAFT", pattern="^(DRAFT|PENDING_REVIEW)$")
    expiry_at: Optional[datetime] = None
    change_reason: Optional[str] = Field(default=None, max_length=500)

class AdminLogin(BaseModel):
    email: str
    password: str

def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()

def _admin(user: User = Depends(require_role(["ADMIN", "SUPER_ADMIN"]))) -> User:
    return user

def _audit(db: Session, actor: User, action: str, entity: str, details: dict):
    db.add(AuditLog(actor_id=actor.id, actor_role="ADMIN", action=action, target_entity=entity, details=details))

def _safe_official_url(raw: str) -> str:
    parsed = urlparse(raw)
    allowed = urlparse(settings.AIT_OFFICIAL_BASE_URL).hostname
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.hostname.lower() != (allowed or "").lower():
        raise HTTPException(400, "Only the configured official AIT HTTPS domain may be imported")
    try:
        addresses = socket.getaddrinfo(parsed.hostname, None)
        if any(ipaddress.ip_address(item[4][0]).is_private or ipaddress.ip_address(item[4][0]).is_loopback or ipaddress.ip_address(item[4][0]).is_link_local for item in addresses):
            raise HTTPException(400, "Internal and private network targets are blocked")
    except socket.gaierror:
        raise HTTPException(400, "Official source cannot be resolved")
    return raw

def _source_view(source: KnowledgeSource) -> dict:
    return {"id": source.id, "title": source.title, "category": source.category, "source": source.source_type,
            "source_url": source.source_url, "status": source.approval_status, "created_at": source.created_at,
            "updated_at": source.updated_at, "verified_at": source.last_verified_at, "version": source.version,
            "creator": source.verified_by, "expiry_at": source.expiry_date, "is_stale": source.is_stale}

@router.post("/login")
def admin_login(payload: AdminLogin, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password) or not user.is_active or not any(r.name in {"ADMIN", "SUPER_ADMIN"} for r in user.roles):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid admin credentials")
    raw = secrets.token_urlsafe(48)
    session = AdminSession(user_id=user.id, token_hash=_hash(raw), expires_at=datetime.now(UTC) + timedelta(minutes=60))
    db.add(session); _audit(db, user, "LOGIN", "AdminSession", {"session_id": session.id}); db.commit()
    response.set_cookie("ait_admin_session", raw, max_age=3600, httponly=True, secure=not settings.DEBUG, samesite="strict", path="/")
    return {"success": True, "expires_in": 3600, "user": {"id": user.id, "email": user.email, "roles": [r.name for r in user.roles]}}

@router.post("/logout")
def admin_logout(request: Request, response: Response, db: Session = Depends(get_db), user: User = Depends(_admin)):
    raw = request.cookies.get("ait_admin_session")
    if raw:
        session = db.query(AdminSession).filter(AdminSession.token_hash == _hash(raw), AdminSession.user_id == user.id).first()
        if session: session.revoked_at = datetime.now(UTC)
    db.commit(); response.delete_cookie("ait_admin_session", path="/")
    return {"success": True}

@router.get("/knowledge")
def list_knowledge(search: Optional[str] = None, status_filter: Optional[str] = Query(None, alias="status"), page: int = 1, page_size: int = 25, db: Session = Depends(get_db), user: User = Depends(_admin)):
    query = db.query(KnowledgeSource)
    if search: query = query.filter(KnowledgeSource.title.ilike(f"%{search}%"))
    if status_filter: query = query.filter(KnowledgeSource.approval_status == status_filter.upper())
    total = query.count(); rows = query.order_by(KnowledgeSource.updated_at.desc()).offset(max(0, page - 1) * min(page_size, 100)).limit(min(page_size, 100)).all()
    return {"items": [_source_view(row) for row in rows], "total": total, "page": page, "page_size": min(page_size, 100)}

@router.post("/knowledge")
def create_knowledge(payload: KnowledgeCreate, db: Session = Depends(get_db), user: User = Depends(_admin)):
    clean = sanitize_user_input(payload.content)
    digest = hashlib.sha256(clean.encode()).hexdigest()
    duplicate = db.query(KnowledgeSource).filter(KnowledgeSource.content_hash == digest).first()
    if duplicate: raise HTTPException(409, "Duplicate knowledge content")
    source = KnowledgeSource(source_type="ADMIN_DATABASE", source_url="internal://admin", title=sanitize_user_input(payload.title), category=payload.category, raw_content=clean, clean_text=clean, content_hash=digest, is_official=False, is_verified=False, approval_status=payload.status, verification_status="PENDING", ai_visible=False, expiry_date=payload.expiry_at, version=1)
    db.add(source); db.flush(); db.add(KnowledgeVersion(source_id=source.id, version=1, content=clean, content_hash=digest, status=payload.status, change_reason=payload.change_reason, created_by=user.id)); _audit(db, user, "CREATE", "KnowledgeSource", {"source_id": source.id, "status": payload.status}); db.commit(); db.refresh(source)
    return _source_view(source)

@router.post("/knowledge/{source_id}/publish")
def publish_knowledge(source_id: str, db: Session = Depends(get_db), user: User = Depends(_admin)):
    source = db.query(KnowledgeSource).filter(KnowledgeSource.id == source_id).first()
    if not source: raise HTTPException(404, "Knowledge not found")
    source.approval_status = "APPROVED"; source.verification_status = "VERIFIED"; source.is_verified = True; source.ai_visible = True; source.last_verified_at = datetime.now(UTC); source.verified_by = user.id
    _audit(db, user, "PUBLISH", "KnowledgeSource", {"source_id": source.id, "version": source.version}); db.commit()
    result = KnowledgeSyncService(db).reindex_rag_for_source(source.id)
    return {"success": True, "knowledge": _source_view(source), "index": result}

@router.post("/knowledge/{source_id}/archive")
def archive_knowledge(source_id: str, db: Session = Depends(get_db), user: User = Depends(_admin)):
    source = db.query(KnowledgeSource).filter(KnowledgeSource.id == source_id).first()
    if not source: raise HTTPException(404, "Knowledge not found")
    result = KnowledgeSyncService(db).archive_knowledge_source(source.id, archived_by=user.id)
    return result
@router.post("/website/import")
async def import_website(url: str, db: Session = Depends(get_db), user: User = Depends(_admin)):
    _safe_official_url(url)
    report = await KnowledgeSyncService(db).sync_official_website(urls=[url], actor_id=user.id)
    return {"success": True, "read_only": True, "report": report}

@router.get("/gaps")
def list_gaps(db: Session = Depends(get_db), user: User = Depends(_admin)):
    return db.query(KnowledgeGapEvent).filter(KnowledgeGapEvent.status == "OPEN").order_by(KnowledgeGapEvent.last_seen_at.desc()).all()

@router.post("/reindex")
def reindex(db: Session = Depends(get_db), user: User = Depends(_admin)):
    return KnowledgeSyncService(db).reindex_all_approved_knowledge(actor_id=user.id)

@router.post("/documents")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(_admin)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_DOCUMENTS or not file.filename or Path(file.filename).name != file.filename: raise HTTPException(400, "Unsupported or unsafe filename")
    data = await file.read(MAX_DOCUMENT_BYTES + 1)
    if len(data) > MAX_DOCUMENT_BYTES: raise HTTPException(413, "Document exceeds size limit")
    if suffix == ".pdf" and not data.startswith(b"%PDF-"): raise HTTPException(400, "Invalid PDF signature")
    digest = hashlib.sha256(data).hexdigest()
    if db.query(KnowledgeSource).filter(KnowledgeSource.content_hash == digest).first(): raise HTTPException(409, "Duplicate document")
    if suffix == ".pdf":
        try:
            from io import BytesIO
            from PyPDF2 import PdfReader
            text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(data)).pages)
        except Exception as exc:
            raise HTTPException(400, f"Document extraction failed: {exc}")
    else:
        text = data.decode("utf-8", errors="ignore")
    source = KnowledgeSource(source_type="ADMIN_DOCUMENT", source_url="internal://upload", title=sanitize_user_input(Path(file.filename).stem), category="General", raw_content=text, clean_text=sanitize_user_input(text), content_hash=digest, is_official=False, is_verified=False, approval_status="PENDING", verification_status="PENDING", ai_visible=False, source_metadata={"filename": Path(file.filename).name, "extension": suffix, "size": len(data)})
    db.add(source); db.flush(); _audit(db, user, "UPLOAD", "KnowledgeSource", {"source_id": source.id, "size": len(data), "extension": suffix}); db.commit()
    return {"success": True, "source_id": source.id, "status": "PENDING", "extracted": bool(text)}




