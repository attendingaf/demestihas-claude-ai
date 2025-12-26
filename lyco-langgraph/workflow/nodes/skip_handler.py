"""
Skip intelligence nodes for pattern detection and smart handling.

Implements v2's skip intelligence features.
"""

from typing import Dict, Any, List
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add v2 path for skip intelligence
lyco_v2_path = Path(__file__).parent.parent.parent.parent / "lyco-v2"
sys.path.insert(0, str(lyco_v2_path))

try:
    from src.skip_intelligence import SkipIntelligence
    from src.pattern_learner import PatternLearner
except ImportError:
    SkipIntelligence = None
    PatternLearner = None

from workflow.state import LycoGraphState


async def detect_skip_patterns(state: LycoGraphState) -> Dict[str, Any]:
    """
    Detect skip patterns in task history.

    Patterns include:
    - Time-based (always skipped at certain times)
    - Context-based (skipped when certain conditions present)
    - Person-based (tasks involving certain people)
    - Energy-based (high energy tasks when tired)
    """

    # Use v2 PatternLearner if available
    if PatternLearner and os.path.exists(lyco_v2_path / "src"):
        try:
            learner = PatternLearner()
            patterns = await learner.detect_patterns(
                task_title=state.get("task_title", ""),
                task_description=state.get("task_description", ""),
                user_id=state.get("user_id", ""),
                energy_level=state.get("energy_level"),
                quadrant=state.get("quadrant")
            )

            return {
                "patterns_detected": patterns,
                "skip_pattern": patterns[0]["name"] if patterns else None,
                "messages": state.get("messages", []) + [
                    {"role": "system", "content": f"Patterns detected: {len(patterns)}"}
                ]
            }
        except:
            pass

    # Fallback pattern detection
    patterns_detected = []
    skip_pattern = None

    task_title = state.get("task_title", "").lower()
    energy_level = state.get("energy_level")
    current_user_energy = state.get("current_user_energy")
    current_hour = datetime.now().hour

    # Time-based patterns
    if 20 <= current_hour or current_hour < 6:
        if energy_level == "high":
            patterns_detected.append({
                "type": "time_energy_mismatch",
                "name": "late_night_high_energy",
                "confidence": 0.8,
                "suggestion": "Schedule for morning"
            })
            skip_pattern = "late_night_high_energy"

    # Context patterns
    if "meeting" in task_title and current_user_energy == "low":
        patterns_detected.append({
            "type": "context_energy_mismatch",
            "name": "meeting_when_tired",
            "confidence": 0.7,
            "suggestion": "Reschedule meeting or delegate"
        })
        skip_pattern = "meeting_when_tired"

    # Delegation patterns
    delegation_triggers = ["coordinate", "follow up", "check with", "ask"]
    if any(trigger in task_title for trigger in delegation_triggers):
        patterns_detected.append({
            "type": "delegation_opportunity",
            "name": "can_delegate",
            "confidence": 0.6,
            "suggestion": "Consider delegating to Cindy or team"
        })

    return {
        "patterns_detected": patterns_detected,
        "skip_pattern": skip_pattern,
        "messages": state.get("messages", []) + [
            {"role": "system", "content": f"Patterns: {skip_pattern or 'none'}"}
        ]
    }


async def process_skip_intelligence(state: LycoGraphState) -> Dict[str, Any]:
    """
    Process skip intelligence to determine best action.

    Skip reasons:
    1. too_tired - Energy mismatch
    2. no_context - Missing required information
    3. needs_cindy - Requires family member input
    4. blocked - Waiting on dependency
    5. not_ready - Not mentally prepared
    """

    # Use v2 SkipIntelligence if available
    if SkipIntelligence and os.path.exists(lyco_v2_path / "src"):
        try:
            skip_intel = SkipIntelligence()
            result = await skip_intel.analyze_skip(
                task_id=state.get("task_id"),
                skip_count=state.get("skip_count", 0),
                patterns=state.get("patterns_detected", []),
                energy_level=state.get("energy_level"),
                current_energy=state.get("current_user_energy")
            )

            return {
                "skip_reasons": result.get("reasons", []),
                "should_park": result.get("should_park", False),
                "park_until": result.get("park_until"),
                "delegation_signal": result.get("delegation_signal"),
                "auto_skip_confidence": result.get("confidence", 0),
                "messages": state.get("messages", []) + [
                    {"role": "system", "content": f"Skip analysis: {result.get('action')}"}
                ]
            }
        except:
            pass

    # Fallback skip intelligence
    skip_count = state.get("skip_count", 0)
    skip_reasons = state.get("skip_reasons", [])
    patterns = state.get("patterns_detected", [])

    # Determine skip reason
    if state.get("energy_mismatch"):
        skip_reasons.append("too_tired")

    if state.get("context_required") and not state.get("extracted_entities"):
        skip_reasons.append("no_context")

    # Check for delegation signals
    task_title = state.get("task_title", "").lower()
    delegation_signal = None

    cindy_keywords = ["coordinate", "schedule", "organize", "plan", "arrange"]
    if any(keyword in task_title for keyword in cindy_keywords):
        skip_reasons.append("needs_cindy")
        delegation_signal = {
            "delegate_to": "cindy",
            "reason": "coordination task",
            "confidence": 0.7
        }

    # Determine action based on skip count and reasons
    should_park = False
    park_until = None

    if skip_count >= 3:
        if "too_tired" in skip_reasons:
            # Park until tomorrow morning
            tomorrow_9am = datetime.now().replace(hour=9, minute=0, second=0) + timedelta(days=1)
            should_park = True
            park_until = tomorrow_9am.isoformat()
        elif "no_context" in skip_reasons:
            # Park for 3 days to gather context
            should_park = True
            park_until = (datetime.now() + timedelta(days=3)).isoformat()

    # Calculate auto-skip confidence
    auto_skip_confidence = min(0.9, 0.3 + (skip_count * 0.15))

    return {
        "skip_reasons": skip_reasons,
        "should_park": should_park,
        "park_until": park_until,
        "delegation_signal": delegation_signal,
        "auto_skip_confidence": auto_skip_confidence,
        "messages": state.get("messages", []) + [
            {"role": "system", "content": f"Skip decision: {'park' if should_park else 'process'}"}
        ]
    }
