"""
Action nodes for task execution and user interaction.

These nodes perform the actual actions on tasks.
"""

from typing import Dict, Any
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add v2 path
lyco_v2_path = Path(__file__).parent.parent.parent.parent / "lyco-v2"
sys.path.insert(0, str(lyco_v2_path))

from workflow.state import LycoGraphState


async def send_notification(state: LycoGraphState) -> Dict[str, Any]:
    """
    Send notification to user about task.

    Channels:
    - Terminal (default)
    - Email
    - SMS (future)
    - Slack (future)
    """

    task_title = state.get("task_title", "Task")
    task_description = state.get("task_description", "")
    priority_score = state.get("priority_score", 0)
    quadrant = state.get("quadrant", "")

    # Determine notification channel
    channel = "terminal"  # Default
    if priority_score > 4.5:
        channel = "email"  # High priority gets email

    # Format notification message
    if channel == "terminal":
        message = f"""
🔔 TASK NOTIFICATION
Title: {task_title}
Priority: {quadrant} (Score: {priority_score:.1f})
Description: {task_description[:200]}
Action: Ready for immediate attention
"""
    else:
        message = f"Task '{task_title}' requires your attention"

    # In production, would actually send notification
    # For now, just log it
    print(message)

    return {
        "notification_sent": True,
        "notification_channel": channel,
        "messages": state.get("messages", []) + [
            {"role": "system", "content": f"Notification sent via {channel}"}
        ]
    }


async def block_calendar_time(state: LycoGraphState) -> Dict[str, Any]:
    """
    Block time on calendar for task execution.

    Integrates with Google Calendar via Huata.
    """

    task_title = state.get("task_title", "Task")
    time_estimate = state.get("time_estimate", 30)  # Default 30 minutes
    deadline = state.get("deadline")

    # Calculate when to schedule
    if deadline:
        # Schedule before deadline
        schedule_time = datetime.fromisoformat(deadline) - timedelta(minutes=time_estimate)
    else:
        # Schedule based on energy and quadrant
        energy_level = state.get("energy_level")
        if energy_level == "high":
            # Schedule for next morning
            tomorrow = datetime.now() + timedelta(days=1)
            schedule_time = tomorrow.replace(hour=9, minute=0, second=0)
        else:
            # Schedule for this afternoon
            schedule_time = datetime.now().replace(hour=14, minute=0, second=0)
            if schedule_time < datetime.now():
                schedule_time += timedelta(days=1)

    # In production, would integrate with Google Calendar API
    calendar_block_id = f"cal_{datetime.now().timestamp()}"

    return {
        "calendar_blocked": True,
        "calendar_block_id": calendar_block_id,
        "rescheduled_for": schedule_time.isoformat(),
        "messages": state.get("messages", []) + [
            {"role": "system", "content": f"Calendar blocked: {schedule_time.strftime('%Y-%m-%d %H:%M')}"}
        ]
    }


async def assign_to_family(state: LycoGraphState) -> Dict[str, Any]:
    """
    Delegate task to family member.

    Family members:
    - Cindy: Coordination, scheduling, planning
    - Elena: Creative tasks, design
    - Aris: Technical tasks, research
    """

    task_title = state.get("task_title", "").lower()
    task_description = state.get("task_description", "").lower()
    delegation_signal = state.get("delegation_signal", {})

    # Determine best assignee
    if delegation_signal.get("delegate_to"):
        assigned_to = delegation_signal["delegate_to"]
    else:
        # Use heuristics
        if any(word in task_title for word in ["coordinate", "schedule", "organize", "plan"]):
            assigned_to = "cindy"
        elif any(word in task_title for word in ["design", "creative", "visual", "art"]):
            assigned_to = "elena"
        elif any(word in task_title for word in ["code", "technical", "research", "analyze"]):
            assigned_to = "aris"
        else:
            assigned_to = "team"  # General delegation

    # Format delegation message
    delegation_message = f"""
Task Delegated to {assigned_to.title()}:
{state.get("task_title")}

{state.get("task_description", "")}

Priority: {state.get("quadrant", "NORMAL")}
Deadline: {state.get("deadline", "No specific deadline")}
"""

    return {
        "assigned_to": assigned_to,
        "notification_sent": True,
        "messages": state.get("messages", []) + [
            {"role": "system", "content": f"Delegated to {assigned_to}"}
        ]
    }


async def park_for_later(state: LycoGraphState) -> Dict[str, Any]:
    """
    Park task for later processing.

    Parking reasons:
    - Energy mismatch
    - Missing context
    - Not the right time
    - Waiting on dependency
    """

    park_until = state.get("park_until")

    if not park_until:
        # Default parking logic
        skip_reasons = state.get("skip_reasons", [])

        if "too_tired" in skip_reasons:
            # Park until tomorrow morning
            tomorrow_9am = datetime.now().replace(hour=9, minute=0, second=0)
            if tomorrow_9am < datetime.now():
                tomorrow_9am += timedelta(days=1)
            park_until = tomorrow_9am.isoformat()
        elif "no_context" in skip_reasons:
            # Park for 3 days
            park_until = (datetime.now() + timedelta(days=3)).isoformat()
        else:
            # Default: park for 24 hours
            park_until = (datetime.now() + timedelta(days=1)).isoformat()

    return {
        "should_park": True,
        "park_until": park_until,
        "action": "park",
        "messages": state.get("messages", []) + [
            {"role": "system", "content": f"Parked until {park_until}"}
        ]
    }


async def move_to_archive(state: LycoGraphState) -> Dict[str, Any]:
    """
    Archive task (eliminate or complete).

    Archives when:
    - Task is in ELIMINATE quadrant
    - Repeatedly skipped (>7 times)
    - Marked as not important
    - Completed
    """

    quadrant = state.get("quadrant")
    skip_count = state.get("skip_count", 0)

    # Determine archive reason
    if quadrant == "ELIMINATE":
        archive_reason = "Not important or urgent"
    elif skip_count > 7:
        archive_reason = f"Skipped {skip_count} times"
    else:
        archive_reason = "Task completed or no longer relevant"

    return {
        "action": "archive",
        "messages": state.get("messages", []) + [
            {"role": "system", "content": f"Archived: {archive_reason}"}
        ]
    }
