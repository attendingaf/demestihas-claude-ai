#!/bin/bash

echo "HTTP API Endpoint Testing"
echo "========================="

# Health check
echo -e "\n1. Health Check:"
curl -s http://localhost:7777/health | python3 -m json.tool

# Store memory
echo -e "\n2. Store Memory:"
curl -s -X POST http://localhost:7777/store \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Chapter 1 validation complete - all systems operational",
    "type": "configuration",
    "importance": "high"
  }' | python3 -m json.tool

# Get context (should still fail due to retrieval issue)
echo -e "\n3. Get Context:"
curl -s "http://localhost:7777/context?q=Chapter&limit=5" | python3 -m json.tool

echo -e "\n========================="
echo "Testing complete"
