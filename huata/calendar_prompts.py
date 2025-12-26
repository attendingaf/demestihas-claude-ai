# Calendar LLM Prompts for Huata Agent
# Structured prompts for natural language calendar understanding
# Part of Demestihas.ai Calendar Intelligence System

from datetime import datetime
from typing import Dict, List, Any

class CalendarPrompts:
    """
    LLM prompt templates for calendar intelligence.
    
    Designed for Claude Haiku to understand natural language calendar queries
    and generate family-friendly responses.
    """
    
    def __init__(self):
        """Initialize prompt templates"""
        pass
    
    def intent_classification_prompt(self, query: str, current_time: datetime, 
                                   user_context: dict, available_intents: List[str]) -> str:
        """
        Prompt for classifying calendar intent and extracting parameters
        
        Returns structured JSON with intent, confidence, and parameters
        """
        
        family_context = self._build_family_context(user_context)
        time_context = self._build_time_context(current_time)
        
        prompt = f"""You are Huata, the family's intelligent calendar assistant. Parse this calendar query and extract the intent and parameters.

QUERY: "{query}"

CURRENT CONTEXT:
{time_context}
{family_context}

AVAILABLE INTENTS:
{', '.join(available_intents)}

INTENT DEFINITIONS:
- check_availability: Asking if someone is free/busy at specific times
- schedule_event: Creating a new calendar event/meeting 
- list_events: Showing what's on the calendar for a period
- find_time_slot: Finding available time for a specific duration
- check_conflicts: Looking for scheduling conflicts across calendars
- block_time: Reserving time for focused work or tasks
- modify_event: Changing/canceling existing events
- event_details: Getting information about a specific event

PARAMETER EXTRACTION RULES:

Time Expressions (convert to ISO format):
- "tomorrow" → {(current_time + timedelta(days=1)).strftime('%Y-%m-%dT09:00:00')}
- "Thursday afternoon" → next Thursday 13:00-17:00
- "next week" → start of next week
- "2pm" → today at 14:00 
- "morning" → 09:00-12:00
- "afternoon" → 13:00-17:00
- "evening" → 18:00-21:00

Participants (normalize):
- "me", "myself" → {user_context.get('user', 'mene')}
- "Cindy", "Viola", "Persy" → family member names
- Email addresses → keep as-is

Duration (extract from context):
- Look for "30 min", "2 hours", "quick meeting", etc.
- Default to 60 minutes if not specified

RESPONSE FORMAT (valid JSON only):
{{
    "intent": "one_of_available_intents",
    "confidence": 0.0-1.0,
    "parameters": {{
        "time_range": {{
            "start": "YYYY-MM-DDTHH:MM:SS",
            "end": "YYYY-MM-DDTHH:MM:SS"
        }},
        "participants": ["list", "of", "participants"],
        "duration_minutes": 60,
        "title": "event title if scheduling",
        "location": "location if mentioned",
        "description": "additional context",
        "priority": "urgent/normal/low"
    }}
}}

IMPORTANT: Return only valid JSON. No explanations or markdown."""
        
        return prompt
    
    def response_generation_prompt(self, query: str, result: dict, user_context: dict) -> str:
        """
        Prompt for generating natural, family-friendly responses
        """
        
        user_name = user_context.get('user', 'there')
        current_time = datetime.now().strftime('%A, %B %d at %I:%M %p')
        
        prompt = f"""You are Huata, the family's friendly calendar assistant. Generate a natural response about this calendar result.

ORIGINAL QUERY: "{query}"
USER: {user_name}
CURRENT TIME: {current_time}

CALENDAR RESULT:
{self._format_result_for_prompt(result)}

RESPONSE GUIDELINES:
- Be conversational and helpful, like talking to family
- Use specific times in human-friendly format ("2:30pm" not "14:30")  
- Mention specific dates when relevant ("Thursday afternoon", "tomorrow")
- Flag any conflicts or concerns naturally
- Suggest alternatives if something isn't available
- Keep it concise but complete (2-3 sentences max)
- Use emojis sparingly and appropriately (📅 🕐 ✅ ❌)

FAMILY CONTEXT:
- This is a family calendar system for busy parents and kids
- Users want quick, clear answers without technical jargon
- ADHD-friendly: important info first, details second
- Assume follow-up questions are welcome

RESPONSE TONE EXAMPLES:
- Success: "✅ You're free Thursday afternoon except for a dentist appointment at 2:30pm!"
- Conflict: "❌ You've got three meetings that overlap with lunch. Want me to suggest some other times?"  
- Scheduling: "📅 Created your Consilium review for Tuesday 10-11:30am. I've invited the team."
- No availability: "Looks pretty packed! Your first opening is Friday morning at 9am for 90 minutes."

Generate a natural response now:"""
        
        return prompt
    
    def time_parsing_prompt(self, time_expression: str, current_time: datetime, user_context: dict) -> str:
        """
        Specialized prompt for parsing complex time expressions
        """
        
        prompt = f"""Parse this time expression into structured datetime information.

TIME EXPRESSION: "{time_expression}"
CURRENT TIME: {current_time.isoformat()}
USER TIMEZONE: {user_context.get('timezone', 'America/New_York')}

PARSING RULES:
- "tomorrow" = next day at 9am
- "Thursday" = next Thursday at 9am  
- "next week" = Monday of next week at 9am
- "afternoon" = 1pm-5pm range
- "morning" = 9am-12pm range
- "evening" = 6pm-9pm range
- Specific times: "2pm" = 14:00 today, "2:30" = 14:30 today

Return JSON:
{{
    "start": "YYYY-MM-DDTHH:MM:SS",
    "end": "YYYY-MM-DDTHH:MM:SS", 
    "confidence": 0.0-1.0,
    "interpretation": "human description"
}}"""
        
        return prompt
    
    def conflict_analysis_prompt(self, events: List[dict], proposed_time: dict) -> str:
        """
        Prompt for analyzing scheduling conflicts
        """
        
        events_text = "\n".join([
            f"- {event.get('summary', 'Busy')}: {event.get('start', {}).get('human_time', '')} to {event.get('end', {}).get('human_time', '')}"
            for event in events
        ])
        
        prompt = f"""Analyze these calendar events for conflicts with a proposed time slot.

EXISTING EVENTS:
{events_text}

PROPOSED TIME:
Start: {proposed_time.get('start', 'Not specified')}
End: {proposed_time.get('end', 'Not specified')}

ANALYSIS NEEDED:
1. Are there any direct time conflicts?
2. Are there back-to-back meetings that might be problematic?
3. Is there adequate travel/buffer time?
4. Any family scheduling considerations?

Return JSON:
{{
    "has_conflicts": true/false,
    "conflict_details": [
        {{
            "event": "conflicting event name",
            "overlap_minutes": 30,
            "severity": "major/minor"
        }}
    ],
    "recommendations": "suggested alternatives",
    "analysis": "brief explanation for family"
}}"""
        
        return prompt
    
    def scheduling_suggestions_prompt(self, requirements: dict, availability: dict) -> str:
        """
        Prompt for intelligent scheduling suggestions
        """
        
        prompt = f"""Generate intelligent scheduling suggestions based on availability and requirements.

REQUIREMENTS:
Duration: {requirements.get('duration_minutes', 60)} minutes
Participants: {', '.join(requirements.get('participants', ['Unknown']))}
Preferences: {requirements.get('preferences', 'None specified')}
Priority: {requirements.get('priority', 'Normal')}

AVAILABILITY DATA:
{self._format_availability_for_prompt(availability)}

FAMILY SCHEDULING PRINCIPLES:
- Respect school hours for kids (8am-3pm weekdays)
- Avoid family dinner time (6pm-7pm)  
- Consider commute times between locations
- Buffer time between back-to-back meetings
- Prefer mornings for important meetings

Generate 2-3 scheduling options with reasoning:

Return JSON:
{{
    "suggestions": [
        {{
            "start_time": "YYYY-MM-DDTHH:MM:SS",
            "end_time": "YYYY-MM-DDTHH:MM:SS", 
            "confidence": 0.0-1.0,
            "reasoning": "why this time works well",
            "pros": ["advantage 1", "advantage 2"],
            "cons": ["potential issue if any"]
        }}
    ],
    "best_option": 0,
    "family_note": "additional context for family"
}}"""
        
        return prompt
    
    def _build_family_context(self, user_context: dict) -> str:
        """Build family context section for prompts"""
        
        context_lines = [
            f"Current User: {user_context.get('user', 'Unknown')}",
            f"Timezone: {user_context.get('timezone', 'America/New_York')}"
        ]
        
        # Add family member info if available
        if 'family_members' in user_context:
            context_lines.append("Family Members:")
            for member, info in user_context['family_members'].items():
                context_lines.append(f"  - {member}: {info}")
        
        return "\n".join(context_lines)
    
    def _build_time_context(self, current_time: datetime) -> str:
        """Build current time context for prompts"""
        
        return f"""Current Date/Time: {current_time.strftime('%A, %B %d, %Y at %I:%M %p')}
Today: {current_time.strftime('%A')}
This Week: {current_time.strftime('%B %d')} - {(current_time + timedelta(days=6)).strftime('%B %d')}"""
    
    def _format_result_for_prompt(self, result: dict) -> str:
        """Format calendar operation result for response generation"""
        
        if not isinstance(result, dict):
            return str(result)
        
        formatted_lines = []
        
        # Success/failure status
        if 'success' in result:
            formatted_lines.append(f"Success: {result['success']}")
        
        # Error information
        if 'error' in result:
            formatted_lines.append(f"Error: {result['error']}")
        
        # Event information
        if 'events' in result:
            formatted_lines.append(f"Found {len(result['events'])} events")
            for event in result.get('events', [])[:3]:  # Show first 3
                formatted_lines.append(f"  - {event.get('title', 'Untitled')}: {event.get('start', 'No time')}")
        
        # Availability information
        if 'busy_periods' in result:
            formatted_lines.append(f"Busy periods: {len(result['busy_periods'])}")
        
        # Time range information
        if 'time_range' in result:
            time_range = result['time_range']
            formatted_lines.append(f"Time range: {time_range.get('start', '')} to {time_range.get('end', '')}")
        
        return "\n".join(formatted_lines) if formatted_lines else "No specific result data"
    
    def _format_availability_for_prompt(self, availability: dict) -> str:
        """Format availability data for prompt"""
        
        if not availability:
            return "No availability data provided"
        
        formatted = []
        
        if 'free_slots' in availability:
            formatted.append("Available time slots:")
            for slot in availability['free_slots'][:5]:  # Show first 5
                formatted.append(f"  - {slot.get('start', '')} to {slot.get('end', '')} ({slot.get('duration_minutes', 0)} min)")
        
        if 'busy_periods' in availability:
            formatted.append("Busy periods:")
            for busy in availability['busy_periods'][:3]:  # Show first 3
                formatted.append(f"  - {busy.get('title', 'Busy')}: {busy.get('start', '')} to {busy.get('end', '')}")
        
        return "\n".join(formatted) if formatted else "No availability details"

# Helper function for time calculations
from datetime import timedelta

def get_next_weekday(current_date: datetime, target_weekday: int) -> datetime:
    """Get next occurrence of target weekday (0=Monday, 6=Sunday)"""
    days_ahead = target_weekday - current_date.weekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    return current_date + timedelta(days=days_ahead)

# Factory function
def create_calendar_prompts() -> CalendarPrompts:
    """Create configured calendar prompts instance"""
    return CalendarPrompts()