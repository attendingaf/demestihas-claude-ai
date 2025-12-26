# Calendar Intent Classification System
# LLM-powered intent understanding for natural calendar queries
# Part of Huata Calendar Agent

import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from anthropic import AsyncAnthropic
from calendar_prompts import CalendarPrompts

class CalendarIntentClassifier:
    """
    Uses Claude Haiku to understand natural language calendar queries
    and extract structured parameters for calendar operations.
    
    No pattern matching - pure LLM intelligence handles variations like:
    - "Am I free Thursday afternoon?" 
    - "Are you available tomorrow around 2?"
    - "What's my schedule look like next week?"
    """
    
    def __init__(self, anthropic_client: AsyncAnthropic):
        self.llm = anthropic_client
        self.prompts = CalendarPrompts()
        
        # Supported calendar intents - LLM maps natural language to these
        self.calendar_intents = [
            "check_availability",    # Am I free? When can I meet?
            "schedule_event",        # Book a meeting, Schedule appointment
            "list_events",          # What's on my calendar? Show my day
            "find_time_slot",       # Find time for X, When can I do Y?
            "check_conflicts",      # Any conflicts? Double-booked?
            "block_time",          # Block time for, Reserve hours for
            "modify_event",        # Move meeting, Cancel appointment
            "event_details"        # Tell me about X meeting
        ]
    
    async def classify_intent(self, query: str, user_context: dict) -> dict:
        """
        Use LLM to classify calendar intent and extract parameters
        
        Args:
            query: Natural language calendar query
            user_context: User info for context-aware parsing
            
        Returns:
            {
                'intent': 'check_availability',
                'confidence': 0.95,
                'parameters': {
                    'time_range': {...},
                    'participants': [...],
                    'duration_minutes': 60
                }
            }
        """
        try:
            # Build context-aware prompt
            current_time = datetime.now()
            prompt = self.prompts.intent_classification_prompt(
                query=query,
                current_time=current_time,
                user_context=user_context,
                available_intents=self.calendar_intents
            )
            
            # Get LLM classification
            response = await self.llm.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse LLM response as JSON
            classification = json.loads(response.content[0].text.strip())
            
            # Validate and sanitize the classification
            validated = await self.validate_classification(classification, query, user_context)
            
            return validated
            
        except Exception as e:
            # Fallback to basic classification if LLM fails
            return {
                'intent': 'list_events',  # Safe default
                'confidence': 0.1,
                'parameters': {
                    'time_range': self.get_default_time_range(),
                    'error': f"Classification failed: {str(e)}"
                }
            }
    
    async def validate_classification(self, classification: dict, original_query: str, user_context: dict) -> dict:
        """Validate and enhance LLM classification results"""
        
        # Ensure required fields exist
        intent = classification.get('intent', 'list_events')
        confidence = classification.get('confidence', 0.5)
        parameters = classification.get('parameters', {})
        
        # Validate intent is supported
        if intent not in self.calendar_intents:
            intent = 'list_events'  # Safe fallback
            confidence = 0.1
        
        # Validate time expressions are properly formatted
        if 'time_range' in parameters:
            parameters['time_range'] = await self.validate_time_range(
                parameters['time_range'], 
                user_context
            )
        
        # Add default duration for scheduling operations
        if intent in ['schedule_event', 'find_time_slot', 'block_time']:
            if 'duration_minutes' not in parameters:
                parameters['duration_minutes'] = self.extract_duration_from_query(original_query)
        
        # Ensure participant list is properly formatted
        if 'participants' in parameters:
            parameters['participants'] = self.validate_participants(
                parameters['participants'], 
                user_context
            )
        
        return {
            'intent': intent,
            'confidence': confidence,
            'parameters': parameters,
            'original_query': original_query,
            'classification_timestamp': datetime.now().isoformat()
        }
    
    async def validate_time_range(self, time_range: dict, user_context: dict) -> dict:
        """Ensure time range is properly formatted with ISO timestamps"""
        
        try:
            # If LLM provided good ISO timestamps, use them
            if isinstance(time_range.get('start'), str) and isinstance(time_range.get('end'), str):
                # Validate they're parseable
                datetime.fromisoformat(time_range['start'].replace('Z', '+00:00'))
                datetime.fromisoformat(time_range['end'].replace('Z', '+00:00'))
                return time_range
                
        except (ValueError, TypeError):
            pass
        
        # Fallback: provide sensible default based on current time
        now = datetime.now()
        
        # If no specific time mentioned, default to business hours today
        return {
            'start': now.replace(hour=9, minute=0, second=0, microsecond=0).isoformat(),
            'end': now.replace(hour=17, minute=0, second=0, microsecond=0).isoformat(),
            'fallback_used': True
        }
    
    def extract_duration_from_query(self, query: str) -> int:
        """Extract meeting duration from natural language"""
        
        # Simple heuristics - could be enhanced with LLM
        query_lower = query.lower()
        
        if '30 min' in query_lower or 'half hour' in query_lower:
            return 30
        elif '90 min' in query_lower or 'hour and half' in query_lower:
            return 90
        elif '2 hour' in query_lower or 'two hour' in query_lower:
            return 120
        elif 'quick' in query_lower or 'brief' in query_lower:
            return 15
        elif 'long' in query_lower or 'extended' in query_lower:
            return 120
        else:
            return 60  # Default to 1 hour
    
    def validate_participants(self, participants: List[str], user_context: dict) -> List[str]:
        """Validate and normalize participant list"""
        
        if not isinstance(participants, list):
            participants = [str(participants)]
        
        # Map family names to proper identifiers
        family_mapping = {
            'mene': 'mene',
            'cindy': 'cindy', 
            'persy': 'persy',
            'viola': 'viola',
            'me': user_context.get('user', 'mene'),
            'myself': user_context.get('user', 'mene')
        }
        
        normalized = []
        for participant in participants:
            participant_lower = participant.lower().strip()
            if participant_lower in family_mapping:
                normalized.append(family_mapping[participant_lower])
            else:
                # Assume it's an email or external contact
                normalized.append(participant)
        
        # Always include the requesting user
        requesting_user = user_context.get('user', 'mene')
        if requesting_user not in normalized:
            normalized.append(requesting_user)
        
        return normalized
    
    def get_default_time_range(self) -> dict:
        """Get sensible default time range for calendar queries"""
        now = datetime.now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0)
        
        return {
            'start': start_of_day.isoformat(),
            'end': end_of_day.isoformat(),
            'default_range': 'today'
        }

# Helper functions for specific intent patterns
class IntentPatterns:
    """Common patterns for calendar intent classification"""
    
    @staticmethod
    def is_availability_check(query: str) -> bool:
        """Check if query is asking about availability"""
        indicators = [
            'free', 'available', 'busy', 'open',
            'can i', 'am i', 'are you', 'what about'
        ]
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in indicators)
    
    @staticmethod 
    def is_scheduling_request(query: str) -> bool:
        """Check if query is requesting to schedule something"""
        indicators = [
            'schedule', 'book', 'set up', 'arrange', 
            'meeting', 'appointment', 'call', 'dinner'
        ]
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in indicators)
    
    @staticmethod
    def is_list_request(query: str) -> bool:
        """Check if query is asking for event listing"""
        indicators = [
            'what', 'show', 'list', 'today', 'tomorrow',
            'schedule', 'calendar', 'agenda', 'day'
        ]
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in indicators)

# Factory function for easy instantiation
def create_intent_classifier(anthropic_client: AsyncAnthropic) -> CalendarIntentClassifier:
    """Create a configured calendar intent classifier"""
    return CalendarIntentClassifier(anthropic_client)