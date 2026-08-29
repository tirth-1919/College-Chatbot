"""
Enhanced Authentication System for AIT AI Assistant
ChatGPT-style authentication with improved UX, email verification, and password reset
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.entities import User
from backend.app.security.auth import get_password_hash, verify_password
import logging

logger = logging.getLogger(__name__)


class EmailVerificationService:
    """Email verification service for user registration"""
    
    def __init__(self):
        self.verification_codes = {}  # In production, use Redis or database
        self.code_expiry_minutes = 15
        self.max_attempts = 3
        self.resend_cooldown_seconds = 60
    
    def generate_verification_code(self, user_id: int) -> str:
        """Generate a 6-digit verification code"""
        code = str(secrets.randbelow(1000000)).zfill(6)
        expiry = datetime.utcnow() + timedelta(minutes=self.code_expiry_minutes)
        
        self.verification_codes[user_id] = {
            'code': code,
            'expiry': expiry,
            'attempts': 0,
            'last_sent': datetime.utcnow()
        }
        
        return code
    
    def verify_code(self, user_id: int, code: str) -> bool:
        """Verify the verification code"""
        if user_id not in self.verification_codes:
            return False
        
        stored = self.verification_codes[user_id]
        
        # Check expiry
        if datetime.utcnow() > stored['expiry']:
            del self.verification_codes[user_id]
            return False
        
        # Check attempts
        if stored['attempts'] >= self.max_attempts:
            return False
        
        # Verify code
        if secrets.compare_digest(stored['code'], code):
            del self.verification_codes[user_id]
            return True
        
        # Increment attempts
        stored['attempts'] += 1
        return False
    
    def can_resend(self, user_id: int) -> bool:
        """Check if code can be resent"""
        if user_id not in self.verification_codes:
            return True
        
        stored = self.verification_codes[user_id]
        elapsed = (datetime.utcnow() - stored['last_sent']).total_seconds()
        return elapsed >= self.resend_cooldown_seconds


class PasswordResetService:
    """Password reset service"""
    
    def __init__(self):
        self.reset_tokens = {}  # In production, use database
        self.token_expiry_hours = 1
    
    def generate_reset_token(self, email: str) -> str:
        """Generate a secure password reset token"""
        token = secrets.token_urlsafe(32)
        expiry = datetime.utcnow() + timedelta(hours=self.token_expiry_hours)
        
        self.reset_tokens[token] = {
            'email': email,
            'expiry': expiry,
            'used': False
        }
        
        return token
    
    def validate_token(self, token: str) -> Optional[str]:
        """Validate reset token and return email if valid"""
        if token not in self.reset_tokens:
            return None
        
        stored = self.reset_tokens[token]
        
        # Check expiry
        if datetime.utcnow() > stored['expiry']:
            del self.reset_tokens[token]
            return None
        
        # Check if already used
        if stored['used']:
            return None
        
        return stored['email']
    
    def mark_token_used(self, token: str):
        """Mark token as used"""
        if token in self.reset_tokens:
            self.reset_tokens[token]['used'] = True


class EnhancedAuthService:
    """Enhanced authentication service with ChatGPT-style UX"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.email_verification = EmailVerificationService()
        self.password_reset = PasswordResetService()
    
    def initiate_signup(self, email: str, full_name: str) -> Dict[str, Any]:
        """
        Initiate signup process - Step 1: Email validation
        """
        # Check if email already exists
        existing_user = self.db.query(User).filter(User.email == email).first()
        if existing_user:
            return {
                'success': False,
                'error': 'Email already registered',
                'step': 'email'
            }
        
        # Validate email format
        if not self._validate_email(email):
            return {
                'success': False,
                'error': 'Invalid email format',
                'step': 'email'
            }
        
        # Check for disposable emails (basic check)
        if self._is_disposable_email(email):
            return {
                'success': False,
                'error': 'Disposable emails not allowed',
                'step': 'email'
            }
        
        # Generate verification code
        temp_user_id = hash(email)  # Temporary ID for verification
        verification_code = self.email_verification.generate_verification_code(temp_user_id)
        
        # In production, send actual email
        logger.info(f"Verification code for {email}: {verification_code}")
        
        return {
            'success': True,
            'step': 'verification',
            'message': 'Verification code sent to email',
            'temp_user_id': temp_user_id
        }
    
    def verify_email(self, temp_user_id: int, code: str) -> Dict[str, Any]:
        """
        Verify email code - Step 2: Verification
        """
        if not self.email_verification.verify_code(temp_user_id, code):
            return {
                'success': False,
                'error': 'Invalid or expired verification code',
                'step': 'verification'
            }
        
        return {
            'success': True,
            'step': 'account_details',
            'message': 'Email verified successfully'
        }
    
    def complete_signup(self, email: str, full_name: str, password: str, 
                        role: str = "STUDENT", department_id: int = None,
                        course_id: int = None, current_semester: int = None) -> Dict[str, Any]:
        """
        Complete signup - Step 3: Account creation
        """
        # Validate password
        password_validation = self._validate_password(password)
        if not password_validation['valid']:
            return {
                'success': False,
                'error': password_validation['error'],
                'step': 'account_details'
            }
        
        # Check if email already exists (double-check)
        existing_user = self.db.query(User).filter(User.email == email).first()
        if existing_user:
            return {
                'success': False,
                'error': 'Email already registered',
                'step': 'account_details'
            }
        
        # Create user
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=get_password_hash(password),
            role=role,
            department_id=department_id,
            course_id=course_id,
            current_semester=current_semester,
            is_active=True
        )
        
        try:
            self.db.add(user)
            self.db.commit()
            
            return {
                'success': True,
                'step': 'complete',
                'message': 'Account created successfully',
                'user_id': user.id
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"User creation failed: {e}")
            return {
                'success': False,
                'error': 'Account creation failed',
                'step': 'account_details'
            }
    
    def initiate_password_reset(self, email: str) -> Dict[str, Any]:
        """
        Initiate password reset
        """
        # Always return success to prevent email enumeration
        user = self.db.query(User).filter(User.email == email).first()
        
        if user:
            reset_token = self.password_reset.generate_reset_token(email)
            logger.info(f"Password reset token for {email}: {reset_token}")
            # In production, send actual email
        else:
            logger.info(f"Password reset requested for non-existent email: {email}")
        
        return {
            'success': True,
            'message': 'If an account exists for this email, you will receive a password reset link'
        }
    
    def reset_password(self, token: str, new_password: str) -> Dict[str, Any]:
        """
        Reset password with token
        """
        email = self.password_reset.validate_token(token)
        if not email:
            return {
                'success': False,
                'error': 'Invalid or expired reset token'
            }
        
        # Validate new password
        password_validation = self._validate_password(new_password)
        if not password_validation['valid']:
            return {
                'success': False,
                'error': password_validation['error']
            }
        
        # Update password
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            return {
                'success': False,
                'error': 'User not found'
            }
        
        user.hashed_password = get_password_hash(new_password)
        
        try:
            self.db.commit()
            self.password_reset.mark_token_used(token)
            
            return {
                'success': True,
                'message': 'Password reset successfully'
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Password reset failed: {e}")
            return {
                'success': False,
                'error': 'Password reset failed'
            }
    
    def _validate_email(self, email: str) -> bool:
        """Basic email validation"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _is_disposable_email(self, email: str) -> bool:
        """Check for disposable email domains"""
        disposable_domains = {
            'tempmail.com', 'guerrillamail.com', 'mailinator.com',
            '10minutemail.com', 'yopmail.com', 'trashmail.com'
        }
        domain = email.split('@')[-1].lower()
        return domain in disposable_domains
    
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