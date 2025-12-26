#!/bin/bash

# MCP Server Diagnostic Script
# Checks the status of all MCP servers

echo "🔍 MCP Server Diagnostics"
echo "========================="
echo ""

# Check config file
CONFIG_FILE="/Users/menedemestihas/Library/Application Support/Claude/claude_desktop_config.json"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Claude config file not found!"
    exit 1
fi

echo "📋 Configured MCP Servers:"
echo "--------------------------"
cat "$CONFIG_FILE" | jq -r '.mcpServers | keys[]' | while read server; do
    echo "  • $server"
done

echo ""
echo "📊 Server Status:"
echo "-----------------"

# Check EA-AI
echo -n "EA-AI: "
if [ -f "/Users/menedemestihas/Projects/claude-desktop-ea-ai/mcp-server-fixed.js" ]; then
    echo "✅ Fixed server exists"
else
    echo "❌ Fixed server missing"
fi

# Check Git
echo -n "Git: "
if command -v uvx &> /dev/null; then
    echo "✅ uvx available"
else
    echo "❌ uvx not found"
fi

# Check Smart Memory
echo -n "Smart Memory: "
if [ -f "/Users/menedemestihas/Projects/demestihas-ai/mcp-smart-memory/index.js" ]; then
    echo "✅ Server exists"
else
    echo "❌ Server missing"
fi

# Check Pluma
echo -n "Pluma: "
if [ -f "/Users/menedemestihas/Projects/demestihas-ai/pluma-mcp-server/src/index.js" ]; then
    echo "✅ Server exists"
else
    echo "❌ Server missing"
fi

echo ""
echo "📝 Recent Errors (last 10 lines per server):"
echo "--------------------------------------------"

for log in /Users/menedemestihas/Library/Logs/Claude/mcp-server-*.log; do
    if [ -f "$log" ]; then
        server_name=$(basename "$log" .log)
        echo ""
        echo "[$server_name]"
        tail -n 10 "$log" | grep -i "error" | tail -n 3 || echo "  No recent errors"
    fi
done

echo ""
echo "💡 Quick Fixes:"
echo "---------------"
echo "1. If EA-AI shows errors: Run restart-claude.sh"
echo "2. If Git server fails: pip install mcp-server-git"
echo "3. If Smart Memory fails: Check node_modules in mcp-smart-memory"
echo "4. If Pluma fails: Check Python environment"
echo ""
echo "📖 For detailed logs: ~/Library/Logs/Claude/"
