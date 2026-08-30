import os
import json
from datetime import datetime, UTC
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response, Query
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.app.database import get_db
from backend.app.models.entities import User, Conversation, Message, VoiceAsset
from backend.app.schemas.schemas import ChatRequest, ChatResponse, FeedbackRequest
from backend.app.security.auth import get_current_user, require_authenticated_user
from backend.app.security.sanitizer import sanitize_user_input, check_prompt_injection
from backend.app.security.file_validator import FileSecurityValidator
from backend.app.config import settings
from ai.router.intent_router import AIRouter
from voice.stt.stt_engine import SpeechToTextEngine
from voice.tts.tts_engine import TextToSpeechEngine

router = APIRouter(prefix="/chat", tags=["Chat & Voice"])

ai_router = AIRouter(
    use_ml_intent=True,
    enable_semantic=settings.SEMANTIC_INTENT_ENABLED,
    semantic_threshold=settings.SEMANTIC_INTENT_THRESHOLD,
    context_ttl_seconds=settings.SEMANTIC_CONTEXT_TTL
)
stt_engine = SpeechToTextEngine()
tts_engine = TextToSpeechEngine()

@router.post("", response_model=ChatResponse)
@router.post("/", response_model=ChatResponse)
@router.post("/send", response_model=ChatResponse)
async def send_message(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    sanitized = sanitize_user_input(payload.message)
    if not sanitized:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    is_injection, note = check_prompt_injection(sanitized)
    if is_injection:
        msg_id = f"msg-{int(datetime.now(UTC).timestamp())}"
        violation_text = "Your request contains safety policy violations and cannot be processed."
        return {
            "id": msg_id,
            "message_id": msg_id,
            "role": "assistant",
            "conversation_id": payload.conversation_id or "conv-default",
            "answer": violation_text,
            "content": violation_text,
            "status": "complete",
            "intent": "POLICY_VIOLATION",
            "entities": {},
            "selected_source": "SAFETY_GUARD",
            "confidence": 1.0,
            "sources": [],
            "images": [],
            "suggested_followups": [],
            "voice_asset_id": None,
            "is_general_knowledge": False,
            "timestamp": datetime.now(UTC).isoformat()
        }

    # Find or create conversation
    conv = None
    if payload.conversation_id:
        conv = db.query(Conversation).filter(Conversation.id == payload.conversation_id).first()
        # Security: Verify conversation ownership if it exists
        if conv and conv.user_id:
            if not current_user or conv.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Access to this conversation is denied")
    
    if not conv:
        conv = Conversation(
            user_id=current_user.id if current_user else None,
            title=sanitized[:40] + ("..." if len(sanitized) > 40 else ""),
            mode=payload.mode
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

    # Persist user message with voice mode indicator
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=sanitized,
        language=payload.language or "en",
        # Voice mode is tracked at conversation level, but we can add metadata
        source_metadata={"input_mode": "voice" if payload.mode == "VOICE" else "text"}
    )
    db.add(user_msg)
    db.commit()

    # Route and respond via AI Router
    role = "STUDENT" if current_user else "PUBLIC"
    response_data = await ai_router.route_and_respond(
        db=db,
        query=sanitized,
        user_id=current_user.id if current_user else None,
        role=role,
        mode=payload.mode,
        conversation_id=conv.id
    )

    # Validate response is non-empty and not a query echo
    answer_text = response_data.get("answer", response_data.get("content", ""))
    if not answer_text or not answer_text.strip():
        answer_text = "I'm sorry, I couldn't answer that right now. Please try again."
        response_data["answer"] = answer_text
        response_data["content"] = answer_text

    # Ensure answer is not just echoing the user's query
    if answer_text.strip() == sanitized.strip():
        # Let the resolver handle this with Gemini instead of generic fallback
        answer_text = "I'd be happy to help you with that! Could you provide more details about what you'd like to know?"
        response_data["answer"] = answer_text
        response_data["content"] = answer_text

    # Persist assistant message
    asst_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=response_data["answer"],
        language=payload.language or "en",
        intent=response_data["intent"],
        entities=response_data["entities"],
        selected_source=response_data["selected_source"],
        source_metadata={"sources": response_data["sources"]},
        images_json=response_data["images"],
        voice_asset_id=response_data["voice_asset_id"],
        confidence_score=response_data["confidence"]
    )
    db.add(asst_msg)
    db.commit()

    response_data["id"] = asst_msg.id
    response_data["message_id"] = asst_msg.id
    response_data["role"] = "assistant"
    response_data["content"] = response_data["answer"]
    response_data["status"] = "complete"
    response_data["conversation_id"] = conv.id
    return response_data

@router.post("/voice")
async def handle_voice_chat(
    file: Optional[UploadFile] = File(None),
    transcript: Optional[str] = Form(None),
    conversation_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    final_text = transcript or ""
    detected_lang = "en"
    
    if file:
        # Validate audio file
        validator = FileSecurityValidator()
        is_valid, error_msg, safe_filename = validator.validate_file(file)

        if not is_valid:
            raise HTTPException(status_code=400, detail=f"File validation failed: {error_msg}")

        audio_bytes = await file.read()
        stt_result = stt_engine.transcribe_audio_bytes(audio_bytes)
        final_text = stt_result.get("transcript", "")
        detected_lang = stt_result.get("language", "en")

    if not final_text:
        raise HTTPException(status_code=400, detail="No speech or transcript detected")

    chat_payload = ChatRequest(
        conversation_id=conversation_id,
        message=final_text,
        language=detected_lang,
        mode="VOICE"
    )
    res = await send_message(chat_payload, db=db, current_user=current_user)
    return {
        "user_transcript": final_text,
        "language": detected_lang,
        "chat_response": res
    }

@router.get("/voice-asset/{asset_id}")
def get_voice_audio(asset_id: str, db: Session = Depends(get_db)):
    asset = db.query(VoiceAsset).filter(VoiceAsset.id == asset_id).first()
    if not asset or not os.path.exists(asset.file_path):
        raise HTTPException(status_code=404, detail="Voice audio asset not found")
    return FileResponse(asset.file_path, media_type="audio/wav")

@router.get("/conversations")
def list_conversations(
    search: Optional[str] = Query(None, description="Search conversations by title"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    if not current_user:
        return []
    
    query = db.query(Conversation).filter(Conversation.user_id == current_user.id)
    
    # Add search filter if provided
    if search:
        search_term = f"%{search}%"
        query = query.filter(Conversation.title.ilike(search_term))
    
    convs = query.order_by(Conversation.updated_at.desc()).all()

    return [
        {
            "id": c.id,
            "title": c.title,
            "mode": c.mode,
            "is_pinned": c.is_pinned,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat()
        }
        for c in convs
    ]

@router.get("/conversations/{conv_id}")
def get_conversation_details(
    conv_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Security: Verify conversation ownership
    if conv.user_id and current_user:
        if conv.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access to this conversation is denied")
    elif conv.user_id and not current_user:
        raise HTTPException(status_code=401, detail="Authentication required to access this conversation")

    messages = []
    for m in conv.messages:
        messages.append({
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "language": m.language,
            "intent": m.intent,
            "selected_source": m.selected_source,
            "sources": m.source_metadata.get("sources", []) if m.source_metadata else [],
            "images": m.images_json or [],
            "voice_asset_id": m.voice_asset_id,
            "confidence": m.confidence_score,
            "feedback": m.feedback,
            "created_at": m.created_at.isoformat()
        })

    return {
        "id": conv.id,
        "title": conv.title,
        "mode": conv.mode,
        "messages": messages
    }

@router.post("/feedback")
def submit_feedback(payload: FeedbackRequest, db: Session = Depends(get_db)):
    msg = db.query(Message).filter(Message.id == payload.message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    msg.feedback = payload.feedback
    db.commit()

    # If student provided negative feedback, queue for controlled intent training review
    if payload.feedback in ["unhelpful", "reported"]:
        from backend.app.models.entities import TrainingExample
        from backend.app.security.pii import PIIDetector
        detector = PIIDetector()

        # Find the user's question before this assistant response
        user_msg = (
            db.query(Message)
            .filter(Message.conversation_id == msg.conversation_id, Message.role == "user", Message.created_at <= msg.created_at)
            .order_by(Message.created_at.desc())
            .first()
        )
        if user_msg and user_msg.content:
            raw_text = user_msg.content.strip()
            # Redact any PII before staging candidate training example
            scrubbed_text = detector.redact_pii(raw_text)
            if scrubbed_text:
                existing = db.query(TrainingExample).filter(TrainingExample.text == scrubbed_text).first()
                if not existing:
                    example = TrainingExample(
                        text=scrubbed_text,
                        language=user_msg.language or "en",
                        predicted_intent=msg.intent,
                        status="PENDING",
                        source="STUDENT_FEEDBACK",
                        metadata_json={
                            "comment": payload.comment,
                            "message_id": msg.id,
                            "was_scrubbed": (scrubbed_text != raw_text)
                        }
                    )
                    db.add(example)
                    db.commit()

    return {"success": True, "message_id": msg.id, "feedback": payload.feedback}


# ----------------- Chat Management Endpoints -----------------

class RenameConversationRequest(BaseModel):
    title: str

@router.patch("/conversations/{conv_id}/rename")
def rename_conversation(
    conv_id: str,
    payload: RenameConversationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user)
):
    """Rename a conversation (ChatGPT-style)"""
    # Verify conversation ownership
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Update title
    conv.title = payload.title
    conv.updated_at = datetime.now(UTC)
    db.commit()
    
    return {
        "success": True,
        "id": conv.id,
        "title": conv.title,
        "updated_at": conv.updated_at.isoformat()
    }

@router.delete("/conversations/{conv_id}")
def delete_conversation(
    conv_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user)
):
    """Delete a conversation (ChatGPT-style)"""
    # Verify conversation ownership
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Delete conversation (cascade will handle messages)
    db.delete(conv)
    db.commit()
    
    return {
        "success": True,
        "message": "Conversation deleted successfully"
    }

@router.post("/conversations/{conv_id}/archive")
def archive_conversation(
    conv_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user)
):
    """Archive a conversation"""
    # Verify conversation ownership
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Toggle archive status
    conv.is_archived = not conv.is_archived
    conv.updated_at = datetime.now(UTC)
    db.commit()
    
    return {
        "success": True,
        "id": conv.id,
        "is_archived": conv.is_archived,
        "updated_at": conv.updated_at.isoformat()
    }

@router.post("/conversations/{conv_id}/pin")
def pin_conversation(
    conv_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user)
):
    """Pin/unpin a conversation"""
    # Verify conversation ownership
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Toggle pin status
    conv.is_pinned = not conv.is_pinned
    conv.updated_at = datetime.now(UTC)
    db.commit()
    
    return {
        "success": True,
        "id": conv.id,
        "is_pinned": conv.is_pinned,
        "updated_at": conv.updated_at.isoformat()
    }
