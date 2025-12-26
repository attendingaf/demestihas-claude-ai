"""
Main LangChain Agent for intelligent task management.
Combines model routing, tool usage, and ADHD-optimized decision making.
"""

import logging
import json
import asyncio
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import redis

from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain.memory import ConversationBufferWindowMemory
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import SystemMessage, HumanMessage
from langchain.callbacks import AsyncCallbackHandler
from langchain.tools import BaseTool

from bot.agents.core.model_router import ModelRouter, TaskComplexity
from bot.tools.notion_tools import create_notion_tools

logger = logging.getLogger(__name__)

class TimingCallback(AsyncCallbackHandler):
    """Track timing and tokens for model routing metrics"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.total_tokens_in = 0
        self.total_tokens_out = 0
    
    async def on_llm_start(self, *args, **kwargs):
        self.start_time = datetime.now()
    
    async def on_llm_end(self, *args, **kwargs):
        self.end_time = datetime.now()
    
    async def on_llm_new_token(self, token: str, **kwargs):
        self.total_tokens_out += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        if self.start_time and self.end_time:
            duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        else:
            duration_ms = 0
        
        return {
            "duration_ms": duration_ms,
            "tokens_in": self.total_tokens_in,
            "tokens_out": self.total_tokens_out
        }

class LycoIntelligentAgent:
    """
    Main intelligent agent that orchestrates task management with ADHD optimization.
    Uses LangChain for tool orchestration and intelligent decision making.
    """
    
    SYSTEM_PROMPT = """You are Lycurgus (Lyco), an intelligent ADHD-optimized task management assistant for the Demestihas family.

## Your Purpose
Help Mene (emergency physician with ADHD) and his family manage tasks efficiently using the Eisenhower Matrix methodology.

## Family Context
- **Mene**: Primary user, ER physician with high-functioning ADHD, transitioning to health tech leadership
- **Cindy**: Wife, ER physician with inattentive ADHD, Spanish speaker
- **Viola**: Au pair from Germany, helps with childcare and household
- **Persy**: 11yo, loves reading and weather
- **Stelios**: 8yo, soccer fan (Arsenal), competitive player
- **Franci**: 5yo, loves singing and dancing

## Task Categorization Rules

### Eisenhower Matrix:
- **🔥 Do Now**: Urgent + Important (deadlines <24hrs, health/safety, emergencies)
- **📅 Schedule**: Important but not urgent (goals, routines, relationships)
- **👥 Delegate**: Urgent but not important (can be done by others)
- **🗄️ Someday/Maybe**: Neither urgent nor important (nice to have)
- **🧠 Brain Dump**: Default for unclear priority (needs processing)

### Context Tags (can be multiple):
- **Quick Win**: Tasks under 15 minutes that provide dopamine boost
- **Deep Work**: Requires focus and concentration
- **Errand**: Shopping, pickups, physical locations
- **Call/Email**: Communication tasks
- **Family**: Kid activities, family coordination
- **Household**: Home maintenance, chores
- **Appointment**: Scheduled meetings, medical visits

### Energy Levels:
- **Low**: Can be done when tired (errands, simple tasks)
- **Medium**: Standard focus required
- **High**: Requires peak mental energy (complex decisions, creative work)

### Time Estimates:
- **⚡ Quick (<15m)**: Single action items
- **📝 Short (15-30m)**: Focused task blocks
- **🎯 Deep (>30m)**: Significant work sessions
- **📅 Multi-hour**: Projects or multiple related tasks

## ADHD Optimization Strategies
1. Break complex requests into multiple smaller tasks
2. Add clear action verbs (Call, Email, Buy, Schedule)
3. Consider energy matching - schedule high-energy tasks for morning
4. Protect against hyperfocus with time estimates
5. Use "Quick Win" tags liberally for dopamine rewards

## Family Task Assignment
- **Viola**: Childcare, school pickups, household support, grocery runs
- **Cindy**: Medical decisions, family planning, shared household
- **Kids**: Age-appropriate chores and self-care tasks
- **Mene**: Default for work, financial, and complex decisions

## Important Rules
1. ALWAYS check for existing similar tasks before creating new ones
2. Extract ALL tasks from a message (there may be multiple)
3. Be specific with task names - include context
4. Default to "🧠 Brain Dump" if priority is unclear
5. Add helpful notes for context and success criteria

You have access to tools for creating, searching, and updating tasks in Notion.
Always confirm what actions you've taken in a friendly, conversational way."""
    
    def __init__(
        self,
        anthropic_api_key: str,
        notion_token: str,
        notion_database_id: str,
        redis_client: redis.Redis,
        test_mode: bool = False
    ):
        self.redis = redis_client
        self.test_mode = test_mode
        
        # Initialize model router for cost optimization
        self.model_router = ModelRouter(redis_client)
        if test_mode:
            self.model_router.set_test_mode(True)
        
        # Create Notion tools
        self.tools = create_notion_tools(
            notion_token=notion_token,
            database_id=notion_database_id,
            test_mode=test_mode
        )
        
        # Initialize both models
        self.haiku_model = ChatAnthropic(
            anthropic_api_key=anthropic_api_key,
            model="claude-3-haiku-20240307",
            temperature=0.3,
            max_tokens=2000
        )
        
        self.sonnet_model = ChatAnthropic(
            anthropic_api_key=anthropic_api_key,
            model="claude-3-5-sonnet-20241022",
            temperature=0.3,
            max_tokens=2000
        )
        
        # Create prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # Initialize agents for both models
        self.haiku_agent = None
        self.sonnet_agent = None
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize LangChain agents for both models"""
        # Create Haiku agent
        self.haiku_agent = create_structured_chat_agent(
            llm=self.haiku_model,
            tools=self.tools,
            prompt=self.prompt
        )
        
        # Create Sonnet agent
        self.sonnet_agent = create_structured_chat_agent(
            llm=self.sonnet_model,
            tools=self.tools,
            prompt=self.prompt
        )
    
    def _analyze_message_context(self, message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze message to determine routing context"""
        message_lower = message.lower()
        context = {
            "multiple_tasks": False,
            "requires_search": False,
            "cross_family_coordination": False,
            "user_role": user_context.get("role", "parent")
        }
        
        # Check for multiple tasks
        task_indicators = ["and", "also", "plus", "then", "after", "before"]
        task_count = sum(1 for indicator in task_indicators if indicator in message_lower)
        context["multiple_tasks"] = task_count >= 2
        
        # Check if search might be needed
        search_indicators = ["did i", "have i", "already", "existing", "previous"]
        context["requires_search"] = any(ind in message_lower for ind in search_indicators)
        
        # Check for family coordination
        family_members = ["viola", "cindy", "persy", "stelios", "franci", "everyone", "family"]
        family_count = sum(1 for member in family_members if member in message_lower)
        context["cross_family_coordination"] = family_count >= 2
        
        return context
    
    def _get_conversation_memory(self, user_id: str) -> ConversationBufferWindowMemory:
        """Get or create conversation memory for user"""
        memory_key = f"lyco:memory:{user_id}"
        
        # Try to load existing memory from Redis
        stored_memory = self.redis.get(memory_key)
        
        memory = ConversationBufferWindowMemory(
            memory_key="chat_history",
            return_messages=True,
            k=10  # Keep last 10 exchanges
        )
        
        if stored_memory:
            try:
                messages = json.loads(stored_memory)
                for msg in messages:
                    if msg["type"] == "human":
                        memory.chat_memory.add_user_message(msg["content"])
                    else:
                        memory.chat_memory.add_ai_message(msg["content"])
            except Exception as e:
                logger.error(f"Error loading memory: {e}")
        
        return memory
    
    def _save_conversation_memory(self, user_id: str, memory: ConversationBufferWindowMemory):
        """Save conversation memory to Redis"""
        memory_key = f"lyco:memory:{user_id}"
        
        # Extract messages
        messages = []
        for message in memory.chat_memory.messages:
            messages.append({
                "type": message.type,
                "content": message.content
            })
        
        # Store in Redis with 24 hour expiry
        self.redis.setex(
            memory_key,
            24 * 3600,
            json.dumps(messages)
        )
    
    async def process_message(
        self,
        message: str,
        user_id: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """Process a message using the intelligent agent"""
        if not user_context:
            user_context = {"role": "parent", "name": "Mene"}
        
        try:
            # Analyze message complexity
            message_context = self._analyze_message_context(message, user_context)
            complexity = self.model_router.analyze_complexity(message, message_context)
            
            # Decide which model to use
            use_sonnet = self.model_router.should_use_sonnet(complexity)
            model_name = "sonnet" if use_sonnet else "haiku"
            
            logger.info(
                f"Processing message with {model_name} model. "
                f"Complexity: {complexity.value}, Context: {message_context}"
            )
            
            # Get conversation memory
            memory = self._get_conversation_memory(user_id)
            
            # Select appropriate agent
            agent = self.sonnet_agent if use_sonnet else self.haiku_agent
            
            # Create executor with memory
            executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                memory=memory,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=3
            )
            
            # Track timing
            callback = TimingCallback()
            
            # Run the agent
            start_time = datetime.now()
            result = await executor.ainvoke(
                {"input": message},
                callbacks=[callback]
            )
            end_time = datetime.now()
            
            # Calculate metrics
            duration_ms = (end_time - start_time).total_seconds() * 1000
            metrics = callback.get_metrics()
            
            # Record usage for cost tracking
            self.model_router.record_usage(
                model=model_name,
                complexity=complexity.value,
                tokens_in=metrics.get("tokens_in", 100),  # Estimate if not available
                tokens_out=metrics.get("tokens_out", 200),
                response_time_ms=duration_ms,
                task_type="task_management",
                success=True
            )
            
            # Save updated memory
            self._save_conversation_memory(user_id, memory)
            
            # Prepare metadata
            metadata = {
                "model_used": model_name,
                "complexity": complexity.value,
                "duration_ms": duration_ms,
                "tokens": metrics,
                "test_mode": self.test_mode
            }
            
            return result["output"], metadata
        
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            
            # Record failure
            self.model_router.record_usage(
                model="haiku",
                complexity="error",
                tokens_in=len(message.split()),
                tokens_out=50,
                response_time_ms=0,
                task_type="error",
                success=False
            )
            
            error_response = (
                "I encountered an error processing your request. "
                "Could you please try rephrasing it or breaking it into smaller parts?"
            )
            
            return error_response, {"error": str(e), "test_mode": self.test_mode}
    
    def get_usage_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get model usage statistics"""
        return self.model_router.get_usage_stats(days)
    
    def update_routing_config(self, **kwargs):
        """Update model routing configuration"""
        self.model_router.update_config(**kwargs)
    
    def set_test_mode(self, enabled: bool):
        """Enable/disable test mode"""
        self.test_mode = enabled
        self.model_router.set_test_mode(enabled)
        
        # Recreate tools with new test mode setting
        self.tools = create_notion_tools(
            notion_token=os.getenv("NOTION_TOKEN"),
            database_id=os.getenv("NOTION_DATABASE_ID"),
            test_mode=enabled
        )
        
        # Reinitialize agents with new tools
        self._initialize_agents()
