#!/bin/bash

# Lyco Eisenhower Matrix Deployment Script
# For VPS deployment at 178.156.170.161

set -e

echo "🚀 Lyco Deployment Script"
echo "========================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Please copy .env.example to .env and fill in your credentials"
    exit 1
fi

# Validate required environment variables
required_vars=("TELEGRAM_BOT_TOKEN" "ANTHROPIC_API_KEY" "NOTION_API_KEY" "NOTION_TASKS_DATABASE_ID")
for var in "${required_vars[@]}"; do
    if ! grep -q "^${var}=" .env || grep -q "^${var}=your_" .env; then
        echo "❌ ${var} is not properly configured in .env"
        exit 1
    fi
done

echo "✅ Environment configuration validated"

# Stop existing containers (if any)
echo "🛑 Stopping existing containers..."
docker-compose down 2>/dev/null || true

# Clean up old images
echo "🧹 Cleaning up old images..."
docker system prune -f

# Build and start services
echo "🔨 Building Docker image..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 5

# Check service status
echo "📊 Checking service status..."
docker-compose ps

# Check logs for errors
echo "📋 Checking recent logs..."
docker-compose logs --tail=20

# Health check
if docker-compose ps | grep -q "Up"; then
    echo ""
    echo "✅ Deployment successful!"
    echo ""
    echo "📱 Your bot is now running at @LycurgusBot"
    echo "💬 Send 'help' to see available commands"
    echo ""
    echo "Useful commands:"
    echo "  docker-compose logs -f        # View logs"
    echo "  docker-compose restart lyco   # Restart bot"
    echo "  docker-compose down           # Stop services"
else
    echo ""
    echo "❌ Deployment failed! Check logs with:"
    echo "  docker-compose logs"
    exit 1
fi