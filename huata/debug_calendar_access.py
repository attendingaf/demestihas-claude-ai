#!/usr/bin/env python3
"""Debug script to test calendar access methods"""

import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def test_calendar_access():
    # Load credentials
    creds_path = '/app/credentials/huata-service-account.json'
    print(f"Loading credentials from: {creds_path}")
    
    with open(creds_path, 'r') as f:
        cred_data = json.load(f)
        service_account = cred_data.get('client_email')
        print(f"Service Account: {service_account}\n")
    
    # Build service
    creds = Credentials.from_service_account_file(
        creds_path,
        scopes=[
            'https://www.googleapis.com/auth/calendar.readonly',
            'https://www.googleapis.com/auth/calendar.events'
        ]
    )
    service = build('calendar', 'v3', credentials=creds)
    
    print("="*60)
    print("METHOD 1: List calendars via calendarList().list()")
    print("="*60)
    try:
        result = service.calendarList().list().execute()
        calendars = result.get('items', [])
        print(f"✓ Found {len(calendars)} calendars")
        for cal in calendars:
            print(f"  📅 {cal.get('summary', 'Unnamed')}")
            print(f"     ID: {cal.get('id')}")
            print(f"     Role: {cal.get('accessRole')}")
    except HttpError as e:
        print(f"✗ Error: {e.resp.status} - {e.error_details}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("\n" + "="*60)
    print("METHOD 2: Direct calendar access")
    print("="*60)
    
    # Test calendars to try
    test_calendars = [
        'menelaos4@gmail.com',
        'primary',  # This would only work if impersonating
        'mene@beltlineconsulting.co'
    ]
    
    for cal_id in test_calendars:
        print(f"\nTrying calendar: {cal_id}")
        try:
            # Try to get calendar metadata
            calendar = service.calendars().get(calendarId=cal_id).execute()
            print(f"  ✓ Can access calendar: {calendar.get('summary', 'Unnamed')}")
            
            # Try to list events
            events = service.events().list(
                calendarId=cal_id, 
                maxResults=2,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            event_items = events.get('items', [])
            print(f"  ✓ Can read events: {len(event_items)} events found")
            for event in event_items:
                print(f"    - {event.get('summary', 'No title')}")
                
        except HttpError as e:
            if e.resp.status == 404:
                print(f"  ✗ Calendar not found")
            elif e.resp.status == 403:
                print(f"  ✗ Access denied - calendar not shared or permissions insufficient")
            else:
                print(f"  ✗ HTTP Error {e.resp.status}: {e.error_details}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    print("\n" + "="*60)
    print("METHOD 3: Check if Calendar API is enabled")
    print("="*60)
    try:
        # Simple API call to verify the API is enabled
        colors = service.colors().get().execute()
        print(f"✓ Calendar API is enabled (found {len(colors.get('calendar', {}))} color definitions)")
    except HttpError as e:
        if e.resp.status == 403:
            print("✗ Calendar API may not be enabled in the Google Cloud project")
        else:
            print(f"✗ API Error: {e.resp.status}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("\n" + "="*60)
    print("DIAGNOSIS")
    print("="*60)
    print("\nPossible issues if calendars aren't showing:")
    print("1. Service account needs to ACCEPT the calendar invitation")
    print("   - Service accounts can't accept automatically")
    print("   - Try using 'Make changes and manage sharing' permission")
    print("2. Use domain-wide delegation (Google Workspace only)")
    print("3. Access calendars directly by ID instead of listing")
    print("4. Ensure Calendar API is enabled in Google Cloud Console")
    print("\nRecommended approach:")
    print("- Use direct calendar access with known calendar IDs")
    print("- Store calendar IDs in configuration")
    print("- Don't rely on calendarList() for service accounts")

if __name__ == "__main__":
    test_calendar_access()
