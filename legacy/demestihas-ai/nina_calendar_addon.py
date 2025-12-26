# Nina Phase 2 - Google Calendar Integration Add-on
# This code will be merged into nina.py

import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class CalendarIntegration:
    """Google Calendar integration for Nina scheduling"""
    
    def __init__(self):
        self.calendar_service = None
        self.viola_calendar_id = None
        self.family_calendar_id = 'primary'
        self._init_calendar()
    
    def _init_calendar(self):
        """Initialize Google Calendar API connection"""
        try:
            creds_path = os.getenv('GOOGLE_CALENDAR_CREDS_PATH', '/root/demestihas-ai/credentials/google-service-account.json')
            if os.path.exists(creds_path):
                creds = service_account.Credentials.from_service_account_file(
                    creds_path,
                    scopes=['https://www.googleapis.com/auth/calendar']
                )
                self.calendar_service = build('calendar', 'v3', credentials=creds)
                logger.info("✅ Google Calendar API initialized")
                
                # Find or create Viola's calendar
                self._setup_viola_calendar()
            else:
                logger.warning(f"Calendar credentials not found at {creds_path}")
        except Exception as e:
            logger.warning(f"Google Calendar initialization failed: {e}")
            # Continue without calendar - graceful degradation
    
    def _setup_viola_calendar(self):
        """Find or create a calendar for Viola's schedule"""
        try:
            # For service accounts, we'll create events in the primary calendar
            # with a specific tag/color for Viola's schedule
            self.viola_calendar_id = 'primary'
            logger.info("📅 Using primary calendar for Viola's schedule")
            
        except Exception as e:
            logger.error(f"Failed to setup Viola calendar: {e}")
    
    def sync_schedule_to_calendar(self, schedule_data, week_offset=0):
        """Sync schedule to Google Calendar"""
        if not self.calendar_service:
            return {"success": False, "message": "Calendar sync not available - no API connection"}
        
        try:
            synced_count = 0
            today = datetime.now()
            week_start = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
            
            # Process each day in the schedule
            for day_num in range(7):
                current_date = week_start + timedelta(days=day_num)
                date_str = current_date.strftime('%Y-%m-%d')
                day_name = current_date.strftime('%A').lower()
                
                # Get schedule for this day
                day_schedule = schedule_data.get(day_name, {})
                
                if day_schedule.get('working'):
                    # Create working event
                    start_time = day_schedule.get('start', '07:00')
                    end_time = day_schedule.get('end', '19:00')
                    
                    event = {
                        'summary': '👩‍💼 Viola Working',
                        'description': 'Au pair on duty - regular schedule',
                        'start': {
                            'dateTime': f"{date_str}T{start_time}:00",
                            'timeZone': 'America/New_York',
                        },
                        'end': {
                            'dateTime': f"{date_str}T{end_time}:00",
                            'timeZone': 'America/New_York',
                        },
                        'colorId': '2',  # Green
                        'reminders': {'useDefault': False}
                    }
                    
                    # Check if event already exists
                    existing = self._find_existing_event(date_str, 'Viola')
                    if not existing:
                        self.calendar_service.events().insert(
                            calendarId=self.viola_calendar_id,
                            body=event
                        ).execute()
                        synced_count += 1
                
            return {
                "success": True, 
                "message": f"✅ Calendar synced: {synced_count} events created",
                "events_created": synced_count
            }
            
        except Exception as e:
            logger.error(f"Calendar sync failed: {e}")
            return {"success": False, "message": f"⚠️ Calendar sync failed: {str(e)}"}
    
    def _find_existing_event(self, date_str, keyword):
        """Check if an event already exists for a date"""
        try:
            time_min = f"{date_str}T00:00:00Z"
            time_max = f"{date_str}T23:59:59Z"
            
            events_result = self.calendar_service.events().list(
                calendarId=self.viola_calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            for event in events:
                if keyword.lower() in event.get('summary', '').lower():
                    return event
            return None
            
        except Exception as e:
            logger.error(f"Error checking existing events: {e}")
            return None
    
    def check_calendar_conflicts(self, date, time_range=None):
        """Check for conflicts between Viola's schedule and family events"""
        if not self.calendar_service:
            return []
        
        conflicts = []
        
        try:
            # Format date for API
            if isinstance(date, str):
                target_date = date
            else:
                target_date = date.strftime('%Y-%m-%d')
            
            # Set time bounds
            time_min = f"{target_date}T00:00:00Z"
            time_max = f"{target_date}T23:59:59Z"
            
            # Get all events for that day
            events_result = self.calendar_service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            family_events = events_result.get('items', [])
            
            # Check each family event
            for event in family_events:
                summary = event.get('summary', '').lower()
                
                # Skip Viola's own schedule events
                if 'viola' in summary:
                    continue
                
                # Detect events that might need childcare
                childcare_keywords = ['date night', 'dinner', 'meeting', 'appointment', 
                                     'work', 'conference', 'travel', 'out', 'event']
                
                if any(keyword in summary for keyword in childcare_keywords):
                    conflicts.append({
                        'event': event.get('summary'),
                        'time': self._format_event_time(event),
                        'needs_coverage': True
                    })
            
            return conflicts
            
        except Exception as e:
            logger.error(f"Conflict detection failed: {e}")
            return []
    
    def _format_event_time(self, event):
        """Format event time for display"""
        start = event.get('start', {})
        if 'dateTime' in start:
            # Parse and format the time
            dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
            return dt.strftime('%I:%M %p')
        elif 'date' in start:
            return 'All day'
        return 'Unknown time'
    
    def proactive_gap_detection(self, schedule_data):
        """Scan next 2 weeks for potential coverage gaps"""
        if not self.calendar_service:
            return {"gaps": [], "message": "Calendar integration not available"}
        
        gaps = []
        
        try:
            # Check next 14 days
            for day_offset in range(14):
                check_date = datetime.now() + timedelta(days=day_offset)
                date_str = check_date.strftime('%Y-%m-%d')
                day_name = check_date.strftime('%A').lower()
                
                # Get Viola's schedule for that day
                viola_schedule = schedule_data.get(day_name, {})
                viola_working = viola_schedule.get('working', False)
                
                # Get family events that might need coverage
                conflicts = self.check_calendar_conflicts(date_str)
                
                # Detect gaps
                for conflict in conflicts:
                    if conflict.get('needs_coverage') and not viola_working:
                        gaps.append({
                            'date': date_str,
                            'day': day_name.capitalize(),
                            'event': conflict['event'],
                            'time': conflict['time'],
                            'action': 'Need to arrange coverage'
                        })
            
            if gaps:
                message = f"⚠️ Detected {len(gaps)} coverage gaps in next 2 weeks"
            else:
                message = "✅ No coverage gaps detected in next 2 weeks"
            
            return {"gaps": gaps, "message": message}
            
        except Exception as e:
            logger.error(f"Gap detection failed: {e}")
            return {"gaps": [], "message": "Gap detection encountered an error"}
