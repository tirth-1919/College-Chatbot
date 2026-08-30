import hashlib
import secrets
from datetime import datetime, UTC
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.entities import Conversation, ConversationShare, User
from backend.app.security.auth import require_authenticated_user
router = APIRouter(prefix="/shares", tags=["Conversation Sharing"])

def safe_conversation(conversation):
    return {"title": conversation.title, "messages": [{
        "role": message.role,
        "content": message.content,
        "created_at": (message.created_at or datetime.now(UTC)).isoformat(),
        "images": message.images_json or [],
        "sources": (message.source_metadata or {}).get("sources", [])
    } for message in conversation.messages if message.role in {"user", "assistant"}]}

def owned_conversation(db, conversation_id, user_id):
    item = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == user_id).first()
    if not item: raise HTTPException(status_code=404, detail="Conversation not found")
    return item
@router.post("/conversations/{conversation_id}")
def create_share(conversation_id: str, db: Session = Depends(get_db), user: User = Depends(require_authenticated_user)):
    conversation = owned_conversation(db, conversation_id, user.id)
    token = secrets.token_urlsafe(32)
    share = ConversationShare(conversation_id=conversation.id, created_by=user.id, share_token_hash=hashlib.sha256(token.encode()).hexdigest())
    db.add(share); db.commit(); db.refresh(share)
    return {"id": share.id, "token": token, "status": "ACTIVE", "created_at": share.created_at.isoformat()}

@router.get("/{token}")
def read_share(token: str, db: Session = Depends(get_db)):
    digest = hashlib.sha256(token.encode()).hexdigest()
    share = db.query(ConversationShare).filter(ConversationShare.share_token_hash == digest, ConversationShare.revoked_at.is_(None)).first()
    if not share or not share.conversation: raise HTTPException(status_code=404, detail="Shared conversation not found")
    if share.expires_at and share.expires_at <= datetime.now(UTC): raise HTTPException(status_code=404, detail="Shared conversation not found")
    return safe_conversation(share.conversation)

@router.delete("/{share_id}")
def revoke_share(share_id: str, db: Session = Depends(get_db), user: User = Depends(require_authenticated_user)):
    share = db.query(ConversationShare).filter(ConversationShare.id == share_id, ConversationShare.created_by == user.id, ConversationShare.revoked_at.is_(None)).first()
    if not share: raise HTTPException(status_code=404, detail="Share not found")
    share.revoked_at = datetime.now(UTC); db.commit()
    return {"success": True, "status": "REVOKED"}
