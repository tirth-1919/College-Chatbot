import hashlib
import secrets
from datetime import datetime, UTC
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.entities import Project, Conversation, ConversationShare, Canvas, CanvasVersion, User
from backend.app.security.auth import require_authenticated_user
from backend.app.security.sanitizer import sanitize_user_input
from backend.app.api.chat_routes import ai_router
router = APIRouter(prefix="/workspace", tags=["Projects, Sharing & Canvas"])

class ProjectInput(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: Optional[str] = Field(None, max_length=1000)
    instructions: Optional[str] = Field(None, max_length=10000)

class CanvasInput(BaseModel):
    title: str = Field(default="Untitled Canvas", max_length=255)
    content: str = Field(default="", max_length=500000)
    content_type: str = Field(default="markdown", max_length=30)

class CanvasAction(BaseModel):
    action: str = Field(min_length=1, max_length=40)
    selection: str = Field(default="", max_length=50000)
    context: str = Field(default="", max_length=50000)


def owned_project(db, project_id, user_id):
    item = db.query(Project).filter(Project.id == project_id, Project.owner_id == user_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Project not found")
    return item

def project_view(item):
    return {"id": item.id, "name": item.name, "description": item.description,
            "instructions": item.instructions, "is_archived": item.is_archived,
            "created_at": item.created_at.isoformat(), "updated_at": item.updated_at.isoformat()}

def canvas_view(item):
    return {"id": item.id, "project_id": item.project_id, "title": item.title,
            "content": item.content, "content_type": item.content_type,
            "revision": item.revision, "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat()}

@router.post("/projects")
def create_project(payload: ProjectInput, db: Session = Depends(get_db), user: User = Depends(require_authenticated_user)):
    item = Project(owner_id=user.id, name=sanitize_user_input(payload.name),
                   description=sanitize_user_input(payload.description or ""), instructions=payload.instructions)
    db.add(item); db.commit(); db.refresh(item)
    return project_view(item)

@router.get("/projects")
def list_projects(search: Optional[str] = Query(None, max_length=100), page: int = Query(1, ge=1, le=10000),
                  page_size: int = Query(25, ge=1, le=100), db: Session = Depends(get_db),
                  user: User = Depends(require_authenticated_user)):
    query = db.query(Project).filter(Project.owner_id == user.id, Project.is_archived.is_(False))
    if search: query = query.filter(Project.name.ilike(f"%{search}%"))
    total = query.count(); items = query.order_by(Project.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [project_view(item) for item in items], "page": page, "page_size": page_size, "total": total}

@router.get("/projects/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db), user: User = Depends(require_authenticated_user)):
    return project_view(owned_project(db, project_id, user.id))

@router.patch("/projects/{project_id}")
def update_project(project_id: str, payload: ProjectInput, db: Session = Depends(get_db), user: User = Depends(require_authenticated_user)):
    item = owned_project(db, project_id, user.id)
    item.name = sanitize_user_input(payload.name); item.description = sanitize_user_input(payload.description or ""); item.instructions = payload.instructions
    db.commit(); db.refresh(item); return project_view(item)

@router.delete("/projects/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db), user: User = Depends(require_authenticated_user)):
    item = owned_project(db, project_id, user.id)
    for conversation in item.conversations: conversation.project_id = None
    for attachment in item.attachments: attachment.project_id = None
    item.is_archived = True; db.commit()
    return {"success": True, "id": project_id, "archived": True}

@router.get("/projects/{project_id}/conversations")
def project_conversations(project_id: str, search: Optional[str] = Query(None, max_length=100), page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), db: Session = Depends(get_db), user: User = Depends(require_authenticated_user)):
    owned_project(db, project_id, user.id)
    query = db.query(Conversation).filter(Conversation.project_id == project_id, Conversation.user_id == user.id)
    if search: query = query.filter(Conversation.title.ilike(f"%{search}%"))
    total = query.count(); items = query.order_by(Conversation.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [{"id": item.id, "title": item.title, "updated_at": item.updated_at.isoformat()} for item in items], "page": page, "page_size": page_size, "total": total}

@router.post("/projects/{project_id}/canvases")
def create_canvas(project_id: str, payload: CanvasInput, db: Session = Depends(get_db), user: User = Depends(require_authenticated_user)):
    owned_project(db, project_id, user.id)
    item = Canvas(project_id=project_id, owner_id=user.id, title=sanitize_user_input(payload.title), content=payload.content, content_type=payload.content_type)
    db.add(item); db.flush(); db.add(CanvasVersion(canvas_id=item.id, version=1, content=payload.content)); db.commit(); db.refresh(item)
    return canvas_view(item)

@router.get("/projects/{project_id}/canvases")
def list_canvases(project_id: str, db: Session = Depends(get_db), user: User = Depends(require_authenticated_user)):
    owned_project(db, project_id, user.id)
    return {"items": [canvas_view(item) for item in db.query(Canvas).filter(Canvas.project_id == project_id, Canvas.owner_id == user.id).order_by(Canvas.updated_at.desc()).limit(100).all()]}

@router.get("/canvases/{canvas_id}")
def get_canvas(canvas_id: str, db: Session = Depends(get_db), user: User = Depends(require_authenticated_user)):
    item = db.query(Canvas).filter(Canvas.id == canvas_id, Canvas.owner_id == user.id).first()
    if not item: raise HTTPException(status_code=404, detail="Canvas not found")
    return {**canvas_view(item), "versions": [{"version": version.version, "created_at": version.created_at.isoformat()} for version in item.versions]}

@router.put("/canvases/{canvas_id}")
def update_canvas(canvas_id: str, payload: CanvasInput, db: Session = Depends(get_db), user: User = Depends(require_authenticated_user)):
    item = db.query(Canvas).filter(Canvas.id == canvas_id, Canvas.owner_id == user.id).first()
    if not item: raise HTTPException(status_code=404, detail="Canvas not found")
    item.title = sanitize_user_input(payload.title); item.content = payload.content; item.content_type = payload.content_type; item.revision += 1
    db.add(CanvasVersion(canvas_id=item.id, version=item.revision, content=payload.content)); db.commit(); db.refresh(item)
    return canvas_view(item)

@router.post("/canvases/{canvas_id}/restore/{version}")
def restore_canvas(canvas_id: str, version: int, db: Session = Depends(get_db), user: User = Depends(require_authenticated_user)):
    item = db.query(Canvas).filter(Canvas.id == canvas_id, Canvas.owner_id == user.id).first()
    saved = db.query(CanvasVersion).filter(CanvasVersion.canvas_id == canvas_id, CanvasVersion.version == version).first()
    if not item or not saved: raise HTTPException(status_code=404, detail="Canvas version not found")
    item.content = saved.content; item.revision += 1; db.add(CanvasVersion(canvas_id=item.id, version=item.revision, content=saved.content)); db.commit(); db.refresh(item)
    return canvas_view(item)

@router.get("/canvases/{canvas_id}/export")
def export_canvas(canvas_id: str, format: str = Query("txt", pattern="^(txt|md)$"), db: Session = Depends(get_db), user: User = Depends(require_authenticated_user)):
    item = db.query(Canvas).filter(Canvas.id == canvas_id, Canvas.owner_id == user.id).first()
    if not item: raise HTTPException(status_code=404, detail="Canvas not found")
    media = "text/markdown" if format == "md" else "text/plain"
    return PlainTextResponse(item.content, media_type=media, headers={"Content-Disposition": f'attachment; filename="canvas.{format}"'})

@router.post("/canvases/{canvas_id}/ai")
async def canvas_ai_action(canvas_id: str, payload: CanvasAction, db: Session = Depends(get_db), user: User = Depends(require_authenticated_user)):
    item = db.query(Canvas).filter(Canvas.id == canvas_id, Canvas.owner_id == user.id).first()
    if not item: raise HTTPException(status_code=404, detail="Canvas not found")
    selected = payload.selection or item.content
    prompt = f"Canvas action: {payload.action}\nSelected content:\n{selected}\nAdditional context:\n{payload.context[:12000]}"
    result = await ai_router.route_and_respond(db=db, query=prompt, user_id=user.id, role="STUDENT", mode="TEXT")
    return {"action": payload.action, "selection": selected, "result": result.get("answer", "")}

