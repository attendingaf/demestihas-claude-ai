#!/usr/bin/env python3
"""
Lyco Intelligent Bot - Simple Version
"""

import os
import json
import logging
import asyncio
from typing import Dict, Tuple
from datetime import datetime
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SimpleTaskProcessor:
    def __init__(self, test_mode=True):
        self.test_mode = test_mode
        
        import anthropic
        from notion_client import Client
        
        self.anthropic = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        self.notion = Client(auth=os.getenv("NOTION_TOKEN"))
        self.notion_db_id = os.getenv("NOTION_DATABASE_ID")
    
    def process_message(self, message: str) -> Tuple[str, Dict]:
        prompt = f"""You are Lycurgus, an ADHD task management assistant.

Extract tasks from this message and return JSON:
{message}

Return JSON with this structure:
{{
    "tasks": [
        {{
            "name": "task description",
            "eisenhower": "🔥 Do Now" or "📅 Schedule" or "👥 Delegate" or "🗄️ Someday/Maybe" or "🧠 Brain Dump",
            "energy": "Low" or "Medium" or "High",
            "time": "⚡ Quick (<15m)" or "📝 Short (15-30m)" or "🎯 Deep (>30m)" or "📅 Multi-hour",
            "tags": ["Quick Win", "Errand", etc],
            "assigned": "mene" or "cindy" or "viola" or null,
            "notes": "any additional context"
        }}
    ],
    "response": "Natural language response to user"
}}

Rules:
- Extract ALL tasks from the message
- Default eisenhower is "🧠 Brain Dump"
- Default energy is "Low"
- Default time is "⚡ Quick (<15m)"
- Be specific in task names
- Family: Mene (user), Cindy (wife), Viola (au pair), kids: Persy, Stelios, Franci
"""

        try:
            start_time = datetime.now()
            response = self.anthropic.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1000,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            content = response.content[0].text
            
            # Extract JSON
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = {
                    "tasks": [{
                        "name": message,
                        "eisenhower": "🧠 Brain Dump",
                        "energy": "Low",
                        "time": "⚡ Quick (<15m)",
                        "tags": [],
                        "assigned": "mene",
                        "notes": ""
                    }],
                    "response": "I've captured your task."
                }
            
            # Create tasks
            created_tasks = []
            for task in data.get("tasks", []):
                if self.test_mode:
                    logger.info(f"TEST MODE - Would create: {task['name']}")
                    created_tasks.append(task['name'])
                else:
                    self._create_notion_task(task)
                    created_tasks.append(task['name'])
            
            response_text = data.get("response", f"Created {len(created_tasks)} task(s)")
            if self.test_mode:
                response_text = f"[TEST MODE] {response_text}"
            
            return response_text, {
                "tasks_created": len(created_tasks),
                "duration_ms": duration_ms,
                "tasks": created_tasks
            }
            
        except Exception as e:
            logger.error(f"Error: {e}")
            return "Error processing message.", {"error": str(e)}
    
    def _create_notion_task(self, task: Dict):
        try:
            properties = {
                "Name": {"title": [{"text": {"content": task["name"]}}]},
                "Eisenhower": {"select": {"name": task.get("eisenhower", "🧠 Brain Dump")}},
                "Energy Level Required": {"select": {"name": task.get("energy", "Low")}},
                "Time Estimate": {"select": {"name": task.get("time", "⚡ Quick (<15m)")}},
                "Source": {"select": {"name": "Telegram"}},
                "Complete": {"checkbox": False}
            }
            
            if task.get("tags"):
                properties["Context/Tags"] = {
                    "multi_select": [{"name": tag} for tag in task["tags"]]
                }
            
            if task.get("notes"):
                properties["Notes"] = {
                    "rich_text": [{"text": {"content": task["notes"]}}]
                }
            
            self.notion.pages.create(
                parent={"database_id": self.notion_db_id},
                properties=properties
            )
        except Exception as e:
            logger.error(f"Notion error: {e}")

# Test function
if __name__ == "__main__":
    print("Testing processor...")
    processor = SimpleTaskProcessor(test_mode=True)
    
    test_messages = [
        "Buy milk",
        "Schedule dentist next week",
        "Have Viola pick up kids at 3pm"
    ]
    
    for msg in test_messages:
        print(f"\nMessage: {msg}")
        response, meta = processor.process_message(msg)
        print(f"Response: {response}")
        print(f"Tasks: {meta.get('tasks_created', 0)}")
        print(f"Time: {meta.get('duration_ms', 0):.0f}ms")
