#!/usr/bin/env python3
"""
Migration Script: Convert Existing FalkorDB Memories to Dual-Memory Architecture

This script migrates existing shared graph data to the new dual-memory system where:
- Private memories are isolated per user (default)
- System memories are shared family-wide

Run this script after deploying the dual-memory system.
"""

import asyncio
import sys
import logging
from datetime import datetime

# Add agent directory to path
sys.path.insert(0, "/root/agent")

from falkordb_manager import FalkorDBManager
from dual_memory_manager import FalkorDBDualMemory

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def migrate_falkordb_to_dual_memory():
    """
    Migrate existing FalkorDB graph to dual-memory architecture.

    Process:
    1. Connect to FalkorDB
    2. Retrieve all existing User-Entity relationships
    3. Classify each as private or system-wide
    4. Create new UserMemory or SystemMemory nodes
    5. Preserve old structure for backup
    """

    print("=" * 80)
    print("FalkorDB Dual-Memory Migration")
    print("=" * 80)
    print()

    # Initialize managers
    logger.info("Initializing FalkorDB connection...")
    falkordb = FalkorDBManager()

    try:
        await falkordb.connect()
        logger.info("✅ Connected to FalkorDB")
    except Exception as e:
        logger.error(f"❌ Failed to connect to FalkorDB: {e}")
        return False

    # Initialize dual-memory manager
    logger.info("Initializing dual-memory system...")
    dual_memory = FalkorDBDualMemory(falkordb)
    await dual_memory.ensure_system_user()
    logger.info("✅ Dual-memory system initialized")

    print()
    print("-" * 80)
    print("STEP 1: Analyzing Existing Data")
    print("-" * 80)

    # Get all existing relationships
    try:
        query = """
        MATCH (u:User)-[r:KNOWS_ABOUT]->(e:Entity)
        RETURN u.id as user_id, e.name as entity_name, e.created_by as created_by,
               e.created_at as created_at, properties(e) as props
        LIMIT 1000
        """

        results = await falkordb.execute_query(query, readonly=True)

        if not results:
            logger.warning("No existing relationships found to migrate")
            print("\n⚠️  No data to migrate")
            return True

        logger.info(f"Found {len(results)} relationships to analyze")
        print(f"\nFound {len(results)} existing memory relationships")

    except Exception as e:
        logger.error(f"Failed to query existing data: {e}")
        return False

    print()
    print("-" * 80)
    print("STEP 2: Migrating to Dual-Memory Structure")
    print("-" * 80)
    print()

    migrated_count = 0
    private_count = 0
    system_count = 0
    errors = []

    # Family member names for classification
    family_keywords = [
        "elena",
        "aris",
        "persy",
        "stelios",
        "franci",
        "cindy",
        "mene",
        "demestihas",
        "family",
        "everyone",
        "vacation",
        "school",
        "doctor",
    ]

    for row in results:
        user_id = row[0]
        entity_name = row[1]
        created_by = row[2]
        props = row[4] if len(row) > 4 else {}

        # Build content from entity
        content = str(entity_name)

        # Determine if this is family-wide or private
        content_lower = content.lower()
        is_family = any(keyword in content_lower for keyword in family_keywords)

        # Determine memory type
        if is_family:
            memory_type = "system"
            system_count += 1
            indicator = "📁 SHARED"
        else:
            memory_type = "private"
            private_count += 1
            indicator = "🔒 PRIVATE"

        try:
            # Store in dual-memory system
            result = await dual_memory.store_memory(
                user_id=user_id,
                subject=entity_name.split()[0] if entity_name else "Unknown",
                predicate="is"
                if len(entity_name.split()) <= 1
                else entity_name.split()[1],
                obj=" ".join(entity_name.split()[2:])
                if len(entity_name.split()) > 2
                else entity_name,
                memory_type=memory_type,
                metadata={
                    "migrated": True,
                    "original_entity": entity_name,
                    "created_by": created_by,
                    "migration_date": datetime.utcnow().isoformat(),
                },
                confidence=0.8,
            )

            if result["success"]:
                migrated_count += 1
                print(
                    f"  {indicator} {content[:60]}..."
                    + (" " * (70 - len(content[:60])))
                )
            else:
                errors.append(f"{entity_name}: {result.get('error')}")
                logger.warning(f"Failed to migrate: {entity_name}")

        except Exception as e:
            errors.append(f"{entity_name}: {str(e)}")
            logger.error(f"Migration error for {entity_name}: {e}")

    print()
    print("-" * 80)
    print("STEP 3: Verification")
    print("-" * 80)
    print()

    # Get statistics
    try:
        stats = await dual_memory.get_memory_stats()

        print(f"Migration Statistics:")
        print(f"  Total migrated: {migrated_count}")
        print(f"  Private memories: {private_count}")
        print(f"  System memories: {system_count}")
        print(f"  Errors: {len(errors)}")
        print()

        print(f"Final Memory Counts:")
        print(f"  Private: {stats.get('private_memories', 0)}")
        print(f"  System: {stats.get('system_memories', 0)}")
        print(f"  Total: {stats.get('total_memories', 0)}")
        print()

    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")

    if errors:
        print("Errors encountered:")
        for error in errors[:10]:  # Show first 10 errors
            print(f"  ❌ {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")
        print()

    print("=" * 80)
    if migrated_count > 0 and len(errors) == 0:
        print("✅ MIGRATION COMPLETE - All memories migrated successfully!")
    elif migrated_count > 0:
        print("⚠️  MIGRATION COMPLETE WITH ERRORS - Some memories failed to migrate")
    else:
        print("❌ MIGRATION FAILED - No memories were migrated")
    print("=" * 80)
    print()

    print("Next Steps:")
    print("1. Test the dual-memory system with: python3 /root/test_dual_memory.py")
    print("2. Verify privacy isolation between users")
    print("3. Confirm family-wide memories are accessible to all users")
    print()

    # Close connection
    await falkordb.disconnect()

    return migrated_count > 0


async def main():
    """Main migration entry point."""
    try:
        success = await migrate_falkordb_to_dual_memory()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Migration failed with exception: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
