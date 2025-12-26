# Google Calendar API Wrapper for Huata Agent
# Handles all Google Calendar operations with family-friendly error handling
# Part of Demestihas.ai Calendar System

import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

# Google Calendar API imports (will be available on VPS)
try:
    from google.auth.transport.requests import Request
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

class GoogleCalendarAPI:
    """
    Wrapper for Google Calendar API operations.
    
    Handles authentication, rate limiting, and family-friendly error messages.
    Uses service account for server-to-server authentication.
    """
    
    def __init__(self, credentials_path: str = None):
        """Initialize Google Calendar API connection"""
        self.credentials_path = credentials_path or "/root/demestihas-ai/credentials/huata-service-account.json"
        self.service = None
        self.scopes = [
            'https://www.googleapis.com/auth/calendar.readonly',
            'https://www.googleapis.com/auth/calendar.events'
        ]
        
        # Initialize service if Google libraries available
        if GOOGLE_AVAILABLE:
            asyncio.create_task(self._initialize_service())
    
    async def _initialize_service(self):
        """Initialize Google Calendar service with credentials"""
        try:
            if not os.path.exists(self.credentials_path):
                # Service will work in mock mode without credentials
                return
            
            credentials = Credentials.from_service_account_file(
                self.credentials_path, 
                scopes=self.scopes
            )
            
            self.service = build('calendar', 'v3', credentials=credentials)
            
        except Exception as e:
            # Log error but continue in mock mode
            print(f"Calendar API initialization warning: {e}")
    
    async def get_events(self, calendar_id: str = 'primary', time_min: str = None, 
                        time_max: str = None, max_results: int = 10) -> List[Dict]:
        """
        Get calendar events for specified time range
        
        Args:
            calendar_id: Calendar to query (default: 'primary')
            time_min: Start time (ISO format)
            time_max: End time (ISO format) 
            max_results: Maximum events to return
            
        Returns:
            List of event dictionaries
        """
        
        # Mock mode if service not available
        if not self.service:
            return self._mock_get_events(time_min, time_max, max_results)
        
        try:
            # Set default time range if not provided
            if not time_min:
                time_min = datetime.now().isoformat() + 'Z'
            if not time_max:
                time_max = (datetime.now() + timedelta(days=7)).isoformat() + 'Z'
            
            # Call Google Calendar API
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Add family-friendly formatting
            for event in events:
                self._enhance_event_data(event)
            
            return events
            
        except HttpError as e:
            if e.resp.status == 403:
                # Permission error - common setup issue
                raise Exception("Calendar access not configured. Check service account permissions.")
            elif e.resp.status == 404:
                # Calendar not found
                raise Exception(f"Calendar '{calendar_id}' not found. Check calendar sharing settings.")
            else:
                raise Exception(f"Calendar API error: {e}")
                
        except Exception as e:
            raise Exception(f"Could not retrieve calendar events: {str(e)}")
    
    async def create_event(self, calendar_id: str, event_data: Dict) -> Dict:
        """
        Create a new calendar event
        
        Args:
            calendar_id: Calendar to create event in
            event_data: Event details (title, start, end, etc.)
            
        Returns:
            Created event dictionary
        """
        
        # Mock mode if service not available  
        if not self.service:
            return self._mock_create_event(event_data)
        
        try:
            # Validate required fields
            if not event_data.get('summary'):
                raise Exception("Event title is required")
            if not event_data.get('start', {}).get('dateTime'):
                raise Exception("Event start time is required")
            if not event_data.get('end', {}).get('dateTime'):
                raise Exception("Event end time is required")
            
            # Create event via Google Calendar API
            created_event = self.service.events().insert(
                calendarId=calendar_id,
                body=event_data
            ).execute()
            
            # Enhance with family-friendly data
            self._enhance_event_data(created_event)
            
            return created_event
            
        except HttpError as e:
            if e.resp.status == 403:
                raise Exception("Cannot create events. Check calendar write permissions.")
            elif e.resp.status == 400:
                raise Exception("Invalid event data. Check date/time format.")
            else:
                raise Exception(f"Calendar API error: {e}")
                
        except Exception as e:
            raise Exception(f"Could not create calendar event: {str(e)}")
    
    async def update_event(self, calendar_id: str, event_id: str, event_data: Dict) -> Dict:
        """Update an existing calendar event"""
        
        if not self.service:
            return self._mock_update_event(event_id, event_data)
        
        try:
            updated_event = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event_data
            ).execute()
            
            self._enhance_event_data(updated_event)
            return updated_event
            
        except HttpError as e:
            if e.resp.status == 404:
                raise Exception("Event not found. It may have been deleted.")
            elif e.resp.status == 403:
                raise Exception("Cannot modify this event. Check permissions.")
            else:
                raise Exception(f"Calendar API error: {e}")
                
        except Exception as e:
            raise Exception(f"Could not update calendar event: {str(e)}")
    
    async def delete_event(self, calendar_id: str, event_id: str) -> bool:
        """Delete a calendar event"""
        
        if not self.service:
            return True  # Mock success
        
        try:
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            return True
            
        except HttpError as e:
            if e.resp.status == 404:
                # Event already deleted
                return True
            elif e.resp.status == 403:
                raise Exception("Cannot delete this event. Check permissions.")
            else:
                raise Exception(f"Calendar API error: {e}")
                
        except Exception as e:
            raise Exception(f"Could not delete calendar event: {str(e)}")
    
    async def get_free_busy(self, calendar_ids: List[str], time_min: str, time_max: str) -> Dict:
        """Get free/busy information for multiple calendars"""
        
        if not self.service:
            return self._mock_free_busy(calendar_ids, time_min, time_max)
        
        try:
            # Build request for free/busy query
            body = {
                "timeMin": time_min,
                "timeMax": time_max,
                "items": [{"id": cal_id} for cal_id in calendar_ids]
            }
            
            freebusy_result = self.service.freebusy().query(body=body).execute()
            
            return freebusy_result.get('calendars', {})
            
        except HttpError as e:
            raise Exception(f"Free/busy query failed: {e}")
        except Exception as e:
            raise Exception(f"Could not check availability: {str(e)}")
    
    def _enhance_event_data(self, event: Dict):
        """Add family-friendly enhancements to event data"""
        
        # Add human-readable time formats
        if event.get('start', {}).get('dateTime'):
            start_dt = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
            event['start']['human_time'] = start_dt.strftime("%I:%M %p")
            event['start']['human_date'] = start_dt.strftime("%A, %B %d")
        
        if event.get('end', {}).get('dateTime'):
            end_dt = datetime.fromisoformat(event['end']['dateTime'].replace('Z', '+00:00'))
            event['end']['human_time'] = end_dt.strftime("%I:%M %p")
        
        # Calculate duration
        if (event.get('start', {}).get('dateTime') and 
            event.get('end', {}).get('dateTime')):
            start_dt = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(event['end']['dateTime'].replace('Z', '+00:00'))
            duration = end_dt - start_dt
            event['duration_minutes'] = int(duration.total_seconds() / 60)
        
        # Family-friendly summary
        if not event.get('summary'):
            event['summary'] = 'Busy'
    
    def _mock_get_events(self, time_min: str, time_max: str, max_results: int) -> List[Dict]:
        """Mock calendar events for testing without API access"""
        
        # Generate sample events for development/testing
        now = datetime.now()
        mock_events = [
            {
                'id': 'mock_event_1',
                'summary': 'Morning Standup',
                'start': {
                    'dateTime': (now + timedelta(hours=1)).isoformat(),
                    'human_time': '9:00 AM',
                    'human_date': 'Today'
                },
                'end': {
                    'dateTime': (now + timedelta(hours=1, minutes=30)).isoformat(),
                    'human_time': '9:30 AM'
                },
                'location': 'Conference Room',
                'duration_minutes': 30
            },
            {
                'id': 'mock_event_2',
                'summary': 'Lunch with Cindy',
                'start': {
                    'dateTime': (now + timedelta(hours=4)).isoformat(),
                    'human_time': '12:00 PM',
                    'human_date': 'Today'
                },
                'end': {
                    'dateTime': (now + timedelta(hours=5)).isoformat(),
                    'human_time': '1:00 PM'
                },
                'duration_minutes': 60
            }
        ]
        
        # Filter by time range if provided
        if time_min and time_max:
            filtered_events = []
            for event in mock_events:
                event_start = event['start']['dateTime']
                if time_min <= event_start <= time_max:
                    filtered_events.append(event)
            return filtered_events[:max_results]
        
        return mock_events[:max_results]
    
    def _mock_create_event(self, event_data: Dict) -> Dict:
        """Mock event creation for testing"""
        
        created_event = {
            'id': f'mock_created_{datetime.now().timestamp()}',
            'summary': event_data.get('summary', 'New Event'),
            'start': event_data.get('start', {}),
            'end': event_data.get('end', {}),
            'location': event_data.get('location', ''),
            'description': event_data.get('description', ''),
            'htmlLink': f'https://calendar.google.com/calendar/event?eid=mock_link',
            'created': datetime.now().isoformat(),
            'status': 'confirmed'
        }
        
        self._enhance_event_data(created_event)
        return created_event
    
    def _mock_update_event(self, event_id: str, event_data: Dict) -> Dict:
        """Mock event update for testing"""
        
        updated_event = {
            'id': event_id,
            'summary': event_data.get('summary', 'Updated Event'),
            'start': event_data.get('start', {}),
            'end': event_data.get('end', {}),
            'location': event_data.get('location', ''),
            'description': event_data.get('description', ''),
            'htmlLink': f'https://calendar.google.com/calendar/event?eid={event_id}',
            'updated': datetime.now().isoformat(),
            'status': 'confirmed'
        }
        
        self._enhance_event_data(updated_event)
        return updated_event
    
    def _mock_free_busy(self, calendar_ids: List[str], time_min: str, time_max: str) -> Dict:
        """Mock free/busy data for testing"""
        
        # Generate mock busy periods
        now = datetime.now()
        mock_busy = {
            cal_id: {
                'busy': [
                    {
                        'start': (now + timedelta(hours=2)).isoformat(),
                        'end': (now + timedelta(hours=3)).isoformat()
                    }
                ]
            }
            for cal_id in calendar_ids
        }
        
        return mock_busy

# Utility functions
def format_datetime_for_calendar(dt: datetime, timezone: str = 'America/New_York') -> Dict:
    """Format datetime for Google Calendar API"""
    return {
        'dateTime': dt.isoformat(),
        'timeZone': timezone
    }

def parse_calendar_datetime(cal_datetime: Dict) -> datetime:
    """Parse datetime from Google Calendar API response"""
    if 'dateTime' in cal_datetime:
        return datetime.fromisoformat(cal_datetime['dateTime'].replace('Z', '+00:00'))
    elif 'date' in cal_datetime:
        # All-day event
        return datetime.fromisoformat(cal_datetime['date'])
    else:
        raise ValueError("Invalid calendar datetime format")

# Factory function
def create_calendar_api(credentials_path: str = None) -> GoogleCalendarAPI:
    """Create configured Google Calendar API wrapper"""
    return GoogleCalendarAPI(credentials_path)