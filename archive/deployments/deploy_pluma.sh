#!/bin/bash

# Deploy Pluma Agent to VPS
# This script builds and deploys the Pluma agent container

set -e

# Configuration
VPS_IP="178.156.170.161"
VPS_USER="root"
PROJECT_PATH="/root/demestihas-ai"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Deploying Pluma Agent to VPS${NC}"

# Function to print status
print_status() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we can connect to VPS
print_status "Testing VPS connection..."
if ! ssh -o ConnectTimeout=10 ${VPS_USER}@${VPS_IP} "echo 'Connection successful'" > /dev/null 2>&1; then
    print_error "Cannot connect to VPS. Check SSH connection."
    exit 1
fi
print_success "VPS connection verified"

# Upload Pluma agent files
print_status "Uploading Pluma agent files..."

# Create local tar of Pluma files
tar -czf pluma-agent.tar.gz \
    pluma.py \
    agents/pluma/ \
    Dockerfile.pluma \
    requirements-pluma.txt \
    docker-compose-pluma-addition.yml \
    pluma_yanay_integration.py

# Upload to VPS
scp pluma-agent.tar.gz ${VPS_USER}@${VPS_IP}:${PROJECT_PATH}/
rm pluma-agent.tar.gz

print_success "Files uploaded"

# Deploy on VPS
print_status "Deploying Pluma agent on VPS..."

ssh ${VPS_USER}@${VPS_IP} << 'ENDSSH'
set -e

cd /root/demestihas-ai

# Extract uploaded files
echo "Extracting Pluma agent files..."
tar -xzf pluma-agent.tar.gz
rm pluma-agent.tar.gz

# Update requirements.txt for Pluma
echo "Updating requirements..."
if [ ! -f requirements.txt ]; then
    cp requirements-pluma.txt requirements.txt
else
    # Merge requirements
    cat requirements-pluma.txt >> requirements.txt
    sort requirements.txt | uniq > requirements_temp.txt
    mv requirements_temp.txt requirements.txt
fi

# Add Pluma service to docker-compose.yml
echo "Updating docker-compose.yml..."

# Check if Pluma service already exists
if ! grep -q "pluma:" docker-compose.yml; then
    echo "" >> docker-compose.yml
    echo "  # Pluma Agent - Email Management and Executive Assistant" >> docker-compose.yml
    cat docker-compose-pluma-addition.yml >> docker-compose.yml
    echo "Added Pluma service to docker-compose.yml"
else
    echo "Pluma service already exists in docker-compose.yml"
fi

# Build Pluma container
echo "Building Pluma container..."
docker build -f Dockerfile.pluma -t demestihas-pluma:latest .

# Check if Pluma container is running and stop it
if [ "$(docker ps -q -f name=demestihas-pluma)" ]; then
    echo "Stopping existing Pluma container..."
    docker stop demestihas-pluma
fi

# Remove old Pluma container if it exists
if [ "$(docker ps -aq -f name=demestihas-pluma)" ]; then
    echo "Removing old Pluma container..."
    docker rm demestihas-pluma
fi

# Start Pluma service
echo "Starting Pluma agent..."
docker-compose up -d pluma

# Wait a moment for startup
sleep 10

# Check Pluma health
echo "Checking Pluma agent health..."
if docker ps | grep -q demestihas-pluma; then
    echo "✅ Pluma agent container is running"
    
    # Test health endpoint (may fail initially)
    set +e
    for i in {1..3}; do
        if docker exec demestihas-pluma python -c "
import asyncio
import sys
sys.path.append('/app')
from pluma import PlumaAgent
agent = PlumaAgent()
health = asyncio.run(agent.health_check())
print(f'Health status: {health[\"status\"]}')
exit(0 if health['status'] in ['healthy', 'degraded'] else 1)
        "; then
            echo "✅ Pluma agent health check passed"
            break
        else
            echo "⚠️  Pluma agent health check failed, attempt $i/3"
            sleep 5
        fi
        
        if [ $i -eq 3 ]; then
            echo "❌ Pluma agent health check failed after 3 attempts"
            echo "Container logs:"
            docker logs --tail=20 demestihas-pluma
        fi
    done
    set -e
else
    echo "❌ Pluma agent container failed to start"
    echo "Docker logs:"
    docker logs demestihas-pluma
    exit 1
fi

echo ""
echo "🎉 Pluma agent deployment completed!"
echo ""
echo "Next steps:"
echo "1. Set up Gmail API credentials (see Google Cloud Console)"
echo "2. Test email drafting via @LycurgusBot"
echo "3. Test meeting notes processing"
echo "4. Monitor logs: docker logs -f demestihas-pluma"

ENDSSH

print_success "Pluma agent deployed successfully!"

# Display connection info
echo ""
echo -e "${GREEN}📊 Pluma Agent Status${NC}"
echo "Container: demestihas-pluma"
echo "Health Check: Run 'docker logs demestihas-pluma' on VPS"
echo "Test Command: Message @LycurgusBot with 'draft email reply'"

# Show container status
print_status "Checking final container status..."
ssh ${VPS_USER}@${VPS_IP} "cd ${PROJECT_PATH} && docker ps | grep -E '(yanay|pluma)'"

echo ""
echo -e "${GREEN}🎊 Deployment Complete!${NC}"
echo ""
echo "Pluma agent is now integrated with your multi-agent system:"
echo "• Email drafting with Gmail API integration"  
echo "• Meeting notes processing via Hermes"
echo "• Smart inbox management"
echo "• Integrated with Yanay.ai orchestration"
echo ""
echo "Cost estimate: ~$5-10/month (Claude API + Gmail API)"
echo "Replaces: \$336/year Fyxer AI subscription"
echo ""
echo -e "${YELLOW}Next: Set up Gmail OAuth credentials and test functionality${NC}"
