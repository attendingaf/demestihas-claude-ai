"""
Learning node for pattern detection and model updates.

Implements adaptive intelligence from v2.
"""

from typing import Dict, Any
import sys
import os
from pathlib import Path
import json
from datetime import datetime

# Add v2 path
lyco_v2_path = Path(__file__).parent.parent.parent.parent / "lyco-v2"
sys.path.insert(0, str(lyco_v2_path))

try:
    from src.adaptive_intelligence import AdaptiveIntelligence
    from src.pattern_learner import PatternLearner
except ImportError:
    AdaptiveIntelligence = None
    PatternLearner = None

from workflow.state import LycoGraphState


async def update_learning_model(state: LycoGraphState) -> Dict[str, Any]:
    """
    Update learning model based on task patterns and outcomes.

    Learns from:
    - Skip patterns
    - Energy mismatches
    - Time-of-day preferences
    - Delegation patterns
    - Success/failure rates
    """

    # Use v2 AdaptiveIntelligence if available
    if AdaptiveIntelligence and os.path.exists(lyco_v2_path / "src"):
        try:
            ai = AdaptiveIntelligence()

            # Prepare learning data
            learning_data = {
                "task_title": state.get("task_title"),
                "task_description": state.get("task_description"),
                "energy_level": state.get("energy_level"),
                "quadrant": state.get("quadrant"),
                "skip_count": state.get("skip_count", 0),
                "skip_reasons": state.get("skip_reasons", []),
                "action_taken": state.get("action"),
                "user_energy": state.get("current_user_energy"),
                "timestamp": state.get("timestamp"),
                "patterns_detected": state.get("patterns_detected", [])
            }

            # Update model
            result = await ai.learn_from_interaction(learning_data)

            return {
                "learning_adjustments": result.get("adjustments", {}),
                "prompt_version": result.get("prompt_version", 1),
                "model_feedback": result.get("feedback"),
                "messages": state.get("messages", []) + [
                    {"role": "system", "content": f"Learning updated: {result.get('summary')}"}
                ]
            }
        except Exception as e:
            pass

    # Fallback learning logic
    patterns = state.get("patterns_detected", [])
    skip_reasons = state.get("skip_reasons", [])
    action = state.get("action")

    # Build learning adjustments
    adjustments = {}
    feedback = []

    # Learn from skip patterns
    if state.get("skip_count", 0) > 3:
        if "too_tired" in skip_reasons:
            adjustments["energy_threshold"] = "increase"
            feedback.append("Adjusting energy requirements based on skip patterns")

        if "needs_cindy" in skip_reasons:
            adjustments["delegation_sensitivity"] = "increase"
            feedback.append("Improving delegation detection")

    # Learn from successful actions
    if action in ["notify", "schedule"] and not state.get("error"):
        adjustments["confidence_boost"] = 0.1
        feedback.append("Successful task routing reinforced")

    # Learn from time patterns
    current_hour = datetime.now().hour
    if action == "park" and 20 <= current_hour:
        adjustments["evening_threshold"] = "lower"
        feedback.append("Adjusting evening task thresholds")

    # Calculate new prompt version (increment if significant changes)
    prompt_version = state.get("prompt_version", 1)
    if len(adjustments) > 2:
        prompt_version += 1

    return {
        "learning_adjustments": adjustments,
        "prompt_version": prompt_version,
        "model_feedback": " | ".join(feedback) if feedback else "No significant patterns",
        "messages": state.get("messages", []) + [
            {"role": "system", "content": f"Learning: {len(adjustments)} adjustments made"}
        ]
    }
