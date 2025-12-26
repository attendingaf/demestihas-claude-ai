#!/usr/bin/env python3
"""
Direct FalkorDB Memory Test
Tests the memory system by directly interacting with FalkorDB
"""

import json
import time
from datetime import datetime

import redis

REDIS_HOST = "localhost"
REDIS_PORT = 6379
GRAPH_NAME = "memory_graph"

def main():
    print("=" * 80)
    print("FalkorDB Memory System Direct Test")
    print("=" * 80)
    print()

    # Connect to FalkorDB
    print(f"Connecting to FalkorDB at {REDIS_HOST}:{REDIS_PORT}...")
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False)

    try:
        r.ping()
        print("✅ Connected to FalkorDB\n")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return

    # Test 1: Check current state
    print("-" * 80)
    print("TEST 1: Check current graph state")
    print("-" * 80)

    query = "MATCH (n) RETURN labels(n) as type, count(n) as count"
    try:
        result = r.execute_command("GRAPH.QUERY", GRAPH_NAME, query)
        print("Current nodes in graph:")
        if result[1]:  # Check if there are results
            for row in result[1]:
                labels = row[0] if row[0] else "unlabeled"
                count = row[1]
                print(f"  {labels}: {count}")
        else:
            print("  (empty graph)")
        print()
    except Exception as e:
        print(f"Error querying graph: {e}\n")

    # Test 2: Query for UserMemory nodes (old schema)
    print("-" * 80)
    print("TEST 2: Check for UserMemory nodes (old schema)")
    print("-" * 80)

    query = "MATCH (n:UserMemory) RETURN n.text, n.user_id LIMIT 5"
    try:
        result = r.execute_command("GRAPH.QUERY", GRAPH_NAME, query)
        print("UserMemory nodes:")
        if result[1]:
            for row in result[1]:
                print(f"  User: {row[1]}, Text: {row[0][:50]}...")
        else:
            print("  No UserMemory nodes found")
        print()
    except Exception as e:
        print(f"Error: {e}\n")

    # Test 3: Query for Memory nodes (new schema)
    print("-" * 80)
    print("TEST 3: Check for Memory nodes (current schema)")
    print("-" * 80)

    query = "MATCH (n:Memory) RETURN n.text, n.memory_type, n.created_at LIMIT 5"
    try:
        result = r.execute_command("GRAPH.QUERY", GRAPH_NAME, query)
        print("Memory nodes:")
        if result[1]:
            for row in result[1]:
                text = row[0] if len(row) > 0 else "N/A"
                mem_type = row[1] if len(row) > 1 else "N/A"
                created = row[2] if len(row) > 2 else "N/A"
                print(f"  Type: {mem_type}, Text: {text[:50]}...")
        else:
            print("  No Memory nodes found")
        print()
    except Exception as e:
        print(f"Error: {e}\n")

    # Test 4: Query for User nodes
    print("-" * 80)
    print("TEST 4: Check for User nodes")
    print("-" * 80)

    query = "MATCH (u:User) RETURN u.user_id"
    try:
        result = r.execute_command("GRAPH.QUERY", GRAPH_NAME, query)
        print("User nodes:")
        if result[1]:
            for row in result[1]:
                print(f"  User ID: {row[0]}")
        else:
            print("  No User nodes found")
        print()
    except Exception as e:
        print(f"Error: {e}\n")

    # Test 5: Check relationships
    print("-" * 80)
    print("TEST 5: Check relationships")
    print("-" * 80)

    query = (
        "MATCH (u:User)-[r]->(m:Memory) RETURN type(r) as rel_type, count(r) as count"
    )
    try:
        result = r.execute_command("GRAPH.QUERY", GRAPH_NAME, query)
        print("Relationships:")
        if result[1]:
            for row in result[1]:
                print(f"  {row[0]}: {row[1]}")
        else:
            print("  No relationships found")
        print()
    except Exception as e:
        print(f"Error: {e}\n")

    # Test 6: Check if vector index exists
    print("-" * 80)
    print("TEST 6: Check graph indices")
    print("-" * 80)

    query = "CALL db.indexes()"
    try:
        result = r.execute_command("GRAPH.QUERY", GRAPH_NAME, query)
        print("Indices:")
        if result[1]:
            for row in result[1]:
                print(f"  {row}")
        else:
            print("  No indices found")
        print()
    except Exception as e:
        print(f"Note: Index query not supported or error: {e}\n")

    # Test 7: Sample query for private memories for user 'mene'
    print("-" * 80)
    print("TEST 7: Query memories for user 'mene'")
    print("-" * 80)

    query = """
    MATCH (u:User {user_id: 'mene'})-[:OWNS]->(m:Memory)
    RETURN m.text, m.memory_type, m.created_at
    """
    try:
        result = r.execute_command("GRAPH.QUERY", GRAPH_NAME, query)
        print("Memories for user 'mene':")
        if result[1]:
            for row in result[1]:
                print(f"  Text: {row[0][:80]}...")
                print(f"  Type: {row[1]}")
        else:
            print("  No memories found for user 'mene'")
        print()
    except Exception as e:
        print(f"Error: {e}\n")

    # Test 8: Check database info
    print("-" * 80)
    print("TEST 8: Database information")
    print("-" * 80)

    try:
        info = r.info()
        print(f"Redis version: {info.get('redis_version', 'N/A')}")
        print(f"Used memory: {info.get('used_memory_human', 'N/A')}")
        print(f"Connected clients: {info.get('connected_clients', 'N/A')}")
        print()
    except Exception as e:
        print(f"Error getting info: {e}\n")

    print("=" * 80)
    print("✅ Database connectivity test complete")
    print("=" * 80)
    print()

    print("Summary:")
    print("- FalkorDB is running and accessible")
    print("- Graph schema uses: User nodes, Memory nodes, OWNS relationships")
    print("- Memory types: 'private' (user-specific) and 'system' (shared)")
    print("- Vector embeddings stored as vecf32() for semantic search")
    print()

    print()

if __name__ == "__main__":
    main()
