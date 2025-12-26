#!/bin/bash
# Debug and restart MiMerc with conversational bot

echo "🔍 MiMerc Bot Diagnostic & Fix"
echo "==============================="
echo ""

# Check which telegram_bot.py is in the container
echo "📦 Checking which bot version is deployed..."
echo ""

# Look for signs of conversational vs command bot
echo "🔎 Checking bot characteristics:"
if docker exec mimerc-telegram grep -q "handle_message" telegram_bot.py 2>/dev/null; then
    echo "✅ Found handle_message function (conversational)"
else
    echo "❌ Missing handle_message function"
fi

if docker exec mimerc-telegram grep -q "CommandHandler.*list" telegram_bot.py 2>/dev/null; then
    echo "⚠️  Found /list command handler (old command-based version)"
else
    echo "✅ No /list command (pure conversational)"
fi

echo ""
echo "==============================="
echo ""

# Stop and rebuild with latest code
echo "🔄 Rebuilding with latest conversational bot..."
echo ""

# Stop current bot
echo "1️⃣ Stopping current bot..."
docker-compose stop mimerc-telegram

# Remove old container to force fresh build
echo "2️⃣ Removing old container..."
docker-compose rm -f mimerc-telegram

# Rebuild with no cache to ensure latest code
echo "3️⃣ Building fresh container..."
docker-compose build --no-cache mimerc-telegram

# Start the new container
echo "4️⃣ Starting conversational bot..."
docker-compose up -d mimerc-telegram

echo ""
echo "⏳ Waiting for bot to initialize..."
sleep 5

# Check new logs
echo ""
echo "📜 New Bot Startup Logs:"
echo "------------------------"
docker-compose logs --tail=20 mimerc-telegram

echo ""
echo "==============================="
echo ""

# Test the bot
echo "✅ Bot has been rebuilt and restarted!"
echo ""
echo "🧪 To test:"
echo "1. Open Telegram"
echo "2. Send a simple message like 'hi' or 'what's on my list'"
echo "3. You should see processing logs here:"
echo ""
echo "   docker-compose logs -f mimerc-telegram"
echo ""
echo "📝 The conversational bot should:"
echo "- Respond to natural language"
echo "- NOT require /commands (except /start)"
echo "- Show clean lists without duplicates"
echo ""
echo "⚠️  Note: Your bot token was visible in logs."
echo "   Consider regenerating it with @BotFather after testing."
