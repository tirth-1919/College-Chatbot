import hashlib
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, UTC, timedelta
from sqlalchemy.orm import Session
from backend.app.models.entities import WebsiteSyncState, WebsiteContentVersion, WebsiteSyncReport
from rag.crawlers.ait.crawler import AITWebsiteCrawler


class WebsiteChangeDetector:
    """
    Production-grade website change detection system.
    Detects content changes, manages incremental sync, and tracks freshness.
    """

    def __init__(self, db: Session, crawler: Optional[AITWebsiteCrawler] = None):
        self.db = db
        self.crawler = crawler or AITWebsiteCrawler()
        self.sync_report = {
            "new_pages": [],
            "modified_pages": [],
            "unchanged_pages": [],
            "deleted_pages": [],
            "failed_pages": []
        }

    async def detect_changes(self, urls: List[str]) -> WebsiteSyncReport:
        """
        Detect changes for a list of URLs.

        Args:
            urls: List of URLs to check for changes

        Returns:
            WebsiteSyncReport with detailed change information
        """
        start_time = datetime.now(UTC)
        report = WebsiteSyncReport(
            sync_timestamp=start_time,
            total_pages_processed=len(urls),
            status="IN_PROGRESS"
        )

        try:
            for url in urls:
                change_result = await self._check_single_url(url)
                self._update_sync_report(change_result)

            # Detect deleted pages
            await self._detect_deleted_pages(urls)

            # Finalize report
            report.new_pages = len(self.sync_report["new_pages"])
            report.modified_pages = len(self.sync_report["modified_pages"])
            report.unchanged_pages = len(self.sync_report["unchanged_pages"])
            report.deleted_pages = len(self.sync_report["deleted_pages"])
            report.failed_pages = len(self.sync_report["failed_pages"])
            report.sync_duration_seconds = (datetime.now(UTC) - start_time).total_seconds()
            report.status = "COMPLETED"
            report.sync_summary = self._generate_sync_summary()
            report.error_details = self.sync_report["failed_pages"]

            self.db.add(report)
            self.db.commit()

        except Exception as e:
            report.status = "FAILED"
            report.error_details = [{"error": str(e)}]
            self.db.add(report)
            self.db.commit()
            raise

        return report

    async def _check_single_url(self, url: str) -> Dict[str, Any]:
        """
        Check a single URL for changes.

        Returns:
            Dictionary with change detection result
        """
        result = {
            "url": url,
            "change_type": "UNKNOWN",
            "previous_hash": None,
            "new_hash": None,
            "content": None,
            "error": None
        }

        try:
            # Fetch current content
            crawled_data = await self.crawler.crawl_page(url)

            if not crawled_data:
                result["change_type"] = "FAILED"
                result["error"] = "Failed to crawl page"
                return result

            current_hash = crawled_data["content_hash"]
            result["new_hash"] = current_hash
            result["content"] = crawled_data

            # Check existing state
            existing_state = self.db.query(WebsiteSyncState).filter(
                WebsiteSyncState.source_url == url,
                WebsiteSyncState.is_active == True
            ).first()

            if not existing_state:
                # New page
                result["change_type"] = "NEW"
                self._create_new_page_state(url, crawled_data, current_hash)
                self.sync_report["new_pages"].append(url)
            elif existing_state.content_hash != current_hash:
                # Modified page
                result["change_type"] = "MODIFIED"
                result["previous_hash"] = existing_state.content_hash
                self._update_modified_page(existing_state, crawled_data, current_hash)
                self.sync_report["modified_pages"].append(url)
            else:
                # Unchanged page
                result["change_type"] = "UNCHANGED"
                result["previous_hash"] = existing_state.content_hash
                self._update_unchanged_page(existing_state)
                self.sync_report["unchanged_pages"].append(url)

        except Exception as e:
            result["change_type"] = "FAILED"
            result["error"] = str(e)
            self.sync_report["failed_pages"].append({
                "url": url,
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            })

        return result

    def _create_new_page_state(self, url: str, crawled_data: Dict[str, Any], content_hash: str):
        """Create state for a new page"""
        state = WebsiteSyncState(
            source_url=url,
            content_hash=content_hash,
            first_discovered_at=datetime.now(UTC),
            last_fetched_at=datetime.now(UTC),
            last_changed_at=datetime.now(UTC),
            indexed_at=datetime.now(UTC),
            freshness_status="FRESH",
            sync_status="SYNCED",
            current_version=1,
            page_title=crawled_data.get("title", ""),
            change_count=1
        )
        self.db.add(state)
        self.db.flush()

        # Create content version
        version = WebsiteContentVersion(
            source_url=url,
            version_number=1,
            content_hash=content_hash,
            change_type="INITIAL",
            raw_html=crawled_data.get("raw_html", ""),
            clean_text=crawled_data.get("clean_text", ""),
            page_title=crawed_data.get("title", ""),
            change_timestamp=datetime.now(UTC),
            indexed_at=datetime.now(UTC),
            is_current=True
        )
        self.db.add(version)

    def _update_modified_page(self, existing_state: WebsiteSyncState, crawled_data: Dict[str, Any], new_hash: str):
        """Update state for a modified page"""
        # Archive old version
        old_version = WebsiteContentVersion(
            source_url=existing_state.source_url,
            version_number=existing_state.current_version,
            content_hash=existing_state.content_hash,
            change_type="MODIFIED",
            previous_content_hash=existing_state.content_hash,
            raw_html=crawled_data.get("raw_html", ""),
            clean_text=crawed_data.get("clean_text", ""),
            page_title=crawled_data.get("title", ""),
            change_timestamp=existing_state.last_changed_at,
            is_current=False
        )
        self.db.add(old_version)

        # Update current state
        existing_state.content_hash = new_hash
        existing_state.last_fetched_at = datetime.now(UTC)
        existing_state.last_changed_at = datetime.now(UTC)
        existing_state.indexed_at = datetime.now(UTC)
        existing_state.freshness_status = "FRESH"
        existing_state.sync_status = "SYNCED"
        existing_state.previous_version = existing_state.current_version
        existing_state.current_version += 1
        existing_state.page_title = crawled_data.get("title", "")
        existing_state.change_count += 1

        # Create new version
        new_version = WebsiteContentVersion(
            source_url=existing_state.source_url,
            version_number=existing_state.current_version,
            content_hash=new_hash,
            change_type="MODIFIED",
            previous_content_hash=existing_state.content_hash,
            raw_html=crawled_data.get("raw_html", ""),
            clean_text=crawled_data.get("clean_text", ""),
            page_title=crawled_data.get("title", ""),
            change_summary="Content updated from previous version",
            change_timestamp=datetime.now(UTC),
            indexed_at=datetime.now(UTC),
            is_current=True
        )
        self.db.add(new_version)

    def _update_unchanged_page(self, existing_state: WebsiteSyncState):
        """Update state for an unchanged page"""
        existing_state.last_fetched_at = datetime.now(UTC)
        existing_state.sync_status = "SYNCED"

        # Check if page is stale (not updated in 7 days)
        if existing_state.last_changed_at:
            days_since_change = (datetime.now(UTC) - existing_state.last_changed_at).days
            if days_since_change > 7:
                existing_state.freshness_status = "STALE"

    async def _detect_deleted_pages(self, current_urls: List[str]):
        """Detect pages that have been deleted"""
        active_states = self.db.query(WebsiteSyncState).filter(
            WebsiteSyncState.is_active == True
        ).all()

        for state in active_states:
            if state.source_url not in current_urls:
                # Page has been deleted
                state.is_active = False
                state.sync_status = "DELETED"
                state.freshness_status = "STALE"

                # Create deletion version record
                deletion_version = WebsiteContentVersion(
                    source_url=state.source_url,
                    version_number=state.current_version + 1,
                    content_hash=state.content_hash,
                    change_type="DELETED",
                    change_summary="Page no longer available",
                    change_timestamp=datetime.now(UTC),
                    is_current=False
                )
                self.db.add(deletion_version)

                self.sync_report["deleted_pages"].append(state.source_url)

    def _update_sync_report(self, result: Dict[str, Any]):
        """Update sync report with individual result"""
        # This is handled in the individual methods
        pass

    def _generate_sync_summary(self) -> str:
        """Generate human-readable sync summary"""
        total = (len(self.sync_report["new_pages"]) +
                len(self.sync_report["modified_pages"]) +
                len(self.sync_report["unchanged_pages"]) +
                len(self.sync_report["deleted_pages"]) +
                len(self.sync_report["failed_pages"]))

        summary = f"Sync completed: {total} pages processed. "
        summary += f"New: {len(self.sync_report['new_pages'])}, "
        summary += f"Modified: {len(self.sync_report['modified_pages'])}, "
        summary += f"Unchanged: {len(self.sync_report['unchanged_pages'])}, "
        summary += f"Deleted: {len(self.sync_report['deleted_pages'])}, "
        summary += f"Failed: {len(self.sync_report['failed_pages'])}"

        return summary

    def get_freshness_status(self, url: str) -> Optional[Dict[str, Any]]:
        """Get freshness status for a specific URL"""
        state = self.db.query(WebsiteSyncState).filter(
            WebsiteSyncState.source_url == url,
            WebsiteSyncState.is_active == True
        ).first()

        if not state:
            return None

        return {
            "url": state.source_url,
            "freshness_status": state.freshness_status,
            "last_fetched_at": state.last_fetched_at.isoformat() if state.last_fetched_at else None,
            "last_changed_at": state.last_changed_at.isoformat() if state.last_changed_at else None,
            "current_version": state.current_version,
            "change_count": state.change_count,
            "is_stale": state.freshness_status == "STALE"
        }

    def get_stale_pages(self, days_threshold: int = 7) -> List[Dict[str, Any]]:
        """Get all pages that are considered stale"""
        threshold_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days_threshold)

        stale_states = self.db.query(WebsiteSyncState).filter(
            WebsiteSyncState.is_active == True,
            WebsiteSyncState.last_changed_at < threshold_date
        ).all()

        return [
            {
                "url": state.source_url,
                "last_changed_at": state.last_changed_at.isoformat() if state.last_changed_at else None,
                "days_since_change": (datetime.now(UTC).replace(tzinfo=None) - (state.last_changed_at.replace(tzinfo=None) if state.last_changed_at else datetime.now())).days if state.last_changed_at else None,
                "current_version": state.current_version
            }
            for state in stale_states
        ]

    def get_page_version_history(self, url: str) -> List[Dict[str, Any]]:
        """Get version history for a specific page"""
        versions = self.db.query(WebsiteContentVersion).filter(
            WebsiteContentVersion.source_url == url
        ).order_by(WebsiteContentVersion.version_number).all()

        return [
            {
                "version": version.version_number,
                "content_hash": version.content_hash,
                "change_type": version.change_type,
                "change_timestamp": version.change_timestamp.isoformat() if version.change_timestamp else None,
                "is_current": version.is_current,
                "page_title": version.page_title
            }
            for version in versions
        ]