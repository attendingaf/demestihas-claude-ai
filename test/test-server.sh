#!/bin/bash

# Test EA-AI MCP Server JSON-RPC compliance

echo "Testing EA-AI MCP Server..."
echo ""

# Test initialize
echo "Test 1: Initialize"
echo '{"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}},"jsonrpc":"2.0","id":1}' | node ../mcp-server-fixed.js 2>/dev/null | jq '.'

echo ""
echo "Test 2: List Tools"
echo '{"method":"tools/list","params":{},"jsonrpc":"2.0","id":2}' | node ../mcp-server-fixed.js 2>/dev/null | jq '.'

echo ""
echo "Test 3: Call Tool (ea_ai_memory)"
echo '{"method":"tools/call","params":{"name":"ea_ai_memory","arguments":{"action":"set","key":"test","value":"working"}},"jsonrpc":"2.0","id":3}' | node ../mcp-server-fixed.js 2>/dev/null | jq '.'

echo ""
echo "All tests completed. Check for proper JSON-RPC format:"
echo "- jsonrpc: '2.0'"
echo "- id: matching request"
echo "- result or error object"
