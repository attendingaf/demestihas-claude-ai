#!/bin/bash
# Complete cleanup and restart

echo "================================"
echo "🧹 Complete Bot Cleanup"
echo "================================"
echo ""

# Step 1: Stop EVERYTHING
echo "Step 1: Stopping all bot instances..."

# Kill any local Python processes
pkill -f telegram_bot 2>/dev/null
pkill -f "8069314502" 2>/dev/null

# Stop ALL Docker containers related to mimerc
docker compose down

echo ""
echo "Step 2: Checking for any webhooks..."
# Sometimes bots can have webhooks set that interfere
curl -X POST "https://api.telegram.org/bot8069314502:AAFanF8YmQe8lOGNzvaqqxSD6bCFtvYQY3A/deleteWebhook" 2>/dev/null
echo ""

echo "Step 3: Waiting for cleanup..."
sleep 5

echo ""
echo "Step 4: Starting ONLY the Docker container..."
docker compose up -d mimerc-telegram

echo ""
echo "Step 5: Checking logs..."
sleep 3
docker compose logs --tail=20 mimerc-telegram

echo ""
echo "================================"
echo "If still getting conflicts:"
echo "================================"
echo "The bot token might be used by:"
echo "1. Another server/cloud instance"
echo "2. A different computer"
echo "3. An old cloud deployment"
echo ""
echo "Solution: Create a new bot token from @BotFather"
