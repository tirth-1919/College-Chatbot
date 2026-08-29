import hashlib
import logging
from datetime import datetime, UTC
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.app.models.entities import (
    KnowledgeSource, KnowledgeDocument, KnowledgeChunk,
    PendingKnowledgeUpdate, WebsiteSyncState, WebsiteContentVersion,
    WebsiteSyncReport, AuditLog, Facility, FacilityImage, Event, EventImage
)
from backend.app.config import settings
from rag.crawlers.ait.crawler import AITWebsiteCrawler
from rag.chunkers.chunker import DocumentChunker

logger = logging.getLogger(__name__)

class KnowledgeSyncService:
    """
    Automatic Official AIT Knowledge Synchronization & Governance Service.
    - Official AIT Crawler with domain whitelist & robots compliance
    - Deterministic SHA-256 change detection
    - Non-destructive pending knowledge versioning
    - Admin approval workflow integration
    - Incremental RAG re-indexing (Approved & Verified only)
    """
    def __init__(self, db: Session, crawler: Optional[AITWebsiteCrawler] = None):
        self.db = db
        self.crawler = crawler or AITWebsiteCrawler()
        self.chunker = DocumentChunker()
    async def sync_official_website(self, urls: Optional[List[str]] = None, actor_id: str = "SYSTEM") -> Dict[str, Any]:
        """
        Crawls configured AIT seed/target URLs, detects changes, and generates pending updates.
        """
        target_urls = urls or self.crawler.get_seed_urls()
        start_time = datetime.now(UTC)

        report = {
            "total_urls": len(target_urls),
            "new_pending": 0,
            "modified_pending": 0,
            "unchanged": 0,
            "failed": 0,
            "details": []
        }

        # Audit crawl start
        audit_start = AuditLog(
            actor_id=actor_id,
            actor_role="ADMIN" if actor_id != "SYSTEM" else "SYSTEM",
            action="KNOWLEDGE_CRAWL_STARTED",
            target_entity="KnowledgeSource",
            details={"url_count": len(target_urls), "timestamp": start_time.isoformat()}
        )
        self.db.add(audit_start)
        self.db.commit()

        for url in target_urls:
            try:
                page_data = await self.crawler.crawl_page(url)
                if not page_data:
                    report["failed"] += 1
                    report["details"].append({"url": url, "status": "FAILED", "reason": "Fetch error"})
                    continue

                res = self._process_crawled_page(page_data, actor_id=actor_id)
                status = res["status"]
                if status == "NEW_PENDING":
                    report["new_pending"] += 1
                elif status == "MODIFIED_PENDING":
                    report["modified_pending"] += 1
                elif status == "UNCHANGED":
                    report["unchanged"] += 1

                report["details"].append(res)
            except Exception as e:
                logger.error(f"[KnowledgeSync] Error processing {url}: {e}")
                report["failed"] += 1
                report["details"].append({"url": url, "status": "ERROR", "error": str(e)})

        # Audit crawl complete
        audit_end = AuditLog(
            actor_id=actor_id,
            actor_role="ADMIN" if actor_id != "SYSTEM" else "SYSTEM",
            action="KNOWLEDGE_CRAWL_COMPLETED",
            target_entity="KnowledgeSource",
            details={
                "duration_seconds": (datetime.now(UTC) - start_time).total_seconds(),
                "summary": report
            }
        )
        self.db.add(audit_end)
        self.db.commit()

        return report
    def _process_crawled_page(self, page_data: Dict[str, Any], actor_id: str = "SYSTEM") -> Dict[str, Any]:
        """
        Determines if page is NEW, CHANGED, or UNCHANGED using SHA-256 fingerprinting.
        Creates PENDING updates for admin review without overwriting verified live records.
        """
        url = page_data["source_url"]
        new_hash = page_data["content_hash"]
        title = page_data["title"]
        category = page_data.get("category", "General")
        clean_text = page_data["clean_text"]
        raw_html = page_data.get("raw_html", "")

        existing_source = self.db.query(KnowledgeSource).filter(KnowledgeSource.source_url == url).first()

        if not existing_source:
            # BRAND NEW SOURCE -> Create source record in PENDING status and create PendingKnowledgeUpdate
            source = KnowledgeSource(
                source_type="OFFICIAL_WEBSITE",
                source_url=url,
                canonical_url=page_data.get("canonical_url", url),
                source_page=title,
                title=title,
                category=category,
                content_hash=new_hash,
                raw_content=raw_html,
                clean_text=clean_text,
                is_official=True,
                is_verified=False,
                approval_status="PENDING",
                authority_score=1.0,
                last_crawled_at=datetime.now(UTC),
                last_changed_at=datetime.now(UTC)
            )
            self.db.add(source)
            self.db.flush()

            pending_update = PendingKnowledgeUpdate(
                source_id=source.id,
                source_url=url,
                title=title,
                category=category,
                source_type="OFFICIAL_WEBSITE",
                old_value=None,
                new_value=clean_text,
                clean_text=clean_text,
                change_type="NEW",
                change_summary=f"Discovered new official AIT page: {title}",
                content_hash=new_hash,
                approval_status="PENDING",
                update_metadata={"images_count": len(page_data.get("images", []))}
            )
            self.db.add(pending_update)
            self.db.commit()

            return {
                "url": url,
                "status": "NEW_PENDING",
                "source_id": source.id,
                "update_id": pending_update.id,
                "title": title
            }

        # Check if content has changed
        if existing_source.content_hash == new_hash:
            # UNCHANGED -> update last crawled timestamp only
            existing_source.last_crawled_at = datetime.now(UTC)
            self.db.commit()
            return {
                "url": url,
                "status": "UNCHANGED",
                "source_id": existing_source.id,
                "title": title
            }

        # CONTENT CHANGED -> Create PENDING update for admin review (do not overwrite verified data yet)
        existing_source.last_crawled_at = datetime.now(UTC)

        # Check if a pending update already exists for this hash
        existing_pending = self.db.query(PendingKnowledgeUpdate).filter(
            PendingKnowledgeUpdate.source_url == url,
            PendingKnowledgeUpdate.content_hash == new_hash,
            PendingKnowledgeUpdate.approval_status == "PENDING"
        ).first()

        if not existing_pending:
            pending_update = PendingKnowledgeUpdate(
                source_id=existing_source.id,
                source_url=url,
                title=title,
                category=category,
                source_type="OFFICIAL_WEBSITE",
                old_value=existing_source.clean_text or existing_source.raw_content,
                new_value=clean_text,
                clean_text=clean_text,
                change_type="MODIFIED",
                change_summary=f"Content updated on official page (Previous hash: {existing_source.content_hash[:8]} -> New hash: {new_hash[:8]})",
                content_hash=new_hash,
                approval_status="PENDING",
                update_metadata={"images": page_data.get("images", [])}
            )
            self.db.add(pending_update)
            self.db.commit()
            return {
                "url": url,
                "status": "MODIFIED_PENDING",
                "source_id": existing_source.id,
                "update_id": pending_update.id,
                "title": title
            }

        return {
            "url": url,
            "status": "ALREADY_PENDING",
            "source_id": existing_source.id,
            "title": title
        }
    def approve_pending_update(self, update_id: str, approved_by: str = "ADMIN") -> Dict[str, Any]:
        """
        Approves a pending knowledge item.
        - Sets update approval_status to 'APPROVED'
        - Updates the active verified record in KnowledgeSource
        - Triggers incremental RAG re-indexing for this source
        """
        pending = self.db.query(PendingKnowledgeUpdate).filter(PendingKnowledgeUpdate.id == update_id).first()
        if not pending:
            raise ValueError(f"Pending update {update_id} not found")

        pending.approval_status = "APPROVED"
        pending.reviewed_at = datetime.now(UTC)
        pending.reviewed_by = approved_by

        # Update or create the target KnowledgeSource
        source = pending.source
        if not source:
            source = self.db.query(KnowledgeSource).filter(KnowledgeSource.source_url == pending.source_url).first()

        if source:
            source.title = pending.title
            source.category = pending.category
            source.clean_text = pending.new_value
            source.content_hash = pending.content_hash
            source.is_verified = True
            source.approval_status = "APPROVED"
            source.verification_status = "VERIFIED"
            source.version = (source.version or 1) + 1
            source.last_verified_at = datetime.now(UTC)
            source.verified_by = approved_by
            source.last_changed_at = datetime.now(UTC)
        else:
            source = KnowledgeSource(
                source_type="OFFICIAL_WEBSITE",
                source_url=pending.source_url,
                title=pending.title,
                category=pending.category,
                clean_text=pending.new_value,
                content_hash=pending.content_hash,
                is_official=True,
                is_verified=True,
                approval_status="APPROVED",
                verification_status="VERIFIED",
                version=1,
                last_verified_at=datetime.now(UTC),
                verified_by=approved_by,
                last_changed_at=datetime.now(UTC)
            )
            self.db.add(source)
            self.db.flush()

        self.db.commit()

        # Incremental RAG re-index for this source
        rag_result = self.reindex_rag_for_source(source.id)

        # Audit Log
        audit = AuditLog(
            actor_id=approved_by,
            actor_role="ADMIN",
            action="APPROVE_KNOWLEDGE_UPDATE",
            target_entity="KnowledgeSource",
            details={
                "update_id": update_id,
                "source_id": source.id,
                "url": source.source_url,
                "new_version": source.version,
                "rag_chunks_indexed": rag_result.get("chunks_indexed", 0)
            }
        )
        self.db.add(audit)
        self.db.commit()

        return {
            "success": True,
            "message": f"Approved update for '{source.title}'. Active version updated to v{source.version}.",
            "source_id": source.id,
            "rag": rag_result
        }

    def reject_pending_update(self, update_id: str, rejected_by: str = "ADMIN", reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Rejects a pending knowledge item. Live active data remains untouched.
        """
        pending = self.db.query(PendingKnowledgeUpdate).filter(PendingKnowledgeUpdate.id == update_id).first()
        if not pending:
            raise ValueError(f"Pending update {update_id} not found")

        pending.approval_status = "REJECTED"
        pending.reviewed_at = datetime.now(UTC)
        pending.reviewed_by = rejected_by
        pending.rejection_reason = reason or "Rejected during admin review"
        self.db.commit()

        audit = AuditLog(
            actor_id=rejected_by,
            actor_role="ADMIN",
            action="REJECT_KNOWLEDGE_UPDATE",
            target_entity="PendingKnowledgeUpdate",
            details={"update_id": update_id, "url": pending.source_url, "reason": pending.rejection_reason}
        )
        self.db.add(audit)
        self.db.commit()

        return {"success": True, "message": f"Rejected update for '{pending.title}'. Active live knowledge was not modified."}

    def archive_knowledge_source(self, source_id: str, archived_by: str = "ADMIN") -> Dict[str, Any]:
        """
        Archives a knowledge source and de-indexes its chunks so it is excluded from RAG retrieval.
        """
        source = self.db.query(KnowledgeSource).filter(KnowledgeSource.id == source_id).first()
        if not source:
            raise ValueError(f"Knowledge source {source_id} not found")

        source.approval_status = "ARCHIVED"
        source.verification_status = "ARCHIVED"
        source.ai_visible = False
        self.db.commit()

        # Remove chunks associated with this source
        for doc in source.documents:
            self.db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == doc.id).delete()
            doc.is_active = False
        self.db.commit()

        audit = AuditLog(
            actor_id=archived_by,
            actor_role="ADMIN",
            action="ARCHIVE_KNOWLEDGE_SOURCE",
            target_entity="KnowledgeSource",
            details={"source_id": source_id, "url": source.source_url}
        )
        self.db.add(audit)
        self.db.commit()

        return {"success": True, "message": f"Archived knowledge source '{source.title}' and removed its chunks from RAG index."}
    def reindex_rag_for_source(self, source_id: str) -> Dict[str, Any]:
        """
        Incrementally re-indexes ONLY APPROVED & VERIFIED documents for a specific source.
        Replaces previous chunks cleanly to avoid duplicate chunks.
        """
        source = self.db.query(KnowledgeSource).filter(KnowledgeSource.id == source_id).first()
        if not source or source.approval_status != "APPROVED":
            return {"chunks_indexed": 0, "status": "SKIPPED_NOT_APPROVED"}

        clean_text = source.clean_text or source.raw_content or ""
        if not clean_text:
            return {"chunks_indexed": 0, "status": "EMPTY_CONTENT"}

        # Delete old document & chunks for this source to ensure zero duplicates
        old_docs = self.db.query(KnowledgeDocument).filter(KnowledgeDocument.source_id == source.id).all()
        for d in old_docs:
            self.db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == d.id).delete()
            self.db.delete(d)
        self.db.flush()

        # Create fresh active KnowledgeDocument
        doc = KnowledgeDocument(
            source_id=source.id,
            title=source.title,
            doc_type="HTML",
            raw_content=source.raw_content or clean_text,
            clean_text=clean_text,
            is_active=True,
            version=source.version or 1,
            file_hash=source.content_hash
        )
        self.db.add(doc)
        self.db.flush()

        # Chunk clean text
        chunk_dicts = self.chunker.chunk_text(clean_text, {
            "source_id": source.id,
            "source_url": source.source_url,
            "title": source.title,
            "category": source.category
        })

        created_chunks = 0
        for ch in chunk_dicts:
            k_chunk = KnowledgeChunk(
                document_id=doc.id,
                chunk_index=ch["chunk_index"],
                content=ch["content"],
                keywords=ch.get("keywords", ""),
                section_title=ch.get("section_title", source.title),
                verification_status="VERIFIED",
                source_type="OFFICIAL_WEBSITE",
                department=ch.get("department", "All"),
                academic_year=ch.get("academic_year", "2026-27"),
                freshness_score=1.0,
                chunk_metadata={"source_url": source.source_url, "title": source.title, "category": source.category}
            )
            self.db.add(k_chunk)
            created_chunks += 1

        self.db.commit()
        return {"chunks_indexed": created_chunks, "status": "INDEXED", "doc_id": doc.id}

    def reindex_all_approved_knowledge(self, actor_id: str = "SYSTEM") -> Dict[str, Any]:
        """
        Re-indexes all approved and verified knowledge sources across the entire database.
        """
        approved_sources = self.db.query(KnowledgeSource).filter(
            KnowledgeSource.approval_status == "APPROVED",
            KnowledgeSource.is_verified == True
        ).all()

        total_chunks = 0
        for src in approved_sources:
            res = self.reindex_rag_for_source(src.id)
            total_chunks += res.get("chunks_indexed", 0)

        audit = AuditLog(
            actor_id=actor_id,
            actor_role="ADMIN" if actor_id != "SYSTEM" else "SYSTEM",
            action="RAG_REINDEX_ALL",
            target_entity="KnowledgeChunk",
            details={"sources_indexed": len(approved_sources), "total_chunks": total_chunks}
        )
        self.db.add(audit)
        self.db.commit()

        return {
            "success": True,
            "sources_reindexed": len(approved_sources),
            "total_chunks_indexed": total_chunks
        }
