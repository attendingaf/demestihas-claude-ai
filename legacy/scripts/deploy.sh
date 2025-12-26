#!/bin/bash
set -e

# Deployment script for DemestiChat
# This script is executed on the VPS to deploy new versions

REGISTRY="ghcr.io"
IMAGE_PREFIX="menedemestihas/demestihas"

echo "🚀 Starting deployment..."

# Pull latest images
echo "📦 Pulling latest images..."
docker pull ${REGISTRY}/${IMAGE_PREFIX}-agent:latest
docker pull ${REGISTRY}/${IMAGE_PREFIX}-streamlit:latest

# Stop current containers
echo "🛑 Stopping current containers..."
docker-compose down

# Start new containers
echo "▶️  Starting new containers..."
export AGENT_IMAGE="${REGISTRY}/${IMAGE_PREFIX}-agent:latest"
export STREAMLIT_IMAGE="${REGISTRY}/${IMAGE_PREFIX}-streamlit:latest"
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Health checks
echo "🏥 Running health checks..."

if curl -f http://localhost:8000/health > /dev/null 2>&1; then
  echo "✅ Agent service is healthy"
else
  echo "❌ Agent service health check failed"
  echo "🔄 Rolling back..."
  docker-compose down
  docker-compose up -d
  exit 1
fi

if curl -f http://localhost:8501 > /dev/null 2>&1; then
  echo "✅ Streamlit service is healthy"
else
  echo "❌ Streamlit service health check failed"
  echo "🔄 Rolling back..."
  docker-compose down
  docker-compose up -d
  exit 1
fi

echo "✅ Deployment successful!"
