from datetime import timedelta, datetime, UTC
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.entities import User, Role, Course, Department
from backend.app.schemas.schemas import UserLogin, UserRegister, Token, UserResponse
from backend.app.security.auth import verify_password, get_password_hash, create_access_token, require_authenticated_user
from backend.app.security.google_oauth import GoogleOAuthService
from backend.app.security.password_reset import PasswordResetService
from backend.app.config import settings
from pydantic import BaseModel, EmailStr
import re

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

    # Update last login time
    user.last_login_at = datetime.now(UTC)
    db.commit()

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
            "current_semester": user.current_semester,
            "profile_image_url": user.profile_image_url,
            "is_verified": user.is_verified
        }
    }

@router.post("/register", response_model=Token)
def register(data: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email is already registered")

    # Public registration is always least-privilege; privileged roles are assigned administratively.
    role = db.query(Role).filter(Role.name == "STUDENT").first()
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


from pydantic import BaseModel

class ReAuthRequest(BaseModel):
    password: str
    action_type: str = "DESTRUCTIVE_ACTION"

class ReAuthResponse(BaseModel):
    success: bool
    reauth_token: str
    expires_in_minutes: int
    message: str

@router.post("/reauth", response_model=ReAuthResponse)
def reauthenticate_admin(
    payload: ReAuthRequest,
    current_user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db)
):
    from backend.app.models.entities import AuditLog
    from backend.app.security.auth import verify_password, create_reauth_token

    if not verify_password(payload.password, current_user.hashed_password):
        # Audit failed re-authentication attempt
        audit_failed = AuditLog(
            actor_role=current_user.roles[0].name if current_user.roles else "USER",
            action="REAUTH_FAILED",
            target_entity="UserSecurity",
            details={"email": current_user.email, "action_type": payload.action_type, "status": "DENIED"}
        )
        db.add(audit_failed)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Re-authentication failed: Invalid password"
        )

    # Success audit
    audit_ok = AuditLog(
        actor_role=current_user.roles[0].name if current_user.roles else "USER",
        action="REAUTH_SUCCESS",
        target_entity="UserSecurity",
        details={"email": current_user.email, "action_type": payload.action_type, "status": "GRANTED"}
    )
    db.add(audit_ok)
    db.commit()

    reauth_token = create_reauth_token(current_user.id, purpose=payload.action_type)
    return {
        "success": True,
        "reauth_token": reauth_token,
        "expires_in_minutes": settings.REAUTH_TOKEN_EXPIRE_MINUTES,
        "message": "Re-authentication successful. Token authorized for destructive operation."
    }


# ----------------- Google OAuth Routes -----------------

class GoogleAuthUrlResponse(BaseModel):
    auth_url: str
    state: str

@router.get("/google/auth-url", response_model=GoogleAuthUrlResponse)
def get_google_auth_url(redirect_uri: Optional[str] = Query(None)):
    """Get Google OAuth authorization URL"""
    google_service = GoogleOAuthService(db=None)  # We don't need DB for this
    auth_url = google_service.get_google_auth_url(redirect_uri)
    
    # Extract state from URL for response
    state = auth_url.split("state=")[-1] if "state=" in auth_url else ""
    
    return {
        "auth_url": auth_url,
        "state": state
    }

class GoogleCallbackRequest(BaseModel):
    code: str
    state: str

@router.post("/google/callback", response_model=Token)
def google_callback(payload: GoogleCallbackRequest, db: Session = Depends(get_db)):
    """Handle Google OAuth callback"""
    google_service = GoogleOAuthService(db)
    result = google_service.handle_google_callback(payload.code, payload.state)
    return result


# ----------------- Password Reset Routes -----------------

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ForgotPasswordResponse(BaseModel):
    success: bool
    message: str

@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Initiate password reset process"""
    reset_service = PasswordResetService(db)
    result = reset_service.initiate_password_reset(payload.email)
    return result

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: str

class ResetPasswordResponse(BaseModel):
    success: bool
    message: str
    error: Optional[str] = None

@router.post("/reset-password", response_model=ResetPasswordResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password with token"""
    # Validate password confirmation
    if payload.new_password != payload.confirm_password:
        return {
            "success": False,
            "message": "Password reset failed",
            "error": "Passwords do not match"
        }
    
    reset_service = PasswordResetService(db)
    result = reset_service.reset_password(payload.token, payload.new_password)
    
    if result["success"]:
        return {
            "success": True,
            "message": result["message"]
        }
    else:
        return {
            "success": False,
            "message": "Password reset failed",
            "error": result.get("error", "Unknown error")
        }

class ValidateTokenRequest(BaseModel):
    token: str

class ValidateTokenResponse(BaseModel):
    valid: bool
    message: str
    error: Optional[str] = None

@router.post("/validate-reset-token", response_model=ValidateTokenResponse)
def validate_reset_token(payload: ValidateTokenRequest, db: Session = Depends(get_db)):
    """Validate password reset token"""
    reset_service = PasswordResetService(db)
    result = reset_service.validate_token(payload.token)
    
    if result["valid"]:
        return {
            "valid": True,
            "message": result["message"]
        }
    else:
        return {
            "valid": False,
            "message": "Token validation failed",
            "error": result.get("error", "Invalid token")
        }


# ----------------- Enhanced Signup with Password Validation -----------------

class EnhancedUserRegister(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    confirm_password: str
    enrollment_number: Optional[str] = None
    course_code: Optional[str] = None
    semester: Optional[int] = None
    role: str = "STUDENT"

@router.post("/register/enhanced", response_model=Token)
def register_enhanced(data: EnhancedUserRegister, db: Session = Depends(get_db)):
    """Enhanced registration with password validation and confirmation"""
    # Validate password confirmation
    if data.password != data.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    # Validate password strength
    password_validation = _validate_password_strength(data.password)
    if not password_validation['valid']:
        raise HTTPException(status_code=400, detail=password_validation['error'])
    
    # Validate email format
    if not _validate_email_format(data.email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    # Check if email already exists
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email is already registered")
    
    # Get role
    # Public registration is always least-privilege; privileged roles are assigned administratively.
    role = db.query(Role).filter(Role.name == "STUDENT").first()
    if not role:
        role = db.query(Role).filter(Role.name == "STUDENT").first()
    
    # Get course if provided
    course = db.query(Course).filter(Course.code == data.course_code.upper()).first() if data.course_code else None
    
    # Create user
    new_user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name,
        enrollment_number=data.enrollment_number,
        is_active=True,
        is_verified=False,  # Will need email verification in production
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
            "current_semester": new_user.current_semester,
            "is_verified": new_user.is_verified
        }
    }


# ----------------- Helper Functions -----------------

def _validate_password_strength(password: str) -> dict:
    """Validate password strength"""
    if len(password) < 8:
        return {'valid': False, 'error': 'Password must be at least 8 characters'}
    
    if not any(c.isupper() for c in password):
        return {'valid': False, 'error': 'Password must contain at least one uppercase letter'}
    
    if not any(c.islower() for c in password):
        return {'valid': False, 'error': 'Password must contain at least one lowercase letter'}
    
    if not any(c.isdigit() for c in password):
        return {'valid': False, 'error': 'Password must contain at least one digit'}
    
    common_passwords = {'password', '12345678', 'qwerty', 'abc123'}
    if password.lower() in common_passwords:
        return {'valid': False, 'error': 'Password is too common'}
    
    return {'valid': True, 'error': None}

def _validate_email_format(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


