#!/bin/bash

# Health Check Verification Script
# Run this after manual deployment to validate everything works

set -e

VPS_IP="178.156.170.161"
echo "🔍 Health Check Deployment Verification"
echo "========================================"

echo -e "\n1. Testing Local Health Endpoint..."
ssh root@${VPS_IP} << 'EOF'
echo "📡 Local health check:"
curl -s http://localhost:8080/health | python3 -m json.tool || {
    echo "❌ Local health endpoint failed"
    echo "🔍 Checking port status:"
    netstat -tlnp | grep :8080 || echo "Port 8080 not found"
    echo "🔍 Checking bot process:"
    ps aux | grep python | grep bot
    echo "🔍 Recent bot logs:"
    tail -10 bot.log 2>/dev/null || echo "No bot.log found"
}
EOF

echo -e "\n2. Testing External Health Endpoint..."
HEALTH_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://${VPS_IP}:8080/health)
if [ "$HEALTH_CODE" = "200" ]; then
    echo "✅ External health endpoint: HTTP $HEALTH_CODE"
    echo "📊 Health response:"
    curl -s http://${VPS_IP}:8080/health | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" 2>/dev/null || {
        echo "Raw response:"
        curl -s http://${VPS_IP}:8080/health
    }
else
    echo "❌ External health endpoint: HTTP $HEALTH_CODE"
    echo "⚠️  May be firewall issue or bot not started"
fi

echo -e "\n3. Checking Bot Process Status..."
ssh root@${VPS_IP} << 'EOF'
echo "🔍 Bot process status:"
BOT_PROCESS=$(ps aux | grep "python.*bot\.py" | grep -v grep)
if [ ! -z "$BOT_PROCESS" ]; then
    echo "✅ Bot process running:"
    echo "$BOT_PROCESS"
else
    echo "❌ No bot.py process found"
    echo "🔍 Checking for any Python processes:"
    ps aux | grep python | grep -v grep
fi
EOF

echo -e "\n4. Checking Bot Logs..."
ssh root@${VPS_IP} << 'EOF'
echo "📋 Last 10 lines of bot log:"
if [ -f bot.log ]; then
    tail -10 bot.log
else
    echo "No bot.log file found"
fi
EOF

echo -e "\n5. Final Status Summary..."
ssh root@${VPS_IP} << 'EOF'
echo "📊 Infrastructure Status:"
echo "  Directory: $(pwd)"
echo "  Bot files: $(ls -1 bot*.py | wc -l) versions"
echo "  Log file: $([ -f bot.log ] && echo "Present ($(stat -c%s bot.log) bytes)" || echo "Missing")"
echo "  Port 8080: $(netstat -tln | grep -q :8080 && echo "Listening" || echo "Not bound")"
echo "  Bot process: $(ps aux | grep "python.*bot\.py" | grep -v grep | wc -l) running"
EOF

echo -e "\n✅ Verification Complete!"
echo ""
echo "🎯 Next Steps:"
echo "  1. Test @LycurgusBot on Telegram with: 'Test health check'"
echo "  2. Verify health endpoint updates last_message timestamp"
echo "  3. Monitor for 10 minutes to ensure stability"
echo "  4. Update CURRENT_STATE.md with results"
echo ""
echo "🔗 Health URL: http://${VPS_IP}:8080/health"
echo "📱 Telegram: @LycurgusBot"

