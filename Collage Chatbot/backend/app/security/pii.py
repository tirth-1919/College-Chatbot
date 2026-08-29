import re
from typing import List, Tuple, Optional

class PIIDetector:
    """
    Personally Identifiable Information (PII) Detector and redactor.
    Detects and masks sensitive information like Aadhaar numbers, phone numbers, email addresses, etc.
    """

    # Indian-specific patterns
    AADHAAR_PATTERN = r'\b[2-9]\d{11}\b'  # 12-digit Aadhaar (simplified)
    AADHAAR_PATTERN_FORMATTED = r'\b[2-9]\d{4}\s?\d{4}\s?\d{4}\b'  # Formatted Aadhaar

    # Generic patterns
    EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    PHONE_PATTERN = r'(?:\+?91[\s-]?)?[6-9]\d{9}\b|\b\d{10}\b'  # Indian / 10-digit phone numbers
    PHONE_PATTERN_FORMATTED = r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b'

    # Payment card patterns (basic)
    CREDIT_CARD_PATTERN = r'\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{16}\b'

    # Academic identifiers
    ENROLLMENT_PATTERN = r'\b(?:20\d{2}[A-Za-z0-9]{6,10}|\d{10,14})\b'  # Generic enrollment/roll numbers

    # Secrets / Tokens / Keys
    API_KEY_PATTERN = r'\b(?:sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,}|AIza[0-9A-Za-z-_]{35}|eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+)\b'
    PASSWORD_PATTERN = r'(?i)\b(?:password|passwd|pwd)\s*[:=]\s*(\S+)'

    def __init__(self):
        self.patterns = {
            'aadhaar': [self.AADHAAR_PATTERN, self.AADHAAR_PATTERN_FORMATTED],
            'email': [self.EMAIL_PATTERN],
            'phone': [self.PHONE_PATTERN, self.PHONE_PATTERN_FORMATTED],
            'credit_card': [self.CREDIT_CARD_PATTERN],
            'enrollment': [self.ENROLLMENT_PATTERN],
            'api_key': [self.API_KEY_PATTERN],
            'password': [self.PASSWORD_PATTERN]
        }

    def detect_pii(self, text: str) -> List[Tuple[str, str, int, int]]:
        """
        Detect PII in text.

        Returns:
            List of tuples: (pii_type, matched_text, start_position, end_position)
        """
        detected_pii = []

        for pii_type, patterns in self.patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text):
                    detected_pii.append((
                        pii_type,
                        match.group(),
                        match.start(),
                        match.end()
                    ))

        return detected_pii

    def redact_pii(self, text: str, mask_char: str = "*", preserve_length: bool = True) -> str:
        """
        Redact PII from text by replacing with mask characters.

        Args:
            text: Input text containing potential PII
            mask_char: Character to use for masking
            preserve_length: Whether to preserve the original length

        Returns:
            Text with PII redacted
        """
        detected_pii = self.detect_pii(text)

        if not detected_pii:
            return text

        # Sort by position in reverse order to avoid index shifting
        detected_pii.sort(key=lambda x: x[2], reverse=True)

        redacted_text = text
        for pii_type, matched_text, start, end in detected_pii:
            if preserve_length:
                masked = mask_char * len(matched_text)
            else:
                masked = f"[{pii_type.upper()}_REDACTED]"

            redacted_text = redacted_text[:start] + masked + redacted_text[end:]

        return redacted_text

    def is_pii_present(self, text: str) -> bool:
        """Check if any PII is present in the text"""
        return len(self.detect_pii(text)) > 0

    def get_pii_summary(self, text: str) -> dict:
        """Get a summary of PII types and counts found in text"""
        detected_pii = self.detect_pii(text)

        summary = {}
        for pii_type, _, _, _ in detected_pii:
            summary[pii_type] = summary.get(pii_type, 0) + 1

        return summary

class ContentSanitizer:
    """
    Content sanitizer for security and safety.
    Handles input sanitization, output encoding, and security checks.
    """

    def __init__(self):
        self.pii_detector = PIIDetector()

    def sanitize_input(self, text: str) -> str:
        """
        Sanitize user input by removing potentially harmful content.

        Args:
            text: Raw user input

        Returns:
            Sanitized text
        """
        if not text:
            return ""

        # Remove null bytes and other control characters
        text = text.replace('\x00', '')
        text = text.replace('\r\n', '\n')

        # Remove excessive whitespace
        text = ' '.join(text.split())

        # Limit length to prevent DoS
        max_length = 10000
        if len(text) > max_length:
            text = text[:max_length]

        return text

    def sanitize_output(self, text: str) -> str:
        """
        Sanitize output text for safe display.

        Args:
            text: Raw output text

        Returns:
            Sanitized text safe for display
        """
        if not text:
            return ""

        # Basic HTML escaping (simplified)
        html_escape_map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;'
        }

        for char, escaped in html_escape_map.items():
            text = text.replace(char, escaped)

        return text

    def remove_pii_from_text(self, text: str) -> str:
        """Remove PII from text for privacy"""
        return self.pii_detector.redact_pii(text)

    def check_for_sensitive_content(self, text: str) -> dict:
        """
        Check for sensitive content patterns.

        Returns:
            Dictionary with flags for different types of sensitive content
        """
        checks = {
            'has_pii': self.pii_detector.is_pii_present(text),
            'has_sql_keywords': self._check_sql_keywords(text),
            'has_script_tags': self._check_script_tags(text),
            'has_command_injection': self._check_command_injection(text)
        }

        return checks

    def _check_sql_keywords(self, text: str) -> bool:
        """Check for SQL injection keywords"""
        sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'UNION', 'OR', 'AND']
        lowered = text.lower()
        return any(keyword in lowered for keyword in sql_keywords)

    def _check_script_tags(self, text: str) -> bool:
        """Check for script tags or HTML"""
        script_patterns = ['<script', '</script>', 'javascript:', 'onerror=', 'onload=']
        lowered = text.lower()
        return any(pattern in lowered for pattern in script_patterns)

    def _check_command_injection(self, text: str) -> bool:
        """Check for command injection patterns"""
        command_patterns = [';', '|', '&', '&&', '||', '`', '$(', 'nc ', 'wget ']
        return any(pattern in text for pattern in command_patterns)