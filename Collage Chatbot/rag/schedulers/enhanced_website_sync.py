"""
Enhanced Website Sync with Incremental Updates and Versioning
Improved website crawling with change detection, versioning, and efficient updates
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from sqlalchemy.orm import Session
from rag.crawlers.ait.crawler import AITWebsiteCrawler
from backend.app.models.entities import KnowledgeSource, KnowledgeDocument
import logging

logger = logging.getLogger(__name__)


class EnhancedWebsiteSync:
    """Enhanced website synchronization with incremental updates"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.crawler = AITWebsiteCrawler()
        self.page_hashes = {}  # Track page content hashes
        self.page_versions = {}  # Track page versions
        self.removed_pages = set()  # Track removed pages
    
    def sync_website(self, base_url: str = "https://www.aitindia.in") -> Dict[str, any]:
        """
        Perform incremental website sync with change detection
        """
        sync_result = {
            'started_at': datetime.utcnow().isoformat(),
            'pages_processed': 0,
            'pages_added': 0,
            'pages_updated': 0,
            'pages_removed': 0,
            'pages_unchanged': 0,
            'errors': [],
            'completed_at': None
        }
        
        try:
            # Discover pages
            discovered_pages = self.crawler.discover_pages(base_url)
            current_page_urls = set(discovered_pages.keys())
            
            # Load previous page hashes
            previous_hashes = self._load_page_hashes()
            previous_urls = set(previous_hashes.keys())
            
            # Detect new pages
            new_pages = current_page_urls - previous_urls
            # Detect removed pages
            removed_pages = previous_urls - current_page_urls
            # Detect potentially changed pages
            potentially_changed = current_page_urls & previous_urls
            
            # Process new pages
            for page_url in new_pages:
                try:
                    self._process_new_page(page_url, discovered_pages[page_url])
                    sync_result['pages_added'] += 1
                    sync_result['pages_processed'] += 1
                except Exception as e:
                    sync_result['errors'].append(f"Error processing new page {page_url}: {str(e)}")
                    logger.error(f"Error processing new page {page_url}: {e}")
            
            # Process potentially changed pages
            for page_url in potentially_changed:
                try:
                    page_content = discovered_pages[page_url]
                    current_hash = self._calculate_hash(page_content)
                    
                    if current_hash != previous_hashes[page_url]:
                        self._process_updated_page(page_url, page_content, current_hash)
                        sync_result['pages_updated'] += 1
                    else:
                        sync_result['pages_unchanged'] += 1
                    
                    sync_result['pages_processed'] += 1
                except Exception as e:
                    sync_result['errors'].append(f"Error processing page {page_url}: {str(e)}")
                    logger.error(f"Error processing page {page_url}: {e}")
            
            # Handle removed pages
            for page_url in removed_pages:
                try:
                    self._handle_removed_page(page_url)
                    sync_result['pages_removed'] += 1
                except Exception as e:
                    sync_result['errors'].append(f"Error handling removed page {page_url}: {str(e)}")
                    logger.error(f"Error handling removed page {page_url}: {e}")
            
            # Save current hashes
            self._save_page_hashes({url: self._calculate_hash(content) for url, content in discovered_pages.items()})
            
            # Update sync metadata
            self._update_sync_metadata(sync_result)
            
        except Exception as e:
            sync_result['errors'].append(f"Sync failed: {str(e)}")
            logger.error(f"Website sync failed: {e}")
        
        sync_result['completed_at'] = datetime.utcnow().isoformat()
        return sync_result
    
    def _process_new_page(self, page_url: str, page_content: str):
        """Process a newly discovered page"""
        logger.info(f"Processing new page: {page_url}")
        
        # Create knowledge source
        source = KnowledgeSource(
            source_url=page_url,
            source_type="WEBSITE",
            authority_level="OFFICIAL",
            freshness_score=1.0,
            last_synced_at=datetime.utcnow(),
            sync_status="ACTIVE"
        )
        
        self.db.add(source)
        self.db.flush()
        
        # Parse and create document
        document = KnowledgeDocument(
            source_id=source.id,
            title=self._extract_title(page_content),
            content=page_content,
            document_type="WEB_PAGE",
            status="PUBLISHED",
            version=1,
            language="en",
            published_at=datetime.utcnow()
        )
        
        self.db.add(document)
        self.db.commit()
    
    def _process_updated_page(self, page_url: str, page_content: str, new_hash: str):
        """Process an updated page with versioning"""
        logger.info(f"Processing updated page: {page_url}")
        
        # Find existing source
        source = self.db.query(KnowledgeSource).filter(
            KnowledgeSource.source_url == page_url
        ).first()
        
        if not source:
            # Source was deleted, recreate it
            self._process_new_page(page_url, page_content)
            return
        
        # Update source
        source.last_synced_at = datetime.utcnow()
        source.freshness_score = 1.0
        
        # Create new version of document
        latest_version = self.db.query(KnowledgeDocument).filter(
            KnowledgeDocument.source_id == source.id
        ).order_by(KnowledgeDocument.version.desc()).first()
        
        new_version = (latest_version.version + 1) if latest_version else 1
        
        # Archive old version
        if latest_version:
            latest_version.status = "SUPERSEDED"
            latest_version.superseded_at = datetime.utcnow()
        
        # Create new document version
        document = KnowledgeDocument(
            source_id=source.id,
            title=self._extract_title(page_content),
            content=page_content,
            document_type="WEB_PAGE",
            status="PUBLISHED",
            version=new_version,
            language="en",
            published_at=datetime.utcnow()
        )
        
        self.db.add(document)
        self.db.commit()
    
    def _handle_removed_page(self, page_url: str):
        """Handle a page that no longer exists"""
        logger.info(f"Handling removed page: {page_url}")
        
        # Find and update source
        source = self.db.query(KnowledgeSource).filter(
            KnowledgeSource.source_url == page_url
        ).first()
        
        if source:
            source.sync_status = "REMOVED"
            source.last_synced_at = datetime.utcnow()
            
            # Archive associated documents
            documents = self.db.query(KnowledgeDocument).filter(
                KnowledgeDocument.source_id == source.id
            ).all()
            
            for doc in documents:
                doc.status = "ARCHIVED"
                doc.archived_at = datetime.utcnow()
            
            self.db.commit()
    
    def _calculate_hash(self, content: str) -> str:
        """Calculate SHA-256 hash of content"""
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _extract_title(self, content: str) -> str:
        """Extract title from HTML content"""
        # Simple title extraction
        if "<title>" in content and "</title>" in content:
            start = content.find("<title>") + 7
            end = content.find("</title>")
            return content[start:end].strip()
        return "Untitled Page"
    
    def _load_page_hashes(self) -> Dict[str, str]:
        """Load previous page hashes from database"""
        # In production, store in a dedicated table
        # For now, load from metadata
        sources = self.db.query(KnowledgeSource).filter(
            KnowledgeSource.source_type == "WEBSITE"
        ).all()
        
        hashes = {}
        for source in sources:
            latest_doc = self.db.query(KnowledgeDocument).filter(
                KnowledgeDocument.source_id == source.id
            ).order_by(KnowledgeDocument.version.desc()).first()
            
            if latest_doc:
                hashes[source.source_url] = self._calculate_hash(latest_doc.content)
        
        return hashes
    
    def _save_page_hashes(self, hashes: Dict[str, str]):
        """Save current page hashes"""
        # In production, save to dedicated table
        # For now, this is handled by the document versions
        pass
    
    def _update_sync_metadata(self, sync_result: Dict[str, any]):
        """Update sync metadata"""
        # Store sync results for monitoring
        logger.info(f"Sync completed: {sync_result}")
    
    def get_sync_status(self) -> Dict[str, any]:
        """Get current sync status"""
        total_sources = self.db.query(KnowledgeSource).filter(
            KnowledgeSource.source_type == "WEBSITE"
        ).count()
        
        active_sources = self.db.query(KnowledgeSource).filter(
            KnowledgeSource.source_type == "WEBSITE",
            KnowledgeSource.sync_status == "ACTIVE"
        ).count()
        
        last_sync = self.db.query(KnowledgeSource).filter(
            KnowledgeSource.source_type == "WEBSITE"
        ).order_by(KnowledgeSource.last_synced_at.desc()).first()
        
        return {
            'total_pages': total_sources,
            'active_pages': active_sources,
            'last_sync': last_sync.last_synced_at.isoformat() if last_sync else None,
            'stale_pages': total_sources - active_sources
        }