"""
LLM parsing node using existing v2 IntelligenceEngine.

Wraps the v2 processor for task extraction and understanding.
"""

from typing import Dict, Any
import sys
import os
from pathlib import Path
from datetime import datetime
import asyncio

# Add v2 path
lyco_v2_path = Path(__file__).parent.parent.parent.parent / "lyco-v2"
sys.path.insert(0, str(lyco_v2_path))

try:
    from src.processor import IntelligenceEngine
except ImportError:
    # Fallback if v2 is not available
    IntelligenceEngine = None

from workflow.state import LycoGraphState


async def parse_with_llm(state: LycoGraphState) -> Dict[str, Any]:
    """
    Parse raw input using v2 IntelligenceEngine with Claude Haiku.

    Extracts:
    - Task title and description
    - Required context
    - Entities (people, dates, locations)
    - Initial priority signals
    """

    # Use v2 IntelligenceEngine if available
    if IntelligenceEngine and os.path.exists(lyco_v2_path / "src"):
        try:
            # Initialize engine with API keys from environment
            engine = IntelligenceEngine(
                anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
                openai_api_key=os.getenv("OPENAI_API_KEY")
            )

            # Process using v2 logic
            result = await engine.parse_signal(
                content=state.get("raw_input", ""),
                source=state.get("source", "terminal"),
                user_id=state.get("user_id", "mene@beltlineconsulting.co")
            )

            return {
                "task_title": result.get("title"),
                "task_description": result.get("description"),
                "context_required": result.get("context", []),
                "extracted_entities": result.get("entities", {}),
                "confidence_score": result.get("confidence", 0.8),
                "model_used": "claude-3-haiku",
                "processing_time_ms": result.get("processing_time", 0),
                "messages": state.get("messages", []) + [
                    {"role": "assistant", "content": f"Parsed task: {result.get('title')}"}
                ]
            }
        except Exception as e:
            # Fall back to simple parsing if v2 fails
            pass

    # Fallback parsing logic when v2 is not available
    raw_input = state.get("raw_input", "")

    # Simple extraction
    lines = raw_input.split('\n')
    title = lines[0][:100] if lines else "New Task"
    description = '\n'.join(lines[1:]) if len(lines) > 1 else raw_input

    # Extract entities with simple heuristics
    entities = {}

    # Look for email addresses
    import re
    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', raw_input)
    if emails:
        entities["emails"] = emails

    # Look for dates
    date_patterns = [
        r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
        r'\b\d{4}-\d{2}-\d{2}\b',
        r'\b(today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b'
    ]
    dates = []
    for pattern in date_patterns:
        found = re.findall(pattern, raw_input, re.IGNORECASE)
        dates.extend(found)
    if dates:
        entities["dates"] = dates

    # Look for people names (simple heuristic)
    people_keywords = ["mene", "cindy", "elena", "aris", "team"]
    found_people = [p for p in people_keywords if p.lower() in raw_input.lower()]
    if found_people:
        entities["people"] = found_people

    # Determine context requirements
    context_required = []
    if "meeting" in raw_input.lower():
        context_required.append("calendar_availability")
    if "email" in raw_input.lower() or "@" in raw_input:
        context_required.append("email_context")
    if any(word in raw_input.lower() for word in ["deadline", "due", "by"]):
        context_required.append("deadline_info")

    return {
        "task_title": title,
        "task_description": description,
        "context_required": context_required,
        "extracted_entities": entities,
        "confidence_score": 0.6,  # Lower confidence for fallback
        "model_used": "fallback_parser",
        "processing_time_ms": 10,
        "messages": state.get("messages", []) + [
            {"role": "assistant", "content": f"Parsed task (fallback): {title}"}
        ]
    }
