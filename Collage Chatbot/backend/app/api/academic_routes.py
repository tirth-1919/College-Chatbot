from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.entities import (
    Course, Subject, Faculty, FacultySubject, Fee, Timetable, Exam, Result, AuditLog, User
)
from backend.app.schemas.schemas import (
    CourseSchema, SubjectSchema, FacultySchema, FeeSchema, TimetableSchema, ExamSchema, ResultSchema
)
from backend.app.security.auth import require_role, get_current_user

router = APIRouter(prefix="/academic", tags=["Academic Data & Admin CRUD"])

# ----------------- Courses -----------------
@router.get("/courses")
def get_courses(db: Session = Depends(get_db)):
    courses = db.query(Course).all()
    return [
        {
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "duration_years": c.duration_years,
            "total_semesters": c.total_semesters,
            "degree_level": c.degree_level,
            "description": c.description,
            "department_name": c.department.name if c.department else ""
        }
        for c in courses
    ]

# ----------------- Fees (Admin CRUD + Read) -----------------
@router.get("/fees")
def get_fees(
    course_code: Optional[str] = None,
    academic_year: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Fee)
    if course_code:
        course = db.query(Course).filter(Course.code == course_code.upper()).first()
        if course:
            query = query.filter(Fee.course_id == course.id)
    if academic_year:
        query = query.filter(Fee.academic_year == academic_year)
        
    fees = query.all()
    return [
        {
            "id": f.id,
            "course_code": f.course.code,
            "course_name": f.course.name,
            "academic_year": f.academic_year,
            "tuition_fee": f.tuition_fee,
            "exam_fee": f.exam_fee,
            "other_charges": f.other_charges,
            "total_fee": f.total_fee,
            "payment_terms": f.payment_terms,
            "verification_status": f.verification_status,
            "version": f.version,
            "ai_visible": f.ai_visible,
            "created_at": f.created_at.isoformat()
        }
        for f in fees
    ]

@router.post("/fees", dependencies=[Depends(require_role(["ADMIN", "SUPER_ADMIN"]))])
def create_or_update_fee(payload: FeeSchema, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.code == payload.course_code.upper()).first()
    if not course:
        raise HTTPException(status_code=404, detail=f"Course '{payload.course_code}' not found")

    existing = db.query(Fee).filter(
        Fee.course_id == course.id,
        Fee.academic_year == payload.academic_year
    ).first()

    total = payload.tuition_fee + payload.exam_fee + payload.other_charges

    if existing:
        existing.tuition_fee = payload.tuition_fee
        existing.exam_fee = payload.exam_fee
        existing.other_charges = payload.other_charges
        existing.total_fee = total
        existing.payment_terms = payload.payment_terms
        existing.verification_status = payload.verification_status
        existing.version += 1
        db.commit()
        db.refresh(existing)
        target_fee = existing
        action = "UPDATE_FEE"
    else:
        new_fee = Fee(
            course_id=course.id,
            academic_year=payload.academic_year,
            tuition_fee=payload.tuition_fee,
            exam_fee=payload.exam_fee,
            other_charges=payload.other_charges,
            total_fee=total,
            payment_terms=payload.payment_terms,
            verification_status=payload.verification_status
        )
        db.add(new_fee)
        db.commit()
        db.refresh(new_fee)
        target_fee = new_fee
        action = "CREATE_FEE"

    # Audit Log
    audit = AuditLog(
        actor_role="ADMIN",
        action=action,
        target_entity="Fee",
        details={
            "course": course.code,
            "academic_year": target_fee.academic_year,
            "tuition_fee": target_fee.tuition_fee,
            "version": target_fee.version
        }
    )
    db.add(audit)
    db.commit()

    return {
        "success": True,
        "message": f"Fee record for {course.code} ({target_fee.academic_year}) saved successfully",
        "fee_id": target_fee.id,
        "tuition_fee": target_fee.tuition_fee,
        "total_fee": target_fee.total_fee
    }

# ----------------- Faculty & Mappings -----------------
@router.get("/faculty")
def get_faculty_list(db: Session = Depends(get_db)):
    faculty_members = db.query(Faculty).filter(Faculty.is_active == True).all()
    results = []
    for f in faculty_members:
        subjects_taught = [m.subject.name for m in f.subject_mappings if m.subject]
        results.append({
            "id": f.id,
            "employee_id": f.employee_id,
            "name": f.name,
            "designation": f.designation,
            "department": f.department.name if f.department else "",
            "email": f.email,
            "office_room": f.office_room,
            "office_hours": f.office_hours,
            "qualification": f.qualification,
            "subjects_taught": subjects_taught
        })
    return results

# ----------------- Subjects -----------------
@router.get("/subjects")
def get_subjects(course_code: Optional[str] = None, semester: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Subject).filter(Subject.is_active == True)
    if course_code:
        course = db.query(Course).filter(Course.code == course_code.upper()).first()
        if course:
            query = query.filter(Subject.course_id == course.id)
    if semester:
        query = query.filter(Subject.semester == semester)
    subjects = query.all()
    return [
        {
            "id": s.id,
            "code": s.code,
            "name": s.name,
            "course": s.course.code if s.course else "",
            "semester": s.semester,
            "credits": s.credits,
            "syllabus_summary": s.syllabus_summary,
            "academic_year": s.academic_year
        }
        for s in subjects
    ]

# ----------------- Timetables -----------------
@router.get("/timetable")
def get_timetable(
    course_code: str = "BCA",
    semester: int = 4,
    day: Optional[str] = None,
    db: Session = Depends(get_db)
):
    course = db.query(Course).filter(Course.code == course_code.upper()).first()
    if not course:
        return []
    query = db.query(Timetable).filter(Timetable.course_id == course.id, Timetable.semester == semester)
    if day:
        query = query.filter(Timetable.day_of_week.ilike(day))
    tt_entries = query.order_by(Timetable.start_time).all()
    return [
        {
            "id": t.id,
            "day": t.day_of_week,
            "start_time": t.start_time,
            "end_time": t.end_time,
            "subject": t.subject_name,
            "faculty": t.faculty_name,
            "room": t.room_number,
            "division": t.division
        }
        for t in tt_entries
    ]

# ----------------- Exams -----------------
@router.get("/exams")
def get_exams(course_code: str = "BCA", semester: int = 4, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.code == course_code.upper()).first()
    if not course:
        return []
    exams = db.query(Exam).filter(Exam.course_id == course.id, Exam.semester == semester).all()
    return [
        {
            "id": e.id,
            "subject_code": e.subject_code,
            "subject_name": e.subject_name,
            "exam_type": e.exam_type,
            "date": e.exam_date,
            "start_time": e.start_time,
            "end_time": e.end_time,
            "room": e.room_number,
            "status": e.status
        }
        for e in exams
    ]

# ----------------- Results -----------------
@router.get("/results")
def get_results(
    enrollment: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    # Private student results
    target_enrollment = enrollment or (current_user.enrollment_number if current_user else None)
    if not target_enrollment:
        return []
    results = db.query(Result).filter(Result.student_enrollment == target_enrollment).all()
    return [
        {
            "id": r.id,
            "subject_code": r.subject_code,
            "subject_name": r.subject_name,
            "semester": r.semester,
            "grade": r.grade,
            "spi": r.spi,
            "cpi": r.cpi,
            "academic_year": r.academic_year
        }
        for r in results
    ]
