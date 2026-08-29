"""
Unified Entity Extractor for College Domain
Extracts, normalizes, and validates college-specific entities:
course, semester, subject, department, faculty, exam, event, facility, notice, date, academic_year, result_type, language
Supports English, Hindi, Gujarati, Hinglish, and colloquial variations.
"""

import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, UTC

"""
Unified Entity Extractor for College Domain
Extracts, normalizes, and validates college-specific entities:
course, semester, subject, department, faculty, exam, event, facility, notice, date, academic_year, result_type, language
Supports English, Hindi, Gujarati, Hinglish, typos, and colloquial variations.
"""

import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, UTC

class CollegeEntityExtractor:
    """
    Multilingual, normalization-aware entity extractor for AIT College domain.
    Extracts and standardizes all college-specific entities.
    """

    # 1. Course mappings and canonical normalization
    COURSES = {
        # BCA
        "bca": "BCA",
        "b.c.a": "BCA",
        "b c a": "BCA",
        "bca course": "BCA",
        "bachelor of computer applications": "BCA",
        "bca program": "BCA",
        "bca degree": "BCA",
        "બીસીએ": "BCA",
        "બીસીએ કોર્સ": "BCA",
        "बीसीए": "BCA",
        "बीसीए कोर्स": "BCA",
        "bca ka": "BCA",
        "bca nu": "BCA",
        "bca ma": "BCA",

        # BTech CSE
        "btech": "BTECH_CSE",
        "b.tech": "BTECH_CSE",
        "b tech": "BTECH_CSE",
        "btech cse": "BTECH_CSE",
        "b.tech cse": "BTECH_CSE",
        "computer engineering": "BTECH_CSE",
        "computer science": "BTECH_CSE",
        "cse": "BTECH_CSE",
        "bachelor of technology": "BTECH_CSE",
        "बीटेक": "BTECH_CSE",
        "બીટેક": "BTECH_CSE",
        "બીટેક કમ્પ્યુટર": "BTECH_CSE",
        "बीटेक कंप्यूटर": "BTECH_CSE",

        # BTech IT
        "btech it": "BTECH_IT",
        "b.tech it": "BTECH_IT",
        "information technology": "BTECH_IT",
        "it department": "BTECH_IT",

        # MCA
        "mca": "MCA",
        "m.c.a": "MCA",
        "mca course": "MCA",
        "master of computer applications": "MCA",
        "એમસીએ": "MCA",
        "एमसीए": "MCA",

        # MBA
        "mba": "MBA",
        "m.b.a": "MBA",
        "mba course": "MBA",
        "master of business administration": "MBA",
        "એમબીએ": "MBA",
        "एमबीए": "MBA"
    }

    # 2. Subject mappings and canonical normalization
    SUBJECTS = {
        # DBMS
        "dbms": "DBMS",
        "database": "DBMS",
        "databases": "DBMS",
        "database management": "DBMS",
        "database management system": "DBMS",
        "database management systems": "DBMS",
        "rdbms": "DBMS",
        "sql": "DBMS",
        "ડીબીએમએસ": "DBMS",
        "ડેટાબેઝ": "DBMS",
        "ડેટાબેસ": "DBMS",
        "डीबीएमएस": "DBMS",
        "डेटाबेस": "DBMS",

        # Python
        "python": "Python Programming",
        "python programming": "Python Programming",
        "python language": "Python Programming",
        "py": "Python Programming",
        "પાયથોન": "Python Programming",
        "पायथन": "Python Programming",

        # Data Structures
        "data structures": "Data Structures",
        "data structure": "Data Structures",
        "ds": "Data Structures",
        "dsa": "Data Structures",
        "data structures and algorithms": "Data Structures",
        "ડેટા સ્ટ્રક્ચર": "Data Structures",
        "ડેટા સ્ટ્રક્ચર્સ": "Data Structures",
        "डेटा स्ट्रक्चर": "Data Structures",

        # Operating Systems
        "operating systems": "Operating Systems",
        "operating system": "Operating Systems",
        "os": "Operating Systems",
        "ઓપરેટિંગ સિસ્ટમ": "Operating Systems",
        "ऑपरेटिंग सिस्टम": "Operating Systems",

        # Java
        "java": "Java Programming",
        "java programming": "Java Programming",
        "core java": "Java Programming",
        "advance java": "Java Programming",
        "જાવા": "Java Programming",
        "जावा": "Java Programming",

        # Computer Networks
        "computer networks": "Computer Networks",
        "computer network": "Computer Networks",
        "networking": "Computer Networks",
        "cn": "Computer Networks",
        "કમ્પ્યુટર નેટવર્ક્સ": "Computer Networks",
        "कंप्यूटर नेटवर्क": "Computer Networks",

        # Web Development
        "web development": "Web Development",
        "web technology": "Web Development",
        "web tech": "Web Development",
        "html": "Web Development",
        "css": "Web Development",
        "javascript": "Web Development",

        # Software Engineering
        "software engineering": "Software Engineering",
        "software eng": "Software Engineering",
        "se": "Software Engineering",

        # Mathematics
        "mathematics": "Mathematics",
        "maths": "Mathematics",
        "math": "Mathematics",
        "discrete maths": "Mathematics",
        "ગણિત": "Mathematics",
        "गणित": "Mathematics"
    }

    # 3. Department mappings
    DEPARTMENTS = {
        "computer engineering": "Computer Engineering",
        "computer applications": "Computer Applications",
        "information technology": "Information Technology",
        "mechanical engineering": "Mechanical Engineering",
        "civil engineering": "Civil Engineering",
        "electrical engineering": "Electrical Engineering",
        "management studies": "Management Studies",
        "applied sciences": "Applied Sciences & Humanities",
        "bca department": "Computer Applications",
        "mca department": "Computer Applications",
        "cse department": "Computer Engineering",
        "it department": "Information Technology"
    }

    # 4. Facility mappings
    FACILITIES = {
        "library": "Central Library",
        "central library": "Central Library",
        "reading room": "Central Library",
        "smart classroom": "Smart Classroom",
        "smart class": "Smart Classroom",
        "classroom": "Smart Classroom",
        "class": "Smart Classroom",
        "computer lab": "High-Performance Computer Lab",
        "lab": "High-Performance Computer Lab",
        "laboratory": "High-Performance Computer Lab",
        "campus": "AIT Green Campus",
        "canteen": "Campus Canteen",
        "cafeteria": "Campus Canteen",
        "sports ground": "Sports Complex & Ground",
        "auditorium": "Main Auditorium",
        "લાઇબ્રેરી": "Central Library",
        "સ્માર્ટ ક્લાસ": "Smart Classroom",
        "કમ્પ્યુટર લેબ": "High-Performance Computer Lab",
        "કેમ્પસ": "AIT Green Campus",
        "કેન્ટીન": "Campus Canteen",
        "लाइब्रेरी": "Central Library",
        "स्मार्ट क्लास": "Smart Classroom",
        "कंप्यूटर लैब": "High-Performance Computer Lab",
        "कैंपस": "AIT Green Campus",
        "कैंटीन": "Campus Canteen"
    }

    # 5. Event mappings
    EVENTS = {
        "techfest": "Ignite Techfest",
        "ignite": "Ignite Techfest",
        "hackathon": "AIT Hackathon",
        "cultural fest": "Tarang Cultural Fest",
        "tarang": "Tarang Cultural Fest",
        "annual day": "Annual Function",
        "sports day": "Annual Sports Week",
        "sports week": "Annual Sports Week",
        "navratri": "Navratri Mahotsav",
        "orientation": "Student Orientation Program",
        "convocation": "Annual Convocation",
        "ટેકફેસ્ટ": "Ignite Techfest",
        "નવરાત્રી": "Navratri Mahotsav",
        "टेकफेस्ट": "Ignite Techfest",
        "नवरात्रि": "Navratri Mahotsav"
    }

    # 6. Faculty Title mappings
    FACULTY_TITLES = {
        "prof": "Professor",
        "professor": "Professor",
        "dr": "Dr.",
        "doctor": "Dr.",
        "sir": "Sir",
        "madam": "Madam",
        "ma'am": "Madam",
        "hod": "Head of Department",
        "head of department": "Head of Department",
        "dean": "Dean",
        "principal": "Principal",
        "director": "Director"
    }

    # 7. Result types
    RESULT_TYPES = {
        "spi": "SPI",
        "cpi": "CPI",
        "cgpa": "CGPA",
        "sgpa": "SGPA",
        "grade": "Grades",
        "grades": "Grades",
        "marksheet": "Marksheet",
        "scorecard": "Scorecard",
        "result": "Semester Result",
        "પરિણામ": "Semester Result",
        "રિઝલ્ટ": "Semester Result",
        "परिणाम": "Semester Result",
        "रिजल्ट": "Semester Result"
    }

    def __init__(self):
        pass

    def detect_language(self, text: str) -> str:
        """
        Detects primary language: en (English), hi (Hindi), gu (Gujarati), hinglish
        """
        text_lower = text.lower()
        if re.search(r'[\u0A80-\u0AFF]', text):
            return "gu"
        if re.search(r'[\u0900-\u097F]', text):
            return "hi"
        # Check for common Gujarati transliterations
        gu_words = ["kem", "su", "shu", "nathi", "batavo", "kaya", "keva", "che", "kyare", "maro", "mara", "bhanave", "bhanavse", "ketli", "ketla"]
        if any(w in text_lower.split() for w in gu_words):
            return "gu"
        # Check for Hinglish / Hindi transliterations
        hi_words = ["kya", "kaun", "kab", "dikhao", "hai", "batao", "mera", "padhate", "kitni", "kitna", "karo", "chahiye", "padhai"]
        if any(w in text_lower.split() for w in hi_words):
            return "hinglish"
        return "en"

    def normalize_text(self, text: str) -> str:
        """
        Clean and normalize input text while preserving Gujarati/Devanagari Unicode.
        """
        if not text:
            return ""
        # Collapse multiple whitespaces and control characters
        cleaned = re.sub(r'\s+', ' ', text.strip())
        # Replace repeated punctuation
        cleaned = re.sub(r'([!?.])\1+', r'\1', cleaned)
        return cleaned

    def extract_entities(self, text: str) -> Dict[str, Any]:
        """
        Extract and canonicalize college domain entities from query.
        """
        raw_text = text or ""
        normalized = self.normalize_text(raw_text)
        lowered = normalized.lower()
        language = self.detect_language(raw_text)

        entities: Dict[str, Any] = {
            "detected_language": language,
            "normalized_query": normalized
        }

        # 1. Course Extraction
        for alias, norm in self.COURSES.items():
            pattern = rf"\b{re.escape(alias)}\b"
            if re.search(pattern, lowered, re.IGNORECASE) or alias in raw_text:
                entities["course"] = norm
                break

        # 2. Subject Extraction
        for alias, norm in self.SUBJECTS.items():
            pattern = rf"\b{re.escape(alias)}\b"
            if re.search(pattern, lowered, re.IGNORECASE) or alias in raw_text:
                entities["subject"] = norm
                break

        # 3. Department Extraction
        for alias, norm in self.DEPARTMENTS.items():
            if alias in lowered:
                entities["department"] = norm
                break

        # 4. Semester Extraction
        sem_match = re.search(r"\b(?:sem(?:ester)?|સેમેસ્ટર|सेमेस्टर)\s*([1-8])\b", lowered)
        if not sem_match:
            sem_match = re.search(r"\b([1-8])(?:st|nd|rd|th)?\s*(?:sem(?:ester)?|સેમેસ્ટર|सेमेस्टर)\b", lowered)
        if not sem_match:
            # Roman numerals
            roman_map = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8}
            rom_match = re.search(r"\bsem(?:ester)?\s*(i|ii|iii|iv|v|vi|vii|viii)\b", lowered)
            if rom_match:
                entities["semester"] = roman_map.get(rom_match.group(1).lower())
        if sem_match:
            entities["semester"] = int(sem_match.group(1))

        # 5. Facility Extraction
        for alias, norm in self.FACILITIES.items():
            pattern = rf"\b{re.escape(alias)}\b"
            if re.search(pattern, lowered, re.IGNORECASE) or alias in raw_text:
                entities["facility"] = norm
                break

        # 6. Event Extraction
        for alias, norm in self.EVENTS.items():
            pattern = rf"\b{re.escape(alias)}\b"
            if re.search(pattern, lowered, re.IGNORECASE) or alias in raw_text:
                entities["event"] = norm
                break

        # 7. Faculty Title / Role
        for alias, norm in self.FACULTY_TITLES.items():
            pattern = rf"\b{re.escape(alias)}\b"
            if re.search(pattern, lowered, re.IGNORECASE):
                entities["faculty_title"] = norm
                break

        # 8. Result Type
        for alias, norm in self.RESULT_TYPES.items():
            pattern = rf"\b{re.escape(alias)}\b"
            if re.search(pattern, lowered, re.IGNORECASE) or alias in raw_text:
                entities["result_type"] = norm
                break

        # 9. Academic Year & Relative Year
        if any(w in lowered for w in ["last year", "previous year", "pichle saal", "pichla saal", "ગયા વર્ષે", "પાછલા વર્ષે", "पिछले साल"]):
            entities["academic_year"] = "2024-25"
            entities["year"] = 2025
            entities["year_relative"] = "previous"
        elif any(w in lowered for w in ["this year", "current year", "is saal", "આ વર્ષે", "इस साल"]):
            entities["academic_year"] = "2026-27"
            entities["year"] = 2026
            entities["year_relative"] = "current"
        elif any(w in lowered for w in ["next year", "upcoming year", "aavta varshe", "આવતા વર્ષે", "अगले साल"]):
            entities["academic_year"] = "2027-28"
            entities["year"] = 2027
            entities["year_relative"] = "next"
        else:
            yr_match = re.search(r"\b(202[0-9])\b", lowered)
            if yr_match:
                y = int(yr_match.group(1))
                entities["year"] = y
                entities["academic_year"] = f"{y}-{(y+1)%100:02d}"

        # 10. Day Extraction for Timetables
        days_en = {"monday": "Monday", "tuesday": "Tuesday", "wednesday": "Wednesday", "thursday": "Thursday", "friday": "Friday", "saturday": "Saturday"}
        for d_key, d_val in days_en.items():
            if d_key in lowered:
                entities["day"] = d_val
                break
        if not entities.get("day"):
            if any(w in lowered for w in ["today", "aaj", "aaje", "આજે", "आज"]):
                entities["day"] = "Monday"  # Default reference day for schedule lookup
            elif any(w in lowered for w in ["tomorrow", "kal", "kale", "કાલે", "कल"]):
                entities["day"] = "Tuesday"

        # 11. Date / Exam reference extraction
        date_match = re.search(r"\b(\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*(?:202[0-9])?)\b", lowered)
        if date_match:
            entities["date"] = date_match.group(1)

        # 12. Notice / Circular
        if any(w in lowered for w in ["notice", "circular", "announcement", "paripatra", "નોટિસ", "પરિપત્ર", "नोटिस", "परिपत्र"]):
            entities["notice"] = True

        # 13. Exam type
        if any(w in lowered for w in ["mid-term", "midterm", "mid sem", "internal exam"]):
            entities["exam_type"] = "Mid-Term"
        elif any(w in lowered for w in ["end-term", "final exam", "gtu exam", "external exam", "sem exam"]):
            entities["exam_type"] = "End-Term"
        elif any(w in lowered for w in ["viva", "practical", "lab exam"]):
            entities["exam_type"] = "Practical/Viva"

        return entities

    def get_entity_confidence(self, entities: Dict[str, Any]) -> Dict[str, float]:
        """Calculates extraction confidence per entity type"""
        confidences = {}
        for k in ["course", "subject", "semester", "facility", "event", "department", "academic_year"]:
            if k in entities:
                confidences[k] = 0.95
        return confidences

