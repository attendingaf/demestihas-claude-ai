"""
AI-powered classification using actual LLMs for understanding.

This replaces the keyword-based classification with real intelligence.
"""

from typing import Dict, Any
import os
import json
from workflow.state import LycoGraphState

# Try multiple AI providers
try:
    from anthropic import Anthropic
    anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
except:
    anthropic_client = None

try:
    from openai import OpenAI
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except:
    openai_client = None


async def classify_with_ai(state: LycoGraphState) -> Dict[str, Any]:
    """
    Use actual AI to understand and classify tasks properly.
    """
    
    task = state.get("raw_input", "")
    user_context = """
    User: Mene Demestihas
    Role: CMO-level physician executive
    Context: Managing healthcare consulting firm, family of 5
    Priorities: Strategic initiatives, client deliverables, family coordination
    """
    
    classification_prompt = f"""
    Classify this task for a CMO-level executive:
    Task: {task}
    
    {user_context}
    
    Return JSON with:
    - urgency: 1-5 (5=do today, 1=can wait months)
    - importance: 1-5 (5=critical for role/family, 1=nice to have)
    - quadrant: DO_FIRST, SCHEDULE, DELEGATE, or ELIMINATE
    - energy_level: high, medium, or low
    - reasoning: Brief explanation
    
    Consider:
    - Quarterly reports are IMPORTANT for executives
    - Board/client items are DO_FIRST or SCHEDULE
    - Family items are usually SCHEDULE unless urgent
    - Admin tasks can be DELEGATE
    - Only truly useless tasks are ELIMINATE
    
    Return ONLY valid JSON.
    """
    
    try:
        # Try Anthropic first
        if anthropic_client:
            response = anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=300,
                temperature=0.3,
                system="You are a task classification expert. Always return valid JSON.",
                messages=[{"role": "user", "content": classification_prompt}]
            )
            
            # Extract JSON from response
            text = response.content[0].text
            # Clean up the response to get just JSON
            if "{" in text and "}" in text:
                json_str = text[text.index("{"):text.rindex("}")+1]
                result = json.loads(json_str)
                
                return {
                    "urgency": result.get("urgency", 3),
                    "importance": result.get("importance", 3),
                    "quadrant": result.get("quadrant", "SCHEDULE"),
                    "energy_level": result.get("energy_level", "medium"),
                    "priority_score": (result.get("importance", 3) * 2 + result.get("urgency", 3)) / 3,
                    "confidence_score": 0.95,
                    "model_used": "claude-3-haiku",
                    "action_reason": result.get("reasoning", "AI classified based on executive context")
                }
        
        # Try OpenAI as fallback
        if openai_client:
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a task classification expert. Always return valid JSON."},
                    {"role": "user", "content": classification_prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            text = response.choices[0].message.content
            if "{" in text and "}" in text:
                json_str = text[text.index("{"):text.rindex("}")+1]
                result = json.loads(json_str)
                
                return {
                    "urgency": result.get("urgency", 3),
                    "importance": result.get("importance", 3),
                    "quadrant": result.get("quadrant", "SCHEDULE"),
                    "energy_level": result.get("energy_level", "medium"),
                    "priority_score": (result.get("importance", 3) * 2 + result.get("urgency", 3)) / 3,
                    "confidence_score": 0.90,
                    "model_used": "gpt-3.5-turbo",
                    "action_reason": result.get("reasoning", "AI classified based on executive context")
                }
                
    except Exception as e:
        print(f"AI classification error: {e}")
    
    # If AI fails, at least use better defaults for executives
    task_lower = task.lower()
    
    # Executive-appropriate defaults
    if any(word in task_lower for word in ["report", "quarterly", "board", "client", "review", "analysis"]):
        return {
            "urgency": 3,
            "importance": 4,
            "quadrant": "SCHEDULE",
            "energy_level": "high",
            "priority_score": 3.67,
            "confidence_score": 0.5,
            "model_used": "executive_defaults",
            "action_reason": "Executive task - defaulting to SCHEDULE"
        }
    
    # Fallback
    return state
