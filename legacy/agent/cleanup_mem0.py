#!/usr/bin/env python3
"""
Mem0 Semantic Memory Purge Script

This script removes stale conversation history and semantic memory from Mem0
to prevent contaminated context from being re-injected into agent reasoning.

Mem0 stores vector embeddings of conversation history in Qdrant, which can
persist incorrect information across service restarts.

Usage:
    python cleanup_mem0.py --user USER_ID [--dry-run]
    python cleanup_mem0.py --all [--dry-run]

Examples:
    # Remove all memories for a specific user
    python cleanup_mem0.py --user default_user

    # Preview what would be deleted
    python cleanup_mem0.py --user test_user --dry-run

    # Remove all memories (requires confirmation)
    python cleanup_mem0.py --all
"""

import os
import sys
import argparse
import requests
from typing import Optional, Dict, Any
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

MEM0_SERVICE_URL = os.getenv("MEM0_SERVICE_URL", "http://mem0:8080")
MEM0_MEMORY_ENDPOINT = f"{MEM0_SERVICE_URL}/memory"


# ============================================================================
# MEM0 API FUNCTIONS
# ============================================================================


def get_user_memories(user_id: str) -> Dict[str, Any]:
    """
    Retrieves all memories for a specific user from Mem0.

    Args:
        user_id: User identifier

    Returns:
        Dictionary with memory data
    """
    try:
        response = requests.post(
            MEM0_MEMORY_ENDPOINT,
            json={
                "user_id": user_id,
                "action": "retrieve",
                "limit": 100,  # Get up to 100 memories
            },
            timeout=15,
        )

        if response.status_code == 200:
            return response.json()
        else:
            print(f"⚠️  Warning: Mem0 returned status {response.status_code}")
            return {"error": response.text, "status_code": response.status_code}

    except Exception as e:
        print(f"❌ Error retrieving memories: {str(e)}")
        return {"error": str(e)}


def delete_user_memories(user_id: str, dry_run: bool = False) -> Dict[str, Any]:
    """
    Deletes all memories for a specific user from Mem0.

    This uses the Mem0 service API to delete all semantic memories
    and conversation history stored in Qdrant.

    Args:
        user_id: User identifier
        dry_run: If True, only preview without deleting

    Returns:
        Dictionary with deletion results
    """
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Connecting to Mem0 service...")
    print(f"  Endpoint: {MEM0_SERVICE_URL}")
    print(f"  User: {user_id}")

    # First, retrieve current memories to show what will be deleted
    print(
        f"\n{'[DRY RUN] ' if dry_run else ''}Retrieving current memories for user '{user_id}'..."
    )

    memories_data = get_user_memories(user_id)

    if "error" in memories_data:
        print(f"❌ Failed to retrieve memories: {memories_data['error']}")
        return memories_data

    # Extract memory count
    data = memories_data.get("data", {})
    recent_messages = data.get("recent_messages", [])
    user_preferences = data.get("user_preferences", {})

    print(f"\nMemories found for user '{user_id}':")
    print(f"  - Recent messages: {len(recent_messages)}")
    print(f"  - User preferences: {len(user_preferences)} keys")

    if len(recent_messages) > 0:
        print(f"\nSample messages (first 3):")
        for i, msg in enumerate(recent_messages[:3], 1):
            preview = str(msg)[:100]
            print(f"  {i}. {preview}...")

    total_items = len(recent_messages) + len(user_preferences)

    if total_items == 0:
        print(f"\n✅ No memories found for user '{user_id}'")
        return {"memories_deleted": 0, "user_id": user_id, "dry_run": dry_run}

    if dry_run:
        print("\n[DRY RUN] No data was deleted. Remove --dry-run to execute deletion.")
        return {
            "memories_found": total_items,
            "memories_deleted": 0,
            "user_id": user_id,
            "dry_run": True,
        }

    # Confirm deletion
    print(
        f"\n⚠️  WARNING: About to DELETE {total_items} memory items for user '{user_id}'!"
    )
    confirmation = input("Type 'DELETE' to confirm: ")

    if confirmation != "DELETE":
        print("❌ Deletion cancelled by user.")
        return {"memories_deleted": 0, "cancelled": True}

    # Execute deletion via Mem0 API
    print("\n🗑️  Executing deletion...")

    try:
        # The Mem0 service may not have a direct "delete_all" endpoint
        # Try using a delete action with the user_id
        response = requests.post(
            MEM0_MEMORY_ENDPOINT,
            json={
                "user_id": user_id,
                "action": "delete_all",  # Assuming this action exists
            },
            timeout=15,
        )

        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ MEM0 PURGE COMPLETE:")
            print(f"   User: {user_id}")
            print(f"   Memories deleted: {total_items}")
            print(f"   Response: {result}")

            return {
                "memories_deleted": total_items,
                "user_id": user_id,
                "dry_run": False,
                "timestamp": datetime.utcnow().isoformat(),
                "response": result,
            }
        else:
            print(f"⚠️  Warning: Mem0 returned status {response.status_code}")
            print(f"   Response: {response.text}")

            # Alternative: Use Qdrant directly if available
            print(
                "\n💡 TIP: If the Mem0 service doesn't support delete_all, you may need to:"
            )
            print("   1. Connect directly to Qdrant (if exposed)")
            print("   2. Delete the user's collection manually")
            print("   3. Restart the Mem0 service to clear in-memory cache")

            return {
                "error": "Mem0 delete_all action not supported or failed",
                "status_code": response.status_code,
                "response": response.text,
            }

    except Exception as e:
        print(f"\n❌ ERROR during Mem0 cleanup: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"error": str(e)}


def delete_all_memories(dry_run: bool = False) -> Dict[str, Any]:
    """
    Deletes ALL memories from Mem0 for all users.

    ⚠️  DANGEROUS - USE WITH CAUTION! ⚠️

    Args:
        dry_run: If True, only preview without deleting

    Returns:
        Dictionary with deletion results
    """
    print(f"\n{'[DRY RUN] ' if dry_run else ''}⚠️  DANGER ZONE: PURGE ALL MEMORIES ⚠️")
    print(f"  Endpoint: {MEM0_SERVICE_URL}")

    print("\n⚠️  This will delete ALL semantic memories for ALL users!")
    print("⚠️  This includes conversation history, preferences, and context!")

    if dry_run:
        print("\n[DRY RUN] No data was deleted. Remove --dry-run to execute deletion.")
        return {
            "memories_deleted": 0,
            "dry_run": True,
            "note": "Use Qdrant UI or API to get actual counts",
        }

    # Confirm deletion with extra safety
    print(f"\n⚠️⚠️⚠️  EXTREME WARNING  ⚠️⚠️⚠️")
    print("You are about to DELETE ALL MEMORIES for ALL USERS!")
    print("This action CANNOT be undone!")
    print("\nType 'DELETE ALL MEMORIES' to confirm: ")
    confirmation = input()

    if confirmation != "DELETE ALL MEMORIES":
        print("❌ Deletion cancelled by user.")
        return {"memories_deleted": 0, "cancelled": True}

    print("\n🗑️  Executing full memory purge...")
    print("\n💡 NOTE: Mem0 service may not support full purge via API.")
    print("   You may need to manually:")
    print("   1. Stop the Mem0 service")
    print("   2. Clear the Qdrant data directory")
    print("   3. Restart Mem0 service")
    print(
        "\nAlternatively, use: docker-compose down mem0 && docker volume rm demestihas_qdrant_data"
    )

    return {
        "memories_deleted": 0,
        "manual_action_required": True,
        "instructions": [
            "docker-compose down mem0",
            "docker volume rm <qdrant_volume_name>",
            "docker-compose up -d mem0",
        ],
    }


# ============================================================================
# ALTERNATIVE: Direct Qdrant Access (if Mem0 API doesn't support deletion)
# ============================================================================


def delete_via_qdrant(
    user_id: Optional[str] = None, dry_run: bool = False
) -> Dict[str, Any]:
    """
    Alternative deletion method using direct Qdrant API access.

    This bypasses the Mem0 service and deletes directly from Qdrant.
    Only use if Mem0 API doesn't support deletion.

    Args:
        user_id: User identifier (None = delete all)
        dry_run: If True, only preview without deleting

    Returns:
        Dictionary with deletion results
    """
    qdrant_host = os.getenv("QDRANT_HOST", "qdrant")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
    collection_name = os.getenv("MEM0_COLLECTION", "demestihas_memories")

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Using direct Qdrant API access...")
    print(f"  Host: {qdrant_host}:{qdrant_port}")
    print(f"  Collection: {collection_name}")

    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        client = QdrantClient(host=qdrant_host, port=qdrant_port)

        # Get collection info
        collection_info = client.get_collection(collection_name)
        total_points = collection_info.points_count

        print(f"\nCollection info:")
        print(f"  Total points: {total_points}")

        if dry_run:
            print(
                "\n[DRY RUN] No data was deleted. Remove --dry-run to execute deletion."
            )
            return {"points_found": total_points, "points_deleted": 0, "dry_run": True}

        if user_id:
            # Delete specific user's points
            print(f"\nDeleting points for user: {user_id}...")

            # Assuming user_id is stored as metadata field
            filter_condition = Filter(
                must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
            )

            result = client.delete(
                collection_name=collection_name, points_selector=filter_condition
            )

            print(f"✅ Deleted points for user '{user_id}'")
            return {
                "points_deleted": "unknown",  # Qdrant doesn't return count
                "user_id": user_id,
                "operation": "delete_by_filter",
            }
        else:
            # Delete entire collection
            print(f"\n⚠️  Deleting entire collection '{collection_name}'...")
            confirmation = input("Type 'DELETE COLLECTION' to confirm: ")

            if confirmation != "DELETE COLLECTION":
                print("❌ Deletion cancelled.")
                return {"cancelled": True}

            client.delete_collection(collection_name)

            print(f"✅ Collection '{collection_name}' deleted")
            print(f"   You may need to restart Mem0 service to recreate the collection")

            return {
                "collection_deleted": True,
                "collection_name": collection_name,
                "points_deleted": total_points,
            }

    except ImportError:
        print("❌ qdrant-client not installed. Install with: pip install qdrant-client")
        return {"error": "qdrant-client not available"}
    except Exception as e:
        print(f"❌ Error accessing Qdrant: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"error": str(e)}


# ============================================================================
# CLI INTERFACE
# ============================================================================


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Mem0 Semantic Memory Purge Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Remove all memories for a specific user
  python cleanup_mem0.py --user default_user

  # Preview what would be deleted
  python cleanup_mem0.py --user test_user --dry-run

  # DANGER: Purge all memories (requires confirmation)
  python cleanup_mem0.py --all

  # Use direct Qdrant access (if Mem0 API doesn't support deletion)
  python cleanup_mem0.py --user test_user --direct-qdrant
        """,
    )

    parser.add_argument("--user", type=str, help="Purge all memories for this user ID")

    parser.add_argument(
        "--all",
        action="store_true",
        help="Purge ALL memories for all users (DANGEROUS!)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be deleted without actually deleting",
    )

    parser.add_argument(
        "--direct-qdrant",
        action="store_true",
        help="Use direct Qdrant API instead of Mem0 service (fallback method)",
    )

    args = parser.parse_args()

    # Validate arguments
    if not (args.user or args.all):
        parser.error("Must specify one of: --user or --all")

    if args.user and args.all:
        parser.error("Cannot specify both --user and --all")

    # Execute appropriate purge operation
    if args.direct_qdrant:
        # Use direct Qdrant access
        user_id = args.user if args.user else None
        result = delete_via_qdrant(user_id=user_id, dry_run=args.dry_run)
    elif args.user:
        # Use Mem0 API for specific user
        result = delete_user_memories(args.user, dry_run=args.dry_run)
    elif args.all:
        # Purge all memories
        result = delete_all_memories(dry_run=args.dry_run)

    # Exit with appropriate code
    if "error" in result:
        sys.exit(1)
    elif result.get("cancelled"):
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
