from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field

# ----------------- Auth Schemas -----------------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class UserLogin(BaseModel):
    email: str
    password: str

class UserRegister(BaseModel):
    email: str
    password: str
    full_name: str
    enrollment_number: Optional[str] = None
    role: str = "STUDENT"
    course_code: Optional[str] = "BCA"
    semester: Optional[int] = 1

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    enrollment_number: Optional[str]
    is_active: bool
    roles: List[str]
    course_id: Optional[str]
    current_semester: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True

# ----------------- Academic Schemas -----------------
class CourseSchema(BaseModel):
    id: Optional[str] = None
    code: str
    name: str
    department_id: Optional[str] = None
    duration_years: int = 3
    total_semesters: int = 6
    degree_level: str = "Undergraduate"
    description: Optional[str] = None

class SubjectSchema(BaseModel):
    id: Optional[str] = None
    code: str
    name: str
    course_id: str
    semester: int
    credits: int = 4
    syllabus_summary: Optional[str] = None
    academic_year: str = "2026-27"

class FacultySchema(BaseModel):
    id: Optional[str] = None
    employee_id: str
    name: str
    designation: str = "Assistant Professor"
    department_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    office_room: Optional[str] = None
    office_hours: Optional[str] = None
    qualification: Optional[str] = None
    ai_visible: bool = True

class FacultySubjectCreate(BaseModel):
    faculty_id: str
    subject_id: str
    division: str = "A"
    academic_year: str = "2026-27"

class FeeSchema(BaseModel):
    id: Optional[str] = None
    course_code: str
    academic_year: str = "2026-27"
    tuition_fee: float
    exam_fee: float = 1500.0
    other_charges: float = 1000.0
    total_fee: Optional[float] = None
    payment_terms: str = "Semester-wise or Annual"
    verification_status: str = "VERIFIED"

class TimetableSchema(BaseModel):
    id: Optional[str] = None
    course_code: str
    semester: int
    division: str = "A"
    day_of_week: str
    start_time: str
    end_time: str
    subject_name: str
    faculty_name: str
    room_number: str
    academic_year: str = "2026-27"

class ExamSchema(BaseModel):
    id: Optional[str] = None
    course_code: str
    semester: int
    subject_code: str
    subject_name: str
    exam_type: str = "End-Term"
    exam_date: str
    start_time: str
    end_time: str
    room_number: str = "Block A, Exam Hall"
    academic_year: str = "2026-27"

class ResultSchema(BaseModel):
    id: Optional[str] = None
    student_enrollment: str
    course_code: str
    semester: int
    subject_code: str
    subject_name: str
    grade: str
    spi: Optional[float] = None
    cpi: Optional[float] = None

# ----------------- Visual & Campus Media Schemas -----------------
class ImageCard(BaseModel):
    image_url: str
    source_url: str
    source_page: str
    caption: Optional[str] = None
    alt_text: Optional[str] = None
    year: Optional[str] = None
    category: Optional[str] = None

class FacilitySchema(BaseModel):
    id: Optional[str] = None
    name: str
    category: str
    location: Optional[str] = None
    description: Optional[str] = None
    timings: Optional[str] = "08:00 AM - 05:00 PM"
    images: List[ImageCard] = []

class EventSchema(BaseModel):
    id: Optional[str] = None
    name: str
    event_type: str = "Technical"
    date_start: str
    date_end: Optional[str] = None
    academic_year: str
    calendar_year: int
    description: str
    department: str = "Campus-wide"
    organizer: str = "AIT Student Council"
    official_source_url: str = "https://www.aitindia.in/events"
    images: List[ImageCard] = []

class NoticeSchema(BaseModel):
    id: Optional[str] = None
    title: str
    category: str = "Academic"
    department: str = "All"
    content: str
    attachment_url: Optional[str] = None
    publish_date: Optional[datetime] = None
    academic_year: str = "2026-27"

# ----------------- RAG & Conflict Schemas -----------------
class SourceCard(BaseModel):
    source_type: str # DATABASE, OFFICIAL_WEBSITE, OFFICIAL_DOCUMENT, GENERAL_AI
    title: str
    source_url: Optional[str] = None
    page_or_record: Optional[str] = None
    authority_level: str = "PRIORITY 1" # PRIORITY 1, PRIORITY 2, PRIORITY 3
    verified_at: Optional[str] = None

class KnowledgeConflictSchema(BaseModel):
    id: str
    topic: str
    source_a_type: str
    source_a_value: str
    source_a_ref: Optional[str]
    source_b_type: str
    source_b_value: str
    source_b_ref: Optional[str]
    status: str
    resolution_choice: Optional[str]
    created_at: datetime

class ResolveConflictRequest(BaseModel):
    conflict_id: str
    resolution_choice: str # KEEP_WEBSITE, KEEP_DATABASE, CUSTOM_OVERRIDE
    custom_value: Optional[str] = None
    resolution_notes: Optional[str] = None

# ----------------- Chat & Voice Schemas -----------------
class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str
    language: Optional[str] = None # Auto-detect if None
    mode: str = "TEXT" # TEXT, VOICE
    stream: bool = False

class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    id: Optional[str] = None
    role: str = "assistant"
    answer: str
    content: Optional[str] = None
    status: str = "complete"
    intent: str
    entities: Dict[str, Any] = {}
    selected_source: str
    confidence: float
    sources: List[SourceCard] = []
    images: List[ImageCard] = []
    suggested_followups: List[str] = []
    voice_asset_id: Optional[str] = None
    is_general_knowledge: bool = False
    timestamp: str

class VoiceTranscribeResponse(BaseModel):
    transcript: str
    language: str
    confidence: float

class VoiceSynthesizeRequest(BaseModel):
    text: str
    language: str = "en"
    voice_id: Optional[str] = None

class FeedbackRequest(BaseModel):
    message_id: str
    feedback: str # helpful, unhelpful, reported
    comment: Optional[str] = None

# ----------------- Support & Admin Schemas -----------------
class SupportTicketCreate(BaseModel):
    subject: str
    description: str
    department: str = "Administration"
    priority: str = "MEDIUM"

class AuditLogSchema(BaseModel):
    id: str
    actor_role: str
    action: str
    target_entity: str
    details: Dict[str, Any]
    timestamp: datetime

class ApproveTrainingExampleRequest(BaseModel):
    approved_intent: str

class RejectKnowledgeRequest(BaseModel):
    reason: Optional[str] = None

