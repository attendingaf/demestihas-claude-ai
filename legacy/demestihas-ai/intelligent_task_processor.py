#!/usr/bin/env python3
"""
Simplified intelligent task processor using LangChain and Anthropic.
This can be easily integrated into your existing Telegram bot.
"""

import os
import logging
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class IntelligentTaskProcessor:
    """
    Process natural language task requests using AI.
    """
    
    def __init__(self, anthropic_key: str, notion_token: str, notion_db_id: str, test_mode: bool = True):
        self.test_mode = test_mode
        self.notion_token = notion_token
        self.notion_db_id = notion_db_id
        
        # Import required modules
        try:
            from langchain_anthropic import ChatAnthropic
            from langchain.prompts import ChatPromptTemplate
            from langchain.output_parsers import PydanticOutputParser
            from pydantic import BaseModel, Field
            from typing import List, Optional
            from notion_client import Client
            
            # Store imports
            self.ChatAnthropic = ChatAnthropic
            self.ChatPromptTemplate = ChatPromptTemplate
            self.BaseModel = BaseModel
            self.Field = Field
            self.List = List
            self.Optional = Optional
            self.notion_client = Client(auth=notion_token)
            
        except ImportError as e:
            logger.error(f"Missing required module: {e}")
            raise
        
        # Define the task schema
        class Task(BaseModel):
            name: str = Field(description="Task name/title")
            eisenhower: str = Field(
                default="🧠 Brain Dump",
                description="Priority: 🔥 Do Now, 📅 Schedule, 👥 Delegate, 🗄️ Someday/Maybe, 🧠 Brain Dump"
            )
            context_tags: List[str] = Field(
                default=[],
                description="Tags like: Quick Win, Deep Work, Errand, Call, Email, Family"
            )
            energy_level: str = Field(
                default="Low",
                description="Energy required: Low, Medium, or High"
            )
            time_estimate: str = Field(
                default="⚡ Quick (<15m)",
                description="Time: ⚡ Quick (<15m), 📝 Short (15-30m), 🎯 Deep (>30m), 📅 Multi-hour"
            )
            assigned_to: Optional[str] = Field(
                default="mene",
                description="Person: mene, cindy, viola, persy, stelios, franci"
            )
            notes: Optional[str] = Field(default="", description="Additional notes")
        
        class TaskList(BaseModel):
            tasks: List[Task] = Field(description="List of tasks extracted from the message")
            response: str = Field(description="Natural language response to the user")
        
        self.Task = Task
        self.TaskList = TaskList
        
        # Initialize the LLM
        self.llm = ChatAnthropic(
            anthropic_api_key=anthropic_key,
            model="claude-3-haiku-20240307",  # Start with Haiku for cost
            temperature=0.3,
            max_tokens=2000
        )
        
        # Create parser
        self.parser = PydanticOutputParser(pydantic_object=TaskList)
        
        # Create the prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are Lycurgus, an ADHD-optimized task management assistant.
            
Family Context:
- Mene: Primary user, ER physician with ADHD
- Cindy: Wife, ER physician with ADHD
- Viola: Au pair, helps with childcare
- Persy: 11yo, Stelios: 8yo, Franci: 5yo

Extract ALL tasks from the message and categorize them using:
- Eisenhower: 🔥 Do Now (urgent+important), 📅 Schedule (important), 👥 Delegate, 🗄️ Someday/Maybe, 🧠 Brain Dump (default)
- Energy: Low (errands), Medium (standard), High (complex)
- Time: ⚡ Quick (<15m), 📝 Short (15-30m), 🎯 Deep (>30m), 📅 Multi-hour
- Context: Quick Win, Deep Work, Errand, Call, Email, Family, Household, etc.

{format_instructions}"""),
            ("human", "{message}")
        ])
    
    def process_message(self, message: str) -> Tuple[str, Dict[str, Any]]:
        """
        Process a message and extract tasks.
        Returns: (response_text, metadata)
        """
        try:
            # Format the prompt
            formatted_prompt = self.prompt.format_messages(
                format_instructions=self.parser.get_format_instructions(),
                message=message
            )
            
            # Get LLM response
            start_time = datetime.now()
            response = self.llm.invoke(formatted_prompt)
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Parse the response
            parsed = self.parser.parse(response.content)
            
            # Create tasks in Notion (or test mode)
            created_tasks = []
            for task in parsed.tasks:
                if self.test_mode:
                    logger.info(f"TEST MODE - Would create: {task.name}")
                    created_tasks.append({
                        "name": task.name,
                        "eisenhower": task.eisenhower,
                        "test_mode": True
                    })
                else:
                    # Create in Notion
                    notion_task = self._create_notion_task(task)
                    created_tasks.append(notion_task)
            
            # Prepare metadata
            metadata = {
                "tasks_created": len(created_tasks),
                "duration_ms": duration_ms,
                "test_mode": self.test_mode,
                "tasks": created_tasks
            }
            
            return parsed.response, metadata
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"I had trouble processing that. Could you rephrase?", {"error": str(e)}
    
    def _create_notion_task(self, task) -> Dict[str, Any]:
        """Create a task in Notion"""
        try:
            properties = {
                "Name": {"title": [{"text": {"content": task.name}}]},
                "Eisenhower": {"select": {"name": task.eisenhower}},
                "Energy Level Required": {"select": {"name": task.energy_level}},
                "Time Estimate": {"select": {"name": task.time_estimate}},
                "Source": {"select": {"name": "Telegram"}},
                "Complete": {"checkbox": False}
            }
            
            if task.context_tags:
                properties["Context/Tags"] = {
                    "multi_select": [{"name": tag} for tag in task.context_tags]
                }
            
            if task.notes:
                properties["Notes"] = {
                    "rich_text": [{"text": {"content": task.notes}}]
                }
            
            # Create the page
            response = self.notion_client.pages.create(
                parent={"database_id": self.notion_db_id},
                properties=properties
            )
            
            return {
                "name": task.name,
                "eisenhower": task.eisenhower,
                "url": response.get("url", ""),
                "id": response.get("id", "")
            }
            
        except Exception as e:
            logger.error(f"Error creating Notion task: {e}")
            return {"name": task.name, "error": str(e)}

# Simple test function
def test_processor():
    """Test the processor with sample messages"""
    from dotenv import load_dotenv
    load_dotenv()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize processor
    processor = IntelligentTaskProcessor(
        anthropic_key=os.getenv("ANTHROPIC_API_KEY"),
        notion_token=os.getenv("NOTION_TOKEN"),
        notion_db_id=os.getenv("NOTION_DATABASE_ID"),
        test_mode=True  # Start in test mode
    )
    
    # Test messages
    test_messages = [
        "Buy milk and eggs",
        "Schedule dentist appointment for next week",
        "Have Viola pick up Stelios from soccer at 4pm"
    ]
    
    print("\nTesting Intelligent Task Processor")
    print("=" * 50)
    
    for msg in test_messages:
        print(f"\nMessage: {msg}")
        print("-" * 30)
        response, metadata = processor.process_message(msg)
        print(f"Response: {response}")
        print(f"Tasks: {metadata.get('tasks_created', 0)} created")
        print(f"Time: {metadata.get('duration_ms', 0):.0f}ms")

if __name__ == "__main__":
    test_processor()
