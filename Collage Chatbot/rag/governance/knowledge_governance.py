from datetime import datetime, UTC, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend.app.models.entities import KnowledgeSource, KnowledgeDocument, AuditLog
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KnowledgeGovernanceManager:
    """
    Manages knowledge governance including freshness tracking, verification, and expiry.
    Ensures authoritative information remains current and stale data is identified.
    """
    
    # Default freshness thresholds (in days)
    DEFAULT_FRESHNESS_THRESHOLDS = {
        'WEBSITE_CRAWL': 7,      # Website content: 7 days
        'OFFICIAL_DOCUMENT': 30,  # Official documents: 30 days
        'ADMIN_ENTRY': 90,       # Admin entries: 90 days
        'FAQ': 60               # FAQs: 60 days
    }
    
    def __init__(self, db: Session):
        self.db = db
        self.freshness_thresholds = self.DEFAULT_FRESHNESS_THRESHOLDS.copy()
    
    def update_knowledge_freshness(
        self, 
        source_id: str, 
        verifier: Optional[str] = None,
        new_expiry_days: Optional[int] = None
    ) -> KnowledgeSource:
        """
        Update knowledge freshness information.
        
        Args:
            source_id: Knowledge source ID
            verifier: Person/system verifying the knowledge
            new_expiry_days: New expiry period in days
            
        Returns:
            Updated KnowledgeSource
        """
        source = self.db.query(KnowledgeSource).filter(
            KnowledgeSource.id == source_id
        ).first()
        
        if not source:
            raise ValueError(f"Knowledge source {source_id} not found")
        
        # Update verification information
        source.last_verified_at = datetime.now(UTC)
        source.verified_by = verifier or "SYSTEM"
        source.updated_at = datetime.now(UTC)
        
        # Update expiry if specified
        if new_expiry_days:
            source.expiry_date = (datetime.now(UTC) + timedelta(days=new_expiry_days)).replace(tzinfo=None)
        
        # Update staleness status
        source.is_stale = self._check_staleness(source)
        
        # Log governance action
        audit = AuditLog(
            actor_id=verifier,
            actor_role="ADMIN" if verifier else "SYSTEM",
            action="UPDATE_KNOWLEDGE_FRESHNESS",
            target_entity="KnowledgeSource",
            details={
                "source_id": source_id,
                "source_url": source.source_url,
                "verifier": verifier,
                "last_verified_at": source.last_verified_at.isoformat(),
                "expiry_date": source.expiry_date.isoformat() if source.expiry_date else None,
                "is_stale": source.is_stale
            }
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(source)
        
        logger.info(f"[KnowledgeGovernance] Updated freshness for source {source_id}")
        return source
    
    def verify_knowledge(
        self,
        source_id: str,
        verifier: str,
        verification_notes: Optional[str] = None,
        extend_expiry_days: Optional[int] = None
    ) -> KnowledgeSource:
        """
        Mark knowledge as verified by an authority.
        
        Args:
            source_id: Knowledge source ID
            verifier: Person performing verification
            verification_notes: Notes about verification
            extend_expiry_days: Extend expiry by this many days
            
        Returns:
            Updated KnowledgeSource
        """
        source = self.db.query(KnowledgeSource).filter(
            KnowledgeSource.id == source_id
        ).first()
        
        if not source:
            raise ValueError(f"Knowledge source {source_id} not found")
        
        # Update verification status
        source.verification_status = "VERIFIED"
        source.last_verified_at = datetime.now(UTC)
        source.verified_by = verifier
        source.updated_at = datetime.now(UTC)
        
        # Extend expiry if specified
        if extend_expiry_days:
            current_expiry = source.expiry_date or datetime.now(UTC)
            source.expiry_date = current_expiry + timedelta(days=extend_expiry_days)
        
        # Update staleness
        source.is_stale = False
        
        # Log verification
        audit = AuditLog(
            actor_id=verifier,
            actor_role="ADMIN",
            action="VERIFY_KNOWLEDGE",
            target_entity="KnowledgeSource",
            details={
                "source_id": source_id,
                "source_url": source.source_url,
                "verifier": verifier,
                "verification_notes": verification_notes,
                "extended_expiry_days": extend_expiry_days,
                "new_expiry_date": source.expiry_date.isoformat() if source.expiry_date else None
            }
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(source)
        
        logger.info(f"[KnowledgeGovernance] Verified knowledge source {source_id} by {verifier}")
        return source
    
    def mark_knowledge_stale(
        self,
        source_id: str,
        reason: str,
        mark_by: str
    ) -> KnowledgeSource:
        """
        Mark knowledge as stale with reason.
        
        Args:
            source_id: Knowledge source ID
            reason: Reason for marking as stale
            mark_by: Person marking as stale
            
        Returns:
            Updated KnowledgeSource
        """
        source = self.db.query(KnowledgeSource).filter(
            KnowledgeSource.id == source_id
        ).first()
        
        if not source:
            raise ValueError(f"Knowledge source {source_id} not found")
        
        source.is_stale = True
        source.updated_at = datetime.now(UTC)
        
        # Optionally mark as not AI visible
        source.ai_visible = False
        
        # Log staleness marking
        audit = AuditLog(
            actor_id=mark_by,
            actor_role="ADMIN",
            action="MARK_KNOWLEDGE_STALE",
            target_entity="KnowledgeSource",
            details={
                "source_id": source_id,
                "source_url": source.source_url,
                "reason": reason,
                "marked_by": mark_by,
                "ai_visible": source.ai_visible
            }
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(source)
        
        logger.warning(f"[KnowledgeGovernance] Marked knowledge {source_id} as stale: {reason}")
        return source
    
    def get_stale_knowledge(self, source_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all stale knowledge entries.
        
        Args:
            source_type: Filter by source type (optional)
            
        Returns:
            List of stale knowledge entries
        """
        query = self.db.query(KnowledgeSource).filter(
            KnowledgeSource.is_stale == True
        )
        
        if source_type:
            query = query.filter(KnowledgeSource.source_type == source_type)
        
        stale_sources = query.all()
        
        return [
            {
                "id": source.id,
                "source_url": source.source_url,
                "source_type": source.source_type,
                "title": source.title,
                "last_verified_at": source.last_verified_at.isoformat() if source.last_verified_at else None,
                "expiry_date": source.expiry_date.isoformat() if source.expiry_date else None,
                "verified_by": source.verified_by,
                "verification_status": source.verification_status,
                "ai_visible": source.ai_visible,
                "days_since_expiry": self._days_since_expiry(source)
            }
            for source in stale_sources
        ]
    
    def get_knowledge_requiring_verification(self, days_threshold: int = 7) -> List[Dict[str, Any]]:
        """
        Get knowledge that requires re-verification.
        
        Args:
            days_threshold: Days after which verification is required
            
        Returns:
            List of knowledge requiring verification
        """
        threshold_date = datetime.now(UTC) - timedelta(days=days_threshold)
        
        sources = self.db.query(KnowledgeSource).filter(
            KnowledgeSource.last_verified_at < threshold_date,
            KnowledgeSource.is_stale == False,
            KnowledgeSource.ai_visible == True
        ).all()
        
        return [
            {
                "id": source.id,
                "source_url": source.source_url,
                "source_type": source.source_type,
                "title": source.title,
                "last_verified_at": source.last_verified_at.isoformat() if source.last_verified_at else None,
                "days_since_verification": (datetime.now(UTC) - source.last_verified_at.replace(tzinfo=UTC)).days if source.last_verified_at else None,
                "verified_by": source.verified_by,
                "verification_status": source.verification_status,
                "priority": self._calculate_verification_priority(source)
            }
            for source in sources
        ]
    
    def check_all_knowledge_freshness(self) -> Dict[str, Any]:
        """
        Check freshness of all knowledge and update staleness status.
        
        Returns:
            Summary of freshness check results
        """
        sources = self.db.query(KnowledgeSource).filter(
            KnowledgeSource.ai_visible == True
        ).all()
        
        stale_count = 0
        fresh_count = 0
        requires_verification = 0
        
        for source in sources:
            was_stale = source.is_stale
            source.is_stale = self._check_staleness(source)
            
            if source.is_stale and not was_stale:
                stale_count += 1
                logger.warning(f"[KnowledgeGovernance] Source {source.id} became stale")
            elif not source.is_stale:
                fresh_count += 1
                
                # Check if verification is needed
                if self._requires_verification(source):
                    requires_verification += 1
        
        self.db.commit()
        
        return {
            "total_sources": len(sources),
            "fresh_count": fresh_count,
            "stale_count": stale_count,
            "requires_verification": requires_verification,
            "checked_at": datetime.now(UTC).isoformat()
        }
    
    def _check_staleness(self, source: KnowledgeSource) -> bool:
        """Check if a knowledge source is stale"""
        # Check explicit staleness flag
        if source.is_stale:
            return True
        
        # Check expiry date
        if source.expiry_date:
            expiry_date = source.expiry_date.replace(tzinfo=UTC) if source.expiry_date.tzinfo is None else source.expiry_date
            if datetime.now(UTC) > expiry_date:
                return True
        
        # Check based on source type and last verification
        threshold_days = self.freshness_thresholds.get(
            source.source_type, 
            self.DEFAULT_FRESHNESS_THRESHOLDS['WEBSITE_CRAWL']
        )
        
        if source.last_verified_at:
            verified_at = source.last_verified_at.replace(tzinfo=UTC) if source.last_verified_at.tzinfo is None else source.last_verified_at
            days_since_verification = (datetime.now(UTC) - verified_at).days
            if days_since_verification > threshold_days:
                return True
        
        return False
    
    def _requires_verification(self, source: KnowledgeSource) -> bool:
        """Check if source requires verification"""
        threshold_days = self.freshness_thresholds.get(
            source.source_type,
            self.DEFAULT_FRESHNESS_THRESHOLDS['WEBSITE_CRAWL']
        )
        
        if source.last_verified_at:
            verified_at = source.last_verified_at.replace(tzinfo=UTC) if source.last_verified_at.tzinfo is None else source.last_verified_at
            days_since_verification = (datetime.now(UTC) - verified_at).days
            return days_since_verification > (threshold_days * 0.7)  # 70% of threshold
        
        return True
    
    def _days_since_expiry(self, source: KnowledgeSource) -> Optional[int]:
        """Calculate days since expiry"""
        if not source.expiry_date:
            return None
        
        expiry_date = source.expiry_date.replace(tzinfo=UTC) if source.expiry_date.tzinfo is None else source.expiry_date
        if datetime.now(UTC) > expiry_date:
            return (datetime.now(UTC) - expiry_date).days
        
        return None
    
    def _calculate_verification_priority(self, source: KnowledgeSource) -> str:
        """Calculate verification priority based on staleness and importance"""
        if source.is_stale:
            return "URGENT"
        
        if not source.last_verified_at:
            return "HIGH"
        
        threshold_days = self.freshness_thresholds.get(
            source.source_type,
            self.DEFAULT_FRESHNESS_THRESHOLDS['WEBSITE_CRAWL']
        )
        
        if source.last_verified_at:
            verified_at = source.last_verified_at.replace(tzinfo=UTC) if source.last_verified_at.tzinfo is None else source.last_verified_at
            days_since = (datetime.now(UTC) - verified_at).days
            if days_since > threshold_days:
                return "URGENT"
            elif days_since > (threshold_days * 0.8):
                return "HIGH"
            elif days_since > (threshold_days * 0.5):
                return "MEDIUM"
        
        return "LOW"
    
    def get_knowledge_version_history(self, source_id: str) -> List[Dict[str, Any]]:
        """
        Get version/audit history for a knowledge source.
        
        Args:
            source_id: Knowledge source ID
            
        Returns:
            List of audit history entries
        """
        audits = self.db.query(AuditLog).filter(
            AuditLog.target_entity == "KnowledgeSource",
            AuditLog.details['source_id'].astext == source_id
        ).order_by(AuditLog.timestamp.desc()).all()
        
        return [
            {
                "timestamp": audit.timestamp.isoformat(),
                "actor": audit.actor_id,
                "action": audit.action,
                "details": audit.details
            }
            for audit in audits
        ]
    
    def set_freshness_threshold(self, source_type: str, days: int):
        """
        Set custom freshness threshold for a source type.
        
        Args:
            source_type: Type of knowledge source
            days: Threshold in days
        """
        self.freshness_thresholds[source_type] = days
        logger.info(f"[KnowledgeGovernance] Set freshness threshold for {source_type} to {days} days")
    
    def get_governance_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive governance report.
        
        Returns:
            Governance status report
        """
        total_sources = self.db.query(KnowledgeSource).count()
        stale_sources = self.db.query(KnowledgeSource).filter(
            KnowledgeSource.is_stale == True
        ).count()
        
        verified_sources = self.db.query(KnowledgeSource).filter(
            KnowledgeSource.verification_status == "VERIFIED"
        ).count()
        
        ai_visible_sources = self.db.query(KnowledgeSource).filter(
            KnowledgeSource.ai_visible == True
        ).count()
        
        # Get breakdown by source type
        source_type_breakdown = {}
        for source_type in self.DEFAULT_FRESHNESS_THRESHOLDS.keys():
            count = self.db.query(KnowledgeSource).filter(
                KnowledgeSource.source_type == source_type
            ).count()
            source_type_breakdown[source_type] = count
        
        return {
            "total_sources": total_sources,
            "stale_sources": stale_sources,
            "fresh_sources": total_sources - stale_sources,
            "verified_sources": verified_sources,
            "unverified_sources": total_sources - verified_sources,
            "ai_visible_sources": ai_visible_sources,
            "ai_hidden_sources": total_sources - ai_visible_sources,
            "source_type_breakdown": source_type_breakdown,
            "freshness_thresholds": self.freshness_thresholds,
            "report_generated_at": datetime.now(UTC).isoformat()
        }