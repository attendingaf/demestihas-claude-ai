#!/bin/bash

echo "Testing Smart MCP Memory HTTP API"
echo "=================================="

# Test 1: Health check
echo -e "\n1. Health Check:"
curl -s http://localhost:7777/health | jq .

# Test 2: Get context
echo -e "\n2. Get Context (searching for 'configuration'):"
curl -s "http://localhost:7777/context?q=configuration&limit=5" | jq .

# Test 3: Store a test memory
echo -e "\n3. Store Memory:"
curl -s -X POST http://localhost:7777/store \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Test memory from HTTP API - MCP server running successfully",
    "type": "note",
    "importance": "medium"
  }' | jq .

# Test 4: Analyze text
echo -e "\n4. Analyze Text:"
curl -s -X POST http://localhost:7777/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Successfully deployed Smart MCP Memory Server with 9 tools",
    "focus_areas": ["solution", "configuration"]
  }' | jq .

# Test 5: Augment prompt
echo -e "\n5. Augment Prompt:"
curl -s -X POST http://localhost:7777/augment \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "How do I configure MCP servers?",
    "max_context": 3
  }' | jq .

echo -e "\n=================================="
echo "API Testing Complete"
