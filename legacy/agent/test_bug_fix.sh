#!/bin/bash
#
# Quick Test Script for General Agent Bug Fix
# Tests the knowledge retrieval functionality after deployment
#

set -e

echo "=========================================="
echo "General Agent Bug Fix - Test Suite"
echo "Date: $(date)"
echo "=========================================="
echo ""

# Configuration
AGENT_URL="${AGENT_URL:-http://localhost:8000}"
USER_ID="${TEST_USER_ID:-default_user}"
JWT_TOKEN="${JWT_TOKEN:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if JWT token is available
if [ -z "$JWT_TOKEN" ]; then
    echo -e "${YELLOW}⚠️  WARNING: JWT_TOKEN not set${NC}"
    echo "Set JWT_TOKEN environment variable for authenticated testing"
    echo "Example: export JWT_TOKEN=your_token_here"
    echo ""
    echo "Attempting to continue without authentication..."
    AUTH_HEADER=""
else
    AUTH_HEADER="-H \"Authorization: Bearer $JWT_TOKEN\""
fi

echo "Test Configuration:"
echo "  Agent URL: $AGENT_URL"
echo "  User ID: $USER_ID"
echo "  Auth: ${JWT_TOKEN:+Enabled}${JWT_TOKEN:-Disabled}"
echo ""

# Function to test a query
test_query() {
    local test_name=$1
    local query=$2
    local expected_pattern=$3

    echo "=========================================="
    echo "TEST: $test_name"
    echo "Query: $query"
    echo ""

    # Make the request
    response=$(curl -s -X POST "$AGENT_URL/chat" \
        -H "Content-Type: application/json" \
        ${AUTH_HEADER} \
        -d "{\"message\": \"$query\", \"user_id\": \"$USER_ID\"}" \
        2>&1)

    # Check if request succeeded
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ FAILED: Request failed${NC}"
        echo "Error: $response"
        return 1
    fi

    # Pretty print JSON response
    echo "Response:"
    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
    echo ""

    # Check for expected pattern
    if [ -n "$expected_pattern" ]; then
        if echo "$response" | grep -q "$expected_pattern"; then
            echo -e "${GREEN}✅ PASSED: Found expected pattern '$expected_pattern'${NC}"
            return 0
        else
            echo -e "${RED}❌ FAILED: Expected pattern '$expected_pattern' not found${NC}"
            return 1
        fi
    else
        echo -e "${GREEN}✅ Request completed${NC}"
        return 0
    fi
}

# Test 1: Health Check
echo "=========================================="
echo "TEST 0: Health Check"
echo ""

health_response=$(curl -s "$AGENT_URL/health" 2>&1)
echo "Health Status:"
echo "$health_response" | python3 -m json.tool 2>/dev/null || echo "$health_response"
echo ""

if echo "$health_response" | grep -q "ok"; then
    echo -e "${GREEN}✅ Agent service is healthy${NC}"
else
    echo -e "${RED}❌ Agent service health check failed${NC}"
    exit 1
fi
echo ""

# Test 2: Knowledge Retrieval (PRIMARY BUG FIX TEST)
test_query \
    "Knowledge Retrieval - Primary Fix" \
    "Tell me three random things you know about me" \
    "knowledge\|facts\|know"

echo ""

# Test 3: Alternative Knowledge Query
test_query \
    "Knowledge Retrieval - Alternative Phrasing" \
    "What do you know about me?" \
    ""

echo ""

# Test 4: Conversational Fallback (No Tool Call Expected)
test_query \
    "Conversational Fallback" \
    "What is the meaning of life?" \
    ""

echo ""

# Test 5: Check Logs for Tool Calls
echo "=========================================="
echo "TEST: Log Verification"
echo ""

if command -v docker &> /dev/null; then
    echo "Checking agent logs for tool call evidence..."

    # Check for tool calls in last 100 log lines
    tool_calls=$(docker logs demestihas-agent --tail 100 2>&1 | grep -c "🛠️" || echo "0")
    tool_executions=$(docker logs demestihas-agent --tail 100 2>&1 | grep -c "Executing tool: get_user_knowledge" || echo "0")
    tool_success=$(docker logs demestihas-agent --tail 100 2>&1 | grep -c "✅ Retrieved" || echo "0")

    echo "Tool Call Metrics (last 100 log lines):"
    echo "  Tool call requests: $tool_calls"
    echo "  Tool executions: $tool_executions"
    echo "  Successful retrievals: $tool_success"
    echo ""

    if [ "$tool_executions" -gt 0 ]; then
        echo -e "${GREEN}✅ PASSED: Tool calls detected in logs${NC}"

        # Show last 5 tool-related log lines
        echo ""
        echo "Recent tool-related logs:"
        docker logs demestihas-agent --tail 100 2>&1 | grep -E "(🛠️|Executing tool|Retrieved)" | tail -5
    else
        echo -e "${YELLOW}⚠️  WARNING: No tool calls detected in recent logs${NC}"
        echo "This may be normal if no knowledge queries were made recently"
    fi
else
    echo -e "${YELLOW}⚠️  Docker not available - skipping log verification${NC}"
fi

echo ""

# Test 6: FalkorDB Connection Verification
echo "=========================================="
echo "TEST: FalkorDB Connection"
echo ""

if command -v docker &> /dev/null; then
    echo "Checking FalkorDB connectivity..."

    falkordb_status=$(docker logs demestihas-agent --tail 200 2>&1 | grep -E "FalkorDB.*connected|FalkorDB.*initialized" | tail -1 || echo "")

    if [ -n "$falkordb_status" ]; then
        echo "FalkorDB Status:"
        echo "$falkordb_status"
        echo ""
        echo -e "${GREEN}✅ PASSED: FalkorDB connection verified${NC}"
    else
        echo -e "${YELLOW}⚠️  WARNING: Could not verify FalkorDB connection from logs${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Docker not available - skipping FalkorDB verification${NC}"
fi

echo ""

# Summary
echo "=========================================="
echo "TEST SUITE COMPLETE"
echo "=========================================="
echo ""
echo "Next Steps:"
echo "1. Review test results above"
echo "2. Check agent logs: docker logs demestihas-agent --tail 50"
echo "3. Monitor for tool calls: docker logs -f demestihas-agent | grep '🛠️'"
echo "4. Test in Streamlit UI for full user experience"
echo ""
echo "Troubleshooting:"
echo "- If 'I don't know anything' appears: Check FalkorDB connection"
echo "- If no tool calls in logs: Verify tools are bound to general agent"
echo "- If tool execution fails: Check falkordb_manager connectivity"
echo ""
echo "Cleanup commands:"
echo "  python /root/agent/cleanup_db.py --pattern 'bad_data' --dry-run"
echo "  python /root/agent/cleanup_mem0.py --user '$USER_ID' --dry-run"
echo ""
