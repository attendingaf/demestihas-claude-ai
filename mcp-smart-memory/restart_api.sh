#!/bin/bash

echo "Checking port 7777..."

# Find process using port 7777
PID=$(lsof -t -i:7777)

if [ -z "$PID" ]; then
    echo "No process found on port 7777"
else
    echo "Found process $PID using port 7777"
    echo "Process details:"
    ps aux | grep $PID | grep -v grep
    
    echo -e "\nKilling process $PID..."
    kill -9 $PID
    echo "Process killed. Port 7777 is now free."
fi

echo -e "\nStarting API server..."
cd ~/Projects/demestihas-ai/mcp-smart-memory
npm run api
