import os
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.app.database import SessionLocal, engine, Base
from backend.app.models.entities import (
    Role, Permission, User, Department, Course, Subject, Faculty, FacultySubject,
    Fee, Timetable, Exam, Result, Facility, FacilityImage, Event, EventImage, Notice,
    KnowledgeSource, KnowledgeDocument, KnowledgeChunk, KnowledgeConflict
)
from backend.app.security.auth import get_password_hash

def seed_database():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # Check if already seeded
        if db.query(Role).first():
            print("Database already seeded. Skipping initial seeding.")
            return

        print("Seeding AIT College AI Assistant Master Database...")

        # 1. Roles & Permissions
        admin_role = Role(name="ADMIN", description="College Administrator with full knowledge & data management")
        student_role = Role(name="STUDENT", description="Authenticated AIT Student with personalized academic access")
        faculty_role = Role(name="FACULTY", description="Faculty Member with class and subject management")
        public_role = Role(name="PUBLIC", description="Public Visitor with access to official public knowledge")
        super_admin_role = Role(name="SUPER_ADMIN", description="System Super Admin")

        db.add_all([admin_role, student_role, faculty_role, public_role, super_admin_role])
        db.flush()

        # 2. Departments
        dept_ca = Department(code="CA", name="Department of Computer Applications", head_of_department="Dr. Rajesh Patel")
        dept_cse = Department(code="CSE", name="Department of Computer Engineering", head_of_department="Dr. Samir Shah")
        dept_it = Department(code="IT", name="Department of Information Technology", head_of_department="Prof. Neha Trivedi")
        dept_mgmt = Department(code="MGMT", name="Department of Management Studies", head_of_department="Dr. Priya Mehta")

        db.add_all([dept_ca, dept_cse, dept_it, dept_mgmt])
        db.flush()

        # 3. Courses
        course_bca = Course(
            code="BCA",
            name="Bachelor of Computer Applications",
            department_id=dept_ca.id,
            duration_years=3,
            total_semesters=6,
            degree_level="Undergraduate",
            description="3-year full-time undergraduate program specializing in software development and computing."
        )
        course_btech_cse = Course(
            code="BTECH_CSE",
            name="B.Tech in Computer Engineering",
            department_id=dept_cse.id,
            duration_years=4,
            total_semesters=8,
            degree_level="Undergraduate",
            description="4-year engineering program approved by AICTE & affiliated with Gujarat Technological University."
        )
        course_mca = Course(
            code="MCA",
            name="Master of Computer Applications",
            department_id=dept_ca.id,
            duration_years=2,
            total_semesters=4,
            degree_level="Postgraduate",
            description="2-year postgraduate professional degree in advanced computer applications."
        )

        db.add_all([course_bca, course_btech_cse, course_mca])
        db.flush()

        # 4. Users (Admin, Student, Faculty)
        admin_user = User(
            email="admin@aitindia.in",
            hashed_password=get_password_hash("Admin@123"),
            full_name="AIT Administrator",
            is_active=True,
            department_id=dept_ca.id
        )
        admin_user.roles.append(admin_role)
        admin_user.roles.append(super_admin_role)

        student_user = User(
            email="student@aitindia.in",
            hashed_password=get_password_hash("Student@123"),
            full_name="Dharmik Patel",
            enrollment_number="210020107001",
            is_active=True,
            department_id=dept_ca.id,
            course_id=course_bca.id,
            current_semester=4
        )
        student_user.roles.append(student_role)

        faculty_user = User(
            email="faculty@aitindia.in",
            hashed_password=get_password_hash("Faculty@123"),
            full_name="Prof. Anjali Sharma",
            is_active=True,
            department_id=dept_ca.id
        )
        faculty_user.roles.append(faculty_role)

        db.add_all([admin_user, student_user, faculty_user])
        db.flush()

        # 5. Faculty Master Data
        f1 = Faculty(
            employee_id="AIT-FAC-101",
            name="Prof. Anjali Sharma",
            designation="Associate Professor",
            department_id=dept_ca.id,
            email="anjali.sharma@aitindia.in",
            phone="+91 98765 43210",
            office_room="Block B, Room 204",
            office_hours="Mon-Fri 2:00 PM - 4:00 PM",
            qualification="M.Tech (CSE), Ph.D (Pursuing)"
        )
        f2 = Faculty(
            employee_id="AIT-FAC-102",
            name="Prof. Ramesh Joshi",
            designation="Assistant Professor",
            department_id=dept_ca.id,
            email="ramesh.joshi@aitindia.in",
            office_room="Block B, Room 208",
            office_hours="Mon-Thu 11:00 AM - 1:00 PM",
            qualification="MCA, UGC-NET"
        )
        f3 = Faculty(
            employee_id="AIT-FAC-103",
            name="Dr. Rajesh Patel",
            designation="Professor & HOD",
            department_id=dept_ca.id,
            email="rajesh.patel@aitindia.in",
            office_room="Block B, HOD Cabin",
            office_hours="Tue-Fri 3:00 PM - 5:00 PM",
            qualification="Ph.D (Computer Science)"
        )

        db.add_all([f1, f2, f3])
        db.flush()

        # 6. Subjects for BCA Semester 4 & Mappings
        sub_dbms = Subject(
            code="BCA401",
            name="Database Management Systems (DBMS)",
            course_id=course_bca.id,
            semester=4,
            credits=4,
            syllabus_summary="Relational database design, ER modeling, Normalization (1NF-BCNF), SQL/PL-SQL queries, Transactions, ACID properties, Indexing and Concurrency control.",
            academic_year="2026-27"
        )
        sub_python = Subject(
            code="BCA402",
            name="Python Programming & Data Analysis",
            course_id=course_bca.id,
            semester=4,
            credits=4,
            syllabus_summary="Python syntax, OOP in Python, NumPy, Pandas, Matplotlib, Data visualization and API integrations.",
            academic_year="2026-27"
        )
        sub_ds = Subject(
            code="BCA403",
            name="Data Structures & Algorithms",
            course_id=course_bca.id,
            semester=4,
            credits=4,
            syllabus_summary="Arrays, Stacks, Queues, Linked Lists, Binary Trees, Graph traversals (BFS/DFS), Sorting and Searching algorithms.",
            academic_year="2026-27"
        )

        db.add_all([sub_dbms, sub_python, sub_ds])
        db.flush()

        # Faculty Mappings
        map_dbms = FacultySubject(faculty_id=f1.id, subject_id=sub_dbms.id, division="A", academic_year="2026-27")
        map_python = FacultySubject(faculty_id=f3.id, subject_id=sub_python.id, division="A", academic_year="2026-27")
        map_ds = FacultySubject(faculty_id=f2.id, subject_id=sub_ds.id, division="A", academic_year="2026-27")

        db.add_all([map_dbms, map_python, map_ds])
        db.flush()

        # 7. Exact Structured Fees (BCA Fee = ₹32,000 for 2026-27)
        fee_bca_2627 = Fee(
            course_id=course_bca.id,
            academic_year="2026-27",
            tuition_fee=32000.0,
            exam_fee=1500.0,
            other_charges=1000.0,
            total_fee=34500.0,
            payment_terms="Per semester (or ₹64,000 Annual)",
            verification_status="VERIFIED",
            ai_visible=True
        )
        fee_bca_2526 = Fee(
            course_id=course_bca.id,
            academic_year="2025-26",
            tuition_fee=30000.0,
            exam_fee=1500.0,
            other_charges=1000.0,
            total_fee=32500.0,
            payment_terms="Per semester",
            verification_status="VERIFIED",
            ai_visible=True
        )
        fee_btech = Fee(
            course_id=course_btech_cse.id,
            academic_year="2026-27",
            tuition_fee=78000.0,
            exam_fee=2000.0,
            other_charges=2000.0,
            total_fee=82000.0,
            payment_terms="Per semester as fixed by FRC Gujarat",
            verification_status="VERIFIED",
            ai_visible=True
        )

        db.add_all([fee_bca_2627, fee_bca_2526, fee_btech])
        db.flush()

        # 8. Timetable for BCA Sem 4 Div A
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        tt_entries = [
            Timetable(course_id=course_bca.id, semester=4, division="A", day_of_week="Monday", start_time="09:00 AM", end_time="10:00 AM", subject_name="Database Management Systems", faculty_name="Prof. Anjali Sharma", room_number="Room 204", academic_year="2026-27"),
            Timetable(course_id=course_bca.id, semester=4, division="A", day_of_week="Monday", start_time="10:00 AM", end_time="11:00 AM", subject_name="Python Programming", faculty_name="Dr. Rajesh Patel", room_number="Lab 3", academic_year="2026-27"),
            Timetable(course_id=course_bca.id, semester=4, division="A", day_of_week="Monday", start_time="11:30 AM", end_time="01:30 PM", subject_name="DBMS Practical Lab", faculty_name="Prof. Anjali Sharma", room_number="Computer Lab 2", academic_year="2026-27"),
            Timetable(course_id=course_bca.id, semester=4, division="A", day_of_week="Tuesday", start_time="09:00 AM", end_time="10:00 AM", subject_name="Data Structures & Algorithms", faculty_name="Prof. Ramesh Joshi", room_number="Room 204", academic_year="2026-27"),
            Timetable(course_id=course_bca.id, semester=4, division="A", day_of_week="Tuesday", start_time="10:00 AM", end_time="11:00 AM", subject_name="Database Management Systems", faculty_name="Prof. Anjali Sharma", room_number="Room 204", academic_year="2026-27"),
            Timetable(course_id=course_bca.id, semester=4, division="A", day_of_week="Wednesday", start_time="09:00 AM", end_time="10:00 AM", subject_name="Python Programming", faculty_name="Dr. Rajesh Patel", room_number="Room 204", academic_year="2026-27"),
            Timetable(course_id=course_bca.id, semester=4, division="A", day_of_week="Thursday", start_time="09:00 AM", end_time="10:00 AM", subject_name="Database Management Systems", faculty_name="Prof. Anjali Sharma", room_number="Room 204", academic_year="2026-27"),
            Timetable(course_id=course_bca.id, semester=4, division="A", day_of_week="Friday", start_time="10:00 AM", end_time="12:00 PM", subject_name="Data Structures Lab", faculty_name="Prof. Ramesh Joshi", room_number="Computer Lab 1", academic_year="2026-27"),
        ]
        db.add_all(tt_entries)
        db.flush()

        # 9. Exams
        exam1 = Exam(
            course_id=course_bca.id,
            semester=4,
            subject_code="BCA401",
            subject_name="Database Management Systems (DBMS)",
            exam_type="Mid-Term",
            exam_date="2026-10-12",
            start_time="10:00 AM",
            end_time="12:00 PM",
            room_number="Block B - Hall 3",
            academic_year="2026-27",
            status="SCHEDULED"
        )
        exam2 = Exam(
            course_id=course_bca.id,
            semester=4,
            subject_code="BCA402",
            subject_name="Python Programming",
            exam_type="Mid-Term",
            exam_date="2026-10-14",
            start_time="10:00 AM",
            end_time="12:00 PM",
            room_number="Block B - Hall 3",
            academic_year="2026-27",
            status="SCHEDULED"
        )
        db.add_all([exam1, exam2])
        db.flush()

        # 10. Official AIT Facilities & Images with Provenance
        fac_smartclass = Facility(
            name="Smart Classroom",
            category="Academic",
            location="Block A & Block B, 1st & 2nd Floors",
            description="Air-conditioned interactive smart classrooms equipped with ultra-HD touch displays, motorized acoustic projection, digital podiums, and high-speed campus Wi-Fi for multimedia interactive lectures.",
            timings="08:30 AM - 05:30 PM",
            contact_person="Campus Facilities Office"
        )
        fac_library = Facility(
            name="Central Library",
            category="Academic",
            location="Block A, Ground Floor",
            description="Comprehensive institutional library housing over 35,000+ technical and reference volumes, national/international journals, IEEE digital portal access, and dedicated silent reading cubicles.",
            timings="08:00 AM - 07:00 PM",
            contact_person="Chief Librarian (library@aitindia.in)"
        )
        fac_lab = Facility(
            name="High-Performance Computer Lab",
            category="Labs",
            location="Block B, 2nd Floor (Labs 1 to 6)",
            description="State-of-the-art computing laboratories equipped with Intel Core i7 workstations, dual displays, Gigabit LAN, specialized AI/ML tools, and Linux/Windows dual-boot environments.",
            timings="08:30 AM - 06:00 PM",
            contact_person="Lab In-charge"
        )
        fac_campus = Facility(
            name="AIT Green Campus & Sports Ground",
            category="Infrastructure",
            location="AIT Campus, Gota-Ognaj Road, Ahmedabad",
            description="Expansive lush-green campus spanning serene grounds, dedicated cricket & football field, basketball court, modern canteen, and seminar auditoriums.",
            timings="Open 24/7 for residents / 07:30 AM - 07:00 PM for day scholars",
            contact_person="Estate Officer"
        )

        db.add_all([fac_smartclass, fac_library, fac_lab, fac_campus])
        db.flush()

        # Facility Images (Real official AIT references)
        img_smartclass = FacilityImage(
            facility_id=fac_smartclass.id,
            image_url="https://www.aitindia.in/assets/images/facilities/smart_classroom.jpg",
            source_url="https://www.aitindia.in/facilities/smart-classrooms",
            source_page="AIT Official Website - Facilities",
            caption="AIT Interactive Smart Classroom with Digital Podium and HD Touch Projection",
            alt_text="AIT Smart Classroom",
            tags="smart class, classroom, lecture hall, interactive, audio video",
            approval_status="APPROVED",
            ai_visible=True
        )
        img_library = FacilityImage(
            facility_id=fac_library.id,
            image_url="https://www.aitindia.in/assets/images/facilities/central_library.jpg",
            source_url="https://www.aitindia.in/facilities/central-library",
            source_page="AIT Official Website - Library",
            caption="AIT Central Library and Digital Research Resource Center",
            alt_text="AIT Central Library",
            tags="library, books, reading room, research, journals",
            approval_status="APPROVED",
            ai_visible=True
        )
        img_lab = FacilityImage(
            facility_id=fac_lab.id,
            image_url="https://www.aitindia.in/assets/images/facilities/computer_lab_center.jpg",
            source_url="https://www.aitindia.in/facilities/computer-labs",
            source_page="AIT Official Website - Labs",
            caption="AIT Advanced Computer Application & AI Programming Laboratory",
            alt_text="AIT Computer Laboratory",
            tags="computer lab, lab, programming, hardware, systems",
            approval_status="APPROVED",
            ai_visible=True
        )
        img_campus = FacilityImage(
            facility_id=fac_campus.id,
            image_url="https://www.aitindia.in/assets/images/campus/ait_main_building.jpg",
            source_url="https://www.aitindia.in/about-us/campus",
            source_page="AIT Official Website - Campus",
            caption="Ahmedabad Institute of Technology Main Academic Block & Green Lawn",
            alt_text="AIT Main Academic Building",
            tags="campus, building, ait main block, entrance, infrastructure",
            approval_status="APPROVED",
            ai_visible=True
        )

        db.add_all([img_smartclass, img_library, img_lab, img_campus])
        db.flush()

        # 11. Historical Events (2024 & 2025)
        ev_ignite2025 = Event(
            name="TechFest IGNITE 2025",
            event_type="Technical",
            date_start="2025-02-21",
            date_end="2025-02-22",
            academic_year="2024-25",
            calendar_year=2025,
            description="National-level annual technical festival featuring RoboWars, Hackathon, Code Arena, Web3 sprint, and Tech Paper Presentations with over 3,500+ participants across India.",
            department="Computer & IT Engineering",
            organizer="AIT Technical Club & Student Council",
            official_source_url="https://www.aitindia.in/events/ignite-2025",
            status="COMPLETED"
        )
        ev_hackathon2024 = Event(
            name="AIT Smart Gujarat Hackathon 2024",
            event_type="Technical",
            date_start="2024-09-18",
            date_end="2024-09-19",
            academic_year="2024-25",
            calendar_year=2024,
            description="36-hour non-stop hackathon focused on AI in Healthcare, Smart Agriculture, and Citizen Governance in Gujarat.",
            department="Department of Computer Applications",
            organizer="AIT Innovation & Incubation Cell",
            official_source_url="https://www.aitindia.in/events/hackathon-2024",
            status="COMPLETED"
        )
        ev_tarang2024 = Event(
            name="Cultural Fest TARANG 2024",
            event_type="Cultural",
            date_start="2024-03-15",
            date_end="2024-03-16",
            academic_year="2023-24",
            calendar_year=2024,
            description="Annual grand cultural festival featuring inter-college music band face-off, Garba nights, dance drama, and celebrity star performance.",
            department="Campus-wide",
            organizer="AIT Cultural Committee",
            official_source_url="https://www.aitindia.in/events/tarang-2024",
            status="COMPLETED"
        )

        db.add_all([ev_ignite2025, ev_hackathon2024, ev_tarang2024])
        db.flush()

        # Event Images with Official Provenance
        img_ev_ignite = EventImage(
            event_id=ev_ignite2025.id,
            image_url="https://www.aitindia.in/assets/images/events/ignite2025_winners.jpg",
            source_url="https://www.aitindia.in/events/ignite-2025",
            source_page="AIT Official Website - Events Gallery 2025",
            caption="IGNITE 2025 Grand Hackathon Winners Award Ceremony at AIT Auditorium",
            alt_text="IGNITE 2025 Winners",
            tags="ignite 2025, techfest, award ceremony, event photo, winners",
            approval_status="APPROVED",
            ai_visible=True
        )
        img_ev_hackathon = EventImage(
            event_id=ev_hackathon2024.id,
            image_url="https://www.aitindia.in/assets/images/events/hackathon2024_coding.jpg",
            source_url="https://www.aitindia.in/events/hackathon-2024",
            source_page="AIT Official Website - Events Gallery 2024",
            caption="Participants during the 36-Hour Hackathon 2024 in AIT Computer Labs",
            alt_text="AIT Hackathon 2024 Teams Coding",
            tags="hackathon 2024, coding, students, 2024 events, lab coding",
            approval_status="APPROVED",
            ai_visible=True
        )
        img_ev_tarang = EventImage(
            event_id=ev_tarang2024.id,
            image_url="https://www.aitindia.in/assets/images/events/tarang2024_celebration.jpg",
            source_url="https://www.aitindia.in/events/tarang-2024",
            source_page="AIT Official Website - Cultural Gallery 2024",
            caption="Cultural Dance & Musical Performance at TARANG 2024 Open Stage",
            alt_text="TARANG 2024 Stage Celebration",
            tags="tarang 2024, cultural fest, dance, music, annual celebration",
            approval_status="APPROVED",
            ai_visible=True
        )

        db.add_all([img_ev_ignite, img_ev_hackathon, img_ev_tarang])
        db.flush()

        # 12. Official Notices
        notices = [
            Notice(
                title="BCA Semester 4 Mid-Term Examination Schedule Announced",
                category="Exam",
                department="Department of Computer Applications",
                content="The mid-term examination for BCA Semester 4 students will commence from October 12, 2026. Detailed seating arrangement will be posted outside Room 204.",
                source_url="https://www.aitindia.in/notices/bca-midterm-2026",
                academic_year="2026-27"
            ),
            Notice(
                title="Fee Payment Deadline for Academic Year 2026-27",
                category="Academic",
                department="All",
                content="All undergraduate and postgraduate students are requested to clear their academic semester tuition fee on or before September 15, 2026 to avoid late penalty.",
                source_url="https://www.aitindia.in/notices/fee-deadline-2026",
                academic_year="2026-27"
            )
        ]
        db.add_all(notices)

        # 12b. Student Exam Results (Dharmik Patel)
        res_dbms = Result(
            student_enrollment="210020107001",
            course_id=course_bca.id,
            subject_code="BCA401",
            subject_name="Database Management Systems",
            semester=4,
            grade="AA",
            spi=8.50,
            cpi=8.40,
            academic_year="2026-27"
        )
        res_python = Result(
            student_enrollment="210020107001",
            course_id=course_bca.id,
            subject_code="BCA402",
            subject_name="Python Programming",
            semester=4,
            grade="AB",
            spi=8.50,
            cpi=8.40,
            academic_year="2026-27"
        )
        db.add_all([res_dbms, res_python])

        # 13. Knowledge Source & RAG Document Seed
        ks_main = KnowledgeSource(
            source_type="WEBSITE_CRAWL",
            source_url="https://www.aitindia.in",
            source_page="Home & Admissions",
            title="AIT Official Website Portal",
            authority_score=1.0,
            verification_status="VERIFIED"
        )
        db.add(ks_main)
        db.flush()

        doc_about = KnowledgeDocument(
            source_id=ks_main.id,
            title="About Ahmedabad Institute of Technology",
            doc_type="HTML",
            raw_content="Ahmedabad Institute of Technology (AIT) was established in 2004 by the Ashok Education Landmark Trust. Approved by AICTE, New Delhi, and affiliated with Gujarat Technological University (GTU), AIT offers top-tier Bachelor and Master degrees in Engineering and Computer Applications.",
            clean_text="Ahmedabad Institute of Technology (AIT) was established in 2004 by the Ashok Education Landmark Trust. Approved by AICTE, New Delhi, and affiliated with Gujarat Technological University (GTU), AIT offers top-tier Bachelor and Master degrees in Engineering and Computer Applications located at Near Vasantnagar Township, Gota-Ognaj Road, Ahmedabad, Gujarat 382481."
        )
        db.add(doc_about)
        db.flush()

        chunk_about = KnowledgeChunk(
            document_id=doc_about.id,
            chunk_index=0,
            content=doc_about.clean_text,
            keywords="AIT, Ahmedabad Institute of Technology, established 2004, GTU, AICTE, Ashok Education Landmark Trust, address, location",
            section_title="About AIT"
        )
        db.add(chunk_about)

        db.commit()
        print("Database successfully seeded with official AIT data!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
