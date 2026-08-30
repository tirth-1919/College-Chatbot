"""
Password reset service for AIT AI Assistant
Handles secure password reset functionality
"""

import secrets
from datetime import datetime, timedelta, UTC
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend.app.models.entities import User, PasswordResetToken
from backend.app.security.auth import get_password_hash, verify_password
from backend.app.config import settings
import logging

logger = logging.getLogger(__name__)


class PasswordResetService:
    """Password reset service with secure token management"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def initiate_password_reset(self, email: str) -> Dict[str, Any]:
        """
        Initiate password reset process
        Always returns success to prevent email enumeration
        """
        # Find user by email
        user = self.db.query(User).filter(User.email == email).first()
        
        if user:
            # Generate secure reset token
            reset_token = secrets.token_urlsafe(32)
            expires_at = datetime.now(UTC) + timedelta(minutes=settings.PASSWORD_RESET_EXPIRY_MINUTES)
            
            # Delete any existing tokens for this user
            self.db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).delete()
            
            # Create new reset token
            token_record = PasswordResetToken(
                user_id=user.id,
                token=reset_token,
                expires_at=expires_at,
                used=False
            )
            
            self.db.add(token_record)
            self.db.commit()
            
            # In production, send email with reset link
            # For now, log the token (development only)
            logger.info(f"Password reset token for {email}: {reset_token}")
            logger.info(f"Reset link would be: /reset-password/{reset_token}")
        
        # Always return success to prevent email enumeration
        return {
            "success": True,
            "message": "If an account exists for this email, you will receive password reset instructions"
        }
    
    def reset_password(self, token: str, new_password: str) -> Dict[str, Any]:
        """
        Reset password using valid token
        """
        # Validate token
        token_record = self.db.query(PasswordResetToken).filter(
            PasswordResetToken.token == token,
            PasswordResetToken.used == False
        ).first()
        
        if not token_record:
            return {
                "success": False,
                "error": "Invalid or expired reset token"
            }
        
        # Check if token is expired
        if datetime.now(UTC) > token_record.expires_at:
            return {
                "success": False,
                "error": "Reset token has expired"
            }
        
        # Get user
        user = self.db.query(User).filter(User.id == token_record.user_id).first()
        if not user:
            return {
                "success": False,
                "error": "User not found"
            }
        
        # Validate new password
        password_validation = self._validate_password(new_password)
        if not password_validation['valid']:
            return {
                "success": False,
                "error": password_validation['error']
            }
        
        # Update password
        user.hashed_password = get_password_hash(new_password)
        
        # Mark token as used
        token_record.used = True
        
        try:
            self.db.commit()
            
            return {
                "success": True,
                "message": "Password has been reset successfully"
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Password reset failed: {e}")
            return {
                "success": False,
                "error": "Password reset failed"
            }
    
    def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate reset token without using it
        """
        token_record = self.db.query(PasswordResetToken).filter(
            PasswordResetToken.token == token,
            PasswordResetToken.used == False
        ).first()
        
        if not token_record:
            return {
                "valid": False,
                "error": "Invalid token"
            }
        
        if datetime.now(UTC) > token_record.expires_at:
            return {
                "valid": False,
                "error": "Token has expired"
            }
        
        return {
            "valid": True,
            "message": "Token is valid"
        }
    
    def _validate_password(self, password: str) -> Dict[str, Any]:
        """Validate password strength"""
        if len(password) < 8:
            return {'valid': False, 'error': 'Password must be at least 8 characters'}
        
        if not any(c.isupper() for c in password):
            return {'valid': False, 'error': 'Password must contain at least one uppercase letter'}
        
        if not any(c.islower() for c in password):
            return {'valid': False, 'error': 'Password must contain at least one lowercase letter'}
        
        if not any(c.isdigit() for c in password):
            return {'valid': False, 'error': 'Password must contain at least one digit'}
        
        # Check for common passwords
        common_passwords = {'password', '12345678', 'qwerty', 'abc123'}
        if password.lower() in common_passwords:
            return {'valid': False, 'error': 'Password is too common'}
        
        return {'valid': True, 'error': None}