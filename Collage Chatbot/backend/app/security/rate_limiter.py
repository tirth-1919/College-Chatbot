"""
Comprehensive Rate Limiting for Phase 3
Per-endpoint specific limits, per-user/IP limits, and resource protection
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from functools import wraps
from fastapi import Request, HTTPException
from typing import Callable, Optional
import hashlib


class CustomRateLimiter:
    """
    Enhanced rate limiter with:
    - Per-endpoint specific limits
    - Per-user/IP limits
    - Resource protection
    - Safe error messages
    """
    
    def __init__(self):
        self.limiter = Limiter(key_func=self._get_key)
        
        # Rate limit configurations (requests per time window)
        self.endpoint_limits = {
            # General endpoints
            "health_check": "100/minute",
            "root": "60/minute",
            
            # Authentication endpoints
            "login": "10/minute",
            "register": "5/minute",
            "password_reset": "3/minute",
            
            # Chat endpoints (most important)
            "chat": "30/minute",
            "chat_stream": "20/minute",
            
            # File operations
            "upload_file": "10/minute",
            "download_file": "20/minute",
            
            # Deep research (resource intensive)
            "deep_research": "3/hour",
            "data_analysis": "5/hour",
            
            # Admin endpoints
            "admin_knowledge": "60/minute",
            "admin_users": "30/minute",
            
            # Memory operations
            "memory": "60/minute",
            
            # API endpoints
            "api_request": "100/minute",
        }
        
        # User role-based multipliers
        self.role_multipliers = {
            "SUPER_ADMIN": 10.0,  # 10x limit
            "ADMIN": 5.0,         # 5x limit
            "FACULTY": 2.0,       # 2x limit
            "STUDENT": 1.0,       # 1x limit
            "PUBLIC": 0.5,        # 0.5x limit
        }
    
    def _get_key(self, request: Request) -> str:
        """Generate rate limit key combining IP and user info"""
        # Get IP address
        ip = get_remote_address(request)
        
        # Get user ID if authenticated
        user_id = getattr(request.state, "user_id", None)
        
        # Get endpoint type
        endpoint = self._classify_endpoint(request.url.path)
        
        # Create composite key
        key_parts = [ip, endpoint]
        if user_id:
            key_parts.append(user_id)
        
        return ":".join(key_parts)
    
    def _classify_endpoint(self, path: str) -> str:
        """Classify endpoint type for rate limiting"""
        path_lower = path.lower()
        
        if "/health" in path_lower:
            return "health_check"
        elif "/api/v1/auth/login" in path_lower or "/api/auth/login" in path_lower:
            return "login"
        elif "/api/v1/auth/register" in path_lower or "/api/auth/register" in path_lower:
            return "register"
        elif "/password-reset" in path_lower:
            return "password_reset"
        elif "/api/v1/chat" in path_lower or "/api/chat" in path_lower:
            return "chat"
        elif "/upload" in path_lower:
            return "upload_file"
        elif "/download" in path_lower:
            return "download_file"
        elif "/research/deep" in path_lower:
            return "deep_research"
        elif "/analysis/data" in path_lower:
            return "data_analysis"
        elif "/admin" in path_lower:
            return "admin_knowledge"
        elif "/memory" in path_lower:
            return "memory"
        else:
            return "api_request"
    
    def get_limit_for_endpoint(self, endpoint: str, user_role: str = "STUDENT") -> str:
        """Get rate limit for specific endpoint and user role"""
        base_limit = self.endpoint_limits.get(endpoint, "60/minute")
        
        # Apply role multiplier
        multiplier = self.role_multipliers.get(user_role, 1.0)
        
        # Parse and adjust limit
        # Format: "X/minute" or "X/hour"
        parts = base_limit.split("/")
        count = int(parts[0])
        period = parts[1]
        
        adjusted_count = int(count * multiplier)
        
        return f"{adjusted_count}/{period}"
    
    def limit_for_endpoint(self, endpoint: str):
        """Decorator for endpoint-specific rate limiting"""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(request: Request, *args, **kwargs):
                # Get user role from request state if available
                user_role = getattr(request.state, "user_role", "STUDENT")
                
                # Get appropriate limit
                limit_str = self.get_limit_for_endpoint(endpoint, user_role)
                
                # Apply limit
                return self.limiter.limit(limit_str)(func)(request, *args, **kwargs)
            
            return wrapper
        return decorator


# Global rate limiter instance
rate_limiter = CustomRateLimiter()


# Rate limit exceeded handler with safe messages
def handle_rate_limit_exceeded(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded with safe, user-friendly messages"""
    endpoint = rate_limiter._classify_endpoint(request.url.path)
    
    # Safe error messages (don't expose internal limits)
    safe_messages = {
        "login": "Too many login attempts. Please try again later.",
        "register": "Registration rate limit exceeded. Please wait before trying again.",
        "chat": "You're sending messages too quickly. Please wait a moment.",
        "upload_file": "Upload rate limit exceeded. Please wait before uploading more files.",
        "deep_research": "Research rate limit exceeded. Please wait before starting another research task.",
        "data_analysis": "Analysis rate limit exceeded. Please wait before running another analysis.",
        "default": "Rate limit exceeded. Please slow down and try again."
    }
    
    message = safe_messages.get(endpoint, safe_messages["default"])
    
    return HTTPException(
        status_code=429,
        detail={
            "error": "Rate limit exceeded",
            "message": message,
            "retry_after": 60  # Suggest retry after 60 seconds
        }
    )