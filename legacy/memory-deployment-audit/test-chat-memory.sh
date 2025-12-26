#!/bin/bash

echo "=== TESTING CHAT AGENT MEMORY INTEGRATION ==="
echo ""

# Get token
TOKEN=$(curl -s -X POST "http://localhost:8000/auth/token?user_id=mene" | \
  python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

echo "✅ Token obtained"
echo ""

# 1. Check initial memory count
echo "=== 1. INITIAL MEMORY COUNT ==="
INITIAL_COUNT=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/memory/list?memory_type=all&limit=100" | \
  python3 -c "import json,sys; print(len(json.load(sys.stdin).get('memories', [])))")
echo "Initial memories in database: $INITIAL_COUNT"
echo ""

# 2. Send test chat messages
echo "=== 2. SENDING TEST CHAT MESSAGES ==="

# Message 1: Medical reminder (should trigger memory storage)
echo "Sending message 1: Medical reminder..."
CHAT1=$(curl -s -X POST "http://localhost:8000/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Remember that I need to take my blood pressure medication every morning at 8am",
    "user_id": "mene",
    "chat_id": "test-session-1"
  }')

echo "Response 1:"
echo "$CHAT1" | python3 -m json.tool | head -20
echo ""
sleep 3

# Message 2: Family information (should be system memory)
echo "Sending message 2: Family doctor info..."
CHAT2=$(curl -s -X POST "http://localhost:8000/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Our family doctor is Dr. Smith at Main Street Medical Center, phone 555-0123",
    "user_id": "mene",
    "chat_id": "test-session-1"
  }')

echo "Response 2:"
echo "$CHAT2" | python3 -m json.tool | head -20
echo ""
sleep 3

# 3. Check if memories increased
echo "=== 3. CHECKING MEMORY COUNT AFTER CHAT ==="
AFTER_COUNT=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/memory/list?memory_type=all&limit=100" | \
  python3 -c "import json,sys; print(len(json.load(sys.stdin).get('memories', [])))")
echo "Memories after chat: $AFTER_COUNT"
echo "Change: +$(($AFTER_COUNT - $INITIAL_COUNT))"
echo ""

# 4. Check Mem0 directly for stored conversations
echo "=== 4. CHECKING MEM0 DIRECTLY ==="
docker exec demestihas-mem0 curl -s -X POST http://localhost:8080/memory \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "mene",
    "action": "retrieve",
    "limit": 10
  }' | python3 -m json.tool
echo ""

# 5. Check agent logs for memory storage activity
echo "=== 5. AGENT LOGS - MEMORY ACTIVITY ==="
docker logs demestihas-agent --tail 50 2>&1 | grep -i "memory\|mem0" | tail -20
echo ""

# 6. Test the /memory/store endpoint that the UI uses
echo "=== 6. TESTING UI MEMORY STORE ENDPOINT ==="
echo "This is what the UI calls when user manually stores a memory..."
MANUAL_STORE=$(curl -s -X POST "http://localhost:8000/memory/store?content=Test%20memory%20from%20diagnostic&memory_type=private" \
  -H "Authorization: Bearer $TOKEN")
echo "$MANUAL_STORE" | python3 -m json.tool
echo ""

# 7. Final memory list with details
echo "=== 7. FINAL MEMORY LIST ==="
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/memory/list?memory_type=all&limit=10" | \
  python3 -c "
import json, sys
data = json.load(sys.stdin)
memories = data.get('memories', [])
print(f'Total memories: {len(memories)}')
print()
for i, mem in enumerate(memories[:10], 1):
    print(f'{i}. {mem.get(\"content\", \"\")}')
    print(f'   Source: {mem.get(\"source\", \"unknown\")}')
    print(f'   Added by: {mem.get(\"added_by\", \"unknown\")}')
    print(f'   Timestamp: {mem.get(\"timestamp\", \"unknown\")}')
    print()
"

