#!/bin/bash

echo "Diagnosing Memory API Auto-Start"
echo "================================="

# 1. Check if service is loaded
echo -e "\n1. Service Status:"
if launchctl list | grep "com.demestihas.memory-api"; then
    echo "   Service is loaded"
    launchctl list | grep "com.demestihas.memory-api"
else
    echo "   ❌ Service not in list"
fi

# 2. Check node path
echo -e "\n2. Node.js Path:"
NODE_PATH=$(which node)
echo "   System node: $NODE_PATH"
if [ "$NODE_PATH" != "/usr/local/bin/node" ]; then
    echo "   ⚠️  Node path mismatch - plist expects /usr/local/bin/node"
    echo "   Actual path: $NODE_PATH"
fi

# 3. Try to start manually via launchctl
echo -e "\n3. Starting Service:"
launchctl start com.demestihas.memory-api
sleep 2

# 4. Check if running now
echo -e "\n4. Port 7777 Status:"
if lsof -i :7777 > /dev/null 2>&1; then
    echo "   ✅ API server is now running!"
else
    echo "   ❌ Still not running"
    
    # Check logs for errors
    echo -e "\n5. Checking Error Logs:"
    if [ -f ~/Projects/demestihas-ai/mcp-smart-memory/logs/api-error.log ]; then
        echo "   Recent errors:"
        tail -5 ~/Projects/demestihas-ai/mcp-smart-memory/logs/api-error.log
    else
        echo "   No error log found"
    fi
fi

# 6. Alternative: Start directly
echo -e "\n6. Direct Start Attempt:"
cd ~/Projects/demestihas-ai/mcp-smart-memory
npm run api > /dev/null 2>&1 &
sleep 3

if curl -s http://localhost:7777/health > /dev/null 2>&1; then
    echo "   ✅ API server started successfully!"
    curl -s http://localhost:7777/health | python3 -m json.tool
else
    echo "   ❌ Direct start also failed"
fi

echo -e "\n================================="
