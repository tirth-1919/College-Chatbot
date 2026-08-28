from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.entities import Facility, FacilityImage, Event, EventImage
from rag.images.image_retriever import OfficialImageRetriever

router = APIRouter(prefix="/visual", tags=["Visual Media & Official Gallery"])

@router.get("/facilities")
def get_facilities(db: Session = Depends(get_db)):
    facs = db.query(Facility).filter(Facility.is_active == True).all()
    results = []
    for f in facs:
        imgs = [
            {
                "image_url": i.image_url,
                "source_url": i.source_url,
                "source_page": i.source_page,
                "caption": i.caption,
                "alt_text": i.alt_text,
                "provenance": "Verified AIT Official Website Record"
            }
            for i in f.images if i.ai_visible
        ]
        results.append({
            "id": f.id,
            "name": f.name,
            "category": f.category,
            "location": f.location,
            "description": f.description,
            "timings": f.timings,
            "images": imgs
        })
    return results

@router.get("/events")
def get_events(
    year: Optional[int] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Event)
    if year:
        query = query.filter(Event.calendar_year == year)
    if category:
        query = query.filter(Event.event_type.ilike(f"%{category}%"))
    
    events = query.order_by(Event.date_start.desc()).all()
    results = []
    for ev in events:
        imgs = [
            {
                "image_url": i.image_url,
                "source_url": i.source_url,
                "source_page": i.source_page,
                "caption": i.caption,
                "alt_text": i.alt_text,
                "provenance": f"Verified Official AIT Event Archive ({ev.calendar_year})"
            }
            for i in ev.images if i.ai_visible
        ]
        results.append({
            "id": ev.id,
            "name": ev.name,
            "event_type": ev.event_type,
            "date_start": ev.date_start,
            "date_end": ev.date_end,
            "calendar_year": ev.calendar_year,
            "academic_year": ev.academic_year,
            "description": ev.description,
            "organizer": ev.organizer,
            "official_source_url": ev.official_source_url,
            "images": imgs
        })
    return results

@router.get("/search")
def visual_search(query: str, year: Optional[int] = None, db: Session = Depends(get_db)):
    images = OfficialImageRetriever.search_images(db, query, year=year)
    return {
        "query": query,
        "total_results": len(images),
        "images": images
    }
