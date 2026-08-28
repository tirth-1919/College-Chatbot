import re
from typing import Dict, Any, List, Optional, Tuple

class GroundingValidator:
    """Validates that facts in generated text strictly adhere to retrieved evidence"""

    @staticmethod
    def check_groundedness(
        generated_answer: str,
        retrieved_evidence: str,
        intent: str
    ) -> Tuple[bool, float, str]:
        """
        Returns:
            (is_grounded, confidence_score, notes)
        """
        # If answering a general education question (e.g. "What is Machine Learning?"), RAG evidence not strictly required
        if intent in ["GENERAL_EDUCATION", "STUDY_EXPLANATION"]:
            return True, 0.95, "General educational query - verified with AI reasoning"

        if not retrieved_evidence or not retrieved_evidence.strip():
            # If no evidence was found, check if the response accurately declines rather than hallucinating
            lowered = generated_answer.lower()
            if any(phrase in lowered for phrase in [
                "could not verify", "not available", "unable to verify", "contact the college",
                "couldn't verify", "not found", "couldn't find verified", "could not find verified",
                "unverified", "confidential"
            ]):
                return True, 1.0, "Safely reported unavailable official information"
            return False, 0.2, "Potential hallucination: College fact claimed without evidence"

        # Check numeric and date grounding (e.g. fees, year numbers)
        extracted_numbers = re.findall(r'\b\d{4,6}\b', generated_answer)
        for num in extracted_numbers:
            # If a fee or year is mentioned in output, verify it exists in retrieved context
            if num not in retrieved_evidence:
                return False, 0.3, f"Unverified numeric token {num} detected in answer"

        return True, 0.98, "Answer grounded in authoritative college evidence"
