#!/bin/bash

echo "Restarting Memory System with FTS5 Fix"
echo "======================================="

# 1. Kill existing processes
echo -e "\n1. Stopping existing processes..."

# Kill API server
API_PID=$(lsof -t -i:7777)
if [ ! -z "$API_PID" ]; then
    kill -9 $API_PID
    echo "   ✓ Stopped API server (PID: $API_PID)"
else
    echo "   ✓ API server not running"
fi

# 2. Restart API server
echo -e "\n2. Starting API server with FTS5 support..."
cd ~/Projects/demestihas-ai/mcp-smart-memory
npm run api &
API_NEW_PID=$!
echo "   ✓ API server started (PID: $API_NEW_PID)"

# Wait for API to initialize
sleep 3

# 3. Test the fix
echo -e "\n3. Testing retrieval with FTS5:"
echo "   Searching for 'configuration'..."
RESULT=$(curl -s "http://localhost:7777/context?q=configuration&limit=2")
if echo "$RESULT" | grep -q "results"; then
    echo "   ✅ RETRIEVAL WORKING!"
    echo "$RESULT" | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'   Found {len(data.get(\"results\", []))} results')"
else
    echo "   ❌ Retrieval still not working"
fi

echo -e "\n4. MCP Server (Claude Desktop):"
echo "   ⚠️  Restart Claude Desktop to load the FTS5 changes"
echo "   1. Quit Claude Desktop (Cmd+Q)"
echo "   2. Reopen Claude Desktop"
echo "   3. The memory tools will use the new FTS5 search"

echo -e "\n======================================="
echo "System restart complete!"
