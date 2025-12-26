#!/usr/bin/env python3
"""
Lyco Eisenhower Matrix Agent
Simple task management using Eisenhower Matrix for family use
Optimized for ADHD-friendly interaction patterns
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import re

import anthropic
from notion_client import Client
import redis

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    CANCELLED = "cancelled"


class Quadrant(Enum):
    DO_FIRST = 1  # Urgent + Important
    SCHEDULE = 2  # Important + Not Urgent
    DELEGATE = 3  # Urgent + Not Important
    DONT_DO = 4   # Not Urgent + Not Important


@dataclass
class Task:
    """Task object for Eisenhower Matrix"""
    title: str
    description: str = ""
    urgency: int = 3  # 1-5 scale
    importance: int = 3  # 1-5 scale
    due_date: Optional[str] = None
    assigned_to: str = "both"  # mene, cindy, both
    status: TaskStatus = TaskStatus.NEW
    context_tags: List[str] = None
    created_at: str = None
    updated_at: str = None
    notion_id: Optional[str] = None
    
    def __post_init__(self):
        if self.context_tags is None:
            self.context_tags = []
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()
    
    @property
    def quadrant(self) -> Quadrant:
        """Determine Eisenhower quadrant based on urgency and importance"""
        if self.urgency >= 4 and self.importance >= 4:
            return Quadrant.DO_FIRST
        elif self.urgency < 4 and self.importance >= 4:
            return Quadrant.SCHEDULE
        elif self.urgency >= 4 and self.importance < 4:
            return Quadrant.DELEGATE
        else:
            return Quadrant.DONT_DO
    
    @property
    def is_due_today(self) -> bool:
        """Check if task is due today"""
        if not self.due_date:
            return False
        try:
            due = datetime.fromisoformat(self.due_date).date()
            return due == datetime.now().date()
        except:
            return False
    
    @property
    def is_due_this_week(self) -> bool:
        """Check if task is due this week"""
        if not self.due_date:
            return False
        try:
            due = datetime.fromisoformat(self.due_date).date()
            today = datetime.now().date()
            week_end = today + timedelta(days=(6 - today.weekday()))
            return today <= due <= week_end
        except:
            return False


class LycoEisenhowerAgent:
    """Simple Eisenhower Matrix task management agent"""
    
    def __init__(self):
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.notion_api_key = os.getenv("NOTION_API_KEY")
        self.notion_database_id = os.getenv("NOTION_TASKS_DATABASE_ID")
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", 6379))
        
        # Initialize clients
        self.claude = anthropic.Client(api_key=self.anthropic_api_key) if self.anthropic_api_key else None
        self.notion = Client(auth=self.notion_api_key) if self.notion_api_key else None
        
        try:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                decode_responses=True
            )
            self.redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Running without cache.")
            self.redis_client = None
    
    def parse_task_from_message(self, message: str, user: str = "both") -> Optional[Task]:
        """Parse natural language message into Task object using Claude Haiku"""
        if not self.claude:
            return self._fallback_parse(message, user)
        
        try:
            prompt = f"""Extract task information from this message. Return ONLY valid JSON.

Message: "{message}"
User: {user}

Extract and return JSON with these fields:
{{
    "title": "brief task title",
    "description": "optional details",
    "urgency": 1-5 (1=not urgent, 5=very urgent),
    "importance": 1-5 (1=not important, 5=very important),
    "due_date": "ISO date if mentioned (YYYY-MM-DD)",
    "assigned_to": "{user}" or "both" if not specified,
    "context_tags": ["work", "personal", "family", "medical", etc]
}}

Consider deadlines for urgency. Consider impact for importance.
If unclear, use urgency=3, importance=3."""

            response = self.claude.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=300,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            
            task_data = json.loads(response.content[0].text)
            return Task(
                title=task_data.get("title", message[:50]),
                description=task_data.get("description", ""),
                urgency=task_data.get("urgency", 3),
                importance=task_data.get("importance", 3),
                due_date=task_data.get("due_date"),
                assigned_to=task_data.get("assigned_to", user),
                context_tags=task_data.get("context_tags", [])
            )
        except Exception as e:
            logger.error(f"Claude parsing failed: {e}")
            return self._fallback_parse(message, user)
    
    def _fallback_parse(self, message: str, user: str) -> Task:
        """Simple regex-based fallback parser"""
        title = message[:100].strip()
        urgency = 4 if any(word in message.lower() for word in ["urgent", "asap", "today", "now"]) else 3
        importance = 4 if any(word in message.lower() for word in ["important", "critical", "priority"]) else 3
        
        # Extract due date
        due_date = None
        date_patterns = [
            r"due (\w+)",
            r"by (\w+)",
            r"before (\w+)",
            r"(\w+day)",  # Monday, Tuesday, etc
            r"(tomorrow|today)"
        ]
        for pattern in date_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                due_date = self._parse_date_string(date_str)
                break
        
        # Detect context
        context_tags = []
        if any(word in message.lower() for word in ["work", "meeting", "project", "office"]):
            context_tags.append("work")
        if any(word in message.lower() for word in ["family", "kids", "home", "soccer", "school"]):
            context_tags.append("family")
        if any(word in message.lower() for word in ["doctor", "appointment", "medical", "prescription"]):
            context_tags.append("medical")
        if not context_tags:
            context_tags.append("personal")
        
        return Task(
            title=title,
            urgency=urgency,
            importance=importance,
            due_date=due_date,
            assigned_to=user,
            context_tags=context_tags
        )
    
    def _parse_date_string(self, date_str: str) -> Optional[str]:
        """Convert natural language date to ISO format"""
        date_str = date_str.lower()
        today = datetime.now()
        
        if date_str == "today":
            return today.date().isoformat()
        elif date_str == "tomorrow":
            return (today + timedelta(days=1)).date().isoformat()
        elif "monday" in date_str:
            days_ahead = (0 - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            return (today + timedelta(days=days_ahead)).date().isoformat()
        elif "friday" in date_str:
            days_ahead = (4 - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            return (today + timedelta(days=days_ahead)).date().isoformat()
        
        return None
    
    def save_task_to_notion(self, task: Task) -> bool:
        """Save task to Notion database"""
        if not self.notion or not self.notion_database_id:
            logger.warning("Notion not configured")
            return False
        
        try:
            properties = {
                "Title": {"title": [{"text": {"content": task.title}}]},
                "Status": {"select": {"name": task.status.value}},
                "Urgency": {"number": task.urgency},
                "Importance": {"number": task.importance},
                "Assigned To": {"select": {"name": task.assigned_to.title()}},
                "Quadrant": {"select": {"name": f"Q{task.quadrant.value}"}},
            }
            
            if task.description:
                properties["Description"] = {"rich_text": [{"text": {"content": task.description}}]}
            
            if task.due_date:
                properties["Due Date"] = {"date": {"start": task.due_date}}
            
            if task.context_tags:
                properties["Tags"] = {"multi_select": [{"name": tag} for tag in task.context_tags]}
            
            response = self.notion.pages.create(
                parent={"database_id": self.notion_database_id},
                properties=properties
            )
            
            task.notion_id = response["id"]
            
            # Cache in Redis
            if self.redis_client:
                self.redis_client.setex(
                    f"task:{task.notion_id}",
                    3600,  # 1 hour TTL
                    json.dumps(asdict(task))
                )
            
            return True
        except Exception as e:
            logger.error(f"Failed to save to Notion: {e}")
            return False
    
    def get_tasks_by_quadrant(self, user: Optional[str] = None) -> Dict[Quadrant, List[Task]]:
        """Get all tasks organized by quadrant"""
        tasks = self._fetch_all_tasks(user)
        
        quadrants = {q: [] for q in Quadrant}
        for task in tasks:
            if task.status != TaskStatus.COMPLETE:
                quadrants[task.quadrant].append(task)
        
        # Sort by urgency and importance within each quadrant
        for q in quadrants:
            quadrants[q].sort(key=lambda t: (t.urgency * t.importance), reverse=True)
        
        return quadrants
    
    def get_today_tasks(self, user: Optional[str] = None) -> List[Task]:
        """Get tasks for today (due today or in Q1)"""
        tasks = self._fetch_all_tasks(user)
        
        today_tasks = []
        for task in tasks:
            if task.status != TaskStatus.COMPLETE:
                if task.is_due_today or task.quadrant == Quadrant.DO_FIRST:
                    today_tasks.append(task)
        
        today_tasks.sort(key=lambda t: (t.urgency * t.importance), reverse=True)
        return today_tasks
    
    def get_week_tasks(self, user: Optional[str] = None) -> List[Task]:
        """Get tasks for this week"""
        tasks = self._fetch_all_tasks(user)
        
        week_tasks = []
        for task in tasks:
            if task.status != TaskStatus.COMPLETE:
                if task.is_due_this_week or task.quadrant in [Quadrant.DO_FIRST, Quadrant.SCHEDULE]:
                    week_tasks.append(task)
        
        week_tasks.sort(key=lambda t: (t.urgency * t.importance), reverse=True)
        return week_tasks
    
    def _fetch_all_tasks(self, user: Optional[str] = None) -> List[Task]:
        """Fetch all tasks from Notion"""
        if not self.notion or not self.notion_database_id:
            return []
        
        try:
            filter_params = {"property": "Status", "select": {"does_not_equal": "complete"}}
            
            if user and user != "both":
                filter_params = {
                    "and": [
                        filter_params,
                        {
                            "or": [
                                {"property": "Assigned To", "select": {"equals": user.title()}},
                                {"property": "Assigned To", "select": {"equals": "Both"}}
                            ]
                        }
                    ]
                }
            
            response = self.notion.databases.query(
                database_id=self.notion_database_id,
                filter=filter_params
            )
            
            tasks = []
            for page in response["results"]:
                try:
                    props = page["properties"]
                    task = Task(
                        title=props["Title"]["title"][0]["text"]["content"],
                        description=props.get("Description", {}).get("rich_text", [{}])[0].get("text", {}).get("content", ""),
                        urgency=props.get("Urgency", {}).get("number", 3),
                        importance=props.get("Importance", {}).get("number", 3),
                        due_date=props.get("Due Date", {}).get("date", {}).get("start"),
                        assigned_to=props.get("Assigned To", {}).get("select", {}).get("name", "both").lower(),
                        status=TaskStatus(props.get("Status", {}).get("select", {}).get("name", "new")),
                        context_tags=[tag["name"] for tag in props.get("Tags", {}).get("multi_select", [])],
                        notion_id=page["id"]
                    )
                    tasks.append(task)
                except Exception as e:
                    logger.warning(f"Failed to parse task: {e}")
                    continue
            
            return tasks
        except Exception as e:
            logger.error(f"Failed to fetch from Notion: {e}")
            return []
    
    def complete_task(self, task_id: str) -> bool:
        """Mark a task as complete"""
        if not self.notion:
            return False
        
        try:
            self.notion.pages.update(
                page_id=task_id,
                properties={
                    "Status": {"select": {"name": "complete"}}
                }
            )
            
            if self.redis_client:
                self.redis_client.delete(f"task:{task_id}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to complete task: {e}")
            return False
    
    def format_matrix_display(self, quadrants: Dict[Quadrant, List[Task]]) -> str:
        """Format Eisenhower Matrix for display"""
        output = "📊 **Eisenhower Matrix**\n\n"
        
        quadrant_info = {
            Quadrant.DO_FIRST: ("🔴 DO FIRST", "Urgent & Important"),
            Quadrant.SCHEDULE: ("🟡 SCHEDULE", "Important, Not Urgent"),
            Quadrant.DELEGATE: ("🟢 DELEGATE", "Urgent, Not Important"),
            Quadrant.DONT_DO: ("⚪ DON'T DO", "Not Urgent, Not Important")
        }
        
        for quadrant, tasks in quadrants.items():
            emoji, description = quadrant_info[quadrant]
            output += f"{emoji} - {description}\n"
            
            if tasks:
                for task in tasks[:5]:  # Show top 5 per quadrant
                    assignee = f"({task.assigned_to[0].upper()})" if task.assigned_to != "both" else ""
                    due = f" 📅{task.due_date}" if task.due_date else ""
                    output += f"  • {task.title} {assignee}{due}\n"
            else:
                output += "  _No tasks_\n"
            output += "\n"
        
        return output
    
    def format_task_list(self, tasks: List[Task], title: str) -> str:
        """Format a list of tasks for display"""
        if not tasks:
            return f"**{title}**\n_No tasks_"
        
        output = f"**{title}**\n\n"
        for i, task in enumerate(tasks[:10], 1):
            quadrant_emoji = ["🔴", "🟡", "🟢", "⚪"][task.quadrant.value - 1]
            assignee = f"({task.assigned_to[0].upper()})" if task.assigned_to != "both" else ""
            due = f" 📅{task.due_date}" if task.due_date else ""
            output += f"{i}. {quadrant_emoji} {task.title} {assignee}{due}\n"
        
        return output
    
    def handle_message(self, message: str, user: str = "mene") -> str:
        """Main message handler for Telegram bot integration"""
        message_lower = message.lower().strip()
        
        # Task addition
        if message_lower.startswith(("add task:", "add:", "task:")):
            task_text = message.split(":", 1)[1].strip()
            task = self.parse_task_from_message(task_text, user)
            if task and self.save_task_to_notion(task):
                quadrant_name = ["Do First!", "Schedule", "Delegate", "Maybe skip"][task.quadrant.value - 1]
                return f"✅ Added: {task.title}\n📊 Quadrant: {quadrant_name}"
            return "❌ Failed to add task"
        
        # View today's tasks
        elif any(phrase in message_lower for phrase in ["today", "to-do list", "todo list", "what's urgent"]):
            tasks = self.get_today_tasks(user)
            return self.format_task_list(tasks, "📅 Today's Tasks")
        
        # View week's tasks
        elif any(phrase in message_lower for phrase in ["week", "weekly review", "this week"]):
            tasks = self.get_week_tasks()
            return self.format_task_list(tasks, "📅 This Week's Tasks")
        
        # View matrix
        elif any(phrase in message_lower for phrase in ["matrix", "eisenhower", "quadrants", "all tasks"]):
            quadrants = self.get_tasks_by_quadrant(user if "my" in message_lower else None)
            return self.format_matrix_display(quadrants)
        
        # Complete task
        elif message_lower.startswith(("complete:", "done:", "mark done:")):
            # This would need task selection UI in real implementation
            return "Please specify which task to complete"
        
        # Help
        elif "help" in message_lower:
            return self._get_help_text()
        
        # Default: try to parse as new task
        else:
            task = self.parse_task_from_message(message, user)
            if task and self.save_task_to_notion(task):
                quadrant_name = ["Do First!", "Schedule", "Delegate", "Maybe skip"][task.quadrant.value - 1]
                return f"✅ Added: {task.title}\n📊 Quadrant: {quadrant_name}"
            return "I didn't understand. Try:\n• Add task: [description]\n• Show today\n• Show matrix\n• Help"
    
    def _get_help_text(self) -> str:
        """Return help text for users"""
        return """🤖 **Lyco Task Manager**

**Add Tasks:**
• Add task: [description]
• Just type any task naturally

**View Tasks:**
• Show today / What's my to-do list?
• Show this week / Weekly review
• Show matrix / All tasks

**Examples:**
• "Add task: Schedule Persy's soccer registration due Friday"
• "Review insurance documents - urgent"
• "What's urgent and important for today?"

**Tips:**
• Include "urgent" or "important" for better sorting
• Mention due dates (today, tomorrow, Friday)
• Tasks go to the right quadrant automatically"""


if __name__ == "__main__":
    # Test the agent locally
    agent = LycoEisenhowerAgent()
    
    # Test task parsing
    test_messages = [
        "Schedule Persy's soccer registration due Friday",
        "Review insurance documents urgent",
        "Pick up prescription tomorrow",
        "Plan Q2 strategy meeting important but not urgent"
    ]
    
    for msg in test_messages:
        task = agent.parse_task_from_message(msg, "mene")
        if task:
            print(f"Parsed: {task.title} -> Q{task.quadrant.value}")