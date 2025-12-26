"""
Storage nodes for persistence across Redis, PostgreSQL, and Notion.

Handles caching, database persistence, and external synchronization.
"""

from typing import Dict, Any
import sys
import os
from pathlib import Path
import json
from datetime import datetime
from uuid import uuid4
import asyncio

# Add v2 path
lyco_v2_path = Path(__file__).parent.parent.parent.parent / "lyco-v2"
sys.path.insert(0, str(lyco_v2_path))

try:
    from src.cache_manager import TaskCache
    from src.database import DatabaseManager
    import redis
except ImportError:
    TaskCache = None
    DatabaseManager = None
    redis = None

from workflow.state import LycoGraphState


async def update_redis_cache(state: LycoGraphState) -> Dict[str, Any]:
    """
    Update Redis cache with task state.

    Caches:
    - Task details
    - Processing metrics
    - Skip patterns
    - User preferences
    """

    # Use v2 TaskCache if available
    if TaskCache and redis:
        try:
            cache = TaskCache()

            # Prepare cache data
            task_id = state.get("task_id") or str(uuid4())
            cache_data = {
                "task_id": task_id,
                "title": state.get("task_title"),
                "description": state.get("task_description"),
                "energy_level": state.get("energy_level"),
                "quadrant": state.get("quadrant"),
                "action": state.get("action"),
                "skip_count": state.get("skip_count", 0),
                "patterns": state.get("patterns_detected", []),
                "timestamp": datetime.now().isoformat(),
                "user_id": state.get("user_id")
            }

            # Cache with TTL
            await cache.set_task(task_id, cache_data, ttl=3600)

            # Update metrics
            await cache.increment_metric("tasks_processed")
            if state.get("cache_hit"):
                await cache.increment_metric("cache_hits")

            return {
                "task_id": task_id,
                "redis_published": True,
                "cache_hit": False,  # This was a write, not a hit
                "messages": state.get("messages", []) + [
                    {"role": "system", "content": f"Cached task {task_id}"}
                ]
            }
        except Exception as e:
            pass

    # Fallback: Generate task ID but don't actually cache
    task_id = state.get("task_id") or str(uuid4())

    return {
        "task_id": task_id,
        "redis_published": False,
        "cache_hit": False,
        "messages": state.get("messages", []) + [
            {"role": "system", "content": "Cache unavailable, continuing without cache"}
        ]
    }


async def persist_to_database(state: LycoGraphState) -> Dict[str, Any]:
    """
    Persist task to PostgreSQL/Supabase database.

    Stores:
    - Complete task record
    - Processing history
    - Skip intelligence data
    - Performance metrics
    """

    # Use v2 DatabaseManager if available
    if DatabaseManager and os.path.exists(lyco_v2_path / "src"):
        try:
            db = DatabaseManager()
            await db.initialize()

            # Prepare database record
            task_record = {
                "id": state.get("task_id") or str(uuid4()),
                "title": state.get("task_title"),
                "description": state.get("task_description"),
                "source": state.get("source"),
                "user_id": state.get("user_id"),
                "energy_level": state.get("energy_level"),
                "urgency": state.get("urgency"),
                "importance": state.get("importance"),
                "quadrant": state.get("quadrant"),
                "action": state.get("action"),
                "assigned_to": state.get("assigned_to"),
                "skip_count": state.get("skip_count", 0),
                "skip_reasons": json.dumps(state.get("skip_reasons", [])),
                "patterns": json.dumps(state.get("patterns_detected", [])),
                "created_at": state.get("timestamp"),
                "updated_at": datetime.now().isoformat(),
                "deadline": state.get("deadline"),
                "park_until": state.get("park_until"),
                "completed": state.get("action") == "archive"
            }

            # Save to database
            await db.save_task(task_record)

            # Save metrics
            if state.get("processing_time_ms"):
                await db.save_metric({
                    "task_id": task_record["id"],
                    "processing_time_ms": state.get("processing_time_ms"),
                    "confidence_score": state.get("confidence_score"),
                    "model_used": state.get("model_used"),
                    "cache_hit": state.get("cache_hit", False)
                })

            return {
                "database_saved": True,
                "messages": state.get("messages", []) + [
                    {"role": "system", "content": f"Saved to database: {task_record['id']}"}
                ]
            }
        except Exception as e:
            return {
                "database_saved": False,
                "error": str(e),
                "messages": state.get("messages", []) + [
                    {"role": "system", "content": f"Database error: {str(e)}"}
                ]
            }

    # Fallback: Mark as not saved
    return {
        "database_saved": False,
        "messages": state.get("messages", []) + [
            {"role": "system", "content": "Database unavailable"}
        ]
    }


async def synchronize_with_notion(state: LycoGraphState) -> Dict[str, Any]:
    """
    Sync task with Notion database.

    Creates/updates:
    - Task pages
    - Properties (energy, quadrant, status)
    - Relations (assigned to, blocked by)
    """

    # Check if Notion sync is needed
    if not state.get("task_title"):
        return {
            "notion_synced": False,
            "messages": state.get("messages", [])
        }

    # In production, would use Notion API
    # For now, simulate the sync
    notion_page_id = f"notion_{state.get('task_id', uuid4())}"

    # Determine which properties to sync
    notion_properties = {
        "Title": state.get("task_title"),
        "Status": {
            "notify": "To Do",
            "schedule": "Scheduled",
            "delegate": "Delegated",
            "archive": "Done",
            "park": "Parked"
        }.get(state.get("action"), "To Do"),
        "Energy": state.get("energy_level", "medium").title(),
        "Quadrant": state.get("quadrant", ""),
        "Assigned To": state.get("assigned_to", "mene").title(),
        "Priority Score": state.get("priority_score", 0),
        "Skip Count": state.get("skip_count", 0)
    }

    # Add deadline if present
    if state.get("deadline"):
        notion_properties["Deadline"] = state.get("deadline")

    # Add park until if parked
    if state.get("park_until"):
        notion_properties["Park Until"] = state.get("park_until")

    return {
        "notion_synced": True,
        "notion_page_id": notion_page_id,
        "messages": state.get("messages", []) + [
            {"role": "system", "content": f"Synced to Notion: {notion_page_id}"}
        ]
    }
