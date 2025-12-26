#!/bin/bash

echo "Smart Memory System Status"
echo "=========================="
echo ""

# Check MCP Server (via Claude Desktop)
echo "1. MCP Server (Claude Desktop):"
if pgrep -f "claude_desktop" > /dev/null; then
    echo "   ✅ Claude Desktop is running (MCP server active)"
else
    echo "   ❌ Claude Desktop not running (MCP server inactive)"
    echo "   → Start Claude Desktop to activate MCP tools"
fi

# Check HTTP API Server
echo ""
echo "2. HTTP API Server (Port 7777):"
if lsof -i :7777 > /dev/null 2>&1; then
    echo "   ✅ API server is running"
    HEALTH=$(curl -s http://localhost:7777/health | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'   Status: {d.get(\"status\", \"unknown\")}')" 2>/dev/null)
    echo "$HEALTH"
else
    echo "   ❌ API server not running"
    echo "   → Start with: cd ~/Projects/demestihas-ai/mcp-smart-memory && npm run api"
fi

# Check Database
echo ""
echo "3. Memory Database:"
if [ -f ~/Projects/demestihas-ai/mcp-smart-memory/data/local_memory.db ]; then
    SIZE=$(du -h ~/Projects/demestihas-ai/mcp-smart-memory/data/local_memory.db | cut -f1)
    echo "   ✅ Database exists (Size: $SIZE)"
else
    echo "   ⚠️  Database not found (will be created on first use)"
fi

# Check Auto-start
echo ""
echo "4. Auto-start Configuration:"
if launchctl list | grep -q "com.demestihas.memory-api" 2>/dev/null; then
    echo "   ✅ API auto-start is configured"
else
    echo "   ❌ API auto-start not configured"
    echo "   → To enable: bash ~/Projects/demestihas-ai/mcp-smart-memory/setup_autostart.sh"
fi

echo ""
echo "=========================="
echo ""
echo "Quick Actions:"
echo "• Start API manually: cd ~/Projects/demestihas-ai/mcp-smart-memory && npm run api"
echo "• Enable auto-start:  bash ~/Projects/demestihas-ai/mcp-smart-memory/setup_autostart.sh"
echo "• Check API health:   curl http://localhost:7777/health"
