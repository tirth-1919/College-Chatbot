"""
Phase 3 API Routes
Background Jobs, Deep Research, Memory Controls, Data Analysis
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from backend.app.database import get_db
from backend.app.security.auth import get_current_user
from backend.app.models.entities import User, BackgroundJob, UserMemory
from backend.app.services.background_job_service import BackgroundJobService, UserMemoryService

router = APIRouter()


# ----------------- Background Job Routes -----------------

class JobCreateRequest(BaseModel):
    job_type: str = Field(..., description="DEEP_RESEARCH, DATA_ANALYSIS, FILE_PROCESSING")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=5, ge=1, le=10)


class JobResponse(BaseModel):
    id: str
    job_type: str
    status: str
    progress: int
    current_step: Optional[str]
    created_at: str
    result: Optional[Dict[str, Any]]
    error_message: Optional[str]


@router.post("/jobs", response_model=JobResponse)
async def create_job(
    request: JobCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new background job"""
    job_service = BackgroundJobService(db)
    
    job = job_service.create_job(
        job_type=request.job_type,
        owner_id=current_user.id,
        owner_role=current_user.roles[0].name if current_user.roles else "STUDENT",
        parameters=request.parameters,
        priority=request.priority
    )
    
    # Start job execution in background
    background_tasks.add_task(job_service.execute_job, job.id)
    
    return JobResponse(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        progress=job.progress,
        current_step=job.current_step,
        created_at=job.created_at.isoformat(),
        result=job.result,
        error_message=job.error_message
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get job status with ownership verification"""
    job_service = BackgroundJobService(db)
    
    user_role = current_user.roles[0].name if current_user.roles else "STUDENT"
    job = job_service.get_job(job_id, current_user.id, user_role)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or access denied")
    
    return JobResponse(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        progress=job.progress,
        current_step=job.current_step,
        created_at=job.created_at.isoformat(),
        result=job.result,
        error_message=job.error_message
    )


@router.get("/jobs", response_model=List[JobResponse])
async def list_jobs(
    status: Optional[str] = None,
    job_type: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's jobs with security filtering"""
    job_service = BackgroundJobService(db)
    
    user_role = current_user.roles[0].name if current_user.roles else "STUDENT"
    jobs = job_service.list_user_jobs(current_user.id, user_role, status, job_type, limit)
    
    return [
        JobResponse(
            id=job.id,
            job_type=job.job_type,
            status=job.status,
            progress=job.progress,
            current_step=job.current_step,
            created_at=job.created_at.isoformat(),
            result=job.result,
            error_message=job.error_message
        )
        for job in jobs
    ]


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel a running job with ownership verification"""
    job_service = BackgroundJobService(db)
    
    user_role = current_user.roles[0].name if current_user.roles else "STUDENT"
    success = job_service.cancel_job(job_id, current_user.id, user_role)
    
    if not success:
        raise HTTPException(status_code=400, detail="Job not found or cannot be cancelled")
    
    return {"success": True, "message": "Job cancellation requested"}


# ----------------- Deep Research Routes -----------------

class DeepResearchRequest(BaseModel):
    question: str = Field(..., min_length=10, max_length=500)
    max_sources: int = Field(default=10, ge=1, le=20)


@router.post("/research/deep")
async def start_deep_research(
    request: DeepResearchRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start deep research as background job"""
    job_service = BackgroundJobService(db)
    
    job = job_service.create_job(
        job_type="DEEP_RESEARCH",
        owner_id=current_user.id,
        owner_role=current_user.roles[0].name if current_user.roles else "STUDENT",
        parameters={
            "question": request.question,
            "max_sources": request.max_sources
        },
        priority=7  # Higher priority for research
    )
    
    # Start research in background
    background_tasks.add_task(job_service.execute_job, job.id)
    
    return {
        "job_id": job.id,
        "status": "QUEUED",
        "message": "Deep research started",
        "estimated_time": "2-5 minutes"
    }


@router.get("/research/{job_id}")
async def get_research_results(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get deep research results"""
    from backend.app.models.entities import DeepResearchReport
    
    job_service = BackgroundJobService(db)
    user_role = current_user.roles[0].name if current_user.roles else "STUDENT"
    
    job = job_service.get_job(job_id, current_user.id, user_role)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != "COMPLETED":
        return {
            "job_id": job_id,
            "status": job.status,
            "progress": job.progress,
            "current_step": job.current_step
        }
    
    # Get research report
    report = db.query(DeepResearchReport).filter(DeepResearchReport.job_id == job_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Research report not found")
    
    return {
        "job_id": job_id,
        "status": job.status,
        "research_question": report.research_question,
        "summary": report.summary,
        "detailed_report": report.detailed_report,
        "key_findings": report.key_findings,
        "total_sources": report.total_sources,
        "authoritative_sources": report.authoritative_sources,
        "confidence_level": report.confidence_level,
        "suggested_followups": report.suggested_followups
    }


# ----------------- Memory Control Routes -----------------

class MemoryUpdateRequest(BaseModel):
    preferred_language: Optional[str] = None
    preferred_answer_style: Optional[str] = None
    study_preferences: Optional[Dict[str, Any]] = None


@router.get("/memory")
async def get_user_memory(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user memory with privacy controls"""
    memory_service = UserMemoryService(db)
    memory = memory_service.get_user_memory(current_user.id)
    
    if not memory:
        return {
            "memory_enabled": False,
            "message": "No memory data found"
        }
    
    return {
        "memory_enabled": True,
        "data": memory
    }


@router.put("/memory")
async def update_user_memory(
    request: MemoryUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user memory with conflict resolution"""
    memory_service = UserMemoryService(db)
    
    memory = memory_service.update_user_memory(
        user_id=current_user.id,
        preferred_language=request.preferred_language,
        preferred_answer_style=request.preferred_answer_style,
        study_preferences=request.study_preferences
    )
    
    return {
        "success": True,
        "message": "Memory updated successfully",
        "memory_id": memory.id
    }


@router.delete("/memory")
async def delete_user_memory(
    specific_key: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete user memory (all or specific key)"""
    memory_service = UserMemoryService(db)
    
    success = memory_service.delete_user_memory(current_user.id, specific_key)
    
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    return {
        "success": True,
        "message": f"Memory {'partially' if specific_key else 'completely'} deleted"
    }


@router.put("/memory/enabled")
async def set_memory_enabled(
    enabled: bool,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enable or disable memory for user"""
    memory_service = UserMemoryService(db)
    
    success = memory_service.set_memory_enabled(current_user.id, enabled)
    
    return {
        "success": success,
        "memory_enabled": enabled,
        "message": f"Memory {'enabled' if enabled else 'disabled'}"
    }


# ----------------- Data Analysis Routes -----------------

class DataAnalysisRequest(BaseModel):
    file_id: str = Field(..., description="Attachment ID to analyze")
    operations: List[str] = Field(default_factory=list)


@router.post("/analysis/data")
async def start_data_analysis(
    request: DataAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start data analysis as background job"""
    job_service = BackgroundJobService(db)
    
    job = job_service.create_job(
        job_type="DATA_ANALYSIS",
        owner_id=current_user.id,
        owner_role=current_user.roles[0].name if current_user.roles else "STUDENT",
        parameters={
            "file_id": request.file_id,
            "operations": request.operations
        },
        priority=6
    )
    
    # Start analysis in background
    background_tasks.add_task(job_service.execute_job, job.id)
    
    return {
        "job_id": job.id,
        "status": "QUEUED",
        "message": "Data analysis started"
    }


@router.get("/analysis/{job_id}")
async def get_analysis_results(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get data analysis results"""
    from backend.app.models.entities import DataAnalysisJob
    
    job_service = BackgroundJobService(db)
    user_role = current_user.roles[0].name if current_user.roles else "STUDENT"
    
    job = job_service.get_job(job_id, current_user.id, user_role)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != "COMPLETED":
        return {
            "job_id": job_id,
            "status": job.status,
            "progress": job.progress,
            "current_step": job.current_step
        }
    
    # Get analysis results
    analysis = db.query(DataAnalysisJob).filter(DataAnalysisJob.job_id == job_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis results not found")
    
    return {
        "job_id": job_id,
        "status": job.status,
        "file_name": analysis.file_name,
        "row_count": analysis.row_count,
        "column_count": analysis.column_count,
        "schema_detected": analysis.schema_detected,
        "statistics": analysis.statistics,
        "operations_performed": analysis.operations_performed,
        "charts_generated": analysis.charts_generated,
        "data_quality_score": analysis.data_quality_score
    }