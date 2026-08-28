from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.entities import User, Role, Course, Department
from backend.app.schemas.schemas import UserLogin, UserRegister, Token, UserResponse
from backend.app.security.auth import verify_password, get_password_hash, create_access_token, require_authenticated_user
from backend.app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
def login(form_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.email).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    roles = [role.name for role in user.roles]
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "roles": roles},
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "roles": roles,
            "enrollment_number": user.enrollment_number,
            "current_semester": user.current_semester
        }
    }

@router.post("/register", response_model=Token)
def register(data: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email is already registered")

    role = db.query(Role).filter(Role.name == data.role.upper()).first()
    if not role:
        role = db.query(Role).filter(Role.name == "STUDENT").first()

    course = db.query(Course).filter(Course.code == data.course_code.upper()).first() if data.course_code else None

    new_user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name,
        enrollment_number=data.enrollment_number,
        is_active=True,
        course_id=course.id if course else None,
        current_semester=data.semester or 1
    )
    if role:
        new_user.roles.append(role)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    roles = [r.name for r in new_user.roles]
    access_token = create_access_token(data={"sub": new_user.id, "email": new_user.email, "roles": roles})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": new_user.id,
            "email": new_user.email,
            "full_name": new_user.full_name,
            "roles": roles,
            "enrollment_number": new_user.enrollment_number,
            "current_semester": new_user.current_semester
        }
    }

@router.get("/me")
def get_current_user_profile(current_user: User = Depends(require_authenticated_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "enrollment_number": current_user.enrollment_number,
        "roles": [r.name for r in current_user.roles],
        "is_active": current_user.is_active,
        "course_id": current_user.course_id,
        "current_semester": current_user.current_semester,
        "created_at": current_user.created_at.isoformat()
    }
