"""
Conversation Context Manager for AIT College AI Assistant
Tracks session-level conversational context, enables follow-up pronoun/entity resolution,
handles topic shifting, and provides ambiguity resolution without leaking PII.
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, UTC
import re
import logging

logger = logging.getLogger(__name__)

class ConversationContext:
    """Represents the active conversational state for a session"""
    def __init__(
        self,
        conversation_id: str,
        last_intent: Optional[str] = None,
        last_entities: Optional[Dict[str, Any]] = None,
        recent_topics: Optional[List[str]] = None,
        last_query: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ):
        self.conversation_id = conversation_id
        self.last_intent = last_intent
        self.last_entities = last_entities or {}
        self.recent_topics = recent_topics or []
        self.last_query = last_query
        self.timestamp = timestamp or datetime.now(UTC)

    def update(self, intent: str, entities: Dict[str, Any], query: str):
        self.last_intent = intent
        # Filter out transient / non-sticky fields
        sticky_entities = {}
        for k in ["course", "subject", "semester", "department", "event", "facility", "academic_year"]:
            if k in entities:
                sticky_entities[k] = entities[k]
        
        # Merge new entities over older ones
        self.last_entities.update(sticky_entities)
        self.last_query = query
        self.timestamp = datetime.now(UTC)
        if intent not in self.recent_topics:
            self.recent_topics.append(intent)
            if len(self.recent_topics) > 5:
                self.recent_topics.pop(0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "last_intent": self.last_intent,
            "last_entities": self.last_entities,
            "recent_topics": self.recent_topics,
            "last_query": self.last_query,
            "timestamp": self.timestamp.isoformat()
        }

class ConversationContextManager:
    """
    Manages in-memory context resolution and contextual routing.
    Enables follow-ups such as:
      User: "What is BCA fee?" -> Intent: FEE_QUERY, course: BCA
      User: "What about semester 2?" -> Intent: FEE_QUERY, course: BCA, semester: 2
      User: "Who teaches DBMS?" -> Intent: FACULTY_SUBJECT_QUERY, subject: DBMS
      User: "What about Python?" -> Intent: FACULTY_SUBJECT_QUERY, subject: Python
      User: "Show today's timetable" -> Intent: TIMETABLE_QUERY (topic reset: fee context cleared)
    """

    def __init__(self, context_ttl_seconds: int = 1800):
        self._sessions: Dict[str, ConversationContext] = {}
        self.context_ttl_seconds = context_ttl_seconds

    def get_or_create_context(self, conversation_id: str) -> ConversationContext:
        """Get existing session context or create a new one"""
        if conversation_id not in self._sessions:
            self._sessions[conversation_id] = ConversationContext(conversation_id=conversation_id)
        else:
            # Check if context has expired
            ctx = self._sessions[conversation_id]
            age_seconds = (datetime.now(UTC) - ctx.timestamp).total_seconds()
            if age_seconds > self.context_ttl_seconds:
                # Context expired, create fresh context
                self._sessions[conversation_id] = ConversationContext(conversation_id=conversation_id)
        return self._sessions[conversation_id]

    def reset_context(self, conversation_id: str):
        """Explicitly reset context for a conversation"""
        if conversation_id in self._sessions:
            del self._sessions[conversation_id]

    def cleanup_expired_contexts(self):
        """Remove all expired contexts (call periodically)"""
        current_time = datetime.now(UTC)
        expired_ids = [
            conv_id for conv_id, ctx in self._sessions.items()
            if (current_time - ctx.timestamp).total_seconds() > self.context_ttl_seconds
        ]
        for conv_id in expired_ids:
            del self._sessions[conv_id]
        return len(expired_ids)

    def resolve_context(
        self,
        query: str,
        detected_intent: str,
        extracted_entities: Dict[str, Any],
        conversation_id: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any], bool]:
        """
        Applies conversation context rules to resolve follow-ups.
        Returns: Tuple of (resolved_intent, resolved_entities, context_used_flag)
        """
        if not conversation_id or conversation_id not in self._sessions:
            # Store initial context
            if conversation_id:
                ctx = self.get_or_create_context(conversation_id)
                ctx.update(detected_intent, extracted_entities, query)
            return detected_intent, extracted_entities, False

        ctx = self._sessions[conversation_id]
        lowered = query.lower().strip()
        context_used = False
        resolved_intent = detected_intent
        resolved_entities = dict(extracted_entities)

        # Detect explicit topic resets
        topic_reset_signals = [
            "timetable", "time table", "aaj no timetable", "exam", "pariksha", "parixa",
            "result", "spi", "cpi", "photos", "photo", "images", "notice", "circular",
            "complaint", "ticket", "hi", "hello", "kem cho", "namaste"
        ]
        is_topic_reset = any(w in lowered for w in topic_reset_signals) and not any(w in lowered for w in ["what about", "and for", "how about", "and "])

        # Follow-up indicators (e.g., "what about...", "and...", "in semester 2?", "for python?")
        is_followup = any(w in lowered for w in [
            "what about", "how about", "and ", "and for", "for ", "su che", "kya hai",
            "in semester", "sem ", "semester ", "installment", "payment", "fees"
        ]) or (len(lowered.split()) <= 4 and not is_topic_reset)

        if is_followup and not is_topic_reset:
            # 1. Fee follow-ups
            if ctx.last_intent == "FEE_QUERY":
                if any(w in lowered for w in ["semester", "sem", "installment", "instalment", "terms", "scholarship", "how much", "kitna", "ketli"]) or (
                    "semester" in extracted_entities and not extracted_entities.get("course")
                ):
                    resolved_intent = "FEE_QUERY"
                    if "course" in ctx.last_entities and "course" not in resolved_entities:
                        resolved_entities["course"] = ctx.last_entities["course"]
                        context_used = True

            # 2. Faculty follow-ups
            elif ctx.last_intent == "FACULTY_SUBJECT_QUERY":
                if "subject" in extracted_entities and not any(w in lowered for w in ["exam", "syllabus", "timetable"]):
                    resolved_intent = "FACULTY_SUBJECT_QUERY"
                    context_used = True
                elif any(w in lowered for w in ["who teaches", "teacher", "professor", "faculty", "department", "office", "sir", "madam"]):
                    resolved_intent = "FACULTY_SUBJECT_QUERY"
                    if "subject" in ctx.last_entities and "subject" not in resolved_entities:
                        resolved_entities["subject"] = ctx.last_entities["subject"]
                        context_used = True

            # 3. Exam follow-ups
            elif ctx.last_intent == "EXAM_QUERY":
                if "subject" in extracted_entities and not any(w in lowered for w in ["syllabus", "who teaches", "teacher"]):
                    resolved_intent = "EXAM_QUERY"
                    if "course" in ctx.last_entities and "course" not in resolved_entities:
                        resolved_entities["course"] = ctx.last_entities["course"]
                    context_used = True
                elif any(w in lowered for w in ["when", "date", "time", "schedule", "timing", "hall"]):
                    resolved_intent = "EXAM_QUERY"
                    if "subject" in ctx.last_entities and "subject" not in resolved_entities:
                        resolved_entities["subject"] = ctx.last_entities["subject"]
                        context_used = True
                    if "course" in ctx.last_entities and "course" not in resolved_entities:
                        resolved_entities["course"] = ctx.last_entities["course"]
                        context_used = True

            # 4. General entity inheritance if query has pronouns
            if any(p in lowered for p in [" it", " it?", " this", " that", " this subject", " that course"]):
                for k in ["course", "subject", "semester", "academic_year"]:
                    if k in ctx.last_entities and k not in resolved_entities:
                        resolved_entities[k] = ctx.last_entities[k]
                        context_used = True

        # Update context state with resolved values
        ctx.update(resolved_intent, resolved_entities, query)
        return resolved_intent, resolved_entities, context_used
