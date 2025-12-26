#!/bin/bash

# MiMerc Deployment Orchestration Script
# This script handles the complete deployment from local to VPS

set -e

# Configuration
VPS_HOST="root@178.156.170.161"
VPS_DEPLOYMENT_DIR="/root/mimerc"
LOCAL_DEPLOYMENT_DIR="/Users/menedemestihas/Projects/demestihas-ai/mimerc-deployment"
LOCAL_SOURCE_DIR="/Users/menedemestihas/Projects/demestihas-ai/agents/mimerc"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

echo "========================================="
echo "MiMerc VPS Deployment Tool"
echo "========================================="
echo ""

# Step 1: Check SSH connectivity
log_step "1/8 - Testing SSH connection to VPS..."
if ssh -o ConnectTimeout=5 $VPS_HOST "echo 'SSH connection successful'" > /dev/null 2>&1; then
    log_info "SSH connection established successfully"
else
    log_error "Cannot connect to VPS. Please check your SSH configuration."
    exit 1
fi

# Step 2: Evaluate VPS current state
log_step "2/8 - Evaluating current VPS state..."
log_info "Checking existing Docker containers on VPS..."
ssh $VPS_HOST "docker ps -a 2>/dev/null || echo 'Docker not installed'" || true

echo ""
read -p "The VPS will be cleaned and prepared for MiMerc deployment. Continue? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    log_warning "Deployment cancelled by user"
    exit 0
fi

# Step 3: Create .env file from current environment
log_step "3/8 - Creating production .env file..."
cd $LOCAL_DEPLOYMENT_DIR

if [ -f "$LOCAL_SOURCE_DIR/.env" ]; then
    log_info "Using existing .env file from source directory"
    cp "$LOCAL_SOURCE_DIR/.env" .env
else
    log_warning "No .env file found. Creating from running containers..."
    cat > .env << EOF
# MiMerc Production Environment Variables
# Generated on $(date)

OPENAI_API_KEY=$(docker exec mimerc-agent printenv OPENAI_API_KEY 2>/dev/null || echo "")
TELEGRAM_BOT_TOKEN=$(docker exec mimerc-agent printenv TELEGRAM_BOT_TOKEN 2>/dev/null || echo "")
POSTGRES_USER=$(docker exec mimerc-agent printenv POSTGRES_USER 2>/dev/null || echo "mimerc")
POSTGRES_PASSWORD=$(docker exec mimerc-agent printenv POSTGRES_PASSWORD 2>/dev/null || echo "")
POSTGRES_DB=$(docker exec mimerc-agent printenv POSTGRES_DB 2>/dev/null || echo "mimerc_db")
EOF
fi

# Verify critical environment variables
source .env
if [ -z "$OPENAI_API_KEY" ] || [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$POSTGRES_PASSWORD" ]; then
    log_error "Critical environment variables are missing in .env file"
    log_info "Please edit $LOCAL_DEPLOYMENT_DIR/.env and fill in the required values"
    exit 1
fi

log_info "Environment file created successfully"

# Step 4: Prepare VPS
log_step "4/8 - Preparing VPS environment..."
ssh $VPS_HOST << 'EOF'
# Stop and remove any existing containers
if command -v docker &> /dev/null; then
    echo "Stopping existing Docker containers..."
    docker stop $(docker ps -aq) 2>/dev/null || true
    docker rm $(docker ps -aq) 2>/dev/null || true
    docker system prune -f 2>/dev/null || true
fi

# Create deployment directory
mkdir -p /root/mimerc
cd /root/mimerc

# Clean existing deployment if present
rm -rf /root/mimerc/*
EOF

log_info "VPS prepared successfully"

# Step 5: Transfer deployment package
log_step "5/8 - Transferring deployment package to VPS..."
log_info "Compressing deployment package..."
cd $LOCAL_DEPLOYMENT_DIR
tar czf mimerc-deployment.tar.gz \
    agent.py \
    telegram_bot.py \
    requirements.txt \
    Dockerfile \
    docker-compose.yml \
    init-tables.sql \
    setup_vps.sh \
    .env \
    .env.template

log_info "Uploading to VPS..."
scp mimerc-deployment.tar.gz $VPS_HOST:/root/mimerc/
ssh $VPS_HOST "cd /root/mimerc && tar xzf mimerc-deployment.tar.gz && rm mimerc-deployment.tar.gz"

# Make setup script executable
ssh $VPS_HOST "chmod +x /root/mimerc/setup_vps.sh"

log_info "Deployment package transferred successfully"

# Step 6: Execute deployment on VPS
log_step "6/8 - Executing deployment on VPS..."
echo ""
log_warning "Starting VPS deployment. This may take several minutes..."
echo ""

ssh $VPS_HOST "cd /root/mimerc && ./setup_vps.sh"

# Step 7: Verify deployment
log_step "7/8 - Verifying deployment..."
VPS_IP=$(ssh $VPS_HOST "curl -s ifconfig.me || hostname -I | awk '{print \$1}'")

# Test API endpoint
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://$VPS_IP:8002/health 2>/dev/null || echo "000")

if [ "$API_STATUS" = "200" ]; then
    log_info "API endpoint verified successfully!"
else
    log_warning "API endpoint returned status: $API_STATUS"
fi

# Check Telegram bot
log_info "Checking Telegram bot status..."
ssh $VPS_HOST "docker logs mimerc-telegram --tail=5"

# Step 8: Create local management scripts
log_step "8/8 - Creating local management scripts..."

# Create VPS management script
cat > manage_vps.sh << 'EOF'
#!/bin/bash

VPS_HOST="root@178.156.170.161"
VPS_DIR="/root/mimerc"

case "$1" in
    status)
        echo "Checking VPS services status..."
        ssh $VPS_HOST "cd $VPS_DIR && docker-compose ps"
        ;;
    logs)
        SERVICE=${2:-""}
        if [ -z "$SERVICE" ]; then
            ssh $VPS_HOST "cd $VPS_DIR && docker-compose logs --tail=50"
        else
            ssh $VPS_HOST "cd $VPS_DIR && docker-compose logs --tail=50 $SERVICE"
        fi
        ;;
    restart)
        SERVICE=${2:-""}
        if [ -z "$SERVICE" ]; then
            ssh $VPS_HOST "cd $VPS_DIR && docker-compose restart"
        else
            ssh $VPS_HOST "cd $VPS_DIR && docker-compose restart $SERVICE"
        fi
        ;;
    stop)
        ssh $VPS_HOST "cd $VPS_DIR && docker-compose down"
        ;;
    start)
        ssh $VPS_HOST "cd $VPS_DIR && docker-compose up -d"
        ;;
    update)
        echo "Updating deployment..."
        ./deploy_to_vps.sh
        ;;
    shell)
        SERVICE=${2:-agent}
        ssh $VPS_HOST "docker exec -it mimerc-$SERVICE /bin/sh"
        ;;
    *)
        echo "Usage: $0 {status|logs|restart|stop|start|update|shell} [service]"
        echo ""
        echo "Commands:"
        echo "  status              - Show status of all services"
        echo "  logs [service]      - Show logs (optionally for specific service)"
        echo "  restart [service]   - Restart services"
        echo "  stop                - Stop all services"
        echo "  start               - Start all services"
        echo "  update              - Redeploy from local"
        echo "  shell [service]     - Get shell access to container"
        echo ""
        echo "Services: postgres, agent, telegram"
        exit 1
        ;;
esac
EOF

chmod +x manage_vps.sh

# Create stop local containers script
cat > stop_local.sh << 'EOF'
#!/bin/bash

echo "Stopping local MiMerc containers..."
docker stop mimerc-telegram mimerc-agent mimerc-postgres 2>/dev/null || true
echo "Local containers stopped."
echo ""
echo "To remove them completely, run:"
echo "  docker rm mimerc-telegram mimerc-agent mimerc-postgres"
EOF

chmod +x stop_local.sh

# Clean up temporary files
rm -f mimerc-deployment.tar.gz

# Final summary
echo ""
echo "========================================="
echo -e "${GREEN}DEPLOYMENT COMPLETED SUCCESSFULLY!${NC}"
echo "========================================="
echo ""
echo "VPS ACCESS INFORMATION:"
echo "  API Endpoint: http://$VPS_IP:8002"
echo "  API Health Check: http://$VPS_IP:8002/health"
echo "  Telegram Bot: @MiMercBot"
echo ""
echo "MANAGEMENT COMMANDS:"
echo "  View status:      ./manage_vps.sh status"
echo "  View logs:        ./manage_vps.sh logs [service]"
echo "  Restart service:  ./manage_vps.sh restart [service]"
echo "  Stop services:    ./manage_vps.sh stop"
echo "  Start services:   ./manage_vps.sh start"
echo "  Update deploy:    ./manage_vps.sh update"
echo "  Shell access:     ./manage_vps.sh shell [service]"
echo ""
echo "LOCAL CLEANUP:"
echo "  Stop local containers: ./stop_local.sh"
echo ""
echo "ROLLBACK PROCEDURE:"
echo "  1. SSH to VPS: ssh $VPS_HOST"
echo "  2. cd /root/mimerc"
echo "  3. docker-compose down"
echo "  4. Restore from backup if needed"
echo ""
echo "========================================="

log_info "Deployment package saved in: $LOCAL_DEPLOYMENT_DIR"
log_info "VPS deployment directory: /root/mimerc"
