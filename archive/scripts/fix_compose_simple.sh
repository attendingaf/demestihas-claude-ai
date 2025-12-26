#!/bin/bash

echo "🔧 Fixing Email Service - Removing Unsupported Options"
echo "====================================================="
echo ""

# Navigate to project directory
cd /root/demestihas-ai

# Backup current docker-compose.yml
echo "📋 Creating backup..."
cp docker-compose.yml docker-compose.yml.backup.$(date +%Y%m%d_%H%M%S)

# Remove the email-webhook service entirely first
echo "🧹 Removing malformed email-webhook service..."
sed -i '/email-webhook:/,/^[[:space:]]*$/d' docker-compose.yml
sed -i '/email-webhook:/,/^$/d' docker-compose.yml

# Clean up any trailing whitespace
sed -i 's/[[:space:]]*$//' docker-compose.yml

# Add simplified email-webhook service without healthcheck
echo "✅ Adding simplified email-webhook service..."

cat >> docker-compose.yml << 'EOF'

  email-webhook:
    build: .
    container_name: demestihas-email
    restart: unless-stopped
    ports:
      - "8090:8090"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - NOTION_TOKEN=${NOTION_TOKEN}
      - NOTION_DATABASE_ID=${NOTION_DATABASE_ID}
      - REDIS_HOST=lyco-redis
      - REDIS_PORT=6379
    volumes:
      - ./logs:/app/logs
    networks:
      - lyco-network

EOF

echo ""
echo "📋 Docker-compose.yml updated successfully!"
echo ""

# Verify the syntax
echo "🔍 Verifying docker-compose syntax..."
docker-compose config > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Docker-compose syntax is valid!"
else
    echo "⚠️  Docker-compose syntax check failed, trying even simpler config..."
    
    # Remove the service again
    sed -i '/email-webhook:/,/^[[:space:]]*$/d' docker-compose.yml
    
    # Try super simple version
    cat >> docker-compose.yml << 'EOF'

  email-webhook:
    image: python:3.9-slim
    container_name: demestihas-email
    ports:
      - "8090:8090"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - NOTION_TOKEN=${NOTION_TOKEN}
      - REDIS_HOST=lyco-redis
    command: sh -c "pip install fastapi uvicorn redis anthropic && python email_webhook.py"
    working_dir: /app
    volumes:
      - .:/app

EOF
fi

echo ""
echo "🚀 Ready to build and start the email service!"
echo ""
echo "Run these commands:"
echo "  docker-compose build email-webhook"
echo "  docker-compose up -d email-webhook"
echo ""
echo "Or use the simple start command:"
echo "  docker run -d --name demestihas-email -p 8090:8090 -v $(pwd):/app -w /app --network lyco-network python:3.9-slim sh -c 'pip install fastapi uvicorn redis anthropic requests && python email_webhook.py'"
