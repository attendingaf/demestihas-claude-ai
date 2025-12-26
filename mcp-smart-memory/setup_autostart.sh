#!/bin/bash

echo "Setting up Smart Memory API Auto-Start"
echo "======================================="

# Create logs directory if it doesn't exist
mkdir -p ~/Projects/demestihas-ai/mcp-smart-memory/logs

# Copy the plist to LaunchAgents
cp ~/Projects/demestihas-ai/mcp-smart-memory/com.demestihas.memory-api.plist \
   ~/Library/LaunchAgents/

# Load the service
launchctl load ~/Library/LaunchAgents/com.demestihas.memory-api.plist

# Check if it's running
sleep 2
if launchctl list | grep -q "com.demestihas.memory-api"; then
    echo "✅ Smart Memory API will now auto-start on login"
    echo ""
    echo "Test with:"
    echo "  curl http://localhost:7777/health"
    echo ""
    echo "To stop auto-start:"
    echo "  launchctl unload ~/Library/LaunchAgents/com.demestihas.memory-api.plist"
    echo "  rm ~/Library/LaunchAgents/com.demestihas.memory-api.plist"
else
    echo "❌ Failed to set up auto-start"
fi

echo ""
echo "View logs at:"
echo "  ~/Projects/demestihas-ai/mcp-smart-memory/logs/api.log"
