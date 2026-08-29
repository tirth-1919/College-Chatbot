import pytest
import asyncio
from sqlalchemy.orm import Session
from backend.app.database import SessionLocal, engine, Base
from backend.app.models.entities import Course, Subject, Faculty, Fee, Timetable, Exam, Event, Facility, KnowledgeConflict, User
from database.seed.seed_data import seed_database
from ai.router.source_resolver import SourceResolver
from ai.router.intent_router import AIRouter

@pytest.fixture(scope="module")
def db():
    Base.metadata.create_all(bind=engine)
    seed_database()
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture(scope="module")
def resolver():
    return SourceResolver()

@pytest.fixture(scope="module")
def router():
    return AIRouter()

# Test 1: "What is the BCA fee?" -> Database when website fee not verified
@pytest.mark.asyncio
async def test_case_1_bca_fee(db, resolver):
    res = await resolver.resolve_question(db, "What is the BCA fee?")
    assert res["selected_source"] == "DATABASE"
    assert "32,000" in res["answer"]
    assert "BCA" in res["answer"]
    assert any(s["authority_level"] == "PRIORITY 2" for s in res["sources"])

# Test 2: "Who teaches BCA Data Structures?" -> Database allocation
@pytest.mark.asyncio
async def test_case_2_bca_data_structures_faculty(db, resolver):
    res = await resolver.resolve_question(db, "Who teaches BCA Data Structures?")
    assert res["selected_source"] == "DATABASE"
    assert "Ramesh Joshi" in res["answer"]
    assert "Data Structures" in res["answer"]

# Test 3: "Who teaches DBMS?" -> Verified DB allocation
@pytest.mark.asyncio
async def test_case_3_who_teaches_dbms(db, resolver):
    res = await resolver.resolve_question(db, "Who teaches DBMS?")
    assert res["selected_source"] == "DATABASE"
    assert "Anjali Sharma" in res["answer"]

# Test 4: "When is the DBMS exam?" -> Verified DB exam schedule
@pytest.mark.asyncio
async def test_case_4_when_is_dbms_exam(db, resolver):
    res = await resolver.resolve_question(db, "When is the DBMS exam?")
    assert res["selected_source"] == "DATABASE"
    assert "2026-10-12" in res["answer"]

# Test 5: "What is the DBMS syllabus?" -> Verified database syllabus summary
@pytest.mark.asyncio
async def test_case_5_dbms_syllabus(db, resolver):
    res = await resolver.resolve_question(db, "What is the DBMS syllabus?")
    assert res["selected_source"] == "DATABASE"
    assert "Syllabus" in res["answer"] or "Relational" in res["answer"]
    assert "4 Credits" in res["answer"] or "Credits" in res["answer"]

# Test 6: "Show AIT library." -> Official website image/text with provenance
@pytest.mark.asyncio
async def test_case_6_show_ait_library(db, resolver):
    res = await resolver.resolve_question(db, "Show AIT library.")
    assert res["selected_source"] == "OFFICIAL_AIT_WEBSITE"
    assert len(res["images"]) > 0
    img = res["images"][0]
    assert "central_library" in img["image_url"] or "library" in img.get("caption", "").lower()
    assert img["source_url"].startswith("https://www.aitindia.in")

# Test 7: "Tell me about Nirma University." -> Gemini general knowledge
@pytest.mark.asyncio
async def test_case_7_nirma_university(db, resolver):
    res = await resolver.resolve_question(db, "Tell me about Nirma University.")
    assert res["selected_source"] == "GEMINI"
    assert res["is_general_knowledge"] is True
    assert "Nirma" in res["answer"]

# Test 8: "Explain normalization." -> Gemini general educational answer
@pytest.mark.asyncio
async def test_case_8_explain_normalization(db, resolver):
    res = await resolver.resolve_question(db, "Explain normalization.")
    assert res["selected_source"] == "GEMINI"
    assert "Normalization" in res["answer"] or "1NF" in res["answer"]
    assert res["is_general_knowledge"] is True

# Test 9: "Who is the current BCA HOD at AIT?" -> Zero hallucination unable-to-verify
@pytest.mark.asyncio
async def test_case_9_ait_hod_zero_hallucination(db, resolver):
    res = await resolver.resolve_question(db, "Who is the current BCA HOD at AIT?")
    assert res["selected_source"] == "SAFETY_GUARD"
    assert any(phrase in res["answer"].lower() for phrase in ["couldn't verify", "could not verify", "unable to verify", "verified college database"])

# Test 10: "Show my result." -> Authentication / Privacy enforcement
@pytest.mark.asyncio
async def test_case_10_show_my_result_privacy(db, resolver):
    # Public unauthenticated request rejected
    res_pub = await resolver.resolve_question(db, "Show my result.", role="PUBLIC", user_id=None)
    assert res_pub["selected_source"] == "SAFETY_GUARD"
    assert "Authentication required" in res_pub["answer"]

    # Authenticated student request returns verified result
    student = db.query(User).filter(User.email == "student@aitindia.in").first()
    res_auth = await resolver.resolve_question(db, "Show my result.", role="STUDENT", user_id=student.id)
    assert res_auth["selected_source"] == "DATABASE"
    assert "Dharmik Patel" in res_auth["answer"]
    assert "210020107001" in res_auth["answer"]

# Test 11: Conflict resolution: Website wins over database by default
@pytest.mark.asyncio
async def test_case_11_website_wins_over_database(db, resolver):
    # Query matching official website content returns website as source
    res = await resolver.resolve_question(db, "About Ahmedabad Institute of Technology")
    assert res["selected_source"] == "OFFICIAL_AIT_WEBSITE"
    assert any(s["authority_level"] == "PRIORITY 1" for s in res["sources"])

# Test 12: Frontend response contract
@pytest.mark.asyncio
async def test_case_12_frontend_response_contract(db, resolver):
    res = await resolver.resolve_question(db, "What is the BCA fee?")
    required_keys = [
        "conversation_id", "message_id", "answer", "content", "status", "role",
        "intent", "entities", "selected_source", "confidence", "sources", "images", "suggested_followups"
    ]
    for k in required_keys:
        assert k in res
    assert res["status"] == "complete"
    assert res["content"] == res["answer"]
    assert len(res["content"]) > 0

# Test 13: Thinking lifecycle contract (AIRouter output complete)
@pytest.mark.asyncio
async def test_case_13_thinking_lifecycle(db, router):
    res = await router.route_and_respond(db, "Who teaches DBMS?")
    assert res["status"] == "complete"
    assert len(res["answer"]) > 0

# Test 14: Gujarati / Hindi multilingual support
@pytest.mark.asyncio
async def test_case_14_multilingual_gujarati_hindi(db, resolver):
    res_gu = await resolver.resolve_question(db, "DBMS kon bhanave che?")
    assert "Anjali Sharma" in res_gu["answer"]
    assert res_gu["selected_source"] == "DATABASE"

    res_hi = await resolver.resolve_question(db, "DBMS कौन पढ़ाते हैं?")
    assert "Anjali Sharma" in res_hi["answer"]
    assert res_hi["selected_source"] == "DATABASE"
