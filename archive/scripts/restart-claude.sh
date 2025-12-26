#!/bin/bash

# Restart Claude Desktop with Fixed EA-AI Server
# This script ensures the EA-AI MCP server is properly configured

echo "🔧 EA-AI MCP Server Fix & Restart Script"
echo "========================================"
echo ""

# 1. Check if the fixed server exists
if [ ! -f "/Users/menedemestihas/Projects/claude-desktop-ea-ai/mcp-server-fixed.js" ]; then
    echo "❌ Fixed server not found. Please run the fix first."
    exit 1
fi

echo "✅ Fixed server file exists"

# 2. Backup current config
cp "/Users/menedemestihas/Library/Application Support/Claude/claude_desktop_config.json" \
   "/Users/menedemestihas/Library/Application Support/Claude/claude_desktop_config.json.backup.$(date +%Y%m%d_%H%M%S)"
echo "✅ Config backed up"

# 3. Verify config points to fixed server
if grep -q "mcp-server-fixed.js" "/Users/menedemestihas/Library/Application Support/Claude/claude_desktop_config.json"; then
    echo "✅ Config already using fixed server"
else
    echo "❌ Config still using old server - please update config"
    exit 1
fi

# 4. Clear MCP logs
echo "Clearing old MCP logs..."
rm -f "/Users/menedemestihas/Library/Logs/Claude/mcp-server-ea-ai.log"
echo "✅ Logs cleared"

# 5. Kill any existing Claude processes
echo "Stopping Claude Desktop..."
pkill -f "Claude.app" 2>/dev/null || true
sleep 2

# 6. Test the server quickly
echo ""
echo "Testing EA-AI server..."
cd /Users/menedemestihas/Projects/claude-desktop-ea-ai/test
node test-jsonrpc.js

# 7. Restart Claude
echo ""
echo "Starting Claude Desktop..."
open -a "Claude"

echo ""
echo "🎉 Claude Desktop restarted with fixed EA-AI server!"
echo ""
echo "The EA-AI tools should now be available:"
echo "  • ea_ai_route - Route to specialized agents"
echo "  • ea_ai_memory - Smart memory system"
echo "  • ea_ai_calendar_check - 6-calendar management"
echo "  • ea_ai_task_adhd - ADHD task optimization"
echo "  • ea_ai_family - Family context loading"
echo ""
echo "Monitor logs at: ~/Library/Logs/Claude/mcp-server-ea-ai.log"
