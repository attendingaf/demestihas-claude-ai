#!/bin/bash

echo "🚀 Deploying Huata Calendar fixes..."

# Navigate to project directory
cd /Users/menedemestihas/Projects/demestihas-ai/huata

# Stop existing containers
echo "📦 Stopping existing containers..."
docker-compose down

# Rebuild with no cache to ensure all changes are included
echo "🔨 Building new container with fixes..."
docker-compose build --no-cache huata

# Start containers
echo "🎯 Starting containers..."
docker-compose up -d

# Wait for startup
echo "⏰ Waiting for services to start..."
sleep 10

# Show logs to check connection status
echo "📋 Checking logs for Google Calendar connection..."
docker logs huata-calendar-agent --tail 50 | grep -E "(Google Calendar|credentials|✅|❌|🔍)"

echo ""
echo "🧪 Running connection test..."
docker exec huata-calendar-agent python claude_interface.py check

echo ""
echo "📅 Testing calendar query..."
docker exec huata-calendar-agent python claude_interface.py query --text "What's on my calendar today?"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Quick test commands:"
echo "  Check connection:  docker exec huata-calendar-agent python claude_interface.py check"
echo "  Query calendar:    docker exec huata-calendar-agent python claude_interface.py query --text 'What is free tomorrow?'"
echo "  Schedule event:    docker exec huata-calendar-agent python claude_interface.py schedule --title 'Test Event' --date '2025-09-20' --time '14:00' --duration 30"
echo "  View logs:         docker logs huata-calendar-agent --tail 100"
