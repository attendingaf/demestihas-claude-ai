#!/usr/bin/env python3
"""
LLM Extraction Bridge for Dual Memory System

This script queries Qdrant for chat messages, uses Claude API to extract
structured facts, and stores them in FalkorDB via the memory API.

Architecture:
  Chat → Agent → Mem0/Qdrant (98 memories) ✅
              ↓
       [LLM Extractor] ← This Script
              ↓
           FalkorDB ✅
              ↑
      Memory UI (queries FalkorDB)
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import yaml
from anthropic import Anthropic
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, Range

# Configure logging
log_dir = os.getenv("LOG_DIR", "/root/memory-bridge")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "extraction.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class MemoryBridge:
    """Extracts facts from chat messages and stores in FalkorDB."""

    def __init__(self, config_path: str = "/root/memory-bridge/config.yaml"):
        """Initialize the memory bridge with configuration."""
        logger.info("Initializing Memory Bridge...")

        # Load configuration - try multiple paths
        config_paths = [config_path, "/app/config.yaml", "./config.yaml"]
        config_loaded = False

        for path in config_paths:
            try:
                if os.path.exists(path):
                    with open(path, "r") as f:
                        self.config = yaml.safe_load(f)
                    config_loaded = True
                    logger.info(f"Loaded config from: {path}")
                    break
            except Exception:
                continue

        if not config_loaded:
            raise FileNotFoundError(f"Config file not found in any of: {config_paths}")

        # Load environment variables
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        # Initialize Anthropic client
        self.anthropic = Anthropic(api_key=self.anthropic_api_key)

        # Initialize Qdrant client
        qdrant_config = self.config["qdrant"]
        self.qdrant = QdrantClient(
            host=qdrant_config["host"], port=qdrant_config["port"]
        )
        self.collection_name = qdrant_config["collection_name"]

        # JWT token for memory API
        self.jwt_token = self._get_jwt_token()

        # Statistics tracking
        self.stats = {
            "messages_processed": 0,
            "facts_extracted": 0,
            "facts_stored": 0,
            "duplicates_skipped": 0,
            "errors": 0,
            "api_calls": 0,
            "start_time": datetime.utcnow().isoformat(),
        }

        logger.info(f"✅ Memory Bridge initialized successfully")
        logger.info(f"   Qdrant: {qdrant_config['host']}:{qdrant_config['port']}")
        logger.info(f"   Collection: {self.collection_name}")
        logger.info(f"   Model: {self.config['anthropic']['model']}")

    def _get_jwt_token(self) -> str:
        """Get JWT token for memory API authentication."""
        # Try multiple token file locations
        token_files = [
            "/root/mene-jwt-token.json",
            "/app/mene-jwt-token.json",
            "./mene-jwt-token.json",
        ]

        for token_file in token_files:
            try:
                if os.path.exists(token_file):
                    with open(token_file, "r") as f:
                        token_data = json.load(f)
                        logger.info(f"Loaded JWT token from: {token_file}")
                        return token_data["access_token"]
            except Exception:
                continue

        logger.error(f"Failed to load JWT token from any location: {token_files}")
        raise ValueError("JWT token file not found")

    def get_recent_memories(
        self, hours: int = 24, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query Qdrant for recent chat messages.

        Args:
            hours: Look back this many hours
            limit: Maximum number of messages to retrieve

        Returns:
            List of message dictionaries with content and metadata
        """
        logger.info(f"Querying Qdrant for messages from last {hours} hours...")

        try:
            # Check if collection exists
            collections = self.qdrant.get_collections().collections
            collection_names = [col.name for col in collections]

            if self.collection_name not in collection_names:
                logger.warning(
                    f"Collection '{self.collection_name}' not found in Qdrant"
                )
                logger.info(f"Available collections: {collection_names}")

                # Try alternative collection names
                alternative_names = ["demestihas", "memories", "chat", "mem0"]
                for alt_name in alternative_names:
                    if alt_name in collection_names:
                        logger.info(f"Using alternative collection: {alt_name}")
                        self.collection_name = alt_name
                        break
                else:
                    logger.error("No suitable collection found")
                    return []

            # Calculate timestamp threshold
            threshold = datetime.utcnow() - timedelta(hours=hours)
            threshold_timestamp = int(threshold.timestamp())

            # Scroll through all points in the collection
            # Qdrant scroll API allows fetching all points without vector search
            all_points = []
            offset = None

            while True:
                result = self.qdrant.scroll(
                    collection_name=self.collection_name,
                    limit=100,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )

                points, next_offset = result

                if not points:
                    break

                all_points.extend(points)
                offset = next_offset

                if next_offset is None:
                    break

                if len(all_points) >= limit:
                    break

            logger.info(f"Retrieved {len(all_points)} total points from Qdrant")

            # Filter and format messages
            messages = []
            for point in all_points[:limit]:
                payload = point.payload

                # Extract message content (adjust field names based on actual structure)
                content = (
                    payload.get("text")
                    or payload.get("message")
                    or payload.get("content")
                    or payload.get("data", {})
                    .get("messages", [{}])[-1]
                    .get("content", "")
                )

                # Skip empty messages
                if not content or len(content.strip()) < 10:
                    continue

                # Extract timestamp
                timestamp_field = (
                    payload.get("timestamp")
                    or payload.get("created_at")
                    or payload.get("created_date")
                )

                message_data = {
                    "id": point.id,
                    "content": content,
                    "timestamp": timestamp_field or datetime.utcnow().isoformat(),
                    "user_id": payload.get("user_id", "unknown"),
                    "metadata": payload,
                }

                messages.append(message_data)

            logger.info(f"✅ Found {len(messages)} valid messages")

            # Log sample message for debugging
            if messages:
                sample = messages[0]
                logger.info(f"Sample message: {sample['content'][:100]}...")

            return messages

        except Exception as e:
            logger.error(f"Failed to query Qdrant: {e}")
            import traceback

            logger.error(traceback.format_exc())
            return []

    def extract_facts_from_message(self, message: str) -> List[Dict[str, Any]]:
        """
        Use Claude API to extract structured facts from a message.

        Args:
            message: The message text to extract facts from

        Returns:
            List of fact dictionaries
        """
        extraction_prompt = f"""Analyze this conversation excerpt and extract factual information as structured triples.

Conversation:
{message}

Extract facts in this JSON format:
{{
  "facts": [
    {{
      "subject": "Dr. Chen",
      "predicate": "wants patient to",
      "object": "check blood pressure before meals",
      "context": "medical",
      "importance": 9,
      "confidence": 0.95
    }}
  ]
}}

Rules:
1. Only extract verifiable facts, not opinions or questions
2. Medical info = importance 9-10
3. Family info = importance 7-8
4. Preferences = importance 5-6
5. Context must be: medical, family, project, schedule, preference, or adhd-optimization
6. Confidence: how certain you are this is a fact (0.0-1.0)
7. Ignore greetings, acknowledgments, and meta-conversation
8. If no facts found, return {{"facts": []}}

Respond with ONLY valid JSON. No explanation."""

        try:
            self.stats["api_calls"] += 1

            response = self.anthropic.messages.create(
                model=self.config["anthropic"]["model"],
                max_tokens=self.config["anthropic"]["max_tokens"],
                temperature=self.config["anthropic"]["temperature"],
                messages=[{"role": "user", "content": extraction_prompt}],
            )

            # Extract JSON from response
            content = response.content[0].text

            # Parse JSON
            try:
                data = json.loads(content)
                facts = data.get("facts", [])

                # Filter by confidence and importance
                min_confidence = self.config["filtering"]["min_confidence"]
                min_importance = self.config["filtering"]["min_importance"]

                filtered_facts = [
                    fact
                    for fact in facts
                    if fact.get("confidence", 0) >= min_confidence
                    and fact.get("importance", 0) >= min_importance
                ]

                logger.info(
                    f"Extracted {len(facts)} facts, {len(filtered_facts)} after filtering"
                )

                return filtered_facts

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Response content: {content}")
                return []

        except Exception as e:
            logger.error(f"Claude API extraction failed: {e}")
            self.stats["errors"] += 1
            return []

    def store_fact_in_falkordb(
        self, fact: Dict[str, Any], user_id: str = "system"
    ) -> bool:
        """
        Store a fact in FalkorDB via the memory API.

        Args:
            fact: Fact dictionary with subject, predicate, object, etc.
            user_id: User ID for the memory

        Returns:
            True if stored successfully, False otherwise
        """
        try:
            # Format enriched content
            enriched_content = {
                "subject": fact["subject"],
                "predicate": fact["predicate"],
                "object": fact["object"],
                "context": fact.get("context", "general"),
                "importance": fact.get("importance", 5),
                "confidence": fact.get("confidence", 0.8),
                "extracted_at": datetime.utcnow().isoformat(),
                "source": "memory_bridge",
            }

            # Check for duplicates if enabled
            if self.config["storage"]["deduplicate"]:
                if self._is_duplicate(fact):
                    logger.info(
                        f"Skipping duplicate fact: {fact['subject']} {fact['predicate']} {fact['object']}"
                    )
                    self.stats["duplicates_skipped"] += 1
                    return False

            # Store via memory API
            api_url = self.config["storage"]["api_url"]

            payload = {
                "user_id": user_id,
                "subject": fact["subject"],
                "predicate": fact["predicate"],
                "object": fact["object"],
                "memory_type": self.config["storage"]["memory_type"],
                "metadata": enriched_content,
            }

            response = requests.post(
                f"{api_url}/memory/store",
                json=payload,
                headers={"Authorization": f"Bearer {self.jwt_token}"},
                timeout=10,
            )

            if response.status_code == 200:
                logger.info(
                    f"✅ Stored fact: {fact['subject']} → {fact['predicate']} → {fact['object']}"
                )
                self.stats["facts_stored"] += 1
                return True
            else:
                logger.error(
                    f"Failed to store fact: {response.status_code} - {response.text}"
                )
                self.stats["errors"] += 1
                return False

        except Exception as e:
            logger.error(f"Error storing fact in FalkorDB: {e}")
            self.stats["errors"] += 1
            return False

    def _is_duplicate(self, fact: Dict[str, Any]) -> bool:
        """
        Check if a fact already exists in FalkorDB.

        Simple implementation: Check if the content string is similar.
        More sophisticated: Query FalkorDB for similar triples.

        Args:
            fact: Fact to check

        Returns:
            True if duplicate found
        """
        # Simple string-based check for now
        # In production, this would query FalkorDB
        content = f"{fact['subject']} {fact['predicate']} {fact['object']}"

        # TODO: Implement actual FalkorDB query for duplicate detection
        # For now, assume no duplicates (basic implementation)
        return False

    def run_extraction(
        self, hours: int = 24, once: bool = False, dry_run: bool = False
    ):
        """
        Main extraction loop.

        Args:
            hours: Look back this many hours
            once: Run once and exit (default: continuous loop)
            dry_run: Don't actually store facts, just extract and display
        """
        logger.info(
            f"Starting extraction (hours={hours}, once={once}, dry_run={dry_run})"
        )

        iteration = 0

        while True:
            iteration += 1
            logger.info(f"=== Extraction Iteration {iteration} ===")

            try:
                # Get recent messages
                messages = self.get_recent_memories(
                    hours=hours, limit=self.config["extraction"]["batch_size"]
                )

                if not messages:
                    logger.warning("No messages found")
                else:
                    # Process each message
                    for msg in messages:
                        self.stats["messages_processed"] += 1

                        logger.info(
                            f"Processing message {msg['id']}: {msg['content'][:80]}..."
                        )

                        # Extract facts
                        facts = self.extract_facts_from_message(msg["content"])

                        if facts:
                            self.stats["facts_extracted"] += len(facts)

                            logger.info(f"  Extracted {len(facts)} facts")

                            # Store each fact
                            for fact in facts:
                                if dry_run:
                                    logger.info(f"  [DRY RUN] Would store: {fact}")
                                else:
                                    self.store_fact_in_falkordb(fact, msg["user_id"])
                        else:
                            logger.info(f"  No facts extracted")

                # Log statistics
                self._log_stats()

                # Exit if running once
                if once:
                    logger.info("Single run complete, exiting")
                    break

                # Wait before next iteration
                interval = self.config["extraction"]["interval_seconds"]
                logger.info(f"Waiting {interval} seconds before next run...")
                time.sleep(interval)

            except KeyboardInterrupt:
                logger.info("Interrupted by user, exiting...")
                break
            except Exception as e:
                logger.error(f"Error in extraction loop: {e}")
                import traceback

                logger.error(traceback.format_exc())
                self.stats["errors"] += 1

                # Wait before retry
                logger.info("Waiting 60 seconds before retry...")
                time.sleep(60)

        # Final statistics
        logger.info("=== Final Statistics ===")
        self._log_stats()

    def _log_stats(self):
        """Log current statistics."""
        logger.info(f"Statistics:")
        logger.info(f"  Messages processed: {self.stats['messages_processed']}")
        logger.info(f"  Facts extracted: {self.stats['facts_extracted']}")
        logger.info(f"  Facts stored: {self.stats['facts_stored']}")
        logger.info(f"  Duplicates skipped: {self.stats['duplicates_skipped']}")
        logger.info(f"  API calls: {self.stats['api_calls']}")
        logger.info(f"  Errors: {self.stats['errors']}")

        # Calculate cost estimate (rough)
        # Claude Sonnet 4 pricing: ~$3 per million input tokens, ~$15 per million output tokens
        # Assume ~500 input tokens and ~200 output tokens per call
        estimated_cost = self.stats["api_calls"] * (
            (500 * 3 / 1000000) + (200 * 15 / 1000000)
        )
        logger.info(f"  Estimated API cost: ${estimated_cost:.4f}")


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(description="Memory Bridge - LLM Fact Extractor")
    parser.add_argument(
        "--dry-run", action="store_true", help="Extract but don't store facts"
    )
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument(
        "--hours", type=int, default=24, help="Look back N hours (default: 24)"
    )
    parser.add_argument(
        "--test-message", type=str, help="Test extraction on a single message"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="/root/memory-bridge/config.yaml",
        help="Config file path",
    )

    args = parser.parse_args()

    try:
        bridge = MemoryBridge(config_path=args.config)

        # Test mode: single message
        if args.test_message:
            logger.info(f"Testing extraction on message: {args.test_message}")
            facts = bridge.extract_facts_from_message(args.test_message)

            print("\n=== Extracted Facts ===")
            if facts:
                for i, fact in enumerate(facts, 1):
                    print(f"\n{i}. Subject: {fact['subject']}")
                    print(f"   Predicate: {fact['predicate']}")
                    print(f"   Object: {fact['object']}")
                    print(f"   Context: {fact.get('context', 'N/A')}")
                    print(f"   Importance: {fact.get('importance', 'N/A')}")
                    print(f"   Confidence: {fact.get('confidence', 'N/A')}")
            else:
                print("No facts extracted")

            return

        # Normal mode: process messages
        bridge.run_extraction(hours=args.hours, once=args.once, dry_run=args.dry_run)

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback

        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
