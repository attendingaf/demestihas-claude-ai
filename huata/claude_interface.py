#!/usr/bin/env python3
"""
Claude Desktop Interface for Huata Calendar Agent
Provides simple command-line access to calendar functions
"""

import sys
import os
import asyncio
import json
import argparse
from datetime import datetime, timedelta
from huata import HuataCalendarAgent

async def main():
    parser = argparse.ArgumentParser(description='Huata Calendar CLI')
    parser.add_argument('action', choices=['query', 'schedule', 'list', 'check', 'test'])
    parser.add_argument('--text', help='Natural language query')
    parser.add_argument('--date', help='Date (YYYY-MM-DD)')
    parser.add_argument('--time', help='Time (HH:MM)')
    parser.add_argument('--duration', type=int, help='Duration in minutes')
    parser.add_argument('--title', help='Event title')

    args = parser.parse_args()

    # Initialize Huata with API key from environment
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key and args.action != 'check':
        print("❌ Error: ANTHROPIC_API_KEY not found in environment")
        sys.exit(1)

    # Create agent (API key can be empty for 'check' action)
    agent = HuataCalendarAgent(anthropic_api_key=api_key or 'dummy-key-for-check')
    # No initialize() method needed - agent is ready after __init__

    # Route based on action
    if args.action == 'query':
        user_context = {'user': 'mene', 'timezone': 'America/New_York'}
        result = await agent.process_query(
            args.text or "What's on my calendar today?",
            user_context
        )
        print(result)  # process_query returns a string, not dict

    elif args.action == 'schedule':
        user_context = {'user': 'mene', 'timezone': 'America/New_York'}

        # Calculate end time based on duration
        start_datetime = datetime.strptime(f"{args.date or datetime.now().strftime('%Y-%m-%d')} {args.time or '09:00'}", '%Y-%m-%d %H:%M')
        end_datetime = start_datetime + timedelta(minutes=args.duration or 60)

        event_params = {
            'title': args.title or 'New Event',
            'start_time': start_datetime.isoformat(),
            'end_time': end_datetime.isoformat()
        }
        result = await agent.schedule_event(event_params, user_context)
        print(json.dumps(result, indent=2))

    elif args.action == 'list':
        user_context = {'user': 'mene', 'timezone': 'America/New_York'}
        date = args.date or datetime.now().strftime('%Y-%m-%d')

        # Create time range for the day
        start_datetime = datetime.strptime(date, '%Y-%m-%d')
        end_datetime = start_datetime + timedelta(days=1)

        params = {
            'time_range': {
                'start': start_datetime.isoformat(),
                'end': end_datetime.isoformat()
            }
        }
        result = await agent.list_events(params, user_context)
        print(json.dumps(result, indent=2))

    elif args.action == 'check':
        # Check if service is working
        print("🔍 Checking Huata Calendar Agent Status...")
        print("-" * 50)

        # Check Google Calendar connection
        try:
            # Check if using OAuth or service account
            using_oauth = hasattr(agent.gcal, 'creds')  # OAuth has creds attribute

            if agent.gcal.service:
                if using_oauth:
                    print("✅ Using OAuth authentication")
                    print("✅ Google Calendar service initialized")

                    # List all accessible calendars for OAuth
                    calendars = await agent.gcal.list_calendars()
                    if calendars:
                        print(f"✅ OAuth initialized: {len(calendars)} calendars accessible")
                        for cal in calendars[:6]:  # Show first 6
                            summary = cal.get('summary', 'Unnamed')
                            if cal.get('primary'):
                                print(f"  📅 {summary} (primary)")
                            else:
                                print(f"  📅 {summary}")
                        if len(calendars) > 6:
                            print(f"  ... and {len(calendars) - 6} more")
                else:
                    print("✅ Using service account authentication")
                    print("✅ Google Calendar service initialized")

                    # Check accessible calendars using direct access
                    accessible = await agent.gcal.list_accessible_calendars()

                    if accessible:
                        print(f"✅ Found {len(accessible)} accessible calendars:")
                        for name, cal_id in accessible.items():
                            # Get first part of calendar ID for display
                            display_id = cal_id.split('@')[0] if '@' in cal_id else cal_id[:30]
                            print(f"  📅 {name}: {display_id}...")
                    else:
                        print("⚠️  No calendars accessible. Share calendars with service account:")
                        if os.path.exists('/app/credentials/huata-service-account.json'):
                            with open('/app/credentials/huata-service-account.json', 'r') as f:
                                creds = json.load(f)
                                service_email = creds.get('client_email', 'unknown')
                                print(f"  📧 Service Account: {service_email}")

                print("\n✅ Huata is fully operational! Try:")
                print("  Query: docker exec huata-calendar-agent python claude_interface.py query --text 'What's on my calendar today?'")
                print("  List:  docker exec huata-calendar-agent python claude_interface.py list")
            else:
                print("❌ Google Calendar service not initialized")
                print("  Running in mock mode - will return sample data")

        except Exception as e:
            print(f"❌ Error checking Google Calendar: {str(e)}")

        # Check Redis connection
        print("\n🔍 Checking Redis connection...")
        try:
            if agent.redis:
                await agent.redis.ping()
                print("✅ Redis connected")
            else:
                print("⚠️  Redis not configured (optional for caching)")
        except Exception as e:
            print(f"⚠️  Redis not connected: {str(e)}")
            print("  (Redis is optional for caching)")

        # Check Anthropic API
        print("\n🔍 Checking Anthropic API...")
        if api_key:
            print("✅ Anthropic API key configured")
        else:
            print("⚠️  Anthropic API key not set")
            print("  Set ANTHROPIC_API_KEY environment variable for LLM features")

    elif args.action == 'test':
        # Test full workflow with real calendar data
        print("🧪 Testing Huata Calendar Agent with REAL DATA...")
        user_context = {'user': 'mene', 'timezone': 'America/New_York'}

        print("\n1️⃣ Testing real event listing...")
        try:
            # List today's events from primary calendar
            params = {
                'time_range': {
                    'start': datetime.now().replace(hour=0, minute=0, second=0).isoformat(),
                    'end': (datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat()
                }
            }
            result = await agent.list_events(params, user_context)
            if result.get('success'):
                print(f"   ✅ Success! Found {result.get('total_count', 0)} events today")
                for event in result.get('events', [])[:3]:
                    print(f"   📅 {event.get('title')} at {event.get('start', 'unknown time')}")
            else:
                print(f"   ❌ Failed: {result.get('error')}")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")

        print("\n2️⃣ Testing availability check...")
        try:
            # Check if free now for next 2 hours
            result = await agent.check_availability(
                {
                    'time_range': {
                        'start': datetime.now().isoformat(),
                        'end': (datetime.now() + timedelta(hours=2)).isoformat()
                    }
                },
                user_context
            )
            if result.get('success'):
                print(f"   ✅ Success! Currently {'free' if result.get('is_free') else 'busy'}")
                print(f"   📊 {result.get('total_events', 0)} events in next 2 hours")
            else:
                print(f"   ❌ Failed: {result.get('error')}")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")

        print("\n✅ Test complete! Huata is working with real calendar data!")

if __name__ == "__main__":
    asyncio.run(main())
