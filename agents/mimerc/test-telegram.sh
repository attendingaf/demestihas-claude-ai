#!/bin/bash
# Quick test script for MiMerc Telegram Bot

echo "🧪 MiMerc Telegram Bot Test"
echo "=========================="
echo ""

# Check environment
if [ -f ".env" ]; then
    source .env
    
    if [ "$TELEGRAM_BOT_TOKEN" = "YOUR_BOT_TOKEN_HERE" ] || [ -z "$TELEGRAM_BOT_TOKEN" ]; then
        echo "❌ Telegram bot token not configured"
        echo "   Run ./activate-mimerc.sh first"
        exit 1
    fi
    
    echo "✅ Configuration loaded"
else
    echo "❌ .env file not found"
    exit 1
fi

# Test bot token validity
echo ""
echo "🔍 Testing bot token..."
RESPONSE=$(curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe")

if echo "$RESPONSE" | grep -q '"ok":true'; then
    BOT_USERNAME=$(echo "$RESPONSE" | grep -o '"username":"[^"]*' | sed 's/"username":"//')
    BOT_NAME=$(echo "$RESPONSE" | grep -o '"first_name":"[^"]*' | sed 's/"first_name":"//')
    
    echo "✅ Bot token is valid!"
    echo ""
    echo "📱 Bot Details:"
    echo "   Name: $BOT_NAME"
    echo "   Username: @$BOT_USERNAME"
    echo "   Link: https://t.me/$BOT_USERNAME"
else
    echo "❌ Invalid bot token or API error"
    echo "   Response: $RESPONSE"
    exit 1
fi

# Check Docker status
echo ""
echo "🐳 Docker Status:"
if docker ps | grep -q "mimerc-telegram"; then
    echo "✅ MiMerc Telegram bot is running"
    docker ps | grep mimerc-telegram
elif docker ps | grep -q "mimerc-agent"; then
    echo "✅ MiMerc agent is running (but Telegram bot is not)"
    docker ps | grep mimerc-agent
else
    echo "⚠️  MiMerc containers are not running"
fi

if docker ps | grep -q "mimerc-postgres"; then
    echo "✅ PostgreSQL container is running"
else
    echo "⚠️  PostgreSQL container is not running"
fi

echo ""
echo "📊 Quick Health Check Complete!"
echo ""
echo "To start chatting:"
echo "1. Open Telegram"
echo "2. Go to: https://t.me/$BOT_USERNAME"
echo "3. Send /start"
