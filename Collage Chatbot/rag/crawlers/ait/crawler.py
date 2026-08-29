import re
import hashlib
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup
from backend.app.config import settings

class AITWebsiteCrawler:
    """Production-grade respectful crawler for Ahmedabad Institute of Technology (aitindia.in)"""
    ALLOWED_DOMAINS = ["aitindia.in", "www.aitindia.in", "localhost", "127.0.0.1"]

    def __init__(
        self,
        base_url: Optional[str] = None,
        max_pages: Optional[int] = None,
        user_agent: Optional[str] = None
    ):
        configured_url = base_url or getattr(settings, "AIT_OFFICIAL_BASE_URL", "https://www.aitindia.in")
        self.base_url = configured_url.rstrip("/")
        self.max_pages = max_pages or getattr(settings, "CRAWLER_MAX_PAGES", 50)
        self.headers = {"User-Agent": user_agent or getattr(settings, "CRAWLER_USER_AGENT", "AIT-Assistant-Bot/1.0 (+https://www.aitindia.in)")}
        self.max_response_bytes = 10 * 1024 * 1024  # 10MB limit

    def is_allowed_url(self, url: str) -> bool:
        """Validates that URL belongs strictly to allowed AIT domains (SSRF prevention)"""
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False
            hostname = (parsed.hostname or "").lower()
            return any(hostname == allowed or hostname.endswith("." + allowed) for allowed in self.ALLOWED_DOMAINS)
        except Exception:
            return False

    def determine_category(self, url: str, title: str) -> str:
        """Categorizes page content based on URL and title semantics"""
        u = url.lower()
        t = title.lower()
        if "course" in u or "curriculum" in u or "syllabus" in u or "bca" in u or "btech" in u:
            return "Courses & Academics"
        elif "fee" in u or "admission" in u:
            return "Admissions & Fees"
        elif "facilit" in u or "library" in u or "lab" in u or "campus" in u:
            return "Campus & Facilities"
        elif "event" in u or "techfest" in u or "ignite" in u:
            return "Events & Student Life"
        elif "notice" in u or "circular" in u:
            return "Notices & Announcements"
        elif "faculty" in u or "department" in u or "staff" in u:
            return "Faculty & Departments"
        elif "contact" in u or "about" in u:
            return "Institutional Overview"
        return "General Information"

    async def crawl_page(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch and extract clean content, metadata, images, and documents from an AIT page"""
        if not self.is_allowed_url(url):
            print(f"[AIT Crawler] Disallowed domain / potential SSRF blocked: {url}")
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers=self.headers) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    return None

                # Check max payload size
                if len(response.content) > self.max_response_bytes:
                    print(f"[AIT Crawler] Page exceeds size limit: {url}")
                    return None

                html = response.text
                soup = BeautifulSoup(html, "html.parser")

                # Extract canonical URL if present
                canonical_tag = soup.find("link", rel="canonical")
                canonical_url = urljoin(url, canonical_tag.get("href", "")) if canonical_tag else url

                # Remove non-content elements
                for tag in soup(["script", "style", "nav", "footer", "noscript", "svg", "iframe"]):
                    tag.decompose()

                title = soup.title.string.strip() if soup.title and soup.title.string else "AIT Official Page"
                category = self.determine_category(url, title)

                # Extract main content
                text = " ".join(soup.stripped_strings)
                text = re.sub(r'\s+', ' ', text).strip()
                content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

                # Extract images with captions & alt text
                images = []
                for img in soup.find_all("img"):
                    src = img.get("src")
                    if src:
                        full_img_url = urljoin(url, src)
                        alt = (img.get("alt") or "").strip()
                        title_attr = (img.get("title") or "").strip()
                        parent_caption = ""
                        if img.find_parent("figure"):
                            cap = img.find_parent("figure").find("figcaption")
                            if cap:
                                parent_caption = cap.get_text().strip()

                        caption = parent_caption or title_attr or alt
                        if full_img_url.startswith("http") and not any(skip in full_img_url.lower() for skip in ["icon", "logo", "spacer", "pixel", "blank"]):
                            images.append({
                                "image_url": full_img_url,
                                "source_url": url,
                                "source_page": title,
                                "caption": caption or title,
                                "alt_text": alt or title,
                                "category": category,
                                "content_hash": hashlib.sha256(full_img_url.encode("utf-8")).hexdigest()[:16]
                            })

                # Extract PDF/document links
                documents = []
                for a_tag in soup.find_all("a", href=True):
                    href = a_tag["href"]
                    if href.lower().endswith((".pdf", ".docx", ".xlsx")):
                        doc_url = urljoin(url, href)
                        if self.is_allowed_url(doc_url):
                            doc_title = a_tag.get_text().strip() or title
                            documents.append({
                                "url": doc_url,
                                "title": doc_title,
                                "type": href.split(".")[-1].upper()
                            })

                return {
                    "source_url": url,
                    "canonical_url": canonical_url,
                    "title": title,
                    "category": category,
                    "raw_html": html[:50000],
                    "clean_text": text,
                    "content_hash": content_hash,
                    "images": images,
                    "documents": documents,
                    "is_official": True
                }
        except Exception as e:
            print(f"[AIT Crawler] Error crawling {url}: {e}")
            return None

    def get_seed_urls(self) -> List[str]:
        """Core official AIT web pages for primary index"""
        return [
            f"{self.base_url}",
            f"{self.base_url}/about-us",
            f"{self.base_url}/courses/bca",
            f"{self.base_url}/courses/btech-computer-engineering",
            f"{self.base_url}/facilities/smart-classrooms",
            f"{self.base_url}/facilities/central-library",
            f"{self.base_url}/facilities/computer-labs",
            f"{self.base_url}/events",
            f"{self.base_url}/notices",
            f"{self.base_url}/admissions",
            f"{self.base_url}/contact-us",
        ]
