#!/bin/bash

# Quick Pluma Deployment - Manual Upload and Build
# Deploy Pluma agent container to VPS immediately

set -e

VPS_IP="178.156.170.161"
VPS_USER="root"
PROJECT_PATH="/root/demestihas-ai"

echo "🚀 MANUAL PLUMA DEPLOYMENT"
echo "Uploading files and building container..."

# Create deployment package
echo "📦 Creating deployment package..."
mkdir -p pluma_deploy/agents/pluma

# Copy main files
cp pluma.py pluma_deploy/
cp Dockerfile.pluma pluma_deploy/
cp requirements-pluma.txt pluma_deploy/

# Copy agent directory if it exists
if [ -d "agents/pluma" ]; then
    cp -r agents/pluma/* pluma_deploy/agents/pluma/
fi

# Create docker-compose addition
cat << 'EOF' > pluma_deploy/docker-compose-pluma.yml
  pluma:
    build:
      context: .
      dockerfile: Dockerfile.pluma
    container_name: demestihas-pluma
    networks:
      - lyco-network
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - REDIS_URL=redis://lyco-redis:6379
    volumes:
      - ./google_credentials:/app/google_credentials:ro
    healthcheck:
      test: ["CMD", "python", "-c", "import asyncio; import sys; sys.path.append('/app'); from pluma import PlumaAgent; agent = PlumaAgent(); health = asyncio.run(agent.health_check()); exit(0 if health['status'] in ['healthy', 'degraded'] else 1)"]
      interval: 30s
      timeout: 10s
      retries: 3
    depends_on:
      - redis
    restart: unless-stopped
EOF

# Upload to VPS
echo "📤 Uploading to VPS..."
tar -czf pluma_deploy.tar.gz pluma_deploy/
scp pluma_deploy.tar.gz ${VPS_USER}@${VPS_IP}:${PROJECT_PATH}/

# Clean up local files
rm -rf pluma_deploy/
rm pluma_deploy.tar.gz

# Deploy on VPS
echo "🔧 Deploying on VPS..."
ssh ${VPS_USER}@${VPS_IP} << 'ENDSSH'
set -e

cd /root/demestihas-ai

# Extract files
echo "Extracting deployment files..."
tar -xzf pluma_deploy.tar.gz
cp pluma_deploy/* ./ 2>/dev/null || true
if [ -d "pluma_deploy/agents" ]; then
    cp -r pluma_deploy/agents ./
fi

# Clean up
rm -rf pluma_deploy/
rm pluma_deploy.tar.gz

# Add Pluma to docker-compose.yml if not present
if ! grep -q "pluma:" docker-compose.yml; then
    echo "" >> docker-compose.yml
    echo "  # Pluma Agent - Email Management" >> docker-compose.yml
    cat docker-compose-pluma.yml >> docker-compose.yml
    echo "✅ Added Pluma to docker-compose.yml"
else
    echo "✅ Pluma already in docker-compose.yml"
fi

# Stop any existing Pluma container
if docker ps -q -f name=demestihas-pluma; then
    echo "Stopping existing Pluma container..."
    docker stop demestihas-pluma
fi

if docker ps -aq -f name=demestihas-pluma; then
    echo "Removing old Pluma container..."
    docker rm demestihas-pluma
fi

# Build and start Pluma
echo "🔨 Building Pluma container..."
docker build -f Dockerfile.pluma -t demestihas-pluma:latest .

echo "🚀 Starting Pluma container..."
docker-compose up -d pluma

# Wait for startup
sleep 15

# Check status
echo "📊 Checking Pluma status..."
if docker ps | grep -q demestihas-pluma; then
    echo "✅ Pluma container is running"
    
    # Test health endpoint
    if docker exec demestihas-pluma python -c "
import asyncio
import sys
sys.path.append('/app')
from pluma import PlumaAgent
agent = PlumaAgent()
health = asyncio.run(agent.health_check())
print(f'Health: {health[\"status\"]}')
exit(0 if health['status'] in ['healthy', 'degraded'] else 1)
    " 2>/dev/null; then
        echo "✅ Pluma health check passed"
    else
        echo "⚠️  Pluma health check failed (may need Gmail setup)"
    fi
    
    echo ""
    echo "🎉 PLUMA DEPLOYMENT COMPLETE!"
    echo ""
    echo "Container Status:"
    docker ps | grep -E "(yanay|pluma|redis)" | head -4
    
else
    echo "❌ Pluma container failed to start"
    echo "Logs:"
    docker logs demestihas-pluma 2>/dev/null || echo "No logs available"
    exit 1
fi

ENDSSH

echo ""
echo "🎊 Pluma Agent Deployed Successfully!"
echo ""
echo "Next steps:"
echo "1. Set up Gmail OAuth credentials"
echo "2. Test integration via @LycurgusBot"
echo "3. Run verification: ./verification/test_pluma_integration.sh"

