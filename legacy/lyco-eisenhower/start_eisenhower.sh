#!/bin/bash
# Start Eisenhower test deployment

cd /root/lyco-eisenhower

# Check for .env
if [ ! -f .env ]; then
    echo "❌ Please create .env from .env.template first!"
    echo "   cp .env.template .env"
    echo "   nano .env"
    exit 1
fi

# Check for test bot token
if grep -q "your_test_bot_token_here" .env; then
    echo "❌ Please add your TEST bot token to .env"
    echo "   Create a new bot with @BotFather first!"
    exit 1
fi

# Stop any existing Eisenhower containers
docker-compose down 2>/dev/null || true

# Build and start
echo "🔨 Building containers..."
docker-compose build

echo "🚀 Starting Eisenhower system..."
docker-compose up -d

# Check status
sleep 5
echo -e "\n📊 Container Status:"
docker-compose ps

echo -e "\n📋 Recent Logs:"
docker-compose logs --tail=10

echo -e "\n✅ Deployment complete!"
echo "   Test your bot in Telegram"
echo "   View logs: docker-compose logs -f"
