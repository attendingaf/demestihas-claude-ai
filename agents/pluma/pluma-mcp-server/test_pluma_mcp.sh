#!/bin/bash

echo "🔧 Pluma MCP Server Testing"
echo "=========================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test function
test_command() {
    local test_name=$1
    local command=$2
    echo -e "${BLUE}Testing: $test_name${NC}"
    echo "Command: $command"
    echo "---"
    
    # Run the command with timeout
    if timeout 5 bash -c "$command" > /tmp/test_output.txt 2>&1; then
        if grep -q "error" /tmp/test_output.txt; then
            echo -e "${RED}✗ Test failed with error${NC}"
            cat /tmp/test_output.txt | head -10
        else
            echo -e "${GREEN}✓ Test passed${NC}"
            cat /tmp/test_output.txt | head -10
        fi
    else
        echo -e "${RED}✗ Test timed out or failed${NC}"
        cat /tmp/test_output.txt 2>&1 | head -10
    fi
    echo ""
}

# Change to project directory
cd ~/Projects/demestihas-ai/pluma-mcp-server

echo "📁 Project directory: $(pwd)"
echo ""

# Test 1: Python environment
echo -e "${BLUE}Test 1: Python Environment${NC}"
if [ -f "/Users/menedemestihas/Projects/demestihas-ai/pluma-local/pluma-env/bin/python" ]; then
    echo -e "${GREEN}✓ Python environment exists${NC}"
    /Users/menedemestihas/Projects/demestihas-ai/pluma-local/pluma-env/bin/python --version
else
    echo -e "${RED}✗ Python environment not found${NC}"
fi
echo ""

# Test 2: Python imports
echo -e "${BLUE}Test 2: Python Imports${NC}"
/Users/menedemestihas/Projects/demestihas-ai/pluma-local/pluma-env/bin/python -c "
import sys
sys.path.insert(0, '/Users/menedemestihas/Projects/demestihas-ai/pluma-local')
try:
    from pluma_local import LocalPlumaAgent
    print('✓ pluma_local import successful')
    from gmail_auth import GmailAuthenticator
    print('✓ gmail_auth import successful')
    import anthropic
    print('✓ anthropic import successful')
    print('✓ All imports successful')
except ImportError as e:
    print(f'✗ Import failed: {e}')
"
echo ""

# Test 3: Gmail credentials
echo -e "${BLUE}Test 3: Gmail Credentials${NC}"
if [ -f "/Users/menedemestihas/Projects/demestihas-ai/pluma-local/credentials/credentials.json" ]; then
    echo -e "${GREEN}✓ Gmail credentials.json exists${NC}"
else
    echo -e "${RED}✗ Gmail credentials.json not found${NC}"
fi

if [ -f "/Users/menedemestihas/Projects/demestihas-ai/pluma-local/credentials/token.pickle" ]; then
    echo -e "${GREEN}✓ Gmail token.pickle exists${NC}"
else
    echo -e "${RED}✗ Gmail token.pickle not found${NC}"
fi
echo ""

# Test 4: Python bridge with fetch_emails
test_command "Python Bridge - Fetch Emails" \
    "/Users/menedemestihas/Projects/demestihas-ai/pluma-local/pluma-env/bin/python python/pluma_bridge.py '{\"method\": \"pluma_fetch_emails\", \"params\": {\"max_results\": 1}}'"

# Test 5: Node.js MCP server
echo -e "${BLUE}Test 5: MCP Server Startup${NC}"
timeout 2 node src/index.js > /tmp/mcp_test.txt 2>&1 &
MCP_PID=$!
sleep 1

if ps -p $MCP_PID > /dev/null 2>&1; then
    echo -e "${GREEN}✓ MCP server started successfully${NC}"
    kill $MCP_PID 2>/dev/null
else
    echo -e "${RED}✗ MCP server failed to start${NC}"
    cat /tmp/mcp_test.txt | head -10
fi
echo ""

# Test 6: Check Claude Desktop config
echo -e "${BLUE}Test 6: Claude Desktop Configuration${NC}"
if grep -q "pluma" ~/Library/Application\ Support/Claude/claude_desktop_config.json 2>/dev/null; then
    echo -e "${GREEN}✓ Pluma configured in Claude Desktop${NC}"
    grep -A 5 '"pluma"' ~/Library/Application\ Support/Claude/claude_desktop_config.json
else
    echo -e "${RED}✗ Pluma not configured in Claude Desktop${NC}"
fi
echo ""

# Summary
echo "=========================="
echo "🎯 Test Summary"
echo "=========================="
echo ""
echo "To use Pluma in Claude Desktop:"
echo "1. Restart Claude Desktop application"
echo "2. Look for pluma tools in the tools menu"
echo "3. Try: 'Show me my latest emails'"
echo ""
echo "If tools don't appear:"
echo "- Check Claude Desktop logs: ~/Library/Logs/Claude/"
echo "- Verify MCP server starts: node src/index.js"
echo "- Test Python bridge directly"
echo ""
echo "✅ Testing complete!"
