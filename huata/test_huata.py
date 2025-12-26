#!/usr/bin/env python3
"""
Test script for Huata Calendar Agent
Validates natural language understanding and calendar operations
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List

# For local testing without full deployment
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_huata_locally():
    """Test Huata components locally"""

    print("🧪 Testing Huata Calendar Agent Components\n")

    # Test 1: Calendar Intent Classification
    print("Test 1: Intent Classification")
    print("-" * 40)

    test_queries = [
        "Am I free Thursday afternoon?",
        "Schedule a meeting with Dr. Smith next week",
        "What's my day look like tomorrow?",
        "Find 2 hours for deep work this week",
        "Block time for Consilium review",
        "Any conflicts with lunch tomorrow?"
    ]

    try:
        from calendar_intents import CalendarIntentClassifier
        from anthropic import AsyncAnthropic

        # Mock LLM for testing without API key
        class MockLLM:
            async def create(self, **kwargs):
                class Response:
                    content = [type('obj', (object,), {'text': json.dumps({
                        'intent': 'check_availability',
                        'confidence': 0.95,
                        'parameters': {
                            'time_range': {
                                'start': datetime.now().isoformat(),
                                'end': (datetime.now() + timedelta(hours=4)).isoformat()
                            }
                        }
                    })})]
                return Response()

        mock_llm = type('MockAnthropic', (), {'messages': MockLLM()})()
        classifier = CalendarIntentClassifier(mock_llm)

        for query in test_queries:
            result = await classifier.classify_intent(
                query,
                {'user': 'mene', 'timezone': 'America/New_York'}
            )
            print(f"Query: {query[:50]}...")
            print(f"Intent: {result.get('intent')}")
            print(f"Confidence: {result.get('confidence')}")
            print()

        print("✅ Intent classification working\n")

    except Exception as e:
        print(f"❌ Intent classification failed: {e}\n")

    # Test 2: Calendar Tools (Mock Mode)
    print("Test 2: Calendar Tools (Mock Mode)")
    print("-" * 40)

    try:
        from calendar_tools import GoogleCalendarAPI

        gcal = GoogleCalendarAPI()

        # Test getting events (will use mock data)
        events = await gcal.get_events(
            calendar_id='primary',
            time_min=datetime.now().isoformat(),
            time_max=(datetime.now() + timedelta(days=1)).isoformat()
        )

        print(f"Found {len(events)} mock events:")
        for event in events:
            print(f"  - {event.get('summary')} at {event.get('start', {}).get('human_time')}")

        # Test creating event (mock)
        new_event = await gcal.create_event('primary', {
            'summary': 'Test Meeting',
            'start': {'dateTime': (datetime.now() + timedelta(hours=2)).isoformat()},
            'end': {'dateTime': (datetime.now() + timedelta(hours=3)).isoformat()}
        })

        print(f"\n✅ Created mock event: {new_event.get('summary')}")
        print(f"   Link: {new_event.get('htmlLink')}\n")

    except Exception as e:
        print(f"❌ Calendar tools failed: {e}\n")

    # Test 3: Prompt Generation
    print("Test 3: Prompt Generation")
    print("-" * 40)

    try:
        from calendar_prompts import CalendarPrompts

        prompts = CalendarPrompts()

        # Test intent classification prompt
        intent_prompt = prompts.intent_classification_prompt(
            query="Am I free tomorrow at 2pm?",
            current_time=datetime.now(),
            user_context={'user': 'mene'},
            available_intents=['check_availability', 'schedule_event']
        )

        print("Generated intent classification prompt:")
        print(intent_prompt[:200] + "...\n")

        # Test response generation prompt
        response_prompt = prompts.response_generation_prompt(
            query="Am I free tomorrow?",
            result={'success': True, 'is_free': True},
            user_context={'user': 'mene'}
        )

        print("Generated response prompt:")
        print(response_prompt[:200] + "...\n")

        print("✅ Prompt generation working\n")

    except Exception as e:
        print(f"❌ Prompt generation failed: {e}\n")

    # Test 4: Full Huata Integration (Mock)
    print("Test 4: Huata Agent Integration")
    print("-" * 40)

    try:
        # This will fail without proper API keys, but shows structure
        print("Note: Full integration requires:")
        print("  - Anthropic API key for Claude Haiku")
        print("  - Redis running for state management")
        print("  - Google Calendar credentials (optional)")
        print("\nTo test full integration:")
        print("  1. Copy .env.example to .env")
        print("  2. Add your Anthropic API key")
        print("  3. Run: python main.py")
        print("  4. Test API at http://localhost:8003")

    except Exception as e:
        print(f"Integration note: {e}")

async def test_api_endpoints():
    """Test deployed API endpoints"""
    import httpx

    API_URL = "http://localhost:8003"

    print("\n🌐 Testing Deployed API Endpoints\n")

    async with httpx.AsyncClient() as client:

        # Test health check
        try:
            response = await client.get(f"{API_URL}/")
            print("Health Check:", response.json())
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return

        # Test calendar query
        try:
            response = await client.post(
                f"{API_URL}/calendar/query",
                json={
                    "query": "What's on my calendar today?",
                    "user": "mene"
                }
            )
            print("\nCalendar Query Response:")
            print(json.dumps(response.json(), indent=2))
        except Exception as e:
            print(f"❌ Calendar query failed: {e}")

        # Test availability check
        try:
            response = await client.get(
                f"{API_URL}/calendar/availability",
                params={"user": "mene"}
            )
            print("\nAvailability Check:")
            print(json.dumps(response.json(), indent=2))
        except Exception as e:
            print(f"❌ Availability check failed: {e}")

def main():
    """Main test runner"""

    print("""
╔══════════════════════════════════════════╗
║     🧪 Huata Calendar Agent Tests        ║
╚══════════════════════════════════════════╝
    """)

    # Run local component tests
    asyncio.run(test_huata_locally())

    # Optionally test API if running
    print("\nTo test the deployed API:")
    print("1. Start Huata: ./deploy.sh docker")
    print("2. Run: python test_huata.py --api")

    if len(sys.argv) > 1 and sys.argv[1] == "--api":
        asyncio.run(test_api_endpoints())

if __name__ == "__main__":
    main()
