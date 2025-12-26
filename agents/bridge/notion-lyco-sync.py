#!/usr/bin/env python3
"""
Notion-Lyco Bidirectional Sync Bridge
Synchronizes tasks between Lyco database and Notion Master Tasks
"""

import asyncio
import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import hashlib
import aiohttp
from dotenv import load_dotenv
import logging

load_dotenv()

# Configuration
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "245413ec-f376-8021-8ddc-000b4ab96ae2")
LYCO_DB_PATH = os.getenv("LYCO_DB_PATH", "/Users/menedemestihas/Projects/demestihas-ai/agents/lyco/lyco.db")
LYCO_API_URL = os.getenv("LYCO_API_URL", "http://localhost:8000")
SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL_SECONDS", "300"))
LOG_DIR = Path("/Users/menedemestihas/Projects/demestihas-ai/logs/sync-audit")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"sync_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class NotionLycoSync:
    """Handles bidirectional sync between Notion and Lyco"""

    def __init__(self):
        self.notion_headers = {
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        self.session: Optional[aiohttp.ClientSession] = None
        self.sync_state = {}
        self.field_mappings = self._load_field_mappings()

    def _load_field_mappings(self) -> Dict[str, Any]:
        """Load field mapping configuration"""
        mapping_file = Path(__file__).parent / "field-mappings.json"
        if mapping_file.exists():
            with open(mapping_file, "r") as f:
                return json.load(f)
        else:
            # Default mappings
            return {
                "lyco_to_notion": {
                    "title": "Name",
                    "energy_level": "Energy Level Required",
                    "estimated_duration": "Time Estimate",
                    "skip_reason": "Notes",
                    "completed": "Complete",
                    "completed_at": "date:Completed Date:start",
                    "context": "Context/Tags",
                    "priority": "Priority"
                },
                "notion_to_lyco": {
                    "Name": "title",
                    "Energy Level Required": "energy_level",
                    "Time Estimate": "estimated_duration",
                    "Complete": "completed",
                    "date:Completed Date:start": "completed_at",
                    "Context/Tags": "context",
                    "Priority": "priority",
                    "Notes": "skip_reason"
                }
            }

    async def initialize(self):
        """Initialize HTTP session and load sync state"""
        self.session = aiohttp.ClientSession()
        await self._load_sync_state()
        logger.info("Notion-Lyco sync bridge initialized")

    async def _load_sync_state(self):
        """Load last sync state from file"""
        state_file = LOG_DIR / "sync_state.json"
        if state_file.exists():
            with open(state_file, "r") as f:
                self.sync_state = json.load(f)
        else:
            self.sync_state = {
                "last_sync": None,
                "lyco_hashes": {},
                "notion_hashes": {}
            }

    async def _save_sync_state(self):
        """Save current sync state to file"""
        state_file = LOG_DIR / "sync_state.json"
        with open(state_file, "w") as f:
            json.dump(self.sync_state, f, indent=2, default=str)

    def _get_task_hash(self, task: Dict[str, Any]) -> str:
        """Generate hash for task to detect changes"""
        # Create deterministic string representation
        hash_str = json.dumps(task, sort_keys=True, default=str)
        return hashlib.md5(hash_str.encode()).hexdigest()

    def _map_eisenhower_matrix(self, lyco_task: Dict[str, Any]) -> str:
        """Map Lyco task properties to Eisenhower matrix quadrant"""
        priority = lyco_task.get("priority", "medium")
        energy_level = lyco_task.get("energy_level", "medium")
        skip_count = lyco_task.get("skip_count", 0)

        if priority == "critical" or priority == "high":
            return "🔥 Do Now"
        elif energy_level == "high" and priority == "medium":
            return "📅 Schedule"
        elif skip_count > 3:
            return "🗄️ Someday/Maybe"
        else:
            return "🧠 Brain Dump"

    async def fetch_lyco_tasks(self) -> List[Dict[str, Any]]:
        """Fetch all tasks from Lyco database"""
        try:
            conn = sqlite3.connect(LYCO_DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    id, title, context, energy_level, estimated_duration,
                    skip_count, skip_reason, completed, completed_at,
                    created_at, updated_at, priority
                FROM tasks
                WHERE deleted_at IS NULL
                ORDER BY created_at DESC
            """)

            tasks = [dict(row) for row in cursor.fetchall()]
            conn.close()

            logger.info(f"Fetched {len(tasks)} tasks from Lyco")
            return tasks

        except Exception as e:
            logger.error(f"Error fetching Lyco tasks: {e}")
            return []

    async def fetch_notion_tasks(self) -> List[Dict[str, Any]]:
        """Fetch all tasks from Notion database"""
        try:
            url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"

            all_tasks = []
            has_more = True
            start_cursor = None

            while has_more:
                payload = {
                    "page_size": 100,
                    "filter": {
                        "property": "Archived",
                        "checkbox": {
                            "equals": False
                        }
                    }
                }

                if start_cursor:
                    payload["start_cursor"] = start_cursor

                async with self.session.post(url, headers=self.notion_headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        all_tasks.extend(data.get("results", []))
                        has_more = data.get("has_more", False)
                        start_cursor = data.get("next_cursor")
                    else:
                        logger.error(f"Error fetching Notion tasks: {response.status}")
                        break

            logger.info(f"Fetched {len(all_tasks)} tasks from Notion")
            return all_tasks

        except Exception as e:
            logger.error(f"Error fetching Notion tasks: {e}")
            return []

    def _extract_notion_properties(self, notion_page: Dict[str, Any]) -> Dict[str, Any]:
        """Extract properties from Notion page"""
        props = notion_page.get("properties", {})

        extracted = {
            "notion_id": notion_page["id"],
            "title": "",
            "energy_level": "medium",
            "estimated_duration": None,
            "completed": False,
            "completed_at": None,
            "context": "",
            "notes": "",
            "eisenhower": "",
            "priority": "medium"
        }

        # Extract title
        if "Name" in props and props["Name"]["title"]:
            extracted["title"] = props["Name"]["title"][0].get("plain_text", "")

        # Extract other properties
        if "Energy Level Required" in props:
            select = props["Energy Level Required"].get("select")
            if select:
                extracted["energy_level"] = select["name"].lower()

        if "Time Estimate" in props and props["Time Estimate"]["number"]:
            extracted["estimated_duration"] = props["Time Estimate"]["number"]

        if "Complete" in props:
            extracted["completed"] = props["Complete"]["checkbox"]

        if "date:Completed Date:start" in props and props["date:Completed Date:start"]["date"]:
            extracted["completed_at"] = props["date:Completed Date:start"]["date"]["start"]

        if "Context/Tags" in props and props["Context/Tags"]["multi_select"]:
            tags = [tag["name"] for tag in props["Context/Tags"]["multi_select"]]
            extracted["context"] = ", ".join(tags)

        if "Notes" in props and props["Notes"]["rich_text"]:
            extracted["notes"] = props["Notes"]["rich_text"][0].get("plain_text", "")

        if "Eisenhower" in props and props["Eisenhower"]["select"]:
            extracted["eisenhower"] = props["Eisenhower"]["select"]["name"]

        if "Priority" in props and props["Priority"]["select"]:
            extracted["priority"] = props["Priority"]["select"]["name"].lower()

        return extracted

    async def create_notion_task(self, lyco_task: Dict[str, Any]) -> Optional[str]:
        """Create a new task in Notion"""
        try:
            url = "https://api.notion.com/v1/pages"

            properties = {
                "Name": {
                    "title": [{"text": {"content": lyco_task["title"]}}]
                },
                "Complete": {
                    "checkbox": lyco_task.get("completed", False)
                },
                "Eisenhower": {
                    "select": {"name": self._map_eisenhower_matrix(lyco_task)}
                }
            }

            # Add optional properties
            if lyco_task.get("energy_level"):
                properties["Energy Level Required"] = {
                    "select": {"name": lyco_task["energy_level"].capitalize()}
                }

            if lyco_task.get("estimated_duration"):
                properties["Time Estimate"] = {
                    "number": lyco_task["estimated_duration"]
                }

            if lyco_task.get("context"):
                tags = [tag.strip() for tag in lyco_task["context"].split(",")]
                properties["Context/Tags"] = {
                    "multi_select": [{"name": tag} for tag in tags]
                }

            if lyco_task.get("skip_reason"):
                properties["Notes"] = {
                    "rich_text": [{"text": {"content": lyco_task["skip_reason"]}}]
                }

            if lyco_task.get("completed_at"):
                properties["date:Completed Date:start"] = {
                    "date": {"start": lyco_task["completed_at"]}
                }

            payload = {
                "parent": {"database_id": NOTION_DATABASE_ID},
                "properties": properties
            }

            async with self.session.post(url, headers=self.notion_headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Created Notion task: {lyco_task['title']}")
                    return result["id"]
                else:
                    logger.error(f"Failed to create Notion task: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Error creating Notion task: {e}")
            return None

    async def update_notion_task(self, notion_id: str, updates: Dict[str, Any]):
        """Update existing Notion task"""
        try:
            url = f"https://api.notion.com/v1/pages/{notion_id}"

            properties = {}

            if "title" in updates:
                properties["Name"] = {
                    "title": [{"text": {"content": updates["title"]}}]
                }

            if "completed" in updates:
                properties["Complete"] = {"checkbox": updates["completed"]}

            if "energy_level" in updates:
                properties["Energy Level Required"] = {
                    "select": {"name": updates["energy_level"].capitalize()}
                }

            if "estimated_duration" in updates:
                properties["Time Estimate"] = {
                    "number": updates["estimated_duration"]
                }

            payload = {"properties": properties}

            async with self.session.patch(url, headers=self.notion_headers, json=payload) as response:
                if response.status == 200:
                    logger.info(f"Updated Notion task: {notion_id}")
                else:
                    logger.error(f"Failed to update Notion task: {response.status}")

        except Exception as e:
            logger.error(f"Error updating Notion task: {e}")

    async def create_lyco_task(self, notion_task: Dict[str, Any]) -> bool:
        """Create a new task in Lyco"""
        try:
            payload = {
                "title": notion_task["title"],
                "context": notion_task.get("context", ""),
                "energy_level": notion_task.get("energy_level", "medium"),
                "estimated_duration": notion_task.get("estimated_duration"),
                "completed": notion_task.get("completed", False),
                "priority": notion_task.get("priority", "medium"),
                "source": "notion_sync",
                "notion_id": notion_task["notion_id"]
            }

            async with self.session.post(
                f"{LYCO_API_URL}/api/tasks",
                json=payload
            ) as response:
                if response.status in [200, 201]:
                    logger.info(f"Created Lyco task: {notion_task['title']}")
                    return True
                else:
                    logger.error(f"Failed to create Lyco task: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Error creating Lyco task: {e}")
            return False

    async def update_lyco_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """Update existing Lyco task"""
        try:
            async with self.session.put(
                f"{LYCO_API_URL}/api/tasks/{task_id}",
                json=updates
            ) as response:
                if response.status == 200:
                    logger.info(f"Updated Lyco task: {task_id}")
                    return True
                else:
                    logger.error(f"Failed to update Lyco task: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Error updating Lyco task: {e}")
            return False

    async def sync_tasks(self):
        """Main sync logic"""
        logger.info("Starting sync cycle")

        # Fetch tasks from both systems
        lyco_tasks = await self.fetch_lyco_tasks()
        notion_tasks = await self.fetch_notion_tasks()

        # Build lookup maps
        lyco_by_id = {task["id"]: task for task in lyco_tasks}
        notion_by_id = {}
        notion_extracted = {}

        for notion_page in notion_tasks:
            extracted = self._extract_notion_properties(notion_page)
            notion_by_id[extracted["notion_id"]] = notion_page
            notion_extracted[extracted["notion_id"]] = extracted

        # Track synced items
        synced_lyco = set()
        synced_notion = set()

        # Sync Lyco → Notion
        for lyco_task in lyco_tasks:
            task_hash = self._get_task_hash(lyco_task)

            # Check if task has changed since last sync
            if (lyco_task["id"] in self.sync_state.get("lyco_hashes", {}) and
                self.sync_state["lyco_hashes"][lyco_task["id"]] == task_hash):
                continue

            # Find matching Notion task (by title for now)
            notion_match = None
            for notion_id, notion_task in notion_extracted.items():
                if notion_task["title"] == lyco_task["title"]:
                    notion_match = notion_id
                    break

            if notion_match:
                # Update existing Notion task
                await self.update_notion_task(notion_match, lyco_task)
                synced_notion.add(notion_match)
            else:
                # Create new Notion task
                notion_id = await self.create_notion_task(lyco_task)
                if notion_id:
                    synced_notion.add(notion_id)

            # Update hash
            self.sync_state.setdefault("lyco_hashes", {})[lyco_task["id"]] = task_hash
            synced_lyco.add(lyco_task["id"])

        # Sync Notion → Lyco
        for notion_id, notion_task in notion_extracted.items():
            if notion_id in synced_notion:
                continue  # Already synced

            task_hash = self._get_task_hash(notion_task)

            # Check if task has changed
            if (notion_id in self.sync_state.get("notion_hashes", {}) and
                self.sync_state["notion_hashes"][notion_id] == task_hash):
                continue

            # Find matching Lyco task
            lyco_match = None
            for lyco_id, lyco_task in lyco_by_id.items():
                if lyco_task["title"] == notion_task["title"]:
                    lyco_match = lyco_id
                    break

            if lyco_match:
                # Update existing Lyco task
                await self.update_lyco_task(lyco_match, notion_task)
            else:
                # Create new Lyco task
                await self.create_lyco_task(notion_task)

            # Update hash
            self.sync_state.setdefault("notion_hashes", {})[notion_id] = task_hash

        # Save sync state
        self.sync_state["last_sync"] = datetime.now().isoformat()
        await self._save_sync_state()

        logger.info(f"Sync complete. Synced {len(synced_lyco)} Lyco tasks, {len(synced_notion)} Notion tasks")

    async def run_sync_loop(self):
        """Run continuous sync loop"""
        while True:
            try:
                await self.sync_tasks()
                await asyncio.sleep(SYNC_INTERVAL)
            except Exception as e:
                logger.error(f"Sync error: {e}")
                await asyncio.sleep(60)  # Wait before retry

    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()


async def main():
    """Main entry point"""
    if not NOTION_API_KEY:
        logger.error("NOTION_API_KEY not set in environment")
        return

    sync_bridge = NotionLycoSync()

    try:
        await sync_bridge.initialize()
        await sync_bridge.run_sync_loop()
    finally:
        await sync_bridge.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Sync bridge stopped by user")
