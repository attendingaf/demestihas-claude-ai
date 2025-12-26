#!/bin/bash
# install_vps_monitoring.sh - Complete Docker monitoring setup for VPS
# Provides Docker Desktop-like visibility for remote containers

set -e

# Configuration
VPS_HOST="${VPS_HOST:-your-vps-ip}"
VPS_USER="${VPS_USER:-root}"
VPS_PORT="${VPS_PORT:-22}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "🖥️  Docker VPS Monitoring Setup"
echo "================================"
echo ""

# Check if VPS details are set
if [ "$VPS_HOST" = "your-vps-ip" ]; then
    log_error "Please set VPS details:"
    echo "  VPS_HOST=1.2.3.4 VPS_USER=root ./install_vps_monitoring.sh"
    exit 1
fi

# Menu selection
echo "Choose monitoring solution to install:"
echo ""
echo "1) 🌟 Portainer CE (Recommended - Full Docker Desktop-like UI)"
echo "2) 🔧 Docker Context (Use local Docker CLI with remote)"
echo "3) 📊 Both Portainer + Docker Context"
echo "4) 🚀 Quick Portainer (One-command install)"
echo ""
read -p "Select option (1-4): " choice

case $choice in
    1|3|4)
        log_info "Installing Portainer on VPS..."
        
        if [ "$choice" = "4" ]; then
            # Quick one-liner install
            ssh -p $VPS_PORT $VPS_USER@$VPS_HOST << 'ENDSSH'
docker run -d \
  -p 9000:9000 \
  -p 9443:9443 \
  --name portainer \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce:latest \
  --http-enabled
ENDSSH
        else
            # Full install with checks
            ssh -p $VPS_PORT $VPS_USER@$VPS_HOST << 'ENDSSH'
#!/bin/bash
set -e

echo "🚀 Installing Portainer CE..."

# Check if Portainer already exists
if docker ps -a | grep -q portainer; then
    echo "⚠️  Portainer already exists. Removing old instance..."
    docker stop portainer 2>/dev/null || true
    docker rm portainer 2>/dev/null || true
fi

# Create volume if not exists
docker volume create portainer_data 2>/dev/null || true

# Deploy Portainer
docker run -d \
  -p 9000:9000 \
  -p 9443:9443 \
  --name portainer \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce:latest \
  --http-enabled

# Wait for Portainer to start
echo "⏳ Waiting for Portainer to start..."
sleep 5

# Check if running
if docker ps | grep -q portainer; then
    echo "✅ Portainer installed successfully!"
else
    echo "❌ Portainer installation failed"
    docker logs portainer
    exit 1
fi
ENDSSH
        fi
        
        # Get VPS IP
        VPS_IP=$(ssh -p $VPS_PORT $VPS_USER@$VPS_HOST "hostname -I | awk '{print \$1}'")
        
        echo ""
        echo "✅ Portainer Installed!"
        echo "========================"
        echo "📊 Access URL: http://$VPS_IP:9000"
        echo "🔒 Secure URL: https://$VPS_IP:9443"
        echo ""
        echo "📝 First-time Setup:"
        echo "1. Open http://$VPS_IP:9000 in your browser"
        echo "2. Create an admin username and password"
        echo "3. Choose 'Docker Standalone' environment"
        echo "4. Click 'Connect'"
        echo ""
        echo "You'll then see all your containers just like Docker Desktop!"
        ;;
esac

case $choice in
    2|3)
        log_info "Setting up Docker Context for local CLI access..."
        
        echo ""
        echo "📝 Docker Context Setup"
        echo "======================="
        
        # Check if context already exists
        if docker context ls | grep -q "vps"; then
            log_warn "Docker context 'vps' already exists. Removing..."
            docker context rm vps -f
        fi
        
        # Create new context
        log_info "Creating Docker context 'vps'..."
        docker context create vps \
            --description "VPS Docker at $VPS_HOST" \
            --docker "host=ssh://$VPS_USER@$VPS_HOST:$VPS_PORT"
        
        echo ""
        echo "✅ Docker Context Created!"
        echo "=========================="
        echo ""
        echo "📝 Usage Commands:"
        echo "  docker context use vps     # Switch to VPS"
        echo "  docker ps                  # Shows VPS containers"
        echo "  docker logs container-name # Shows VPS logs"
        echo "  docker context use default # Switch back to local"
        echo ""
        echo "🚀 Quick Test:"
        echo "  docker --context vps ps"
        echo ""
        
        # Test the context
        log_info "Testing VPS context..."
        if docker --context vps ps > /dev/null 2>&1; then
            echo "✅ Context working! Showing VPS containers:"
            echo ""
            docker --context vps ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        else
            log_error "Context test failed. Check SSH access."
        fi
        
        # Add convenient aliases
        read -p "Add convenient aliases to your shell? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            SHELL_RC="$HOME/.zshrc"
            if [ ! -f "$SHELL_RC" ]; then
                SHELL_RC="$HOME/.bashrc"
            fi
            
            # Remove old aliases if they exist
            sed -i.bak '/alias vps-docker=/d' $SHELL_RC
            sed -i.bak '/alias local-docker=/d' $SHELL_RC
            
            # Add new aliases
            echo "" >> $SHELL_RC
            echo "# Docker VPS shortcuts" >> $SHELL_RC
            echo "alias vps-docker='docker --context vps'" >> $SHELL_RC
            echo "alias local-docker='docker --context default'" >> $SHELL_RC
            echo "alias vps-ps='docker --context vps ps --format \"table {{.Names}}\t{{.Status}}\"'" >> $SHELL_RC
            
            echo "✅ Aliases added! Reload your shell or run: source $SHELL_RC"
            echo ""
            echo "New commands available:"
            echo "  vps-docker ps      # Quick VPS container list"
            echo "  vps-ps            # Formatted VPS status"
            echo "  local-docker ps   # Local containers"
        fi
        ;;
esac

# Create monitoring bookmark file
cat > ~/vps-monitoring.md << EOF
# VPS Docker Monitoring

## Portainer
- URL: http://$VPS_IP:9000
- Admin Panel: Full container management
- Features: Logs, Stats, Exec, Restart

## Docker Context Commands
\`\`\`bash
# Switch to VPS
docker context use vps

# List VPS containers
docker ps

# View VPS logs
docker logs container-name

# Switch back to local
docker context use default

# Quick commands
vps-docker ps
vps-ps
\`\`\`

## Quick Health Check
\`\`\`bash
# All containers status
docker --context vps ps -a

# Resource usage
docker --context vps stats --no-stream

# Check specific container
docker --context vps inspect container-name | grep -i health
\`\`\`
EOF

echo ""
echo "================================================"
echo "🎉 VPS MONITORING SETUP COMPLETE!"
echo "================================================"
echo ""
echo "📊 Your Monitoring Options:"

if [ "$choice" = "1" ] || [ "$choice" = "3" ] || [ "$choice" = "4" ]; then
    echo "✅ Portainer: http://$VPS_IP:9000"
fi

if [ "$choice" = "2" ] || [ "$choice" = "3" ]; then
    echo "✅ Docker Context: Use 'docker context use vps'"
fi

echo ""
echo "📝 Reference saved to: ~/vps-monitoring.md"
echo ""
echo "🎯 Next Steps:"
echo "1. Open Portainer in your browser for visual monitoring"
echo "2. Try 'docker --context vps ps' for CLI access"
echo "3. Bookmark the Portainer URL for quick access"
echo ""
echo "================================================"
