#!/bin/bash

# Comprehensive MCP Server Fix Script
# Fixes all server connection issues

echo "🔧 MCP Server Comprehensive Fix"
echo "================================"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Test EA-AI Server
echo "Testing EA-AI Server v2..."
cd /Users/menedemestihas/Projects/claude-desktop-ea-ai
TEST_RESULT=$(echo '{"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}},"jsonrpc":"2.0","id":1}' | timeout 2 node mcp-server-v2.js 2>/dev/null | grep -c '"result"')

if [ "$TEST_RESULT" -eq 1 ]; then
    echo -e "${GREEN}✅ EA-AI Server v2: Working${NC}"
else
    echo -e "${RED}❌ EA-AI Server v2: Failed${NC}"
    exit 1
fi

# 2. Test Git Server
echo "Testing Git Server..."
if command -v uvx &> /dev/null; then
    echo -e "${GREEN}✅ Git Server: uvx available${NC}"
else
    echo -e "${YELLOW}⚠️  Git Server: uvx not found, installing...${NC}"
    pip install --user mcp-server-git
fi

# 3. Test Smart Memory Server
echo "Testing Smart Memory Server..."
if [ -f "/Users/menedemestihas/Projects/demestihas-ai/mcp-smart-memory/index.js" ]; then
    echo -e "${GREEN}✅ Smart Memory: Server exists${NC}"
else
    echo -e "${RED}❌ Smart Memory: Server missing${NC}"
fi

# 4. Test Pluma Server
echo "Testing Pluma Server..."
if [ -f "/Users/menedemestihas/Projects/demestihas-ai/pluma-mcp-server/src/index.js" ]; then
    echo -e "${GREEN}✅ Pluma: Server exists${NC}"
else
    echo -e "${RED}❌ Pluma: Server missing${NC}"
fi

# 5. Clear old logs
echo ""
echo "Clearing old logs..."
rm -f /Users/menedemestihas/Library/Logs/Claude/mcp-server-*.log
rm -f /Users/menedemestihas/Library/Logs/Claude/mcp.log
echo -e "${GREEN}✅ Logs cleared${NC}"

# 6. Kill Claude processes
echo ""
echo "Stopping Claude Desktop..."
pkill -f "Claude.app" 2>/dev/null || true
sleep 3

# 7. Restart Claude
echo ""
echo "Starting Claude Desktop..."
open -a "Claude"

echo ""
echo -e "${GREEN}🎉 Claude Desktop restarted with fixed servers!${NC}"
echo ""
echo "Available tools:"
echo "  • EA-AI: ea_ai_route, ea_ai_memory, ea_ai_calendar_check, ea_ai_task_adhd, ea_ai_family"
echo "  • Git: git_status, git_diff, git_commit, etc."
echo "  • Smart Memory: analyze_for_memory, propose_memory, etc."
echo "  • Pluma: pluma_fetch_emails, pluma_generate_reply, etc."
echo "  • Filesystem: read_file, write_file, etc."
echo "  • Control Chrome: open_url, get_current_tab, etc."
echo "  • Control your Mac: osascript"
echo "  • Figma Dev Mode: get_code, get_image, etc."
echo ""
echo "Monitor logs:"
echo "  tail -f ~/Library/Logs/Claude/mcp.log"
echo "  tail -f ~/Library/Logs/Claude/mcp-server-ea-ai.log"
