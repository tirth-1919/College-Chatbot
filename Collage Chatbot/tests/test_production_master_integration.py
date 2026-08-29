import pytest
import asyncio
from datetime import datetime, UTC
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database import SessionLocal, engine, Base
from backend.app.models.entities import (
    Course, Subject, Faculty, Fee, Timetable, Exam, Event, Facility,
    KnowledgeSource, KnowledgeDocument, KnowledgeChunk,
    PendingKnowledgeUpdate, TrainingExample, MLModel, User, Message, Conversation
)
from database.seed.seed_data import seed_database
from ai.router.source_resolver import SourceResolver
from ai.router.intent_router import AIRouter
from backend.app.services.knowledge_sync_service import KnowledgeSyncService
from ml.intent.intent_classifier import IntentClassifier
from rag.crawlers.ait.crawler import AITWebsiteCrawler

@pytest.fixture(scope="module")
def db():
    Base.metadata.create_all(bind=engine)
    seed_database()
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture(scope="module")
def router():
    return AIRouter()

@pytest.fixture(scope="module")
def resolver():
    return SourceResolver()

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client
# ==============================================================================
# PART 1: GENERAL QUESTIONS & ZERO-GENERIC-FALLBACK TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_greeting_natural_response(db, router):
    res = await router.route_and_respond(db, "hi")
    assert len(res["answer"]) > 0
    assert "Ahmedabad Institute of Technology" in res["answer"] or "AIT" in res["answer"] or "Hello" in res["answer"]
    assert "Here is educational information regarding your query" not in res["answer"]
    assert res["status"] == "complete"
    assert res["content"] == res["answer"]

@pytest.mark.asyncio
async def test_which_university_best_real_answer(db, router):
    res = await router.route_and_respond(db, "which university best")
    assert "Here is educational information regarding your query" not in res["answer"]
    assert "university" in res["answer"].lower() or "course" in res["answer"].lower() or "accreditation" in res["answer"].lower()
    assert len(res["answer"]) > 30
    assert res["selected_source"] == "GEMINI"
    assert res["content"] == res["answer"]

@pytest.mark.asyncio
async def test_what_is_python_real_answer(db, router):
    res = await router.route_and_respond(db, "what is python?")
    assert "Here is educational information regarding your query" not in res["answer"]
    assert "Python" in res["answer"]
    assert "programming" in res["answer"].lower() or "language" in res["answer"].lower()
    assert res["selected_source"] == "GEMINI"

@pytest.mark.asyncio
async def test_explain_normalization_real_answer(db, router):
    res = await router.route_and_respond(db, "explain normalization")
    assert "Normalization" in res["answer"] or "1NF" in res["answer"]
    assert "Here is educational information regarding your query" not in res["answer"]

@pytest.mark.asyncio
async def test_viva_and_study_plan_answers(db, router):
    res_viva = await router.route_and_respond(db, "how can I prepare for viva?")
    assert "Viva" in res_viva["answer"] or "prepare" in res_viva["answer"].lower() or "project" in res_viva["answer"].lower()

    res_plan = await router.route_and_respond(db, "make a study plan")
    assert "study plan" in res_plan["answer"].lower() or "pomodoro" in res_plan["answer"].lower() or "curriculum" in res_plan["answer"].lower()

# ==============================================================================
# PART 2: AIT VERIFIED QUESTIONS & HIERARCHY
# ==============================================================================

@pytest.mark.asyncio
async def test_bca_fee_verified_db(db, router):
    res = await router.route_and_respond(db, "What is BCA fee?")
    assert "32,000" in res["answer"]
    assert res["selected_source"] == "DATABASE"
    assert res["status"] == "complete"

@pytest.mark.asyncio
async def test_dbms_faculty_verified_db(db, router):
    res = await router.route_and_respond(db, "Who teaches DBMS?")
    assert "Anjali Sharma" in res["answer"]
    assert res["selected_source"] == "DATABASE"

@pytest.mark.asyncio
async def test_dbms_exam_verified_db(db, router):
    res = await router.route_and_respond(db, "When is the DBMS exam?")
    assert "2026-10-12" in res["answer"] or "BCA401" in res["answer"]
    assert res["selected_source"] == "DATABASE"

@pytest.mark.asyncio
async def test_dbms_syllabus_verified_db(db, router):
    res = await router.route_and_respond(db, "What is DBMS syllabus?")
    assert "Syllabus" in res["answer"] or "Relational" in res["answer"] or "Credits" in res["answer"]
    assert res["selected_source"] == "DATABASE"

@pytest.mark.asyncio
async def test_bca_timetable_verified_db(db, router):
    res = await router.route_and_respond(db, "What is BCA timetable?")
    assert "Timetable" in res["answer"] or "BCA" in res["answer"]
    assert res["selected_source"] == "DATABASE"

@pytest.mark.asyncio
async def test_ait_canteen_zero_hallucination(db, router):
    res = await router.route_and_respond(db, "What is the AIT canteen price?")
    assert "couldn't verify" in res["answer"].lower() or "could not verify" in res["answer"].lower() or "canteen" in res["answer"].lower()
    assert res["selected_source"] == "SAFETY_GUARD"
# ==============================================================================
# PART 3: CONVERSATION CONTEXT PRESERVATION
# ==============================================================================

@pytest.mark.asyncio
async def test_conversation_context_dbms_faculty(db, router):
    # Setup a conversation
    conv = Conversation(title="DBMS Conversation Context Test")
    db.add(conv)
    db.commit()
    db.refresh(conv)

    # Turn 1: User asks "What is DBMS?"
    m1 = Message(conversation_id=conv.id, role="user", content="What is DBMS?")
    m2 = Message(conversation_id=conv.id, role="assistant", content="Database Management System (DBMS) is software used to store and manage data.", entities={"subject": "DBMS"})
    db.add_all([m1, m2])
    db.commit()

    # Turn 2: User asks follow-up "Who teaches it?"
    res = await router.route_and_respond(db, "Who teaches it?", conversation_id=conv.id)
    assert "Anjali Sharma" in res["answer"]
    assert res["selected_source"] == "DATABASE"
    assert res["intent"] == "FACULTY_SUBJECT_QUERY"

@pytest.mark.asyncio
async def test_conversation_context_payment_terms(db, router):
    conv = Conversation(title="BCA Fee Follow-up Test")
    db.add(conv)
    db.commit()
    db.refresh(conv)

    m1 = Message(conversation_id=conv.id, role="user", content="What is BCA fee?")
    m2 = Message(conversation_id=conv.id, role="assistant", content="The total annual fee for BCA is ₹34,500.", entities={"course": "BCA"})
    db.add_all([m1, m2])
    db.commit()

    res = await router.route_and_respond(db, "What about payment terms?", conversation_id=conv.id)
    assert "BCA" in res["answer"] or "Semester" in res["answer"] or "fee" in res["answer"].lower()

# ==============================================================================
# PART 4: KNOWLEDGE SYNC, CHANGE DETECTION & ADMIN APPROVAL
# ==============================================================================

def test_knowledge_sync_and_approval_workflow(db):
    service = KnowledgeSyncService(db)

    # 1. Simulate new crawl page
    test_url = "https://www.aitindia.in/academics/test-bca-syllabus"
    sample_page = {
        "source_url": test_url,
        "canonical_url": test_url,
        "title": "AIT Advanced BCA Cloud Syllabus 2026",
        "category": "Courses & Academics",
        "clean_text": "AIT Advanced BCA includes Cloud Computing, Distributed Systems, and DevOps.",
        "raw_html": "<html><body>AIT Advanced BCA Cloud Syllabus</body></html>",
        "content_hash": "hash_initial_12345",
        "images": []
    }

    # First sync creates NEW_PENDING
    res1 = service._process_crawled_page(sample_page)
    assert res1["status"] == "NEW_PENDING"

    # Verify pending update created
    pending = db.query(PendingKnowledgeUpdate).filter(PendingKnowledgeUpdate.source_url == test_url).first()
    assert pending is not None
    assert pending.approval_status == "PENDING"
    assert pending.change_type == "NEW"

    # Second crawl of same hash returns UNCHANGED
    res2 = service._process_crawled_page(sample_page)
    assert res2["status"] == "UNCHANGED"

    # Content change detected
    modified_page = dict(sample_page)
    modified_page["clean_text"] = "AIT Advanced BCA updated to include Artificial Intelligence & DevOps."
    modified_page["content_hash"] = "hash_modified_67890"

    res3 = service._process_crawled_page(modified_page)
    assert res3["status"] == "MODIFIED_PENDING"

    # Admin approval updates active record & indexes RAG
    pending_mod = db.query(PendingKnowledgeUpdate).filter(
        PendingKnowledgeUpdate.source_url == test_url,
        PendingKnowledgeUpdate.content_hash == "hash_modified_67890"
    ).first()

    app_res = service.approve_pending_update(pending_mod.id, approved_by="admin@aitindia.in")
    assert app_res["success"] is True

    # Active source updated
    src = db.query(KnowledgeSource).filter(KnowledgeSource.source_url == test_url).first()
    assert src.approval_status == "APPROVED"
    assert src.is_verified is True
    assert "Artificial Intelligence" in src.clean_text

    # Chunks created
    chunks = db.query(KnowledgeChunk).join(KnowledgeDocument).filter(KnowledgeDocument.source_id == src.id).all()
    assert len(chunks) > 0

    # Admin rejection test
    dummy_pending = PendingKnowledgeUpdate(
        source_url="https://www.aitindia.in/unverified-rumor",
        title="Unverified Rumor",
        new_value="Invalid unverified data",
        content_hash="hash_invalid_999",
        approval_status="PENDING"
    )
    db.add(dummy_pending)
    db.commit()

    rej_res = service.reject_pending_update(dummy_pending.id, rejected_by="admin@aitindia.in", reason="Not verified by Dean")
    assert rej_res["success"] is True
    assert dummy_pending.approval_status == "REJECTED"

    # Clean up test source
    service.archive_knowledge_source(src.id)
    assert src.approval_status == "ARCHIVED"
# ==============================================================================
# PART 5: MULTILINGUAL INTENT & CONTROLLED RETRAINING
# ==============================================================================

def test_multilingual_intent_classification():
    classifier = IntentClassifier()

    # English variations
    assert classifier.predict("who teaches DBMS?")[0] == "FACULTY_SUBJECT_QUERY"
    assert classifier.predict("DBMS teacher?")[0] == "FACULTY_SUBJECT_QUERY"
    assert classifier.predict("dbms faculty name?")[0] == "FACULTY_SUBJECT_QUERY"
    assert classifier.predict("who is teaching database?")[0] == "FACULTY_SUBJECT_QUERY"

    # Gujarati / Hinglish variations
    assert classifier.predict("DBMS na teacher kon che?")[0] == "FACULTY_SUBJECT_QUERY"
    assert classifier.predict("dbms teacher kon che")[0] == "FACULTY_SUBJECT_QUERY"
    assert classifier.predict("DBMS kon bhanave che?")[0] == "FACULTY_SUBJECT_QUERY"

    # Syllabus
    assert classifier.predict("What is DBMS syllabus?")[0] == "SYLLABUS_QUERY"
    assert classifier.predict("DBMS syllabus?")[0] == "SYLLABUS_QUERY"
    assert classifier.predict("DBMS ma shu bhnavse?")[0] == "SYLLABUS_QUERY"
    assert classifier.predict("give DBMS curriculum")[0] == "SYLLABUS_QUERY"

    # Exam
    assert classifier.predict("When is DBMS exam?")[0] == "EXAM_QUERY"
    assert classifier.predict("DBMS exam date?")[0] == "EXAM_QUERY"
    assert classifier.predict("DBMS ni exam kyare che?")[0] == "EXAM_QUERY"

    # Fees
    assert classifier.predict("BCA fee?")[0] == "FEE_QUERY"
    assert classifier.predict("How much is BCA?")[0] == "FEE_QUERY"
    assert classifier.predict("BCA fees ketli che?")[0] == "FEE_QUERY"

def test_intent_retraining_pipeline(db):
    classifier = IntentClassifier(use_ml=True)

    # Seed approved training examples
    examples = [
        ("who is teaching python programming", "FACULTY_SUBJECT_QUERY"),
        ("python na professor kon che", "FACULTY_SUBJECT_QUERY"),
        ("operating system teacher name", "FACULTY_SUBJECT_QUERY"),
        ("data structures faculty details", "FACULTY_SUBJECT_QUERY"),
        ("what is the exam date for btech", "EXAM_QUERY"),
        ("btech exam schedule 2026", "EXAM_QUERY"),
        ("bca fees kitni hai", "FEE_QUERY"),
        ("mba tuition charge", "FEE_QUERY"),
        ("where can i find the timetable", "TIMETABLE_QUERY"),
        ("daily lecture timetable", "TIMETABLE_QUERY"),
        ("explain neural networks in ai", "GENERAL_EDUCATION"),
        ("what is relational database model", "GENERAL_EDUCATION")
    ]

    for text, intent in examples:
        ex = TrainingExample(
            text=text,
            language="en",
            predicted_intent="GENERAL_ACADEMIC",
            approved_intent=intent,
            status="APPROVED",
            source="TEST_SUITE"
        )
        db.add(ex)
    db.commit()

    # Retrain
    result = classifier.retrain_from_database(db, min_accuracy=0.75, min_f1=0.75)
    assert result["success"] is True
    assert result["accuracy"] >= 0.75
    assert classifier.is_trained is True

# ==============================================================================
# PART 6: ADMIN API ENDPOINTS VERIFICATION
# ==============================================================================

def test_admin_api_endpoints(client):
    # Health check
    res_health = client.get("/health")
    assert res_health.status_code == 200

    # Metrics
    res_metrics = client.get("/api/v1/admin/metrics")
    assert res_metrics.status_code == 200
    assert "total_users" in res_metrics.json()

    # ML Models
    res_models = client.get("/api/v1/admin/ml/models")
    assert res_models.status_code == 200
    assert len(res_models.json()) > 0

    # Student feedback creates training example on unhelpful feedback
    res_chat = client.post("/api/v1/chat/send", json={"message": "What is BCA fee?"})
    assert res_chat.status_code == 200
    msg_id = res_chat.json()["id"]

    res_fb = client.post("/api/v1/chat/feedback", json={
        "message_id": msg_id,
        "feedback": "unhelpful",
        "comment": "Needs more detail"
    })
    assert res_fb.status_code == 200
