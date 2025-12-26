#!/usr/bin/env python3
"""
Setup script for Google API authentication
Helps configure Gmail and Calendar API access for ambient capture
"""
import os
import json
import sys


def setup_google_auth():
    """Guide user through Google API setup"""
    print("=" * 60)
    print("Lyco 2.0 - Google API Setup")
    print("=" * 60)
    print("\nThis script will help you set up Google API access for:")
    print("  • Gmail (for email signal capture)")
    print("  • Calendar (for meeting preparation tasks)")
    print("\n" + "=" * 60)

    # Check if credentials directory exists
    creds_dir = os.path.join(os.path.dirname(__file__), 'credentials')
    if not os.path.exists(creds_dir):
        os.makedirs(creds_dir)
        print(f"✓ Created credentials directory: {creds_dir}")

    print("\n📋 SETUP INSTRUCTIONS:")
    print("\n1. Go to: https://console.cloud.google.com/")
    print("2. Create a new project or select existing one")
    print("3. Enable these APIs:")
    print("   • Gmail API")
    print("   • Google Calendar API")
    print("\n4. Create OAuth 2.0 credentials:")
    print("   • Go to APIs & Services > Credentials")
    print("   • Click 'Create Credentials' > 'OAuth client ID'")
    print("   • Choose 'Desktop app' as application type")
    print("   • Download the JSON file")
    print("\n5. Save the downloaded files as:")
    print(f"   • Gmail: {creds_dir}/gmail_credentials.json")
    print(f"   • Calendar: {creds_dir}/calendar_credentials.json")
    print("   (You can use the same file for both)")

    print("\n" + "=" * 60)

    # Check current status
    gmail_creds = os.path.join(creds_dir, 'gmail_credentials.json')
    calendar_creds = os.path.join(creds_dir, 'calendar_credentials.json')

    print("\n📊 CURRENT STATUS:")
    if os.path.exists(gmail_creds):
        print("✅ Gmail credentials found")
    else:
        print("❌ Gmail credentials missing")

    if os.path.exists(calendar_creds):
        print("✅ Calendar credentials found")
    else:
        print("❌ Calendar credentials missing")

    # Offer to copy credentials if one exists
    if os.path.exists(gmail_creds) and not os.path.exists(calendar_creds):
        response = input("\nUse same credentials for Calendar? (y/n): ")
        if response.lower() == 'y':
            with open(gmail_creds, 'r') as f:
                data = f.read()
            with open(calendar_creds, 'w') as f:
                f.write(data)
            print("✓ Copied Gmail credentials to Calendar")

    elif os.path.exists(calendar_creds) and not os.path.exists(gmail_creds):
        response = input("\nUse same credentials for Gmail? (y/n): ")
        if response.lower() == 'y':
            with open(calendar_creds, 'r') as f:
                data = f.read()
            with open(gmail_creds, 'w') as f:
                f.write(data)
            print("✓ Copied Calendar credentials to Gmail")

    # Test authentication
    if os.path.exists(gmail_creds) and os.path.exists(calendar_creds):
        print("\n" + "=" * 60)
        print("\n🔐 AUTHENTICATION TEST:")
        print("\nWhen you first run ambient capture, you'll be prompted to:")
        print("1. Authorize Gmail access in your browser")
        print("2. Authorize Calendar access in your browser")
        print("\nTokens will be saved for future use.")

        response = input("\nTest authentication now? (y/n): ")
        if response.lower() == 'y':
            test_auth()
    else:
        print("\n⚠️  Please add credential files before running ambient capture")
        print("\nRun this script again after adding credentials to test.")

    print("\n" + "=" * 60)
    print("Setup complete! Next steps:")
    print("1. Ensure credentials are in place")
    print("2. Run: python ambient/ambient_capture.py")
    print("3. Or deploy with: docker-compose up -d")
    print("=" * 60)


def test_auth():
    """Test Google API authentication"""
    try:
        print("\nTesting Gmail authentication...")
        from ambient.capture_email import EmailCapture
        email_capture = EmailCapture()
        if email_capture.service:
            print("✅ Gmail authentication successful!")
        else:
            print("❌ Gmail authentication failed")

        print("\nTesting Calendar authentication...")
        from ambient.capture_calendar import CalendarCapture
        calendar_capture = CalendarCapture()
        if calendar_capture.service:
            print("✅ Calendar authentication successful!")
        else:
            print("❌ Calendar authentication failed")

    except ImportError as e:
        print(f"\n❌ Error: Missing dependencies. Run: pip install -r requirements.txt")
        print(f"   Details: {e}")
    except Exception as e:
        print(f"\n❌ Authentication test failed: {e}")


if __name__ == "__main__":
    setup_google_auth()
