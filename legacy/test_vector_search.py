#!/usr/bin/env python3
"""
Test vector search with various thresholds
"""

import openai
import redis

REDIS_HOST = "localhost"
REDIS_PORT = 6379
GRAPH_NAME = "memory_graph"
USER_ID = "mene"


def load_openai_key():
    with open("/root/falkordb-mcp-server/.env", "r") as f:
        for line in f:
            if line.startswith("OPENAI_API_KEY="):
                return line.strip().split("=", 1)[1]
    raise Exception("OPENAI_API_KEY not found")


def get_embedding(text):
    client = openai.OpenAI(api_key=load_openai_key())
    response = client.embeddings.create(input=text, model="text-embedding-3-small")
    return response.data[0].embedding


def test_search(r, query_text, threshold=0.0):
    """Test search with detailed output"""
    print(f"\nSearching for: '{query_text}' (threshold: {threshold})")
    print("-" * 60)

    query_vector = get_embedding(query_text)
    vector_str = "[" + ",".join(str(v) for v in query_vector) + "]"

    query = f"""
    MATCH (m:Memory)
    OPTIONAL MATCH (u:User {{user_id: '{USER_ID}'}})-[:OWNS]->(m)
    WHERE
        m.memory_type = 'system' OR
        (m.memory_type = 'private' AND u IS NOT NULL)
    WITH m, vec.euclideanDistance(m.vector, vecf32({vector_str})) AS distance
    WITH m, (1.0 / (1.0 + distance)) AS similarity
    WHERE similarity >= {threshold}
    RETURN m.text AS text,
           m.memory_type AS memory_type,
           similarity
    ORDER BY similarity DESC
    """

    result = r.execute_command("GRAPH.QUERY", GRAPH_NAME, query)
    results = result[1] if len(result) > 1 else []

    if results:
        for i, row in enumerate(results, 1):
            text = row[0].decode("utf-8") if isinstance(row[0], bytes) else row[0]
            sim_val = row[2]
            if isinstance(sim_val, bytes):
                sim_val = float(sim_val.decode("utf-8"))
            print(f"  {i}. [similarity: {sim_val:.6f}] {text}")
    else:
        print("  No results found")

    return results


def main():
    print("=" * 80)
    print("Vector Search Debug Test")
    print("=" * 80)

    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False)
    r.ping()

    # Test 1: Search with no threshold
    test_search(r, "doctor", threshold=0.0)

    # Test 2: Search for morning energy
    test_search(r, "morning energy", threshold=0.0)

    # Test 3: Search for work
    test_search(r, "work projects", threshold=0.0)

    # Test 4: Try exact match
    test_search(r, "My morning energy peaks between 9-11am", threshold=0.0)

    # Test 5: Try physician
    test_search(r, "physician", threshold=0.0)

    # Test 6: Try diabetes
    test_search(r, "diabetes", threshold=0.0)

    print("\n" + "=" * 80)
    print("Analysis:")
    print("If similarity scores are very low (< 0.5), check:")
    print("1. Vector dimensions match (1536 for text-embedding-3-small)")
    print("2. Vector normalization")
    print("3. Distance metric (cosine vs euclidean)")
    print("=" * 80)


if __name__ == "__main__":
    main()
