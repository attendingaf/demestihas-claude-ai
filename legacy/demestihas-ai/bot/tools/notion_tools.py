"""
LangChain tools for Notion integration.
These tools are used by the AI agent to intelligently interact with Notion.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from langchain.tools import BaseTool
from langchain.pydantic_v1 import BaseModel, Field
from notion_client import Client
import os

logger = logging.getLogger(__name__)

class NotionTaskInput(BaseModel):
    """Input schema for creating a Notion task"""
    name: str = Field(description="The task title/name")
    eisenhower: Optional[str] = Field(
        default="🧠 Brain Dump",
        description="Priority: 🔥 Do Now, 📅 Schedule, 👥 Delegate, 🗄️ Someday/Maybe, 🧠 Brain Dump"
    )
    context_tags: Optional[List[str]] = Field(
        default=[],
        description="Context tags like: Quick Win, Deep Work, Errand, Call, Email, Family, etc."
    )
    energy_level: Optional[str] = Field(
        default="Low",
        description="Energy required: Low, Medium, or High"
    )
    time_estimate: Optional[str] = Field(
        default="⚡ Quick (<15m)",
        description="Time needed: ⚡ Quick (<15m), 📝 Short (15-30m), 🎯 Deep (>30m), 📅 Multi-hour"
    )
    due_date: Optional[str] = Field(
        default=None,
        description="Due date in YYYY-MM-DD format"
    )
    assigned_to: Optional[str] = Field(
        default=None,
        description="Person to assign: mene, cindy, viola, persy, stelios, franci"
    )
    notes: Optional[str] = Field(
        default="",
        description="Additional notes or details"
    )
    source: Optional[str] = Field(
        default="Telegram",
        description="Source of the task"
    )

class CreateNotionTaskTool(BaseTool):
    """Tool for creating tasks in Notion with ADHD-optimized categorization"""
    
    name = "create_notion_task"
    description = """Create a new task in Notion. Use this when the user wants to add a task.
    Automatically categorizes using Eisenhower Matrix and ADHD-friendly properties.
    Can assign to family members: mene, cindy, viola (au pair), persy (11yo), stelios (8yo), franci (5yo)."""
    args_schema = NotionTaskInput
    
    def __init__(self, notion_client: Client, database_id: str, test_mode: bool = False):
        super().__init__()
        self.notion = notion_client
        self.database_id = database_id
        self.test_mode = test_mode
        
        # Family member mapping to Notion user IDs
        self.family_mapping = {
            "mene": "22fd872b-594c-81ba-a126-000278a2f41f",
            "cindy": None,  # Add Cindy's Notion ID when available
            "viola": None,  # Add Viola's Notion ID when available
            "persy": None,  # Kids might not have Notion accounts
            "stelios": None,
            "franci": None
        }
    
    def _run(self, **kwargs) -> str:
        """Create a task in Notion"""
        try:
            # Build properties for Notion page
            properties = {
                "Name": {
                    "title": [{
                        "text": {"content": kwargs.get("name", "New Task")}
                    }]
                },
                "Eisenhower": {
                    "select": {"name": kwargs.get("eisenhower", "🧠 Brain Dump")}
                },
                "Energy Level Required": {
                    "select": {"name": kwargs.get("energy_level", "Low")}
                },
                "Time Estimate": {
                    "select": {"name": kwargs.get("time_estimate", "⚡ Quick (<15m)")}
                },
                "Source": {
                    "select": {"name": kwargs.get("source", "Telegram")}
                },
                "Complete": {
                    "checkbox": False
                }
            }
            
            # Add context tags if provided
            if kwargs.get("context_tags"):
                properties["Context/Tags"] = {
                    "multi_select": [
                        {"name": tag} for tag in kwargs["context_tags"]
                    ]
                }
            
            # Add due date if provided
            if kwargs.get("due_date"):
                properties["Due Date"] = {
                    "date": {"start": kwargs["due_date"]}
                }
            
            # Add notes if provided
            if kwargs.get("notes"):
                properties["Notes"] = {
                    "rich_text": [{
                        "text": {"content": kwargs["notes"]}
                    }]
                }
            
            # Add assigned person if provided and has Notion ID
            assigned_to = kwargs.get("assigned_to")
            if assigned_to and self.family_mapping.get(assigned_to):
                notion_user_id = self.family_mapping[assigned_to]
                if notion_user_id:
                    properties["Assigned To"] = {
                        "people": [{"id": notion_user_id}]
                    }
            
            # Create the page in test mode or real mode
            if self.test_mode:
                logger.info(f"TEST MODE - Would create task: {json.dumps(properties, indent=2)}")
                return f"✅ TEST MODE: Task '{kwargs.get('name')}' would be created with priority {kwargs.get('eisenhower')}"
            else:
                response = self.notion.pages.create(
                    parent={"database_id": self.database_id},
                    properties=properties
                )
                
                task_url = response.get("url", "")
                logger.info(f"Created Notion task: {kwargs.get('name')} - {task_url}")
                
                return f"✅ Created task: '{kwargs.get('name')}' with {kwargs.get('eisenhower')} priority. Assigned to: {assigned_to or 'Mene'}"
        
        except Exception as e:
            logger.error(f"Error creating Notion task: {e}")
            return f"❌ Failed to create task: {str(e)}"
    
    async def _arun(self, **kwargs) -> str:
        """Async version of _run"""
        return self._run(**kwargs)

class SearchNotionTasksInput(BaseModel):
    """Input schema for searching Notion tasks"""
    query: Optional[str] = Field(default=None, description="Search query for task name")
    eisenhower: Optional[str] = Field(default=None, description="Filter by Eisenhower quadrant")
    assigned_to: Optional[str] = Field(default=None, description="Filter by assigned person")
    is_complete: Optional[bool] = Field(default=None, description="Filter by completion status")
    limit: int = Field(default=5, description="Maximum number of results")

class SearchNotionTasksTool(BaseTool):
    """Tool for searching existing tasks in Notion"""
    
    name = "search_notion_tasks"
    description = """Search for existing tasks in Notion. Use this to check if a task already exists
    or to find tasks by various criteria like priority, assignment, or completion status."""
    args_schema = SearchNotionTasksInput
    
    def __init__(self, notion_client: Client, database_id: str):
        super().__init__()
        self.notion = notion_client
        self.database_id = database_id
    
    def _run(self, **kwargs) -> str:
        """Search for tasks in Notion"""
        try:
            # Build filter
            filter_conditions = []
            
            if kwargs.get("query"):
                filter_conditions.append({
                    "property": "Name",
                    "title": {"contains": kwargs["query"]}
                })
            
            if kwargs.get("eisenhower"):
                filter_conditions.append({
                    "property": "Eisenhower",
                    "select": {"equals": kwargs["eisenhower"]}
                })
            
            if kwargs.get("is_complete") is not None:
                filter_conditions.append({
                    "property": "Complete",
                    "checkbox": {"equals": kwargs["is_complete"]}
                })
            
            # Build request
            request = {
                "database_id": self.database_id,
                "page_size": kwargs.get("limit", 5)
            }
            
            if filter_conditions:
                if len(filter_conditions) == 1:
                    request["filter"] = filter_conditions[0]
                else:
                    request["filter"] = {"and": filter_conditions}
            
            # Query Notion
            response = self.notion.databases.query(**request)
            
            # Format results
            tasks = []
            for page in response.get("results", []):
                props = page["properties"]
                task = {
                    "name": props["Name"]["title"][0]["text"]["content"] if props["Name"]["title"] else "Untitled",
                    "eisenhower": props["Eisenhower"]["select"]["name"] if props["Eisenhower"]["select"] else None,
                    "complete": props["Complete"]["checkbox"],
                    "url": page["url"]
                }
                tasks.append(task)
            
            if not tasks:
                return "No tasks found matching your criteria."
            
            # Format response
            response_text = f"Found {len(tasks)} task(s):\n"
            for i, task in enumerate(tasks, 1):
                status = "✅" if task["complete"] else "⏳"
                response_text += f"{i}. {status} {task['name']} [{task['eisenhower']}]\n"
            
            return response_text
        
        except Exception as e:
            logger.error(f"Error searching Notion tasks: {e}")
            return f"❌ Failed to search tasks: {str(e)}"
    
    async def _arun(self, **kwargs) -> str:
        """Async version of _run"""
        return self._run(**kwargs)

class UpdateNotionTaskInput(BaseModel):
    """Input schema for updating a Notion task"""
    task_id: str = Field(description="The Notion page ID of the task to update")
    complete: Optional[bool] = Field(default=None, description="Mark task as complete/incomplete")
    eisenhower: Optional[str] = Field(default=None, description="Update priority")
    notes: Optional[str] = Field(default=None, description="Update or append to notes")

class UpdateNotionTaskTool(BaseTool):
    """Tool for updating existing tasks in Notion"""
    
    name = "update_notion_task"
    description = """Update an existing task in Notion. Can mark as complete, change priority, or update notes."""
    args_schema = UpdateNotionTaskInput
    
    def __init__(self, notion_client: Client):
        super().__init__()
        self.notion = notion_client
    
    def _run(self, **kwargs) -> str:
        """Update a task in Notion"""
        try:
            properties = {}
            
            if kwargs.get("complete") is not None:
                properties["Complete"] = {"checkbox": kwargs["complete"]}
                if kwargs["complete"]:
                    properties["Completed Date"] = {
                        "date": {"start": datetime.now().strftime("%Y-%m-%d")}
                    }
            
            if kwargs.get("eisenhower"):
                properties["Eisenhower"] = {
                    "select": {"name": kwargs["eisenhower"]}
                }
            
            if kwargs.get("notes"):
                properties["Notes"] = {
                    "rich_text": [{
                        "text": {"content": kwargs["notes"]}
                    }]
                }
            
            response = self.notion.pages.update(
                page_id=kwargs["task_id"],
                properties=properties
            )
            
            return "✅ Task updated successfully"
        
        except Exception as e:
            logger.error(f"Error updating Notion task: {e}")
            return f"❌ Failed to update task: {str(e)}"
    
    async def _arun(self, **kwargs) -> str:
        """Async version of _run"""
        return self._run(**kwargs)

def create_notion_tools(
    notion_token: str,
    database_id: str,
    test_mode: bool = False
) -> List[BaseTool]:
    """
    Create all Notion tools for the agent.
    
    Args:
        notion_token: Notion integration token
        database_id: Notion database ID for tasks
        test_mode: If True, don't actually create tasks
    
    Returns:
        List of configured Notion tools
    """
    notion_client = Client(auth=notion_token)
    
    return [
        CreateNotionTaskTool(notion_client, database_id, test_mode),
        SearchNotionTasksTool(notion_client, database_id),
        UpdateNotionTaskTool(notion_client)
    ]
