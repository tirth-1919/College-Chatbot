"""
Enhanced Admin Dashboard Routes
Complete admin controls for knowledge, AI, safety, analytics, and infrastructure
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.services.knowledge_governance import KnowledgeGovernanceService
from backend.app.services.analytics_service import AnalyticsService
from backend.app.services.backup_service import BackupService
from backend.app.security.ai_safety import AISafetyService
from backend.app.security.enhanced_auth import EnhancedAuthService
from backend.app.security.auth import require_role
from typing import Optional

router = APIRouter(
    prefix="/admin/enhanced",
    tags=["Enhanced Admin"],
    dependencies=[Depends(require_role(["ADMIN", "SUPER_ADMIN"]))]
 )


# Knowledge Management Routes
@router.get("/knowledge/review-queue")
async def get_knowledge_review_queue(db: Session = Depends(get_db)):
    """Get knowledge review queue"""
    service = KnowledgeGovernanceService(db)
    return service.get_review_queue()


@router.get("/knowledge/stale")
async def get_stale_knowledge(days: int = 30, db: Session = Depends(get_db)):
    """Get stale knowledge that needs updating"""
    service = KnowledgeGovernanceService(db)
    return service.check_stale_knowledge(days)


@router.get("/knowledge/history/{document_id}")
async def get_document_history(document_id: int, db: Session = Depends(get_db)):
    """Get document version history"""
    service = KnowledgeGovernanceService(db)
    return service.get_document_history(document_id)


# Analytics Dashboard Routes
@router.get("/analytics/dashboard")
async def get_analytics_dashboard(days: int = 30, db: Session = Depends(get_db)):
    """Get complete analytics dashboard"""
    service = AnalyticsService(db)
    return service.get_analytics_dashboard(days)


@router.get("/analytics/users")
async def get_user_analytics(days: int = 30, db: Session = Depends(get_db)):
    """Get user analytics"""
    service = AnalyticsService(db)
    return service.get_user_analytics(days)


@router.get("/analytics/questions")
async def get_question_analytics(days: int = 30, db: Session = Depends(get_db)):
    """Get question analytics"""
    service = AnalyticsService(db)
    return service.get_question_analytics(days)


@router.get("/analytics/ai-usage")
async def get_ai_usage_analytics(days: int = 30, db: Session = Depends(get_db)):
    """Get AI usage analytics"""
    service = AnalyticsService(db)
    return service.get_ai_usage_analytics(days)


# Backup and Infrastructure Routes
@router.get("/backup/status")
async def get_backup_status(db: Session = Depends(get_db)):
    """Get backup status"""
    service = BackupService()
    return service.get_backup_status()


@router.post("/backup/create")
async def create_backup(db: Session = Depends(get_db)):
    """Create full system backup"""
    service = BackupService()
    return service.create_full_backup(db)


@router.post("/backup/cleanup")
async def cleanup_old_backups():
    """Clean up old backups"""
    service = BackupService()
    deleted_count, deleted_files = service.cleanup_old_backups()
    return {
        'success': True,
        'deleted_count': deleted_count,
        'deleted_files': deleted_files
    }


# AI Safety and Security Routes
@router.get("/safety/status")
async def get_safety_status():
    """Get AI safety status"""
    service = AISafetyService()
    return service.get_safety_status()


@router.post("/safety/kill-switch/activate")
async def activate_kill_switch(reason: Optional[str] = None):
    """Activate AI kill switch"""
    service = AISafetyService()
    return service.activate_kill_switch(reason)


@router.post("/safety/kill-switch/deactivate")
async def deactivate_kill_switch():
    """Deactivate AI kill switch"""
    service = AISafetyService()
    return service.deactivate_kill_switch()


@router.post("/safety/knowledge/freeze")
async def freeze_knowledge(reason: Optional[str] = None):
    """Freeze knowledge base"""
    service = AISafetyService()
    return service.freeze_knowledge(reason)


@router.post("/safety/knowledge/unfreeze")
async def unfreeze_knowledge():
    """Unfreeze knowledge base"""
    service = AISafetyService()
    return service.unfreeze_knowledge()


# Authentication Management Routes
@router.get("/auth/users")
async def get_user_list(db: Session = Depends(get_db)):
    """Get list of users"""
    from backend.app.models.entities import User
    users = db.query(User).all()
    
    return {
        'users': [
            {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'roles': [role.name for role in user.roles],
                'is_active': user.is_active,
                'created_at': user.created_at.isoformat() if user.created_at else None
            }
            for user in users
        ]
    }


@router.get("/auth/stats")
async def get_auth_stats(db: Session = Depends(get_db)):
    """Get authentication statistics"""
    from backend.app.models.entities import User
    from sqlalchemy import func
    
    total_users = db.query(func.count(User.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    
    # Count by role
    role_counts = db.query(User.role, func.count(User.id)).group_by(User.role).all()
    
    return {
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': total_users - active_users,
        'role_distribution': {role: count for role, count in role_counts}
    }
