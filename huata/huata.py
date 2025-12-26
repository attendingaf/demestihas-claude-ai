# Huata Calendar Agent - LLM-Powered Natural Language Calendar Assistant
# Implementation for Demestihas Family AI System
# Date: August 27, 2025

import asyncio
import json
import os
import redis.asyncio as redis
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from anthropic import AsyncAnthropic

# Try to import OAuth version first, fall back to service account if needed
try:
    from calendar_tools_oauth import GoogleCalendarOAuth
    print("✅ Using OAuth authentication for calendar access")
    USING_OAUTH = True
except ImportError:
    print("⚠️  OAuth module not found, falling back to service account")
    from calendar_tools import GoogleCalendarAPI
    USING_OAUTH = False

from calendar_intents import CalendarIntentClassifier
from calendar_prompts import CalendarPrompts

class HuataCalendarAgent:
    """
    Huata - Family Calendar Intelligence Agent

    Handles natural language calendar queries using Claude Haiku for intelligence.
    No pattern matching - pure LLM understanding for queries like:
    - "Am I free Thursday afternoon?"
    - "Schedule 90 minutes with the Consilium team next week"
    - "Find time for deep work this week"
    """

    def __init__(self, anthropic_api_key: str, redis_host: str = None, redis_port: int = None):
        """Initialize Huata with LLM and calendar integrations"""
        self.llm = AsyncAnthropic(api_key=anthropic_api_key)
        
        # Use environment variables for Redis if not specified
        redis_host = redis_host or os.environ.get('REDIS_HOST', 'localhost')
        redis_port = redis_port or int(os.environ.get('REDIS_PORT', 6379))
        
        try:
            self.redis = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        except Exception as e:
            print(f"⚠️ Redis connection failed: {e} (optional for caching)")
            self.redis = None

        # Calendar tools and processors
        # Use OAuth if available, otherwise fall back to service account
        if USING_OAUTH:
            self.gcal = GoogleCalendarOAuth()  # OAuth authentication
        else:
            # Use the correct Docker path for credentials
            self.gcal = GoogleCalendarAPI(credentials_path='/app/credentials/huata-service-account.json')

        self.intent_classifier = CalendarIntentClassifier(self.llm)
        self.prompts = CalendarPrompts()

        # Family context for intelligent scheduling
        self.family_context = {
            "mene": {
                "calendar_id": "primary",
                "work_hours": "9-17",
                "timezone": "America/New_York"
            },
            "cindy": {
                "calendar_id": "cindy@demestihas.com",
                "shift_pattern": "variable",
                "timezone": "America/New_York"
            },
            "persy": {
                "calendar_id": "family",
                "school_hours": "8-15",
                "timezone": "America/New_York"
            },
            "viola": {
                "source": "nina_agent",
                "schedule_type": "au_pair",
                "timezone": "America/New_York"
            }
        }

    async def process_query(self, query: str, user_context: dict) -> str:
        """
        Main entry point for calendar queries.
        Uses LLM intelligence to understand and respond to natural language.

        Args:
            query: Natural language calendar query
            user_context: User info (name, timezone, etc.)

        Returns:
            Natural language response about calendar
        """
        try:
            # Step 1: LLM understands intent and extracts parameters
            intent_result = await self.intent_classifier.classify_intent(query, user_context)

            # Step 2: Execute calendar operation based on classified intent
            calendar_result = await self.execute_calendar_action(
                intent_result['intent'],
                intent_result['parameters'],
                user_context
            )

            # Step 3: LLM generates natural, family-friendly response
            response = await self.generate_response(query, calendar_result, user_context)

            # Log successful interaction for family debugging
            await self.log_interaction(query, intent_result, calendar_result, user_context)

            return response

        except Exception as e:
            # Family-friendly error handling
            error_msg = f"I had trouble understanding your calendar request. Could you try rephrasing? (Error: {str(e)[:50]})"
            await self.log_error(query, str(e), user_context)
            return error_msg

    async def execute_calendar_action(self, intent: str, params: dict, user_context: dict) -> dict:
        """Execute the calendar operation based on classified intent"""

        try:
            if intent == "check_availability":
                return await self.check_availability(params, user_context)

            elif intent == "schedule_event":
                return await self.schedule_event(params, user_context)

            elif intent == "list_events":
                return await self.list_events(params, user_context)

            elif intent == "find_time_slot":
                return await self.find_time_slot(params, user_context)

            elif intent == "check_conflicts":
                return await self.check_conflicts(params, user_context)

            elif intent == "block_time":
                return await self.block_time(params, user_context)

            elif intent == "modify_event":
                return await self.modify_event(params, user_context)

            elif intent == "event_details":
                return await self.get_event_details(params, user_context)

            else:
                return {
                    "success": False,
                    "error": f"Unknown calendar intent: {intent}",
                    "suggestion": "Try asking about your availability or schedule"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "intent": intent,
                "params": params
            }

    async def check_availability(self, params: dict, user_context: dict) -> dict:
        """Check if user is free at specified times"""
        try:
            calendar_id = self.get_user_calendar(user_context.get('user', 'mene'))
            time_range = params.get('time_range', {})

            if not time_range.get('start') or not time_range.get('end'):
                return {
                    "success": False,
                    "error": "Need specific time range to check availability"
                }

            # Get events in the specified time range
            events = await self.gcal.get_events(
                calendar_id=calendar_id,
                time_min=time_range['start'],
                time_max=time_range['end']
            )

            # Analyze availability gaps
            busy_periods = []
            for event in events:
                if event.get('start') and event.get('end'):
                    busy_periods.append({
                        'start': event['start']['dateTime'],
                        'end': event['end']['dateTime'],
                        'title': event.get('summary', 'Busy')
                    })

            return {
                "success": True,
                "time_range": time_range,
                "busy_periods": busy_periods,
                "total_events": len(events),
                "is_free": len(busy_periods) == 0
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Could not check availability: {str(e)}"
            }

    async def find_time_slot(self, params: dict, user_context: dict) -> dict:
        """Find available time slots for specified duration"""
        try:
            duration_minutes = params.get('duration_minutes', 60)
            preferred_times = params.get('preferred_times', ['morning', 'afternoon'])
            participants = params.get('participants', [user_context.get('user', 'mene')])

            # For now, return mock data - full implementation needs calendar free/busy
            suggested_slots = [
                {
                    'start': '2024-08-29T10:00:00',
                    'end': '2024-08-29T11:30:00',
                    'duration_minutes': duration_minutes,
                    'confidence': 'high'
                },
                {
                    'start': '2024-08-30T14:00:00',
                    'end': '2024-08-30T15:30:00',
                    'duration_minutes': duration_minutes,
                    'confidence': 'medium'
                }
            ]

            return {
                "success": True,
                "requested_duration": duration_minutes,
                "participants": participants,
                "suggested_slots": suggested_slots,
                "search_criteria": params
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Could not find time slots: {str(e)}"
            }

    async def schedule_event(self, params: dict, user_context: dict) -> dict:
        """Create a new calendar event"""
        try:
            calendar_id = self.get_user_calendar(user_context.get('user', 'mene'))

            event_data = {
                'summary': params.get('title', 'New Event'),
                'description': params.get('description', ''),
                'start': {
                    'dateTime': params.get('start_time'),
                    'timeZone': user_context.get('timezone', 'America/New_York')
                },
                'end': {
                    'dateTime': params.get('end_time'),
                    'timeZone': user_context.get('timezone', 'America/New_York')
                }
            }

            # Add location if provided
            if params.get('location'):
                event_data['location'] = params['location']

            # Add attendees if provided
            if params.get('attendees'):
                event_data['attendees'] = [
                    {'email': attendee} for attendee in params['attendees']
                ]

            # Create the event
            created_event = await self.gcal.create_event(calendar_id, event_data)

            return {
                "success": True,
                "event_id": created_event.get('id'),
                "event_link": created_event.get('htmlLink'),
                "created_event": created_event,
                "message": f"Created event: {event_data['summary']}"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Could not create event: {str(e)}"
            }

    async def list_events(self, params: dict, user_context: dict) -> dict:
        """List events for specified time period"""
        try:
            calendar_id = self.get_user_calendar(user_context.get('user', 'mene'))

            # Default to today if no time range specified
            if not params.get('time_range'):
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                tomorrow = today + timedelta(days=1)
                time_range = {
                    'start': today.isoformat(),
                    'end': tomorrow.isoformat()
                }
            else:
                time_range = params['time_range']

            events = await self.gcal.get_events(
                calendar_id=calendar_id,
                time_min=time_range['start'],
                time_max=time_range['end'],
                max_results=params.get('limit', 10)
            )

            # Format events for family-friendly display
            formatted_events = []
            for event in events:
                formatted_events.append({
                    'title': event.get('summary', 'Untitled Event'),
                    'start': event.get('start', {}).get('dateTime', ''),
                    'end': event.get('end', {}).get('dateTime', ''),
                    'location': event.get('location', ''),
                    'description': event.get('description', ''),
                    'event_id': event.get('id', '')
                })

            return {
                "success": True,
                "events": formatted_events,
                "time_range": time_range,
                "total_count": len(formatted_events)
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Could not list events: {str(e)}"
            }

    async def check_conflicts(self, params: dict, user_context: dict) -> dict:
        """Check for scheduling conflicts across multiple calendars"""
        try:
            calendars = params.get('calendars', [user_context.get('user', 'mene')])
            time_range = params.get('time_range', {})

            conflicts = []
            for calendar_user in calendars:
                calendar_id = self.get_user_calendar(calendar_user)
                events = await self.gcal.get_events(
                    calendar_id=calendar_id,
                    time_min=time_range['start'],
                    time_max=time_range['end']
                )

                for event in events:
                    conflicts.append({
                        'calendar_user': calendar_user,
                        'event': event.get('summary', 'Busy'),
                        'start': event.get('start', {}).get('dateTime', ''),
                        'end': event.get('end', {}).get('dateTime', '')
                    })

            return {
                "success": True,
                "conflicts": conflicts,
                "has_conflicts": len(conflicts) > 0,
                "checked_calendars": calendars
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Could not check conflicts: {str(e)}"
            }

    async def block_time(self, params: dict, user_context: dict) -> dict:
        """Block time for tasks or deep work"""
        try:
            # Create a calendar event that blocks time
            event_params = {
                'title': f"🚫 {params.get('purpose', 'Blocked Time')}",
                'description': params.get('description', 'Time blocked via Huata'),
                'start_time': params.get('start_time'),
                'end_time': params.get('end_time'),
                'location': params.get('location', 'Focus time')
            }

            result = await self.schedule_event(event_params, user_context)

            if result.get('success'):
                result['message'] = f"Blocked time for: {params.get('purpose', 'focus work')}"

            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"Could not block time: {str(e)}"
            }

    async def modify_event(self, params: dict, user_context: dict) -> dict:
        """Modify existing calendar event"""
        return {
            "success": False,
            "error": "Event modification not yet implemented",
            "suggestion": "Try creating a new event or contact support"
        }

    async def get_event_details(self, params: dict, user_context: dict) -> dict:
        """Get detailed information about a specific event"""
        return {
            "success": False,
            "error": "Event details not yet implemented",
            "suggestion": "Try listing your events to see details"
        }

    def get_user_calendar(self, user: str) -> str:
        """Get the calendar ID for a family member"""
        return self.family_context.get(user, {}).get('calendar_id', 'primary')

    async def generate_response(self, original_query: str, calendar_result: dict, user_context: dict) -> str:
        """Use LLM to generate natural, family-friendly response"""
        try:
            prompt = self.prompts.response_generation_prompt(
                query=original_query,
                result=calendar_result,
                user_context=user_context
            )

            response = await self.llm.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )

            return response.content[0].text.strip()

        except Exception as e:
            # Fallback to structured response if LLM fails
            if calendar_result.get('success'):
                return f"✅ Calendar action completed successfully"
            else:
                return f"❌ {calendar_result.get('error', 'Unknown error occurred')}"

    async def log_interaction(self, query: str, intent_result: dict, calendar_result: dict, user_context: dict):
        """Log successful calendar interactions for family debugging"""
        if not self.redis:
            return  # Skip if Redis not available
            
        try:
            log_key = f"huata:log:{datetime.now().strftime('%Y%m%d')}"
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'user': user_context.get('user', 'unknown'),
                'query': query,
                'intent': intent_result.get('intent'),
                'success': calendar_result.get('success', False),
                'response_time_ms': user_context.get('response_time_ms', 0)
            }

            await self.redis.lpush(log_key, json.dumps(log_entry))
            await self.redis.ltrim(log_key, 0, 99)  # Keep last 100 entries
            await self.redis.expire(log_key, 86400 * 7)  # 7 day TTL

        except Exception:
            # Silent fail - logging shouldn't break the main flow
            pass

    async def log_error(self, query: str, error: str, user_context: dict):
        """Log calendar errors for debugging"""
        if not self.redis:
            return  # Skip if Redis not available
            
        try:
            error_key = f"huata:errors:{datetime.now().strftime('%Y%m%d')}"
            error_entry = {
                'timestamp': datetime.now().isoformat(),
                'user': user_context.get('user', 'unknown'),
                'query': query,
                'error': error
            }

            await self.redis.lpush(error_key, json.dumps(error_entry))
            await self.redis.ltrim(error_key, 0, 50)  # Keep last 50 errors
            await self.redis.expire(error_key, 86400 * 7)  # 7 day TTL

        except Exception:
            # Silent fail - error logging shouldn't break anything
            pass

# Utility function for easy integration with Yanay orchestrator
async def create_huata_agent(anthropic_api_key: str, redis_host: str = 'localhost') -> HuataCalendarAgent:
    """Factory function to create configured Huata agent"""
    return HuataCalendarAgent(
        anthropic_api_key=anthropic_api_key,
        redis_host=redis_host,
        redis_port=6379
    )
