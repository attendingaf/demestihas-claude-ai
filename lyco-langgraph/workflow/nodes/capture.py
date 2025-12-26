"""
Capture nodes for multi-source signal input.

These nodes handle input from various sources and normalize
them into the standard LycoGraphState format.
"""

from typing import Dict, Any
import json
from datetime import datetime
from uuid import uuid4
import sys
import os
from pathlib import Path

# Add v2 path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "lyco-v2"))

from workflow.state import LycoGraphState


async def capture_email_signal(state: LycoGraphState) -> Dict[str, Any]:
    """
    Capture and process email signals from Pluma.

    Handles emails from:
    - mene@beltlineconsulting.co
    - menelaos4@gmail.com
    """
    # Generate signal ID if not present
    signal_id = state.get("signal_id") or str(uuid4())

    # Extract email metadata
    metadata = state.get("source_metadata", {})

    return {
        "signal_id": signal_id,
        "source": "email",
        "timestamp": datetime.now().isoformat(),
        "source_metadata": {
            **metadata,
            "from": metadata.get("from", ""),
            "subject": metadata.get("subject", ""),
            "received_at": metadata.get("received_at", datetime.now().isoformat())
        },
        "messages": [{"role": "system", "content": f"Processing email signal: {signal_id}"}]
    }


async def capture_calendar_signal(state: LycoGraphState) -> Dict[str, Any]:
    """
    Capture and process calendar events from Huata.

    Extracts:
    - Event title and description
    - Start/end times
    - Attendees
    - Location
    """
    signal_id = state.get("signal_id") or str(uuid4())
    metadata = state.get("source_metadata", {})

    # Extract calendar-specific information
    event_data = {
        "title": metadata.get("title", ""),
        "start_time": metadata.get("start_time"),
        "end_time": metadata.get("end_time"),
        "attendees": metadata.get("attendees", []),
        "location": metadata.get("location", ""),
        "description": metadata.get("description", "")
    }

    # Build context from calendar event
    context_parts = []
    if event_data["attendees"]:
        context_parts.append(f"Meeting with: {', '.join(event_data['attendees'])}")
    if event_data["location"]:
        context_parts.append(f"Location: {event_data['location']}")

    return {
        "signal_id": signal_id,
        "source": "calendar",
        "timestamp": datetime.now().isoformat(),
        "raw_input": f"{event_data['title']}. {event_data['description']}",
        "context_required": context_parts,
        "source_metadata": event_data,
        "deadline": event_data.get("start_time"),
        "messages": [{"role": "system", "content": f"Processing calendar event: {event_data['title']}"}]
    }


async def capture_terminal_input(state: LycoGraphState) -> Dict[str, Any]:
    """
    Capture direct terminal/CLI input.

    This is the primary input method for quick task capture.
    """
    signal_id = state.get("signal_id") or str(uuid4())

    return {
        "signal_id": signal_id,
        "source": "terminal",
        "timestamp": datetime.now().isoformat(),
        "user_id": state.get("user_id", "mene@beltlineconsulting.co"),
        "source_metadata": {
            "input_method": "cli",
            "session_id": state.get("source_metadata", {}).get("session_id")
        },
        "messages": [{"role": "user", "content": state.get("raw_input", "")}]
    }


async def capture_api_request(state: LycoGraphState) -> Dict[str, Any]:
    """
    Capture API requests including rounds mode triggers.

    Handles:
    - Direct API task creation
    - Rounds mode batch processing
    - Integration webhooks
    """
    signal_id = state.get("signal_id") or str(uuid4())
    metadata = state.get("source_metadata", {})

    # Check if this is a rounds mode request
    is_rounds = metadata.get("rounds_mode", False) or state.get("source") == "rounds"

    return {
        "signal_id": signal_id,
        "source": "api" if not is_rounds else "rounds",
        "timestamp": datetime.now().isoformat(),
        "source_metadata": {
            **metadata,
            "api_version": metadata.get("api_version", "v2"),
            "client_id": metadata.get("client_id"),
            "rounds_mode": is_rounds
        },
        "rounds_session_id": str(uuid4()) if is_rounds else None,
        "messages": [{"role": "system", "content": f"Processing API request: {signal_id}"}]
    }


async def capture_webhook(state: LycoGraphState) -> Dict[str, Any]:
    """
    Capture webhook events from external services.

    Primarily for:
    - Notion updates
    - GitHub issues
    - Slack messages
    """
    signal_id = state.get("signal_id") or str(uuid4())
    metadata = state.get("source_metadata", {})

    # Extract webhook-specific data
    webhook_data = {
        "service": metadata.get("service", "unknown"),
        "event_type": metadata.get("event_type"),
        "payload": metadata.get("payload", {}),
        "signature": metadata.get("signature")
    }

    # Parse based on service type
    raw_input = state.get("raw_input", "")
    if webhook_data["service"] == "notion":
        # Extract Notion page title and content
        payload = webhook_data["payload"]
        raw_input = f"{payload.get('title', '')}. {payload.get('content', '')}"
    elif webhook_data["service"] == "github":
        # Extract issue/PR title and body
        payload = webhook_data["payload"]
        raw_input = f"{payload.get('title', '')}. {payload.get('body', '')}"

    return {
        "signal_id": signal_id,
        "source": "webhook",
        "timestamp": datetime.now().isoformat(),
        "raw_input": raw_input,
        "source_metadata": webhook_data,
        "messages": [{"role": "system", "content": f"Processing webhook from {webhook_data['service']}"}]
    }
