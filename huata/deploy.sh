#!/bin/bash

# Huata Calendar Agent Deployment Script
# Deploy to VPS or local environment

set -e

echo "╔══════════════════════════════════════════╗"
echo "║     🗓️  Huata Calendar Agent Deploy      ║"
echo "╚══════════════════════════════════════════╝"

# Configuration
DEPLOY_ENV=${1:-local}
VPS_HOST="your-vps-host.com"
VPS_USER="root"
DEPLOY_PATH="/root/demestihas-ai/huata"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    echo "Checking prerequisites..."

    # Check for .env file
    if [ ! -f .env ]; then
        print_error ".env file not found. Copy .env.example and configure."
        exit 1
    fi

    # Check for credentials directory
    if [ ! -d credentials ]; then
        print_warning "credentials/ directory not found. Creating..."
        mkdir -p credentials
    fi

    # Check for Google credentials
    if [ ! -f credentials/huata-service-account.json ]; then
        print_warning "Google service account credentials not found."
        print_warning "Add credentials/huata-service-account.json for full functionality."
    fi

    print_status "Prerequisites checked"
}

# Local deployment
deploy_local() {
    echo "Deploying locally..."

    # Check prerequisites
    check_prerequisites

    # Create virtual environment if needed
    if [ ! -d venv ]; then
        print_status "Creating virtual environment..."
        python3 -m venv venv
    fi

    # Activate venv and install dependencies
    print_status "Installing dependencies..."
    source venv/bin/activate
    pip install -r requirements.txt

    # Start Redis if not running
    if ! pgrep -x "redis-server" > /dev/null; then
        print_warning "Redis not running. Starting with Docker..."
        docker run -d -p 6379:6379 --name huata-redis redis:7-alpine
    fi

    # Run the application
    print_status "Starting Huata Calendar Agent..."
    python main.py
}

# Docker deployment
deploy_docker() {
    echo "Deploying with Docker..."

    # Check prerequisites
    check_prerequisites

    # Create network if it doesn't exist
    docker network create demestihas-network 2>/dev/null || true

    # Build and start containers
    print_status "Building Docker image..."
    docker-compose build

    print_status "Starting containers..."
    docker-compose up -d

    # Check container status
    sleep 3
    if docker ps | grep -q huata-calendar-agent; then
        print_status "Huata Calendar Agent is running"
        echo ""
        echo "Access at: http://localhost:8003"
        echo "Logs: docker logs -f huata-calendar-agent"
    else
        print_error "Failed to start Huata"
        docker-compose logs
        exit 1
    fi
}

# VPS deployment
deploy_vps() {
    echo "Deploying to VPS..."

    # Check prerequisites
    check_prerequisites

    # Create deployment package
    print_status "Creating deployment package..."
    tar czf huata-deploy.tar.gz \
        *.py \
        requirements.txt \
        Dockerfile \
        docker-compose.yml \
        .env \
        credentials/

    # Upload to VPS
    print_status "Uploading to VPS..."
    scp huata-deploy.tar.gz ${VPS_USER}@${VPS_HOST}:${DEPLOY_PATH}/

    # Deploy on VPS
    print_status "Deploying on VPS..."
    ssh ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
cd ${DEPLOY_PATH}
tar xzf huata-deploy.tar.gz
docker-compose down
docker-compose build
docker-compose up -d
sleep 5
docker ps | grep huata
ENDSSH

    # Clean up
    rm huata-deploy.tar.gz

    print_status "Deployment complete"
    echo "Access at: http://${VPS_HOST}:8003"
}

# Test deployment
test_deployment() {
    echo "Testing Huata deployment..."

    API_URL=${1:-"http://localhost:8003"}

    # Test health endpoint
    print_status "Testing health endpoint..."
    curl -s ${API_URL}/ | python -m json.tool

    # Test calendar query
    print_status "Testing calendar query..."
    curl -s -X POST ${API_URL}/calendar/query \
        -H "Content-Type: application/json" \
        -d '{
            "query": "Am I free tomorrow afternoon?",
            "user": "mene"
        }' | python -m json.tool

    print_status "Tests complete"
}

# Stop deployment
stop_deployment() {
    echo "Stopping Huata..."

    if [ -f docker-compose.yml ]; then
        docker-compose down
        print_status "Docker containers stopped"
    fi

    # Stop local Python process if running
    pkill -f "python main.py" 2>/dev/null || true

    print_status "Huata stopped"
}

# Main execution
case "$DEPLOY_ENV" in
    local)
        deploy_local
        ;;
    docker)
        deploy_docker
        ;;
    vps)
        deploy_vps
        ;;
    test)
        test_deployment $2
        ;;
    stop)
        stop_deployment
        ;;
    *)
        echo "Usage: $0 {local|docker|vps|test|stop} [api_url]"
        echo ""
        echo "Commands:"
        echo "  local  - Run locally with Python"
        echo "  docker - Run with Docker Compose"
        echo "  vps    - Deploy to VPS"
        echo "  test   - Test deployment"
        echo "  stop   - Stop Huata"
        exit 1
        ;;
esac
