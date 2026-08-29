"""
Notification Service
Email, push, SMS, and WhatsApp notification architecture with provider abstraction
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class NotificationProvider(ABC):
    """Abstract notification provider"""
    
    @abstractmethod
    def send(self, recipient: str, message: str, subject: str = None) -> Dict[str, Any]:
        """Send notification"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available"""
        pass


class EmailProvider(NotificationProvider):
    """Email notification provider"""
    
    def __init__(self, smtp_server: str = None, smtp_port: int = None,
                 smtp_username: str = None, smtp_password: str = None):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port or 587
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.available = bool(smtp_server)
    
    def send(self, recipient: str, message: str, subject: str = None) -> Dict[str, Any]:
        """Send email notification"""
        if not self.is_available():
            return {
                'success': False,
                'error': 'Email provider not configured',
                'provider': 'email'
            }
        
        try:
            # In production, use actual SMTP library
            logger.info(f"Email sent to {recipient}: {subject}")
            
            return {
                'success': True,
                'provider': 'email',
                'recipient': recipient,
                'sent_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'provider': 'email'
            }
    
    def is_available(self) -> bool:
        return self.available


class PushNotificationProvider(NotificationProvider):
    """Push notification provider"""
    
    def __init__(self, fcm_key: str = None):
        self.fcm_key = fcm_key
        self.available = bool(fcm_key)
    
    def send(self, recipient: str, message: str, subject: str = None) -> Dict[str, Any]:
        """Send push notification"""
        if not self.is_available():
            return {
                'success': False,
                'error': 'Push provider not configured',
                'provider': 'push'
            }
        
        try:
            # In production, use FCM or other push service
            logger.info(f"Push notification sent to {recipient}")
            
            return {
                'success': True,
                'provider': 'push',
                'recipient': recipient,
                'sent_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Push notification failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'provider': 'push'
            }
    
    def is_available(self) -> bool:
        return self.available


class SMSProvider(NotificationProvider):
    """SMS notification provider"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.available = bool(api_key)
    
    def send(self, recipient: str, message: str, subject: str = None) -> Dict[str, Any]:
        """Send SMS notification"""
        if not self.is_available():
            return {
                'success': False,
                'error': 'SMS provider not configured',
                'provider': 'sms'
            }
        
        try:
            # In production, use Twilio or other SMS service
            logger.info(f"SMS sent to {recipient}")
            
            return {
                'success': True,
                'provider': 'sms',
                'recipient': recipient,
                'sent_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"SMS send failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'provider': 'sms'
            }
    
    def is_available(self) -> bool:
        return self.available


class NotificationService:
    """Unified notification service with provider management"""
    
    def __init__(self):
        self.providers = {
            'email': EmailProvider(),
            'push': PushNotificationProvider(),
            'sms': SMSProvider()
        }
        self.notification_history = []
        self.templates = self._load_templates()
        self.user_preferences = {}
    
    def send_notification(self, recipient: str, message: str, 
                        channels: List[str] = None, 
                        template: str = None, 
                        context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send notification through specified channels"""
        if channels is None:
            channels = ['email']  # Default to email
        
        # Use template if specified
        if template and template in self.templates:
            message = self._render_template(template, context or {})
        
        results = {}
        for channel in channels:
            if channel in self.providers:
                result = self.providers[channel].send(recipient, message)
                results[channel] = result
                
                # Log to history
                self.notification_history.append({
                    'channel': channel,
                    'recipient': recipient,
                    'message': message,
                    'result': result,
                    'sent_at': datetime.utcnow().isoformat()
                })
        
        return {
            'success': all(r.get('success', False) for r in results.values()),
            'results': results
        }
    
    def set_user_preferences(self, user_id: int, preferences: Dict[str, Any]):
        """Set user notification preferences"""
        self.user_preferences[user_id] = preferences
    
    def get_user_preferences(self, user_id: int) -> Dict[str, Any]:
        """Get user notification preferences"""
        return self.user_preferences.get(user_id, {
            'email_enabled': True,
            'push_enabled': True,
            'sms_enabled': False,
            'quiet_hours_start': '22:00',
            'quiet_hours_end': '08:00'
        })
    
    def check_quiet_hours(self, user_id: int) -> bool:
        """Check if current time is within user's quiet hours"""
        preferences = self.get_user_preferences(user_id)
        current_time = datetime.utcnow().time()
        
        quiet_start = datetime.strptime(preferences['quiet_hours_start'], '%H:%M').time()
        quiet_end = datetime.strptime(preferences['quiet_hours_end'], '%H:%M').time()
        
        if quiet_start < quiet_end:
            return quiet_start <= current_time <= quiet_end
        else:  # Overnight quiet hours
            return current_time >= quiet_start or current_time <= quiet_end
    
    def _load_templates(self) -> Dict[str, str]:
        """Load notification templates"""
        return {
            'verification': 'Your verification code is: {code}',
            'password_reset': 'Click here to reset your password: {reset_link}',
            'exam_reminder': 'Reminder: {exam_name} is scheduled for {exam_date}',
            'deadline_alert': 'Deadline approaching: {task_name} due on {deadline}'
        }
    
    def _render_template(self, template: str, context: Dict[str, Any]) -> str:
        """Render template with context"""
        try:
            return template.format(**context)
        except KeyError as e:
            logger.error(f"Template rendering failed: {e}")
            return template
    
    def get_notification_history(self, user_id: int = None, 
                               limit: int = 50) -> List[Dict[str, Any]]:
        """Get notification history"""
        if user_id:
            return [n for n in self.notification_history if n['recipient'] == str(user_id)][:limit]
        return self.notification_history[-limit:]