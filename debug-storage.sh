#!/bin/bash
# Debug Memory Storage Issue

echo "🔍 Debugging Memory Storage..."
echo "================================"

# Check if server is running
if ! lsof -ti:7777 > /dev/null; then
    echo "❌ Server not running. Start it first with:"
    echo "   /Users/menedemestihas/Projects/demestihas-ai/start-memory-server.sh"
    exit 1
fi

echo "✅ Server is running on port 7777"
echo ""

# 1. Store a test memory with full details
echo "1. Storing test memory with timestamp..."
MEMORY_RESPONSE=$(curl -s -X POST http://localhost:7777/store \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Debug test: Supabase embedding column is now added",
    "type": "solution",
    "importance": "high",
    "metadata": {
      "test": true,
      "debug": true,
      "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
    }
  }')

echo "$MEMORY_RESPONSE" | python3 -m json.tool
MEMORY_ID=$(echo "$MEMORY_RESPONSE" | python3 -c "import json, sys; print(json.load(sys.stdin)['id'])" 2>/dev/null)
echo "Stored memory ID: $MEMORY_ID"
echo ""

# 2. Wait a moment for storage
echo "2. Waiting 2 seconds for storage to complete..."
sleep 2
echo ""

# 3. Check health again
echo "3. Checking system health after storage..."
curl -s http://localhost:7777/health | python3 -m json.tool | grep -E "(totalMemories|cloudStatus|source)"
echo ""

# 4. Search for the memory we just stored
echo "4. Searching for the memory we just stored..."
curl -s "http://localhost:7777/context?q=Supabase%20embedding&limit=5" | python3 -m json.tool
echo ""

# 5. Check SQLite directly
echo "5. Checking SQLite database directly..."
# Check multiple possible locations
for DB_PATH in \
  "/Users/menedemestihas/Projects/demestihas-ai/mcp-smart-memory/data/local_memory.db" \
  "/Users/menedemestihas/Projects/demestihas-ai/claude-desktop-rag/data/local_memory.db" \
  "/Users/menedemestihas/Projects/demestihas-ai/claude-desktop-rag/local_cache.db"
do
  if [ -f "$DB_PATH" ]; then
    echo "Found database at: $DB_PATH"
    sqlite3 "$DB_PATH" "SELECT COUNT(*) as total FROM project_memories_cache;" 2>/dev/null || \
    sqlite3 "$DB_PATH" "SELECT name FROM sqlite_master WHERE type='table';" 2>/dev/null
    break
  fi
done
echo ""

# 6. Check Supabase connection directly
echo "6. Testing Supabase connection..."
curl -s -X GET "https://oletgdpevhdxbywrqeyh.supabase.co/rest/v1/project_memories?select=count" \
  -H "apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9sZXRnZHBldmhkeGJ5d3JxZXloIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcxMjU4MTYsImV4cCI6MjA3MjcwMTgxNn0.Mr3jgTBOfSRq3brhHpp9H-8S_eiugZj88LqZ4ohjVlk" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9sZXRnZHBldmhkeGJ5d3JxZXloIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcxMjU4MTYsImV4cCI6MjA3MjcwMTgxNn0.Mr3jgTBOfSRq3brhHpp9H-8S_eiugZj88LqZ4ohjVlk" \
  | python3 -m json.tool
echo ""

# 7. Check if embedding column exists
echo "7. Checking if embedding column exists in Supabase..."
curl -s -X GET "https://oletgdpevhdxbywrqeyh.supabase.co/rest/v1/project_memories?select=id,embedding&limit=1" \
  -H "apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9sZXRnZHBldmhkeGJ5d3JxZXloIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcxMjU4MTYsImV4cCI6MjA3MjcwMTgxNn0.Mr3jgTBOfSRq3brhHpp9H-8S_eiugZj88LqZ4ohjVlk" \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)
if 'error' in data:
    print(f'❌ Error: {data}')
elif len(data) > 0 and 'embedding' in data[0]:
    print('✅ Embedding column exists!')
else:
    print('⚠️ Embedding column might not exist or no data')
"
echo ""

echo "================================"
echo "Debug complete. Check results above."
echo ""
echo "Key indicators:"
echo "- If totalMemories > 0: Local storage working"
echo "- If Supabase returns data: Cloud connection working"
echo "- If embedding column exists: Ready for semantic search"
