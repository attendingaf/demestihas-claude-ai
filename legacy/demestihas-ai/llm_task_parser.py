import asyncio
import json
import logging
from typing import Dict, Any
from anthropic import Anthropic
from dataclasses import dataclass

@dataclass
class ParsedTask:
    record_type: str
    title: str
    store: str = None
    grocery_category: str = None
    eisenhower_quadrant: str = None
    energy_level: str = None
    time_estimate: str = None
    context_tags: list = None
    assigned_to: str = None
    due_date: str = None
    notes: str = None

class LLMTaskParser:
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self.logger = logging.getLogger(__name__)
    
    def parse(self, text: str) -> ParsedTask:
        """Parse natural language text into structured task data using Claude"""
        try:
            # Create prompt for Claude
            prompt = self._create_parsing_prompt(text)
            
            # Get response from Claude
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse JSON response
            result_json = json.loads(response.content[0].text)
            
            # Create ParsedTask object
            return ParsedTask(
                record_type=result_json.get('record_type', 'Task'),
                title=result_json.get('title', text),
                store=result_json.get('store'),
                grocery_category=result_json.get('grocery_category'),
                eisenhower_quadrant=result_json.get('eisenhower_quadrant', '🧠 Brain Dump'),
                energy_level=result_json.get('energy_level', 'Low'),
                time_estimate=result_json.get('time_estimate', '⚡ Quick (<15m)'),
                context_tags=result_json.get('context_tags', ['Errand']),
                assigned_to=result_json.get('assigned_to', 'mene'),
                due_date=result_json.get('due_date'),
                notes=result_json.get('notes', f'Added by Mene via Lyco v5\nTime: {result_json.get("timestamp", "")}')
            )
            
        except Exception as e:
            self.logger.error(f'LLM parsing failed: {e}')
            # Fallback to simple task
            return ParsedTask(
                record_type='Task',
                title=text,
                eisenhower_quadrant='🧠 Brain Dump',
                energy_level='Low',
                time_estimate='⚡ Quick (<15m)',
                context_tags=['Errand'],
                assigned_to='mene'
            )
    
    def _create_parsing_prompt(self, text: str) -> str:
        return f"""You are an ADHD-optimized task parser for a family management system. Parse this natural language input into structured data.

INPUT: "{text}"

FAMILY CONTEXT:
- Mene: Primary user (ER physician with ADHD)
- Cindy: Wife (ER physician, inattentive ADHD)  
- Persy: 11yo daughter (loves reading, weather)
- Stelios: 8yo son (soccer, Arsenal fan)
- Franci: 5yo daughter (singing, dancing)
- Viola: Au pair from Germany

PARSING RULES:

1. RECORD_TYPE (choose one):
   - "Shopping" for grocery/store items (groceries, buy milk, add eggs to list, etc.)
   - "Task" for general to-dos
   - "Reminder" for time-based alerts
   - "Appointment" for scheduled events

2. STORE (if Shopping):
   - "Groceries" for grocery items
   - "Publix" if specifically mentioned
   - "Target", "Costco", etc. if mentioned
   - null for non-shopping

3. GROCERY_CATEGORY (if grocery item):
   - "Dairy" (milk, eggs, yogurt, cheese)
   - "Produce" (fruits, vegetables)
   - "Meat" (chicken, beef, fish)
   - "Pantry" (canned goods, spices)
   - "Frozen" (frozen foods)
   - "Bakery" (bread, pastries)

4. EISENHOWER_QUADRANT:
   - "🔥 Do Now" (urgent + important)
   - "📅 Schedule" (important, not urgent)
   - "👥 Delegate" (urgent, not important)
   - "🗄️ Someday/Maybe" (neither urgent nor important)
   - "🧠 Brain Dump" (unclear/default)

5. ENERGY_LEVEL:
   - "Low" (simple errands, quick tasks)
   - "Medium" (standard focus needed)
   - "High" (deep work, complex tasks)

6. TIME_ESTIMATE:
   - "⚡ Quick (<15m)" 
   - "🔍 Short (15-30m)"
   - "🎯 Deep (>30m)"
   - "📅 Multi-hour"

7. CONTEXT_TAGS (array):
   - ["Errand"] for shopping/errands
   - ["Family"] for family-related
   - ["Call"] for phone calls
   - ["Email"] for email tasks
   - ["Deep Work"] for focused work
   - ["Quick Win"] for easy tasks

8. ASSIGNED_TO:
   - "mene" (default)
   - "cindy" for wife references
   - "viola" for au pair tasks
   - "persy", "stelios", "franci" for kids

RESPOND WITH ONLY VALID JSON:
{{
  "record_type": "Shopping|Task|Reminder|Appointment",
  "title": "Clear, actionable title",
  "store": "Store name or null",
  "grocery_category": "Category or null",
  "eisenhower_quadrant": "Quadrant with emoji",
  "energy_level": "Low|Medium|High",
  "time_estimate": "Estimate with emoji",
  "context_tags": ["tag1", "tag2"],
  "assigned_to": "family_member",
  "due_date": "YYYY-MM-DD or null",
  "notes": "Additional context",
  "timestamp": "{self._get_timestamp()}"
}}"""
    
    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M')
