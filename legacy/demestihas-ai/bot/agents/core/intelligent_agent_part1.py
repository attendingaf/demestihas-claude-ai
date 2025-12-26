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
