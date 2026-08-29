import threading
import time
import asyncio
from typing import Optional, Callable
from datetime import datetime, UTC
from sqlalchemy.orm import Session
from rag.sync.website_change_detector import WebsiteChangeDetector
from rag.crawlers.ait.crawler import AITWebsiteCrawler

class WebsiteSyncScheduler:
    """
    Enhanced scheduler for periodic website synchronization with change detection.
    Uses background thread for scheduled tasks and incremental sync.
    """

    def __init__(self, sync_interval_hours: int = 24, enable_change_detection: bool = True):
        self.sync_interval_hours = sync_interval_hours
        self.sync_interval_seconds = sync_interval_hours * 3600
        self.is_running = False
        self.sync_thread: Optional[threading.Thread] = None
        self.last_sync_time: Optional[datetime] = None
        self.sync_callback: Optional[Callable] = None
        self.db_session: Optional[Session] = None
        self.enable_change_detection = enable_change_detection
        self.change_detector: Optional[WebsiteChangeDetector] = None
        self.crawler = AITWebsiteCrawler()
        self.max_retries = 3
        self.retry_delay = 60  # seconds

    def set_sync_callback(self, callback: Callable):
        """Set the callback function to execute on sync"""
        self.sync_callback = callback

    def set_db_session(self, db: Session):
        """Set the database session for sync operations"""
        self.db_session = db
        if self.enable_change_detection and db:
            self.change_detector = WebsiteChangeDetector(db, self.crawler)

    def start(self):
        """Start the scheduler background thread"""
        if self.is_running:
            print("[WebsiteSyncScheduler] Already running")
            return

        self.is_running = True
        self.sync_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.sync_thread.start()
        print(f"[WebsiteSyncScheduler] Started with interval: {self.sync_interval_hours} hours")
        print(f"[WebsiteSyncScheduler] Change detection: {'ENABLED' if self.enable_change_detection else 'DISABLED'}")

    def stop(self):
        """Stop the scheduler background thread"""
        self.is_running = False
        if self.sync_thread:
            self.sync_thread.join(timeout=5)
        print("[WebsiteSyncScheduler] Stopped")

    def _run_scheduler(self):
        """Main scheduler loop"""
        while self.is_running:
            try:
                # Execute sync & checks
                self._execute_sync()
                self._check_auto_retrain_threshold()

                # Wait for next interval
                time.sleep(self.sync_interval_seconds)

            except Exception as e:
                print(f"[WebsiteSyncScheduler] Error in scheduler loop: {e}")
                time.sleep(60)  # Wait 1 minute before retry

    def _check_auto_retrain_threshold(self):
        """Checks if enough approved training examples exist to trigger automated model retraining"""
        if not self.db_session:
            return
        try:
            from backend.app.config import settings
            if not getattr(settings, "INTENT_AUTO_TRAIN_ENABLED", True):
                return
            threshold = getattr(settings, "INTENT_RETRAIN_THRESHOLD", 10)
            from backend.app.models.entities import TrainingExample
            approved_count = self.db_session.query(TrainingExample).filter(TrainingExample.status == "APPROVED").count()
            if approved_count >= threshold:
                print(f"[WebsiteSyncScheduler] Approved training examples threshold reached ({approved_count} >= {threshold}). Running controlled retraining...")
                from ml.intent.intent_classifier import IntentClassifier
                classifier = IntentClassifier(use_ml=True)
                res = classifier.retrain_from_database(
                    self.db_session,
                    min_accuracy=getattr(settings, "INTENT_MIN_ACCURACY", 0.85),
                    min_f1=getattr(settings, "INTENT_MIN_F1", 0.85)
                )
                print(f"[WebsiteSyncScheduler] Retraining result: {res.get('message')}")
        except Exception as e:
            print(f"[WebsiteSyncScheduler] Error during auto-retrain threshold check: {e}")


    def _execute_sync(self):
        """Execute the sync with change detection and retry logic"""
        if not self.db_session:
            print("[WebsiteSyncScheduler] No database session available")
            return

        retry_count = 0
        last_error = None

        while retry_count < self.max_retries:
            try:
                print(f"[WebsiteSyncScheduler] Executing sync at {datetime.now(UTC)} (attempt {retry_count + 1})")

                if self.enable_change_detection and self.change_detector:
                    # Use change detection for incremental sync
                    self._execute_incremental_sync()
                elif self.sync_callback:
                    # Use legacy callback
                    self.sync_callback(self.db_session)
                else:
                    print("[WebsiteSyncScheduler] No sync method available")
                    return

                self.last_sync_time = datetime.now(UTC)
                print(f"[WebsiteSyncScheduler] Sync completed at {self.last_sync_time}")
                return

            except Exception as e:
                last_error = e
                retry_count += 1
                print(f"[WebsiteSyncScheduler] Sync attempt {retry_count} failed: {e}")

                if retry_count < self.max_retries:
                    print(f"[WebsiteSyncScheduler] Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                    # Exponential backoff
                    self.retry_delay = min(self.retry_delay * 2, 300)  # Max 5 minutes

        # All retries failed
        print(f"[WebsiteSyncScheduler] Sync failed after {self.max_retries} attempts. Last error: {last_error}")

    def _execute_incremental_sync(self):
        """Execute incremental sync with change detection"""
        if not self.change_detector:
            print("[WebsiteSyncScheduler] Change detector not initialized")
            return

        # Get seed URLs from crawler
        urls = self.crawler.get_seed_urls()

        # Run async change detection in the thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            report = loop.run_until_complete(
                self.change_detector.detect_changes(urls)
            )

            print(f"[WebsiteSyncScheduler] Incremental sync report:")
            print(f"  Total pages: {report.total_pages_processed}")
            print(f"  New pages: {report.new_pages}")
            print(f"  Modified pages: {report.modified_pages}")
            print(f"  Unchanged pages: {report.unchanged_pages}")
            print(f"  Deleted pages: {report.deleted_pages}")
            print(f"  Failed pages: {report.failed_pages}")
            print(f"  Duration: {report.sync_duration_seconds:.2f}s")
            print(f"  Status: {report.status}")

            # Call legacy callback if provided for indexing
            if self.sync_callback:
                self.sync_callback(self.db_session)

        finally:
            loop.close()

    def trigger_sync_now(self):
        """Trigger an immediate sync (manual trigger)"""
        print("[WebsiteSyncScheduler] Manual sync triggered")
        self._execute_sync()

    def get_status(self) -> dict:
        """Get scheduler status"""
        status = {
            "is_running": self.is_running,
            "sync_interval_hours": self.sync_interval_hours,
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "next_sync_in_seconds": self.sync_interval_seconds if self.is_running else None,
            "change_detection_enabled": self.enable_change_detection
        }

        # Add freshness information if available
        if self.change_detector:
            stale_pages = self.change_detector.get_stale_pages()
            status["stale_pages_count"] = len(stale_pages)

        return status

    def is_sync_due(self) -> bool:
        """Check if a sync is due"""
        if not self.last_sync_time:
            return True

        time_since_last = (datetime.now(UTC) - self.last_sync_time).total_seconds()
        return time_since_last >= self.sync_interval_seconds

    def get_freshness_report(self) -> dict:
        """Get freshness report for all tracked pages"""
        if not self.change_detector:
            return {"error": "Change detector not initialized"}

        stale_pages = self.change_detector.get_stale_pages()

        return {
            "total_stale_pages": len(stale_pages),
            "stale_pages": stale_pages,
            "freshness_threshold_days": 7
        }


# Global scheduler instance
_global_scheduler: Optional[WebsiteSyncScheduler] = None

def get_scheduler() -> WebsiteSyncScheduler:
    """Get or create the global scheduler instance"""
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = WebsiteSyncScheduler(sync_interval_hours=24)
    return _global_scheduler

def start_scheduler(db: Session, sync_callback: Callable):
    """Start the global scheduler with database session and callback"""
    scheduler = get_scheduler()
    scheduler.set_db_session(db)
    scheduler.set_sync_callback(sync_callback)
    scheduler.start()
    return scheduler

def stop_scheduler():
    """Stop the global scheduler"""
    global _global_scheduler
    if _global_scheduler:
        _global_scheduler.stop()
        _global_scheduler = None
