#!/bin/bash
echo "Monitoring EA-AI Performance..."
while true; do
    clear
    echo "EA-AI System Monitor"
    echo "==================="
    echo ""
    
    # Check if MCP server is running
    if pgrep -f "mcp-server" > /dev/null; then
        echo "✓ EA-AI MCP Server: Running"
    else
        echo "✗ EA-AI MCP Server: Not Running"
    fi
    
    # Check Claude Desktop
    if pgrep -f "Claude" > /dev/null; then
        echo "✓ Claude Desktop: Running"
    else
        echo "✗ Claude Desktop: Not Running"
    fi
    
    echo ""
    echo "Press Ctrl+C to exit"
    sleep 5
done
