"""
FalkorDB Dual-Memory Manager for DemestiChat

Implements a dual-memory architecture where:
1. Private Memory - User-specific, isolated memories (default)
2. System Memory - Family-wide shared knowledge

This ensures privacy while enabling family collaboration.
"""

import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Literal, Any
from falkordb_manager import FalkorDBManager

logger = logging.getLogger(__name__)


class FalkorDBDualMemory:
    """
    Enhanced FalkorDB manager with dual-memory architecture.

    Memory Types:
    - Private: User-specific memories, completely isolated
    - System: Family-wide shared knowledge, accessible to all

    Default: Private (for safety and privacy)
    """

    def __init__(self, falkordb_manager: Optional[FalkorDBManager] = None):
        """
        Initialize dual-memory manager.

        Args:
            falkordb_manager: Existing FalkorDB connection (optional)
        """
        self.falkordb = falkordb_manager
        self.system_user_id = "family_system"

        logger.info("FalkorDB Dual-Memory Manager initialized")

    async def ensure_system_user(self):
        """Ensure the system user exists for shared memories."""
        if not self.falkordb or not self.falkordb.is_connected():
            logger.error("FalkorDB not connected - cannot ensure system user")
            return False

        try:
            query = """
            MERGE (s:System {id: $system_id})
            SET s.created_at = COALESCE(s.created_at, $timestamp),
                s.type = 'shared_memory_store',
                s.description = 'Shared family knowledge base',
                s.last_updated = $timestamp
            RETURN s.id
            """

            params = {
                "system_id": self.system_user_id,
                "timestamp": datetime.utcnow().isoformat(),
            }

            result = await self.falkordb.execute_query(query, params)

            if result:
                logger.info("✅ System memory node verified")
                return True
            else:
                logger.warning("System node creation returned no result")
                return False

        except Exception as e:
            logger.error(f"Failed to ensure system user: {e}")
            return False

    def determine_memory_type(
        self, content: str, user_id: str = None
    ) -> Literal["private", "system"]:
        """
        Intelligently determine if memory should be private or system-wide.

        Args:
            content: Memory content to classify
            user_id: User ID (for context-aware classification)

        Returns:
            'private' or 'system'
        """
        content_lower = content.lower()

        # PRIVATE keywords (explicit privacy markers take precedence)
        private_keywords = [
            "my password",
            "my secret",
            "my private",
            "don't tell",
            "dont tell",
            "personal",
            "confidential",
            "my account",
            "my login",
            "my pin",
            "my credit card",
            "my ssn",
            "my social security",
            "my bank",
            "diary",
            "my diary",
            "private note",
            "my note",
            "my medical",
            "my prescription",
            "my therapy",
        ]

        # Check for explicit privacy markers first
        for keyword in private_keywords:
            if keyword in content_lower:
                logger.debug(f"Private keyword detected: '{keyword}' in content")
                return "private"

        # SYSTEM-WIDE keywords (family relevant information)
        system_keywords = [
            # Family context
            "family",
            "everyone",
            "all of us",
            "we all",
            "our family",
            # Home/household
            "house",
            "home address",
            "our address",
            "wifi",
            "wi-fi",
            "router",
            "home wifi",
            "household",
            # Emergency and medical
            "emergency",
            "doctor",
            "hospital",
            "pediatrician",
            "dentist",
            "vet",
            "veterinarian",
            # School and activities
            "school",
            "teacher",
            "class",
            "school starts",
            "school ends",
            "practice",
            "lesson",
            "recital",
            "game",
            "match",
            # Events and calendar
            "vacation",
            "trip",
            "holiday",
            "birthday",
            "anniversary",
            "party",
            "celebration",
            "reunion",
            # Shared resources
            "car",
            "vehicle",
            "pet",
            "dog",
            "cat",
            "goldfish",
            # Family member names (customize for each family)
            "elena",
            "aris",
            "persy",
            "stelios",
            "franci",
            "cindy",
            "mene",
            "demestihas",
        ]

        # Check for family-wide relevance
        for keyword in system_keywords:
            if keyword in content_lower:
                logger.debug(f"System keyword detected: '{keyword}' in content")
                return "system"

        # Patterns indicating family-wide information
        family_patterns = [
            "scheduled for",
            "appointment for",
            "meeting at",
            "lives at",
            "located at",
            "address is",
            "everyone should",
            "we need to",
            "reminder for",
        ]

        for pattern in family_patterns:
            if pattern in content_lower:
                logger.debug(f"System pattern detected: '{pattern}' in content")
                return "system"

        # Default to private for safety
        logger.debug("No clear classification - defaulting to private for safety")
        return "private"

    async def store_memory(
        self,
        user_id: str,
        subject: str,
        predicate: str,
        obj: str,
        memory_type: Optional[Literal["private", "system", "auto"]] = "auto",
        metadata: Optional[Dict] = None,
        confidence: float = 0.9,
    ) -> Dict[str, Any]:
        """
        Store memory in either private user space or shared system space.

        Args:
            user_id: User who is creating the memory
            subject: Subject of the triple
            predicate: Predicate/relationship
            obj: Object of the triple
            memory_type: 'private', 'system', or 'auto' (auto-classify)
            metadata: Additional metadata
            confidence: Confidence score (0-1)

        Returns:
            Result dictionary with success status
        """
        if not self.falkordb or not self.falkordb.is_connected():
            logger.error("FalkorDB not connected - cannot store memory")
            return {
                "success": False,
                "error": "FalkorDB not connected",
                "memory_type": None,
            }

        try:
            timestamp = datetime.utcnow().isoformat()
            content = f"{subject} {predicate} {obj}"
            metadata_json = json.dumps(metadata or {})

            # Auto-classify if needed
            if memory_type == "auto":
                memory_type = self.determine_memory_type(content, user_id)

            # Ensure user node exists
            await self.falkordb.merge_node(
                "User",
                {"id": user_id, "last_updated": timestamp},
                match_properties=["id"],
            )

            if memory_type == "private":
                # Store in user's private memory
                query = """
                MATCH (u:User {id: $user_id})
                CREATE (m:UserMemory {
                    subject: $subject,
                    predicate: $predicate,
                    object: $obj,
                    content: $content,
                    timestamp: $timestamp,
                    confidence: $confidence,
                    metadata: $metadata
                })
                CREATE (u)-[:PRIVATE_KNOWS]->(m)
                RETURN m.subject as subject, m.timestamp as timestamp
                """

                params = {
                    "user_id": user_id,
                    "subject": subject,
                    "predicate": predicate,
                    "obj": obj,
                    "content": content,
                    "timestamp": timestamp,
                    "confidence": confidence,
                    "metadata": metadata_json,
                }

                result = await self.falkordb.execute_query(query, params)

                logger.info(
                    f"✅ Stored PRIVATE memory for {user_id}: {content[:50]}..."
                )

                return {
                    "success": True,
                    "memory_type": "private",
                    "message": f"I'll remember this just for you: {content}",
                }

            else:  # system memory
                # Ensure system node exists
                await self.ensure_system_user()

                # Store in shared system memory
                query = """
                MATCH (s:System {id: $system_id})
                MATCH (u:User {id: $user_id})
                CREATE (m:SystemMemory {
                    subject: $subject,
                    predicate: $predicate,
                    object: $obj,
                    content: $content,
                    timestamp: $timestamp,
                    added_by: $user_id,
                    confidence: $confidence,
                    metadata: $metadata
                })
                CREATE (s)-[:SHARED_KNOWS]->(m)
                CREATE (u)-[:CONTRIBUTED]->(m)
                RETURN m.subject as subject, m.timestamp as timestamp
                """

                params = {
                    "system_id": self.system_user_id,
                    "user_id": user_id,
                    "subject": subject,
                    "predicate": predicate,
                    "obj": obj,
                    "content": content,
                    "timestamp": timestamp,
                    "confidence": confidence,
                    "metadata": metadata_json,
                }

                result = await self.falkordb.execute_query(query, params)

                logger.info(f"✅ Stored SYSTEM memory by {user_id}: {content[:50]}...")

                return {
                    "success": True,
                    "memory_type": "system",
                    "message": f"I'll remember this for the whole family: {content}",
                }

        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            return {"success": False, "error": str(e), "memory_type": None}

    async def get_memories(
        self,
        user_id: str,
        query_text: Optional[str] = None,
        include_system: bool = True,
        limit: int = 10,
        memory_type_filter: Optional[Literal["private", "system", "all"]] = "all",
    ) -> List[Dict[str, Any]]:
        """
        Retrieve memories from both user's private space and system space.

        Args:
            user_id: User requesting memories
            query_text: Optional text search filter
            include_system: Whether to include system memories
            limit: Maximum number of memories to return
            memory_type_filter: Filter by memory type

        Returns:
            List of memory dictionaries with source indicators
        """
        if not self.falkordb or not self.falkordb.is_connected():
            logger.error("FalkorDB not connected - cannot retrieve memories")
            return []

        memories = []

        try:
            # Get user's private memories
            if memory_type_filter in ["private", "all"]:
                private_query = """
                MATCH (u:User {id: $user_id})-[:PRIVATE_KNOWS]->(m:UserMemory)
                RETURN
                    m.subject as subject,
                    m.predicate as predicate,
                    m.object as object,
                    m.content as content,
                    m.timestamp as timestamp,
                    m.confidence as confidence,
                    'private' as source,
                    $user_id as added_by,
                    m.metadata as metadata
                ORDER BY m.timestamp DESC
                LIMIT $limit
                """

                private_params = {"user_id": user_id, "limit": limit}
                private_results = await self.falkordb.execute_query(
                    private_query, private_params
                )

                for row in private_results:
                    memories.append(
                        {
                            "subject": row[0],
                            "predicate": row[1],
                            "object": row[2],
                            "content": row[3],
                            "timestamp": row[4],
                            "confidence": row[5],
                            "source": "private",
                            "added_by": user_id,
                            "metadata": json.loads(row[8]) if row[8] else {},
                        }
                    )

            # Get system memories if requested
            if include_system and memory_type_filter in ["system", "all"]:
                system_query = """
                MATCH (s:System {id: $system_id})-[:SHARED_KNOWS]->(m:SystemMemory)
                RETURN
                    m.subject as subject,
                    m.predicate as predicate,
                    m.object as object,
                    m.content as content,
                    m.timestamp as timestamp,
                    m.confidence as confidence,
                    'system' as source,
                    m.added_by as added_by,
                    m.metadata as metadata
                ORDER BY m.timestamp DESC
                LIMIT $limit
                """

                system_params = {"system_id": self.system_user_id, "limit": limit}
                system_results = await self.falkordb.execute_query(
                    system_query, system_params
                )

                for row in system_results:
                    memories.append(
                        {
                            "subject": row[0],
                            "predicate": row[1],
                            "object": row[2],
                            "content": row[3],
                            "timestamp": row[4],
                            "confidence": row[5],
                            "source": "system",
                            "added_by": row[7],
                            "metadata": json.loads(row[8]) if row[8] else {},
                        }
                    )

            # Sort combined results by timestamp (most recent first)
            memories.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

            # Apply text search filter if provided
            if query_text:
                query_lower = query_text.lower()
                memories = [
                    m for m in memories if query_lower in m.get("content", "").lower()
                ]

            # Apply final limit
            memories = memories[:limit]

            logger.info(
                f"Retrieved {len(memories)} memories for {user_id} "
                f"(private: {sum(1 for m in memories if m['source'] == 'private')}, "
                f"system: {sum(1 for m in memories if m['source'] == 'system')})"
            )

            return memories

        except Exception as e:
            logger.error(f"Failed to retrieve memories: {e}")
            return []

    async def get_memory_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about memory storage.

        Args:
            user_id: Optional user to get stats for (None for system-wide)

        Returns:
            Dictionary with memory statistics
        """
        if not self.falkordb or not self.falkordb.is_connected():
            return {"error": "FalkorDB not connected"}

        try:
            if user_id:
                # User-specific stats
                query = """
                MATCH (u:User {id: $user_id})-[:PRIVATE_KNOWS]->(pm:UserMemory)
                WITH count(pm) as private_count
                MATCH (s:System {id: $system_id})-[:SHARED_KNOWS]->(sm:SystemMemory)
                RETURN private_count, count(sm) as system_count
                """
                params = {"user_id": user_id, "system_id": self.system_user_id}
            else:
                # System-wide stats
                query = """
                MATCH (u:User)-[:PRIVATE_KNOWS]->(pm:UserMemory)
                WITH count(pm) as private_count
                MATCH (s:System {id: $system_id})-[:SHARED_KNOWS]->(sm:SystemMemory)
                RETURN private_count, count(sm) as system_count
                """
                params = {"system_id": self.system_user_id}

            result = await self.falkordb.execute_query(query, params)

            if result and len(result) > 0:
                private_count = result[0][0]
                system_count = result[0][1]

                return {
                    "user_id": user_id,
                    "private_memories": private_count,
                    "system_memories": system_count,
                    "total_memories": private_count + system_count,
                }
            else:
                return {
                    "user_id": user_id,
                    "private_memories": 0,
                    "system_memories": 0,
                    "total_memories": 0,
                }

        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {"error": str(e)}

    async def share_private_memory(
        self, user_id: str, memory_content: str
    ) -> Dict[str, Any]:
        """
        Convert a private memory to system memory (share with family).

        Args:
            user_id: User who owns the private memory
            memory_content: Content of the memory to share

        Returns:
            Result dictionary
        """
        # This would involve:
        # 1. Find the UserMemory node matching the content
        # 2. Create a new SystemMemory node with same data
        # 3. Optionally delete the UserMemory node
        # Implementation left for future enhancement

        logger.info(
            f"Share memory feature called by {user_id}: {memory_content[:50]}..."
        )
        return {"success": False, "message": "Share memory feature not yet implemented"}


# Global instance
dual_memory_manager: Optional[FalkorDBDualMemory] = None


def get_dual_memory_manager(
    falkordb_manager: Optional[FalkorDBManager] = None,
) -> Optional[FalkorDBDualMemory]:
    """Get the global dual-memory manager instance."""
    global dual_memory_manager

    if dual_memory_manager is None:
        dual_memory_manager = FalkorDBDualMemory(falkordb_manager)

    return dual_memory_manager
