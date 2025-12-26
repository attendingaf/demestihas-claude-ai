# VPS Deployment Instructions

## Quick Deploy to 178.156.170.161

### 1. Transfer Files to VPS

```bash
# From local machine
cd /Users/menedemestihas/Projects/claude-desktop-ea-ai
rsync -avz --exclude=venv --exclude=.git . root@178.156.170.161:/root/demestihas-ai/
```

### 2. SSH to VPS and Configure

```bash
# Connect to VPS
ssh root@178.156.170.161
cd /root/demestihas-ai

# Create .env file with your credentials
cp .env.example .env
nano .env

# Add these values:
TELEGRAM_BOT_TOKEN=your_bot_token
ANTHROPIC_API_KEY=your_anthropic_key
NOTION_API_KEY=your_notion_key  
NOTION_TASKS_DATABASE_ID=your_database_id
```

### 3. Deploy with Docker

```bash
# Stop any existing containers
docker-compose down

# Build and start
docker-compose build
docker-compose up -d

# Check logs
docker-compose logs -f lyco
```

### 4. Test the Bot

1. Open Telegram
2. Search for @LycurgusBot
3. Send "help" or any task

## Common Commands

```bash
# View logs
docker-compose logs -f lyco

# Restart bot
docker-compose restart lyco

# Stop all services
docker-compose down

# Check status
docker-compose ps
```

## Troubleshooting

If bot doesn't respond:
```bash
# Check container status
docker ps

# Check bot logs for errors
docker logs lyco-yanay

# Test Redis connection
docker exec -it lyco-redis redis-cli ping
```

## Cost Monitoring

- Claude Haiku usage: ~$0.25 per 1M input tokens
- Typical usage: 100-200 requests/month = < $5/month
- Monitor at: https://console.anthropic.com