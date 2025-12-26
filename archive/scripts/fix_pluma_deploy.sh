#!/bin/bash

# Direct Pluma Deploy - Upload and Build Immediately
# Fix the missing Pluma container issue

set -e

VPS_IP="178.156.170.161"
VPS_USER="root"
PROJECT_PATH="/root/demestihas-ai"

echo "🔧 DIRECT PLUMA DEPLOYMENT FIX"
echo "Uploading essential files and building container..."

# Upload core files directly
echo "📤 Uploading Pluma files..."
scp pluma.py ${VPS_USER}@${VPS_IP}:${PROJECT_PATH}/
scp Dockerfile.pluma ${VPS_USER}@${VPS_IP}:${PROJECT_PATH}/
scp requirements-pluma.txt ${VPS_USER}@${VPS_IP}:${PROJECT_PATH}/requirements.txt

# Deploy immediately on VPS
ssh ${VPS_USER}@${VPS_IP} << 'ENDSSH'
set -e

cd /root/demestihas-ai

echo "🔨 Building Pluma container..."
docker build -f Dockerfile.pluma -t demestihas-pluma:latest .

echo "🚀 Starting Pluma container..."
docker run -d \
  --name demestihas-pluma \
  --network lyco-network \
  -e ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY} \
  -e REDIS_URL=redis://lyco-redis:6379 \
  --restart unless-stopped \
  demestihas-pluma:latest

echo "⏳ Waiting for container startup..."
sleep 10

echo "📊 Checking container status..."
if docker ps | grep -q demestihas-pluma; then
    echo "✅ Pluma container running"
    
    # Test basic health
    if docker exec demestihas-pluma python -c "print('Container responsive')" 2>/dev/null; then
        echo "✅ Container responding"
    else
        echo "⚠️  Container may have issues"
        docker logs --tail=5 demestihas-pluma
    fi
else
    echo "❌ Container failed to start"
    docker logs demestihas-pluma
    exit 1
fi

ENDSSH

echo "🧪 Testing Yanay-Pluma connection..."
if ssh ${VPS_USER}@${VPS_IP} "docker exec demestihas-yanay ping -c 1 demestihas-pluma" > /dev/null 2>&1; then
    echo "✅ Network communication working"
else
    echo "⚠️  Network communication failed - may need container restart"
fi

echo ""
echo "🎉 PLUMA DEPLOYMENT COMPLETE!"
echo ""
echo "Container Status:"
ssh ${VPS_USER}@${VPS_IP} "docker ps | grep -E '(yanay|pluma)'"

echo ""
echo "Ready for Gmail setup and testing!"
