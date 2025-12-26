#!/bin/bash

echo "Fixing Memory API Auto-Start"
echo "============================"

# 1. Find actual node path
NODE_PATH=$(which node)
echo "Found node at: $NODE_PATH"

# 2. Unload existing service if present
echo -e "\nRemoving old service..."
launchctl unload ~/Library/LaunchAgents/com.demestihas.memory-api.plist 2>/dev/null
rm -f ~/Library/LaunchAgents/com.demestihas.memory-api.plist

# 3. Create updated plist with correct node path
echo -e "\nCreating updated service configuration..."
cat > ~/Library/LaunchAgents/com.demestihas.memory-api.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.demestihas.memory-api</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>$NODE_PATH</string>
        <string>$HOME/Projects/demestihas-ai/mcp-smart-memory/memory-api.js</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>$HOME/Projects/demestihas-ai/mcp-smart-memory</string>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    
    <key>StandardOutPath</key>
    <string>$HOME/Projects/demestihas-ai/mcp-smart-memory/logs/api.log</string>
    
    <key>StandardErrorPath</key>
    <string>$HOME/Projects/demestihas-ai/mcp-smart-memory/logs/api-error.log</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>NODE_ENV</key>
        <string>production</string>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.nvm/versions/node/v22.17.1/bin</string>
    </dict>
</dict>
</plist>
EOF

# 4. Create logs directory
mkdir -p ~/Projects/demestihas-ai/mcp-smart-memory/logs

# 5. Load the new service
echo -e "\nLoading service..."
launchctl load ~/Library/LaunchAgents/com.demestihas.memory-api.plist

# 6. Start it immediately
echo -e "\nStarting service..."
launchctl start com.demestihas.memory-api

# 7. Wait and check
sleep 3
echo -e "\nChecking status..."

if curl -s http://localhost:7777/health > /dev/null 2>&1; then
    echo "✅ SUCCESS! API server is running"
    echo ""
    curl -s http://localhost:7777/health | python3 -m json.tool
    echo ""
    echo "The API will now auto-start on login."
else
    echo "⚠️  Service configured but not responding yet"
    echo ""
    echo "Starting manually as fallback..."
    cd ~/Projects/demestihas-ai/mcp-smart-memory
    npm run api > logs/api.log 2> logs/api-error.log &
    
    sleep 3
    if curl -s http://localhost:7777/health > /dev/null 2>&1; then
        echo "✅ Manual start successful!"
    else
        echo "❌ Check logs at:"
        echo "  ~/Projects/demestihas-ai/mcp-smart-memory/logs/api-error.log"
    fi
fi

echo ""
echo "============================"
echo "Commands:"
echo "• Check status:  launchctl list | grep memory-api"
echo "• View logs:     tail -f ~/Projects/demestihas-ai/mcp-smart-memory/logs/api.log"
echo "• Stop service:  launchctl stop com.demestihas.memory-api"
echo "• Remove:        launchctl unload ~/Library/LaunchAgents/com.demestihas.memory-api.plist"
