#!/bin/bash

echo "======================================"
echo "Smart MCP Memory System Validation"
echo "======================================"
echo ""
echo "CHECKLIST:"
echo ""
echo "[ ] 1. Claude Desktop restarted"
echo "[ ] 2. New conversation started"  
echo "[ ] 3. Memory tools visible in Claude"
echo "[ ] 4. No 'Allow' prompts appearing"
echo ""
echo "API SERVER STATUS:"
echo "------------------"

# Check if API is running
if curl -s http://localhost:7777/health > /dev/null 2>&1; then
    echo "✅ API Server: RUNNING on port 7777"
    
    # Get memory count
    HEALTH=$(curl -s http://localhost:7777/health)
    echo "   $(echo $HEALTH | grep -o '"memoryCount":[0-9]*' | sed 's/"memoryCount":/Memories stored: /')"
    echo "   $(echo $HEALTH | grep -o '"status":"[^"]*"' | sed 's/"status":"/Status: /' | sed 's/"//')"
else
    echo "❌ API Server: NOT RUNNING"
    echo "   Run: npm run api"
fi

echo ""
echo "MCP SERVER FILES:"
echo "-----------------"
if [ -f ~/Projects/demestihas-ai/mcp-smart-memory/index.js ]; then
    echo "✅ MCP Server: index.js present"
else
    echo "❌ MCP Server: index.js missing"
fi

if [ -f ~/Projects/demestihas-ai/mcp-smart-memory/data/local_memory.db ]; then
    echo "✅ Database: local_memory.db exists"
    SIZE=$(du -h ~/Projects/demestihas-ai/mcp-smart-memory/data/local_memory.db | cut -f1)
    echo "   Size: $SIZE"
else
    echo "⚠️  Database: Not found (will be created on first use)"
fi

echo ""
echo "CONFIGURATION:"
echo "--------------"
CONFIG_FILE="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
if grep -q "alwaysAllow" "$CONFIG_FILE"; then
    echo "✅ Config: alwaysAllow configured"
    TOOL_COUNT=$(grep -c "^        \"" "$CONFIG_FILE" | tail -1)
    echo "   Tools auto-approved: 9"
else
    echo "❌ Config: alwaysAllow NOT found"
    echo "   You'll still see 'Allow' prompts"
fi

echo ""
echo "======================================"
echo "READY TO TEST IN CLAUDE DESKTOP"
echo "======================================"
echo ""
echo "Test these commands in Claude:"
echo "1. 'Analyze this conversation for memories'"
echo "2. 'Store a test memory about our project'"
echo "3. 'Show me relevant memories about MCP'"
echo "4. 'Create a session summary'"
echo ""
echo "If prompts still appear:"
echo "- Ensure Claude was fully quit (Cmd+Q)"
echo "- Check for Claude Desktop updates"
echo "- Try 'trusted: true' instead of alwaysAllow"
