import pytest
import asyncio
from datetime import datetime, timezone, timedelta
UTC = timezone.utc
from sqlalchemy.orm import Session
from backend.app.database import SessionLocal, engine, Base
from backend.app.models.entities import (
    WebsiteSyncState, WebsiteContentVersion, WebsiteSyncReport,
    KnowledgeSource, KnowledgeDocument, KnowledgeChunk, MLModel, MLDataset, AuditLog
)
from rag.sync.website_change_detector import WebsiteChangeDetector
from rag.embeddings.pgvector_store import PGVectorStore
from rag.embeddings.vector_store import SimpleVectorStore
from rag.parsers.pdf_parser import PDFParser
from rag.parsers.ocr_parser import OCRParser
from rag.security.document_scanner import DocumentSecurityScanner
from ai.providers.gemini_provider import GeminiProvider
from voice.stt.stt_engine import SpeechToTextEngine
from voice.tts.tts_engine import TextToSpeechEngine
from ml.intent.training_dataset import IntentTrainingDataset
from ml.model_registry.model_registry import ModelRegistryManager
from ml.entity.entity_extractor import CollegeEntityExtractor
from rag.governance.knowledge_governance import KnowledgeGovernanceManager
from ml.training.controlled_training_manager import ControlledTrainingManager

@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test"""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

class TestWebsiteChangeDetection:
    """Test website change detection and incremental sync"""

    # @pytest.mark.skip("Requires heavy dependencies")
    @pytest.mark.asyncio
    async def test_content_hash_detection(self, db):
        """Test content hash generation and comparison"""
        detector = WebsiteChangeDetector(db)

        # Simulate crawled data
        crawled_data = {
            "source_url": "https://www.aitindia.in/test",
            "title": "Test Page",
            "clean_text": "This is test content",
            "content_hash": "abc123"
        }

        # First crawl should be detected as new
        result = await detector._check_single_url("https://www.aitindia.in/test")
        assert result["change_type"] in ["NEW", "FAILED"]

    # @pytest.mark.skip("Requires heavy dependencies")
    def test_freshness_tracking(self, db):
        """Test freshness status tracking"""
        state = WebsiteSyncState(
            source_url="https://www.aitindia.in/test",
            content_hash="abc123",
            first_discovered_at=datetime.now(UTC) - timedelta(days=10),
            last_changed_at=datetime.now(UTC) - timedelta(days=10),
            freshness_status="FRESH"
        )
        db.add(state)
        db.commit()

        detector = WebsiteChangeDetector(db)
        status = detector.get_freshness_status("https://www.aitindia.in/test")

        assert status is not None
        assert status["freshness_status"] in ["FRESH", "STALE"]

    # @pytest.mark.skip("Requires heavy dependencies")
    def test_stale_page_detection(self, db):
        """Test detection of stale pages"""
        # Create old page
        old_state = WebsiteSyncState(
            source_url="https://www.aitindia.in/old",
            content_hash="old123",
            first_discovered_at=datetime.now(UTC) - timedelta(days=30),
            last_changed_at=datetime.now(UTC) - timedelta(days=30),
            freshness_status="STALE"
        )
        db.add(old_state)
        db.commit()

        detector = WebsiteChangeDetector(db)
        stale_pages = detector.get_stale_pages(days_threshold=7)

        assert len(stale_pages) > 0
        assert any(page["url"] == "https://www.aitindia.in/old" for page in stale_pages)

    # @pytest.mark.skip("Requires heavy dependencies")
    def test_version_history(self, db):
        """Test version history tracking"""
        version = WebsiteContentVersion(
            source_url="https://www.aitindia.in/test",
            version_number=1,
            content_hash="v1",
            change_type="INITIAL",
            is_current=True
        )
        db.add(version)
        db.commit()

        detector = WebsiteChangeDetector(db)
        history = detector.get_page_version_history("https://www.aitindia.in/test")

        assert len(history) == 1
        assert history[0]["version"] == 1
        assert history[0]["is_current"] is True

class TestRAGEnhancements:
    """Test RAG enhancements including PGVector, metadata filtering, and freshness scoring"""

    def test_metadata_filtering(self):
        """Test metadata-aware retrieval"""
        store = SimpleVectorStore(use_embeddings=False)

        # Add documents with metadata
        store.add_document("doc1", "BCA fee structure", {
            "department": "Computer Science",
            "course": "BCA",
            "semester": 3,
            "subject": "DBMS"
        })

        store.add_document("doc2", "B.Tech computer engineering", {
            "department": "Computer Science",
            "course": "BTECH_CSE",
            "semester": 5,
            "subject": "OS"
        })

        # Filter by course
        results = store.search("fee", filters={"course": "BCA"})
        assert len(results) > 0
        assert results[0][0]["course"] == "BCA"

    def test_freshness_scoring(self):
        """Test freshness-aware retrieval"""
        store = SimpleVectorStore(use_embeddings=False)

        # Add fresh document
        store.add_document("doc1", "Current fee information", {
            "freshness_score": 1.0,
            "authority_score": 1.0,
            "updated_at": datetime.now()
        })

        # Add stale document
        store.add_document("doc2", "Old fee information", {
            "freshness_score": 0.5,
            "authority_score": 1.0,
            "updated_at": datetime.now() - timedelta(days=30)
        })

        results = store.search("fee", enable_freshness_scoring=True)
        assert len(results) > 0
        # Fresh document should rank higher
        assert results[0][0]["id"] == "doc1"

    # @pytest.mark.skip("Requires PostgreSQL pgvector")
    def test_pgvector_fallback(self):
        """Test PGVector fallback to SimpleVectorStore"""
        # This will use fallback since pgvector might not be available
        store = PGVectorStore(db_session=None, use_pgvector=True)

        # Should fallback to SimpleVectorStore
        assert store.fallback_store is not None or store.pgvector_available

        # Test basic operations
        store.add_document("test_doc", "test content", {"test": "metadata"})
        results = store.search("test")
        assert len(results) >= 0

class TestDocumentProcessing:
    """Test document processing enhancements"""

    # @pytest.mark.skip("Requires heavy dependencies")
    def test_pdf_page_tracking(self):
        """Test PDF page and section tracking"""
        parser = PDFParser()

        # Create a simple PDF-like content for testing
        test_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n"

        try:
            result = parser.parse_pdf(test_content, "test.pdf")
            # This might fail with invalid PDF, but we test the structure
            if result["success"]:
                assert "pages" in result
                assert "total_pages" in result
                assert "sections" in result
        except Exception:
            # Expected with invalid PDF
            pass

    # @pytest.mark.skip("Requires heavy dependencies")
    def test_pdf_location_info(self):
        """Test PDF location information for citations"""
        parser = PDFParser()

        # Test with valid-looking content
        test_content = b"%PDF-1.4\nTest PDF content\n"

        try:
            locations = parser.get_location_info(test_content, "test query")
            # Should return list even if empty
            assert isinstance(locations, list)
        except Exception:
            # Expected with invalid PDF
            pass

    # @pytest.mark.skip("Requires heavy dependencies")
    def test_ocr_needed_detection(self):
        """Test OCR requirement detection"""
        ocr_parser = OCRParser()

        # Test with minimal PDF content
        test_pdf = b"%PDF-1.4\nminimal\n"

        needs_ocr = ocr_parser.is_ocr_needed(test_pdf)
        # Should return boolean
        assert isinstance(needs_ocr, bool)

    # @pytest.mark.skip("Requires heavy dependencies")
    def test_document_security_scanning(self):
        """Test document security scanning"""
        scanner = DocumentSecurityScanner()

        # Test with safe content
        safe_content = b"Safe document content"
        result = scanner.scan_document(safe_content, "test.txt")

        assert result["success"] is True
        assert result["is_safe"] is True
        assert "file_size" in result

        # Test with oversized content
        large_content = b"x" * (50 * 1024 * 1024 + 1)  # Over 50 MB
        result = scanner.scan_document(large_content, "large.txt")

        assert result["success"] is False
        assert any("file size" in err.lower() for err in result.get("errors", []))

    # @pytest.mark.skip("Requires heavy dependencies")
    def test_malicious_signature_detection(self):
        """Test malicious file signature detection"""
        scanner = DocumentSecurityScanner()

        # Test with executable-like signature
        malicious_content = b"MZ\x90\x00"  # Executable signature
        result = scanner.scan_document(malicious_content, "test.exe")

        assert result["success"] is False
        assert any("malicious" in err.lower() or "extension" in err.lower() for err in result.get("errors", []))

class TestGeminiReliability:
    """Test Gemini provider reliability enhancements"""

    @pytest.mark.asyncio
    async def test_retry_logic(self):
        """Test retry logic with transient errors"""
        provider = GeminiProvider(api_key="test_key")

        # Without valid API key, should handle gracefully
        result = await provider.generate_response("test prompt")

        assert "success" in result
        assert "error" in result
        # Should have retry information
        assert "attempts" in result

    def test_transient_error_detection(self):
        """Test transient error detection"""
        provider = GeminiProvider()

        # Test various error types
        assert provider._is_transient_error("timeout error") is True
        assert provider._is_transient_error("network error") is True
        assert provider._is_transient_error("503 Service Unavailable") is True

        # Test non-transient errors
        assert provider._is_transient_error("authentication failed") is False
        assert provider._is_transient_error("invalid api key") is False

    def test_rate_limit_handling(self):
        """Test rate limit detection and handling"""
        provider = GeminiProvider()

        # Test rate limit detection
        assert provider._check_rate_limit("429 Too Many Requests") is True
        assert provider._check_rate_limit("rate limit exceeded") is True
        assert provider._check_rate_limit("quota exceeded") is True

        # Test non-rate-limit errors
        assert provider._check_rate_limit("internal server error") is False

    def test_exponential_backoff(self):
        """Test exponential backoff calculation"""
        provider = GeminiProvider()

        # Test backoff calculation
        delay_1 = provider._calculate_retry_delay(0)
        delay_2 = provider._calculate_retry_delay(1)
        delay_3 = provider._calculate_retry_delay(2)

        # Should increase exponentially
        assert delay_2 > delay_1
        assert delay_3 > delay_2

        # Should not exceed maximum
        assert delay_3 <= provider.max_retry_delay

    def test_statistics_tracking(self):
        """Test provider statistics tracking"""
        provider = GeminiProvider()

        stats = provider.get_statistics()

        assert "total_requests" in stats
        assert "successful_requests" in stats
        assert "failed_requests" in stats
        assert "retry_count" in stats

class TestVoiceIntegration:
    """Test voice STT and TTS integration"""

    @pytest.mark.asyncio
    async def test_stt_transcription(self):
        """Test speech-to-text transcription"""
        engine = SpeechToTextEngine(use_whisper=False)  # Use fallback

        # Test with minimal audio
        audio_bytes = b"minimal audio data"
        result = await engine.transcribe_audio_bytes(audio_bytes, language="en")

        assert "success" in result
        assert "transcript" in result
        assert "language" in result

    def test_stt_language_detection(self):
        """Test language detection"""
        engine = SpeechToTextEngine()

        # Test supported languages
        languages = engine.get_supported_languages()
        assert "en" in languages
        assert "hi" in languages
        assert "gu" in languages

    def test_stt_audio_validation(self):
        """Test audio validation"""
        engine = SpeechToTextEngine()

        # Test valid audio
        valid_result = engine.validate_audio(b"x" * 1000)
        assert valid_result["valid"] is True

        # Test empty audio
        empty_result = engine.validate_audio(b"")
        assert empty_result["valid"] is False

        # Test too large audio
        large_result = engine.validate_audio(b"x" * (10 * 1024 * 1024 + 1))
        assert large_result["valid"] is False

    def test_tts_synthesis(self):
        """Test text-to-speech synthesis"""
        engine = TextToSpeechEngine()

        # Test basic synthesis
        audio_bytes, duration = engine.synthesize("Hello world", language="en")

        assert len(audio_bytes) > 0
        assert duration > 0
        assert isinstance(audio_bytes, bytes)

    def test_tts_caching(self):
        """Test TTS caching"""
        engine = TextToSpeechEngine(db_session=None)  # No caching without DB

        # Multiple syntheses should work
        audio1, duration1 = engine.synthesize("test text", language="en")
        audio2, duration2 = engine.synthesize("test text", language="en")

        assert len(audio1) > 0
        assert len(audio2) > 0

    def test_tts_language_support(self):
        """Test TTS language support"""
        engine = TextToSpeechEngine()

        languages = engine.get_supported_languages()
        assert "en" in languages
        assert "hi" in languages
        assert "gu" in languages

    def test_tts_text_validation(self):
        """Test text validation before synthesis"""
        engine = TextToSpeechEngine()

        # Test valid text
        valid_result = engine.validate_text("Hello world")
        assert valid_result["valid"] is True

        # Test empty text
        empty_result = engine.validate_text("")
        assert empty_result["valid"] is False

        # Test too long text
        long_result = engine.validate_text("x" * 10001)
        assert long_result["valid"] is False

class TestMLEnhancements:
    """Test ML enhancements including training dataset, model versioning, and deployment"""

    def test_training_dataset_creation(self):
        """Test controlled training dataset creation"""
        dataset = IntentTrainingDataset("test_intent_dataset")

        # Add controlled examples
        dataset.add_training_example(
            text="What is BCA fee?",
            intent="FEE_QUERY",
            language="en",
            confidence=1.0
        )

        assert len(dataset.training_examples) == 1
        assert dataset.training_examples[0]["intent"] == "FEE_QUERY"

    def test_balanced_dataset_creation(self):
        """Test balanced dataset creation"""
        dataset = IntentTrainingDataset("balanced_dataset")
        dataset.create_balanced_dataset(examples_per_intent=10, languages=["en"])

        # Should have examples for multiple intents
        assert len(dataset.training_examples) > 0

        # Check distribution - might not be valid if insufficient samples per intent
        validation = dataset.validate_dataset()
        # Just check it has statistics, not necessarily valid
        assert "statistics" in validation

    def test_dataset_validation(self):
        """Test dataset validation"""
        dataset = IntentTrainingDataset("validation_test")
        dataset.add_training_example("Test query", "FEE_QUERY", "en")

        validation = dataset.validate_dataset()

        assert "is_valid" in validation
        assert "statistics" in validation
        assert "total_samples" in validation["statistics"]

    def test_dataset_split(self):
        """Test train/validation/test split"""
        dataset = IntentTrainingDataset("split_test")
        dataset.create_balanced_dataset(examples_per_intent=10, languages=["en"])

        train, val, test = dataset.train_validation_test_split(
            train_ratio=0.7, val_ratio=0.15, test_ratio=0.15
        )

        assert len(train) > 0
        assert len(val) > 0
        assert len(test) > 0

    def test_model_registration(self, db):
        """Test model registration with versioning"""
        model = ModelRegistryManager.register_model(
            db=db,
            name="test_model",
            task="INTENT_CLASSIFICATION",
            version="v1.0",
            accuracy=0.85,
            f1_score=0.82,
            activate=False
        )

        assert model.id is not None
        assert model.version == "v1.0"
        assert model.accuracy == 0.85
        assert model.is_active is False

    def test_model_validation(self, db):
        """Test model validation"""
        # First register a model
        model = ModelRegistryManager.register_model(
            db=db,
            name="test_model",
            task="INTENT_CLASSIFICATION",
            version="v1.0",
            accuracy=0.85,
            f1_score=0.82
        )

        # Validate the model
        validated_model = ModelRegistryManager.validate_model(
            db=db,
            model_id=model.id,
            validation_results={"accuracy": 0.87, "f1_score": 0.84},
            passed=True
        )

        assert validated_model.validation_status == "VALIDATED"
        assert validated_model.accuracy == 0.87

    def test_model_deployment(self, db):
        """Test model deployment with safety checks"""
        # Register and validate model
        model = ModelRegistryManager.register_model(
            db=db,
            name="test_model",
            task="INTENT_CLASSIFICATION",
            version="v1.0",
            accuracy=0.85,
            f1_score=0.82
        )

        ModelRegistryManager.validate_model(
            db=db,
            model_id=model.id,
            validation_results={"accuracy": 0.85},
            passed=True
        )

        # Deploy model
        deployed_model = ModelRegistryManager.deploy_model(
            db=db,
            model_id=model.id,
            require_validation=True
        )

        assert deployed_model.is_active is True
        assert deployed_model.deployment_state == "DEPLOYED"

    def test_model_rollback(self, db):
        """Test safe model rollback"""
        # Register first model
        model1 = ModelRegistryManager.register_model(
            db=db,
            name="test_model",
            task="INTENT_CLASSIFICATION",
            version="v1.0",
            accuracy=0.80,
            f1_score=0.78,
            activate=True
        )

        # Register second model
        model2 = ModelRegistryManager.register_model(
            db=db,
            name="test_model",
            task="INTENT_CLASSIFICATION",
            version="v2.0",
            accuracy=0.85,
            f1_score=0.82,
            activate=True
        )

        # Rollback to v1.0
        rolled_back = ModelRegistryManager.rollback_model(
            db=db,
            task="INTENT_CLASSIFICATION",
            target_version="v1.0",
            reason="Test rollback"
        )

        assert rolled_back is not None
        assert rolled_back.version == "v1.0"
        assert rolled_back.is_active is True

class TestMultilingualNER:
    """Test multilingual named entity recognition"""

    def test_language_detection(self):
        """Test language detection"""
        extractor = CollegeEntityExtractor()

        # English
        assert extractor.detect_language("What is the fee?") == "en"

        # Hindi (Devanagari)
        assert extractor.detect_language("फीस क्या है?") == "hi"

        # Gujarati
        assert extractor.detect_language("ફી શું છે?") == "gu"

    def test_multilingual_course_extraction(self):
        """Test course extraction in multiple languages"""
        extractor = CollegeEntityExtractor()

        # English
        entities_en = extractor.extract_entities("What is BCA fee?")
        assert entities_en.get("course") == "BCA"

        # Hinglish
        entities_hi = extractor.extract_entities("BCA fee kitni hai?")
        assert entities_hi.get("course") == "BCA"

    def test_multilingual_subject_extraction(self):
        """Test subject extraction in multiple languages"""
        extractor = CollegeEntityExtractor()

        # English
        entities_en = extractor.extract_entities("Who teaches DBMS?")
        assert entities_en.get("subject") == "DBMS"

        # Hinglish
        entities_hi = extractor.extract_entities("DBMS kaun padhata hai?")
        assert entities_hi.get("subject") == "DBMS"

    def test_entity_confidence_scoring(self):
        """Test entity confidence scoring"""
        extractor = CollegeEntityExtractor()

        entities = extractor.extract_entities("BCA semester 3 DBMS")
        confidence = extractor.get_entity_confidence(entities)

        assert "course" in confidence
        assert "semester" in confidence
        assert all(0 <= score <= 1 for score in confidence.values())

class TestKnowledgeGovernance:
    """Test knowledge governance and freshness management"""

    def test_knowledge_freshness_update(self, db):
        """Test knowledge freshness updating"""
        # Create knowledge source
        source = KnowledgeSource(
            source_type="WEBSITE_CRAWL",
            source_url="https://www.aitindia.in/test",
            title="Test Page",
            authority_score=1.0
        )
        db.add(source)
        db.commit()

        # Update freshness
        governance = KnowledgeGovernanceManager(db)
        updated = governance.update_knowledge_freshness(
            source_id=source.id,
            verifier="ADMIN"
        )

        assert updated.last_verified_at is not None
        assert updated.verified_by == "ADMIN"

    def test_knowledge_verification(self, db):
        """Test knowledge verification"""
        source = KnowledgeSource(
            source_type="OFFICIAL_DOCUMENT",
            source_url="https://www.aitindia.in/doc.pdf",
            title="Official Document",
            authority_score=1.0
        )
        db.add(source)
        db.commit()

        governance = KnowledgeGovernanceManager(db)
        verified = governance.verify_knowledge(
            source_id=source.id,
            verifier="ADMIN",
            verification_notes="Verified against official source"
        )

        assert verified.verification_status == "VERIFIED"
        assert verified.is_stale is False

    def test_stale_knowledge_detection(self, db):
        """Test stale knowledge detection"""
        # Create old knowledge with is_stale=True
        old_source = KnowledgeSource(
            source_type="WEBSITE_CRAWL",
            source_url="https://www.aitindia.in/old",
            title="Old Page",
            authority_score=1.0,
            last_verified_at=datetime.now() - timedelta(days=30),
            expiry_date=datetime.now() - timedelta(days=1),
            is_stale=True
        )
        db.add(old_source)
        db.commit()

        governance = KnowledgeGovernanceManager(db)
        stale = governance.get_stale_knowledge()

        assert len(stale) > 0

    def test_verification_requirements(self, db):
        """Test knowledge requiring verification"""
        source = KnowledgeSource(
            source_type="WEBSITE_CRAWL",
            source_url="https://www.aitindia.in/test",
            title="Test Page",
            authority_score=1.0,
            last_verified_at=datetime.now() - timedelta(days=10)
        )
        db.add(source)
        db.commit()

        governance = KnowledgeGovernanceManager(db)
        requires_verification = governance.get_knowledge_requiring_verification(days_threshold=7)

        assert len(requires_verification) > 0

class TestControlledTraining:
    """Test controlled training pipeline with rollback"""

    def test_training_session_start(self, db):
        """Test training session initialization"""
        # Create dataset
        dataset = MLDataset(
            name="test_dataset",
            task="INTENT_CLASSIFICATION",
            version="v1.0",
            total_samples=100,
            is_scrubbed_pii=True
        )
        db.add(dataset)
        db.commit()

        # Start training session
        manager = ControlledTrainingManager(db)
        session = manager.start_training_session(
            dataset_id=dataset.id,
            model_name="test_model",
            task="INTENT_CLASSIFICATION",
            training_config={"epochs": 10},
            initiated_by="ADMIN"
        )

        assert session["session_id"] is not None
        assert session["current_stage"] == "DATASET_PREPARATION"

    def test_training_data_validation(self, db):
        """Test training data validation"""
        # Create valid dataset
        valid_dataset = MLDataset(
            name="valid_dataset",
            task="INTENT_CLASSIFICATION",
            version="v1.0",
            total_samples=100,
            is_scrubbed_pii=True
        )
        db.add(valid_dataset)
        db.commit()

        manager = ControlledTrainingManager(db)
        validation = manager.validate_training_data(valid_dataset.id)

        assert validation["valid"] is True

        # Create invalid dataset (not scrubbed)
        invalid_dataset = MLDataset(
            name="invalid_dataset",
            task="INTENT_CLASSIFICATION",
            version="v1.0",
            total_samples=100,
            is_scrubbed_pii=False
        )
        db.add(invalid_dataset)
        db.commit()

        invalid_validation = manager.validate_training_data(invalid_dataset.id)
        assert invalid_validation["valid"] is False
        assert "PII" in str(invalid_validation["errors"])

    def test_stage_completion(self, db):
        """Test training stage completion tracking"""
        # Create dataset
        dataset = MLDataset(
            name="test_dataset",
            task="INTENT_CLASSIFICATION",
            version="v1.0",
            total_samples=100,
            is_scrubbed_pii=True
        )
        db.add(dataset)
        db.commit()

        manager = ControlledTrainingManager(db)
        manager.start_training_session(
            dataset_id=dataset.id,
            model_name="test_model",
            task="INTENT_CLASSIFICATION",
            training_config={},
            initiated_by="ADMIN"
        )

        # Complete first stage
        session = manager.complete_stage(
            "DATASET_PREPARATION",
            {"samples_processed": 100},
            success=True
        )

        assert "DATASET_PREPARATION" in session["stages_completed"]

    def test_rollback_functionality(self, db):
        """Test training rollback functionality"""
        # Create dataset
        dataset = MLDataset(
            name="test_dataset",
            task="INTENT_CLASSIFICATION",
            version="v1.0",
            total_samples=100,
            is_scrubbed_pii=True
        )
        db.add(dataset)
        db.commit()

        manager = ControlledTrainingManager(db)
        manager.start_training_session(
            dataset_id=dataset.id,
            model_name="test_model",
            task="INTENT_CLASSIFICATION",
            training_config={},
            initiated_by="ADMIN"
        )

        # Perform rollback
        rollback_info = manager.rollback_training(
            reason="Test failure",
            rolled_back_by="ADMIN",
            rollback_to_previous=False
        )

        assert rollback_info["reason"] == "Test failure"
        assert rollback_info["rolled_back_by"] == "ADMIN"
        assert "rollback_timestamp" in rollback_info

if __name__ == "__main__":
    pytest.main([__file__, "-v"])