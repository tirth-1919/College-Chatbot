"""
Enhanced Authentication API Routes
ChatGPT-style authentication with improved UX
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.security.enhanced_auth import EnhancedAuthService
from backend.app.security.auth import create_access_token
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter(prefix="/auth/enhanced", tags=["Enhanced Authentication"])


class EmailValidationRequest(BaseModel):
    email: str
    full_name: str


class EmailVerificationRequest(BaseModel):
    temp_user_id: int
    code: str


class AccountCreationRequest(BaseModel):
    email: str
    full_name: str
    password: str = Field(..., min_length=8)
    role: str = "STUDENT"
    department_id: Optional[int] = None
    course_id: Optional[int] = None
    current_semester: Optional[int] = None


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/signup/initiate")
async def initiate_signup(request: EmailValidationRequest, db: Session = Depends(get_db)):
    """Step 1: Initiate signup with email validation"""
    auth_service = EnhancedAuthService(db)
    result = auth_service.initiate_signup(request.email, request.full_name)
    
    if result['success']:
        return JSONResponse(result)
    else:
        raise HTTPException(status_code=400, detail=result['error'])


@router.post("/signup/verify")
async def verify_email(request: EmailVerificationRequest, db: Session = Depends(get_db)):
    """Step 2: Verify email with code"""
    auth_service = EnhancedAuthService(db)
    result = auth_service.verify_email(request.temp_user_id, request.code)
    
    if result['success']:
        return JSONResponse(result)
    else:
        raise HTTPException(status_code=400, detail=result['error'])


@router.post("/signup/complete")
async def complete_signup(request: AccountCreationRequest, db: Session = Depends(get_db)):
    """Step 3: Complete account creation"""
    auth_service = EnhancedAuthService(db)
    result = auth_service.complete_signup(
        email=request.email,
        full_name=request.full_name,
        password=request.password,
        role=request.role,
        department_id=request.department_id,
        course_id=request.course_id,
        current_semester=request.current_semester
    )
    
    if result['success']:
        return JSONResponse(result)
    else:
        raise HTTPException(status_code=400, detail=result['error'])


@router.post("/password-reset/initiate")
async def initiate_password_reset(request: PasswordResetRequest, db: Session = Depends(get_db)):
    """Initiate password reset"""
    auth_service = EnhancedAuthService(db)
    result = auth_service.initiate_password_reset(request.email)
    return JSONResponse(result)


@router.post("/password-reset/confirm")
async def reset_password(request: PasswordResetConfirmRequest, db: Session = Depends(get_db)):
    """Confirm password reset with token"""
    auth_service = EnhancedAuthService(db)
    result = auth_service.reset_password(request.token, request.new_password)
    
    if result['success']:
        return JSONResponse(result)
    else:
        raise HTTPException(status_code=400, detail=result['error'])


@router.post("/login")
async def enhanced_login(request: LoginRequest, db: Session = Depends(get_db)):
    """Enhanced login with better error messages"""
    from backend.app.models.entities import User
    from backend.app.security.auth import verify_password
    
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Email or password is incorrect"
        )
    
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Email or password is incorrect"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Account is not active. Please verify your email."
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    
    return JSONResponse({
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role
        }
    })