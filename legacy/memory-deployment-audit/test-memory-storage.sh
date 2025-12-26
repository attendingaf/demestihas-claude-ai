#!/bin/bash

echo "=== CORRECTED MEMORY STORAGE TEST ==="

# Get token
TOKEN=$(curl -s -X POST "http://localhost:8000/auth/token?user_id=mene" | \
  python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

echo "Token obtained: ${TOKEN:0:20}..."
echo ""

# Test 1: Store a memory with correct query parameters
echo "=== Test 1: Store test memory ==="
CONTENT="Medical reminder - check blood pressure daily at 8am"
RESULT=$(curl -s -X POST "http://localhost:8000/memory/store?content=$(echo -n "$CONTENT" | python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.stdin.read()))')&memory_type=private" \
  -H "Authorization: Bearer $TOKEN")

echo "$RESULT" | python3 -m json.tool
echo ""

# Test 2: Store another memory
echo "=== Test 2: Store another memory ==="
CONTENT2="Personal note - favorite restaurant is Luigi's on Main Street"
RESULT2=$(curl -s -X POST "http://localhost:8000/memory/store?content=$(echo -n "$CONTENT2" | python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.stdin.read()))')&memory_type=private" \
  -H "Authorization: Bearer $TOKEN")

echo "$RESULT2" | python3 -m json.tool
echo ""

# Test 3: Retrieve all memories
echo "=== Test 3: Retrieve all memories ==="
sleep 2
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/memory/list?memory_type=all&limit=100" | python3 -m json.tool > retrieved-memories.json

MEMORY_COUNT=$(cat retrieved-memories.json | python3 -c "import json,sys; print(len(json.load(sys.stdin).get('memories', [])))")
echo "Total memories found: $MEMORY_COUNT"

if [ "$MEMORY_COUNT" -gt 0 ]; then
    echo ""
    echo "All memories:"
    cat retrieved-memories.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for i, mem in enumerate(data.get('memories', []), 1):
    print(f'{i}. [{mem.get(\"memory_type\", \"unknown\")}] {mem.get(\"content\", \"\")}')
    print(f'   ID: {mem.get(\"id\", \"\")}')
    print(f'   Created: {mem.get(\"created_at\", \"\")}')
    print()
"
fi
echo ""

# Test 4: Get memory stats
echo "=== Test 4: Memory stats ==="
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/memory/stats" | python3 -m json.tool
echo ""

