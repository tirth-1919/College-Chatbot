import re
from typing import Dict, Any, Optional

class CollegeEntityExtractor:
    """
    Enhanced multilingual entity extractor for college domain.
    Supports English, Hindi, Gujarati, Hinglish, and common variations/transliterations.
    """
    
    # English course mappings
    COURSES_EN = {
        "bca": "BCA",
        "b.c.a": "BCA",
        "bachelor of computer applications": "BCA",
        "btech": "BTECH_CSE",
        "b.tech": "BTECH_CSE",
        "b tech": "BTECH_CSE",
        "computer engineering": "BTECH_CSE",
        "mca": "MCA",
        "m.c.a": "MCA",
        "mba": "MBA",
        "m.b.a": "MBA"
    }
    
    # Hindi course mappings (transliteration)
    COURSES_HI = {
        "बीसीए": "BCA",
        "बीसीए कोर्स": "BCA",
        "बीटेक": "BTECH_CSE",
        "बीटेक कंप्यूटर": "BTECH_CSE",
        "एमसीए": "MCA",
        "एमबीए": "MBA"
    }
    
    # Gujarati course mappings (transliteration)
    COURSES_GU = {
        "બીસીએ": "BCA",
        "બીસીએ કોર્સ": "BCA",
        "બીટેક": "BTECH_CSE",
        "બીટેક કમ્પ્યુટર": "BTECH_CSE",
        "એમસીએ": "MCA",
        "એમબીએ": "MBA"
    }
    
    # Hinglish course mappings
    COURSES_HINGLISH = {
        "bca": "BCA",
        "bca course": "BCA",
        "bca ka course": "BCA",
        "btech": "BTECH_CSE",
        "b tech": "BTECH_CSE",
        "btech computer": "BTECH_CSE",
        "mca": "MCA",
        "mba": "MBA"
    }
    
    # Combined course mappings
    COURSES = {**COURSES_EN, **COURSES_HI, **COURSES_GU, **COURSES_HINGLISH}

    # English subject mappings
    SUBJECTS_EN = {
        "dbms": "DBMS",
        "database": "DBMS",
        "database management": "DBMS",
        "database management system": "DBMS",
        "python": "Python Programming",
        "python programming": "Python Programming",
        "data structures": "Data Structures",
        "ds": "Data Structures",
        "dsa": "Data Structures",
        "operating system": "Operating Systems",
        "os": "Operating Systems",
        "computer networks": "Computer Networks",
        "cn": "Computer Networks"
    }
    
    # Hindi subject mappings (transliteration)
    SUBJECTS_HI = {
        "डेटाबेस": "DBMS",
        "डीबीएमएस": "DBMS",
        "पायथन": "Python Programming",
        "डेटा स्ट्रक्चर": "Data Structures",
        "ऑपरेटिंग सिस्टम": "Operating Systems"
    }
    
    # Gujarati subject mappings (transliteration)
    SUBJECTS_GU = {
        "ડેટાબેઝ": "DBMS",
        "ડીબીએએમએસ": "DBMS",
        "પાયથોન": "Python Programming",
        "ડેટા સ્ટ્રક્ચર": "Data Structures",
        "ઓપરેટિંગ સિસ્ટમ": "Operating Systems"
    }
    
    # Hinglish subject mappings
    SUBJECTS_HINGLISH = {
        "dbms": "DBMS",
        "database": "DBMS",
        "database management": "DBMS",
        "python": "Python Programming",
        "data structures": "Data Structures",
        "ds": "Data Structures",
        "operating system": "Operating Systems",
        "os": "Operating Systems"
    }
    
    # Combined subject mappings
    SUBJECTS = {**SUBJECTS_EN, **SUBJECTS_HI, **SUBJECTS_GU, **SUBJECTS_HINGLISH}

    # English facility mappings
    FACILITIES_EN = {
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
    
    # Hindi facility mappings (transliteration)
    FACILITIES_HI = {
        "स्मार्ट क्लास": "Smart Classroom",
        "क्लासरूम": "Smart Classroom",
        "लाइब्रेरी": "Central Library",
        "पढ़ाई कक्ष": "Central Library",
        "लैब": "Computer Lab",
        "कंप्यूटर लैब": "High-Performance Computer Lab",
        "कैंपस": "AIT Green Campus",
        "कैंटीन": "Campus Canteen"
    }
    
    # Gujarati facility mappings (transliteration)
    FACILITIES_GU = {
        "સ્માર્ટ ક્લાસ": "Smart Classroom",
        "ક્લાસરૂમ": "Smart Classroom",
        "લાઇબ્રેરી": "Central Library",
        "પઢાઈ રૂમ": "Central Library",
        "લેબ": "Computer Lab",
        "કમ્પ્યુટર લેબ": "High-Performance Computer Lab",
        "કેમ્પસ": "AIT Green Campus",
        "કેન્ટીન": "Campus Canteen"
    }
    
    # Hinglish facility mappings
    FACILITIES_HINGLISH = {
        "smart class": "Smart Classroom",
        "classroom": "Smart Classroom",
        "library": "Central Library",
        "lib": "Central Library",
        "lab": "Computer Lab",
        "computer lab": "High-Performance Computer Lab",
        "campus": "AIT Green Campus",
        "canteen": "Campus Canteen"
    }
    
    # Combined facility mappings
    FACILITIES = {**FACILITIES_EN, **FACILITIES_HI, **FACILITIES_GU, **FACILITIES_HINGLISH}

    # Batch mappings (multilingual)
    BATCHES = {
        "batch a": "A",
        "batch b": "B",
        "batch c": "C",
        "batch d": "D",
        "morning batch": "Morning",
        "evening batch": "Evening",
        "shift 1": "Shift 1",
        "shift 2": "Shift 2",
        # Hindi
        "बैच ए": "A",
        "मॉर्निंग बैच": "Morning",
        "इवनिंग बैच": "Evening",
        # Gujarati
        "બેચ એ": "A",
        "મોર્નિંગ બેચ": "Morning",
        "ઇવનિંગ બેચ": "Evening",
        # Hinglish
        "batch a": "A",
        "morning batch": "Morning",
        "evening batch": "Evening"
    }

    # Room mappings (multilingual)
    ROOMS = {
        "room 101": "Room 101",
        "room 102": "Room 102",
        "room 103": "Room 103",
        "room 201": "Room 201",
        "room 202": "Room 202",
        "room 203": "Room 203",
        "lab 1": "Lab 1",
        "lab 2": "Lab 2",
        "lab 3": "Lab 3",
        "block a": "Block A",
        "block b": "Block B",
        "block c": "Block C",
        # Hindi
        "रूम 101": "Room 101",
        "लैब 1": "Lab 1",
        "ब्लॉक ए": "Block A",
        # Gujarati
        "રૂમ 101": "Room 101",
        "લેબ 1": "Lab 1",
        "બ્લોક એ": "Block A"
    }

    # Faculty name variations (multilingual)
    FACULTY_VARIATIONS = {
        "prof": "Professor",
        "professor": "Professor",
        "dr": "Dr.",
        "doctor": "Dr.",
        "sir": "Sir",
        "madam": "Madam",
        "ma'am": "Madam",
        # Hindi
        "प्रोफेसर": "Professor",
        "सर": "Sir",
        "मैडम": "Madam",
        # Gujarati
        "પ્રોફેસર": "Professor",
        "સર": "Sir",
        "મેડમ": "Madam"
    }

    def __init__(self):
        self.language_mapping = {
            'en': 'English',
            'hi': 'Hindi',
            'gu': 'Gujarati',
            'hinglish': 'Hinglish'
        }
    
    def detect_language(self, text: str) -> str:
        """
        Detect the language of the input text.
        Returns: 'en', 'hi', 'gu', or 'hinglish'
        """
        text_lower = text.lower()
        
        # Check for Hindi characters (Devanagari script)
        if re.search(r'[\u0900-\u097F]', text):
            return 'hi'
        
        # Check for Gujarati characters
        if re.search(r'[\u0A80-\u0AFF]', text):
            return 'gu'
        
        # Check for Hinglish patterns (Roman script with Hindi words)
        hinglish_patterns = [
            r'\b(kya|hai|kitna|kaise|kaun|kahan|kyun)\b',
            r'\b(batao|dikhai|padhai|fees)\b',
            r'\b(kya|che|che|thay)\b'
        ]
        
        for pattern in hinglish_patterns:
            if re.search(pattern, text_lower):
                return 'hinglish'
        
        # Default to English
        return 'en'
    
    def normalize_text(self, text: str, language: str) -> str:
        """
        Normalize text based on detected language.
        Handles transliteration and common variations.
        """
        text_lower = text.lower()
        
        if language == 'hi':
            # Hindi-specific normalization
            text_lower = text_lower.replace('।', '.')  # Replace Hindi danda
            text_lower = text_lower.replace('?', '')  # Remove question marks
            
        elif language == 'gu':
            # Gujarati-specific normalization
            text_lower = text_lower.replace('્', '')  # Remove virama
            
        elif language == 'hinglish':
            # Hinglish-specific normalization
            text_lower = text_lower.replace(' hai ', ' is ')
            text_lower = text_lower.replace(' kya ', ' what ')
            text_lower = text_lower.replace(' kitna ', ' how much ')
        
        return text_lower

    def extract_entities(self, text: str) -> Dict[str, Any]:
        """
        Extract entities with multilingual support.
        
        Args:
            text: Input text to extract entities from
            
        Returns:
            Dictionary with extracted entities
        """
        # Detect language
        language = self.detect_language(text)
        
        # Normalize text based on language
        normalized_text = self.normalize_text(text, language)
        lowered = normalized_text.lower()
        
        entities = {
            "detected_language": language,
            "original_text": text,
            "normalized_text": normalized_text
        }

        # 1. Course extraction (multilingual)
        for alias, norm in self.COURSES.items():
            if re.search(rf"\b{re.escape(alias)}\b", lowered, re.IGNORECASE):
                entities["course"] = norm
                break

        # 2. Subject extraction (multilingual)
        for alias, norm in self.SUBJECTS.items():
            if re.search(rf"\b{re.escape(alias)}\b", lowered, re.IGNORECASE):
                entities["subject"] = norm
                break

        # 3. Facility extraction (multilingual)
        for alias, norm in self.FACILITIES.items():
            if re.search(rf"\b{re.escape(alias)}\b", lowered, re.IGNORECASE):
                entities["facility"] = norm
                break

        # 4. Batch extraction (multilingual)
        for alias, norm in self.BATCHES.items():
            if re.search(rf"\b{re.escape(alias)}\b", lowered, re.IGNORECASE):
                entities["batch"] = norm
                break

        # 5. Room extraction (multilingual)
        for alias, norm in self.ROOMS.items():
            if re.search(rf"\b{re.escape(alias)}\b", lowered, re.IGNORECASE):
                entities["room"] = norm
                break

        # 6. Semester extraction (multilingual patterns)
        # English
        sem_match = re.search(r"\bsem(?:ester)?\s*([1-8])\b", lowered)
        if not sem_match:
            # Hindi
            sem_match = re.search(r"\bसेमेस्टर\s*([1-8])\b", text)
        if not sem_match:
            # Gujarati
            sem_match = re.search(r"\bસેમેસ્ટર\s*([1-8])\b", text)
        if not sem_match:
            # Hinglish
            sem_match = re.search(r"\bsem\s*([1-8])\b", lowered)
        
        if sem_match:
            entities["semester"] = int(sem_match.group(1))

        # 7. Year resolution (multilingual)
        year_patterns = {
            'en': [
                (r"last year|previous year", 2025, "2024-25"),
                (r"this year|current year", 2026, "2026-27"),
                (r"next year|upcoming year", 2027, "2027-28")
            ],
            'hi': [
                (r"पिछला साल|पिछले साल", 2025, "2024-25"),
                (r"इस साल|वर्तमान साल", 2026, "2026-27"),
                (r"अगला साल|आने वाला साल", 2027, "2027-28")
            ],
            'gu': [
                (r"પાછલો વર્ષ|ગયા વર્ષે", 2025, "2024-25"),
                (r"આ વર્ષ|વર્તમાન વર્ષ", 2026, "2026-27"),
                (r"આવતો વર્ષ|આવતા વર્ષે", 2027, "2027-28")
            ],
            'hinglish': [
                (r"last year|pichla saal", 2025, "2024-25"),
                (r"this year|is saal", 2026, "2026-27"),
                (r"next year|aane wala saal", 2027, "2027-28")
            ]
        }
        
        year_resolved = False
        for pattern, year, academic_year in year_patterns.get(language, []):
            if re.search(pattern, lowered):
                entities["year"] = year
                entities["academic_year"] = academic_year
                year_resolved = True
                break
        
        # Explicit year if not resolved
        if not year_resolved:
            year_match = re.search(r"\b(202[0-9])\b", lowered)
            if year_match:
                entities["year"] = int(year_match.group(1))
                entities["academic_year"] = f"{year_match.group(1)}-{(int(year_match.group(1))+1)%100:02d}"

        # 8. Day resolution (multilingual)
        day_patterns = {
            'en': [
                (r"today|aaj", "Monday"),
                (r"tomorrow|kal", "Tuesday")
            ],
            'hi': [
                (r"आज|आज के", "Monday"),
                (r"कल|कल के", "Tuesday")
            ],
            'gu': [
                (r"આજ|આજે", "Monday"),
                (r"કાલે|કાલે", "Tuesday")
            ],
            'hinglish': [
                (r"today|aaj", "Monday"),
                (r"tomorrow|kal", "Tuesday")
            ]
        }
        
        for pattern, day in day_patterns.get(language, []):
            if re.search(pattern, lowered):
                entities["day"] = day
                break

        # 9. Faculty title extraction (multilingual)
        for alias, norm in self.FACULTY_VARIATIONS.items():
            if re.search(rf"\b{re.escape(alias)}\b", lowered, re.IGNORECASE):
                entities["faculty_title"] = norm
                break

        return entities
    
    def get_entity_confidence(self, entities: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate confidence scores for extracted entities.
        
        Args:
            entities: Extracted entities dictionary
            
        Returns:
            Dictionary with confidence scores per entity type
        """
        confidence = {}
        
        # Higher confidence for direct matches vs inferred
        if "course" in entities:
            confidence["course"] = 0.95 if entities["detected_language"] == "en" else 0.85
        
        if "subject" in entities:
            confidence["subject"] = 0.90 if entities["detected_language"] == "en" else 0.80
        
        if "semester" in entities:
            confidence["semester"] = 0.95  # Usually very explicit
        
        if "year" in entities:
            confidence["year"] = 0.90
        
        if "facility" in entities:
            confidence["facility"] = 0.85 if entities["detected_language"] == "en" else 0.75
        
        return confidence
