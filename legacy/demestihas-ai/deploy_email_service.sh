#!/bin/bash
echo "📧 Deploying Email-to-Task Integration Service"

# Navigate to project directory
cd /root/demestihas-ai

# Backup current docker-compose
cp docker-compose.yml docker-compose.yml.pre-email-backup

# Add email service configuration to docker-compose.yml
echo "  email-webhook:" >> docker-compose.yml
echo "    build:" >> docker-compose.yml
echo "      context: ." >> docker-compose.yml
echo "      dockerfile: Dockerfile.email" >> docker-compose.yml
echo "    container_name: demestihas-email" >> docker-compose.yml
echo "    restart: unless-stopped" >> docker-compose.yml
echo "    environment:" >> docker-compose.yml
echo "      - ANTHROPIC_API_KEY=\${ANTHROPIC_API_KEY}" >> docker-compose.yml
echo "      - NOTION_TOKEN=\${NOTION_TOKEN}" >> docker-compose.yml
echo "      - NOTION_DATABASE_ID=\${NOTION_DATABASE_ID}" >> docker-compose.yml
echo "      - SENDGRID_WEBHOOK_KEY=\${SENDGRID_WEBHOOK_KEY}" >> docker-compose.yml
echo "      - PYTHONUNBUFFERED=1" >> docker-compose.yml
echo "    depends_on:" >> docker-compose.yml
echo "      - redis" >> docker-compose.yml
echo "    ports:" >> docker-compose.yml
echo "      - \"8090:8090\"" >> docker-compose.yml
echo "    volumes:" >> docker-compose.yml
echo "      - ./logs:/app/logs" >> docker-compose.yml
echo "    healthcheck:" >> docker-compose.yml
echo "      test: [\"CMD\", \"curl\", \"-f\", \"http://localhost:8090/health\"]" >> docker-compose.yml
echo "      interval: 30s" >> docker-compose.yml
echo "      timeout: 10s" >> docker-compose.yml
echo "      retries: 3" >> docker-compose.yml
echo "      start_period: 40s" >> docker-compose.yml
echo "    networks:" >> docker-compose.yml
echo "      - default" >> docker-compose.yml
echo "" >> docker-compose.yml

echo "✅ Email service added to docker-compose.yml"

# Build and start the email service
echo "🔨 Building email webhook service..."
docker-compose build email-webhook

echo "🚀 Starting email webhook service..."
docker-compose up -d email-webhook

# Wait for service to start
echo "⏳ Waiting for service to be healthy..."
sleep 15

# Check service status
echo "📊 Email service status:"
docker-compose ps email-webhook

# Test health endpoint
echo "🔍 Testing health endpoint..."
curl -f http://localhost:8090/health

echo ""
echo "✅ Email-to-task service deployment complete!"
echo ""
echo "Next steps:"
echo "1. Set up SendGrid inbound parse webhook"
echo "2. Point webhook to: http://178.156.170.161:8090/email/webhook"
echo "3. Test by forwarding an email to your task address"
echo ""
echo "Monitor logs with: docker logs -f demestihas-email"
echo "Queue status: curl http://localhost:8090/queue/status"
