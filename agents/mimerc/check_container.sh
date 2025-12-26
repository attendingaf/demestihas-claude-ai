#!/bin/bash
# Check what's actually in the running container

echo "================================"
echo "🔍 Checking Container Status"
echo "================================"
echo ""

# Check if the fix is in the CONTAINER (not just the local files)
echo "Checking if persistence fix is in the RUNNING container..."
echo ""

# Look for the critical fix comment in the container's code
docker exec telegram grep -n "Don't initialize grocery_list" /app/telegram_bot.py 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Fix IS in the running container"
else
    echo "❌ Fix is NOT in the running container"
    echo "   The container is still using OLD code!"
fi

echo ""
echo "Checking container creation times..."
docker ps --filter "name=telegram" --format "table {{.Names}}\t{{.CreatedAt}}\t{{.Status}}"

echo ""
echo "================================"
echo "If fix is NOT in container:"
echo "================================"
echo "You must REBUILD (not just restart):"
echo ""
echo "1. docker-compose down"
echo "2. docker-compose build --no-cache"
echo "3. docker-compose up -d"
echo ""
echo "Just restarting keeps the OLD image!"
