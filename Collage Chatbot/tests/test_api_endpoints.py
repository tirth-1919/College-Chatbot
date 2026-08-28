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
