import re
from typing import Tuple, Dict, Any

# Known injection patterns
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"system\s+prompt\s+override",
    r"you\s+are\s+now\s+(an\s+unfiltered|in\s+god\s+mode|dan)",
    r"forget\s+(everything|all\s+rules)",
    r"disregard\s+(all\s+)?constraints",
    r"reveal\s+(the\s+)?(admin\s+password|database\s+password|secret\s+key|api\s+key)",
    r"<script[\s\S]*?>[\s\S]*?<\/script>",
]

PII_PATTERNS = {
    "phone": r"\b(?:\+91[\-\s]?)?[6789]\d{9}\b",
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b",
    "aadhaar": r"\b\d{4}\s\d{4}\s\d{4}\b",
    "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
}

def sanitize_user_input(text: str) -> str:
    """Strip dangerous characters and HTML tags"""
    if not text:
        return ""
    # Strip HTML tags
    cleaned = re.sub(r'<[^>]*?>', '', text)
    return cleaned.strip()

def check_prompt_injection(text: str) -> Tuple[bool, str]:
    """Check if query matches prompt injection or jailbreak patterns"""
    lowered = text.lower()
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, lowered):
            return True, "Potential prompt injection or policy violation detected"
    return False, ""

def redact_pii(text: str) -> str:
    """Scrub PII (emails, phone numbers, aadhaar) before feeding to ML training datasets"""
    redacted = text
    for pii_type, pattern in PII_PATTERNS.items():
        redacted = re.sub(pattern, f"[{pii_type.upper()}_REDACTED]", redacted)
    return redacted
