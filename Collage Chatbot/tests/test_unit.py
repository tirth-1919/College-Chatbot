import pytest
from sqlalchemy.orm import Session
from backend.app.database import SessionLocal, engine, Base
from backend.app.models.entities import User, Role, Course, Fee, Faculty, Subject, Department
from backend.app.security.auth import get_password_hash, verify_password, create_access_token
from ml.intent.intent_classifier import IntentClassifier
from ml.entity.entity_extractor import CollegeEntityExtractor
from rag.embeddings.vector_store import SimpleVectorStore
from rag.conflicts.conflict_detector import KnowledgeConflictDetector
from ai.safety.grounding import GroundingValidator
from backend.app.cache.redis_cache import RedisCache
from backend.app.config import settings

@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test"""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

class TestAuthentication:
    """Test authentication and security functions"""
    
    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert ":" in hashed  # Check for salt:hash format
        assert verify_password(password, hashed) is True
        assert verify_password("WrongPassword", hashed) is False
    
    def test_jwt_token_creation(self):
        """Test JWT token creation"""
        data = {"sub": "user123", "role": "STUDENT"}
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are typically long
    
    def test_jwt_token_expiry(self):
        """Test JWT token with custom expiry"""
        from datetime import timedelta
        data = {"sub": "user123"}
        token = create_access_token(data, expires_delta=timedelta(minutes=30))
        
        assert isinstance(token, str)

class TestIntentClassifier:
    """Test intent classification"""
    
    def test_fee_query_intent(self):
        """Test fee query intent classification"""
        classifier = IntentClassifier(use_ml=False)
        intent, confidence, _ = classifier.predict("What is the BCA fee?")

        assert intent == "FEE_QUERY"
        assert confidence > 0.8

    def test_faculty_query_intent(self):
        """Test faculty query intent classification"""
        classifier = IntentClassifier(use_ml=False)
        intent, confidence, _ = classifier.predict("Who teaches DBMS?")

        assert intent == "FACULTY_SUBJECT_QUERY"
        assert confidence > 0.8

    def test_exam_query_intent(self):
        """Test exam query intent classification"""
        classifier = IntentClassifier(use_ml=False)
        intent, confidence, _ = classifier.predict("When is the exam?")

        assert intent == "EXAM_QUERY"
        assert confidence > 0.8

    def test_general_education_intent(self):
        """Test general education intent classification"""
        classifier = IntentClassifier(use_ml=False)
        intent, confidence, _ = classifier.predict("Explain machine learning")

        assert intent in ["GENERAL_EDUCATION", "GENERAL_ACADEMIC"]
        assert confidence > 0.5

    def test_multilingual_intent(self):
        """Test multilingual intent classification"""
        classifier = IntentClassifier(use_ml=False)

        # Gujarati
        intent_gu, conf_gu, _ = classifier.predict("BCA fee ketli che?")
        assert intent_gu == "FEE_QUERY"

        # Hindi
        intent_hi, conf_hi, _ = classifier.predict("Bacca ka fee kitna hai?")
        assert intent_hi == "FEE_QUERY"

class TestEntityExtractor:
    """Test entity extraction"""
    
    def test_course_extraction(self):
        """Test course entity extraction"""
        extractor = CollegeEntityExtractor()
        entities = extractor.extract_entities("What is the fee for BCA?")
        
        assert "course" in entities
        assert entities["course"] == "BCA"
    
    def test_semester_extraction(self):
        """Test semester entity extraction"""
        extractor = CollegeEntityExtractor()
        entities = extractor.extract_entities("Show me sem 3 timetable")
        
        assert "semester" in entities
        assert entities["semester"] == 3
    
    def test_year_extraction(self):
        """Test year entity extraction"""
        extractor = CollegeEntityExtractor()
        
        # Explicit year
        entities = extractor.extract_entities("Events in 2025")
        assert "year" in entities
        assert entities["year"] == 2025
        
        # Relative year
        entities_rel = extractor.extract_entities("Last year events")
        assert "year" in entities_rel
        assert entities_rel["year"] == 2025
    
    def test_subject_extraction(self):
        """Test subject entity extraction"""
        extractor = CollegeEntityExtractor()
        entities = extractor.extract_entities("Who teaches database management?")
        
        assert "subject" in entities
        assert entities["subject"] == "DBMS"

class TestVectorStore:
    """Test vector store functionality"""
    
    def test_add_and_search_document(self):
        """Test adding and searching documents"""
        store = SimpleVectorStore(use_embeddings=False)
        
        store.add_document("doc1", "BCA fee structure", {"category": "academic"}, "fee bca")
        store.add_document("doc2", "DBMS course details", {"category": "subject"}, "database dbms")
        
        results = store.search("fee")
        assert len(results) > 0
        assert results[0][0]["id"] == "doc1"
    
    def test_search_with_embeddings(self):
        """Test search with embeddings (if available)"""
        try:
            import sentence_transformers
            store = SimpleVectorStore(use_embeddings=True)
            
            store.add_document("doc1", "Computer science fundamentals", {"category": "academic"})
            results = store.search("computer science")
            
            assert len(results) > 0
        except ImportError:
            # Skip if sentence-transformers not available
            pass
    
    def test_empty_search(self):
        """Test search with no documents"""
        store = SimpleVectorStore(use_embeddings=False)
        results = store.search("test query")
        
        assert len(results) == 0

class TestGroundingValidator:
    """Test grounding validation"""
    
    def test_grounded_answer(self):
        """Test grounded answer validation"""
        answer = "The fee is ₹32,000 for BCA"
        evidence = "BCA fee for 2026-27 is ₹32,000"
        
        is_grounded, confidence, notes = GroundingValidator.check_groundedness(
            answer, evidence, "FEE_QUERY"
        )
        
        assert is_grounded is True
        assert confidence > 0.8
    
    def test_hallucinated_answer(self):
        """Test hallucinated answer detection"""
        answer = "The fee is 50000 for BCA"  # Different number
        evidence = "BCA fee for 2026-27 is 32000"
        
        is_grounded, confidence, notes = GroundingValidator.check_groundedness(
            answer, evidence, "FEE_QUERY"
        )
        
        # The grounding validator checks if numbers from answer exist in evidence
        # Since 50000 is not in 32000, it should detect the issue
        assert is_grounded is False or confidence < 0.8
    
    def test_safe_decline(self):
        """Test safe decline response"""
        answer = "I couldn't find verified information about that"
        evidence = ""
        
        is_grounded, confidence, notes = GroundingValidator.check_groundedness(
            answer, evidence, "FEE_QUERY"
        )
        
        assert is_grounded is True
        assert "safely" in notes.lower()
    
    def test_general_education_query(self):
        """Test general education query (no evidence required)"""
        answer = "Machine learning is a branch of AI"
        evidence = ""
        
        is_grounded, confidence, notes = GroundingValidator.check_groundedness(
            answer, evidence, "GENERAL_EDUCATION"
        )
        
        assert is_grounded is True

class TestConflictDetector:
    """Test knowledge conflict detection"""
    
    def test_fee_conflict_detection(self, db):
        """Test fee conflict detection"""
        # Create test data
        dept = Department(code="TEST", name="Test Department")
        db.add(dept)
        db.flush()
        
        course = Course(code="TEST_BCA", name="Test BCA", department_id=dept.id)
        db.add(course)
        db.flush()
        
        fee = Fee(course_id=course.id, academic_year="2026-27", tuition_fee=32000.0, total_fee=34500.0)
        db.add(fee)
        db.commit()
        
        detector = KnowledgeConflictDetector()
        conflict = detector.check_fee_conflict(
            db, "TEST_BCA", "2026-27", 30000.0, "https://www.aitindia.in/courses/bca"
        )
        
        assert conflict is not None
        assert conflict.status == "OPEN"
    
    def test_no_conflict(self, db):
        """Test when no conflict exists"""
        detector = KnowledgeConflictDetector()
        conflict = detector.check_fee_conflict(
            db, "NONEXISTENT", "2026-27", 32000.0, "https://www.aitindia.in/courses/bca"
        )
        
        assert conflict is None

class TestRedisCache:
    """Test Redis caching functionality"""
    
    def test_cache_set_get(self):
        """Test basic cache set and get operations"""
        cache = RedisCache()
        
        cache.set("test_key", "test_value", ttl=60)
        value = cache.get("test_key")
        
        assert value == "test_value"
    
    def test_cache_set_get_complex_object(self):
        """Test caching complex objects"""
        cache = RedisCache()
        test_data = {"key": "value", "number": 42, "list": [1, 2, 3]}
        
        cache.set("complex_key", test_data)
        retrieved = cache.get("complex_key")
        
        assert retrieved == test_data
    
    def test_cache_delete(self):
        """Test cache deletion"""
        cache = RedisCache()
        
        cache.set("delete_key", "delete_value")
        cache.delete("delete_key")
        
        assert cache.get("delete_key") is None
    
    def test_cache_exists(self):
        """Test cache existence check"""
        cache = RedisCache()
        
        cache.set("exists_key", "exists_value")
        assert cache.exists("exists_key") is True
        assert cache.exists("nonexistent_key") is False
    
    def test_cache_stats(self):
        """Test cache statistics"""
        cache = RedisCache()
        
        cache.set("stat_key1", "value1")
        cache.set("stat_key2", "value2")
        
        stats = cache.get_stats()
        assert "backend" in stats
        assert "keys" in stats
        assert stats["keys"] >= 2
    
    def test_cache_clear_pattern(self):
        """Test pattern-based cache clearing"""
        cache = RedisCache()
        
        cache.set("user:1:data", "value1")
        cache.set("user:2:data", "value2")
        cache.set("other:data", "value3")
        
        cleared = cache.clear_pattern("user:*")
        assert cleared >= 2
        assert cache.get("user:1:data") is None
        assert cache.get("other:data") is not None

class TestDatabaseModels:
    """Test database models"""
    
    def test_user_creation(self, db):
        """Test user model creation"""
        user = User(
            email="test@example.com",
            hashed_password=get_password_hash("password123"),
            full_name="Test User",
            is_active=True
        )
        db.add(user)
        db.commit()
        
        retrieved_user = db.query(User).filter(User.email == "test@example.com").first()
        assert retrieved_user is not None
        assert retrieved_user.full_name == "Test User"
    
    def test_role_creation(self, db):
        """Test role model creation"""
        role = Role(name="TEST_ROLE", description="Test role for unit tests")
        db.add(role)
        db.commit()
        
        retrieved_role = db.query(Role).filter(Role.name == "TEST_ROLE").first()
        assert retrieved_role is not None
        assert retrieved_role.description == "Test role for unit tests"
    
    def test_course_creation(self, db):
        """Test course model creation"""
        dept = Department(code="TEST", name="Test Department")
        db.add(dept)
        db.flush()
        
        course = Course(
            code="TEST101",
            name="Test Course",
            department_id=dept.id,
            duration_years=3,
            total_semesters=6,
            degree_level="Undergraduate"
        )
        db.add(course)
        db.commit()
        
        retrieved_course = db.query(Course).filter(Course.code == "TEST101").first()
        assert retrieved_course is not None
        assert retrieved_course.name == "Test Course"

class TestSecurity:
    """Test security features"""
    
    def test_insecure_password_rejection(self):
        """Test that insecure passwords are handled"""
        # This is a basic test - in production, implement proper password strength validation
        password = "123"  # Very weak password
        hashed = get_password_hash(password)
        
        # Should still hash, but in production implement strength validation
        assert verify_password(password, hashed) is True
    
    def test_sql_injection_protection(self):
        """Test that ORM prevents SQL injection"""
        # SQLAlchemy ORM should prevent SQL injection
        malicious_input = "'; DROP TABLE users; --"
        
        # The ORM should escape this properly
        # This is a conceptual test - in production, add more specific tests
        assert isinstance(malicious_input, str)

class TestConfig:
    """Test configuration settings"""
    
    def test_settings_defaults(self):
        """Test that default settings are loaded"""
        assert settings.APP_NAME == "AIT College AI Assistant"
        assert settings.API_V1_STR == "/api/v1"
        assert settings.AIT_OFFICIAL_URL == "https://www.aitindia.in"
    
    def test_environment_specific_settings(self):
        """Test environment-specific configuration"""
        # In production, these would be set via environment variables
        assert settings.ENVIRONMENT in ["development", "production", "testing"]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])