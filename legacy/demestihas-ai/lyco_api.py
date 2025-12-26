#!/usr/bin/env python3
"""
Lyco Task API - Pure task management functionality
Extracted from monolithic bot.py for clean separation of concerns
"""

import os
import asyncio
import logging
import json
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from anthropic import AsyncAnthropic

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
NOTION_TOKEN = os.environ.get('NOTION_TOKEN', '')
NOTION_DATABASE_ID = os.environ.get('NOTION_DATABASE_ID', '245413ec-f376-80f6-ac4b-c0e3bdd449c6')
NOTION_VERSION = '2022-06-28'

class LycoTaskAPI:
    """Pure task management API"""
    
    def __init__(self):
        self.anthropic = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    
    def parse_relative_date(self, date_text: str) -> str:
        """Parse relative date strings to ISO format"""
        if not date_text:
            return None
            
        date_lower = date_text.lower().strip()
        today = datetime.now().date()
        
        # Handle relative dates
        if date_lower in ['today', 'now']:
            return today.strftime('%Y-%m-%d')
        elif date_lower == 'tomorrow':
            return (today + timedelta(days=1)).strftime('%Y-%m-%d')
        elif date_lower == 'yesterday':
            return (today - timedelta(days=1)).strftime('%Y-%m-%d')
        elif 'next week' in date_lower:
            return (today + timedelta(days=7)).strftime('%Y-%m-%d')
        elif 'next month' in date_lower:
            return (today + timedelta(days=30)).strftime('%Y-%m-%d')
        elif date_lower.startswith('in '):
            # Handle in X days format
            try:
                parts = date_lower.split()
                if len(parts) >= 3 and parts[2] in ['days', 'day']:
                    days = int(parts[1])
                    return (today + timedelta(days=days)).strftime('%Y-%m-%d')
            except (ValueError, IndexError):
                pass
        
        # Check if already in ISO format (YYYY-MM-DD)
        try:
            datetime.strptime(date_text, '%Y-%m-%d')
            return date_text
        except ValueError:
            pass
        
        # Default to original if can't parse
        logger.warning(f"Could not parse date: {date_text}, using today's date")
        return today.strftime('%Y-%m-%d')
        
    async def extract_task_from_text(self, text: str, context: str = "") -> Dict:
        """Extract task details from natural language using Claude"""
        
        prompt = f"""Extract task details from this message.
        
{('Context: ' + context) if context else ''}
Message: {text}

Extract:
1. The core task (action item)
2. Eisenhower matrix quadrant (🔥 Do Now, 📅 Schedule, 🤝 Delegate, 🧠 Brain Dump)
3. Energy level required (High, Medium, Low)
4. Time estimate (⚡ Quick (5-15m), 📝 Short (15-30m), 🕐 Medium (30-60m), 📚 Long (1h+))
5. Context tags (e.g., Work, Personal, Health, Finance)
6. Any mentioned due date
7. Any person assigned to

Respond in JSON format:
{{
    "parsed_task": "<clear action item>",
    "eisenhower": "<quadrant>",
    "energy": "<level>",
    "time_estimate": "<estimate>",
    "context": ["<tag1>", "<tag2>"],
    "due_date": "<date if mentioned>",
    "assigned_to": "<person if mentioned>",
    "adhd_notes": "<any ADHD-friendly tips>"
}}"""

        try:
            response = await self.anthropic.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=300,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text
            
            # Parse JSON from response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                task_data = json.loads(json_match.group())
                # Ensure all required fields
                task_data.setdefault('parsed_task', text)
                task_data.setdefault('eisenhower', '🧠 Brain Dump')
                task_data.setdefault('energy', 'Medium')
                task_data.setdefault('time_estimate', '📝 Short (15-30m)')
                task_data.setdefault('context', ['General'])
                task_data.setdefault('due_date', None)
                task_data.setdefault('assigned_to', None)
                task_data.setdefault('adhd_notes', '')
                return task_data
            else:
                raise ValueError("No JSON found in response")
                
        except Exception as e:
            logger.error(f"Task extraction error: {e}")
            # Return default structure
            return {
                'parsed_task': text,
                'eisenhower': '🧠 Brain Dump',
                'energy': 'Medium', 
                'time_estimate': '📝 Short (15-30m)',
                'context': ['General'],
                'due_date': None,
                'assigned_to': None,
                'adhd_notes': 'Auto-categorized due to parsing error'
            }
    
    async def create_task(self, data: Dict) -> Dict:
        """Create a task in Notion"""
        
        # Extract task details from text
        text = data.get('text', '')
        user_name = data.get('user_name', 'User')
        context = data.get('context', '')
        
        task_data = await self.extract_task_from_text(text, context)
        
        # Save to Notion
        success, task_id = await self._save_to_notion(task_data, user_name)
        
        return {
            'success': success,
            'task_id': task_id,
            'task_data': task_data,
            'message': f"Task created: {task_data['parsed_task'][:50]}" if success else "Failed to create task"
        }
    
    async def update_task(self, task_id: Optional[str], updates: Dict) -> Dict:
        """Update an existing task"""
        
        # For now, we'll create a new task with the update
        # In a full implementation, this would find and update the existing task
        text = updates.get('text', '')
        referenced_task = updates.get('referenced_task', '')
        
        # Build update context
        if referenced_task and 'urgent' in text.lower():
            task_data = {
                'parsed_task': referenced_task,
                'eisenhower': '🔥 Do Now',
                'energy': 'High',
                'time_estimate': '⚡ Quick (5-15m)',
                'context': ['Urgent'],
                'due_date': 'Today',
                'assigned_to': None,
                'adhd_notes': 'Marked as urgent based on request'
            }
        else:
            task_data = await self.extract_task_from_text(text, referenced_task)
        
        success, new_task_id = await self._save_to_notion(task_data, updates.get('user_name', 'User'))
        
        return {
            'success': success,
            'task_id': new_task_id,
            'task_data': task_data,
            'message': f"Task updated: {task_data['parsed_task'][:50]}" if success else "Failed to update task"
        }
    
    async def query_tasks(self, filters: Dict) -> Dict:
        """Query tasks from Notion"""
        
        headers = {
            'Authorization': f'Bearer {NOTION_TOKEN}',
            'Content-Type': 'application/json',
            'Notion-Version': NOTION_VERSION
        }
        
        # Build filter
        notion_filter = {}
        if filters.get('eisenhower'):
            notion_filter = {
                'property': 'Eisenhower',
                'select': {'equals': filters['eisenhower']}
            }
        
        query_data = {
            'sorts': [{'timestamp': 'created_time', 'direction': 'descending'}],
            'page_size': 10
        }
        
        # Only add filter if it's not empty
        if notion_filter:
            query_data['filter'] = notion_filter
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query',
                    headers=headers,
                    json=query_data,
                    timeout=10
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        tasks = []
                        for page in result.get('results', [])[:5]:
                            props = page.get('properties', {})
                            name_prop = props.get('Name', {}).get('title', [])
                            task_name = name_prop[0].get('text', {}).get('content', 'Untitled') if name_prop else 'Untitled'
                            tasks.append(task_name)
                        
                        if tasks:
                            task_list = '\n'.join([f"• {task}" for task in tasks])
                            return {
                                'success': True,
                                'tasks': tasks,
                                'message': f"📋 Your recent tasks:\n{task_list}"
                            }
                        else:
                            return {
                                'success': True,
                                'tasks': [],
                                'message': "No tasks found"
                            }
                    else:
                        return {
                            'success': False,
                            'message': f"Failed to query tasks: {response.status}"
                        }
                        
        except Exception as e:
            logger.error(f"Query error: {e}")
            return {
                'success': False,
                'message': f"Error querying tasks: {str(e)[:50]}"
            }
    
    async def _save_to_notion(self, task_data: Dict, user_name: str) -> tuple[bool, str]:
        """Internal method to save task to Notion"""
        
        headers = {
            'Authorization': f'Bearer {NOTION_TOKEN}',
            'Content-Type': 'application/json',
            'Notion-Version': NOTION_VERSION
        }
        
        # Build properties
        properties = {
            'Name': {
                'title': [{
                    'text': {'content': task_data['parsed_task']}
                }]
            },
            'Source': {
                'select': {'name': 'Telegram'}
            },
            'Notes': {
                'rich_text': [{
                    'text': {
                        'content': f"Added by {user_name} via Yanay/Lyco v7\n"
                                  f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                                  f"{task_data.get('adhd_notes', '')}"
                    }
                }]
            },
            'Eisenhower': {
                'select': {'name': task_data['eisenhower']}
            },
            'Energy Level Required': {
                'select': {'name': task_data['energy']}
            },
            'Time Estimate': {
                'select': {'name': task_data['time_estimate']}
            },
            'Context/Tags': {
                'multi_select': [{'name': tag} for tag in task_data.get('context', [])]
            }
        }
        
        # Add due date if present - with proper date parsing
        if task_data.get('due_date'):
            parsed_date = self.parse_relative_date(task_data['due_date'])
            if parsed_date:
                properties['Due Date'] = {
                    'date': {'start': parsed_date}
                }
                logger.info(f"Parsed due date '{task_data['due_date']}' to '{parsed_date}'")
        
        # Prepare request
        notion_data = {
            'parent': {'database_id': NOTION_DATABASE_ID},
            'properties': properties
        }
        
        logger.info(f"Saving to Notion: {task_data['parsed_task'][:50]}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://api.notion.com/v1/pages',
                    headers=headers,
                    json=notion_data,
                    timeout=10
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return True, result['id'][:8]
                    else:
                        error_text = await response.text()
                        logger.error(f"Notion error: {error_text}")
                        return False, f"API error {response.status}"
                        
        except asyncio.TimeoutError:
            return False, "Timeout"
        except Exception as e:
            logger.error(f"Notion save error: {e}")
            return False, str(e)[:50]

# Create global instance for easy import
lyco_api = LycoTaskAPI()

# Export simple functions for compatibility
async def create_task(data: Dict) -> Dict:
    return await lyco_api.create_task(data)

async def update_task(task_id: str, updates: Dict) -> Dict:
    return await lyco_api.update_task(task_id, updates)

async def query_tasks(filters: Dict) -> Dict:
    return await lyco_api.query_tasks(filters)
