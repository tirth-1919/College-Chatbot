"""
Google OAuth integration for AIT AI Assistant
Handles Google OAuth 2.0 authentication flow
"""

import secrets
import json
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend.app.models.entities import User, Role
from backend.app.security.auth import create_access_token, get_password_hash
from backend.app.config import settings
import logging

logger = logging.getLogger(__name__)


class GoogleOAuthService:
    """Google OAuth 2.0 service for authentication"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def get_google_auth_url(self, redirect_uri: Optional[str] = None) -> str:
        """
        Generate Google OAuth authorization URL
        """
        if not settings.GOOGLE_CLIENT_ID:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Google OAuth is not configured"
            )
        
        # Generate state parameter for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Use provided redirect_uri or default from settings
        final_redirect_uri = redirect_uri or settings.GOOGLE_REDIRECT_URI
        
        # Google OAuth 2.0 authorization endpoint
        auth_url = (
            "https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={settings.GOOGLE_CLIENT_ID}"
            f"&redirect_uri={final_redirect_uri}"
            "&response_type=code"
            "&scope=openid email profile"
            f"&state={state}"
        )
        
        return auth_url
    
    def handle_google_callback(self, code: str, state: str) -> Dict[str, Any]:
        """
        Handle Google OAuth callback
        Exchange authorization code for access token and user info
        """
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Google OAuth is not configured"
            )
        
        try:
            # Exchange authorization code for access token
            token_response = self._exchange_code_for_token(code)
            
            if not token_response or "access_token" not in token_response:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to exchange authorization code for access token"
                )
            
            access_token = token_response["access_token"]
            
            # Get user info from Google
            user_info = self._get_google_user_info(access_token)
            
            if not user_info or "email" not in user_info:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to retrieve user information from Google"
                )
            
            # Process user information
            return self._process_google_user(user_info)
            
        except Exception as e:
            logger.error(f"Google OAuth callback error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication failed"
            )
    
    def _exchange_code_for_token(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Exchange authorization code for access token
        """
        import requests
        
        token_url = "https://oauth2.googleapis.com/token"
        
        data = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code"
        }
        
        try:
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Token exchange error: {e}")
            return None
    
    def _get_google_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Get user information from Google using access token
        """
        import requests
        
        user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        try:
            response = requests.get(user_info_url, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"User info retrieval error: {e}")
            return None
    
    def _process_google_user(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process Google user information and create/update user account
        """
        google_id = user_info.get("id")
        email = user_info.get("email")
        name = user_info.get("name")
        picture = user_info.get("picture")
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is required from Google"
            )
        
        # Check if user exists by Google ID
        user = self.db.query(User).filter(User.google_id == google_id).first()
        
        if user:
            # Update existing user
            user.profile_image_url = picture
            user.last_login_at = self._get_current_time()
            user.is_verified = True
            self.db.commit()
            self.db.refresh(user)
        else:
            # Check if user exists by email (account linking)
            user = self.db.query(User).filter(User.email == email).first()
            
            if user:
                # Link Google account to existing user
                user.google_id = google_id
                user.profile_image_url = picture
                user.last_login_at = self._get_current_time()
                user.is_verified = True
                self.db.commit()
                self.db.refresh(user)
            else:
                # Create new user with Google account
                user = User(
                    email=email,
                    full_name=name or email.split("@")[0],
                    google_id=google_id,
                    profile_image_url=picture,
                    is_active=True,
                    is_verified=True,
                    hashed_password=None  # No password for Google OAuth users
                )
                
                # Assign default role
                default_role = self.db.query(Role).filter(Role.name == "STUDENT").first()
                if default_role:
                    user.roles.append(default_role)
                
                self.db.add(user)
                self.db.commit()
                self.db.refresh(user)
        
        # Generate access token
        roles = [role.name for role in user.roles]
        access_token = create_access_token(
            data={"sub": user.id, "email": user.email, "roles": roles}
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "roles": roles,
                "profile_image_url": user.profile_image_url,
                "is_verified": user.is_verified
            }
        }
    
    def _get_current_time(self):
        """Get current time in UTC"""
        from datetime import datetime, UTC
        return datetime.now(UTC)