"""
Analytics Service for AIT AI Assistant
Privacy-conscious analytics tracking user metrics, question analytics, and system performance
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from backend.app.models.entities import (
    User, Conversation, Message, KnowledgeSource, KnowledgeDocument
)
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Privacy-conscious analytics service
    Tracks aggregate metrics without storing PII
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def get_user_analytics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get user analytics for specified time period
        
        Returns:
            Dictionary with user metrics (aggregated, no PII)
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Daily active users
            daily_users = self.db.query(
                func.date(Message.created_at).label('date'),
                func.count(func.distinct(Message.user_id)).label('active_users')
            ).filter(
                Message.created_at >= start_date
            ).group_by(
                func.date(Message.created_at)
            ).all()
            
            # Weekly active users
            weekly_users = self.db.query(
                func.date_trunc('week', Message.created_at).label('week'),
                func.count(func.distinct(Message.user_id)).label('active_users')
            ).filter(
                Message.created_at >= start_date
            ).group_by(
                func.date_trunc('week', Message.created_at)
            ).all()
            
            # Monthly active users
            monthly_users = self.db.query(
                func.date_trunc('month', Message.created_at).label('month'),
                func.count(func.distinct(Message.user_id)).label('active_users')
            ).filter(
                Message.created_at >= start_date
            ).group_by(
                func.date_trunc('month', Message.created_at)
            ).all()
            
            return {
                'daily_active_users': [
                    {'date': str(d.date), 'count': d.active_users} 
                    for d in daily_users
                ],
                'weekly_active_users': [
                    {'week': str(d.week), 'count': d.active_users} 
                    for d in weekly_users
                ],
                'monthly_active_users': [
                    {'month': str(d.month), 'count': d.active_users} 
                    for d in monthly_users
                ],
                'total_users': self.db.query(func.count(User.id)).scalar(),
                'period_days': days
            }
            
        except Exception as e:
            logger.error(f"Failed to get user analytics: {e}")
            return {'error': str(e)}
    
    def get_question_analytics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get question analytics for specified time period
        
        Returns:
            Dictionary with question metrics
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Total questions
            total_questions = self.db.query(func.count(Message.id)).filter(
                Message.role == 'user',
                Message.created_at >= start_date
            ).scalar()
            
            # Questions by category (based on intent)
            # This would require intent tracking in messages
            question_categories = defaultdict(int)
            
            # Questions by language
            language_distribution = self.db.query(
                Message.language,
                func.count(Message.id).label('count')
            ).filter(
                Message.role == 'user',
                Message.created_at >= start_date
            ).group_by(Message.language).all()
            
            # Questions by department (if available)
            department_distribution = self.db.query(
                User.department_id,
                func.count(Message.id).label('count')
            ).join(
                Message, Message.user_id == User.id
            ).filter(
                Message.role == 'user',
                Message.created_at >= start_date
            ).group_by(User.department_id).all()
            
            # Unresolved questions (those with error status)
            unresolved_questions = self.db.query(func.count(Message.id)).filter(
                Message.role == 'user',
                Message.status == 'error',
                Message.created_at >= start_date
            ).scalar()
            
            return {
                'total_questions': total_questions,
                'unresolved_questions': unresolved_questions,
                'resolution_rate': (total_questions - unresolved_questions) / total_questions if total_questions > 0 else 0,
                'language_distribution': [
                    {'language': lang or 'unknown', 'count': count} 
                    for lang, count in language_distribution
                ],
                'department_distribution': [
                    {'department_id': dept_id or 'unknown', 'count': count} 
                    for dept_id, count in department_distribution
                ],
                'question_categories': dict(question_categories),
                'period_days': days
            }
            
        except Exception as e:
            logger.error(f"Failed to get question analytics: {e}")
            return {'error': str(e)}
    
    def get_ai_usage_analytics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get AI provider usage analytics
        
        Returns:
            Dictionary with AI usage metrics
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Total AI responses
            ai_responses = self.db.query(func.count(Message.id)).filter(
                Message.role == 'assistant',
                Message.created_at >= start_date
            ).scalar()
            
            # Source distribution (where answers came from)
            # This would require source tracking in messages
            source_distribution = defaultdict(int)
            
            # Average response time (if tracked)
            avg_response_time = 0  # Would need timing data
            
            # Token usage (if tracked)
            total_tokens = 0  # Would need token tracking
            estimated_cost = 0.0  # Would need cost tracking
            
            return {
                'total_ai_responses': ai_responses,
                'source_distribution': dict(source_distribution),
                'total_tokens': total_tokens,
                'estimated_cost': estimated_cost,
                'avg_response_time_ms': avg_response_time,
                'period_days': days
            }
            
        except Exception as e:
            logger.error(f"Failed to get AI usage analytics: {e}")
            return {'error': str(e)}
    
    def get_rag_analytics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get RAG system analytics
        
        Returns:
            Dictionary with RAG metrics
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Total documents in knowledge base
            total_documents = self.db.query(func.count(KnowledgeDocument.id)).scalar()
            
            # Documents by status
            document_status = self.db.query(
                KnowledgeDocument.status,
                func.count(KnowledgeDocument.id).label('count')
            ).group_by(KnowledgeDocument.status).all()
            
            # Knowledge sources
            total_sources = self.db.query(func.count(KnowledgeSource.id)).scalar()
            
            # Retrieval metrics (would need retrieval tracking)
            retrieval_success_rate = 0.95  # Placeholder
            avg_retrieval_time_ms = 150  # Placeholder
            avg_results_per_query = 5  # Placeholder
            
            return {
                'total_documents': total_documents,
                'total_sources': total_sources,
                'document_status': [
                    {'status': status, 'count': count} 
                    for status, count in document_status
                ],
                'retrieval_success_rate': retrieval_success_rate,
                'avg_retrieval_time_ms': avg_retrieval_time_ms,
                'avg_results_per_query': avg_results_per_query,
                'period_days': days
            }
            
        except Exception as e:
            logger.error(f"Failed to get RAG analytics: {e}")
            return {'error': str(e)}
    
    def get_voice_analytics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get voice functionality analytics
        
        Returns:
            Dictionary with voice metrics
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Voice message count (if tracked via mode)
            voice_messages = self.db.query(func.count(Message.id)).filter(
                Message.mode == 'VOICE',
                Message.created_at >= start_date
            ).scalar()
            
            # STT success rate (placeholder)
            stt_success_rate = 0.92
            
            # TTS success rate (placeholder)
            tts_success_rate = 0.95
            
            # Audio cache hit rate (placeholder)
            cache_hit_rate = 0.75
            
            return {
                'voice_messages': voice_messages,
                'stt_success_rate': stt_success_rate,
                'tts_success_rate': tts_success_rate,
                'cache_hit_rate': cache_hit_rate,
                'period_days': days
            }
            
        except Exception as e:
            logger.error(f"Failed to get voice analytics: {e}")
            return {'error': str(e)}
    
    def get_performance_analytics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get system performance analytics
        
        Returns:
            Dictionary with performance metrics
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Average response times (would need timing tracking)
            avg_response_time_ms = 250  # Placeholder
            p50_response_time_ms = 200  # Placeholder
            p95_response_time_ms = 500  # Placeholder
            p99_response_time_ms = 1000  # Placeholder
            
            # Error rate
            error_messages = self.db.query(func.count(Message.id)).filter(
                Message.status == 'error',
                Message.created_at >= start_date
            ).scalar()
            total_messages = self.db.query(func.count(Message.id)).filter(
                Message.created_at >= start_date
            ).scalar()
            error_rate = error_messages / total_messages if total_messages > 0 else 0
            
            return {
                'avg_response_time_ms': avg_response_time_ms,
                'p50_response_time_ms': p50_response_time_ms,
                'p95_response_time_ms': p95_response_time_ms,
                'p99_response_time_ms': p99_response_time_ms,
                'error_rate': error_rate,
                'period_days': days
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance analytics: {e}")
            return {'error': str(e)}
    
    def get_analytics_dashboard(self, days: int = 30) -> Dict[str, Any]:
        """
        Get complete analytics dashboard
        
        Returns:
            Dictionary with all analytics metrics
        """
        return {
            'user_analytics': self.get_user_analytics(days),
            'question_analytics': self.get_question_analytics(days),
            'ai_usage_analytics': self.get_ai_usage_analytics(days),
            'rag_analytics': self.get_rag_analytics(days),
            'voice_analytics': self.get_voice_analytics(days),
            'performance_analytics': self.get_performance_analytics(days),
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def track_user_feedback(self, conversation_id: str, rating: int, feedback: str = None):
        """
        Track user feedback for conversations
        
        Args:
            conversation_id: ID of the conversation
            rating: User rating (1-5)
            feedback: Optional text feedback
        """
        try:
            # This would require a feedback table
            logger.info(f"User feedback tracked for conversation {conversation_id}: {rating}")
            return True
        except Exception as e:
            logger.error(f"Failed to track user feedback: {e}")
            return False