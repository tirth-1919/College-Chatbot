# Deterministic, database-backed academic catalog queries.
# It returns only active, verified records and never invents subject lists.
import re
from typing import Any, Dict, Optional
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from backend.app.models.entities import Course, Subject
_ROMAN = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8}

def academic_entities(text: str) -> Dict[str, Any]:
    value = (text or "").lower()
    result: Dict[str, Any] = {}
    for alias, code in (("bca", "BCA"), ("bba", "BBA"), ("mca", "MCA"), ("mba", "MBA"), ("b.com", "BCOM"), ("bcom", "BCOM"), ("m.com", "MCOM"), ("mcom", "MCOM"), ("b.sc", "BSC"), ("bsc", "BSC"), ("m.sc", "MSC"), ("msc", "MSC")):
        if alias in value:
            result["course"] = code
            break
    match = re.search(r"\b(?:sem(?:ester)?|semester)\s*(?:no\.?\s*)?([1-8])\b", value)
    if not match:
        match = re.search(r"\b(first|second|third|fourth|fifth|sixth|seventh|eighth)\s+sem", value)
    if match:
        result["semester"] = int(match.group(1)) if match.group(1).isdigit() else _ROMAN[match.group(1)]
    year = re.search(r"\b(20\d{2})\s*[-/]\s*(\d{2,4})\b", value)
    if year:
        result["academic_year"] = f"{year.group(1)}-{year.group(2)[-2:]}"
    result["language"] = "gu" if re.search(r"[\u0a80-\u0aff]", text or "") or any(w in value.split() for w in ("che", "batavo")) else "en"
    return result

def is_academic_query(text: str, entities: Dict[str, Any]) -> bool:
    value = (text or "").lower()
    # Existing verified exam, fee, timetable and faculty routes retain precedence.
    if any(w in value for w in ("exam", "fee", "timetable", "schedule", "who teaches", "faculty")):
        return False
    return bool(entities.get("course") and any(w in value for w in ("subject", "semester", "sem", "syllabus", "curriculum", "code", "credits", "explain", "topics", "academic")))

def query_catalog(db: Session, text: str, entities: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    entities = entities or academic_entities(text)
    if not is_academic_query(text, entities):
        return None
    course_code = entities.get("course")
    course = db.query(Course).filter(Course.code == course_code).first()
    if not course:
        return {"answer": f"I couldn't find a verified academic catalog entry for **{course_code}**.", "course": course_code, "subjects": [], "verified": False}
    query = db.query(Subject).filter(Subject.course_id == course.id, Subject.is_active == True)
    subject_columns = {column["name"] for column in inspect(db.bind).get_columns("subjects")}
    if "verification_status" in subject_columns:
        query = query.filter(Subject.verification_status == "VERIFIED")
    if entities.get("semester"):
        query = query.filter(Subject.semester == entities["semester"])
    if entities.get("academic_year"):
        query = query.filter(Subject.academic_year == entities["academic_year"])
    subjects = query.order_by(Subject.semester, Subject.code).all()
    if not subjects:
        return {"answer": f"I couldn't find verified subjects for **{course.code}** in the requested academic context.", "course": course.code, "subjects": [], "verified": False}
    grouped: Dict[int, list] = {}
    for subject in subjects:
        grouped.setdefault(subject.semester, []).append(subject)
    lines = [f"### {course.name} ({course.code}) — verified subjects", ""]
    for semester, items in grouped.items():
        lines.append(f"**Semester {semester}**")
        for item in items:
            details = [item.code]
            if item.credits is not None: details.append(f"{item.credits} credits")
            if item.category: details.append(item.category)
            lines.append(f"- **{item.name}** ({' · '.join(details)})")
        lines.append("")
    return {"answer": "\n".join(lines).strip(), "course": course.code, "semester": entities.get("semester"), "subjects": subjects, "verified": True, "academic_years": sorted({s.academic_year for s in subjects})}
