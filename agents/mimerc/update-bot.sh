#!/bin/bash
# Quick update script for MiMerc Telegram Bot

echo "🔄 Updating MiMerc Telegram Bot..."
echo ""

cd /Users/menedemestihas/Projects/demestihas-ai/agents/mimerc

# Stop the current bot
echo "🛑 Stopping current bot..."
docker-compose stop mimerc-telegram

# Rebuild with the fix
echo "🔨 Rebuilding with bug fix..."
docker-compose build mimerc-telegram

# Start the updated bot
echo "🚀 Starting updated bot..."
docker-compose up -d mimerc-telegram

echo ""
echo "✅ Bot updated successfully!"
echo ""
echo "📜 Check logs to verify:"
echo "   docker-compose logs -f mimerc-telegram"
echo ""
echo "🧪 Test the fix:"
echo "   1. Open Telegram"
echo "   2. Send: /list"
echo "   3. Verify only grocery items are shown (no 'Added X to list' messages)"
echo ""
echo "The bot should now display lists correctly! 🎉"
