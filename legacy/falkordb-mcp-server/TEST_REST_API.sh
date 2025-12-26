#!/bin/bash

# API Key generated during setup
API_KEY="abe6f599225af86c049b72a3d1cc81dc"
# BASE_URL="http://localhost:8050" # Local
BASE_URL="https://claude.beltlineconsulting.co" # Production

echo "Testing against $BASE_URL with API Key: $API_KEY"

# 1. Health check
echo "1. Health check..."
curl -s "$BASE_URL/health"
echo ""

# 2. Create a test node
echo "2. Create a test node..."
curl -s -X POST "$BASE_URL/graph/nodes" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"label": "Test", "properties": {"name": "test_node", "created": "2024-11-28", "source": "API Test"}}'
echo ""

# 3. Query for the node
echo "3. Query for the node..."
curl -s -X POST "$BASE_URL/graph/query" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"cypher": "MATCH (n:Test) RETURN n"}'
echo ""

# 4. Search endpoint
echo "4. Search endpoint..."
curl -s "$BASE_URL/graph/search?label=Test&property=name&value=test_node" \
  -H "Authorization: Bearer $API_KEY"
echo ""

# 5. Create two nodes for relationship test
echo "5. Creating nodes for relationship test..."
curl -s -X POST "$BASE_URL/graph/nodes" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"label": "SourceNode", "properties": {"name": "A"}}'
echo ""
curl -s -X POST "$BASE_URL/graph/nodes" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"label": "TargetNode", "properties": {"name": "B"}}'
echo ""

# 6. Create Relationship
echo "6. Create Relationship..."
curl -s -X POST "$BASE_URL/graph/relationships" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "from_label": "SourceNode",
    "from_match": {"name": "A"},
    "to_label": "TargetNode",
    "to_match": {"name": "B"},
    "relationship_type": "CONNECTS_TO",
    "properties": {"weight": "heavy"}
  }'
echo ""

# 7. Get Node with Relationships
echo "7. Get Node with Relationships..."
curl -s "$BASE_URL/graph/node/SourceNode/name/A/relationships" \
  -H "Authorization: Bearer $API_KEY"
echo ""

# 8. Cleanup
echo "8. Cleanup..."
curl -s -X POST "$BASE_URL/graph/query" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"cypher": "MATCH (n:Test) DETACH DELETE n"}'
curl -s -X POST "$BASE_URL/graph/query" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"cypher": "MATCH (n:SourceNode) DETACH DELETE n"}'
curl -s -X POST "$BASE_URL/graph/query" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"cypher": "MATCH (n:TargetNode) DETACH DELETE n"}'
echo ""

echo "Done."
