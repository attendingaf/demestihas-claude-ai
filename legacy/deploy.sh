#!/bin/bash

# Commercial Parity Deployment Script
# Deploys the refactored Demestihas-AI agent to VPS

set -e  # Exit on error

VPS_HOST="178.156.170.161"
VPS_USER="root"
VPS_PATH="/root/demestihas-ai"
LOCAL_PATH="."

# Parse arguments
PURGE=false
if [[ "$1" == "--purge" ]]; then
    PURGE=true
    echo "⚠️  PURGE MODE ACTIVATED: This will delete all data on the VPS!"
fi

echo "🚀 Deploying Demestihas-AI to VPS..."
echo ""

# Step 1: Sync code
echo "📦 Step 1/4: Syncing code to VPS..."
# We sync the entire project root to ensure frontend, agent, and support files are there
rsync -avz --progress \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.DS_Store' \
    --exclude '*.log' \
    --exclude '.git' \
    --exclude 'node_modules' \
    --exclude '.next' \
    --exclude '.venv' \
    ${LOCAL_PATH}/ ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/

echo "✅ Code synced successfully"
echo ""

# Step 2: Rebuild and Restart
echo "🔨 Step 2/4: Rebuilding and Restarting..."
ssh ${VPS_USER}@${VPS_HOST} << EOF
    cd ${VPS_PATH}
    
    # If purge is requested, take everything down and remove volumes
    if [ "$PURGE" = true ]; then
        echo "🧹 Purging existing containers and volumes..."
        docker-compose down -v || true
        # Also remove any orphaned images to be clean
        docker system prune -f
    else
        echo "⬇️ Stopping containers..."
        docker-compose down
    fi

    echo "🏗️ Building services (this may take a while)..."
    # Build everything to ensure changes are picked up
    docker-compose build

    echo "🚀 Starting services..."
    docker-compose up -d

    # Update and restart FalkorDB MCP Server (PM2)
    echo "🔄 Updating FalkorDB MCP Server..."
    if [ -d "${VPS_PATH}/falkordb-mcp-server" ]; then
        cd ${VPS_PATH}/falkordb-mcp-server
        echo "   Installing dependencies..."
        npm install --production=false
        echo "   Compiling TypeScript..."
        npm run build
        echo "   Restarting PM2 service..."
        pm2 delete falkordb-api || true
        pm2 start dist/index-sse.js --name falkordb-api
    fi
EOF

echo "✅ Services restarted"
echo ""

# Step 4: Verify deployment
echo "🔍 Step 4/4: Verifying deployment..."
ssh ${VPS_USER}@${VPS_HOST} << 'EOF'
    cd /root/demestihas-ai
    echo "Waiting for health checks (10s)..."
    sleep 10
    echo "Container status:"
    docker-compose ps
    echo ""
    echo "Frontend Logs (last 20 lines):"
    docker-compose logs --tail=20 frontend
EOF

echo ""
echo "✅ Deployment complete!"
echo ""
