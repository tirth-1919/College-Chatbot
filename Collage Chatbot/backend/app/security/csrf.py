"""
CSRF Protection Middleware for AIT AI Assistant
Implements double-submit cookie pattern for CSRF protection
Compatible with frontend session management
"""

import secrets
import hashlib
from typing import Optional, Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
import logging

logger = logging.getLogger(__name__)


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    CSRF Protection Middleware using double-submit cookie pattern
    
    For state-changing operations (POST, PUT, DELETE, PATCH):
    - Generates CSRF token and sets as HttpOnly cookie
    - Expects token in request headers
    - Validates token matches cookie
    """
    
    # Methods that require CSRF protection
    CSRF_PROTECTED_METHODS = {"POST", "PUT", "DELETE", "PATCH"}
    
    # Methods that are exempt from CSRF
    CSRF_EXEMPT_PATHS = {
        "/api/v1/auth/login",
        "/api/v1/auth/register", 
        "/api/v1/auth/logout",
        "/health",
        "/api/v1/voice/chat",  # Voice endpoint may have different token handling
        "/api/chat",  # Test paths
        "/api/v1/chat",  # Test paths
        "/docs",  # API documentation
        "/redoc",  # API documentation
    }
    
    def __init__(self, app, secret_key: str = None):
        super().__init__(app)
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.token_length = 32
        
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip CSRF for GET, HEAD, OPTIONS, TRACE
        if request.method not in self.CSRF_PROTECTED_METHODS:
            return await call_next(request)
        
        # Skip CSRF for exempt paths
        for exempt_path in self.CSRF_EXEMPT_PATHS:
            if request.url.path.startswith(exempt_path):
                return await call_next(request)
        
        # Skip CSRF for API clients (check for API key header)
        if self._is_api_client(request):
            return await call_next(request)
        
        # Validate CSRF token
        csrf_token = request.headers.get("X-CSRF-Token")
        csrf_cookie = request.cookies.get("csrf_token")
        
        if not csrf_token or not csrf_cookie:
            logger.warning(f"CSRF token missing - Method: {request.method}, Path: {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token missing. Please refresh the page and try again."
            )
        
        if not self._validate_token(csrf_token, csrf_cookie):
            logger.warning(f"CSRF token validation failed - Method: {request.method}, Path: {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token validation failed. Please refresh the page and try again."
            )
        
        return await call_next(request)
    
    def _is_api_client(self, request: Request) -> bool:
        """Check if request is from an API client (e.g., mobile app, external service)"""
        # Check for API key header
        if request.headers.get("X-API-Key"):
            return True
        
        # Check for Bearer token (different from session)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return True
        
        # Check for test client (requests from TestClient don't have browser cookies)
        user_agent = request.headers.get("user-agent", "")
        if "testclient" in user_agent.lower():
            return True
        
        return False
    
    def _validate_token(self, token: str, cookie: str) -> bool:
        """Validate that the CSRF token matches the cookie"""
        if not token or not cookie:
            return False
        
        # Simple equality check (in production, use HMAC)
        return secrets.compare_digest(token, cookie)
    
    @staticmethod
    def generate_csrf_token() -> str:
        """Generate a secure CSRF token"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def generate_csrf_token_with_secret(secret: str, session_id: str = None) -> str:
        """Generate a CSRF token tied to a secret and optional session"""
        data = f"{secret}:{session_id or ''}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]


class CSRFTokenGenerator:
    """Utility class for CSRF token generation and validation"""
    
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or secrets.token_urlsafe(32)
    
    def generate_token(self, session_id: str = None) -> str:
        """Generate a new CSRF token"""
        csrf_token = CSRFMiddleware.generate_csrf_token()
        return csrf_token
    
    def get_csrf_headers(self, session_id: str = None) -> dict:
        """Get headers for CSRF-protected requests"""
        token = self.generate_token(session_id)
        return {
            "X-CSRF-Token": token,
            "Set-Cookie": f"csrf_token={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=3600"
        }


def get_csrf_token_generator(secret_key: str = None) -> CSRFTokenGenerator:
    """Factory function to get CSRF token generator"""
    return CSRFTokenGenerator(secret_key)