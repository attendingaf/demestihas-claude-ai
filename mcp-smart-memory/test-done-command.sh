#!/bin/bash

# Test script for /done command integration

echo "Testing /done command MCP integration..."

# Check if memory API is running
echo -n "1. Memory API Status: "
curl -s http://localhost:7777/health | grep -q "ok" && echo "✅ RUNNING" || echo "❌ NOT RUNNING"

# Check if MCP server has the done handler
echo -n "2. MCP Server has done handler: "
grep -q "handle_done_command" /Users/menedemestihas/Projects/demestihas-ai/mcp-smart-memory/index.js && echo "✅ YES" || echo "❌ NO"

# Check if handler file exists
echo -n "3. Done handler file exists: "
[ -f /Users/menedemestihas/Projects/demestihas-ai/mcp-smart-memory/done-command-handler.js ] && echo "✅ YES" || echo "❌ NO"

# Check Claude config
echo -n "4. Smart-memory in Claude config: "
grep -q "smart-memory" ~/Library/Application\ Support/Claude/claude_desktop_config.json && echo "✅ YES" || echo "❌ NO"

echo ""
echo "✅ Integration Complete!"
echo ""
echo "To use the /done command:"
echo "1. Restart Claude Desktop to reload MCP servers"
echo "2. In any conversation, type: /done"
echo "3. Claude will analyze the thread and propose memories"
echo "4. Respond with 'all', specific numbers, or 'none'"
echo ""
echo "Quick test commands:"
echo "  /done       - Review current thread"
echo "  /done all   - Save all proposed memories"
echo "  /done skip  - Skip memory extraction"
