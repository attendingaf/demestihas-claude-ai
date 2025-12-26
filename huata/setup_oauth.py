#!/usr/bin/env python3
"""
One-time OAuth setup for Huata Calendar Agent
Run this locally to authorize Huata to access your calendars
"""

import os
import json
import sys
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from cryptography.fernet import Fernet

# OAuth scopes for full calendar access
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events'
]

def setup_oauth():
    """Run OAuth flow and save encrypted tokens"""

    print("🔐 Huata OAuth Setup")
    print("=" * 50)
    print("This will authorize Huata to manage your Google Calendar.")
    print("A browser window will open for you to approve access.\n")

    # Check if OAuth client credentials exist
    oauth_client_file = 'credentials/oauth_client_secret.json'
    if not os.path.exists(oauth_client_file):
        print(f"❌ OAuth client credentials not found at {oauth_client_file}")
        print("\nTo fix this:")
        print("1. Go to Google Cloud Console (https://console.cloud.google.com)")
        print("2. Select your project (md2-4444)")
        print("3. Go to APIs & Services > Credentials")
        print("4. Click 'Create Credentials' > 'OAuth client ID'")
        print("5. Choose 'Desktop app' as application type")
        print("6. Name it 'Huata Calendar Agent'")
        print("7. Download the JSON file")
        print(f"8. Save it as {oauth_client_file}")
        return False

    try:
        # Use existing credentials file for OAuth client
        flow = InstalledAppFlow.from_client_secrets_file(
            oauth_client_file, SCOPES)

        print("📱 Opening browser for authorization...")
        print("If browser doesn't open automatically, visit this URL:")

        # Run local server for auth callback
        creds = flow.run_local_server(
            port=8080,
            prompt='consent',  # Force consent screen to ensure refresh token
            access_type='offline'  # Request refresh token
        )

        if not creds.refresh_token:
            print("\n⚠️  Warning: No refresh token received. You may need to re-authorize.")
            print("Try removing app access at: https://myaccount.google.com/permissions")
            print("Then run this setup again.")

        # Generate encryption key
        key = Fernet.generate_key()
        cipher = Fernet(key)

        # Prepare token data for encryption
        token_data = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes,
            'expiry': creds.expiry.isoformat() if creds.expiry else None
        }

        # Encrypt the tokens
        encrypted_tokens = cipher.encrypt(json.dumps(token_data).encode())

        # Save encrypted tokens and key
        os.makedirs('credentials', exist_ok=True)

        with open('credentials/oauth_tokens.enc', 'wb') as f:
            f.write(encrypted_tokens)

        with open('credentials/encryption.key', 'wb') as f:
            f.write(key)

        print("\n✅ OAuth setup complete!")
        print("Tokens saved to credentials/oauth_tokens.enc")
        print("\n🎯 Next steps:")
        print("1. Restart Huata: docker-compose down && docker-compose up -d")
        print("2. Test access: docker exec huata-calendar-agent python claude_interface.py check")
        print("3. List events: docker exec huata-calendar-agent python claude_interface.py list")

        # Quick validation
        print("\n🔍 Validating access...")
        from googleapiclient.discovery import build

        service = build('calendar', 'v3', credentials=creds)
        calendars = service.calendarList().list().execute()
        calendar_count = len(calendars.get('items', []))

        print(f"✅ Successfully authorized! Access to {calendar_count} calendars:")
        for cal in calendars.get('items', [])[:6]:  # Show first 6
            print(f"  - {cal.get('summary', 'Unnamed')}")

        if calendar_count > 6:
            print(f"  ... and {calendar_count - 6} more")

        return True

    except Exception as e:
        print(f"\n❌ OAuth setup failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check your internet connection")
        print("2. Ensure you have the correct OAuth client credentials")
        print("3. Try removing existing app permissions at:")
        print("   https://myaccount.google.com/permissions")
        return False

def check_existing_setup():
    """Check if OAuth is already set up"""
    if os.path.exists('credentials/oauth_tokens.enc') and os.path.exists('credentials/encryption.key'):
        print("ℹ️  OAuth tokens already exist.")
        response = input("Do you want to re-authorize? (y/n): ").lower()
        return response == 'y'
    return True

if __name__ == "__main__":
    # Check if we should proceed with setup
    if not check_existing_setup():
        print("Setup cancelled. Existing tokens will be kept.")
        sys.exit(0)

    # Run OAuth setup
    success = setup_oauth()
    sys.exit(0 if success else 1)
