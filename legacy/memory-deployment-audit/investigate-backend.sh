#!/bin/bash

echo "=== BACKEND MEMORY IMPLEMENTATION INVESTIGATION ==="
echo ""

# 1. Check agent container structure
echo "=== 1. AGENT CONTAINER FILE STRUCTURE ==="
docker exec demestihas-agent find /app -name "*memory*.py" -type f 2>/dev/null
echo ""

# 2. Check main.py for memory routes
echo "=== 2. MEMORY ROUTES IN main.py ==="
docker exec demestihas-agent cat /app/main.py | grep -A 20 "/memory" || echo "Not in main.py"
echo ""

# 3. Check if there's a separate memory router
echo "=== 3. LOOKING FOR MEMORY ROUTER FILES ==="
docker exec demestihas-agent ls -la /app/ | grep -i memory
docker exec demestihas-agent ls -la /app/routers/ 2>/dev/null | grep -i memory || echo "No routers directory"
echo ""

# 4. Check the actual memory endpoints implementation
echo "=== 4. MEMORY ENDPOINT IMPLEMENTATION ==="
docker exec demestihas-agent grep -r "def.*store.*memory" /app/*.py /app/routers/*.py 2>/dev/null | head -20
echo ""

# 5. Check how Mem0 is initialized
echo "=== 5. MEM0 CLIENT INITIALIZATION ==="
docker exec demestihas-agent grep -r "mem0\|Mem0\|Memory(" /app/*.py 2>/dev/null | grep -i "client\|init" | head -10
echo ""

# 6. Check environment variables for Mem0
echo "=== 6. MEM0 CONFIGURATION ==="
docker exec demestihas-agent env | grep -i "mem0\|memory" || echo "No mem0 env vars"
echo ""

# 7. Direct Mem0 API test
echo "=== 7. DIRECT MEM0 API TEST ==="
echo "Testing Mem0 container directly..."
docker exec demestihas-mem0 curl -s http://localhost:8080/health 2>/dev/null || echo "Mem0 health check failed"
echo ""

# 8. Check Mem0 logs for storage activity
echo "=== 8. MEM0 RECENT ACTIVITY ==="
docker logs demestihas-mem0 --tail 30 2>&1
echo ""

# 9. Test if chat is actually calling memory endpoints
echo "=== 9. CHECKING CHAT AGENT MEMORY INTEGRATION ==="
docker exec demestihas-agent grep -r "memory" /app/agent.py 2>/dev/null | head -20 || echo "No agent.py found"
docker exec demestihas-agent grep -r "mem0" /app/*.py 2>/dev/null | head -10
echo ""

# 10. Check if there's a memory manager class
echo "=== 10. MEMORY MANAGER CLASS ==="
docker exec demestihas-agent find /app -type f -name "*.py" -exec grep -l "class.*Memory" {} \; 2>/dev/null
echo ""

