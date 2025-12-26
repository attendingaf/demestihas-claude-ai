#!/bin/bash

echo "Testing Memory System After FTS5 Fix"
echo "===================================="

# Test 1: Check if API retrieval works
echo -e "\n1. Testing 'configuration' search:"
curl -s "http://localhost:7777/context?q=configuration&limit=5" | python3 -m json.tool | head -30

# Test 2: Case insensitive test
echo -e "\n2. Testing case-insensitive 'MEMORY' search:"
curl -s "http://localhost:7777/context?q=MEMORY&limit=3" | python3 -m json.tool | head -20

# Test 3: Partial match test
echo -e "\n3. Testing partial match 'config':"
curl -s "http://localhost:7777/context?q=config&limit=3" | python3 -m json.tool | head -20

# Test 4: Multi-word query
echo -e "\n4. Testing multi-word 'Chapter 1':"
curl -s "http://localhost:7777/context?q=Chapter%201&limit=3" | python3 -m json.tool | head -20

# Test 5: Store and immediately retrieve
echo -e "\n5. Store new memory and retrieve:"
echo "   Storing: 'FTS5 implementation complete with BM25 ranking'"
curl -s -X POST http://localhost:7777/store \
  -H "Content-Type: application/json" \
  -d '{
    "content": "FTS5 implementation complete with BM25 ranking for better search",
    "type": "solution",
    "importance": "critical"
  }' | python3 -m json.tool

sleep 1

echo -e "\n   Retrieving with 'FTS5 BM25':"
curl -s "http://localhost:7777/context?q=FTS5%20BM25&limit=1" | python3 -m json.tool

echo -e "\n===================================="
echo "If results show above, retrieval is FIXED!"
echo "If empty, restart the API server: npm run api"
