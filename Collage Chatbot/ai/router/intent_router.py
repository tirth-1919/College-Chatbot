import re
from datetime import datetime, UTC
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from ai.router.source_resolver import SourceResolver

class AIRouter:
    """
    Main AI Router for AIT AI Assistant.
    Delegates to dynamic 3-Tier SourceResolver:
      1. Official AIT Website (https://www.aitindia.in)
      2. Verified AIT Database (Admin Ground Truth)
      3. Gemini AI (Anti-Hallucination Enforced)
    """
    def __init__(self, use_ml_intent: bool = True, enable_semantic: bool = True, semantic_threshold: float = 0.60, context_ttl_seconds: int = 1800):
        from backend.app.config import settings
        context_ttl_seconds = settings.SEMANTIC_CONTEXT_TTL if enable_semantic else context_ttl_seconds

        self.resolver = SourceResolver(
            use_ml_intent=use_ml_intent,
            enable_semantic=enable_semantic,
            semantic_threshold=semantic_threshold,
            context_ttl_seconds=context_ttl_seconds
        )
        self.intent_classifier = self.resolver.intent_classifier
        self.entity_extractor = self.resolver.entity_extractor
        self.gemini_provider = self.resolver.gemini_provider
        self.local_provider = self.resolver.local_provider
        self.tts_engine = self.resolver.tts_engine
        self.audio_manager = self.resolver.audio_manager
        self.content_sanitizer = self.resolver.content_sanitizer

    def detect_language(self, text: str) -> str:
        return self.resolver.detect_language(text)

    async def route_and_respond(
        self,
        db: Session,
        query: str,
        user_id: Optional[str] = None,
        role: str = "STUDENT",
        mode: str = "TEXT",
        conversation_id: Optional[str] = None,
        think: bool = False,
        tool: Optional[str] = None
    ) -> Dict[str, Any]:
        return await self.resolver.resolve_question(
            db=db,
            query=query,
            user_id=user_id,
            role=role,
            mode=mode,
            conversation_id=conversation_id,
            think=think,
            tool=tool
        )
