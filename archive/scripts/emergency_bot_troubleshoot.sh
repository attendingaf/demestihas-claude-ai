#!/bin/bash

# Emergency Bot Troubleshooting Script
# Run this immediately when bot stops responding on Telegram

set -e

VPS_IP="178.156.170.161"
echo "🚨 EMERGENCY: Bot Not Responding on Telegram"
echo "============================================="

echo -e "\n1. Checking Bot Process Status..."
ssh root@${VPS_IP} << 'EOF'
echo "🔍 Current bot processes:"
ps aux | grep python | grep bot

echo -e "\n🔍 Any Python processes running:"
ps aux | grep python | grep -v grep

echo -e "\n🔍 Recent bot logs (last 20 lines):"
if [ -f /root/demestihas-ai/bot.log ]; then
    tail -20 /root/demestihas-ai/bot.log
else
    echo "No bot.log found"
    echo "🔍 Checking for any log files:"
    ls -la *.log 2>/dev/null || echo "No log files found"
fi
EOF

echo -e "\n2. Checking File Status..."
ssh root@${VPS_IP} << 'EOF'
cd /root/demestihas-ai
echo "🔍 Bot files present:"
ls -la bot*.py

echo -e "\n🔍 Current bot.py size and date:"
ls -lh bot.py

echo -e "\n🔍 Environment file present:"
ls -la .env || echo ".env file missing!"
EOF

echo -e "\n3. Testing Bot Startup Manually..."
ssh root@${VPS_IP} << 'EOF'
cd /root/demestihas-ai
echo "🚀 Attempting manual bot startup (will run for 30 seconds)..."
timeout 30s python3 bot.py || {
    echo "❌ Bot failed to start!"
    echo "🔍 Python error check:"
    python3 -c "import telegram, anthropic, notion_client; print('All imports OK')" 2>&1 || echo "Import errors detected"
}
EOF

echo -e "\n4. Quick Fix Options..."
echo "🛠️  OPTION 1: Restart with backup (safest):"
echo "   ssh root@${VPS_IP}"
echo "   cd /root/demestihas-ai"
echo "   cp bot.py.backup.[latest_timestamp] bot.py"
echo "   nohup python3 bot.py > bot.log 2>&1 &"

echo -e "\n🛠️  OPTION 2: Fix current version:"
echo "   ssh root@${VPS_IP}"
echo "   cd /root/demestihas-ai"
echo "   # Check error in bot.log"
echo "   tail -50 bot.log"
echo "   # Fix issue and restart"

echo -e "\n🛠️  OPTION 3: Use original working version:"
echo "   ssh root@${VPS_IP}"
echo "   cd /root/demestihas-ai"
echo "   # If you know which version was working:"
echo "   cp bot_v5.py bot.py  # or whatever version was stable"
echo "   nohup python3 bot.py > bot.log 2>&1 &"

echo -e "\n⚡ IMMEDIATE ACTION NEEDED:"
echo "1. SSH to VPS and check bot.log for errors"
echo "2. If critical family dependency, restore backup immediately"  
echo "3. Report back what you see in the logs"

