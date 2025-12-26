#!/bin/bash

# Lyco 2.0 Deployment Script
# Deploys Lyco 2.0 using Docker Compose

set -e

echo "🚀 Deploying Lyco 2.0..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please run setup.sh first"
    exit 1
fi

# Load environment variables
source .env

# Validate required environment variables
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_ANON_KEY" ] || [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ Missing required environment variables in .env"
    echo "   Required: SUPABASE_URL, SUPABASE_ANON_KEY, ANTHROPIC_API_KEY"
    exit 1
fi

# Create network if it doesn't exist
echo "🔗 Creating Docker network..."
docker network create lyco-network 2>/dev/null || true

# Build and start containers
echo "🏗️  Building containers..."
docker-compose build

echo "🚀 Starting containers..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 5

# Check container status
echo "📊 Checking container status..."
docker-compose ps

# Show logs
echo "📋 Recent logs:"
docker-compose logs --tail=20

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Access the UI at: http://localhost:8000"
echo "📋 View logs: docker-compose logs -f"
echo "🛑 Stop: docker-compose down"
echo "🔄 Restart: docker-compose restart"
