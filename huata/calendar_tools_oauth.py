# OAuth-based Google Calendar API wrapper for Huata Agent
# Handles all Google Calendar operations with OAuth2 user authentication
# Part of Demestihas.ai Calendar System

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import traceback
from cryptography.fernet import Fernet
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class GoogleCalendarOAuth:
    """
    OAuth-authenticated Google Calendar API wrapper.

    Uses OAuth2 for user authentication instead of service accounts.
    Provides full read/write access to user's calendars with automatic token refresh.
    """

    def __init__(self):
        """Initialize OAuth-authenticated Google Calendar connection"""
        self.service = None
        self.creds = None
        self.encryption_key = None
        self.cipher = None

        # Known calendar mappings (same as before, for convenience)
        self.known_calendars = {
            'primary': 'primary',  # OAuth uses 'primary' for user's main calendar
            'mene': 'primary',
            'work': 'mene@beltlineconsulting.co',
            'familia': '7dia35946hir6rbq10stda8hk4@group.calendar.google.com',
            'limon': 'e46i6ac3ipii8b7iugsqfeh2j8@group.calendar.google.com',
            'cindy': 'c4djl5q698b556jqliablah9uk@group.calendar.google.com',
            'aupair': 'up5jrbrsng5le7qmu0uhi6pedo@group.calendar.google.com'
        }

        # Initialize OAuth synchronously to ensure service is ready
        try:
            self._initialize_oauth()
        except Exception as e:
            print(f"⚠️  OAuth initialization failed: {e}")
            # Don't raise here - allow graceful degradation

    def _initialize_oauth(self):
        """Load and decrypt OAuth tokens, initialize service"""
        try:
            # Check for encryption key
            key_path = '/app/credentials/encryption.key'
            if not os.path.exists(key_path):
                # Try local path for development
                key_path = 'credentials/encryption.key'
                if not os.path.exists(key_path):
                    raise Exception("Encryption key not found. Run setup_oauth.py first.")

            # Load encryption key
            with open(key_path, 'rb') as f:
                self.encryption_key = f.read()
            self.cipher = Fernet(self.encryption_key)

            # Check for encrypted tokens
            token_path = '/app/credentials/oauth_tokens.enc'
            if not os.path.exists(token_path):
                # Try local path for development
                token_path = 'credentials/oauth_tokens.enc'
                if not os.path.exists(token_path):
                    raise Exception("OAuth tokens not found. Run setup_oauth.py first.")

            # Load and decrypt tokens
            with open(token_path, 'rb') as f:
                encrypted_tokens = f.read()

            decrypted = self.cipher.decrypt(encrypted_tokens)
            token_data = json.loads(decrypted)

            # Recreate credentials object
            self.creds = Credentials(
                token=token_data['token'],
                refresh_token=token_data['refresh_token'],
                token_uri=token_data['token_uri'],
                client_id=token_data['client_id'],
                client_secret=token_data['client_secret'],
                scopes=token_data['scopes']
            )

            # Check if token is expired and refresh if needed
            if self.creds.expired and self.creds.refresh_token:
                print("🔄 Refreshing expired access token...")
                self.creds.refresh(Request())
                self._save_refreshed_token()
                print("✅ Token refreshed successfully")

            # Build Google Calendar service
            self.service = build('calendar', 'v3', credentials=self.creds)

            # Test access by listing calendars
            calendars = self.service.calendarList().list().execute()
            calendar_items = calendars.get('items', [])

            print(f"✅ OAuth initialized: {len(calendar_items)} calendars accessible")

            # Show accessible calendars
            if calendar_items:
                print("📅 Accessible calendars:")
                for cal in calendar_items[:6]:  # Show first 6
                    summary = cal.get('summary', 'Unnamed')
                    cal_id = cal.get('id', '')
                    if cal.get('primary'):
                        print(f"  - {summary} (primary)")
                    else:
                        print(f"  - {summary}")

        except Exception as e:
            print(f"❌ OAuth initialization error: {e}")
            raise

    def _save_refreshed_token(self):
        """Save refreshed token back to encrypted file"""
        try:
            if not self.creds or not self.cipher:
                return

            # Prepare updated token data
            token_data = {
                'token': self.creds.token,
                'refresh_token': self.creds.refresh_token,
                'token_uri': self.creds.token_uri,
                'client_id': self.creds.client_id,
                'client_secret': self.creds.client_secret,
                'scopes': self.creds.scopes,
                'expiry': self.creds.expiry.isoformat() if self.creds.expiry else None
            }

            # Encrypt the updated tokens
            encrypted = self.cipher.encrypt(json.dumps(token_data).encode())

            # Determine token path
            token_path = '/app/credentials/oauth_tokens.enc'
            if not os.path.exists(os.path.dirname(token_path)):
                token_path = 'credentials/oauth_tokens.enc'

            # Save encrypted tokens
            with open(token_path, 'wb') as f:
                f.write(encrypted)

            print("💾 Refreshed token saved")

        except Exception as e:
            print(f"⚠️  Could not save refreshed token: {e}")

    def _ensure_authenticated(self):
        """Ensure we have valid authentication before API calls"""
        if not self.service:
            raise Exception("Calendar service not initialized. Run setup_oauth.py")

        # Check if token needs refresh
        if self.creds and self.creds.expired and self.creds.refresh_token:
            print("🔄 Token expired, refreshing...")
            self.creds.refresh(Request())
            self._save_refreshed_token()
            self.service = build('calendar', 'v3', credentials=self.creds)

    def _resolve_calendar_id(self, calendar_id: str) -> str:
        """Resolve calendar aliases to actual calendar IDs"""
        # For OAuth, 'primary' is a special keyword that works directly
        if calendar_id == 'primary' or calendar_id == 'mene':
            return 'primary'

        # Check known aliases
        if calendar_id in self.known_calendars:
            return self.known_calendars[calendar_id]

        # Otherwise, assume it's a real calendar ID
        return calendar_id

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
        self._ensure_authenticated()

        try:
            # Resolve calendar ID
            actual_calendar_id = self._resolve_calendar_id(calendar_id)

            # Set default time range if not provided
            if not time_min:
                time_min = datetime.now().isoformat() + 'Z'
            if not time_max:
                time_max = (datetime.now() + timedelta(days=7)).isoformat() + 'Z'

            # Call Google Calendar API
            print(f"📅 Fetching events from: {actual_calendar_id}")
            events_result = self.service.events().list(
                calendarId=actual_calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])

            # Add human-readable formatting
            for event in events:
                self._enhance_event_data(event)

            print(f"✅ Found {len(events)} events")
            return events

        except HttpError as e:
            if e.resp.status == 403:
                raise Exception(f"Access denied to calendar '{actual_calendar_id}'")
            elif e.resp.status == 404:
                raise Exception(f"Calendar '{actual_calendar_id}' not found")
            else:
                raise Exception(f"Calendar API error: {e.resp.status}")

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
        self._ensure_authenticated()

        try:
            # Resolve calendar ID
            actual_calendar_id = self._resolve_calendar_id(calendar_id)

            # Validate required fields
            if not event_data.get('summary'):
                raise Exception("Event title is required")
            if not event_data.get('start'):
                raise Exception("Event start time is required")
            if not event_data.get('end'):
                raise Exception("Event end time is required")

            # Create event via Google Calendar API
            print(f"📝 Creating event in: {actual_calendar_id}")
            created_event = self.service.events().insert(
                calendarId=actual_calendar_id,
                body=event_data
            ).execute()

            # Enhance with human-readable data
            self._enhance_event_data(created_event)

            print(f"✅ Event created: {created_event.get('summary')}")
            return created_event

        except HttpError as e:
            if e.resp.status == 403:
                raise Exception(f"Cannot create events in '{actual_calendar_id}'")
            elif e.resp.status == 400:
                raise Exception("Invalid event data. Check date/time format.")
            else:
                raise Exception(f"Calendar API error: {e.resp.status}")

        except Exception as e:
            raise Exception(f"Could not create calendar event: {str(e)}")

    async def update_event(self, calendar_id: str, event_id: str, updates: Dict) -> Dict:
        """
        Update an existing calendar event

        Args:
            calendar_id: Calendar containing the event
            event_id: ID of event to update
            updates: Fields to update

        Returns:
            Updated event dictionary
        """
        self._ensure_authenticated()

        try:
            # Resolve calendar ID
            actual_calendar_id = self._resolve_calendar_id(calendar_id)

            # Get existing event
            print(f"🔍 Fetching event {event_id} from {actual_calendar_id}")
            event = self.service.events().get(
                calendarId=actual_calendar_id,
                eventId=event_id
            ).execute()

            # Apply updates
            event.update(updates)

            # Save changes
            print(f"💾 Updating event: {event.get('summary')}")
            updated_event = self.service.events().update(
                calendarId=actual_calendar_id,
                eventId=event_id,
                body=event
            ).execute()

            # Enhance with human-readable data
            self._enhance_event_data(updated_event)

            print(f"✅ Event updated: {updated_event.get('summary')}")
            return updated_event

        except HttpError as e:
            if e.resp.status == 404:
                raise Exception("Event not found. It may have been deleted.")
            elif e.resp.status == 403:
                raise Exception("Cannot modify this event. Check permissions.")
            else:
                raise Exception(f"Calendar API error: {e.resp.status}")

        except Exception as e:
            raise Exception(f"Could not update calendar event: {str(e)}")

    async def delete_event(self, calendar_id: str, event_id: str) -> bool:
        """
        Delete a calendar event

        Args:
            calendar_id: Calendar containing the event
            event_id: ID of event to delete

        Returns:
            True if successful
        """
        self._ensure_authenticated()

        try:
            # Resolve calendar ID
            actual_calendar_id = self._resolve_calendar_id(calendar_id)

            print(f"🗑️  Deleting event {event_id} from {actual_calendar_id}")
            self.service.events().delete(
                calendarId=actual_calendar_id,
                eventId=event_id
            ).execute()

            print(f"✅ Event deleted")
            return True

        except HttpError as e:
            if e.resp.status == 404:
                # Event already deleted
                return True
            elif e.resp.status == 403:
                raise Exception("Cannot delete this event. Check permissions.")
            else:
                raise Exception(f"Calendar API error: {e.resp.status}")

        except Exception as e:
            raise Exception(f"Could not delete calendar event: {str(e)}")

    async def list_calendars(self) -> List[Dict]:
        """
        List all accessible calendars

        Returns:
            List of calendar dictionaries
        """
        self._ensure_authenticated()

        try:
            print("📚 Listing all accessible calendars...")
            calendar_list = self.service.calendarList().list().execute()
            calendars = calendar_list.get('items', [])

            print(f"✅ Found {len(calendars)} calendars")
            return calendars

        except HttpError as e:
            raise Exception(f"Could not list calendars: {e.resp.status}")
        except Exception as e:
            raise Exception(f"Could not list calendars: {str(e)}")

    async def get_free_busy(self, calendar_ids: List[str], time_min: str, time_max: str) -> Dict:
        """
        Get free/busy information for multiple calendars

        Args:
            calendar_ids: List of calendar IDs to check
            time_min: Start time (ISO format)
            time_max: End time (ISO format)

        Returns:
            Dictionary of free/busy data per calendar
        """
        self._ensure_authenticated()

        try:
            # Resolve all calendar IDs
            actual_calendar_ids = [self._resolve_calendar_id(cal_id) for cal_id in calendar_ids]

            # Build request for free/busy query
            body = {
                "timeMin": time_min,
                "timeMax": time_max,
                "items": [{"id": cal_id} for cal_id in actual_calendar_ids]
            }

            print(f"🔍 Checking availability for {len(actual_calendar_ids)} calendars...")
            freebusy_result = self.service.freebusy().query(body=body).execute()

            print("✅ Free/busy data retrieved")
            return freebusy_result.get('calendars', {})

        except HttpError as e:
            raise Exception(f"Free/busy query failed: {e.resp.status}")
        except Exception as e:
            raise Exception(f"Could not check availability: {str(e)}")

    def _enhance_event_data(self, event: Dict):
        """Add human-readable enhancements to event data"""

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

        # Ensure summary exists
        if not event.get('summary'):
            event['summary'] = 'Busy'

# Utility functions (same as before)
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
def create_calendar_api() -> GoogleCalendarOAuth:
    """Create configured OAuth Google Calendar API wrapper"""
    return GoogleCalendarOAuth()
