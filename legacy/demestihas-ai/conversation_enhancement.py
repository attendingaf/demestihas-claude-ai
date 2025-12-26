#!/usr/bin/env python3
"""
Conversation Enhancement Module for Yanay
Adds Opus conversational capabilities with intelligent override
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

# Configuration
ANTHROPIC_OPUS_KEY = os.environ.get("ANTHROPIC_OPUS_KEY", os.environ.get("ANTHROPIC_API_KEY", ""))
DAILY_TOKEN_LIMIT = float(os.environ.get("DAILY_TOKEN_LIMIT", "15.0"))

class ConversationalEnhancement:
    """Adds conversational capabilities to Yanay orchestrator"""
    
    def __init__(self, redis_client=None):
        self.opus = AsyncAnthropic(api_key=ANTHROPIC_OPUS_KEY)
        self.haiku = AsyncAnthropic(api_key=ANTHROPIC_OPUS_KEY)  # Same key
        self.redis = redis_client
        self.daily_limit = DAILY_TOKEN_LIMIT
        
        # Family profiles
        self.family_profiles = {
            "mene": "direct executive style, minimal fluff",
            "cindy": "supportive medical professional, ADHD considerations", 
            "viola": "clear instructions, patient explanations",
            "child": "educational and engaging, age-appropriate"
        }
    
    def identify_user_profile(self, user_name: str) -> str:
        """Identify family member from name"""
        name_lower = (user_name or "").lower()
        if "mene" in name_lower:
            return "mene"
        elif "cindy" in name_lower or "cynthia" in name_lower:
            return "cindy"
        elif "viola" in name_lower:
            return "viola"
        elif any(child in name_lower for child in ["persy", "stelios", "franci"]):
            return "child"
        else:
            return "mene"  # Default
    
    async def should_use_conversation(self, message: str, context: List[Dict]) -> Dict:
        """Intelligent override: decide if message needs conversational response"""
        
        # Build context for evaluation
        context_str = ""
        if context:
            context_str = "\n".join([
                f"{msg.get(role, user)}: {msg.get(content, )[:50]}..."
                for msg in context[-3:]  # Last 3 messages
            ])
        
        prompt = f"""Evaluate if this message needs a conversational response or can be handled by task delegation.

Recent context:
{context_str if context_str else No previous context}

Current message: "{message}"

INTELLIGENT OVERRIDE RULES:
- Default to conversation unless clearly a single-agent task
- Use conversation for: emotional content, educational questions, ambiguous requests, error recovery
- Use delegation only for: clear task creation, specific scheduling, direct commands

Respond with JSON:
{{
    "mode": "conversation|delegation",
    "confidence": 0.8,
    "reasoning": "why this mode was chosen"
}}"""

        try:
            response = await self.haiku.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=150,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text
            if "{" in content and "}" in content:
                start = content.index("{")
                end = content.rindex("}") + 1
                return json.loads(content[start:end])
                
        except Exception as e:
            logger.error(f"Conversation evaluation error: {e}")
        
        # Default to conversation (intelligent override)
        return {"mode": "conversation", "confidence": 0.6, "reasoning": "Default to conversation"}
    
    async def opus_conversation(self, message: str, user_name: str, context: List[Dict]) -> str:
        """Generate conversational response using Opus"""
        
        user_profile = self.identify_user_profile(user_name)
        profile_style = self.family_profiles.get(user_profile, self.family_profiles["mene"])
        
        # Build conversation history
        conversation_history = ""
        if context:
            conversation_history = "Recent conversation:\n"
            for turn in context[-5:]:  # Last 5 turns
                role = turn.get("role", "user")
                content = turn.get("content", "")
                if role == "user":
                    conversation_history += f"User: {content}\n"
                else:
                    conversation_history += f"You: {content}\n"
        
        # Detect emotional/educational needs
        message_lower = message.lower()
        needs_support = any(word in message_lower for word in ["stressed", "worried", "frustrated"])
        is_question = "?" in message and any(word in message_lower for word in ["why", "how", "what"])
        
        prompt = f"""You are Yanay, the intelligent AI orchestrator for the Demestihas family. You have sophisticated conversational abilities and coordinate with specialized agents.

USER: {user_name} ({user_profile})
STYLE: {profile_style}

CONVERSATION CONTEXT:
{conversation_history}

CURRENT MESSAGE: "{message}"

ANALYSIS:
- Emotional support needed: {needs_support}
- Educational opportunity: {is_question}
- Available agents: Nina (scheduling), Huata (calendar), Lyco (tasks)

Respond naturally and conversationally. If emotional content is detected, provide support first. For questions (especially from children), be educational. If you need to delegate to an agent, explain what youre doing and coordinate smoothly.
