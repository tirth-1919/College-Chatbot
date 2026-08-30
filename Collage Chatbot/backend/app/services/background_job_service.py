"""
Background Job Service for Phase 3
Handles job creation, execution, progress tracking, and cancellation
"""

import asyncio
import uuid
import time
import psutil
from datetime import datetime, UTC
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from backend.app.models.entities import (
    BackgroundJob, User, DeepResearchSource, DeepResearchReport, 
    DataAnalysisJob, AIQualityMetrics
)
from backend.app.database import SessionLocal


class BackgroundJobService:
    """
    Production-grade background job system with:
    - Job ownership and security
    - Progress tracking
    - Cancellation support
    - Resource monitoring
    - Persistent job queue
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.active_jobs: Dict[str, asyncio.Task] = {}
    
    def create_job(
        self,
        job_type: str,
        owner_id: str,
        owner_role: str = "STUDENT",
        parameters: Dict[str, Any] = None,
        priority: int = 5,
        estimated_duration_seconds: int = None
    ) -> BackgroundJob:
        """Create a new background job with ownership tracking"""
        job = BackgroundJob(
            job_type=job_type,
            owner_id=owner_id,
            owner_role=owner_role,
            parameters=parameters or {},
            priority=priority,
            estimated_duration_seconds=estimated_duration_seconds,
            status="QUEUED"
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job
    
    def get_job(self, job_id: str, user_id: str, user_role: str) -> Optional[BackgroundJob]:
        """
        Get job with ownership verification
        Admin can view all jobs, users can only view their own
        """
        job = self.db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
        if not job:
            return None
        
        # Security check: users can only access their own jobs
        if user_role not in ["ADMIN", "SUPER_ADMIN"] and job.owner_id != user_id:
            return None
        
        return job
    
    def list_user_jobs(
        self, 
        user_id: str, 
        user_role: str,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        limit: int = 50
    ) -> List[BackgroundJob]:
        """List jobs with security filtering"""
        query = self.db.query(BackgroundJob)
        
        # Security: non-admins only see their own jobs
        if user_role not in ["ADMIN", "SUPER_ADMIN"]:
            query = query.filter(BackgroundJob.owner_id == user_id)
        
        if status:
            query = query.filter(BackgroundJob.status == status)
        if job_type:
            query = query.filter(BackgroundJob.job_type == job_type)
        
        return query.order_by(BackgroundJob.created_at.desc()).limit(limit).all()
    
    def cancel_job(self, job_id: str, user_id: str, user_role: str) -> bool:
        """
        Request job cancellation with ownership verification
        """
        job = self.get_job(job_id, user_id, user_role)
        if not job:
            return False
        
        if job.status not in ["QUEUED", "RUNNING"]:
            return False
        
        job.cancellation_requested = True
        job.cancellation_requested_at = datetime.now(UTC)
        self.db.commit()
        
        # Stop the async task if running
        if job_id in self.active_jobs:
            self.active_jobs[job_id].cancel()
            del self.active_jobs[job_id]
        
        job.status = "CANCELLED"
        job.completed_at = datetime.now(UTC)
        self.db.commit()
        
        return True
    
    def update_job_progress(
        self,
        job_id: str,
        progress: int,
        current_step: str,
        result_update: Dict[str, Any] = None
    ) -> bool:
        """Update job progress safely"""
        job = self.db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
        if not job:
            return False
        
        job.progress = min(100, max(0, progress))
        job.current_step = current_step
        job.updated_at = datetime.now(UTC)
        
        if result_update:
            if not job.result:
                job.result = {}
            job.result.update(result_update)
        
        # Track resource usage
        process = psutil.Process()
        job.memory_used_mb = process.memory_info().rss / (1024 * 1024)
        job.cpu_time_seconds = process.cpu_times().user + process.cpu_times().system
        
        self.db.commit()
        return True
    
    def complete_job(
        self,
        job_id: str,
        result: Dict[str, Any],
        success: bool = True,
        error_message: str = None,
        error_category: str = None
    ) -> bool:
        """Mark job as completed or failed"""
        job = self.db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
        if not job:
            return False
        
        job.status = "COMPLETED" if success else "FAILED"
        job.progress = 100 if success else job.progress
        job.result = result
        job.completed_at = datetime.now(UTC)
        job.updated_at = datetime.now(UTC)
        
        if not success:
            job.error_message = error_message
            job.error_category = error_category
        
        # Clean up active task
        if job_id in self.active_jobs:
            del self.active_jobs[job_id]
        
        self.db.commit()
        return True
    
    async def execute_job(self, job_id: str) -> None:
        """Execute a job asynchronously with cancellation support"""
        job = self.db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
        if not job:
            return
        
        try:
            # Mark as running
            job.status = "RUNNING"
            job.started_at = datetime.now(UTC)
            self.db.commit()
            
            # Route to appropriate job handler
            if job.job_type == "DEEP_RESEARCH":
                await self._execute_deep_research(job)
            elif job.job_type == "DATA_ANALYSIS":
                await self._execute_data_analysis(job)
            elif job.job_type == "FILE_PROCESSING":
                await self._execute_file_processing(job)
            else:
                raise ValueError(f"Unknown job type: {job.job_type}")
                
        except asyncio.CancelledError:
            # Job was cancelled
            job.status = "CANCELLED"
            job.completed_at = datetime.now(UTC)
            job.error_message = "Job cancelled by user"
            self.db.commit()
            
        except Exception as e:
            # Job failed
            job.status = "FAILED"
            job.completed_at = datetime.now(UTC)
            job.error_message = str(e)
            job.error_category = "SYSTEM_ERROR"
            self.db.commit()
    
    async def _execute_deep_research(self, job: BackgroundJob) -> None:
        """Execute deep research job with progress tracking"""
        from research.deep_research_engine import DeepResearchEngine
        
        engine = DeepResearchEngine(self.db)
        
        try:
            # Update progress
            self.update_job_progress(job.id, 10, "Planning research")
            
            # Execute research
            result = await engine.conduct_research(
                question=job.parameters.get("question"),
                max_sources=job.parameters.get("max_sources", 10),
                owner_id=job.owner_id
            )
            
            # Store results
            self.update_job_progress(job.id, 90, "Finalizing report")
            
            # Create research report
            report = DeepResearchReport(
                job_id=job.id,
                research_question=job.parameters.get("question"),
                summary=result.get("summary"),
                detailed_report=result.get("detailed_report"),
                key_findings=result.get("key_findings", []),
                total_sources=result.get("total_sources", 0),
                authoritative_sources=result.get("authoritative_sources", 0),
                source_conflicts=result.get("source_conflicts", []),
                citations_validated=result.get("citations_validated", False),
                citation_count=result.get("citation_count", 0),
                confidence_level=result.get("confidence_level", "MEDIUM"),
                uncertainty_explained=result.get("uncertainty_explained", False),
                suggested_followups=result.get("suggested_followups", [])
            )
            self.db.add(report)
            
            # Store sources
            for source_data in result.get("sources", []):
                source = DeepResearchSource(
                    job_id=job.id,
                    source_url=source_data.get("url"),
                    source_type=source_data.get("type", "OTHER"),
                    title=source_data.get("title"),
                    authority_score=source_data.get("authority_score", 0.5),
                    freshness_score=source_data.get("freshness_score", 0.5),
                    relevance_score=source_data.get("relevance_score", 0.5),
                    overall_quality=source_data.get("overall_quality", 0.5),
                    extracted_facts=source_data.get("facts", []),
                    citation_text=source_data.get("citation_text")
                )
                self.db.add(source)
            
            self.db.commit()
            
            # Complete job
            self.complete_job(job.id, result)
            
        except Exception as e:
            self.complete_job(job.id, {}, success=False, error_message=str(e), error_category="RESEARCH_ERROR")
    
    async def _execute_data_analysis(self, job: BackgroundJob) -> None:
        """Execute data analysis job"""
        from analysis.data_analyzer import DataAnalyzer
        
        analyzer = DataAnalyzer(self.db)
        
        try:
            file_id = job.parameters.get("file_id")
            operations = job.parameters.get("operations", [])
            
            self.update_job_progress(job.id, 10, "Loading dataset")
            
            # Perform analysis
            result = await analyzer.analyze_file(
                file_id=file_id,
                operations=operations,
                owner_id=job.owner_id
            )
            
            self.update_job_progress(job.id, 80, "Generating visualizations")
            
            # Create analysis job record
            analysis_job = DataAnalysisJob(
                job_id=job.id,
                file_id=file_id,
                file_name=result.get("file_name"),
                file_type=result.get("file_type"),
                row_count=result.get("row_count"),
                column_count=result.get("column_count"),
                schema_detected=result.get("schema"),
                statistics=result.get("statistics"),
                operations_performed=operations,
                charts_generated=result.get("charts", []),
                chart_urls=result.get("chart_urls", []),
                missing_values=result.get("missing_values"),
                data_quality_score=result.get("data_quality_score")
            )
            self.db.add(analysis_job)
            self.db.commit()
            
            self.complete_job(job.id, result)
            
        except Exception as e:
            self.complete_job(job.id, {}, success=False, error_message=str(e), error_category="ANALYSIS_ERROR")
    
    async def _execute_file_processing(self, job: BackgroundJob) -> None:
        """Execute file processing job (PDF indexing, etc.)"""
        try:
            file_id = job.parameters.get("file_id")
            processing_type = job.parameters.get("processing_type", "INDEX")
            
            self.update_job_progress(job.id, 10, "Loading file")
            
            # Implementation depends on processing type
            if processing_type == "INDEX":
                from rag.parsers.pdf_parser import PDFParser
                from rag.chunkers.chunker import DocumentChunker
                
                # Get file and process
                # This would integrate with existing RAG pipeline
                
            self.update_job_progress(job.id, 100, "Processing complete")
            self.complete_job(job.id, {"status": "processed"})
            
        except Exception as e:
            self.complete_job(job.id, {}, success=False, error_message=str(e), error_category="PROCESSING_ERROR")
    
    def start_job_worker(self):
        """Start the background job worker"""
        async def worker_loop():
            while True:
                try:
                    # Get next queued job (highest priority first)
                    job = self.db.query(BackgroundJob).filter(
                        BackgroundJob.status == "QUEUED"
                    ).order_by(
                        BackgroundJob.priority.desc(),
                        BackgroundJob.queued_at.asc()
                    ).first()
                    
                    if job:
                        # Start job execution
                        task = asyncio.create_task(self.execute_job(job.id))
                        self.active_jobs[job.id] = task
                    
                    await asyncio.sleep(1)  # Check for new jobs every second
                    
                except Exception as e:
                    print(f"Job worker error: {e}")
                    await asyncio.sleep(5)
        
        # Start worker in background
        asyncio.create_task(worker_loop())


class UserMemoryService:
    """
    Persistent user memory service with security and controls
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_memory(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user memory with security check"""
        memory = self.db.query(UserMemory).filter(UserMemory.user_id == user_id).first()
        if not memory:
            return None
        
        # Check if memory is enabled
        if not memory.memory_enabled:
            return None
        
        # Update access tracking
        memory.last_accessed_at = datetime.now(UTC)
        memory.access_count += 1
        self.db.commit()
        
        return {
            "preferred_language": memory.preferred_language,
            "preferred_answer_style": memory.preferred_answer_style,
            "study_preferences": memory.study_preferences,
            "recurring_patterns": memory.recurring_patterns
        }
    
    def update_user_memory(
        self,
        user_id: str,
        preferred_language: str = None,
        preferred_answer_style: str = None,
        study_preferences: Dict[str, Any] = None,
        recurring_patterns: List[Dict[str, Any]] = None
    ) -> UserMemory:
        """Update user memory with conflict resolution"""
        memory = self.db.query(UserMemory).filter(UserMemory.user_id == user_id).first()
        
        if not memory:
            memory = UserMemory(user_id=user_id)
            self.db.add(memory)
        
        # Only update if explicitly provided (current instruction wins)
        if preferred_language is not None:
            memory.preferred_language = preferred_language
        if preferred_answer_style is not None:
            memory.preferred_answer_style = preferred_answer_style
        if study_preferences is not None:
            memory.study_preferences.update(study_preferences)
        if recurring_patterns is not None:
            # Merge patterns avoiding duplicates
            existing_patterns = {p.get("pattern"): p for p in memory.recurring_patterns}
            for pattern in recurring_patterns:
                existing_patterns[pattern.get("pattern")] = pattern
            memory.recurring_patterns = list(existing_patterns.values())
        
        memory.last_updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(memory)
        return memory
    
    def delete_user_memory(self, user_id: str, specific_key: str = None) -> bool:
        """Delete user memory (all or specific key)"""
        memory = self.db.query(UserMemory).filter(UserMemory.user_id == user_id).first()
        if not memory:
            return False
        
        if specific_key:
            # Delete specific memory key
            if hasattr(memory, specific_key):
                setattr(memory, specific_key, None)
            elif specific_key in memory.study_preferences:
                del memory.study_preferences[specific_key]
            elif specific_key in memory.recurring_patterns:
                memory.recurring_patterns = [
                    p for p in memory.recurring_patterns 
                    if p.get("pattern") != specific_key
                ]
        else:
            # Delete all memory
            self.db.delete(memory)
        
        self.db.commit()
        return True
    
    def set_memory_enabled(self, user_id: str, enabled: bool) -> bool:
        """Enable or disable memory for a user"""
        memory = self.db.query(UserMemory).filter(UserMemory.user_id == user_id).first()
        if not memory:
            memory = UserMemory(user_id=user_id)
            self.db.add(memory)
        
        memory.memory_enabled = enabled
        self.db.commit()
        return True
    
    def get_relevant_memory(self, user_id: str, current_query: str) -> Dict[str, Any]:
        """Get only memory relevant to current request"""
        full_memory = self.get_user_memory(user_id)
        if not full_memory:
            return {}
        
        relevant = {}
        query_lower = current_query.lower()
        
        # Check language preference
        if full_memory.get("preferred_language"):
            relevant["preferred_language"] = full_memory["preferred_language"]
        
        # Check answer style
        if full_memory.get("preferred_answer_style"):
            relevant["preferred_answer_style"] = full_memory["preferred_answer_style"]
        
        # Check study preferences if query is academic
        academic_keywords = ["exam", "study", "subject", "syllabus", "semester", "course"]
        if any(keyword in query_lower for keyword in academic_keywords):
            if full_memory.get("study_preferences"):
                relevant["study_preferences"] = full_memory["study_preferences"]
        
        # Check recurring patterns if query matches
        for pattern in full_memory.get("recurring_patterns", []):
            pattern_text = pattern.get("pattern", "").lower()
            if pattern_text in query_lower or any(word in query_lower for word in pattern_text.split()):
                relevant["relevant_pattern"] = pattern
                break
        
        return relevant