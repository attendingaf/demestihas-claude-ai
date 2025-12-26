#!/bin/bash
# Start MCP Memory Server properly

echo "🚀 Starting MCP Memory Server..."

# Clean up any existing processes
echo "Cleaning up existing processes..."
lsof -ti:7777 | xargs kill -9 2>/dev/null
lsof -ti:7778 | xargs kill -9 2>/dev/null
sleep 1

# Navigate to directory
cd /Users/menedemestihas/Projects/demestihas-ai/mcp-smart-memory

# Start server
echo "Starting server on port 7777..."
npm run api

# Server will run in foreground
# Press Ctrl+C to stop
