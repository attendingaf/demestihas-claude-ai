#!/bin/bash

# Deploy Minimal Bot - Clean Start
# September 1, 2025

set -e

VPS_IP="178.156.170.161"
VPS_USER="root"
VPS_PATH="/root/demestihas-ai"

echo "🚀 Deploying Minimal Lyco Bot..."

# Kill any existing bot processes
echo "🛑 Stopping any existing bot processes..."
ssh ${VPS_USER}@${VPS_IP} << 'EOF'
pkill -f "python.*bot" 2>/dev/null || true
echo "✅ Existing processes stopped"
EOF

# Upload minimal bot
echo "📤 Uploading minimal bot..."
scp ~/Projects/demestihas-ai/bot_minimal.py ${VPS_USER}@${VPS_IP}:${VPS_PATH}/bot_minimal.py

# Backup current bot.py and deploy minimal version
echo "💾 Deploying minimal bot as bot.py..."
ssh ${VPS_USER}@${VPS_IP} << 'EOF'
cd /root/demestihas-ai

# Create backup of current bot.py
if [ -f bot.py ]; then
    cp bot.py bot.py.backup.broken.$(date +%Y%m%d_%H%M)
    echo "✅ Backed up broken bot.py"
fi

# Deploy minimal bot
cp bot_minimal.py bot.py
echo "✅ Minimal bot deployed as bot.py"

# Check file
ls -lh bot.py
EOF

# Start minimal bot
echo "🚀 Starting minimal bot..."
ssh ${VPS_USER}@${VPS_IP} << 'EOF'
cd /root/demestihas-ai

# Start bot
nohup python3 bot.py > bot.log 2>&1 &
NEW_PID=$!

echo "🚀 Bot started with PID: $NEW_PID"

# Wait for startup
sleep 5

# Check if running
if ps -p $NEW_PID > /dev/null 2>&1; then
    echo "✅ Bot process is running (PID: $NEW_PID)"
else
    echo "❌ Bot process died during startup"
    echo "📋 Last 10 lines of log:"
    tail -10 bot.log
    exit 1
fi
EOF

# Test basic functionality
echo -e "\n✅ Minimal Bot Deployment Complete!"
echo ""
echo "🧪 **Testing Steps:**"
echo "1. Open Telegram and message @LycurgusBot"  
echo "2. Send: /start"
echo "3. Should get welcome message with instructions"
echo "4. Send: 'Test minimal bot'"
echo "5. Should get task captured response with buttons"
echo ""
echo "📊 **What This Bot Does:**"
echo "✅ Receives Telegram messages"
echo "✅ Basic task extraction (simple)"  
echo "✅ Interactive buttons"
echo "✅ Clean error handling"
echo "❌ Notion integration (coming next)"
echo "❌ AI parsing (coming next)"
echo ""
echo "🔗 **Bot Status:** @LycurgusBot should now be responding"

