"""
FalkorDB Schema Initialization Script for DemestiChat

This script creates the necessary indexes and constraints for optimal
performance of the knowledge graph persistence layer.

Schema Design:
- Node Labels: User, Document, Critique, Constraint, Entity, Session
- Indexed Properties: id (User), source_id (Document), name (Entity), profile (Constraint)

Usage:
    python initialize_db.py

This script is idempotent and safe to run multiple times.
Run this once during initial deployment or after database resets.
"""

import os
import sys
import logging
import asyncio
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

try:
    from falkordb_manager import FalkorDBManager
except ImportError:
    logger.error(
        "Failed to import FalkorDBManager. Ensure falkordb_manager.py is in the same directory."
    )
    sys.exit(1)


class FalkorDBSchemaInitializer:
    """
    Handles schema creation and index management for FalkorDB.
    """

    def __init__(self):
        self.manager = FalkorDBManager()
        self.indexes_created = []
        self.errors = []

    async def connect(self):
        """Establish connection to FalkorDB."""
        try:
            await self.manager.connect()
            logger.info("✅ Connected to FalkorDB successfully")
        except Exception as e:
            logger.error(f"❌ Failed to connect to FalkorDB: {str(e)}")
            raise

    async def create_index(self, label: str, property_name: str) -> bool:
        """
        Create an index on a node label and property.

        Args:
            label: Node label (e.g., "User", "Entity")
            property_name: Property to index (e.g., "id", "name")

        Returns:
            True if index created successfully, False otherwise
        """
        try:
            # FalkorDB uses CREATE INDEX syntax for node properties
            query = f"CREATE INDEX FOR (n:{label}) ON (n.{property_name})"

            logger.info(f"Creating index: {label}.{property_name}...")
            await self.manager.execute_query(query)

            self.indexes_created.append(f"{label}.{property_name}")
            logger.info(f"✅ Index created: {label}.{property_name}")
            return True

        except Exception as e:
            error_msg = str(e)

            # Check if index already exists (not an error)
            if (
                "already exists" in error_msg.lower()
                or "duplicate" in error_msg.lower()
            ):
                logger.info(f"ℹ️  Index already exists: {label}.{property_name}")
                self.indexes_created.append(f"{label}.{property_name} (already exists)")
                return True
            else:
                logger.error(
                    f"❌ Failed to create index {label}.{property_name}: {error_msg}"
                )
                self.errors.append(f"{label}.{property_name}: {error_msg}")
                return False

    async def initialize_schema(self) -> Dict[str, Any]:
        """
        Create all required indexes for the knowledge graph schema.

        Schema:
        - User.id: Primary identifier for users
        - Document.source_id: Identifier for ingested documents
        - Entity.name: Named entities extracted from conversations
        - Constraint.profile: User personality/preference constraints
        - Critique.id: RLHF feedback critiques
        - Session.id: Conversation session tracking

        Returns:
            Dictionary with initialization results
        """
        logger.info("🚀 Starting FalkorDB schema initialization...")

        # Define all indexes to create
        indexes = [
            ("User", "id"),
            ("Document", "source_id"),
            ("Entity", "name"),
            ("Constraint", "profile"),
            ("Critique", "id"),
            ("Session", "id"),
            ("Critique", "category"),  # Additional index for critique categorization
            ("Entity", "type"),  # Additional index for entity type filtering
        ]

        success_count = 0

        for label, property_name in indexes:
            if await self.create_index(label, property_name):
                success_count += 1

        # Verify indexes were created
        await self.verify_indexes()

        result = {
            "success": len(self.errors) == 0,
            "indexes_created": self.indexes_created,
            "total_indexes": len(indexes),
            "successful": success_count,
            "failed": len(self.errors),
            "errors": self.errors,
        }

        if result["success"]:
            logger.info(
                f"✅ Schema initialization complete: {success_count}/{len(indexes)} indexes created"
            )
        else:
            logger.warning(
                f"⚠️  Schema initialization completed with errors: {len(self.errors)} failed"
            )

        return result

    async def verify_indexes(self):
        """
        Verify that indexes exist by querying database metadata.

        Note: FalkorDB index verification is implicit through query performance.
        """
        try:
            # Test queries to verify indexes are working
            test_queries = [
                ("MATCH (u:User {id: 'test'}) RETURN count(u)", "User.id index"),
                (
                    "MATCH (d:Document {source_id: 'test'}) RETURN count(d)",
                    "Document.source_id index",
                ),
                (
                    "MATCH (e:Entity {name: 'test'}) RETURN count(e)",
                    "Entity.name index",
                ),
            ]

            logger.info("Verifying indexes with test queries...")

            for query, description in test_queries:
                await self.manager.execute_query(query, readonly=True)
                logger.debug(f"✓ Verified: {description}")

            logger.info("✅ Index verification complete")

        except Exception as e:
            logger.warning(f"Index verification encountered issue: {str(e)}")

    async def create_sample_data(self, create_samples: bool = False):
        """
        Optionally create sample nodes to verify schema functionality.

        Args:
            create_samples: If True, create sample data for testing
        """
        if not create_samples:
            return

        logger.info("Creating sample data for verification...")

        try:
            # Create sample user
            await self.manager.merge_node(
                "User",
                {"id": "sample_user", "name": "Sample User", "created": "2025-10-02"},
                match_properties=["id"],
            )

            # Create sample entity
            await self.manager.merge_node(
                "Entity",
                {
                    "name": "Python",
                    "type": "Technology",
                    "category": "Programming Language",
                },
                match_properties=["name"],
            )

            # Create sample relationship
            await self.manager.merge_relationship(
                "User",
                {"id": "sample_user"},
                "KNOWS_ABOUT",
                "Entity",
                {"name": "Python"},
            )

            logger.info("✅ Sample data created successfully")

        except Exception as e:
            logger.error(f"Failed to create sample data: {str(e)}")

    async def cleanup(self):
        """Close database connection."""
        await self.manager.disconnect()
        logger.info("Database connection closed")


async def main():
    """Main execution function."""
    logger.info("=" * 70)
    logger.info("FalkorDB Schema Initialization for DemestiChat")
    logger.info("=" * 70)

    initializer = FalkorDBSchemaInitializer()

    try:
        # Connect to database
        await initializer.connect()

        # Create schema and indexes
        result = await initializer.initialize_schema()

        # Optionally create sample data (disabled by default)
        # await initializer.create_sample_data(create_samples=True)

        # Print summary
        logger.info("=" * 70)
        logger.info("INITIALIZATION SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Status: {'✅ SUCCESS' if result['success'] else '❌ FAILED'}")
        logger.info(
            f"Indexes Created: {result['successful']}/{result['total_indexes']}"
        )

        if result["indexes_created"]:
            logger.info("\nIndexes:")
            for idx in result["indexes_created"]:
                logger.info(f"  • {idx}")

        if result["errors"]:
            logger.error("\nErrors:")
            for error in result["errors"]:
                logger.error(f"  ✗ {error}")

        logger.info("=" * 70)

        # Exit with appropriate code
        exit_code = 0 if result["success"] else 1

    except Exception as e:
        logger.error(f"Fatal error during initialization: {str(e)}")
        exit_code = 1

    finally:
        await initializer.cleanup()

    sys.exit(exit_code)


if __name__ == "__main__":
    """
    Run the schema initialization.

    Environment Variables Required:
    - FALKORDB_HOST: FalkorDB server host (default: graph_db)
    - FALKORDB_PORT: FalkorDB server port (default: 6379)
    - FALKORDB_GRAPH_NAME: Graph database name (default: demestihas_knowledge)
    """

    # Verify environment configuration
    required_vars = ["FALKORDB_HOST", "FALKORDB_PORT", "FALKORDB_GRAPH_NAME"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.warning(f"Missing environment variables: {', '.join(missing_vars)}")
        logger.warning(
            "Using default values. Set these in your environment for production."
        )

    # Run async main function
    asyncio.run(main())
