#!/bin/bash

# Smart Memory API Launcher
# Place this in Login Items or use with launchd

# Wait for system to fully start
sleep 10

# Navigate to project directory
cd ~/Projects/demestihas-ai/mcp-smart-memory

# Start the API server
npm run api >> ~/Projects/demestihas-ai/mcp-smart-memory/api.log 2>&1 &

# Log the PID
echo "API Server started with PID: $!" > ~/Projects/demestihas-ai/mcp-smart-memory/api.pid

echo "Smart Memory API started on port 7777"
