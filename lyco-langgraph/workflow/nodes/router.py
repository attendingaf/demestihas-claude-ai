"""
Routing nodes for decision making and flow control.

These nodes determine the appropriate action based on
task characteristics and user state.
"""

from typing import Dict, Any
from datetime import datetime
import sys
from pathlib import Path

# Add v2 path
lyco_v2_path = Path(__file__).parent.parent.parent.parent / "lyco-v2"
sys.path.insert(0, str(lyco_v2_path))

try:
    from src.rounds_mode import RoundsMode
except ImportError:
    RoundsMode = None

from workflow.state import LycoGraphState


async def route_by_priority(state: LycoGraphState) -> Dict[str, Any]:
    """
    Route task based on priority and current context.

    Considers:
    - Eisenhower quadrant
    - Energy levels
    - Skip patterns
    - Time of day
    - User preferences
    """

    quadrant = state.get("quadrant")
    energy_level = state.get("energy_level")
    current_user_energy = state.get("current_user_energy")
    skip_count = state.get("skip_count", 0)
    patterns = state.get("patterns_detected", [])

    # Default action based on quadrant
    action_map = {
        "DO_FIRST": "notify",
        "SCHEDULE": "schedule",
        "DELEGATE": "delegate",
        "ELIMINATE": "archive"
    }

    action = action_map.get(quadrant, "rounds")
    action_reason = f"Based on {quadrant} quadrant"

    # Override based on energy mismatch
    if state.get("energy_mismatch"):
        if energy_level == "high" and current_user_energy == "low":
            action = "park"
            action_reason = "High energy task but user is tired"
        elif energy_level == "low" and current_user_energy == "high":
            # Good time for quick wins
            if action != "notify":
                action = "rounds"
                action_reason = "Quick win opportunity"

    # Override based on skip patterns
    if skip_count > 5:
        if state.get("delegation_signal"):
            action = "delegate"
            action_reason = f"Repeatedly skipped ({skip_count}x), delegation suggested"
        else:
            action = "archive"
            action_reason = f"Repeatedly skipped ({skip_count}x), may not be important"

    # Check for immediate action signals
    task_title = state.get("task_title", "").lower()
    urgent_signals = ["urgent", "asap", "emergency", "blocked", "critical"]
    if any(signal in task_title for signal in urgent_signals):
        action = "notify"
        action_reason = "Urgent signal detected"

    # Generate alternative actions
    alternatives = []
    if action != "notify":
        alternatives.append("notify")
    if action != "schedule" and not state.get("calendar_blocked"):
        alternatives.append("schedule")
    if action != "delegate" and state.get("delegation_signal"):
        alternatives.append("delegate")
    if action != "rounds":
        alternatives.append("rounds")

    return {
        "action": action,
        "action_reason": action_reason,
        "alternative_actions": alternatives[:3],  # Top 3 alternatives
        "messages": state.get("messages", []) + [
            {"role": "system", "content": f"Routing to: {action} - {action_reason}"}
        ]
    }


async def process_rounds_mode(state: LycoGraphState) -> Dict[str, Any]:
    """
    Process task in rounds mode for rapid decision making.

    Rounds mode presents tasks for quick 4D decisions:
    - Do now
    - Delegate
    - Defer
    - Delete
    """

    # Use v2 RoundsMode if available
    if RoundsMode and os.path.exists(lyco_v2_path / "src"):
        try:
            rounds = RoundsMode()
            result = await rounds.process_task(
                task_title=state.get("task_title"),
                task_description=state.get("task_description"),
                energy_level=state.get("energy_level"),
                quadrant=state.get("quadrant"),
                session_id=state.get("rounds_session_id")
            )

            return {
                "rounds_decision": result.get("decision"),
                "rounds_decision_time_ms": result.get("decision_time"),
                "rounds_position": result.get("position"),
                "messages": state.get("messages", []) + [
                    {"role": "system", "content": f"Rounds decision: {result.get('decision')}"}
                ]
            }
        except:
            pass

    # Fallback rounds logic
    import time
    start_time = time.time()

    # Simple decision heuristics for rounds
    task_title = state.get("task_title", "").lower()
    energy_level = state.get("energy_level")
    current_user_energy = state.get("current_user_energy")
    quadrant = state.get("quadrant")

    # Quick decision logic
    if quadrant == "DO_FIRST":
        decision = "do_now"
    elif quadrant == "DELEGATE":
        decision = "delegate"
    elif quadrant == "ELIMINATE":
        decision = "delete"
    elif energy_level == "low" and current_user_energy in ["medium", "high"]:
        decision = "do_now"  # Quick win
    elif state.get("delegation_signal"):
        decision = "delegate"
    else:
        decision = "defer"

    # Calculate decision time
    decision_time_ms = int((time.time() - start_time) * 1000)

    return {
        "rounds_decision": decision,
        "rounds_decision_time_ms": decision_time_ms,
        "rounds_position": state.get("rounds_position", 1),
        "messages": state.get("messages", []) + [
            {"role": "user", "content": f"Rounds: {decision} ({decision_time_ms}ms)"}
        ]
    }
