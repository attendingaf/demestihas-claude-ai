#!/bin/bash

echo "🔧 Fixing Email Service Configuration"

# Backup current docker-compose.yml
cp docker-compose.yml docker-compose.yml.backup.$(date +%s)

# Remove malformed email-webhook entry if it exists
sed -i '/email-webhook:/,/^$/d' docker-compose.yml

# Add correct email-webhook service
cat >> docker-compose.yml << 'COMPOSE'

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
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8090/health"]
      interval: 30s
      timeout: 10s
      retries: 3

COMPOSE

echo "✅ Docker compose fixed"
