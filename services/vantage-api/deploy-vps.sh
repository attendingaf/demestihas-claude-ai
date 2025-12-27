#!/bin/bash

# Configuration
VPS_USER="root"
VPS_HOST="178.156.170.161"
REMOTE_ROOT="/root/services/vantage"

echo "🦅 Deploying Vantage System (API + UI) to VPS..."

# 1. Build Local (Optional)
# npm run build

# 2. Create Remote Directory Structure
echo "📁 Preparing remote directories..."
ssh $VPS_USER@$VPS_HOST "mkdir -p $REMOTE_ROOT/api $REMOTE_ROOT/ui"

# 3. Upload API Files
echo "📂 Uploading API..."
# Navigate to API dir context
cd "$(dirname "$0")"
scp -r src package.json package-lock.json tsconfig.json Dockerfile $VPS_USER@$VPS_HOST:$REMOTE_ROOT/api/

# 4. Upload UI Files
echo "📂 Uploading UI..."
parent_dir="$(dirname "$(pwd)")"
# Assuming script is in services/vantage-api, ../vantage-ui should be the UI dir
# But verify path:
UI_DIR="../vantage-ui"
if [ -d "$UI_DIR" ]; then
    scp -r $UI_DIR/src $UI_DIR/public $UI_DIR/package.json $UI_DIR/package-lock.json $UI_DIR/tsconfig.json $UI_DIR/tsconfig.app.json $UI_DIR/tsconfig.node.json $UI_DIR/vite.config.ts $UI_DIR/index.html $UI_DIR/Dockerfile $UI_DIR/nginx.conf $VPS_USER@$VPS_HOST:$REMOTE_ROOT/ui/
else
    echo "❌ UI Directory not found at $UI_DIR"
    exit 1
fi

# 5. Upload Compose File
echo "📄 Uploading Orchestration..."
scp docker-compose-prod.yml $VPS_USER@$VPS_HOST:$REMOTE_ROOT/docker-compose.yml

# 6. Deploy on VPS
echo "🚀 Building and Starting Containers..."
ssh $VPS_USER@$VPS_HOST "cd $REMOTE_ROOT && \
    export SUPABASE_URL='${SUPABASE_URL}' && \
    export SUPABASE_KEY='${SUPABASE_KEY}' && \
    export SUPABASE_ANON_KEY='${SUPABASE_ANON_KEY}' && \
    docker-compose down && \
    docker-compose up -d --build"

echo "✅ Deployment Complete!"
echo "   API: http://$VPS_HOST:3005/vantage/dashboard"
echo "   UI:  http://$VPS_HOST:8080"
