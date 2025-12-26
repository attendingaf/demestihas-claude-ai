"""
Lyco 2.0 Google Calendar Signal Capture
Extracts preparation tasks from upcoming calendar events
"""
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("Google API libraries not installed. Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")

logger = logging.getLogger(__name__)

# Event types that need preparation
PREP_REQUIRED_PATTERNS = {
    'board': "Review board deck and quarterly metrics",
    'interview': "Review candidate resume and prepare questions",
    '1:1': "Review notes and prepare agenda for {attendee}",
    'one-on-one': "Review notes and prepare agenda for {attendee}",
    'presentation': "Finalize presentation slides and practice delivery",
    'review': "Gather materials and prepare feedback",
    'strategic': "Review strategic documents and prepare talking points",
    'planning': "Gather data and prepare planning materials",
    'budget': "Review financial reports and prepare questions",
    'quarterly': "Prepare quarterly update and metrics",
    'all-hands': "Prepare all-hands talking points and Q&A",
    'investor': "Review investor deck and metrics",
    'vendor': "Review vendor proposal and prepare questions",
    'customer': "Review customer account and prepare discussion topics",
    'performance': "Review performance data and prepare feedback"
}


class CalendarCapture:
    """Captures preparation signals from Google Calendar"""

    def __init__(self):
        self.service = None
        self.credentials = None
        self._init_calendar_service()

    def _init_calendar_service(self):
        """Initialize Google Calendar API service"""
        try:
            SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
            creds = None

            # Token file path
            token_path = os.path.join(
                os.path.dirname(__file__),
                '../credentials/calendar_token.json'
            )
            creds_path = os.path.join(
                os.path.dirname(__file__),
                '../credentials/calendar_credentials.json'
            )

            # Load token if exists
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)

            # If no valid credentials, authenticate
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if os.path.exists(creds_path):
                        flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                        creds = flow.run_local_server(port=0)
                    else:
                        logger.warning(f"Calendar credentials file not found at {creds_path}")
                        return

                # Save credentials for next time
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())

            self.service = build('calendar', 'v3', credentials=creds)
            logger.info("Calendar API service initialized")

        except Exception as e:
            logger.error(f"Error initializing Calendar service: {e}")

    async def capture_signals(self, calendar_id: str = 'primary') -> List[Dict[str, Any]]:
        """Capture preparation signals from calendar events"""
        if not self.service:
            logger.warning("Calendar service not initialized")
            return []

        signals = []

        try:
            # Get events for next 7 days
            now = datetime.utcnow()
            time_min = now.isoformat() + 'Z'
            time_max = (now + timedelta(days=7)).isoformat() + 'Z'

            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=50,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])

            for event in events:
                prep_task = self._generate_prep_task(event)
                if prep_task:
                    event_time = self._parse_event_time(event)

                    # Only create prep tasks for events > 2 hours away
                    if event_time and (event_time - datetime.now()).total_seconds() > 7200:
                        signals.append({
                            'content': prep_task,
                            'metadata': {
                                'event_id': event['id'],
                                'event_title': event.get('summary', 'Untitled'),
                                'event_time': event_time.isoformat() if event_time else None,
                                'calendar_id': calendar_id,
                                'attendees': self._extract_attendees(event),
                                'location': event.get('location', ''),
                                'timestamp': datetime.now().isoformat()
                            }
                        })

            logger.info(f"Captured {len(signals)} calendar signals from {calendar_id}")

        except HttpError as error:
            logger.error(f"Calendar API error for {calendar_id}: {error}")

        return signals

    def _generate_prep_task(self, event: Dict) -> str:
        """Generate preparation task based on event type"""
        summary = event.get('summary', '').lower()
        description = event.get('description', '').lower()

        # Check if event needs preparation
        for pattern, prep_template in PREP_REQUIRED_PATTERNS.items():
            if pattern in summary or pattern in description:
                # Get first attendee name if applicable
                attendees = self._extract_attendees(event)
                attendee_name = attendees[0].split('@')[0] if attendees else 'the meeting'

                prep_task = prep_template.format(attendee=attendee_name)
                return f"Prepare for {event.get('summary', 'meeting')}: {prep_task}"

        # Check if it's a meeting with multiple attendees (likely needs prep)
        attendees = event.get('attendees', [])
        if len(attendees) > 3:  # Larger meetings often need prep
            return f"Prepare agenda and materials for {event.get('summary', 'meeting')}"

        # Check for recurring meetings (often need prep)
        if event.get('recurringEventId'):
            if '1:1' in summary or 'sync' in summary or 'check-in' in summary:
                attendees = self._extract_attendees(event)
                attendee_name = attendees[0].split('@')[0] if attendees else 'the meeting'
                return f"Review notes for recurring {event.get('summary', 'meeting')} with {attendee_name}"

        return None

    def _parse_event_time(self, event: Dict) -> datetime:
        """Parse event start time"""
        try:
            start = event.get('start', {})

            # Handle all-day events
            if 'date' in start:
                return datetime.strptime(start['date'], '%Y-%m-%d')

            # Handle timed events
            elif 'dateTime' in start:
                # Remove timezone info for simplicity
                dt_str = start['dateTime'].split('+')[0].split('-')[0]
                if 'T' in dt_str:
                    return datetime.strptime(dt_str.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                return datetime.strptime(dt_str, '%Y-%m-%d')

        except Exception as e:
            logger.warning(f"Error parsing event time: {e}")

        return None

    def _extract_attendees(self, event: Dict) -> List[str]:
        """Extract attendee emails from event"""
        attendees = event.get('attendees', [])
        attendee_emails = []

        for attendee in attendees:
            email = attendee.get('email', '')
            # Skip the organizer and resource rooms
            if not attendee.get('organizer') and not attendee.get('resource'):
                if email and '@' in email:
                    attendee_emails.append(email)

        return attendee_emails
