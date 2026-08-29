"""
Enhanced Services API Routes
API endpoints for all the new enhanced services
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.security.enhanced_auth import EnhancedAuthService
from backend.app.services.knowledge_governance import KnowledgeGovernanceService
from backend.app.services.academic_intelligence import AcademicIntelligenceService
from backend.app.services.campus_services import CampusServicesService
from backend.app.services.automation_engine import AutomationEngine
from backend.app.security.ai_safety import AISafetyService
from typing import Optional

router = APIRouter(prefix="/enhanced", tags=["Enhanced Services"])


# Knowledge Governance Routes
@router.post("/knowledge/submit-review/{document_id}")
async def submit_for_review(document_id: int, user_id: int, db: Session = Depends(get_db)):
    """Submit document for review"""
    service = KnowledgeGovernanceService(db)
    result = service.submit_for_review(document_id, user_id)
    
    if result['success']:
        return result
    else:
        raise HTTPException(status_code=400, detail=result['error'])


@router.post("/knowledge/review/{document_id}")
async def review_document(document_id: int, reviewer_id: int, approved: bool, 
                       feedback: Optional[str] = None, db: Session = Depends(get_db)):
    """Review a document"""
    service = KnowledgeGovernanceService(db)
    result = service.review_document(document_id, reviewer_id, approved, feedback)
    
    if result['success']:
        return result
    else:
        raise HTTPException(status_code=400, detail=result['error'])


@router.get("/knowledge/review-queue")
async def get_review_queue(db: Session = Depends(get_db)):
    """Get documents pending review"""
    service = KnowledgeGovernanceService(db)
    return service.get_review_queue()


# Academic Intelligence Routes
@router.get("/academic/syllabus-analysis/{course_id}")
async def analyze_syllabus(course_id: int, db: Session = Depends(get_db)):
    """Analyze syllabus for a course"""
    service = AcademicIntelligenceService(db)
    result = service.analyze_syllabus(course_id)
    
    if result['success']:
        return result
    else:
        raise HTTPException(status_code=404, detail=result['error'])


@router.get("/academic/study-plan/{user_id}/{semester}")
async def get_study_plan(user_id: int, semester: int, db: Session = Depends(get_db)):
    """Generate study plan"""
    service = AcademicIntelligenceService(db)
    return service.generate_study_plan(user_id, semester)


# Campus Services Routes
@router.get("/campus/faq")
async def get_campus_faq(db: Session = Depends(get_db)):
    """Get campus FAQ"""
    service = CampusServicesService(db)
    return service.get_campus_faq()


@router.get("/campus/navigation/{destination}")
async def get_navigation(destination: str, db: Session = Depends(get_db)):
    """Get campus navigation"""
    service = CampusServicesService(db)
    result = service.get_campus_navigation(destination)
    
    if result['success']:
        return result
    else:
        raise HTTPException(status_code=404, detail=result['error'])


# Automation Engine Routes
@router.get("/automation/knowledge-gaps")
async def detect_knowledge_gaps(days: int = 7, db: Session = Depends(get_db)):
    """Detect knowledge gaps"""
    service = AutomationEngine(db)
    return service.detect_knowledge_gaps(days)


@router.get("/automation/faq-suggestions")
async def generate_faq_suggestions(days: int = 30, db: Session = Depends(get_db)):
    """Generate FAQ suggestions"""
    service = AutomationEngine(db)
    return service.generate_faq_suggestions(days)


# AI Safety Routes
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


@router.get("/safety/status")
async def get_safety_status():
    """Get safety status"""
    service = AISafetyService()
    return service.get_safety_status()