#!/bin/bash

# Simple start script that works immediately

echo "Starting Smart Memory API Server"
echo "================================"

# Kill any existing instance
pkill -f "node.*memory-api.js" 2>/dev/null

# Navigate to directory
cd ~/Projects/demestihas-ai/mcp-smart-memory

# Start in background
echo "Starting API server on port 7777..."
nohup npm run api > logs/api.log 2> logs/api-error.log &

# Save PID
echo $! > api.pid

# Wait for startup
sleep 3

# Test
if curl -s http://localhost:7777/health > /dev/null 2>&1; then
    echo "✅ API Server started successfully!"
    echo ""
    echo "Server PID: $(cat api.pid)"
    echo "Logs: tail -f logs/api.log"
    echo ""
    curl -s http://localhost:7777/health | python3 -m json.tool
else
    echo "❌ Failed to start. Check logs:"
    echo "  tail logs/api-error.log"
fi
