import uuid
from datetime import datetime, UTC
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, Table, JSON
)
from sqlalchemy.orm import relationship
from backend.app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

# Many-to-many link tables
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", String, ForeignKey("users.id"), primary_key=True),
    Column("role_id", String, ForeignKey("roles.id"), primary_key=True)
)

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", String, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", String, ForeignKey("permissions.id"), primary_key=True)
)

# ----------------- 1. Identity & RBAC -----------------

class Permission(Base):
    __tablename__ = "permissions"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

class Role(Base):
    __tablename__ = "roles"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(50), unique=True, nullable=False) # PUBLIC, STUDENT, FACULTY, ADMIN, SUPER_ADMIN
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    permissions = relationship("Permission", secondary=role_permissions, backref="roles")

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String(150), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)  # Nullable for Google OAuth users
    full_name = Column(String(150), nullable=False)
    enrollment_number = Column(String(50), unique=True, index=True, nullable=True)
    google_id = Column(String(255), unique=True, index=True, nullable=True)  # Google OAuth ID
    profile_image_url = Column(String(500), nullable=True)  # Profile image from OAuth
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)  # Email verification status
    department_id = Column(String, ForeignKey("departments.id"), nullable=True)
    course_id = Column(String, ForeignKey("courses.id"), nullable=True)
    current_semester = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    last_login_at = Column(DateTime, nullable=True)

    roles = relationship("Role", secondary=user_roles, backref="users")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    support_tickets = relationship("SupportTicket", back_populates="user")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")

# ----------------- 2. Academic Master Data -----------------

class Department(Base):
    __tablename__ = "departments"
    id = Column(String, primary_key=True, default=generate_uuid)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    head_of_department = Column(String(150), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    courses = relationship("Course", back_populates="department")
    faculty_members = relationship("Faculty", back_populates="department")

class Course(Base):
    __tablename__ = "courses"
    id = Column(String, primary_key=True, default=generate_uuid)
    code = Column(String(20), unique=True, nullable=False) # BCA, BTECH_CSE, BTECH_IT, MCA, MBA
    name = Column(String(150), nullable=False)
    department_id = Column(String, ForeignKey("departments.id"), nullable=False)
    duration_years = Column(Integer, default=3)
    total_semesters = Column(Integer, default=6)
    degree_level = Column(String(50), default="Undergraduate") # Undergraduate, Postgraduate, Diploma
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    department = relationship("Department", back_populates="courses")
    subjects = relationship("Subject", back_populates="course")
    fees = relationship("Fee", back_populates="course")

class Subject(Base):
    __tablename__ = "subjects"
    id = Column(String, primary_key=True, default=generate_uuid)
    code = Column(String(20), index=True, nullable=False) # e.g. BCA301, DBMS101
    name = Column(String(150), nullable=False)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    semester = Column(Integer, nullable=False)
    credits = Column(Integer, default=4)
    syllabus_summary = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    academic_year = Column(String(20), default="2026-27")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    course = relationship("Course", back_populates="subjects")
    faculty_mappings = relationship("FacultySubject", back_populates="subject")

class Faculty(Base):
    __tablename__ = "faculty"
    id = Column(String, primary_key=True, default=generate_uuid)
    employee_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(150), nullable=False)
    designation = Column(String(100), default="Assistant Professor")
    department_id = Column(String, ForeignKey("departments.id"), nullable=False)
    email = Column(String(150), nullable=True)
    phone = Column(String(20), nullable=True)
    office_room = Column(String(50), nullable=True)
    office_hours = Column(String(100), nullable=True)
    qualification = Column(String(150), nullable=True)
    ai_visible = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    department = relationship("Department", back_populates="faculty_members")
    subject_mappings = relationship("FacultySubject", back_populates="faculty")

class FacultySubject(Base):
    __tablename__ = "faculty_subjects"
    id = Column(String, primary_key=True, default=generate_uuid)
    faculty_id = Column(String, ForeignKey("faculty.id"), nullable=False)
    subject_id = Column(String, ForeignKey("subjects.id"), nullable=False)
    division = Column(String(10), default="A")
    academic_year = Column(String(20), default="2026-27")
    is_primary = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    faculty = relationship("Faculty", back_populates="subject_mappings")
    subject = relationship("Subject", back_populates="faculty_mappings")

class Fee(Base):
    __tablename__ = "fees"
    id = Column(String, primary_key=True, default=generate_uuid)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    academic_year = Column(String(20), nullable=False) # e.g. 2026-27
    tuition_fee = Column(Float, nullable=False)
    exam_fee = Column(Float, default=1500.0)
    other_charges = Column(Float, default=1000.0)
    total_fee = Column(Float, nullable=False)
    payment_terms = Column(String(255), default="Semester-wise or Annual")
    valid_from = Column(DateTime, default=lambda: datetime.now(UTC))
    valid_until = Column(DateTime, nullable=True)
    version = Column(Integer, default=1)
    verification_status = Column(String(30), default="VERIFIED") # DRAFT, VERIFIED, ARCHIVED
    ai_visible = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    course = relationship("Course", back_populates="fees")

class Timetable(Base):
    __tablename__ = "timetables"
    id = Column(String, primary_key=True, default=generate_uuid)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    semester = Column(Integer, nullable=False)
    division = Column(String(10), default="A")
    day_of_week = Column(String(20), nullable=False) # Monday, Tuesday, etc.
    start_time = Column(String(10), nullable=False) # e.g. "09:00 AM"
    end_time = Column(String(10), nullable=False)   # e.g. "10:00 AM"
    subject_name = Column(String(150), nullable=False)
    faculty_name = Column(String(150), nullable=False)
    room_number = Column(String(50), nullable=False) # e.g. "Lab 3" or "Room 204"
    academic_year = Column(String(20), default="2026-27")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

class Exam(Base):
    __tablename__ = "exams"
    id = Column(String, primary_key=True, default=generate_uuid)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    semester = Column(Integer, nullable=False)
    subject_code = Column(String(20), nullable=False)
    subject_name = Column(String(150), nullable=False)
    exam_type = Column(String(50), default="Mid-Term") # Mid-Term, End-Term, Practical, Viva
    exam_date = Column(String(30), nullable=False) # e.g. "2026-10-15"
    start_time = Column(String(10), nullable=False)
    end_time = Column(String(10), nullable=False)
    room_number = Column(String(50), default="Block A, Exam Hall")
    academic_year = Column(String(20), default="2026-27")
    status = Column(String(30), default="SCHEDULED") # SCHEDULED, COMPLETED, POSTPONED
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

class Result(Base):
    __tablename__ = "results"
    id = Column(String, primary_key=True, default=generate_uuid)
    student_enrollment = Column(String(50), index=True, nullable=False)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    semester = Column(Integer, nullable=False)
    subject_code = Column(String(20), nullable=False)
    subject_name = Column(String(150), nullable=False)
    grade = Column(String(5), nullable=False) # AA, AB, BB, BC, CC, CD, FF
    spi = Column(Float, nullable=True)
    cpi = Column(Float, nullable=True)
    academic_year = Column(String(20), default="2025-26")
    published_date = Column(DateTime, default=lambda: datetime.now(UTC))

# ----------------- 3. Campus, Events & Visual Media -----------------

class Facility(Base):
    __tablename__ = "facilities"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(150), nullable=False) # Smart Classroom, Central Library, Computer Lab, Sports Ground
    category = Column(String(50), nullable=False) # Academic, Sports, Infrastructure, Labs
    location = Column(String(100), nullable=True) # Block B, 2nd Floor
    description = Column(Text, nullable=True)
    timings = Column(String(100), default="08:00 AM - 05:00 PM")
    contact_person = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    images = relationship("FacilityImage", back_populates="facility", cascade="all, delete-orphan")

class FacilityImage(Base):
    __tablename__ = "facility_images"
    id = Column(String, primary_key=True, default=generate_uuid)
    facility_id = Column(String, ForeignKey("facilities.id"), nullable=False)
    image_url = Column(String(500), nullable=False)
    source_url = Column(String(500), nullable=False) # Original URL from aitindia.in
    source_page = Column(String(255), nullable=False) # Page name / context
    caption = Column(String(255), nullable=True)
    alt_text = Column(String(255), nullable=True)
    tags = Column(String(255), nullable=True)
    content_hash = Column(String(64), nullable=True)
    approval_status = Column(String(30), default="APPROVED") # PENDING, APPROVED, REJECTED, ARCHIVED
    ai_visible = Column(Boolean, default=True)
    retrieved_at = Column(DateTime, default=lambda: datetime.now(UTC))

    facility = relationship("Facility", back_populates="images")

class Event(Base):
    __tablename__ = "events"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False) # e.g. "TechFest IGNITE 2025", "AIT Hackathon 2024"
    event_type = Column(String(50), default="Technical") # Technical, Cultural, Sports, Workshop, Seminar
    date_start = Column(String(30), nullable=False) # e.g. "2025-03-20"
    date_end = Column(String(30), nullable=True)
    academic_year = Column(String(20), nullable=False) # e.g. "2024-25" or "2025-26"
    calendar_year = Column(Integer, nullable=False) # 2024, 2025, 2026
    description = Column(Text, nullable=False)
    department = Column(String(100), default="Campus-wide")
    organizer = Column(String(150), default="AIT Student Council")
    official_source_url = Column(String(500), default="https://www.aitindia.in/events")
    status = Column(String(30), default="COMPLETED") # UPCOMING, ONGOING, COMPLETED
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    images = relationship("EventImage", back_populates="event", cascade="all, delete-orphan")

class EventImage(Base):
    __tablename__ = "event_images"
    id = Column(String, primary_key=True, default=generate_uuid)
    event_id = Column(String, ForeignKey("events.id"), nullable=False)
    image_url = Column(String(500), nullable=False)
    source_url = Column(String(500), nullable=False)
    source_page = Column(String(255), nullable=False)
    caption = Column(String(255), nullable=True)
    alt_text = Column(String(255), nullable=True)
    tags = Column(String(255), nullable=True)
    content_hash = Column(String(64), nullable=True)
    approval_status = Column(String(30), default="APPROVED")
    ai_visible = Column(Boolean, default=True)
    retrieved_at = Column(DateTime, default=lambda: datetime.now(UTC))

    event = relationship("Event", back_populates="images")

class Notice(Base):
    __tablename__ = "notices"
    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    category = Column(String(50), default="Academic") # Academic, Exam, Admission, Placement, General
    department = Column(String(100), default="All")
    content = Column(Text, nullable=False)
    attachment_url = Column(String(500), nullable=True)
    source_url = Column(String(500), default="https://www.aitindia.in")
    publish_date = Column(DateTime, default=lambda: datetime.now(UTC))
    expiry_date = Column(DateTime, nullable=True)
    academic_year = Column(String(20), default="2026-27")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

# ----------------- 4. Knowledge & RAG Governance -----------------

class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"
    id = Column(String, primary_key=True, default=generate_uuid)
    source_type = Column(String(50), nullable=False) # OFFICIAL_WEBSITE, OFFICIAL_PDF, ADMIN_DATABASE, ADMIN_DOCUMENT, RAG_DOCUMENT, GEMINI, WEBSITE_CRAWL
    source_url = Column(String(500), nullable=False)
    canonical_url = Column(String(500), nullable=True)
    source_page = Column(String(255), nullable=True)
    title = Column(String(255), nullable=False)
    authority_score = Column(Float, default=1.0) # 1.0 for official website/docs
    content_hash = Column(String(64), nullable=True)
    raw_content = Column(Text, nullable=True)
    clean_text = Column(Text, nullable=True)
    category = Column(String(100), default="General")
    is_official = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=True)
    approval_status = Column(String(30), default="APPROVED") # PENDING, APPROVED, REJECTED, ARCHIVED
    retrieved_at = Column(DateTime, default=lambda: datetime.now(UTC))
    last_crawled_at = Column(DateTime, default=lambda: datetime.now(UTC))
    last_changed_at = Column(DateTime, nullable=True)
    verification_status = Column(String(30), default="VERIFIED")
    ai_visible = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    last_verified_at = Column(DateTime, nullable=True)
    verified_by = Column(String(100), nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    is_stale = Column(Boolean, default=False)
    version = Column(Integer, default=1)
    source_metadata = Column(JSON, default=dict)

    documents = relationship("KnowledgeDocument", back_populates="source", cascade="all, delete-orphan")
    pending_updates = relationship("PendingKnowledgeUpdate", back_populates="source", cascade="all, delete-orphan")

class PendingKnowledgeUpdate(Base):
    __tablename__ = "pending_knowledge_updates"
    id = Column(String, primary_key=True, default=generate_uuid)
    source_id = Column(String, ForeignKey("knowledge_sources.id"), nullable=True)
    source_url = Column(String(500), nullable=False)
    title = Column(String(255), nullable=False)
    category = Column(String(100), default="General")
    source_type = Column(String(50), default="OFFICIAL_WEBSITE") # OFFICIAL_WEBSITE, OFFICIAL_PDF, ADMIN_DOCUMENT
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=False)
    clean_text = Column(Text, nullable=True)
    change_type = Column(String(50), default="MODIFIED") # NEW, MODIFIED, DELETED
    change_summary = Column(Text, nullable=True)
    content_hash = Column(String(64), nullable=False)
    approval_status = Column(String(30), default="PENDING") # PENDING, APPROVED, REJECTED, ARCHIVED
    detected_at = Column(DateTime, default=lambda: datetime.now(UTC))
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    update_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    source = relationship("KnowledgeSource", back_populates="pending_updates")

class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    id = Column(String, primary_key=True, default=generate_uuid)
    source_id = Column(String, ForeignKey("knowledge_sources.id"), nullable=False)
    title = Column(String(255), nullable=False)
    doc_type = Column(String(50), default="HTML") # HTML, PDF, DOCX, FAQ
    raw_content = Column(Text, nullable=False)
    clean_text = Column(Text, nullable=False)
    doc_metadata = Column(JSON, default=dict)
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    total_pages = Column(Integer, default=0)
    language = Column(String(10), default="en")
    ocr_processed = Column(Boolean, default=False)
    security_scanned = Column(Boolean, default=False)
    security_scan_result = Column(String(30), default="PENDING") # PENDING, CLEAN, MALICIOUS
    file_hash = Column(String(64), nullable=True)

    source = relationship("KnowledgeSource", back_populates="documents")
    chunks = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, ForeignKey("knowledge_documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding_json = Column(JSON, nullable=True) # Stored vector representation
    keywords = Column(String(500), nullable=True)
    section_title = Column(String(255), nullable=True)
    page_number = Column(Integer, nullable=True)
    paragraph_index = Column(Integer, nullable=True)
    heading_level = Column(Integer, nullable=True) # 1-6 for h1-h6
    chunk_metadata = Column(JSON, default=dict)
    department = Column(String(100), nullable=True)
    course = Column(String(50), nullable=True)
    semester = Column(Integer, nullable=True)
    subject = Column(String(100), nullable=True)
    academic_year = Column(String(20), nullable=True)
    source_type = Column(String(50), nullable=True)
    event = Column(String(200), nullable=True)
    date = Column(String(30), nullable=True)
    language = Column(String(10), default="en")
    verification_status = Column(String(30), default="VERIFIED")
    freshness_score = Column(Float, default=1.0)
    last_updated = Column(DateTime, default=lambda: datetime.now(UTC))
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    document = relationship("KnowledgeDocument", back_populates="chunks")

class KnowledgeConflict(Base):
    __tablename__ = "knowledge_conflicts"
    id = Column(String, primary_key=True, default=generate_uuid)
    topic = Column(String(150), nullable=False) # e.g. "BCA Fee 2026-27"
    source_a_type = Column(String(50), nullable=False) # e.g. "WEBSITE"
    source_a_value = Column(Text, nullable=False)
    source_a_ref = Column(String(255), nullable=True)
    source_b_type = Column(String(50), nullable=False) # e.g. "DATABASE"
    source_b_value = Column(Text, nullable=False)
    source_b_ref = Column(String(255), nullable=True)
    status = Column(String(30), default="OPEN") # OPEN, RESOLVED, DISMISSED
    resolution_choice = Column(String(50), nullable=True) # KEEP_WEBSITE, KEEP_DATABASE, CUSTOM_OVERRIDE
    resolved_by = Column(String(100), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    resolved_at = Column(DateTime, nullable=True)

# ----------------- 5. Conversations, Voice & AI Audits -----------------

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True) # Optional for public guest chat
    title = Column(String(255), default="New Conversation")
    mode = Column(String(30), default="TEXT") # TEXT, VOICE
    is_pinned = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")

class Message(Base):
    __tablename__ = "messages"
    id = Column(String, primary_key=True, default=generate_uuid)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False) # user, assistant, system
    content = Column(Text, nullable=False)
    language = Column(String(10), default="en") # en, hi, gu, hinglish
    intent = Column(String(50), nullable=True)
    entities = Column(JSON, default=dict)
    selected_source = Column(String(50), nullable=True) # DATABASE, OFFICIAL_RAG, GEMINI, LOCAL_AI
    source_metadata = Column(JSON, default=dict) # citations, source cards, record IDs
    images_json = Column(JSON, default=list) # List of image objects {url, caption, source_url}
    voice_asset_id = Column(String, nullable=True)
    confidence_score = Column(Float, default=1.0)
    latency_ms = Column(Integer, default=0)
    feedback = Column(String(20), nullable=True) # helpful, unhelpful, reported
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    conversation = relationship("Conversation", back_populates="messages")

class VoiceAsset(Base):
    __tablename__ = "voice_assets"
    id = Column(String, primary_key=True, default=generate_uuid)
    text_content = Column(Text, nullable=False)
    language = Column(String(10), default="en")
    audio_format = Column(String(10), default="wav") # wav, mp3
    file_path = Column(String(500), nullable=False)
    duration_seconds = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

class SupportTicket(Base):
    __tablename__ = "support_tickets"
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    department = Column(String(100), default="Administration")
    priority = Column(String(20), default="MEDIUM") # LOW, MEDIUM, HIGH, URGENT
    status = Column(String(30), default="OPEN") # OPEN, IN_PROGRESS, RESOLVED, CLOSED
    ai_summary = Column(Text, nullable=True)
    admin_response = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    user = relationship("User", back_populates="support_tickets")

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    
    user = relationship("User")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True, default=generate_uuid)
    actor_id = Column(String, nullable=True) # User ID or SYSTEM
    actor_role = Column(String(50), default="SYSTEM")
    action = Column(String(100), nullable=False) # e.g. UPDATE_BCA_FEE, PUBLISH_DOCUMENT, RESOLVE_CONFLICT
    target_entity = Column(String(100), nullable=False) # e.g. Fee, KnowledgeSource, User
    details = Column(JSON, default=dict)
    ip_address = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC))

# ----------------- 6. ML Models & Datasets Registry -----------------

class TrainingExample(Base):
    __tablename__ = "training_examples"
    id = Column(String, primary_key=True, default=generate_uuid)
    text = Column(Text, nullable=False)
    language = Column(String(10), default="en")
    predicted_intent = Column(String(100), nullable=True)
    approved_intent = Column(String(100), nullable=True)
    status = Column(String(30), default="PENDING") # PENDING, APPROVED, REJECTED
    source = Column(String(50), default="STUDENT_FEEDBACK") # STUDENT_FEEDBACK, ADMIN_ENTRY, SYNTHETIC
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(String(100), nullable=True)
    metadata_json = Column(JSON, default=dict)

class MLDataset(Base):
    __tablename__ = "ml_datasets"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(150), nullable=False)
    task = Column(String(50), default="INTENT_CLASSIFICATION")
    version = Column(String(20), default="v1.0")
    total_samples = Column(Integer, default=0)
    data_path = Column(String(500), nullable=True)
    is_scrubbed_pii = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

class MLModel(Base):
    __tablename__ = "ml_models"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(150), nullable=False)
    task = Column(String(50), default="INTENT_CLASSIFICATION")
    version = Column(String(20), default="v1.0")
    model_type = Column(String(50), default="NeuralNetwork")
    accuracy = Column(Float, default=0.0)
    f1_score = Column(Float, default=0.0)
    is_active = Column(Boolean, default=False)
    model_path = Column(String(500), nullable=True)
    dataset_version = Column(String(20), nullable=True)
    deployment_state = Column(String(30), default="PENDING") # PENDING, DEPLOYED, ROLLED_BACK
    validation_status = Column(String(30), default="PENDING") # PENDING, VALIDATED, FAILED
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

# ----------------- 7. Website Sync & Freshness Tracking -----------------

class WebsiteSyncState(Base):
    __tablename__ = "website_sync_states"
    id = Column(String, primary_key=True, default=generate_uuid)
    source_url = Column(String(500), nullable=False, index=True)
    content_hash = Column(String(64), nullable=False, index=True)
    first_discovered_at = Column(DateTime, default=lambda: datetime.now(UTC))
    last_fetched_at = Column(DateTime, default=lambda: datetime.now(UTC))
    last_changed_at = Column(DateTime, nullable=True)
    indexed_at = Column(DateTime, nullable=True)
    freshness_status = Column(String(30), default="FRESH") # FRESH, STALE, UNKNOWN
    sync_status = Column(String(30), default="PENDING") # PENDING, SYNCED, FAILED
    current_version = Column(Integer, default=1)
    previous_version = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    page_title = Column(String(255), nullable=True)
    change_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

class WebsiteContentVersion(Base):
    __tablename__ = "website_content_versions"
    id = Column(String, primary_key=True, default=generate_uuid)
    source_url = Column(String(500), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    content_hash = Column(String(64), nullable=False)
    change_type = Column(String(30), default="INITIAL") # INITIAL, MODIFIED, DELETED
    change_summary = Column(Text, nullable=True)
    previous_content_hash = Column(String(64), nullable=True)
    raw_html = Column(Text, nullable=True)
    clean_text = Column(Text, nullable=True)
    page_title = Column(String(255), nullable=True)
    change_timestamp = Column(DateTime, default=lambda: datetime.now(UTC))
    indexed_at = Column(DateTime, nullable=True)
    is_current = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

class WebsiteSyncReport(Base):
    __tablename__ = "website_sync_reports"
    id = Column(String, primary_key=True, default=generate_uuid)
    sync_timestamp = Column(DateTime, default=lambda: datetime.now(UTC))
    total_pages_processed = Column(Integer, default=0)
    new_pages = Column(Integer, default=0)
    modified_pages = Column(Integer, default=0)
    unchanged_pages = Column(Integer, default=0)
    deleted_pages = Column(Integer, default=0)
    failed_pages = Column(Integer, default=0)
    sync_duration_seconds = Column(Float, default=0.0)
    status = Column(String(30), default="COMPLETED") # COMPLETED, PARTIAL, FAILED
    error_details = Column(JSON, default=list)
    sync_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
