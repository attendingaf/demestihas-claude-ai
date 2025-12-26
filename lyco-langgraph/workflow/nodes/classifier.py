"""
Classification nodes for energy levels and Eisenhower Matrix.
Enhanced with actual AI understanding instead of keyword matching.
"""

from typing import Dict, Any
import re
import os
import json
from datetime import datetime, timedelta
from workflow.state import LycoGraphState

# Import AI providers
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


async def determine_energy_level(state: LycoGraphState) -> Dict[str, Any]:
    """
    Classify task energy requirements using AI understanding.
    """
    
    task = state.get("raw_input", "")
    
    # Get current user energy based on time of day
    current_hour = datetime.now().hour
    if 6 <= current_hour < 10:
        current_user_energy = "high"  # Morning fresh
    elif 14 <= current_hour < 16:
        current_user_energy = "low"   # Post-lunch dip
    elif 20 <= current_hour:
        current_user_energy = "low"   # Evening tired
    else:
        current_user_energy = "medium"
    
    # Use AI to determine task energy requirements
    energy_prompt = f"""
    Determine the energy level required for this task:
    "{task}"
    
    Consider:
    - High energy: Strategic thinking, complex analysis, creative work, important reviews
    - Medium energy: Standard meetings, routine decisions, normal work
    - Low energy: Admin tasks, filing, simple responses, routine updates
    
    For a CMO reviewing quarterly reports, that requires HIGH energy (strategic analysis).
    
    Return ONLY: high, medium, or low
    """
    
    energy_level = "medium"  # Default
    
    try:
        if anthropic_client:
            response = anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=10,
                temperature=0.3,
                messages=[{"role": "user", "content": energy_prompt}]
            )
            energy_level = response.content[0].text.strip().lower()
            
        elif openai_client:
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": energy_prompt}],
                temperature=0.3,
                max_tokens=10
            )
            energy_level = response.choices[0].message.content.strip().lower()
    except:
        # Fallback to better heuristics
        task_lower = task.lower()
        if any(word in task_lower for word in ["review", "analyze", "strategic", "plan", "report", "quarterly"]):
            energy_level = "high"
        elif any(word in task_lower for word in ["file", "organize", "update", "remind"]):
            energy_level = "low"
    
    # Ensure valid energy level
    if energy_level not in ["high", "medium", "low"]:
        energy_level = "medium"
    
    # Check for energy mismatch
    energy_mismatch = (energy_level == "high" and current_user_energy == "low")
    
    return {
        "energy_level": energy_level,
        "current_user_energy": current_user_energy,
        "energy_mismatch": energy_mismatch,
        "energy_recommendation": "Schedule for morning when fresh" if energy_mismatch else None
    }


async def apply_eisenhower_matrix(state: LycoGraphState) -> Dict[str, Any]:
    """
    Classify task using Eisenhower Matrix with AI understanding.
    """
    
    task = state.get("raw_input", "")
    
    classification_prompt = f"""
    Classify this task for a CMO-level physician executive:
    "{task}"
    
    Context:
    - Role: CMO at healthcare consulting firm
    - Responsibilities: Strategic planning, client deliverables, team leadership
    - Family: Spouse and 3 children
    
    IMPORTANT: Quarterly reports are ALWAYS important for executives!
    
    Return JSON with these exact fields:
    {{
        "urgency": 1-5 (5=today, 1=months),
        "importance": 1-5 (5=critical, 1=trivial),
        "quadrant": "DO_FIRST" or "SCHEDULE" or "DELEGATE" or "ELIMINATE",
        "reasoning": "One sentence explanation"
    }}
    
    Guidelines:
    - Quarterly/annual reports: importance=5, quadrant=SCHEDULE or DO_FIRST
    - Board/client items: importance=5
    - Strategic planning: importance=4-5
    - Team meetings: importance=3-4
    - Admin tasks: importance=1-2, quadrant=DELEGATE
    - Junk: quadrant=ELIMINATE
    
    Return ONLY valid JSON, no other text.
    """
    
    try:
        if anthropic_client:
            response = anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=200,
                temperature=0.3,
                messages=[{"role": "user", "content": classification_prompt}]
            )
            
            text = response.content[0].text
            # Extract JSON
            if "{" in text and "}" in text:
                json_str = text[text.index("{"):text.rindex("}")+1]
                result = json.loads(json_str)
                
                return {
                    "urgency": result.get("urgency", 3),
                    "importance": result.get("importance", 3),
                    "quadrant": result.get("quadrant", "SCHEDULE"),
                    "priority_score": (result.get("importance", 3) * 2 + result.get("urgency", 3)) / 3,
                    "confidence_score": 0.95,
                    "model_used": "claude-3-haiku",
                    "action_reason": result.get("reasoning", "")
                }
        
        elif openai_client:
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": classification_prompt}],
                temperature=0.3,
                max_tokens=200,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return {
                "urgency": result.get("urgency", 3),
                "importance": result.get("importance", 3),
                "quadrant": result.get("quadrant", "SCHEDULE"),
                "priority_score": (result.get("importance", 3) * 2 + result.get("urgency", 3)) / 3,
                "confidence_score": 0.90,
                "model_used": "gpt-3.5-turbo",
                "action_reason": result.get("reasoning", "")
            }
            
    except Exception as e:
        print(f"AI classification failed: {e}")
    
    # Smart fallback for executive tasks
    task_lower = task.lower()
    
    # Executive report tasks - NEVER eliminate!
    if any(word in task_lower for word in ["quarterly", "annual", "report", "review", "board", "client"]):
        return {
            "urgency": 3,
            "importance": 5,
            "quadrant": "SCHEDULE",
            "priority_score": 4.33,
            "confidence_score": 0.7,
            "model_used": "executive_fallback",
            "action_reason": "Executive reports are always important - schedule appropriately"
        }
    
    # Meeting tasks
    if "meeting" in task_lower or "call" in task_lower:
        return {
            "urgency": 4,
            "importance": 3,
            "quadrant": "SCHEDULE",
            "priority_score": 3.33,
            "confidence_score": 0.6,
            "model_used": "meeting_fallback",
            "action_reason": "Meeting requires scheduling"
        }
    
    # Default fallback - better to schedule than eliminate
    return {
        "urgency": 3,
        "importance": 3,
        "quadrant": "SCHEDULE",
        "priority_score": 3.0,
        "confidence_score": 0.5,
        "model_used": "safe_fallback",
        "action_reason": "Defaulting to SCHEDULE for safety - better than losing tasks"
    }
