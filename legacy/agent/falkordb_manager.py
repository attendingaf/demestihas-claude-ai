"""
FalkorDB Connection Manager for DemestiChat Agent Service

This module provides an asynchronous connection pool manager for FalkorDB,
the persistent graph database backend for the knowledge consolidation system.

Architecture:
- Uses BlockingConnectionPool for optimal async performance
- Implements singleton pattern to prevent connection pool exhaustion
- All configuration externalized via environment variables
- Supports parameterized OpenCypher queries with MERGE semantics

Usage:
    from falkordb_manager import FalkorDBManager

    manager = FalkorDBManager()
    await manager.connect()

    result = await manager.execute_query(
        "MERGE (u:User {id: $userId}) RETURN u",
        {"userId": "EA"}
    )
"""

import os
import logging
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

try:
    from falkordb import FalkorDB, Graph
except ImportError:
    raise ImportError(
        "falkordb-py is not installed. Install it with: pip install falkordb"
    )

logger = logging.getLogger(__name__)


class FalkorDBManager:
    """
    Singleton connection manager for FalkorDB graph database.

    Handles connection pooling, query execution, and resource cleanup
    for the Agent Service's knowledge persistence layer.
    """

    _instance: Optional["FalkorDBManager"] = None
    _initialized: bool = False

    def __new__(cls):
        """Singleton pattern to ensure only one connection pool exists."""
        if cls._instance is None:
            cls._instance = super(FalkorDBManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize configuration from environment variables."""
        if self._initialized:
            return

        # Read configuration from environment
        self.host = os.getenv("FALKORDB_HOST", "graph_db")
        self.port = int(os.getenv("FALKORDB_PORT", "6379"))
        self.graph_name = os.getenv("FALKORDB_GRAPH_NAME", "demestihas_knowledge")
        self.max_connections = int(os.getenv("FALKORDB_MAX_CONNECTIONS", "10"))

        # Connection state
        self.client: Optional[FalkorDB] = None
        self.graph: Optional[Graph] = None
        self._initialized = True

        logger.info(
            f"FalkorDB Manager initialized: host={self.host}, port={self.port}, "
            f"graph={self.graph_name}, max_connections={self.max_connections}"
        )

    async def connect(self) -> None:
        """
        Establish connection to FalkorDB and select the graph.

        This method is idempotent - calling it multiple times is safe.

        Raises:
            ConnectionError: If connection to FalkorDB fails
        """
        if self.client is not None and self.graph is not None:
            logger.debug("FalkorDB connection already established")
            return

        try:
            # Create FalkorDB client with connection pooling
            self.client = FalkorDB(
                host=self.host, port=self.port, max_connections=self.max_connections
            )

            # Select the knowledge graph
            self.graph = self.client.select_graph(self.graph_name)

            logger.info(
                f"✅ Connected to FalkorDB at {self.host}:{self.port}, "
                f"graph: {self.graph_name}"
            )

            # Verify connection with a simple query
            result = await self.execute_query("RETURN 1 AS test")
            if result and len(result) > 0:
                logger.info("FalkorDB connection verified successfully")
            else:
                raise ConnectionError("FalkorDB connection verification failed")

        except Exception as e:
            logger.error(f"Failed to connect to FalkorDB: {str(e)}")
            self.client = None
            self.graph = None
            raise ConnectionError(f"FalkorDB connection failed: {str(e)}")

    async def disconnect(self) -> None:
        """
        Close the FalkorDB connection and release resources.

        Should be called during application shutdown.
        """
        if self.client:
            try:
                self.client.close()
                logger.info("FalkorDB connection closed")
            except Exception as e:
                logger.error(f"Error closing FalkorDB connection: {str(e)}")
            finally:
                self.client = None
                self.graph = None

    async def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        readonly: bool = False,
    ) -> List[Any]:
        """
        Execute a parameterized OpenCypher query against FalkorDB.

        Args:
            query: OpenCypher query string (use $param for parameters)
            params: Dictionary of parameter values
            readonly: If True, uses read-only execution for performance

        Returns:
            List of result records

        Raises:
            ConnectionError: If not connected to FalkorDB
            Exception: If query execution fails

        Example:
            result = await manager.execute_query(
                "MERGE (u:User {id: $userId}) RETURN u",
                {"userId": "EA"}
            )
        """
        if self.graph is None:
            raise ConnectionError("Not connected to FalkorDB. Call connect() first.")

        try:
            # Execute query with parameters
            if readonly:
                result = self.graph.ro_query(query, params or {})
            else:
                result = self.graph.query(query, params or {})

            # Convert result to list format
            result_list = result.result_set if hasattr(result, "result_set") else []

            logger.debug(
                f"Query executed: {query[:100]}... | "
                f"Params: {params} | Results: {len(result_list)}"
            )

            return result_list

        except Exception as e:
            logger.error(
                f"Query execution failed: {str(e)} | Query: {query[:100]}... | "
                f"Params: {params}"
            )
            raise

    async def merge_node(
        self,
        label: str,
        properties: Dict[str, Any],
        match_properties: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create or update a node using MERGE semantics.

        Args:
            label: Node label (e.g., "User", "Entity", "Critique")
            properties: Node properties as key-value pairs
            match_properties: Properties to use for matching (defaults to all)

        Returns:
            Dictionary with created/matched node information

        Example:
            await manager.merge_node(
                "User",
                {"id": "EA", "name": "Executive Assistant"},
                match_properties=["id"]
            )
        """
        if not match_properties:
            match_properties = list(properties.keys())

        # Build MATCH clause
        match_clause = ", ".join([f"{key}: ${key}" for key in match_properties])

        # Build SET clause for additional properties
        set_properties = {
            k: v for k, v in properties.items() if k not in match_properties
        }
        set_clause = (
            ", ".join([f"n.{key} = ${key}" for key in set_properties])
            if set_properties
            else ""
        )

        # Construct MERGE query
        query = f"MERGE (n:{label} {{{match_clause}}})"
        if set_clause:
            query += f" ON CREATE SET {set_clause} ON MATCH SET {set_clause}"
        query += " RETURN n"

        result = await self.execute_query(query, properties)

        return {"success": True, "label": label, "matched": len(result) > 0}

    async def merge_relationship(
        self,
        source_label: str,
        source_props: Dict[str, Any],
        rel_type: str,
        target_label: str,
        target_props: Dict[str, Any],
        rel_props: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create or update a relationship between two nodes using MERGE.

        Args:
            source_label: Label of source node
            source_props: Properties to match source node
            rel_type: Relationship type (e.g., "RECEIVED_CRITIQUE")
            target_label: Label of target node
            target_props: Properties to match target node
            rel_props: Properties to set on the relationship

        Returns:
            Dictionary with relationship creation status

        Example:
            await manager.merge_relationship(
                "User", {"id": "EA"},
                "RECEIVED_CRITIQUE",
                "Critique", {"id": "c123"},
                {"timestamp": "2025-10-02"}
            )
        """
        # Build match clauses
        source_match = ", ".join([f"{k}: $src_{k}" for k in source_props.keys()])
        target_match = ", ".join([f"{k}: $tgt_{k}" for k in target_props.keys()])

        # Prepare parameters with prefixes to avoid collisions
        params = {}
        for k, v in source_props.items():
            params[f"src_{k}"] = v
        for k, v in target_props.items():
            params[f"tgt_{k}"] = v

        # Build relationship properties clause
        rel_props_clause = ""
        if rel_props:
            rel_props_clause = (
                " {" + ", ".join([f"{k}: $rel_{k}" for k in rel_props.keys()]) + "}"
            )
            for k, v in rel_props.items():
                params[f"rel_{k}"] = v

        # Construct MERGE query
        query = f"""
        MERGE (s:{source_label} {{{source_match}}})
        MERGE (t:{target_label} {{{target_match}}})
        MERGE (s)-[r:{rel_type}{rel_props_clause}]->(t)
        RETURN s, r, t
        """

        result = await self.execute_query(query, params)

        return {"success": True, "relationship": rel_type, "created": len(result) > 0}

    async def execute_batch(
        self, queries: List[tuple[str, Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple queries in sequence (transaction-like behavior).

        Args:
            queries: List of (query, params) tuples

        Returns:
            List of result dictionaries

        Example:
            results = await manager.execute_batch([
                ("MERGE (u:User {id: $id})", {"id": "EA"}),
                ("MERGE (c:Critique {text: $text})", {"text": "tone issue"})
            ])
        """
        results = []

        for query, params in queries:
            try:
                result = await self.execute_query(query, params)
                results.append({"success": True, "result": result})
            except Exception as e:
                logger.error(f"Batch query failed: {str(e)}")
                results.append({"success": False, "error": str(e)})

        return results

    @asynccontextmanager
    async def transaction(self):
        """
        Context manager for transactional query execution.

        Note: FalkorDB transactions are handled at the query level.
        This is a convenience wrapper for future transaction support.

        Usage:
            async with manager.transaction():
                await manager.merge_node("User", {"id": "EA"})
                await manager.merge_node("Critique", {"text": "..."})
        """
        # FalkorDB handles transactions internally per query
        # This is a placeholder for future multi-query transaction support
        try:
            yield self
        except Exception as e:
            logger.error(f"Transaction failed: {str(e)}")
            raise

    def is_connected(self) -> bool:
        """Check if the manager is connected to FalkorDB."""
        return self.client is not None and self.graph is not None

    def get_connection_info(self) -> Dict[str, Any]:
        """Get current connection configuration information."""
        return {
            "host": self.host,
            "port": self.port,
            "graph_name": self.graph_name,
            "max_connections": self.max_connections,
            "connected": self.is_connected(),
        }

    # ========================================================================
    # PHASE 3: READ-PATH QUERY FUNCTIONS
    # ========================================================================

    async def get_user_critiques(
        self, user_id: str, limit: int = 5, category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve RLHF critiques for a specific user profile.

        Used by reflection_node to inform agent decision-making based on
        past feedback and identified failure patterns.

        Args:
            user_id: User identifier (e.g., 'EA', 'default_user')
            limit: Maximum number of critiques to retrieve (default: 5)
            category: Optional category filter (tone, formatting, routing, etc.)

        Returns:
            List of critique dictionaries with text, category, timestamp

        Example:
            critiques = await manager.get_user_critiques('EA', limit=5, category='tone')
        """
        try:
            # Build category filter
            category_filter = ""
            params = {"user_id": user_id, "limit": limit}

            if category:
                category_filter = "AND c.category = $category"
                params["category"] = category

            # OpenCypher query to retrieve critiques
            query = f"""
            MATCH (u:User {{id: $user_id}})-[:RECEIVED_CRITIQUE]->(c:Critique)
            WHERE c.timestamp IS NOT NULL {category_filter}
            RETURN c.text AS text,
                   c.category AS category,
                   c.timestamp AS timestamp,
                   c.confidence AS confidence
            ORDER BY c.timestamp DESC
            LIMIT $limit
            """

            result = await self.execute_query(query, params, readonly=True)

            # Convert result to list of dicts
            critiques = []
            for record in result:
                critiques.append(
                    {
                        "text": record[0] if len(record) > 0 else "",
                        "category": record[1] if len(record) > 1 else "unknown",
                        "timestamp": record[2] if len(record) > 2 else "",
                        "confidence": record[3] if len(record) > 3 else 0.0,
                    }
                )

            logger.info(
                f"Retrieved {len(critiques)} critiques for user {user_id}"
                + (f" (category: {category})" if category else "")
            )

            return critiques

        except Exception as e:
            logger.error(f"Failed to retrieve critiques for user {user_id}: {str(e)}")
            return []

    async def get_user_constraints(
        self, user_id: str, active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Retrieve user profile constraints (preferences, rules, boundaries).

        Used by reflection_node and orchestrator to ensure responses
        comply with user-specific requirements.

        Args:
            user_id: User identifier
            active_only: If True, only return active constraints (default: True)

        Returns:
            List of constraint dictionaries with text, type, profile

        Example:
            constraints = await manager.get_user_constraints('EA', active_only=True)
        """
        try:
            # Build active filter
            active_filter = "AND c.active = true" if active_only else ""
            params = {"user_id": user_id}

            # OpenCypher query to retrieve constraints
            query = f"""
            MATCH (c:Constraint)
            WHERE c.profile = $user_id {active_filter}
            RETURN c.text AS text,
                   c.type AS type,
                   c.profile AS profile,
                   c.active AS active
            ORDER BY c.created_at DESC
            """

            result = await self.execute_query(query, params, readonly=True)

            # Convert result to list of dicts
            constraints = []
            for record in result:
                constraints.append(
                    {
                        "text": record[0] if len(record) > 0 else "",
                        "type": record[1] if len(record) > 1 else "general",
                        "profile": record[2] if len(record) > 2 else user_id,
                        "active": record[3] if len(record) > 3 else True,
                    }
                )

            logger.info(
                f"Retrieved {len(constraints)} constraints for user {user_id}"
                + (" (active only)" if active_only else "")
            )

            return constraints

        except Exception as e:
            logger.error(f"Failed to retrieve constraints for user {user_id}: {str(e)}")
            return []

    async def get_user_knowledge_triples(
        self, user_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve knowledge graph triples associated with a user.

        Used by stub_retrieve_memory to provide structured knowledge context
        for the orchestrator's routing decisions.

        Args:
            user_id: User identifier
            limit: Maximum number of triples to retrieve (default: 10)

        Returns:
            List of triple dictionaries with subject, predicate, object, confidence

        Example:
            triples = await manager.get_user_knowledge_triples('EA', limit=10)
        """
        try:
            params = {"user_id": user_id, "limit": limit}

            # OpenCypher query to retrieve user's knowledge relationships
            query = """
            MATCH (u:User {id: $user_id})-[:KNOWS_ABOUT]->(e1:Entity)-[r]->(e2:Entity)
            RETURN e1.name AS subject,
                   type(r) AS predicate,
                   e2.name AS object,
                   r.confidence AS confidence,
                   r.timestamp AS timestamp
            ORDER BY r.timestamp DESC
            LIMIT $limit
            """

            result = await self.execute_query(query, params, readonly=True)

            # Convert result to list of dicts
            triples = []
            for record in result:
                triples.append(
                    {
                        "subject": record[0] if len(record) > 0 else "",
                        "predicate": record[1] if len(record) > 1 else "RELATED_TO",
                        "object": record[2] if len(record) > 2 else "",
                        "confidence": record[3] if len(record) > 3 else 0.0,
                        "timestamp": record[4] if len(record) > 4 else "",
                    }
                )

            logger.info(
                f"Retrieved {len(triples)} knowledge triples for user {user_id}"
            )

            return triples

        except Exception as e:
            logger.error(
                f"Failed to retrieve knowledge triples for user {user_id}: {str(e)}"
            )
            return []

    async def search_entities_by_keyword(
        self, keyword: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for entities in the knowledge graph by keyword.

        Used for context-aware retrieval during query processing.

        Args:
            keyword: Search term to match against entity names
            limit: Maximum number of entities to return (default: 5)

        Returns:
            List of entity dictionaries with name, type, related_count

        Example:
            entities = await manager.search_entities_by_keyword('Python', limit=5)
        """
        try:
            params = {"keyword": keyword.lower(), "limit": limit}

            # OpenCypher query with case-insensitive substring matching
            query = """
            MATCH (e:Entity)
            WHERE toLower(e.name) CONTAINS $keyword
            OPTIONAL MATCH (e)-[r]-()
            RETURN e.name AS name,
                   e.type AS type,
                   count(r) AS related_count
            ORDER BY related_count DESC
            LIMIT $limit
            """

            result = await self.execute_query(query, params, readonly=True)

            # Convert result to list of dicts
            entities = []
            for record in result:
                entities.append(
                    {
                        "name": record[0] if len(record) > 0 else "",
                        "type": record[1] if len(record) > 1 else "unknown",
                        "related_count": record[2] if len(record) > 2 else 0,
                    }
                )

            logger.info(f"Found {len(entities)} entities matching keyword '{keyword}'")

            return entities

        except Exception as e:
            logger.error(
                f"Failed to search entities with keyword '{keyword}': {str(e)}"
            )
            return []
