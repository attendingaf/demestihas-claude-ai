#!/usr/bin/env python3
"""
FalkorDB Data Purge Script

This script removes contaminated/stale data from the FalkorDB knowledge graph.
Specifically targets incorrect date facts and other test data that should not persist.

Usage:
    python cleanup_db.py [--all] [--pattern "February 5, 2025"] [--user USER_ID]

    --all: Purge ALL data (DANGEROUS - use with caution)
    --pattern: Purge nodes containing specific text pattern
    --user: Purge all data for a specific user
    --dry-run: Show what would be deleted without actually deleting

Examples:
    # Remove nodes with stale date
    python cleanup_db.py --pattern "February 5, 2025"

    # Remove all data for a test user
    python cleanup_db.py --user test_user_123

    # Preview what would be deleted
    python cleanup_db.py --pattern "February 5, 2025" --dry-run
"""

import os
import sys
import argparse
import asyncio
from typing import Optional
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from falkordb.asyncio import FalkorDB
except ImportError:
    print("ERROR: falkordb-py not installed. Install with: pip install falkordb")
    sys.exit(1)


# ============================================================================
# CONFIGURATION
# ============================================================================

FALKORDB_HOST = os.getenv("FALKORDB_HOST", "graph_db")
FALKORDB_PORT = int(os.getenv("FALKORDB_PORT", "6379"))
GRAPH_NAME = os.getenv("FALKORDB_GRAPH_NAME", "demestihas_knowledge")


# ============================================================================
# PURGE FUNCTIONS
# ============================================================================


async def purge_by_pattern(pattern: str, dry_run: bool = False) -> dict:
    """
    Purges nodes and relationships containing a specific text pattern.

    This is useful for removing contaminated data like incorrect dates.

    Args:
        pattern: Text pattern to search for in node properties
        dry_run: If True, only show what would be deleted

    Returns:
        Dictionary with deletion statistics
    """
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Connecting to FalkorDB...")
    print(f"  Host: {FALKORDB_HOST}:{FALKORDB_PORT}")
    print(f"  Graph: {GRAPH_NAME}")

    try:
        db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
        graph = db.select_graph(GRAPH_NAME)

        print(
            f"\n{'[DRY RUN] ' if dry_run else ''}Searching for nodes containing pattern: '{pattern}'..."
        )

        # First, query to see what we're about to delete
        preview_query = """
        MATCH (n)
        WHERE any(prop in keys(n) WHERE toString(n[prop]) CONTAINS $pattern)
        RETURN labels(n) AS labels, n AS node
        LIMIT 100
        """

        preview_result = await graph.query(preview_query, {"pattern": pattern})
        preview_nodes = (
            list(preview_result.result_set)
            if hasattr(preview_result, "result_set")
            else []
        )

        if not preview_nodes:
            print(f"✅ No nodes found containing pattern '{pattern}'")
            return {
                "nodes_deleted": 0,
                "relationships_deleted": 0,
                "pattern": pattern,
                "dry_run": dry_run,
            }

        print(
            f"\n{'[DRY RUN] ' if dry_run else ''}Found {len(preview_nodes)} nodes to delete:"
        )
        for i, node_data in enumerate(preview_nodes[:10], 1):  # Show first 10
            labels = node_data[0] if len(node_data) > 0 else []
            node = node_data[1] if len(node_data) > 1 else {}
            print(f"  {i}. {':'.join(labels) if labels else 'Node'}: {node}")

        if len(preview_nodes) > 10:
            print(f"  ... and {len(preview_nodes) - 10} more")

        if dry_run:
            print(
                "\n[DRY RUN] No data was deleted. Remove --dry-run to execute deletion."
            )
            return {
                "nodes_found": len(preview_nodes),
                "nodes_deleted": 0,
                "relationships_deleted": 0,
                "pattern": pattern,
                "dry_run": True,
            }

        # Confirm deletion
        print(
            f"\n⚠️  WARNING: About to DELETE {len(preview_nodes)} nodes and their relationships!"
        )
        confirmation = input("Type 'DELETE' to confirm: ")

        if confirmation != "DELETE":
            print("❌ Deletion cancelled by user.")
            return {"nodes_deleted": 0, "relationships_deleted": 0, "cancelled": True}

        # Execute deletion
        print("\n🗑️  Executing deletion...")
        purge_query = """
        MATCH (n)
        WHERE any(prop in keys(n) WHERE toString(n[prop]) CONTAINS $pattern)
        DETACH DELETE n
        """

        result = await graph.query(purge_query, {"pattern": pattern})

        nodes_deleted = result.nodes_deleted if hasattr(result, "nodes_deleted") else 0
        relationships_deleted = (
            result.relationships_deleted
            if hasattr(result, "relationships_deleted")
            else 0
        )

        print(f"\n✅ PURGE COMPLETE:")
        print(f"   Nodes deleted: {nodes_deleted}")
        print(f"   Relationships deleted: {relationships_deleted}")

        return {
            "nodes_deleted": nodes_deleted,
            "relationships_deleted": relationships_deleted,
            "pattern": pattern,
            "dry_run": False,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        print(f"\n❌ ERROR during FalkorDB cleanup: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"error": str(e)}


async def purge_user_data(user_id: str, dry_run: bool = False) -> dict:
    """
    Purges all data associated with a specific user.

    This removes:
    - The User node
    - All Entity nodes created by the user
    - All Critique nodes for the user
    - All Constraint nodes for the user
    - All relationships involving these nodes

    Args:
        user_id: User identifier to purge
        dry_run: If True, only show what would be deleted

    Returns:
        Dictionary with deletion statistics
    """
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Connecting to FalkorDB...")
    print(f"  Host: {FALKORDB_HOST}:{FALKORDB_PORT}")
    print(f"  Graph: {GRAPH_NAME}")

    try:
        db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
        graph = db.select_graph(GRAPH_NAME)

        print(
            f"\n{'[DRY RUN] ' if dry_run else ''}Searching for data associated with user: {user_id}..."
        )

        # Preview what will be deleted
        preview_queries = {
            "User node": "MATCH (u:User {id: $user_id}) RETURN count(u) AS count",
            "Critiques": "MATCH (u:User {id: $user_id})-[:RECEIVED_CRITIQUE]->(c:Critique) RETURN count(c) AS count",
            "Constraints": "MATCH (c:Constraint {profile: $user_id}) RETURN count(c) AS count",
            "Entities": "MATCH (e:Entity {created_by: $user_id}) RETURN count(e) AS count",
            "Knowledge relationships": "MATCH (u:User {id: $user_id})-[:KNOWS_ABOUT]->(e:Entity) RETURN count(e) AS count",
        }

        print(f"\nData to be deleted for user '{user_id}':")
        total_nodes = 0

        for label, query in preview_queries.items():
            result = await graph.query(query, {"user_id": user_id})
            count = (
                result.result_set[0][0]
                if hasattr(result, "result_set") and result.result_set
                else 0
            )
            print(f"  - {label}: {count}")
            total_nodes += count

        if total_nodes == 0:
            print(f"\n✅ No data found for user '{user_id}'")
            return {
                "nodes_deleted": 0,
                "relationships_deleted": 0,
                "user_id": user_id,
                "dry_run": dry_run,
            }

        if dry_run:
            print(
                "\n[DRY RUN] No data was deleted. Remove --dry-run to execute deletion."
            )
            return {
                "nodes_found": total_nodes,
                "nodes_deleted": 0,
                "relationships_deleted": 0,
                "user_id": user_id,
                "dry_run": True,
            }

        # Confirm deletion
        print(f"\n⚠️  WARNING: About to DELETE all data for user '{user_id}'!")
        confirmation = input("Type 'DELETE' to confirm: ")

        if confirmation != "DELETE":
            print("❌ Deletion cancelled by user.")
            return {"nodes_deleted": 0, "relationships_deleted": 0, "cancelled": True}

        # Execute deletion
        print("\n🗑️  Executing deletion...")

        purge_query = """
        MATCH (u:User {id: $user_id})
        OPTIONAL MATCH (u)-[:RECEIVED_CRITIQUE]->(c:Critique)
        OPTIONAL MATCH (constraint:Constraint {profile: $user_id})
        OPTIONAL MATCH (e:Entity {created_by: $user_id})
        OPTIONAL MATCH (u)-[:KNOWS_ABOUT]->(knowledge:Entity)
        DETACH DELETE u, c, constraint, e, knowledge
        """

        result = await graph.query(purge_query, {"user_id": user_id})

        nodes_deleted = result.nodes_deleted if hasattr(result, "nodes_deleted") else 0
        relationships_deleted = (
            result.relationships_deleted
            if hasattr(result, "relationships_deleted")
            else 0
        )

        print(f"\n✅ PURGE COMPLETE:")
        print(f"   Nodes deleted: {nodes_deleted}")
        print(f"   Relationships deleted: {relationships_deleted}")

        return {
            "nodes_deleted": nodes_deleted,
            "relationships_deleted": relationships_deleted,
            "user_id": user_id,
            "dry_run": False,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        print(f"\n❌ ERROR during FalkorDB cleanup: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"error": str(e)}


async def purge_all_data(dry_run: bool = False) -> dict:
    """
    Purges ALL data from the FalkorDB knowledge graph.

    ⚠️  EXTREMELY DANGEROUS - USE WITH CAUTION! ⚠️

    This will delete EVERYTHING in the graph.

    Args:
        dry_run: If True, only show statistics without deleting

    Returns:
        Dictionary with deletion statistics
    """
    print(f"\n{'[DRY RUN] ' if dry_run else ''}⚠️  DANGER ZONE: PURGE ALL DATA ⚠️")
    print(f"  Host: {FALKORDB_HOST}:{FALKORDB_PORT}")
    print(f"  Graph: {GRAPH_NAME}")

    try:
        db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
        graph = db.select_graph(GRAPH_NAME)

        # Get statistics
        stats_query = """
        MATCH (n)
        RETURN count(n) AS total_nodes,
               count(DISTINCT labels(n)) AS node_types
        """

        result = await graph.query(stats_query)
        stats = (
            result.result_set[0]
            if hasattr(result, "result_set") and result.result_set
            else [0, 0]
        )
        total_nodes = stats[0]
        node_types = stats[1]

        print(f"\nCurrent graph statistics:")
        print(f"  Total nodes: {total_nodes}")
        print(f"  Node types: {node_types}")

        if total_nodes == 0:
            print("\n✅ Graph is already empty.")
            return {"nodes_deleted": 0, "relationships_deleted": 0, "dry_run": dry_run}

        if dry_run:
            print(
                "\n[DRY RUN] No data was deleted. Remove --dry-run to execute deletion."
            )
            return {
                "nodes_found": total_nodes,
                "nodes_deleted": 0,
                "relationships_deleted": 0,
                "dry_run": True,
            }

        # Confirm deletion with extra safety
        print(f"\n⚠️⚠️⚠️  EXTREME WARNING  ⚠️⚠️⚠️")
        print(f"You are about to DELETE {total_nodes} nodes and ALL relationships!")
        print("This action CANNOT be undone!")
        print("\nType 'DELETE ALL DATA' to confirm: ")
        confirmation = input()

        if confirmation != "DELETE ALL DATA":
            print("❌ Deletion cancelled by user.")
            return {"nodes_deleted": 0, "relationships_deleted": 0, "cancelled": True}

        # Execute deletion
        print("\n🗑️  Executing full database purge...")
        purge_query = "MATCH (n) DETACH DELETE n"

        result = await graph.query(purge_query)

        nodes_deleted = result.nodes_deleted if hasattr(result, "nodes_deleted") else 0
        relationships_deleted = (
            result.relationships_deleted
            if hasattr(result, "relationships_deleted")
            else 0
        )

        print(f"\n✅ FULL PURGE COMPLETE:")
        print(f"   Nodes deleted: {nodes_deleted}")
        print(f"   Relationships deleted: {relationships_deleted}")
        print(f"   Graph is now empty.")

        return {
            "nodes_deleted": nodes_deleted,
            "relationships_deleted": relationships_deleted,
            "dry_run": False,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        print(f"\n❌ ERROR during FalkorDB cleanup: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"error": str(e)}


# ============================================================================
# CLI INTERFACE
# ============================================================================


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="FalkorDB Data Purge Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Remove nodes with stale date
  python cleanup_db.py --pattern "February 5, 2025"

  # Remove all data for a test user
  python cleanup_db.py --user test_user_123

  # Preview what would be deleted
  python cleanup_db.py --pattern "February 5, 2025" --dry-run

  # DANGER: Purge everything (requires confirmation)
  python cleanup_db.py --all
        """,
    )

    parser.add_argument(
        "--pattern", type=str, help="Purge nodes containing this text pattern"
    )

    parser.add_argument("--user", type=str, help="Purge all data for this user ID")

    parser.add_argument(
        "--all", action="store_true", help="Purge ALL data from the graph (DANGEROUS!)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be deleted without actually deleting",
    )

    args = parser.parse_args()

    # Validate arguments
    if not (args.pattern or args.user or args.all):
        parser.error("Must specify one of: --pattern, --user, or --all")

    if sum([bool(args.pattern), bool(args.user), args.all]) > 1:
        parser.error("Can only specify one purge operation at a time")

    # Execute appropriate purge operation
    if args.pattern:
        result = asyncio.run(purge_by_pattern(args.pattern, dry_run=args.dry_run))
    elif args.user:
        result = asyncio.run(purge_user_data(args.user, dry_run=args.dry_run))
    elif args.all:
        result = asyncio.run(purge_all_data(dry_run=args.dry_run))

    # Exit with appropriate code
    if "error" in result:
        sys.exit(1)
    elif result.get("cancelled"):
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
