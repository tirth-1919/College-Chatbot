"""
Query Rewriter for AIT College AI Assistant
Intelligently rewrites ambiguous, short, or follow-up queries for better retrieval.
Uses conversation context, entity information, and intent to generate optimized queries.
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, UTC

logger = logging.getLogger(__name__)

class QueryRewriter:
    """
    Rewrites user queries for better retrieval while preserving the original intent.
    Handles:
    - Short queries (e.g., "fees?" -> "What are the fees for BCA?")
    - Follow-up questions (e.g., "How long is it?" -> "What is the duration of BCA?")
    - Pronoun resolution (e.g., "What about Python?" -> "What about Python programming?")
    - Spelling corrections
    - Multi-intent expansion
    """

    # Common spelling corrections
    SPELLING_CORRECTIONS = {
        "admisn": "admission",
        "admisson": "admission",
        "admisson": "admission",
        "collage": "college",
        "princpal": "principal",
        "principl": "principal",
        "timetalbe": "timetable",
        "syllbus": "syllabus",
        "placment": "placement",
        "faclty": "faculty",
        "facilty": "faculty",
        "elgibility": "eligibility",
        "documnts": "documents",
        "installmnt": "installment",
        "schlorship": "scholarship",
        "canteen": "canteen",
        "hostel": "hostel",
        "librery": "library",
        "laboratry": "laboratory",
        "acadamic": "academic",
        "acadmics": "academics",
        "programe": "program",
        "progrram": "program",
        "departmnt": "department",
        "semster": "semester",
        "subjet": "subject",
        "subjec": "subject"
    }

    # Query templates for rewriting
    QUERY_TEMPLATES = {
        "FEE_QUERY": {
            "short": ["fee", "fees", "cost", "price", "amount"],
            "template": "What are the fees for {course} at Ahmedabad Institute of Technology?"
        },
        "PROGRAM_DURATION": {
            "short": ["duration", "how long", "how many year", "years", "length"],
            "template": "What is the duration of the {course} program at Ahmedabad Institute of Technology?"
        },
        "ELIGIBILITY": {
            "short": ["eligibility", "eligible", "requirements", "criteria"],
            "template": "What are the eligibility requirements for {course} admission at Ahmedabad Institute of Technology?"
        },
        "ADMISSION": {
            "short": ["admission", "admit", "join", "enroll", "registration"],
            "template": "What is the admission process for {course} at Ahmedabad Institute of Technology?"
        },
        "FACULTY_SUBJECT_QUERY": {
            "short": ["teacher", "professor", "faculty", "teaches", "instructor"],
            "template": "Who teaches {subject} at Ahmedabad Institute of Technology?"
        },
        "COURSE_SUBJECTS": {
            "short": ["subject", "subjects", "covered", "cover"],
            "template": "What subjects are covered in the {course} program at Ahmedabad Institute of Technology?"
        },
        "SYLLABUS_QUERY": {
            "short": ["syllabus", "curriculum", "course content", "topics"],
            "template": "What is the syllabus for {subject} at Ahmedabad Institute of Technology?"
        },
        "EXAM_QUERY": {
            "short": ["exam", "examination", "test", "exam date", "exam schedule"],
            "template": "When is the {subject} exam at Ahmedabad Institute of Technology?"
        },
        "TIMETABLE_QUERY": {
            "short": ["timetable", "schedule", "routine", "class time"],
            "template": "What is the timetable for {course} at Ahmedabad Institute of Technology?"
        },
        "FACILITY": {
            "short": ["facility", "facilities", "infrastructure", "campus"],
            "template": "What facilities are available at Ahmedabad Institute of Technology?"
        },
        "HOSTEL": {
            "short": ["hostel", "accommodation", "hostel facilities"],
            "template": "What hostel facilities are available at Ahmedabad Institute of Technology?"
        },
        "PRINCIPAL": {
            "short": ["principal", "head", "director"],
            "template": "Who is the principal of Ahmedabad Institute of Technology?"
        },
        "CONTACT": {
            "short": ["contact", "phone", "email", "address", "location"],
            "template": "What is the contact information for Ahmedabad Institute of Technology?"
        },
        "PLACEMENT": {
            "short": ["placement", "job", "career", "recruitment"],
            "template": "What are the placement opportunities at Ahmedabad Institute of Technology?"
        }
    }

    def __init__(self):
        pass

    def correct_spelling(self, text: str) -> str:
        """Apply spelling corrections to the query"""
        corrected = text
        for wrong, correct in self.SPELLING_CORRECTIONS.items():
            corrected = re.sub(rf"\b{re.escape(wrong)}\b", correct, corrected, flags=re.IGNORECASE)
        return corrected

    def detect_is_short_query(self, text: str, intent: str) -> bool:
        """Determine if the query is too short for effective retrieval"""
        words = text.strip().split()
        word_count = len(words)

        # Very short queries (1-2 words) often need expansion
        if word_count <= 2:
            return True

        # Single word regardless of length
        if word_count == 1:
            return True

        # Query without key entities
        # This is handled by entity extraction, but we can add heuristics
        return False

    def detect_multi_intent(self, text: str, primary_intent: str, entities: Dict[str, Any]) -> List[str]:
        """
        Detect if a query contains multiple intents
        Returns list of detected intents
        """
        lowered = text.lower()
        intents = [primary_intent]

        # Check for common multi-intent patterns
        multi_intent_patterns = {
            ("FEE_QUERY", "ELIGIBILITY"): [r"fee.*eligibility", r"eligibility.*fee", r"cost.*eligible", r"eligible.*cost"],
            ("FEE_QUERY", "SYLLABUS_QUERY"): [r"fee.*syllabus", r"syllabus.*fee"],
            ("ADMISSION", "ELIGIBILITY"): [r"admission.*eligibility", r"eligibility.*admission", r"join.*eligible"],
            ("ADMISSION", "DOCUMENTS"): [r"admission.*document", r"document.*admission", r"join.*document"],
            ("EXAM_QUERY", "SYLLABUS_QUERY"): [r"exam.*syllabus", r"syllabus.*exam"],
            ("ADMISSION", "FEE_QUERY"): [r"admission.*fee", r"fee.*admission"],
            ("SYLLABUS_QUERY", "FACULTY_SUBJECT_QUERY"): [r"syllabus.*teaches", r"teaches.*syllabus"]
        }

        for (intent1, intent2), patterns in multi_intent_patterns.items():
            if primary_intent == intent1:
                for pattern in patterns:
                    if re.search(pattern, lowered):
                        if intent2 not in intents:
                            intents.append(intent2)
                        break
            elif primary_intent == intent2:
                for pattern in patterns:
                    if re.search(pattern, lowered):
                        if intent1 not in intents:
                            intents.append(intent1)
                        break

        return intents

    def rewrite_query(
        self,
        original_query: str,
        intent: str,
        entities: Dict[str, Any],
        context_entities: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main rewrite function that generates an optimized query for retrieval.

        Returns:
            {
                "original_query": str,
                "normalized_query": str,
                "rewritten_query": str,
                "was_rewritten": bool,
                "rewrite_reason": str,
                "multi_intents": List[str],
                "confidence": float
            }
        """
        normalized = self.correct_spelling(original_query.strip())
        lowered = normalized.lower()

        # Merge context entities with current entities
        merged_entities = dict(entities)
        if context_entities:
            for k, v in context_entities.items():
                if k not in merged_entities:
                    merged_entities[k] = v

        # Detect multi-intents
        multi_intents = self.detect_multi_intent(normalized, intent, merged_entities)

        # Determine if rewrite is needed
        rewrite_needed = False
        rewrite_reason = ""
        rewritten_query = normalized

        # Course subject requests should be expanded even when colloquial wording
        # makes them longer than the normal short-query threshold.
        is_short = self.detect_is_short_query(normalized, intent)
        is_course_subject_request = intent == "COURSE_SUBJECTS"

        if (is_short or is_course_subject_request) and intent in self.QUERY_TEMPLATES:
            template_info = self.QUERY_TEMPLATES[intent]

            # Check if the query matches short form patterns
            matches_short = any(short in lowered for short in template_info["short"])

            if matches_short:
                # Use template to expand
                course = merged_entities.get("course", "BCA")
                subject = merged_entities.get("subject", "")
                facility = merged_entities.get("facility", "")

                # Select appropriate entity for template
                if intent == "FACULTY_SUBJECT_QUERY" and subject:
                    rewritten_query = template_info["template"].format(subject=subject)
                elif intent == "FACILITY" and facility:
                    rewritten_query = template_info["template"].format(facility=facility)
                else:
                    rewritten_query = template_info["template"].format(course=course)

                rewrite_needed = True
                rewrite_reason = "Short query expansion"

        # Handle pronoun resolution in follow-ups
        elif any(pronoun in lowered for pronoun in ["it", "its", "this", "that"]):
            if "course" in merged_entities:
                # Replace pronouns with course name
                rewritten_query = re.sub(
                    r"\b(it|its|this|that)\b",
                    merged_entities["course"],
                    normalized,
                    flags=re.IGNORECASE
                )
                if rewritten_query != normalized:
                    rewrite_needed = True
                    rewrite_reason = "Pronoun resolution"
            elif "subject" in merged_entities:
                rewritten_query = re.sub(
                    r"\b(it|its|this|that)\b",
                    merged_entities["subject"],
                    normalized,
                    flags=re.IGNORECASE
                )
                if rewritten_query != normalized:
                    rewrite_needed = True
                    rewrite_reason = "Pronoun resolution"

        # Handle "what about" follow-ups
        elif "what about" in lowered or "how about" in lowered:
            if "course" in merged_entities:
                # Keep the "what about" but ensure the course is mentioned
                if merged_entities["course"].lower() not in lowered:
                    rewritten_query = f"What about {merged_entities['course']}?"
                    rewrite_needed = True
                    rewrite_reason = "Entity clarification in follow-up"
            elif "subject" in merged_entities:
                if merged_entities["subject"].lower() not in lowered:
                    rewritten_query = f"What about {merged_entities['subject']}?"
                    rewrite_needed = True
                    rewrite_reason = "Entity clarification in follow-up"

        # Calculate confidence
        confidence = 0.95 if not rewrite_needed else 0.85

        # Lower confidence for complex rewrites
        if rewrite_reason == "Pronoun resolution":
            confidence = 0.90

        return {
            "original_query": original_query,
            "normalized_query": normalized,
            "rewritten_query": rewritten_query,
            "was_rewritten": rewrite_needed,
            "rewrite_reason": rewrite_reason,
            "multi_intents": multi_intents,
            "confidence": confidence,
            "entities": merged_entities
        }

    def detect_ambiguity(
        self,
        query: str,
        intent: str,
        entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Detect if a query is ambiguous and requires clarification.

        Returns:
            {
                "is_ambiguous": bool,
                "ambiguity_reason": str,
                "clarification_question": Optional[str],
                "confidence": float
            }
        """
        lowered = query.lower()

        # Check for ambiguity patterns
        ambiguous_patterns = {
            "FEE_QUERY": {
                "no_course": r"^(fee|fees|cost|price|amount|how much)\s*$",
                "clarification": "Which course's fees would you like to know about?"
            },
            "EXAM_QUERY": {
                "no_subject": r"^(exam|examination|test|exam date)\s*$",
                "clarification": "Which subject's exam are you asking about?"
            },
            "FACULTY_SUBJECT_QUERY": {
                "no_subject": r"^(who teaches|teacher|faculty|professor)\s*$",
                "clarification": "Which subject's faculty information do you need?"
            },
            "SYLLABUS_QUERY": {
                "no_subject": r"^(syllabus|curriculum|topics)\s*$",
                "clarification": "Which subject's syllabus would you like to know about?"
            }
        }

        if intent in ambiguous_patterns:
            pattern_info = ambiguous_patterns[intent]

            # Check if entity is missing
            if intent == "FEE_QUERY" and "course" not in entities:
                if re.search(pattern_info["no_course"], lowered):
                    return {
                        "is_ambiguous": True,
                        "ambiguity_reason": "Course not specified for fee query",
                        "clarification_question": pattern_info["clarification"],
                        "confidence": 0.60
                    }

            elif intent == "EXAM_QUERY" and "subject" not in entities:
                if re.search(pattern_info["no_subject"], lowered):
                    return {
                        "is_ambiguous": True,
                        "ambiguity_reason": "Subject not specified for exam query",
                        "clarification_question": pattern_info["clarification"],
                        "confidence": 0.60
                    }

            elif intent == "FACULTY_SUBJECT_QUERY" and "subject" not in entities:
                if re.search(pattern_info["no_subject"], lowered):
                    return {
                        "is_ambiguous": True,
                        "ambiguity_reason": "Subject not specified for faculty query",
                        "clarification_question": pattern_info["clarification"],
                        "confidence": 0.60
                    }

            elif intent == "SYLLABUS_QUERY" and "subject" not in entities:
                if re.search(pattern_info["no_subject"], lowered):
                    return {
                        "is_ambiguous": True,
                        "ambiguity_reason": "Subject not specified for syllabus query",
                        "clarification_question": pattern_info["clarification"],
                        "confidence": 0.60
                    }

        # Not ambiguous
        return {
            "is_ambiguous": False,
            "ambiguity_reason": "",
            "clarification_question": None,
            "confidence": 0.90
        }
