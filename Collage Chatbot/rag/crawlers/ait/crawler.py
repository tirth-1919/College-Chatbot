import re
import hashlib
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup

class AITWebsiteCrawler:
    """Production-grade respectful crawler for Ahmedabad Institute of Technology (aitindia.in)"""
    def __init__(
        self,
        base_url: str = "https://www.aitindia.in",
        max_pages: int = 50,
        user_agent: str = "AIT-Assistant-Bot/1.0 (+https://www.aitindia.in)"
    ):
        self.base_url = base_url.rstrip("/")
        self.max_pages = max_pages
        self.headers = {"User-Agent": user_agent}

    async def crawl_page(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch and extract clean content, metadata, and images from an AIT page"""
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers=self.headers) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    return None

                html = response.text
                soup = BeautifulSoup(html, "html.parser")

                # Remove non-content tags
                for tag in soup(["script", "style", "nav", "footer", "noscript", "svg"]):
                    tag.decompose()

                title = soup.title.string.strip() if soup.title else "AIT Official Page"
                
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
                        alt = img.get("alt", "").strip()
                        title_attr = img.get("title", "").strip()
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
                                "content_hash": hashlib.sha256(full_img_url.encode("utf-8")).hexdigest()[:16]
                            })

                return {
                    "source_url": url,
                    "title": title,
                    "raw_html": html[:50000],
                    "clean_text": text,
                    "content_hash": content_hash,
                    "images": images
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
