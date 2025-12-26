#!/bin/bash
# deploy_mimerc_to_vps.sh - Complete MiMerc migration to VPS
# Generated: September 28, 2025

set -e  # Exit on error

# ========================================
# CONFIGURATION - UPDATE THESE VALUES
# ========================================
VPS_HOST="${VPS_HOST:-your-vps-ip}"  # Replace with your VPS IP
VPS_USER="${VPS_USER:-root}"         # Replace with your VPS username
VPS_PORT="${VPS_PORT:-22}"           # SSH port (default 22)
VPS_DIR="/home/$VPS_USER/mimerc-bot"

# Local paths
LOCAL_DIR="/Users/menedemestihas/Projects/demestihas-ai"
DEPLOYMENT_DIR="$LOCAL_DIR/mimerc-deployment"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ========================================
# HELPER FUNCTIONS
# ========================================
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    log_info "Checking requirements..."
    
    # Check if Docker is running locally
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker is not running locally"
        exit 1
    fi
    
    # Check if containers exist
    if ! docker ps -a | grep -q mimerc; then
        log_warn "No MiMerc containers found locally"
    fi
    
    # Check SSH connection
    if ! ssh -p $VPS_PORT -o ConnectTimeout=5 $VPS_USER@$VPS_HOST "echo 'SSH OK'" > /dev/null 2>&1; then
        log_error "Cannot connect to VPS via SSH. Please check:"
        echo "  - VPS_HOST=$VPS_HOST"
        echo "  - VPS_USER=$VPS_USER"
        echo "  - VPS_PORT=$VPS_PORT"
        exit 1
    fi
    
    log_info "All requirements met ✓"
}

# ========================================
# MAIN DEPLOYMENT
# ========================================

echo "🚀 MiMerc VPS Deployment Tool"
echo "================================"
echo ""

# Check if VPS details are configured
if [ "$VPS_HOST" = "your-vps-ip" ]; then
    log_error "Please configure VPS details first!"
    echo ""
    echo "Edit this script and set:"
    echo "  VPS_HOST=your-actual-vps-ip"
    echo "  VPS_USER=your-username"
    echo ""
    echo "Or run with environment variables:"
    echo "  VPS_HOST=1.2.3.4 VPS_USER=root ./deploy_mimerc_to_vps.sh"
    exit 1
fi

check_requirements

# Step 1: Prepare deployment package
log_info "Preparing deployment package..."
cd $LOCAL_DIR

# Clean up any previous deployment
rm -rf $DEPLOYMENT_DIR mimerc-deployment.tar.gz

# Create deployment directory structure
mkdir -p $DEPLOYMENT_DIR/agents

# Copy MiMerc agent files
if [ -d "agents/mimerc" ]; then
    cp -r agents/mimerc $DEPLOYMENT_DIR/agents/
    log_info "Copied MiMerc agent files"
else
    log_error "MiMerc agent directory not found at agents/mimerc"
    exit 1
fi

# Extract current environment variables if containers are running
log_info "Extracting configuration from running containers..."
if docker ps | grep -q mimerc-agent; then
    CURRENT_OPENAI_KEY=$(docker exec mimerc-agent printenv OPENAI_API_KEY 2>/dev/null || echo "")
    CURRENT_TELEGRAM_TOKEN=$(docker exec mimerc-telegram printenv TELEGRAM_BOT_TOKEN 2>/dev/null || echo "")
else
    log_warn "Containers not running, will need to set environment variables manually"
    CURRENT_OPENAI_KEY=""
    CURRENT_TELEGRAM_TOKEN=""
fi

# Create VPS-specific docker-compose.yml
log_info "Creating VPS docker-compose configuration..."
cat > $DEPLOYMENT_DIR/docker-compose.yml << 'EOF'
version: '3.8'

services:
  mimerc-postgres:
    image: postgres:16-alpine
    container_name: mimerc-postgres
    environment:
      POSTGRES_USER: mimerc
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-mimerc123}
      POSTGRES_DB: mimerc
    ports:
      - "5433:5432"
    volumes:
      - mimerc_postgres_data:/var/lib/postgresql/data
      - ./agents/mimerc/init-tables.sql:/docker-entrypoint-initdb.d/init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mimerc"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - mimerc-net

  mimerc-agent:
    build: 
      context: ./agents/mimerc
      dockerfile: Dockerfile
    container_name: mimerc-agent
    environment:
      DATABASE_URL: postgresql://mimerc:${POSTGRES_PASSWORD:-mimerc123}@mimerc-postgres:5432/mimerc
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      PYTHONUNBUFFERED: 1
    ports:
      - "8002:8000"
    depends_on:
      mimerc-postgres:
        condition: service_healthy
    restart: unless-stopped
    stop_grace_period: 30s
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - mimerc-net

  mimerc-telegram:
    build:
      context: ./agents/mimerc
      dockerfile: Dockerfile
    container_name: mimerc-telegram
    command: python telegram_bot.py
    environment:
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
      MIMERC_API_URL: http://mimerc-agent:8000
      PYTHONUNBUFFERED: 1
    depends_on:
      mimerc-agent:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - mimerc-net

volumes:
  mimerc_postgres_data:
    driver: local

networks:
  mimerc-net:
    driver: bridge
EOF

# Create environment file
cat > $DEPLOYMENT_DIR/.env << EOF
# MiMerc Environment Variables
POSTGRES_PASSWORD=mimerc123
OPENAI_API_KEY=${CURRENT_OPENAI_KEY:-your-openai-key-here}
TELEGRAM_BOT_TOKEN=${CURRENT_TELEGRAM_TOKEN:-your-telegram-token-here}
EOF

# Create VPS setup script
cat > $DEPLOYMENT_DIR/setup_vps.sh << 'EOF'
#!/bin/bash
# Run this on the VPS after transfer

set -e

echo "🔧 Setting up MiMerc on VPS..."

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker not found. Installing...${NC}"
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

# Check docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "Installing docker-compose..."
    apt-get update && apt-get install -y docker-compose
fi

# Stop existing containers
echo "🛑 Stopping existing containers if any..."
docker-compose down 2>/dev/null || true

# Check environment variables
if grep -q "your-openai-key-here" .env; then
    echo -e "${RED}⚠️  WARNING: Please update .env with your actual API keys${NC}"
    echo "Edit .env and set:"
    echo "  - OPENAI_API_KEY"
    echo "  - TELEGRAM_BOT_TOKEN"
    read -p "Press Enter after updating .env file..." 
fi

# Build images
echo "🏗️ Building Docker images..."
docker-compose build --no-cache

# Start services
echo "🚀 Starting services..."
docker-compose up -d

# Wait for health
echo "⏳ Waiting for services to be healthy (30 seconds)..."
sleep 30

# Check status
echo "📊 Service status:"
docker-compose ps

# Test API
echo "🔍 Testing API endpoint..."
if curl -f -X POST http://localhost:8002/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "show list"}' 2>/dev/null; then
    echo -e "\n${GREEN}✅ API is responding!${NC}"
else
    echo -e "\n${RED}❌ API test failed${NC}"
fi

echo ""
echo "✅ MiMerc deployed successfully!"
echo "📊 Access points:"
echo "  - API: http://$(hostname -I | awk '{print $1}'):8002"
echo "  - Telegram: @MiMercBot"
echo ""
echo "📝 Useful commands:"
echo "  docker-compose logs -f        # View logs"
echo "  docker-compose restart        # Restart services"
echo "  docker-compose down          # Stop services"
EOF

chmod +x $DEPLOYMENT_DIR/setup_vps.sh

# Step 2: Create tarball
log_info "Creating deployment archive..."
cd $LOCAL_DIR
tar czf mimerc-deployment.tar.gz mimerc-deployment/

# Step 3: Backup current database (if running)
if docker ps | grep -q mimerc-postgres; then
    log_info "Backing up PostgreSQL data..."
    docker exec mimerc-postgres pg_dump -U mimerc mimerc > $DEPLOYMENT_DIR/backup.sql 2>/dev/null || log_warn "Could not backup database"
fi

# Step 4: Transfer to VPS
log_info "Transferring files to VPS..."
scp -P $VPS_PORT mimerc-deployment.tar.gz $VPS_USER@$VPS_HOST:~/

# Step 5: Deploy on VPS
log_info "Deploying on VPS..."
ssh -p $VPS_PORT $VPS_USER@$VPS_HOST << 'ENDSSH'
set -e

# Clean up old deployment
rm -rf mimerc-bot mimerc-deployment

# Extract new deployment
tar xzf mimerc-deployment.tar.gz
mv mimerc-deployment mimerc-bot
cd mimerc-bot

# Run setup
bash setup_vps.sh
ENDSSH

# Step 6: Verify deployment
log_info "Verifying deployment..."
if ssh -p $VPS_PORT $VPS_USER@$VPS_HOST "cd mimerc-bot && docker-compose ps | grep -q Up"; then
    log_info "Deployment verified - containers are running! ✓"
else
    log_error "Deployment verification failed"
    exit 1
fi

# Step 7: Test VPS API
log_info "Testing VPS API endpoint..."
if curl -f -X POST http://$VPS_HOST:8002/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "test from deployment script"}' 2>/dev/null; then
    log_info "VPS API is responding! ✓"
else
    log_warn "Could not reach VPS API - may need firewall configuration"
fi

echo ""
echo "================================================"
echo "🎉 VPS DEPLOYMENT SUCCESSFUL!"
echo "================================================"
echo ""

# Step 8: Handle local containers
echo "📦 Local Container Management"
echo "----------------------------"
if docker ps | grep -q mimerc; then
    echo "Current local MiMerc containers:"
    docker ps | grep mimerc | awk '{print "  - "$NF" ("$2")"}'
    echo ""
    
    read -p "Stop local MiMerc containers? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Stopping local containers..."
        docker stop mimerc-agent mimerc-postgres mimerc-telegram 2>/dev/null || true
        echo "✅ Local containers stopped"
        
        read -p "Remove local containers? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker rm mimerc-agent mimerc-postgres mimerc-telegram 2>/dev/null || true
            echo "✅ Local containers removed"
            
            read -p "Remove local volumes? (This will delete local data) (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                docker volume rm demestihas-ai_mimerc_postgres_data 2>/dev/null || true
                echo "✅ Local volumes removed"
            fi
        fi
    fi
else
    log_info "No local MiMerc containers found"
fi

# Cleanup
rm -rf $DEPLOYMENT_DIR mimerc-deployment.tar.gz

echo ""
echo "================================================"
echo "📊 DEPLOYMENT SUMMARY"
echo "================================================"
echo "✅ VPS Deployment:"
echo "   - URL: http://$VPS_HOST:8002"
echo "   - Location: $VPS_USER@$VPS_HOST:~/mimerc-bot"
echo "   - Status: Running"
echo ""
echo "📱 Telegram Bot:"
echo "   - Bot: @MiMercBot"
echo "   - Status: Connected to VPS"
echo ""
echo "🛠️ Management Commands:"
echo "   - Check status:  ssh $VPS_USER@$VPS_HOST 'cd mimerc-bot && docker-compose ps'"
echo "   - View logs:     ssh $VPS_USER@$VPS_HOST 'cd mimerc-bot && docker-compose logs -f'"
echo "   - Restart:       ssh $VPS_USER@$VPS_HOST 'cd mimerc-bot && docker-compose restart'"
echo ""
echo "🔒 Next Steps:"
echo "   1. Configure firewall rules for port 8002"
echo "   2. Set up SSL/reverse proxy (nginx/caddy)"
echo "   3. Configure monitoring/alerts"
echo "   4. Set up automated backups"
echo ""
echo "================================================"
echo "✨ Migration completed successfully!"
echo "================================================"
