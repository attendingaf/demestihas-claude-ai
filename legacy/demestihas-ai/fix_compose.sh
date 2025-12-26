#!/bin/bash

echo "🔧 Fixing docker-compose for older version compatibility"

# Backup
cp docker-compose.yml docker-compose.yml.bak

# Remove problematic email-webhook service
sed -i '/email-webhook:/,/^$/d' docker-compose.yml

# Add simple version
cat >> docker-compose.yml << 'COMPOSE'

  email-webhook:
    image: python:3.9-slim
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
    working_dir: /app
    volumes:
      - .:/app
    command: sh -c "pip install -q fastapi uvicorn redis anthropic requests && uvicorn email_webhook:app --host 0.0.0.0 --port 8090"

COMPOSE

echo "✅ Fixed!"
