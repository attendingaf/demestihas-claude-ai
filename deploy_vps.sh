#!/bin/bash
set -e

VPS_HOST="root@178.156.170.161"
REMOTE_DIR="/root/demestihas-ai"

echo "🚀 Deploying Executive Briefing Service to $VPS_HOST..."

# 1. Create directory structure on VPS
echo "📂 Ensuring directory structure..."
ssh $VPS_HOST "mkdir -p $REMOTE_DIR/services/executive-briefing"

# 2. Upload Docker Compose
echo "📄 Uploading docker-compose.yml..."
scp docker-compose.yml $VPS_HOST:$REMOTE_DIR/

# 3. Sync Service Code
echo "📦 Syncing project directories..."
# Syncing core components needed for docker-compose
for dir in mcp-smart-memory huata agents ea-ai-container services; do
    echo "   Syncing $dir..."
    rsync -avz --exclude 'node_modules' --exclude 'dist' --exclude '__pycache__' --exclude 'venv' --exclude '.venv' ./$dir/ $VPS_HOST:$REMOTE_DIR/$dir/
done

# 4. Update .env content (Appending new keys carefully)
# We won't overwrite the whole .env to avoid breaking other things, but we'll append missing keys
echo "🔑 Updating .env..."
# Read local .env and extract the relevant keys
grep -E "GOOGLE_|TASK_API_KEY|BRIEFING_RECIPIENT|ANTHROPIC_" .env > .env.deploy_temp

# Upload temp env
scp .env.deploy_temp $VPS_HOST:$REMOTE_DIR/.env.deploy_temp

# Merge on VPS
ssh $VPS_HOST "cd $REMOTE_DIR && cat .env.deploy_temp >> .env && rm .env.deploy_temp"
rm .env.deploy_temp

# 5. Remote Build & Restart
echo "🏗️  Rebuilding on VPS..."
ssh $VPS_HOST "cd $REMOTE_DIR && \
    docker-compose build executive-briefing && \
    docker-compose up -d executive-briefing"

echo "✅ Deployment complete!"
echo "⚠️  IMPORTANT: Please update your cron job manually if it pointed to port 8050. It is now 8060."
