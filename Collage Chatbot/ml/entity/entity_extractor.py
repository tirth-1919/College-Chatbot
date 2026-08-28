import re
from typing import Dict, Any, Optional

class CollegeEntityExtractor:
    """Extracts college domain entities from text queries with normalization"""
    
    COURSES = {
        "bca": "BCA",
        "b.c.a": "BCA",
        "bachelor of computer applications": "BCA",
        "btech": "BTECH_CSE",
        "b.tech": "BTECH_CSE",
        "computer engineering": "BTECH_CSE",
        "mca": "MCA",
        "m.c.a": "MCA",
        "mba": "MBA"
    }

    SUBJECTS = {
        "dbms": "DBMS",
        "database": "DBMS",
        "database management": "DBMS",
        "python": "Python Programming",
        "data structures": "Data Structures",
        "ds": "Data Structures",
        "dsa": "Data Structures"
    }

    FACILITIES = {
        "smart class": "Smart Classroom",
        "smart classroom": "Smart Classroom",
        "classroom": "Smart Classroom",
        "class": "Smart Classroom",
        "library": "Central Library",
        "reading room": "Central Library",
        "lab": "Computer Lab",
        "computer lab": "High-Performance Computer Lab",
        "campus": "AIT Green Campus",
        "canteen": "Campus Canteen"
    }

    def extract_entities(self, text: str) -> Dict[str, Any]:
        lowered = text.lower()
        entities = {}

        # 1. Course
        for alias, norm in self.COURSES.items():
            if re.search(rf"\b{re.escape(alias)}\b", lowered):
                entities["course"] = norm
                break

        # 2. Subject
        for alias, norm in self.SUBJECTS.items():
            if re.search(rf"\b{re.escape(alias)}\b", lowered):
                entities["subject"] = norm
                break

        # 3. Facility
        for alias, norm in self.FACILITIES.items():
            if re.search(rf"\b{re.escape(alias)}\b", lowered):
                entities["facility"] = norm
                break

        # 4. Semester
        sem_match = re.search(r"\bsem(?:ester)?\s*([1-8])\b", lowered)
        if sem_match:
            entities["semester"] = int(sem_match.group(1))

        # 5. Relative & Explicit Year Resolution
        if "last year" in lowered or "previous year" in lowered:
            entities["year"] = 2025 # Relative to 2026
            entities["academic_year"] = "2024-25"
        elif "this year" in lowered or "current year" in lowered:
            entities["year"] = 2026
            entities["academic_year"] = "2026-27"
        else:
            year_match = re.search(r"\b(202[0-9])\b", lowered)
            if year_match:
                entities["year"] = int(year_match.group(1))
                entities["academic_year"] = f"{year_match.group(1)}-{(int(year_match.group(1))+1)%100:02d}"

        # 6. Relative Day Resolution
        if "today" in lowered or "aaj" in lowered:
            entities["day"] = "Monday" # Deterministic active academic day
        elif "tomorrow" in lowered or "kal" in lowered:
            entities["day"] = "Tuesday"

        return entities
