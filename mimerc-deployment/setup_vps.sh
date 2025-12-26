#!/bin/bash

# MiMerc VPS Deployment Setup Script
# This script sets up the MiMerc bot on a VPS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions for colored output
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_info "Starting MiMerc VPS deployment..."

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root"
   exit 1
fi

# Check Docker installation
log_info "Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    log_warning "Docker not found. Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    log_info "Docker installed successfully"
else
    log_info "Docker is already installed"
    docker --version
fi

# Check Docker Compose installation
log_info "Checking Docker Compose installation..."
if ! command -v docker-compose &> /dev/null; then
    # Check if docker compose (v2) is available
    if ! docker compose version &> /dev/null; then
        log_warning "Docker Compose not found. Installing Docker Compose..."
        DOCKER_COMPOSE_VERSION="2.23.0"
        curl -L "https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        log_info "Docker Compose installed successfully"
    else
        log_info "Docker Compose v2 is available"
    fi
else
    log_info "Docker Compose is already installed"
    docker-compose --version
fi

# Check if .env file exists
if [ ! -f .env ]; then
    log_error ".env file not found!"
    log_info "Please create .env file from .env.template and fill in your credentials"
    exit 1
fi

# Validate required environment variables
log_info "Validating environment variables..."
source .env

if [ -z "$OPENAI_API_KEY" ]; then
    log_error "OPENAI_API_KEY is not set in .env file"
    exit 1
fi

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    log_error "TELEGRAM_BOT_TOKEN is not set in .env file"
    exit 1
fi

if [ -z "$POSTGRES_PASSWORD" ]; then
    log_error "POSTGRES_PASSWORD is not set in .env file"
    exit 1
fi

log_info "Environment variables validated successfully"

# Stop any existing containers
log_info "Stopping any existing MiMerc containers..."
docker-compose down --remove-orphans 2>/dev/null || true

# Clean up old volumes (optional, uncomment if you want to start fresh)
# log_warning "Removing old volumes..."
# docker volume rm mimerc-deployment_postgres_data 2>/dev/null || true

# Build images with no cache
log_info "Building Docker images (this may take a few minutes)..."
docker-compose build --no-cache

# Start services
log_info "Starting MiMerc services..."
docker-compose up -d

# Wait for services to be healthy
log_info "Waiting for services to be healthy..."
MAX_ATTEMPTS=30
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    POSTGRES_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' mimerc-postgres 2>/dev/null || echo "not running")
    AGENT_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' mimerc-agent 2>/dev/null || echo "not running")
    TELEGRAM_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' mimerc-telegram 2>/dev/null || echo "not running")

    if [ "$POSTGRES_HEALTH" = "healthy" ] && [ "$AGENT_HEALTH" = "healthy" ] && [ "$TELEGRAM_HEALTH" = "healthy" ]; then
        log_info "All services are healthy!"
        break
    fi

    ATTEMPT=$((ATTEMPT + 1))
    log_info "Waiting for services... (Attempt $ATTEMPT/$MAX_ATTEMPTS)"
    log_info "  PostgreSQL: $POSTGRES_HEALTH"
    log_info "  Agent: $AGENT_HEALTH"
    log_info "  Telegram: $TELEGRAM_HEALTH"
    sleep 5
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    log_error "Services failed to become healthy within the timeout period"
    log_info "Checking container logs..."
    docker-compose logs --tail=50
    exit 1
fi

# Test API endpoint
log_info "Testing API endpoint..."
API_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8002/health || echo "000")

if [ "$API_RESPONSE" = "200" ]; then
    log_info "API endpoint is responding successfully!"
else
    log_warning "API endpoint returned status code: $API_RESPONSE"
    log_info "Checking agent logs..."
    docker logs mimerc-agent --tail=20
fi

# Display service status
log_info "Service Status:"
docker-compose ps

# Get VPS IP
VPS_IP=$(curl -s ifconfig.me || hostname -I | awk '{print $1}')

# Display access information
echo ""
echo "========================================="
echo -e "${GREEN}MiMerc Deployment Successful!${NC}"
echo "========================================="
echo ""
echo "Access URLs:"
echo "  API Endpoint: http://$VPS_IP:8002"
echo "  Telegram Bot: @MiMercBot"
echo ""
echo "Management Commands:"
echo "  View logs: docker-compose logs -f [service_name]"
echo "  Restart services: docker-compose restart"
echo "  Stop services: docker-compose down"
echo "  View status: docker-compose ps"
echo ""
echo "Service Names:"
echo "  - mimerc-postgres (PostgreSQL database)"
echo "  - mimerc-agent (LangGraph API)"
echo "  - mimerc-telegram (Telegram bot)"
echo ""
echo "========================================="

log_info "Deployment complete!"
