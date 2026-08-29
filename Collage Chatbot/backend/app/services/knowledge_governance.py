"""
Knowledge Governance Service
Complete lifecycle management for knowledge: review, approval, publishing, versioning
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from backend.app.models.entities import (
    KnowledgeSource, KnowledgeDocument, KnowledgeChunk, 
    User, AuditLog
)
import logging

logger = logging.getLogger(__name__)


class KnowledgeGovernanceService:
    """Knowledge governance service for content lifecycle management"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def submit_for_review(self, document_id: int, submitted_by: int) -> Dict[str, Any]:
        """Submit knowledge document for review"""
        document = self.db.query(KnowledgeDocument).filter(
            KnowledgeDocument.id == document_id
        ).first()
        
        if not document:
            return {'success': False, 'error': 'Document not found'}
        
        document.status = "REVIEW"
        document.submitted_for_review_at = datetime.utcnow()
        document.submitted_by = submitted_by
        
        self.db.commit()
        
        # Create audit log
        self._create_audit_log(
            action="SUBMIT_FOR_REVIEW",
            entity_type="KnowledgeDocument",
            entity_id=document_id,
            user_id=submitted_by,
            details={"previous_status": "INGESTED"}
        )
        
        return {'success': True, 'message': 'Document submitted for review'}
    
    def review_document(self, document_id: int, reviewer_id: int, 
                      approved: bool, feedback: str = None) -> Dict[str, Any]:
        """Review a knowledge document"""
        document = self.db.query(KnowledgeDocument).filter(
            KnowledgeDocument.id == document_id
        ).first()
        
        if not document:
            return {'success': False, 'error': 'Document not found'}
        
        if document.status != "REVIEW":
            return {'success': False, 'error': 'Document not in review status'}
        
        document.reviewed_by = reviewer_id
        document.reviewed_at = datetime.utcnow()
        document.review_feedback = feedback
        
        if approved:
            document.status = "APPROVED"
            document.approved_by = reviewer_id
            document.approved_at = datetime.utcnow()
        else:
            document.status = "REJECTED"
            document.rejected_by = reviewer_id
            document.rejected_at = datetime.utcnow()
        
        self.db.commit()
        
        # Create audit log
        self._create_audit_log(
            action="DOCUMENT_REVIEW",
            entity_type="KnowledgeDocument",
            entity_id=document_id,
            user_id=reviewer_id,
            details={
                "approved": approved,
                "feedback": feedback
            }
        )
        
        return {'success': True, 'message': f'Document {"approved" if approved else "rejected"}'}
    
    def publish_document(self, document_id: int, published_by: int) -> Dict[str, Any]:
        """Publish an approved document"""
        document = self.db.query(KnowledgeDocument).filter(
            KnowledgeDocument.id == document_id
        ).first()
        
        if not document:
            return {'success': False, 'error': 'Document not found'}
        
        if document.status != "APPROVED":
            return {'success': False, 'error': 'Document must be approved before publishing'}
        
        document.status = "PUBLISHED"
        document.published_by = published_by
        document.published_at = datetime.utcnow()
        
        self.db.commit()
        
        # Create audit log
        self._create_audit_log(
            action="PUBLISH_DOCUMENT",
            entity_type="KnowledgeDocument",
            entity_id=document_id,
            user_id=published_by,
            details={}
        )
        
        return {'success': True, 'message': 'Document published successfully'}
    
    def archive_document(self, document_id: int, archived_by: int, 
                       reason: str = None) -> Dict[str, Any]:
        """Archive a document"""
        document = self.db.query(KnowledgeDocument).filter(
            KnowledgeDocument.id == document_id
        ).first()
        
        if not document:
            return {'success': False, 'error': 'Document not found'}
        
        document.status = "ARCHIVED"
        document.archived_by = archived_by
        document.archived_at = datetime.utcnow()
        document.archive_reason = reason
        
        self.db.commit()
        
        # Create audit log
        self._create_audit_log(
            action="ARCHIVE_DOCUMENT",
            entity_type="KnowledgeDocument",
            entity_id=document_id,
            user_id=archived_by,
            details={"reason": reason}
        )
        
        return {'success': True, 'message': 'Document archived successfully'}
    
    def rollback_document(self, document_id: int, target_version: int, 
                        rolled_back_by: int) -> Dict[str, Any]:
        """Rollback document to a previous version"""
        current_document = self.db.query(KnowledgeDocument).filter(
            KnowledgeDocument.id == document_id
        ).first()
        
        if not current_document:
            return {'success': False, 'error': 'Document not found'}
        
        # Find target version
        target_document = self.db.query(KnowledgeDocument).filter(
            KnowledgeDocument.source_id == current_document.source_id,
            KnowledgeDocument.version == target_version
        ).first()
        
        if not target_document:
            return {'success': False, 'error': 'Target version not found'}
        
        # Archive current version
        current_document.status = "SUPERSEDED"
        current_document.superseded_at = datetime.utcnow()
        
        # Reactivate target version
        target_document.status = "PUBLISHED"
        target_document.published_at = datetime.utcnow()
        
        self.db.commit()
        
        # Create audit log
        self._create_audit_log(
            action="ROLLBACK_DOCUMENT",
            entity_type="KnowledgeDocument",
            entity_id=document_id,
            user_id=rolled_back_by,
            details={"target_version": target_version}
        )
        
        return {'success': True, 'message': f'Document rolled back to version {target_version}'}
    
    def get_review_queue(self) -> List[Dict[str, Any]]:
        """Get documents pending review"""
        documents = self.db.query(KnowledgeDocument).filter(
            KnowledgeDocument.status == "REVIEW"
        ).order_by(KnowledgeDocument.submitted_for_review_at.asc()).all()
        
        return [
            {
                'id': doc.id,
                'title': doc.title,
                'submitted_by': doc.submitted_by,
                'submitted_at': doc.submitted_for_review_at.isoformat() if doc.submitted_for_review_at else None,
                'source_id': doc.source_id
            }
            for doc in documents
        ]
    
    def get_document_history(self, document_id: int) -> List[Dict[str, Any]]:
        """Get version history of a document"""
        document = self.db.query(KnowledgeDocument).filter(
            KnowledgeDocument.id == document_id
        ).first()
        
        if not document:
            return []
        
        # Get all versions for this source
        versions = self.db.query(KnowledgeDocument).filter(
            KnowledgeDocument.source_id == document.source_id
        ).order_by(KnowledgeDocument.version.desc()).all()
        
        return [
            {
                'id': ver.id,
                'version': ver.version,
                'status': ver.status,
                'created_at': ver.created_at.isoformat() if ver.created_at else None,
                'published_at': ver.published_at.isoformat() if ver.published_at else None,
                'archived_at': ver.archived_at.isoformat() if ver.archived_at else None
            }
            for ver in versions
        ]
    
    def check_stale_knowledge(self, days_threshold: int = 30) -> List[Dict[str, Any]]:
        """Check for stale knowledge that needs updating"""
        threshold_date = datetime.utcnow() - timedelta(days=days_threshold)
        
        stale_documents = self.db.query(KnowledgeDocument).filter(
            KnowledgeDocument.status == "PUBLISHED",
            KnowledgeDocument.published_at < threshold_date
        ).all()
        
        return [
            {
                'id': doc.id,
                'title': doc.title,
                'published_at': doc.published_at.isoformat() if doc.published_at else None,
                'days_since_publish': (datetime.utcnow() - doc.published_at).days if doc.published_at else 0
            }
            for doc in stale_documents
        ]
    
    def _create_audit_log(self, action: str, entity_type: str, entity_id: int,
                        user_id: int, details: Dict[str, Any] = None):
        """Create an audit log entry"""
        audit_log = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            details=details or {},
            timestamp=datetime.utcnow()
        )
        
        self.db.add(audit_log)
        self.db.commit()