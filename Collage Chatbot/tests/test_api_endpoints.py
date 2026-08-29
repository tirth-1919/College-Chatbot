import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import engine, Base
from database.seed.seed_data import seed_database

@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    seed_database()
    with TestClient(app) as test_client:
        yield test_client

def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "AIT" in data["service"]

def test_chat_api_post_root(client):
    res = client.post("/api/chat", json={"message": "What is the BCA fee?"})
    assert res.status_code == 200
    data = res.json()
    assert "32,000" in data["answer"]
    assert "BCA" in data["answer"]
    assert len(data["sources"]) > 0

def test_chat_api_post_v1(client):
    res = client.post("/api/v1/chat/send", json={"message": "Who teaches DBMS?"})
    assert res.status_code == 200
    data = res.json()
    assert "Anjali Sharma" in data["answer"]
    assert "DBMS" in data["answer"] or "Database" in data["answer"]

def test_auth_login_success(client):
    res = client.post("/api/auth/login", json={
        "email": "student@aitindia.in",
        "password": "Student@123"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == "student@aitindia.in"

def test_auth_login_invalid_password(client):
    res = client.post("/api/auth/login", json={
        "email": "student@aitindia.in",
        "password": "WrongPassword!"
    })
    assert res.status_code == 401

def test_voice_chat_endpoint(client):
    res = client.post("/api/chat/voice", data={
        "transcript": "What is BCA fee?"
    })
    assert res.status_code == 200
    data = res.json()
    assert "chat_response" in data
    assert "32,000" in data["chat_response"]["answer"]
    assert data["chat_response"]["voice_asset_id"] is not None

def test_academic_fees_endpoint(client):
    res = client.get("/api/academic/fees?course_code=BCA")
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0
    assert data[0]["course_code"] == "BCA"
    assert data[0]["tuition_fee"] == 32000.0

def test_visual_facilities_endpoint(client):
    res = client.get("/api/visual/facilities")
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0
    assert any("Library" in f["name"] or "Classroom" in f["name"] for f in data)

def test_visual_events_endpoint(client):
    res = client.get("/api/visual/events")
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0


# ----------------- Unified Single-Port & SPA Fallback Tests -----------------

def test_unified_spa_root_serves_html(client):
    """GET / serves the React single-page application"""
    res = client.get("/")
    assert res.status_code == 200
    # Returns HTML when dist/index.html exists or fallback JSON
    assert "text/html" in res.headers.get("content-type", "") or res.json().get("status") == "backend_online"

def test_unified_spa_fallback_client_routes(client):
    """Client-side SPA routes (/chat, /academic, /study, /gallery, /admin) resolve with 200 without 404"""
    for route in ["/chat", "/academic", "/study", "/gallery", "/admin", "/login"]:
        res = client.get(route)
        assert res.status_code == 200
        # Valid SPA fallback returns index.html
        if "text/html" in res.headers.get("content-type", ""):
            assert "<!DOCTYPE html>" in res.text or "<html" in res.text

def test_unified_api_priority_over_spa(client):
    """API endpoints must return JSON and not get captured by SPA fallback"""
    res = client.get("/api/v1/academic/fees")
    assert res.status_code == 200
    assert "application/json" in res.headers.get("content-type", "")
    assert isinstance(res.json(), list)

# ----------------- Blank Chat Response Regression & 10-Question Tests -----------------

def test_chat_returns_non_empty_answer(client):
    """Verify that chat queries never return empty answer/content"""
    res = client.post("/api/v1/chat/send", json={"message": "What is the BCA fee?"})
    assert res.status_code == 200
    data = res.json()
    assert bool(data.get("answer"))
    assert bool(data.get("content"))
    assert data["answer"].strip() != ""
    assert data["content"].strip() != ""

def test_chat_frontend_response_contract(client):
    """Verify complete response contract matching frontend ChatMessage interface"""
    res = client.post("/api/v1/chat/send", json={"message": "Who teaches DBMS?"})
    assert res.status_code == 200
    data = res.json()
    assert "id" in data or "message_id" in data
    assert data.get("role") == "assistant"
    assert "answer" in data
    assert "content" in data
    assert data.get("status") == "complete"
    assert "conversation_id" in data
    assert isinstance(data.get("sources"), list)
    assert isinstance(data.get("images"), list)
    assert isinstance(data.get("suggested_followups"), list)

def test_chat_error_response_empty_message(client):
    """Verify empty message returns proper 400 error"""
    res = client.post("/api/v1/chat/send", json={"message": "   "})
    assert res.status_code == 400
    data = res.json()
    assert "detail" in data

def test_chat_conversation_persistence(client):
    """Verify conversation_id persists across multiple turns"""
    res1 = client.post("/api/v1/chat/send", json={"message": "What is the BCA fee?"})
    assert res1.status_code == 200
    conv_id = res1.json()["conversation_id"]
    assert conv_id is not None

    res2 = client.post("/api/v1/chat/send", json={
        "message": "Who teaches DBMS?",
        "conversation_id": conv_id
    })
    assert res2.status_code == 200
    assert res2.json()["conversation_id"] == conv_id

def test_required_question_1_bca_fee(client):
    """1. What is the BCA fee?"""
    res = client.post("/api/v1/chat/send", json={"message": "What is the BCA fee?"})
    assert res.status_code == 200
    data = res.json()
    assert "32,000" in data["content"]
    assert "BCA" in data["content"]

def test_required_question_2_who_teaches_dbms(client):
    """2. Who teaches DBMS?"""
    res = client.post("/api/v1/chat/send", json={"message": "Who teaches DBMS?"})
    assert res.status_code == 200
    data = res.json()
    assert "Anjali Sharma" in data["content"]
    assert "DBMS" in data["content"] or "Database" in data["content"]

def test_required_question_3_when_is_dbms_exam(client):
    """3. When is the DBMS exam?"""
    res = client.post("/api/v1/chat/send", json={"message": "When is the DBMS exam?"})
    assert res.status_code == 200
    data = res.json()
    assert "2026-10-12" in data["content"] or "DBMS" in data["content"] or "Database" in data["content"]
    assert len(data["content"]) > 20

def test_required_question_4_dbms_syllabus(client):
    """4. What is the DBMS syllabus?"""
    res = client.post("/api/v1/chat/send", json={"message": "What is the DBMS syllabus?"})
    assert res.status_code == 200
    data = res.json()
    assert "Syllabus" in data["content"] or "Normalization" in data["content"] or "SQL" in data["content"] or "DBMS" in data["content"]
    assert len(data["content"]) > 30

def test_required_question_5_bca_timetable(client):
    """5. What is the BCA timetable?"""
    res = client.post("/api/v1/chat/send", json={"message": "What is the BCA timetable?"})
    assert res.status_code == 200
    data = res.json()
    assert "Timetable" in data["content"] or "BCA" in data["content"]
    assert len(data["content"]) > 30

def test_required_question_6_ait_library_info(client):
    """6. Show AIT library information."""
    res = client.post("/api/v1/chat/send", json={"message": "Show AIT library information."})
    assert res.status_code == 200
    data = res.json()
    assert "Library" in data["content"] or "library" in data["content"]
    assert len(data["content"]) > 30

def test_required_question_7_events_last_year(client):
    """7. What events happened last year?"""
    res = client.post("/api/v1/chat/send", json={"message": "What events happened last year?"})
    assert res.status_code == 200
    data = res.json()
    assert "IGNITE" in data["content"] or "Hackathon" in data["content"] or "TARANG" in data["content"] or "events" in data["content"].lower()

def test_required_question_8_explain_normalization(client):
    """8. Explain normalization."""
    res = client.post("/api/v1/chat/send", json={"message": "Explain normalization."})
    assert res.status_code == 200
    data = res.json()
    assert "1NF" in data["content"] or "Normalization" in data["content"] or "normal" in data["content"].lower()

def test_required_question_9_study_plan(client):
    """9. Make a study plan for my exam."""
    res = client.post("/api/v1/chat/send", json={"message": "Make a study plan for my exam."})
    assert res.status_code == 200
    data = res.json()
    assert "Study Plan" in data["content"] or "DBMS" in data["content"] or "BCA" in data["content"]

def test_required_question_10_private_result_isolation_guest(client):
    """10a. Show my result - Guest (must be isolated/restricted)"""
    res = client.post("/api/v1/chat/send", json={"message": "Show my result."})
    assert res.status_code == 200
    data = res.json()
    assert "Authentication required" in data["content"] or "sign in" in data["content"].lower() or "restricted" in data["content"].lower()

def test_required_question_10_private_result_authenticated_student(client):
    """10b. Show my result - Authenticated Student (must return student's own grades)"""
    login_res = client.post("/api/auth/login", json={
        "email": "student@aitindia.in",
        "password": "Student@123"
    })
    token = login_res.json()["access_token"]

    res = client.post(
        "/api/v1/chat/send",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Show my result."}
    )
    assert res.status_code == 200
    data = res.json()
    assert "Results" in data["content"] or "SPI" in data["content"] or "Grade" in data["content"]

