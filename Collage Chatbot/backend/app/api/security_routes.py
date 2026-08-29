"""
Security API Routes for AIT AI Assistant
Provides CSRF token generation and security-related endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from backend.app.security.csrf import CSRFTokenGenerator, get_csrf_token_generator
from backend.app.security.auth import get_current_user
from backend.app.models.entities import User
from backend.app.config import settings

router = APIRouter(prefix="/security", tags=["Security"])

# Initialize CSRF token generator
csrf_generator = get_csrf_token_generator(settings.CSRF_SECRET_KEY if hasattr(settings, 'CSRF_SECRET_KEY') else None)


@router.get("/csrf-token")
async def get_csrf_token():
    """
    Get CSRF token for frontend forms
    Used for protecting state-changing operations
    """
    try:
        token = csrf_generator.generate_token()
        return JSONResponse({
            "csrf_token": token,
            "message": "CSRF token generated successfully"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate CSRF token: {str(e)}")


@router.get("/security-status")
async def get_security_status(current_user: User = Depends(get_current_user)):
    """
    Get current security status for authenticated users
    """
    return JSONResponse({
        "csrf_protection": "enabled",
        "rate_limiting": "enabled",
        "security_headers": "enabled",
        "file_validation": "enabled",
        "malware_scanning": "available",
        "auth_required": True,
        "user_authenticated": True,
        "user_role": current_user.role
    })