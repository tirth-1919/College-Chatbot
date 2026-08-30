import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.database import Base
from backend.app.models.entities import Department, Course, Subject, Facility, FacilityImage
from ai.academic_catalog import academic_entities, query_catalog
from rag.images.image_retriever import OfficialImageRetriever
@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    department = Department(code="TEST", name="Test")
    session.add(department)
    session.flush()
    course = Course(code="BBA", name="Bachelor of Business Administration", department_id=department.id)
    session.add(course)
    session.flush()
    session.add_all([
        Subject(code="BBA201", name="Accounting", course_id=course.id, semester=2, credits=4, academic_year="2025-26"),
        Subject(code="BBA202", name="Marketing", course_id=course.id, semester=2, credits=3, academic_year="2025-26"),
        Subject(code="BBA301", name="Operations", course_id=course.id, semester=3, credits=4, academic_year="2025-26"),
    ])
    facility = Facility(name="AIT Campus", category="Infrastructure")
    session.add(facility)
    session.flush()
    session.add_all([
        FacilityImage(facility_id=facility.id, image_url="https://www.aitindia.in/media/campus.jpg", source_url="https://www.aitindia.in/campus", source_page="Campus", approval_status="APPROVED", ai_visible=True),
        FacilityImage(facility_id=facility.id, image_url="https://example.com/fake.jpg", source_url="https://www.aitindia.in/campus", source_page="Campus", approval_status="APPROVED", ai_visible=True),
    ])
    session.commit()
    yield session
    session.close()

def test_semester_parser_supports_ordinal_and_hinglish():
    assert academic_entities("BBA second semester subjects")['semester'] == 2
    assert academic_entities("BCA sem 2 ma subjects batavo")['semester'] == 2

def test_catalog_returns_only_requested_semester_and_verified_data(db):
    result = query_catalog(db, "BBA sem 2 subjects")
    assert result["verified"] is True
    assert result["semester"] == 2
    assert [subject.code for subject in result["subjects"]] == ["BBA201", "BBA202"]
    assert "Semester 3" not in result["answer"]

def test_catalog_does_not_claim_unknown_course(db):
    result = query_catalog(db, "MBA sem 1 subjects")
    assert result["verified"] is False

def test_image_retriever_rejects_untrusted_image_url(db):
    images = OfficialImageRetriever.search_images(db, "show campus image")
    assert [image["image_url"] for image in images] == ["https://www.aitindia.in/media/campus.jpg"]
