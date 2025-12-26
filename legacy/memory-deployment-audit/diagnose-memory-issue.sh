#!/bin/bash

echo "=== MEMORY SYSTEM DIAGNOSTIC ==="
echo "Date: $(date)"
echo ""

# Get fresh token
TOKEN=$(curl -s -X POST "http://localhost:8000/auth/token?user_id=mene" | \
  python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

echo "✅ Token obtained"
echo ""

# 1. Check what's actually in the memory database
echo "=== 1. DIRECT DATABASE CHECK ==="
echo "Checking memory/list endpoint..."
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/memory/list?memory_type=all&limit=100" | python3 -m json.tool > memory-list-output.json

MEMORY_COUNT=$(cat memory-list-output.json | python3 -c "import json,sys; print(len(json.load(sys.stdin).get('memories', [])))")
echo "Memories found: $MEMORY_COUNT"

if [ "$MEMORY_COUNT" -gt 0 ]; then
    echo "Sample memory:"
    cat memory-list-output.json | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin).get('memories', [{}])[0], indent=2))"
else
    echo "⚠️ No memories in database"
fi
echo ""

# 2. Check the agent's memory system (Mem0)
echo "=== 2. CHECKING MEM0 CONTAINER ==="
docker ps | grep mem0
docker logs demestihas-mem0 --tail 20 2>&1 | grep -i "error\|memory\|store" || echo "No relevant logs"
echo ""

# 3. Test memory storage directly
echo "=== 3. DIRECT STORAGE TEST ==="
TEST_MEMORY='{"content":"Direct API test - medical reminder to check blood pressure daily","metadata":{"contexts":["medical","test"],"importance":9,"tags":["medical","reminder"],"created_at":"'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'","source":"diagnostic"}}'

echo "Attempting to store test memory..."
STORE_RESULT=$(curl -s -X POST "http://localhost:8000/memory/store" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"content\":\"Direct API test - medical reminder to check blood pressure daily\",\"memory_type\":\"private\",\"metadata\":{\"contexts\":[\"medical\",\"test\"],\"importance\":9,\"tags\":[\"medical\",\"reminder\"],\"source\":\"diagnostic\"}}" 2>&1)

echo "$STORE_RESULT" | python3 -m json.tool

if echo "$STORE_RESULT" | grep -q "id"; then
    echo "✅ Storage successful"

    # Try to retrieve it immediately
    echo ""
    echo "Attempting immediate retrieval..."
    sleep 2
    curl -s -H "Authorization: Bearer $TOKEN" \
      "http://localhost:8000/memory/list?memory_type=all&limit=10" | \
      python3 -c "import json,sys; data=json.load(sys.stdin); print(f'Total now: {len(data.get(\"memories\", []))}')"
else
    echo "❌ Storage failed"
    echo "$STORE_RESULT"
fi
echo ""

# 4. Check PostgreSQL directly
echo "=== 4. POSTGRESQL DIRECT CHECK ==="
docker exec demestihas-postgres psql -U postgres -d demestihas -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public';" 2>&1 | grep -i "memory\|mem0"

echo ""
echo "Checking for memory-related tables..."
docker exec demestihas-postgres psql -U postgres -d demestihas -c "\dt" 2>&1 | grep -i "memory\|mem"
echo ""

# 5. Check agent API endpoints
echo "=== 5. AGENT API ENDPOINTS ==="
echo "Available endpoints:"
curl -s http://localhost:8000/docs 2>&1 | grep -o '/memory[^"]*' | head -10 || echo "Could not fetch OpenAPI docs"
echo ""

# 6. Check if there's a different memory endpoint
echo "=== 6. SEARCHING FOR MEMORY ENDPOINTS ==="
curl -s http://localhost:8000/openapi.json 2>/dev/null | python3 -c "
import json, sys
try:
    api = json.load(sys.stdin)
    paths = api.get('paths', {})
    for path in paths:
        if 'memory' in path.lower() or 'mem0' in path.lower():
            print(f'{path}: {list(paths[path].keys())}')
except:
    print('Could not parse OpenAPI spec')
"
echo ""

# 7. Check Streamlit container logs for memory service errors
echo "=== 7. STREAMLIT MEMORY SERVICE LOGS ==="
docker logs demestihas-streamlit --tail 50 2>&1 | grep -i "memory\|error" || echo "No memory-related logs"
echo ""

# 8. Test the memory_service.py directly in container
echo "=== 8. TEST MEMORY SERVICE MODULE ==="
docker exec demestihas-streamlit python3 << 'PYEOF'
import sys
sys.path.insert(0, '/app')

try:
    from memory_service import MemoryService

    print("Creating MemoryService instance...")
    service = MemoryService(api_url="http://agent:8000", user_id="mene")

    print(f"✅ Authentication successful")
    print(f"Token: {service.token[:20]}...")

    print("\nTesting health check...")
    healthy = service.health_check()
    print(f"Health: {healthy}")

    print("\nTesting get_stats...")
    stats = service.get_stats()
    print(f"Stats: {stats}")

    print("\nTesting save_memory...")
    result = service.save_memory(
        content="Container test - Medical appointment tomorrow at 9am",
        memory_type="private",
        importance=8
    )
    print(f"Save result: {result}")

    print("\nTesting search_memories...")
    results = service.search_memories("medical", limit=5)
    print(f"Search results: {len(results)} found")
    if results:
        print(f"First result: {results[0].get('content', '')[:100]}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
PYEOF

echo ""

# Summary
echo "=== DIAGNOSTIC SUMMARY ==="
cat > diagnostic-summary.txt << EOF
Memory System Diagnostic Report
================================
Date: $(date)

Database Status:
- Memories in /memory/list: $MEMORY_COUNT
- Direct storage test: [see above]
- PostgreSQL tables: [see above]

Key Findings:
1. Memory API endpoint exists: $(curl -s http://localhost:8000/health | grep -q "ok" && echo "YES" || echo "NO")
2. Authentication working: $([ -n "$TOKEN" ] && echo "YES" || echo "NO")
3. Memories found in DB: $([ "$MEMORY_COUNT" -gt 0 ] && echo "YES ($MEMORY_COUNT)" || echo "NO (0)")

Next Steps:
- Check if memories are in Mem0 instead of PostgreSQL
- Verify API endpoint is correct
- Test memory_service.py directly
- Check agent backend implementation

Full output saved to: diagnose-memory-issue.log
EOF

cat diagnostic-summary.txt
