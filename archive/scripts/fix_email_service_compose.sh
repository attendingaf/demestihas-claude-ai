#!/bin/bash

echo "🔧 Fixing Email Service Docker Compose Configuration"

# Navigate to project directory
cd /root/demestihas-ai

# First, let's remove any malformed email-webhook entry
echo "📝 Cleaning up docker-compose.yml..."

# Create a backup
cp docker-compose.yml docker-compose.yml.backup.email

# Remove any existing email-webhook service (if malformed)
sed -i '/email-webhook:/,/^[[:space:]]*$/d' docker-compose.yml

# Add the email-webhook service with correct syntax
echo "✅ Adding email-webhook service with correct syntax..."

cat >> docker-compose.yml << 'EOF'

  email-webhook:
    build:
      context: .
      dockerfile: Dockerfile.email
    container_name: demestihas-email
    restart: unless-stopped
    ports:
      - "8090:8090"
    environment:
      - SENDGRID_WEBHOOK_KEY=${SENDGRID_WEBHOOK_KEY:-}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - NOTION_TOKEN=${NOTION_TOKEN}
      - NOTION_DATABASE_ID=${NOTION_DATABASE_ID}
      - REDIS_HOST=lyco-redis
      - REDIS_PORT=6379
    volumes:
      - ./logs:/app/logs
    networks:
      - lyco-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8090/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

EOF

echo "📋 Updated docker-compose.yml with email-webhook service"
echo ""
echo "🚀 Now starting the email service..."

# Build and start the service
docker-compose build email-webhook
docker-compose up -d email-webhook

# Wait for service to be healthy
echo "⏳ Waiting for service to be healthy..."
sleep 10

# Check service status
echo "📊 Service status:"
docker-compose ps email-webhook

# Check container logs
echo ""
echo "📝 Recent logs:"
docker logs --tail 20 demestihas-email

# Test health endpoint
echo ""
echo "🔍 Testing health endpoint..."
curl -s http://localhost:8090/health | python -m json.tool

echo ""
echo "✅ Email service configuration fixed!"
echo ""
echo "Next steps:"
echo "1. Verify service is running: docker ps | grep demestihas-email"
echo "2. Monitor logs: docker logs -f demestihas-email"
echo "3. Configure SendGrid webhook to point to: http://178.156.170.161:8090/webhook"
echo ""
echo "If the service isn't running, check:"
echo "- Docker logs: docker logs demestihas-email"
echo "- Dockerfile exists: ls -la Dockerfile.email"
echo "- Python files exist: ls -la email_webhook.py email_parser.py"
