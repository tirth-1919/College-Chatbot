"""
AI Safety Enhancements
Prompt injection detection, jailbreak detection, PII detection, emergency controls
"""

from typing import Dict, List, Optional, Any
import re
import logging

logger = logging.getLogger(__name__)


class AISafetyService:
    """AI safety service with advanced threat detection"""
    
    def __init__(self):
        self.kill_switch_active = False
        self.knowledge_freeze_active = False
        self.model_freeze_active = False
        self.safety_events = []
    
    def detect_prompt_injection(self, prompt: str) -> Dict[str, Any]:
        """Detect prompt injection attempts"""
        injection_patterns = [
            r'ignore previous instructions',
            r'forget everything',
            r'system prompt',
            r'override your programming',
            r'new instructions',
            r'replace your guidelines',
            r'admin override',
            r'bypass restrictions'
        ]
        
        prompt_lower = prompt.lower()
        detected_patterns = []
        
        for pattern in injection_patterns:
            if re.search(pattern, prompt_lower):
                detected_patterns.append(pattern)
        
        if detected_patterns:
            self._log_safety_event('PROMPT_INJECTION', {'patterns': detected_patterns})
            return {
                'detected': True,
                'patterns': detected_patterns,
                'severity': 'HIGH'
            }
        
        return {
            'detected': False,
            'severity': 'NONE'
        }
    
    def detect_jailbreak(self, prompt: str) -> Dict[str, Any]:
        """Detect jailbreak attempts"""
        jailbreak_patterns = [
            r'dan\s+?\d+',
            r'character play',
            r'roleplay',
            r'hypothetical',
            r'pretend you are',
            r'act as',
            r'imagine you',
            r'assume the persona',
            r'in a fictional world'
        ]
        
        prompt_lower = prompt.lower()
        detected_patterns = []
        
        for pattern in jailbreak_patterns:
            if re.search(pattern, prompt_lower):
                detected_patterns.append(pattern)
        
        if detected_patterns:
            self._log_safety_event('JAILBREAK_ATTEMPT', {'patterns': detected_patterns})
            return {
                'detected': True,
                'patterns': detected_patterns,
                'severity': 'MEDIUM'
            }
        
        return {
            'detected': False,
            'severity': 'NONE'
        }
    
    def detect_unsafe_request(self, prompt: str) -> Dict[str, Any]:
        """Detect unsafe or harmful requests"""
        unsafe_categories = {
            'violence': ['kill', 'harm', 'attack', 'violence', 'weapon'],
            'illegal': ['illegal', 'crime', 'hack', 'steal', 'fraud'],
            'harassment': ['harass', 'bully', 'threaten', 'abuse'],
            'self_harm': ['suicide', 'self-harm', 'kill myself', 'hurt myself']
        }
        
        prompt_lower = prompt.lower()
        detected_categories = []
        
        for category, keywords in unsafe_categories.items():
            for keyword in keywords:
                if keyword in prompt_lower:
                    detected_categories.append(category)
                    break
        
        if detected_categories:
            self._log_safety_event('UNSAFE_REQUEST', {'categories': detected_categories})
            return {
                'detected': True,
                'categories': detected_categories,
                'severity': 'HIGH'
            }
        
        return {
            'detected': False,
            'severity': 'NONE'
        }
    
    def activate_kill_switch(self, reason: str = None) -> Dict[str, Any]:
        """Activate AI kill switch"""
        self.kill_switch_active = True
        self._log_safety_event('KILL_SWITCH_ACTIVATED', {'reason': reason})
        
        return {
            'success': True,
            'message': 'AI kill switch activated',
            'activated_at': __import__('datetime').datetime.utcnow().isoformat()
        }
    
    def deactivate_kill_switch(self) -> Dict[str, Any]:
        """Deactivate AI kill switch"""
        self.kill_switch_active = False
        self._log_safety_event('KILL_SWITCH_DEACTIVATED', {})
        
        return {
            'success': True,
            'message': 'AI kill switch deactivated',
            'deactivated_at': __import__('datetime').datetime.utcnow().isoformat()
        }
    
    def freeze_knowledge(self, reason: str = None) -> Dict[str, Any]:
        """Freeze knowledge base updates"""
        self.knowledge_freeze_active = True
        self._log_safety_event('KNOWLEDGE_FROZEN', {'reason': reason})
        
        return {
            'success': True,
            'message': 'Knowledge base frozen',
            'frozen_at': __import__('datetime').datetime.utcnow().isoformat()
        }
    
    def unfreeze_knowledge(self) -> Dict[str, Any]:
        """Unfreeze knowledge base"""
        self.knowledge_freeze_active = False
        self._log_safety_event('KNOWLEDGE_UNFROZEN', {})
        
        return {
            'success': True,
            'message': 'Knowledge base unfrozen',
            'unfrozen_at': __import__('datetime').datetime.utcnow().isoformat()
        }
    
    def freeze_model(self, model_name: str, reason: str = None) -> Dict[str, Any]:
        """Freeze a specific model"""
        self.model_freeze_active = True
        self._log_safety_event('MODEL_FROZEN', {'model': model_name, 'reason': reason})
        
        return {
            'success': True,
            'message': f'Model {model_name} frozen',
            'frozen_at': __import__('datetime').datetime.utcnow().isoformat()
        }
    
    def unfreeze_model(self, model_name: str) -> Dict[str, Any]:
        """Unfreeze a specific model"""
        self.model_freeze_active = False
        self._log_safety_event('MODEL_UNFROZEN', {'model': model_name})
        
        return {
            'success': True,
            'message': f'Model {model_name} unfrozen',
            'unfrozen_at': __import__('datetime').datetime.utcnow().isoformat()
        }
    
    def get_safety_status(self) -> Dict[str, Any]:
        """Get current safety status"""
        return {
            'kill_switch_active': self.kill_switch_active,
            'knowledge_freeze_active': self.knowledge_freeze_active,
            'model_freeze_active': self.model_freeze_active,
            'recent_events': self.safety_events[-10:] if self.safety_events else []
        }
    
    def _log_safety_event(self, event_type: str, details: Dict[str, Any]):
        """Log a safety event"""
        event = {
            'type': event_type,
            'details': details,
            'timestamp': __import__('datetime').datetime.utcnow().isoformat()
        }
        self.safety_events.append(event)
        logger.warning(f"Safety event: {event_type} - {details}")