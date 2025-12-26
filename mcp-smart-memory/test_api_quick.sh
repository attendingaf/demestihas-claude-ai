#!/bin/bash

echo "Testing Smart MCP Memory HTTP API"
echo "=================================="

# Test 1: Health check
echo -e "\n1. Health Check:"
curl -s http://localhost:7777/health || echo "Failed to connect"

# Test 2: Store a test memory
echo -e "\n\n2. Store Test Memory:"
curl -s -X POST http://localhost:7777/store \
  -H "Content-Type: application/json" \
  -d '{
    "content": "API Server successfully started and tested",
    "type": "configuration",
    "importance": "high",
    "metadata": {"test": true, "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"} 
  }' || echo "Failed to store"

# Test 3: Get context
echo -e "\n\n3. Get Context:"
curl -s "http://localhost:7777/context?q=API&limit=5" || echo "Failed to get context"

echo -e "\n=================================="
echo "API Testing Complete"
