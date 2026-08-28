import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.models.entities import Facility, FacilityImage, Event, EventImage

class OfficialImageRetriever:
    """Retrieves verified real official AIT photographs with strict provenance guarantee"""
    
    @staticmethod
    def search_images(
        db: Session,
        query: str,
        year: Optional[int] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        lowered = query.lower()
        results = []

        # 1. Check for facility matches (Smart classroom, library, computer lab, sports ground, campus)
        facilities = db.query(Facility).filter(Facility.is_active == True).all()
        for fac in facilities:
            fac_name_low = fac.name.lower()
            fac_cat_low = fac.category.lower()
            # Match keywords
            keywords = [fac_name_low, fac_cat_low]
            if "classroom" in fac_name_low or "smart" in fac_name_low:
                keywords.extend(["class", "classroom", "smart class", "smart classroom"])
            if "library" in fac_name_low:
                keywords.extend(["library", "books", "reading room", "study room"])
            if "lab" in fac_name_low or "computer" in fac_name_low:
                keywords.extend(["lab", "computer lab", "programming lab"])
            if "campus" in fac_name_low or "ground" in fac_name_low:
                keywords.extend(["campus", "building", "grounds", "sports"])

            if any(k in lowered for k in keywords):
                for img in fac.images:
                    if img.ai_visible and img.approval_status == "APPROVED":
                        results.append({
                            "image_url": img.image_url,
                            "source_url": img.source_url,
                            "source_page": img.source_page,
                            "caption": img.caption or fac.name,
                            "alt_text": img.alt_text or fac.name,
                            "facility_id": fac.id,
                            "category": "Facility",
                            "provenance": "Verified Official AIT Facility Record"
                        })

        # 2. Check for event matches (Techfest, Ignite, Hackathon, Cultural, Tarang, 2024, 2025)
        events_query = db.query(Event)
        if year:
            events_query = events_query.filter(Event.calendar_year == year)
        
        events = events_query.all()
        for ev in events:
            ev_name_low = ev.name.lower()
            ev_type_low = ev.event_type.lower()
            ev_year_str = str(ev.calendar_year)

            matches_event = (
                ev_name_low in lowered or
                (ev_type_low in lowered and (ev_year_str in lowered or "event" in lowered)) or
                ("event" in lowered and (ev_year_str in lowered or "last year" in lowered)) or
                (ev_year_str in lowered and ("photo" in lowered or "image" in lowered or "picture" in lowered))
            )

            if matches_event:
                for img in ev.images:
                    if img.ai_visible and img.approval_status == "APPROVED":
                        results.append({
                            "image_url": img.image_url,
                            "source_url": img.source_url,
                            "source_page": img.source_page,
                            "caption": img.caption or ev.name,
                            "alt_text": img.alt_text or ev.name,
                            "event_id": ev.id,
                            "year": ev.calendar_year,
                            "category": "Event",
                            "provenance": f"Verified Official AIT Event Archive ({ev.calendar_year})"
                        })

        # Deduplicate by image_url
        unique_results = []
        seen_urls = set()
        for r in results:
            if r["image_url"] not in seen_urls:
                seen_urls.add(r["image_url"])
                unique_results.append(r)

        return unique_results
