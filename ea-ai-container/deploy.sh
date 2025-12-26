#!/bin/bash

# EA-AI Container Deployment Script
# This script builds and deploys the EA-AI containerized subagent

set -e

echo "🚀 Deploying EA-AI Containerized Subagent..."
echo "==========================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop."
    exit 1
fi

# Navigate to the container directory
cd "$(dirname "$0")"

# Create necessary directories
echo "📁 Creating required directories..."
mkdir -p state logs cache

# Stop existing containers if running
echo "🛑 Stopping existing containers..."
docker-compose down 2>/dev/null || true

# Build the container
echo "🔨 Building EA-AI container..."
docker-compose build

# Start the services
echo "🚀 Starting services..."
docker-compose up -d

# Wait for container to be healthy
echo "⏳ Waiting for container to be healthy..."
sleep 5

# Check health
echo "🏥 Checking container health..."
HEALTH=$(docker exec ea-ai-agent node -e "
const http = require('http');
http.get('http://localhost:8080/health', (res) => {
  let data = '';
  res.on('data', chunk => data += chunk);
  res.on('end', () => {
    const health = JSON.parse(data);
    console.log(JSON.stringify(health, null, 2));
  });
}).on('error', err => {
  console.log(JSON.stringify({status: 'error', message: err.message}));
});
" 2>/dev/null || echo '{"status": "error"}')

echo "$HEALTH"

# Run tests
echo ""
echo "🧪 Running integration tests..."
npm test

echo ""
echo "✅ EA-AI Container deployment complete!"
echo ""
echo "📋 Quick Reference:"
echo "  - Health check: curl http://localhost:8080/health"
echo "  - View logs: docker logs ea-ai-agent"
echo "  - Stop services: docker-compose down"
echo "  - Test integration: node test-integration.js"
echo ""
echo "🔗 Integration with Claude Desktop:"
echo "  1. Use the claude-integration.js module in your MCP tools"
echo "  2. The container exposes HTTP API on port 8080"
echo "  3. All EA-AI tools are now available via HTTP bridge"
echo ""
echo "📊 Available endpoints:"
echo "  - POST /memory - Memory operations"
echo "  - POST /route - Agent routing"
echo "  - GET /family/:member - Family context"
echo "  - POST /calendar/check - Calendar operations"
echo "  - POST /task/adhd - ADHD task management"
