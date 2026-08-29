"""
Campus Services Service
Campus FAQ, navigation, library, hostel, transport, and other campus-specific assistants
"""

from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from backend.app.models.entities import Facility, Event, Fee
import logging

logger = logging.getLogger(__name__)


class CampusServicesService:
    """Campus services for student assistance"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def get_campus_faq(self) -> Dict[str, Any]:
        """Get campus FAQ"""
        faq = {
            'general': [
                {
                    'question': 'What are the library hours?',
                    'answer': 'Library is open from 8:00 AM to 8:00 PM on weekdays and 9:00 AM to 5:00 PM on weekends.'
                },
                {
                    'question': 'Where is the main office?',
                    'answer': 'The main administrative office is located on the ground floor of the main building.'
                }
            ],
            'academic': [
                {
                    'question': 'How do I get my timetable?',
                    'answer': 'Timetables are available through the student portal and are also posted on department notice boards.'
                },
                {
                    'question': 'What is the attendance policy?',
                    'answer': 'Students must maintain minimum 75% attendance to be eligible for examinations.'
                }
            ],
            'facilities': [
                {
                    'question': 'Is there Wi-Fi on campus?',
                    'answer': 'Yes, free Wi-Fi is available throughout the campus for all students.'
                },
                {
                    'question': 'Where are the computer labs?',
                    'answer': 'Computer labs are located on the 2nd floor of the main building and in the library.'
                }
            ]
        }
        
        return {'success': True, 'faq': faq}
    
    def get_campus_navigation(self, destination: str) -> Dict[str, Any]:
        """Get navigation guidance to campus locations"""
        locations = {
            'library': {
                'building': 'Main Building',
                'floor': '2nd Floor',
                'directions': 'Enter main entrance, take stairs to 2nd floor, library is on the right side.'
            },
            'canteen': {
                'building': 'Student Center',
                'floor': 'Ground Floor',
                'directions': 'Student Center is located behind the main building. Canteen is on the ground floor.'
            },
            'auditorium': {
                'building': 'Main Building',
                'floor': 'Ground Floor',
                'directions': 'Enter main entrance, auditorium is straight ahead past the reception.'
            }
        }
        
        destination_lower = destination.lower()
        for key, info in locations.items():
            if key in destination_lower:
                return {'success': True, 'navigation': info}
        
        return {'success': False, 'error': 'Location not found'}
    
    def get_library_assistance(self, query: str) -> Dict[str, Any]:
        """Library assistant for book and resource queries"""
        query_lower = query.lower()
        
        if 'book' in query_lower or 'journal' in query_lower:
            return {
                'success': True,
                'response': 'You can search for books and journals using the library catalog system available at library.aitindia.in or at the library terminals.'
            }
        elif 'hours' in query_lower or 'timing' in query_lower:
            return {
                'success': True,
                'response': 'Library hours: Weekdays 8:00 AM - 8:00 PM, Weekends 9:00 AM - 5:00 PM'
            }
        elif 'membership' in query_lower or 'card' in query_lower:
            return {
                'success': True,
                'response': 'Your student ID card serves as your library membership. Bring it to the circulation desk for any assistance.'
            }
        else:
            return {
                'success': True,
                'response': 'For specific library assistance, please visit the circulation desk or call the library helpline at extension 1234.'
            }
    
    def get_hostel_assistance(self, query: str) -> Dict[str, Any]:
        """Hostel assistant for accommodation queries"""
        query_lower = query.lower()
        
        if 'room' in query_lower or 'accommodation' in query_lower:
            return {
                'success': True,
                'response': 'Room allocation is handled by the hostel administration. Please contact the hostel warden for room-related queries.'
            }
        elif 'rules' in query_lower or 'regulations' in query_lower:
            return {
                'success': True,
                'response': 'Hostel rules include: no visitors after 10 PM, quiet hours from 10 PM to 6 AM, mandatory attendance at roll calls. Full rules are available on the hostel notice board.'
            }
        elif 'mess' in query_lower or 'food' in query_lower:
            return {
                'success': True,
                'response': 'Mess timings: Breakfast 7:00-9:00 AM, Lunch 12:00-2:00 PM, Dinner 7:00-9:00 PM. Menu is posted weekly.'
            }
        else:
            return {
                'success': True,
                'response': 'For hostel-specific queries, please contact the hostel warden office located in the hostel building.'
            }
    
    def get_transport_assistance(self, query: str) -> Dict[str, Any]:
        """Transport assistant for commuting queries"""
        query_lower = query.lower()
        
        if 'bus' in query_lower or 'transport' in query_lower:
            return {
                'success': True,
                'response': 'College bus service covers major routes. Bus passes are available from the transport office. Schedule is available on the college website.'
            }
        elif 'route' in query_lower or 'timing' in query_lower:
            return {
                'success': True,
                'response': 'Bus routes and timings are available on the college notice board and transport office. Buses typically operate from 7:00 AM to 6:00 PM.'
            }
        else:
            return {
                'success': True,
                'response': 'For detailed transport information, please visit the transport office or check the college website.'
            }