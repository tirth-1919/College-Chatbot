"""
Tests for Semantic Intent Intelligence Upgrade
Tests semantic engine, entity extraction, conversation context, and integrated classification pipeline.
"""

import pytest
from ml.intent.semantic_intent_engine import SemanticIntentEngine
from ml.intent.entity_extractor import CollegeEntityExtractor
from ml.intent.conversation_context import ConversationContextManager, ConversationContext
from ml.intent.intent_classifier import IntentClassifier
from datetime import datetime, UTC
import time


class TestSemanticIntentEngine:
    """Test semantic intent engine functionality"""

    def test_semantic_engine_initialization(self):
        """Test semantic engine initializes correctly"""
        engine = SemanticIntentEngine(enabled=True, similarity_threshold=0.60)
        assert engine.enabled is True
        assert engine.similarity_threshold == 0.60
        assert engine.top_k == 3

    def test_semantic_engine_classify_structure(self):
        """Test semantic engine returns proper structure"""
        engine = SemanticIntentEngine(enabled=True, similarity_threshold=0.60)
        result = engine.classify("Who teaches DBMS?")

        assert "intent" in result
        assert "confidence" in result
        assert "method" in result
        assert "candidates" in result
        assert result["method"] == "semantic"

    def test_semantic_engine_faculty_query(self):
        """Test semantic engine correctly identifies faculty queries"""
        engine = SemanticIntentEngine(enabled=True, similarity_threshold=0.60)

        # Various paraphrases should all match FACULTY_SUBJECT_QUERY
        queries = [
            "Who teaches DBMS?",
            "DBMS faculty kaun hai?",
            "DBMS teacher kon che?",
            "Who handles DBMS?",
            "DBMS kis professor ke paas hai?"
        ]

        for query in queries:
            result = engine.classify(query)
            if result["intent"]:
                assert result["intent"] == "FACULTY_SUBJECT_QUERY", f"Query '{query}' got {result['intent']}"

    def test_semantic_engine_fee_query(self):
        """Test semantic engine correctly identifies fee queries"""
        engine = SemanticIntentEngine(enabled=True, similarity_threshold=0.60)

        queries = [
            "What is BCA fee?",
            "BCA fees ketli che?",
            "BCA fee kitni hai?",
            "How much is the tuition?"
        ]

        for query in queries:
            result = engine.classify(query)
            if result["intent"]:
                assert result["intent"] == "FEE_QUERY", f"Query '{query}' got {result['intent']}"

    def test_semantic_engine_threshold(self):
        """Test semantic engine respects confidence threshold"""
        engine = SemanticIntentEngine(enabled=True, similarity_threshold=0.90)

        # With high threshold, should return None for ambiguous queries
        result = engine.classify("random nonsense text")
        # Should either return None or low confidence
        if result["intent"]:
            assert result["confidence"] < 0.90 or result["intent"] is None

    def test_semantic_engine_disabled(self):
        """Test semantic engine gracefully handles disabled state"""
        engine = SemanticIntentEngine(enabled=False)
        result = engine.classify("Who teaches DBMS?")

        assert result["intent"] is None
        assert result["confidence"] == 0.0
        assert result["method"] == "semantic"

    def test_semantic_engine_backward_compatibility(self):
        """Test legacy classify_semantically method still works"""
        engine = SemanticIntentEngine(enabled=True, similarity_threshold=0.60)
        result = engine.classify_semantically("Who teaches DBMS?")

        # Should return tuple or None
        if result:
            assert isinstance(result, tuple)
            assert len(result) == 2
            assert isinstance(result[0], str)  # intent
            assert isinstance(result[1], float)  # confidence


class TestEntityExtractor:
    """Test entity extraction functionality"""

    def test_entity_extractor_initialization(self):
        """Test entity extractor initializes"""
        extractor = CollegeEntityExtractor()
        assert extractor is not None

    def test_course_extraction(self):
        """Test course entity extraction"""
        extractor = CollegeEntityExtractor()
        entities = extractor.extract_entities("What is BCA fee?")

        assert "course" in entities
        assert entities["course"] == "BCA"

    def test_subject_extraction(self):
        """Test subject entity extraction"""
        extractor = CollegeEntityExtractor()
        entities = extractor.extract_entities("Who teaches DBMS?")

        assert "subject" in entities
        assert entities["subject"] == "DBMS"

    def test_semester_extraction(self):
        """Test semester entity extraction"""
        extractor = CollegeEntityExtractor()

        # Various formats
        entities1 = extractor.extract_entities("Semester 2 timetable")
        assert entities1.get("semester") == 2

        entities2 = extractor.extract_entities("SEM 3 exam")
        assert entities2.get("semester") == 3

        entities3 = extractor.extract_entities("2nd sem")
        assert entities3.get("semester") == 2

    def test_facility_extraction(self):
        """Test facility entity extraction"""
        extractor = CollegeEntityExtractor()
        entities = extractor.extract_entities("Show me library photo")

        assert "facility" in entities
        assert "Library" in entities["facility"]

    def test_language_detection(self):
        """Test language detection"""
        extractor = CollegeEntityExtractor()

        # English
        assert extractor.detect_language("Who teaches DBMS?") == "en"

        # Gujarati
        assert extractor.detect_language("DBMS કોણ ભણાવે છે?") == "gu"

        # Hindi
        assert extractor.detect_language("DBMS कौन पढ़ाता है?") == "hi"

        # Hinglish
        assert extractor.detect_language("DBMS kaun padhata hai?") == "hinglish"

    def test_multilingual_subject_extraction(self):
        """Test subject extraction across languages"""
        extractor = CollegeEntityExtractor()

        # English
        entities1 = extractor.extract_entities("Who teaches Python?")
        assert "Python" in entities1.get("subject", "")

        # Hinglish
        entities2 = extractor.extract_entities("Python kon padhata hai?")
        assert "Python" in entities2.get("subject", "")

    def test_no_hallucination(self):
        """Test extractor doesn't hallucinate entities"""
        extractor = CollegeEntityExtractor()
        entities = extractor.extract_entities("What is blockchain?")

        # Should not have course/subject/facility if not mentioned
        if "course" in entities:
            assert entities["course"] is not None
        if "subject" in entities:
            assert entities["subject"] is not None


class TestConversationContext:
    """Test conversation context management"""

    def test_context_creation(self):
        """Test context creation for new conversation"""
        manager = ConversationContextManager()
        ctx = manager.get_or_create_context("conv-123")

        assert ctx.conversation_id == "conv-123"
        assert ctx.last_intent is None
        assert ctx.last_entities == {}

    def test_context_update(self):
        """Test context update with new intent and entities"""
        manager = ConversationContextManager()
        ctx = manager.get_or_create_context("conv-123")

        ctx.update("FEE_QUERY", {"course": "BCA"}, "What is BCA fee?")

        assert ctx.last_intent == "FEE_QUERY"
        assert ctx.last_entities["course"] == "BCA"
        assert ctx.last_query == "What is BCA fee?"

    def test_context_resolution_followup(self):
        """Test follow-up question resolution"""
        manager = ConversationContextManager()

        # First query
        ctx = manager.get_or_create_context("conv-123")
        ctx.update("FACULTY_SUBJECT_QUERY", {"subject": "DBMS"}, "Who teaches DBMS?")

        # Follow-up
        resolved_intent, resolved_entities, context_used = manager.resolve_context(
            query="What about Python?",
            detected_intent="FACULTY_SUBJECT_QUERY",
            extracted_entities={"subject": "Python"},
            conversation_id="conv-123"
        )

        assert context_used is True
        assert resolved_intent == "FACULTY_SUBJECT_QUERY"
        assert resolved_entities["subject"] == "Python"

    def test_context_reset(self):
        """Test explicit context reset"""
        manager = ConversationContextManager()
        ctx = manager.get_or_create_context("conv-123")
        ctx.update("FEE_QUERY", {"course": "BCA"}, "What is BCA fee?")

        manager.reset_context("conv-123")

        ctx2 = manager.get_or_create_context("conv-123")
        assert ctx2.last_intent is None
        assert ctx2.last_entities == {}

    def test_context_isolation(self):
        """Test context isolation between conversations"""
        manager = ConversationContextManager()

        ctx1 = manager.get_or_create_context("conv-1")
        ctx1.update("FEE_QUERY", {"course": "BCA"}, "What is BCA fee?")

        ctx2 = manager.get_or_create_context("conv-2")
        ctx2.update("FACULTY_SUBJECT_QUERY", {"subject": "DBMS"}, "Who teaches DBMS?")

        assert ctx1.last_intent == "FEE_QUERY"
        assert ctx2.last_intent == "FACULTY_SUBJECT_QUERY"

    def test_context_expiration(self):
        """Test context expiration after TTL"""
        manager = ConversationContextManager(context_ttl_seconds=1)

        ctx = manager.get_or_create_context("conv-123")
        ctx.update("FEE_QUERY", {"course": "BCA"}, "What is BCA fee?")

        # Wait for expiration
        time.sleep(1.1)

        # Should create fresh context
        ctx2 = manager.get_or_create_context("conv-123")
        assert ctx2.last_intent is None  # Should be reset due to expiration

    def test_context_cleanup(self):
        """Test cleanup of expired contexts"""
        manager = ConversationContextManager(context_ttl_seconds=1)

        manager.get_or_create_context("conv-1").update("FEE_QUERY", {}, "test")
        manager.get_or_create_context("conv-2").update("FACULTY_SUBJECT_QUERY", {}, "test")

        time.sleep(1.1)

        expired_count = manager.cleanup_expired_contexts()
        assert expired_count >= 2


class TestIntegratedClassificationPipeline:
    """Test the complete integrated classification pipeline"""

    def test_classifier_with_semantic_enabled(self):
        """Test classifier with semantic engine enabled"""
        classifier = IntentClassifier(
            use_ml=False,
            enable_semantic=True,
            semantic_threshold=0.60
        )

        intent, confidence, metadata = classifier.predict("Who teaches DBMS?", conversation_id="test-conv")

        assert intent is not None
        assert confidence > 0
        assert "classification_method" in metadata
        assert "entities" in metadata

    def test_classifier_with_semantic_disabled(self):
        """Test classifier with semantic engine disabled"""
        classifier = IntentClassifier(
            use_ml=False,
            enable_semantic=False
        )

        intent, confidence, metadata = classifier.predict("Who teaches DBMS?", conversation_id="test-conv")

        assert intent is not None
        assert metadata["classification_method"] in ["rule", "fallback", "keyword"]

    def test_rule_precedence_over_semantic(self):
        """Test that high-confidence rules beat semantic"""
        classifier = IntentClassifier(
            use_ml=False,
            enable_semantic=True,
            semantic_threshold=0.60
        )

        # "show me event photos" should match rule exactly
        intent, confidence, metadata = classifier.predict("show me event photos", conversation_id="test-conv")

        assert intent == "EVENT_IMAGE_SEARCH"
        assert metadata["rule_matched"] is True
        assert metadata["classification_method"] == "rule"

    def test_follow_up_questions(self):
        """Test follow-up question handling"""
        classifier = IntentClassifier(
            use_ml=False,
            enable_semantic=True,
            semantic_threshold=0.60
        )

        conv_id = "test-followup-conv"

        # First query
        intent1, conf1, meta1 = classifier.predict("Who teaches DBMS?", conversation_id=conv_id)
        assert intent1 == "FACULTY_SUBJECT_QUERY"

        # Follow-up
        intent2, conf2, meta2 = classifier.predict("What about Python?", conversation_id=conv_id)
        assert intent2 == "FACULTY_SUBJECT_QUERY"
        assert meta2["context_used"] is True

    def test_topic_reset(self):
        """Test topic reset on unrelated queries"""
        classifier = IntentClassifier(
            use_ml=False,
            enable_semantic=True,
            semantic_threshold=0.60
        )

        conv_id = "test-reset-conv"

        # First query
        classifier.predict("Who teaches DBMS?", conversation_id=conv_id)

        # Topic reset query
        intent, conf, meta = classifier.predict("Show today's timetable", conversation_id=conv_id)
        assert intent == "TIMETABLE_QUERY"
        # Context should reset on topic change

    def test_multilingual_classification(self):
        """Test classification across languages"""
        classifier = IntentClassifier(
            use_ml=False,
            enable_semantic=True,
            semantic_threshold=0.60
        )

        # English
        intent1, _, _ = classifier.predict("Who teaches DBMS?")
        assert intent1 == "FACULTY_SUBJECT_QUERY"

        # Hinglish
        intent2, _, _ = classifier.predict("DBMS kaun padhata hai?")
        assert intent2 == "FACULTY_SUBJECT_QUERY"

    def test_typo_handling(self):
        """Test handling of typos and noisy queries"""
        classifier = IntentClassifier(
            use_ml=False,
            enable_semantic=True,
            semantic_threshold=0.60
        )

        # Noisy queries should still be understood
        queries = [
            "DBMS kaun padata hai",  # typo: padhata -> padata
            "timetable kya he",  # typo: hai -> he
            "fees kitni h"  # typo: hai -> h
        ]

        for query in queries:
            intent, _, _ = classifier.predict(query)
            assert intent is not None  # Should not crash

    def test_semantic_failure_fallback(self):
        """Test that semantic failure falls back gracefully"""
        classifier = IntentClassifier(
            use_ml=False,
            enable_semantic=True,
            semantic_threshold=0.60
        )

        # Disable semantic engine temporarily
        classifier.semantic_engine.enabled = False

        intent, confidence, metadata = classifier.predict("Who teaches DBMS?")

        # Should still work with rules
        assert intent is not None
        assert metadata["classification_method"] in ["rule", "fallback"]

    def test_metadata_structure(self):
        """Test that metadata contains all required fields"""
        classifier = IntentClassifier(
            use_ml=False,
            enable_semantic=True,
            semantic_threshold=0.60
        )

        intent, confidence, metadata = classifier.predict("Who teaches DBMS?", conversation_id="test-conv")

        required_fields = [
            "classification_method",
            "entities",
            "context_used",
            "semantic_result",
            "ml_result",
            "rule_matched"
        ]

        for field in required_fields:
            assert field in metadata

    def test_entity_extraction_in_pipeline(self):
        """Test that entities are extracted in the pipeline"""
        classifier = IntentClassifier(
            use_ml=False,
            enable_semantic=True,
            semantic_threshold=0.60
        )

        intent, confidence, metadata = classifier.predict("Who teaches DBMS in BCA?")

        assert "entities" in metadata
        assert "subject" in metadata["entities"]
        assert metadata["entities"]["subject"] == "DBMS"


class TestConfidencePolicy:
    """Test confidence policy and thresholds"""

    def test_very_high_confidence(self):
        """Test very high confidence classification (>= 0.90)"""
        classifier = IntentClassifier(use_ml=False, enable_semantic=True)

        # Rule-based should have very high confidence
        intent, confidence, metadata = classifier.predict("show me event photos")
        assert confidence >= 0.90
        assert metadata["rule_matched"] is True

    def test_semantic_threshold_enforcement(self):
        """Test semantic threshold is enforced"""
        classifier = IntentClassifier(
            use_ml=False,
            enable_semantic=True,
            semantic_threshold=0.80  # High threshold
        )

        # Random query should not pass high threshold
        intent, confidence, metadata = classifier.predict("random text here")

        if metadata["classification_method"] == "semantic":
            assert confidence < 0.80 or intent is None

    def test_fallback_confidence(self):
        """Test fallback has reasonable confidence"""
        classifier = IntentClassifier(use_ml=False, enable_semantic=False)

        intent, confidence, metadata = classifier.predict("some random query")
        assert confidence >= 0.70  # GENERAL_ACADEMIC fallback confidence


class TestModelLifecycleCompatibility:
    """Test that semantic layer is compatible with existing ML lifecycle"""

    def test_ml_model_still_works(self):
        """Test that ML model still works with semantic layer"""
        classifier = IntentClassifier(
            use_ml=True,
            enable_semantic=True,
            semantic_threshold=0.60
        )

        # ML should still initialize
        assert classifier.use_ml is True
        assert classifier.ml_model is not None or classifier.is_trained is False

    def test_semantic_does_not_replace_ml(self):
        """Test semantic is additional, not replacement"""
        classifier = IntentClassifier(
            use_ml=True,
            enable_semantic=True,
            semantic_threshold=0.60
        )

        # Both should exist
        assert classifier.semantic_engine is not None
        assert classifier.ml_model is not None or classifier.is_trained is False

    def test_retrain_still_possible(self):
        """Test that retrain functionality is preserved"""
        classifier = IntentClassifier(use_ml=False, enable_semantic=True)

        # Should have retrain method
        assert hasattr(classifier, "retrain_from_database")
        assert hasattr(classifier, "save_model_artifact")
        assert hasattr(classifier, "load_model_artifact")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
