#!/bin/bash

# Health Check Deployment Script - Single Agent System
# Test of configuration-driven infrastructure
# Date: September 1, 2025

set -e  # Exit on any error

echo "🔄 Starting Health Check Deployment..."
echo "📋 Reading system configuration..."

VPS_IP="178.156.170.161"
VPS_USER="root"
VPS_PATH="/root/demestihas-ai"

echo "🔍 Step 1: Identify current bot process..."
ssh ${VPS_USER}@${VPS_IP} << 'EOF'
cd /root/demestihas-ai
echo "Current directory contents:"
ls -la bot*.py

echo -e "\n🔍 Checking for running bot processes..."
BOT_PID=$(ps aux | grep "python.*bot\.py" | grep -v grep | awk '{print $2}' | head -1)

if [ ! -z "$BOT_PID" ]; then
    echo "✅ Found bot process: PID $BOT_PID"
    ps aux | grep $BOT_PID | grep -v grep
else
    echo "⚠️  No bot.py process found, checking for bot_v* processes..."
    ps aux | grep "python.*bot_v" | grep -v grep
fi
EOF

echo -e "\n💾 Step 2: Backup current bot.py..."
ssh ${VPS_USER}@${VPS_IP} << 'EOF'
cd /root/demestihas-ai
if [ -f bot.py ]; then
    TIMESTAMP=$(date +%Y%m%d_%H%M)
    cp bot.py bot.py.backup.$TIMESTAMP
    echo "✅ Backup created: bot.py.backup.$TIMESTAMP"
else
    echo "⚠️  No bot.py found to backup"
fi
EOF

echo -e "\n🔄 Step 3: Deploy health check version..."
ssh ${VPS_USER}@${VPS_IP} << 'EOF'
cd /root/demestihas-ai
if [ -f bot_v5_with_health.py ]; then
    cp bot_v5_with_health.py bot.py
    echo "✅ Health check version deployed as bot.py"
    echo "File size: $(du -h bot.py | cut -f1)"
else
    echo "❌ bot_v5_with_health.py not found!"
    exit 1
fi
EOF

echo -e "\n⏹️  Step 4: Stop current bot process..."
ssh ${VPS_USER}@${VPS_IP} << 'EOF'
cd /root/demestihas-ai
BOT_PID=$(ps aux | grep "python.*bot\.py" | grep -v grep | awk '{print $2}' | head -1)

if [ ! -z "$BOT_PID" ]; then
    echo "🛑 Stopping bot process: PID $BOT_PID"
    kill -TERM $BOT_PID
    sleep 3
    
    # Check if it's still running
    if ps -p $BOT_PID > /dev/null 2>&1; then
        echo "⚠️  Process still running, forcing kill..."
        kill -KILL $BOT_PID
        sleep 2
    fi
    
    echo "✅ Bot process stopped"
else
    echo "ℹ️  No bot.py process found to stop"
fi
EOF

echo -e "\n🚀 Step 5: Start bot with health check..."
ssh ${VPS_USER}@${VPS_IP} << 'EOF'
cd /root/demestihas-ai

# Start bot in background
echo "🚀 Starting bot with health check..."
nohup python3 bot.py > bot.log 2>&1 &
NEW_PID=$!

echo "✅ Bot started with PID: $NEW_PID"
echo "📋 Log location: /root/demestihas-ai/bot.log"

# Wait for startup
echo "⏳ Waiting for bot to initialize..."
sleep 10

# Check if process is still running
if ps -p $NEW_PID > /dev/null 2>&1; then
    echo "✅ Bot process is running"
else
    echo "❌ Bot process died during startup!"
    echo "📋 Last 10 lines of log:"
    tail -10 bot.log
    exit 1
fi
EOF

echo -e "\n🔍 Step 6: Test health endpoint..."

# Test health endpoint locally on VPS
ssh ${VPS_USER}@${VPS_IP} << 'EOF'
cd /root/demestihas-ai
echo "🔍 Testing health endpoint locally..."
sleep 5  # Give the health server time to start

HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health)
if [ "$HEALTH_RESPONSE" = "200" ]; then
    echo "✅ Health endpoint responding: HTTP $HEALTH_RESPONSE"
    echo "📋 Health check response:"
    curl -s http://localhost:8080/health | python3 -m json.tool || echo "Response: $(curl -s http://localhost:8080/health)"
else
    echo "❌ Health endpoint not responding: HTTP $HEALTH_RESPONSE"
    echo "📋 Checking if port 8080 is in use..."
    netstat -tlnp | grep :8080 || echo "Port 8080 not found in netstat"
fi
EOF

# Test external access
echo -e "\n🌐 Testing external health endpoint..."
EXTERNAL_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://${VPS_IP}:8080/health)
if [ "$EXTERNAL_HEALTH" = "200" ]; then
    echo "✅ External health endpoint working: HTTP $EXTERNAL_HEALTH"
    echo "📋 External health check response:"
    curl -s http://${VPS_IP}:8080/health | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" || echo "Raw response: $(curl -s http://${VPS_IP}:8080/health)"
else
    echo "❌ External health endpoint not accessible: HTTP $EXTERNAL_HEALTH"
    echo "⚠️  This may be due to firewall settings"
fi

echo -e "\n🧪 Step 7: Verify bot functionality..."
echo "📱 Please test @LycurgusBot on Telegram with a simple message like: 'Buy milk'"
echo "⏳ Waiting 30 seconds for you to test..."

# Give user time to test
for i in {30..1}; do
    echo -ne "\r⏳ Testing window: $i seconds remaining..."
    sleep 1
done
echo -ne "\r✅ Testing window complete.                    \n"

# Final status check
ssh ${VPS_USER}@${VPS_IP} << 'EOF'
cd /root/demestihas-ai
echo -e "\n📊 Final Status Report:"
echo "🔍 Bot process status:"
ps aux | grep "python.*bot\.py" | grep -v grep || echo "No bot.py process found"

echo -e "\n📋 Recent log entries:"
tail -5 bot.log

echo -e "\n🔍 Port 8080 status:"
netstat -tlnp | grep :8080 || echo "Port 8080 not bound"
EOF

echo -e "\n✅ Health Check Deployment Complete!"
echo ""
echo "🔗 Health Endpoint: http://${VPS_IP}:8080/health"
echo "📱 Telegram Bot: @LycurgusBot"
echo "📋 VPS Logs: ssh ${VPS_USER}@${VPS_IP} 'tail -f /root/demestihas-ai/bot.log'"
echo ""
echo "🎯 Next Steps:"
echo "  1. Verify bot responds to Telegram messages"  
echo "  2. Monitor health endpoint for 24 hours"
echo "  3. Update CURRENT_STATE.md with deployment success"
echo "  4. Proceed to LangChain base agent implementation"

