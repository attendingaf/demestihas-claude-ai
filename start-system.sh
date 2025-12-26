#!/bin/bash

# Startup script for Demestihas AI System
# This script starts all services in the correct order with health checks

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}    Demestihas AI System Startup${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Function to check if Docker is running
check_docker() {
    if ! docker info &> /dev/null; then
        echo -e "${RED}❌ Docker is not running!${NC}"
        echo "Please start Docker Desktop and try again."
        exit 1
    fi
    echo -e "${GREEN}✅ Docker is running${NC}"
}

# Function to wait for a service to be healthy
wait_for_service() {
    local service=$1
    local max_attempts=30
    local attempt=1

    echo -n "  Waiting for $service to be healthy"

    while [ $attempt -le $max_attempts ]; do
        if docker-compose ps | grep "$service" | grep -q "healthy\|running"; then
            echo -e " ${GREEN}✅${NC}"
            return 0
        fi
        echo -n "."
        sleep 2
        ((attempt++))
    done

    echo -e " ${RED}❌ Timeout${NC}"
    return 1
}

# Check Docker
echo "Checking prerequisites..."
check_docker
echo ""

# Create necessary directories
echo "Creating directories..."
mkdir -p logs/{lyco-v2,huata,mcp-memory,ea-ai-bridge,status-dashboard}
mkdir -p mcp-smart-memory/credentials
mkdir -p huata/credentials
mkdir -p agents/lyco/lyco-v2/credentials
echo -e "${GREEN}✅ Directories created${NC}"
echo ""

# Check for .env files
echo "Checking configuration files..."
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from .env.shared...${NC}"
    if [ -f ".env.shared" ]; then
        cp .env.shared .env
        echo "Please edit .env file with your API keys and configuration"
        read -p "Press Enter when ready to continue..."
    else
        echo -e "${RED}❌ .env.shared not found!${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✅ Configuration files ready${NC}"
echo ""

# Stop any existing containers
echo "Cleaning up existing containers..."
docker-compose down --remove-orphans 2>/dev/null || true
echo -e "${GREEN}✅ Cleanup complete${NC}"
echo ""

# Build images
echo "Building Docker images..."
echo "This may take a few minutes on first run..."
docker-compose build --parallel
echo -e "${GREEN}✅ Images built${NC}"
echo ""

# Start services in order
echo "Starting services..."
echo ""

# 1. Start Redis first
echo -e "${BLUE}Starting Redis...${NC}"
docker-compose up -d redis
wait_for_service "redis"

# 2. Start MCP Memory (depends on Redis)
echo -e "${BLUE}Starting MCP Memory...${NC}"
docker-compose up -d mcp-memory
wait_for_service "mcp-memory"

# 3. Start Huata (depends on Redis)
echo -e "${BLUE}Starting Huata Calendar...${NC}"
docker-compose up -d huata
wait_for_service "huata"

# 4. Start Lyco v2 (depends on Redis)
echo -e "${BLUE}Starting Lyco v2...${NC}"
docker-compose up -d lyco-v2
wait_for_service "lyco-v2"

# 5. Start EA-AI Bridge (depends on all services)
echo -e "${BLUE}Starting EA-AI Bridge...${NC}"
docker-compose up -d ea-ai-bridge
wait_for_service "ea-ai-bridge"

# 6. Start Status Dashboard (monitoring service)
echo -e "${BLUE}Starting Status Dashboard...${NC}"
docker-compose up -d status-dashboard
wait_for_service "status-dashboard"

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}    All services started successfully!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""

# Show service status
echo "Service Status:"
docker-compose ps
echo ""

# Run health check
echo "Running health checks..."
sleep 5
bash test-all-services.sh

echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}    System Ready${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo "📊 Status Dashboard: http://localhost:9999"
echo "🤖 Lyco v2: http://localhost:8000"
echo "📅 Huata Calendar: http://localhost:8003"
echo "🧠 MCP Memory: http://localhost:7777"
echo "🌉 EA-AI Bridge: http://localhost:8080"
echo "💾 Redis: localhost:6379"
echo ""
echo "To view logs: docker-compose logs -f [service-name]"
echo "To stop all: docker-compose down"
echo "To restart: docker-compose restart [service-name]"
