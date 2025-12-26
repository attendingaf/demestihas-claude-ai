#!/bin/bash
# Test Supabase Cloud Sync
# Run after applying supabase-fix.sql

echo "🔍 Testing Supabase Cloud Sync..."
echo "================================"

# Clean up any existing processes on both ports
echo "0. Cleaning up existing processes..."
lsof -ti:7777 | xargs kill -9 2>/dev/null
lsof -ti:7778 | xargs kill -9 2>/dev/null
sleep 1

# Check if MCP server is running
echo "1. Starting MCP server on port 7777..."
cd /Users/menedemestihas/Projects/demestihas-ai/mcp-smart-memory
npm run api > /tmp/mcp-server.log 2>&1 &
SERVER_PID=$!
echo "   Server PID: $SERVER_PID"

# Wait for server to start
echo "   Waiting for server to initialize..."
sleep 5

# Check if server is running
if lsof -ti:7777 > /dev/null; then
    echo "✅ MCP server is running on port 7777"
else
    echo "❌ Failed to start server. Check logs:"
    tail -20 /tmp/mcp-server.log
    exit 1
fi

# Test memory storage with embedding
echo ""
echo "2. Testing memory storage with embedding..."
curl -X POST http://localhost:7777/store \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Supabase cloud sync test with embeddings",
    "type": "test",
    "importance": "high",
    "metadata": {
      "test": true,
      "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
    }
  }' | python3 -m json.tool

# Check system health
echo ""
echo "3. Checking system health..."
curl -s http://localhost:7777/health | python3 -m json.tool

# Test semantic search
echo ""
echo "4. Testing semantic search..."
curl -s "http://localhost:7777/context?q=cloud%20sync&limit=5" | python3 -m json.tool | head -50

# Test analyze endpoint
echo ""
echo "5. Testing analysis endpoint..."
curl -X POST http://localhost:7777/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "We fixed the issue by updating the configuration. The solution was to change the port from 7778 to 7777.",
    "focus_areas": ["solution", "configuration"]
  }' | python3 -m json.tool

# Final health check
echo ""
echo "6. Final health check with stats..."
curl -s http://localhost:7777/health | python3 -m json.tool | grep -E "(status|totalMemories|cloudStatus|uniqueTypes|initialized)"

echo ""
echo "================================"
echo "✅ Test complete. Check results above."
echo ""
echo "Expected outcomes:"
echo "- Server running on port 7777"
echo "- Memory storage returns success"
echo "- Health check shows 'healthy' status"
echo "- Semantic search returns relevant results"
echo ""
echo "Server logs available at: /tmp/mcp-server.log"
echo "To stop server: kill $SERVER_PID"
