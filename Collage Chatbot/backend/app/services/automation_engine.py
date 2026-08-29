"""
Automation Engine
Knowledge gap detection, FAQ automation, deadline extraction, and support ticket automation
"""

from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from backend.app.models.entities import Message, KnowledgeDocument, SupportTicket
from datetime import datetime, timedelta
import logging
from collections import Counter
import re

logger = logging.getLogger(__name__)


class AutomationEngine:
    """Automation engine for intelligent knowledge and support management"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def detect_knowledge_gaps(self, days: int = 7) -> Dict[str, Any]:
        """Detect knowledge gaps from unanswered questions"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get unanswered or poorly answered questions
        unanswered_questions = self.db.query(Message).filter(
            Message.role == 'user',
            Message.created_at >= cutoff_date,
            Message.status == 'error'
        ).all()
        
        # Cluster similar questions
        question_clusters = self._cluster_questions([msg.content for msg in unanswered_questions])
        
        # Generate gap alerts
        gap_alerts = []
        for cluster_id, questions in question_clusters.items():
            if len(questions) >= 3:  # Threshold for gap detection
                gap_alerts.append({
                    'cluster_id': cluster_id,
                    'question_count': len(questions),
                    'sample_questions': questions[:3],
                    'suggested_topic': self._extract_topic(questions[0])
                })
        
        return {
            'success': True,
            'total_unanswered': len(unanswered_questions),
            'gap_alerts': gap_alerts,
            'period_days': days
        }
    
    def generate_faq_suggestions(self, days: int = 30) -> Dict[str, Any]:
        """Generate FAQ suggestions from frequently asked questions"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get all user questions
        user_questions = self.db.query(Message).filter(
            Message.role == 'user',
            Message.created_at >= cutoff_date
        ).all()
        
        # Count question frequency
        question_texts = [msg.content for msg in user_questions]
        question_counter = Counter(question_texts)
        
        # Find frequently asked questions
        frequent_questions = [
            {'question': q, 'frequency': count}
            for q, count in question_counter.most_common(10)
            if count >= 3  # Minimum frequency threshold
        ]
        
        # Generate FAQ drafts
        faq_drafts = []
        for item in frequent_questions:
            faq_drafts.append({
                'question': item['question'],
                'frequency': item['frequency'],
                'suggested_answer': 'This question is frequently asked. Consider adding a verified answer to the knowledge base.',
                'priority': 'HIGH' if item['frequency'] >= 5 else 'MEDIUM'
            })
        
        return {
            'success': True,
            'faq_drafts': faq_drafts,
            'period_days': days
        }
    
    def extract_deadlines(self, notice_text: str) -> Dict[str, Any]:
        """Extract deadlines from institutional notices"""
        # Date pattern matching
        date_patterns = [
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})',  # DD/MM/YYYY or DD-MM-YYYY
            r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',  # YYYY/MM/DD or YYYY-MM-DD
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4})'  # Month DD, YYYY
        ]
        
        deadlines = []
        for pattern in date_patterns:
            matches = re.findall(pattern, notice_text)
            for match in matches:
                deadlines.append({
                    'raw_date': match,
                    'context': self._extract_context(notice_text, match)
                })
        
        return {
            'success': True,
            'deadlines': deadlines,
            'count': len(deadlines)
        }
    
    def create_support_ticket(self, user_id: int, question: str, 
                           category: str = "GENERAL") -> Dict[str, Any]:
        """Create support ticket for unresolved questions"""
        ticket = SupportTicket(
            user_id=user_id,
            subject=question[:100],  # Truncate for subject
            description=question,
            category=category,
            priority="MEDIUM",
            status="OPEN",
            created_at=datetime.utcnow()
        )
        
        try:
            self.db.add(ticket)
            self.db.commit()
            
            return {
                'success': True,
                'ticket_id': ticket.id,
                'message': 'Support ticket created successfully'
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Support ticket creation failed: {e}")
            return {
                'success': False,
                'error': 'Failed to create support ticket'
            }
    
    def route_support_tickets(self) -> Dict[str, Any]:
        """Automatically route support tickets to appropriate departments"""
        open_tickets = self.db.query(SupportTicket).filter(
            SupportTicket.status == "OPEN"
        ).all()
        
        routing_results = []
        for ticket in open_tickets:
            department = self._determine_department(ticket.subject)
            priority = self._determine_priority(ticket)
            
            ticket.assigned_department = department
            ticket.priority = priority
            ticket.status = "ASSIGNED"
            
            routing_results.append({
                'ticket_id': ticket.id,
                'department': department,
                'priority': priority
            })
        
        try:
            self.db.commit()
            return {
                'success': True,
                'routed_tickets': len(routing_results),
                'routing_details': routing_results
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Ticket routing failed: {e}")
            return {
                'success': False,
                'error': 'Failed to route tickets'
            }
    
    def _cluster_questions(self, questions: List[str]) -> Dict[int, List[str]]:
        """Cluster similar questions using simple keyword matching"""
        clusters = {}
        cluster_id = 0
        
        for question in questions:
            # Simple clustering based on keyword overlap
            found_cluster = False
            for cid, cluster_questions in clusters.items():
                if self._similarity_score(question, cluster_questions[0]) > 0.5:
                    clusters[cid].append(question)
                    found_cluster = True
                    break
            
            if not found_cluster:
                clusters[cluster_id] = [question]
                cluster_id += 1
        
        return clusters
    
    def _similarity_score(self, q1: str, q2: str) -> float:
        """Calculate simple similarity score between questions"""
        words1 = set(q1.lower().split())
        words2 = set(q2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _extract_topic(self, question: str) -> str:
        """Extract topic from question"""
        # Simple keyword extraction
        keywords = ['fee', 'exam', 'timetable', 'faculty', 'syllabus', 'admission', 'library']
        
        for keyword in keywords:
            if keyword in question.lower():
                return keyword.capitalize()
        
        return "General"
    
    def _extract_context(self, text: str, match: str) -> str:
        """Extract context around a matched date"""
        # Find position of match
        pos = text.find(str(match))
        if pos == -1:
            return ""
        
        # Extract 50 characters before and after
        start = max(0, pos - 50)
        end = min(len(text), pos + len(str(match)) + 50)
        
        return text[start:end]
    
    def _determine_department(self, subject: str) -> str:
        """Determine appropriate department for support ticket"""
        subject_lower = subject.lower()
        
        if 'fee' in subject_lower or 'payment' in subject_lower:
            return "ACCOUNTS"
        elif 'exam' in subject_lower or 'result' in subject_lower:
            return "ACADEMIC"
        elif 'hostel' in subject_lower or 'mess' in subject_lower:
            return "STUDENT_WELFARE"
        elif 'library' in subject_lower or 'book' in subject_lower:
            return "LIBRARY"
        else:
            return "GENERAL"
    
    def _determine_priority(self, ticket: SupportTicket) -> str:
        """Determine ticket priority based on content"""
        subject_lower = ticket.subject.lower()
        
        if 'urgent' in subject_lower or 'emergency' in subject_lower:
            return "HIGH"
        elif 'deadline' in subject_lower or 'exam' in subject_lower:
            return "MEDIUM"
        else:
            return "LOW"