#!/usr/bin/env python3
"""
Yanay.ai Enhancement Patch - Add this to existing yanay.py
Apply by adding these imports and methods to the existing YanayOrchestrator class
"""

# ============= ADD TO IMPORTS SECTION =============
import os
from anthropic import Anthropic
from conversation_manager import ConversationStateManager
from token_manager import TokenBudgetManager
import asyncio

# ============= ADD TO __init__ METHOD =============
def enhance_init(self):
    """Add these lines to existing __init__"""
    # Multi-model setup
    self.opus_client = Anthropic(api_key=os.getenv('ANTHROPIC_OPUS_KEY', os.getenv('ANTHROPIC_API_KEY')))
    self.haiku_client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    
    # Conversation management
    self.conversation_manager = ConversationStateManager()
    self.token_manager = TokenBudgetManager()
    
    # Family profiles
    self.family_profiles = {
        "mene": {"style": "direct", "focus": "execution"},
        "cindy": {"style": "supportive", "focus": "scheduling"},
        "viola": {"style": "patient", "focus": "coordination"},
        "child": {"style": "educational", "focus": "learning"}
    }

# ============= ADD INTELLIGENT ROUTING METHOD =============
async def evaluate_response_mode(self, message: str, user_id: str, username: str = None):
    """Intelligent override - evaluates best response approach"""
    
    # Get conversation context
    context = self.conversation_manager.get_summary(user_id)
    
    # Quick Haiku evaluation for routing decision
    routing_prompt = f"""
    Evaluate this message for the best response approach.
    
    Message: {message}
    Recent context: {context}
    User: {username or 'unknown'}
    
    Consider:
    1. Emotional content needing support (stress, worry, excitement)
    2. Educational opportunities (why/how questions from children)
    3. Ambiguous intent needing clarification
    4. Complex tasks requiring multiple agents
    5. Simple, direct tasks for single agent
    
    Return a JSON decision:
    {{
        "mode": "conversation|delegation|coordination",
        "confidence": 0.0-1.0,
        "primary_agent": "nina|huata|lyco|none",
        "agents": [],
        "reasoning": "brief explanation"
    }}
    
    Default to "conversation" when uncertain.
    """
    
    try:
        response = self.haiku_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=200,
            messages=[{"role": "user", "content": routing_prompt}]
        )
        
        # Parse response (simple extraction for now)
        decision_text = response.content[0].text
        
        # Simple parsing - in production would use proper JSON parsing
        if "delegation" in decision_text.lower() and any(agent in decision_text.lower() for agent in ["nina", "huata", "lyco"]):
            return {"mode": "delegation", "agent": self._extract_agent(decision_text)}
        elif "coordination" in decision_text.lower():
            return {"mode": "coordination", "agents": self._extract_agents(decision_text)}
        else:
            return {"mode": "conversation"}
            
    except Exception as e:
        print(f"Routing evaluation error: {e}")
        # Default to conversation on error
        return {"mode": "conversation"}

# ============= ADD OPUS CONVERSATION METHOD =============
async def opus_conversation(self, message: str, user_id: str, username: str = None):
    """Handle conversational responses with Opus"""
    
    # Check token budget
    budget_status = self.token_manager.check_budget(user_id)
    
    if not budget_status["allowed"]:
        return f"⚠️ {budget_status['reason']}. Some features may be limited until tomorrow."
    
    # Get conversation history
    conversation_history = self.conversation_manager.get_conversation_context(user_id, max_turns=10)
    
    # Determine user profile
    profile = self._get_user_profile(username)
    
    # Build conversation prompt
    conversation_prompt = f"""
    You are Yanay, the warm and intelligent AI orchestrator for the Demestihas family.
    
    USER PROFILE: {profile}
    
    RECENT CONVERSATION:
    {self._format_conversation_history(conversation_history)}
    
    CURRENT MESSAGE: {message}
    
    AVAILABLE CAPABILITIES:
    - Nina: Scheduling and appointments
    - Huata: Calendar management
    - Lyco: Project and task management
    
    Respond naturally and conversationally. If you identify a clear task that would benefit from a specialized agent, mention you'll handle it and explain briefly.
    
    {budget_status.get('warning', '')}
    """
    
    try:
        # Use Opus or fallback model based on budget
        model = "claude-3-opus-20240229" if budget_status["model"] == "opus" else "claude-3-sonnet-20240229"
        
        response = self.opus_client.messages.create(
            model=model,
            max_tokens=1000,
            messages=[{"role": "user", "content": conversation_prompt}]
        )
        
        response_text = response.content[0].text
        
        # Track token usage
        tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else 1000
        self.token_manager.track_usage(tokens_used, budget_status["model"], user_id)
        
        # Save conversation turn
        self.conversation_manager.add_turn(user_id, message, response_text)
        
        return response_text
        
    except Exception as e:
        print(f"Opus conversation error: {e}")
        return "I'm having a moment of difficulty. Let me try to help you more simply - what's the main thing you need?"

# ============= ADD TO MAIN PROCESS METHOD =============
async def enhanced_process_message(self, message: str, user_id: str, username: str = None):
    """Enhanced message processing with intelligent override"""
    
    # Always evaluate for best approach (intelligent override default)
    decision = await self.evaluate_response_mode(message, user_id, username)
    
    if decision["mode"] == "conversation":
        # Natural conversation with Opus
        response = await self.opus_conversation(message, user_id, username)
        
    elif decision["mode"] == "delegation":
        # Quick task to single agent
        agent = decision.get("agent", "lyco")
        response = await self.delegate_to_agent(agent, message)
        
        # Add conversational wrapper
        response = f"I'll handle that for you right away using {agent.title()}.\n\n{response}"
        
    elif decision["mode"] == "coordination":
        # Complex multi-agent coordination
        agents = decision.get("agents", ["nina", "huata"])
        response = await self.coordinate_agents(agents, message)
        
        # Add narrative explanation
        response = f"This needs coordination across multiple capabilities. Let me orchestrate that for you.\n\n{response}"
        
    else:
        # Fallback to existing behavior
        response = await self.original_process_message(message, user_id)
    
    return response

# ============= HELPER METHODS =============
def _get_user_profile(self, username: str) -> dict:
    """Get family member profile for personalization"""
    username_lower = (username or "").lower()
    
    if "mene" in username_lower:
        return self.family_profiles["mene"]
    elif "cindy" in username_lower:
        return self.family_profiles["cindy"]
    elif "viola" in username_lower:
        return self.family_profiles["viola"]
    elif any(child in username_lower for child in ["persy", "stelios", "franci"]):
        return self.family_profiles["child"]
    else:
        return {"style": "friendly", "focus": "helpful"}

def _format_conversation_history(self, history: list) -> str:
    """Format conversation history for prompt"""
    if not history:
        return "No recent conversation"
    
    formatted = []
    for turn in history[-5:]:  # Last 5 turns
        formatted.append(f"User: {turn['message'][:100]}...")
        formatted.append(f"Yanay: {turn['response'][:100]}...")
    
    return "\n".join(formatted)

def _extract_agent(self, text: str) -> str:
    """Extract agent name from decision text"""
    for agent in ["nina", "huata", "lyco"]:
        if agent in text.lower():
            return agent
    return "lyco"  # default

def _extract_agents(self, text: str) -> list:
    """Extract multiple agent names from decision text"""
    agents = []
    for agent in ["nina", "huata", "lyco"]:
        if agent in text.lower():
            agents.append(agent)
    return agents or ["lyco"]  # default
