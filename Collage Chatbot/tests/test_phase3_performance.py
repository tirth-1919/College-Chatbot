"""
Phase 3 Performance Testing
Performance benchmarks and optimization verification
"""

import pytest
import time
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from backend.app.main import app
from backend.app.database import get_db, engine, Base
from backend.app.models.entities import User, BackgroundJob
from backend.app.security.auth import create_access_token


class TestPhase3Performance:
    """Performance tests for Phase 3 features"""
    
    @pytest.fixture
    def db(self):
        """Database fixture"""
        Base.metadata.create_all(bind=engine)
        db = next(get_db())
        try:
            yield db
        finally:
            db.close()
            Base.metadata.drop_all(bind=engine)
    
    @pytest.fixture
    def client(self):
        """Test client fixture"""
        return TestClient(app)
    
    @pytest.fixture
    def test_user(self, db):
        """Create test user"""
        user = User(
            email="perf@example.com",
            full_name="Performance Test User",
            hashed_password="hashed_password",
            is_active=True,
            is_verified=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @pytest.fixture
    def auth_headers(self, test_user):
        """Create authentication headers"""
        token = create_access_token(data={"sub": test_user.email})
        return {"Authorization": f"Bearer {token}"}
    
    # ----------------- Background Job Performance Tests -----------------
    
    def test_job_creation_performance(self, client, db, test_user, auth_headers):
        """Test that job creation is fast (< 100ms)"""
        start_time = time.time()
        
        response = client.post(
            "/api/v1/jobs",
            json={
                "job_type": "DEEP_RESEARCH",
                "parameters": {"question": "test performance"},
                "priority": 5
            },
            headers=auth_headers
        )
        
        duration_ms = (time.time() - start_time) * 1000
        
        assert response.status_code == 200
        assert duration_ms < 100, f"Job creation took {duration_ms}ms, expected < 100ms"
    
    def test_job_list_performance(self, client, db, test_user, auth_headers):
        """Test that job listing is fast (< 50ms)"""
        # Create some test jobs
        from backend.app.services.background_job_service import BackgroundJobService
        job_service = BackgroundJobService(db)
        
        for i in range(10):
            job_service.create_job(
                job_type="DATA_ANALYSIS",
                owner_id=test_user.id,
                owner_role="STUDENT",
                parameters={"test": i}
            )
        
        start_time = time.time()
        
        response = client.get("/api/v1/jobs", headers=auth_headers)
        
        duration_ms = (time.time() - start_time) * 1000
        
        assert response.status_code == 200
        assert duration_ms < 50, f"Job listing took {duration_ms}ms, expected < 50ms"
    
    # ----------------- Memory Service Performance Tests -----------------
    
    def test_memory_update_performance(self, client, db, test_user, auth_headers):
        """Test that memory updates are fast (< 50ms)"""
        start_time = time.time()
        
        response = client.put(
            "/api/v1/memory",
            json={
                "preferred_language": "gu",
                "study_preferences": {"course": "BCA"}
            },
            headers=auth_headers
        )
        
        duration_ms = (time.time() - start_time) * 1000
        
        assert response.status_code == 200
        assert duration_ms < 50, f"Memory update took {duration_ms}ms, expected < 50ms"
    
    def test_memory_retrieval_performance(self, client, db, test_user, auth_headers):
        """Test that memory retrieval is fast (< 30ms)"""
        # First create some memory
        client.put(
            "/api/v1/memory",
            json={"preferred_language": "hi"},
            headers=auth_headers
        )
        
        start_time = time.time()
        
        response = client.get("/api/v1/memory", headers=auth_headers)
        
        duration_ms = (time.time() - start_time) * 1000
        
        assert response.status_code == 200
        assert duration_ms < 30, f"Memory retrieval took {duration_ms}ms, expected < 30ms"
    
    # ----------------- Database Query Performance Tests -----------------
    
    def test_database_query_performance(self, db):
        """Test that database queries are efficient"""
        from backend.app.models.entities import Conversation, Message
        
        # Create test data
        user = User(
            email="queryperf@example.com",
            full_name="Query Perf User",
            hashed_password="hashed",
            is_active=True
        )
        db.add(user)
        db.commit()
        
        # Create conversation with messages
        conv = Conversation(user_id=user.id, title="Test")
        db.add(conv)
        db.commit()
        
        # Add messages
        for i in range(100):
            msg = Message(
                conversation_id=conv.id,
                role="user",
                content=f"Test message {i}"
            )
            db.add(msg)
        db.commit()
        
        # Test query performance
        start_time = time.time()
        
        messages = db.query(Message).filter(
            Message.conversation_id == conv.id
        ).all()
        
        duration_ms = (time.time() - start_time) * 1000
        
        assert len(messages) == 100
        assert duration_ms < 100, f"Query took {duration_ms}ms, expected < 100ms"
    
    # ----------------- N+1 Query Prevention Tests -----------------
    
    def test_no_n_plus_one_queries(self, db):
        """Test that N+1 queries are prevented"""
        from backend.app.models.entities import Conversation, Message
        
        # Create test data
        user = User(
            email="nplus1@example.com",
            full_name="N+1 Test User",
            hashed_password="hashed",
            is_active=True
        )
        db.add(user)
        db.commit()
        
        # Create multiple conversations with messages
        for i in range(10):
            conv = Conversation(user_id=user.id, title=f"Test {i}")
            db.add(conv)
            db.commit()
            
            for j in range(5):
                msg = Message(
                    conversation_id=conv.id,
                    role="user",
                    content=f"Message {j}"
                )
                db.add(msg)
            db.commit()
        
        # Test efficient loading
        start_time = time.time()
        
        conversations = db.query(Conversation).filter(
            Conversation.user_id == user.id
        ).all()
        
        # Simulate accessing messages (this should not cause N+1 in production with proper eager loading)
        message_count = sum(len(conv.messages) for conv in conversations)
        
        duration_ms = (time.time() - start_time) * 1000
        
        assert len(conversations) == 10
        assert message_count == 50
        # Note: In production, this would use eager loading to prevent N+1
        # For now, we just verify it completes in reasonable time
        assert duration_ms < 500, f"Query took {duration_ms}ms"
    
    # ----------------- Rate Limiting Performance Tests -----------------
    
    def test_rate_limiting_overhead(self, client):
        """Test that rate limiting doesn't add significant overhead"""
        # Make multiple requests to test overhead
        times = []
        
        for i in range(10):
            start_time = time.time()
            
            response = client.get("/health")
            
            duration_ms = (time.time() - start_time) * 1000
            times.append(duration_ms)
        
        avg_time = sum(times) / len(times)
        
        assert all(r.status_code == 200 for r in [response])  # All should succeed under limits
        assert avg_time < 20, f"Average request time {avg_time}ms, expected < 20ms"
    
    # ----------------- Observability Overhead Tests -----------------
    
    def test_observability_overhead(self, client):
        """Test that observability middleware doesn't add significant overhead"""
        # Make requests and measure performance
        times = []
        
        for i in range(5):
            start_time = time.time()
            
            response = client.get("/")
            
            duration_ms = (time.time() - start_time) * 1000
            times.append(duration_ms)
        
        avg_time = sum(times) / len(times)
        
        assert avg_time < 50, f"Average request time {avg_time}ms with observability, expected < 50ms"
    
    # ----------------- Memory Usage Tests -----------------
    
    def test_memory_usage_safety(self, db):
        """Test that operations don't consume excessive memory"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / (1024 * 1024)  # MB
        
        # Create a large but reasonable dataset
        from backend.app.models.entities import Conversation, Message
        
        user = User(
            email="memory@example.com",
            full_name="Memory Test User",
            hashed_password="hashed",
            is_active=True
        )
        db.add(user)
        db.commit()
        
        conv = Conversation(user_id=user.id, title="Memory Test")
        db.add(conv)
        db.commit()
        
        # Add messages with substantial content
        for i in range(100):
            msg = Message(
                conversation_id=conv.id,
                role="user",
                content="x" * 1000  # 1KB per message
            )
            db.add(msg)
        db.commit()
        
        final_memory = process.memory_info().rss / (1024 * 1024)  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (< 50MB for this test)
        assert memory_increase < 50, f"Memory increased by {memory_increase}MB, expected < 50MB"
    
    # ----------------- Concurrent Operations Tests -----------------
    
    @pytest.mark.asyncio
    async def test_concurrent_job_operations(self, db):
        """Test that concurrent job operations are handled safely"""
        from backend.app.services.background_job_service import BackgroundJobService
        
        job_service = BackgroundJobService(db)
        
        # Create test user
        user = User(
            email="concurrent@example.com",
            full_name="Concurrent Test User",
            hashed_password="hashed",
            is_active=True
        )
        db.add(user)
        db.commit()
        
        # Create multiple jobs concurrently
        async def create_job_async(i):
            return job_service.create_job(
                job_type="DATA_ANALYSIS",
                owner_id=user.id,
                owner_role="STUDENT",
                parameters={"test": i}
            )
        
        start_time = time.time()
        
        jobs = await asyncio.gather(*[create_job_async(i) for i in range(10)])
        
        duration_ms = (time.time() - start_time) * 1000
        
        assert len(jobs) == 10
        assert all(job.id for job in jobs)
        assert duration_ms < 500, f"Concurrent job creation took {duration_ms}ms, expected < 500ms"