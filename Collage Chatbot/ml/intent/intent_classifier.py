import re
from typing import Tuple, Dict, Any

class IntentClassifier:
    """
    College Domain Intent Classifier.
    Classifies user intent with confidence scores across 12 distinct functional categories.
    """
    
    INTENT_PATTERNS = {
        "FEE_QUERY": [
            r"\b(fee|fees|tuition|charge|cost|amount|instalment|payment)\b",
            r"\b(bca|btech|mca|mba)\s+(fee|fees)\b",
            r"\bketli\s+fee\s+che\b",
            r"\bkitni\s+fee\s+hai\b"
        ],
        "FACULTY_SUBJECT_QUERY": [
            r"\b(who\s+teaches|faculty\s+for|professor\s+for|teacher\s+for|teaches)\b",
            r"\b(dbms|python|data\s+structures|java|os)\s+(teacher|faculty|sir|madam)\b",
            r"\bkon\s+bhanave\s+che\b",
            r"\bkaun\s+padhata\s+hai\b"
        ],
        "TIMETABLE_QUERY": [
            r"\b(timetable|time\s+table|schedule|class\s+time|today'?s\s+class|lecture)\b",
            r"\baaj\s+no\s+timetable\b",
            r"\baaj\s+ka\s+timetable\b"
        ],
        "EXAM_QUERY": [
            r"\b(exam|examination|mid-?term|end-?term|viva|practical|test\s+date)\b",
            r"\bpariksha|parixa\b",
            r"\bexam\s+kyare\s+che\b"
        ],
        "EVENT_IMAGE_SEARCH": [
            r"\b(event\s+photos?|event\s+pictures?|photos?\s+of.*event|last\s+year.*photos?|show.*event\s+photos?)\b",
            r"\bevents?\s+na\s+photos?\b"
        ],
        "EVENT_HISTORY": [
            r"\b(events?|techfest|hackathon|cultural\s+fest|ignite|tarang|happened\s+last\s+year|organized)\b",
            r"\bkaya\s+events\s+thaya\s+hata\b",
            r"\bkaunse\s+events\s+huye\s+the\b"
        ],
        "FACILITY_IMAGE_SEARCH": [
            r"\b(photo|picture|look\s+like|show\s+me).*(classroom|smart\s+class|library|lab|campus|canteen)\b",
            r"\b(classroom|smart\s+class|library|lab|campus|canteen).*(photo|picture|batavo|dikhaye)\b",
            r"\bphoto\s+batavo\b",
            r"\bfoto\s+dikhao\b"
        ],
        "NOTICE_QUERY": [
            r"\b(notice|announcement|circular|update|deadline|circulars)\b",
            r"\bnotice\s+board\b"
        ],
        "STUDY_ASSISTANT": [
            r"\b(quiz|flashcard|study\s+plan|explain\s+topic|mock\s+test|viva\s+practice)\b",
            r"\bhelp\s+me\s+study\b"
        ],
        "SUPPORT_TICKET": [
            r"\b(complaint|grievance|support|helpdesk|issue|ticket|problem)\b"
        ],
        "GENERAL_EDUCATION": [
            r"\b(what\s+is|explain|how\s+does|difference\s+between|tutorial|algorithm|define)\b",
            r"\b(machine\s+learning|artificial\s+intelligence|blockchain|cloud\s+computing|neural\s+network)\b"
        ]
    }

    def predict(self, text: str) -> Tuple[str, float]:
        lowered = text.lower().strip()
        
        # Priority checking for visual and transactional queries
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, lowered):
                    # Boost confidence
                    return intent, 0.96

        return "GENERAL_ACADEMIC", 0.70
