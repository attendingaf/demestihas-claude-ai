# MiMerc VPS Management Guide

## Deployment Information

- **VPS IP**: 178.156.170.161
- **Deployment Directory**: `/root/mimerc`
- **Services**: PostgreSQL, MiMerc API, Telegram Bot

## Service URLs

- **API Endpoint**: http://178.156.170.161:8002
- **API Health Check**: http://178.156.170.161:8002/health
- **API Docs**: http://178.156.170.161:8002/docs
- **Telegram Bot**: @mimercado_bot

## Service Management Commands

### Check Service Status
```bash
# From your local machine
./manage_vps.sh status

# Or directly via SSH
ssh root@178.156.170.161 "cd /root/mimerc && docker-compose ps"
```

### View Logs
```bash
# All services
./manage_vps.sh logs

# Specific service
./manage_vps.sh logs agent
./manage_vps.sh logs telegram
./manage_vps.sh logs postgres

# Or directly via SSH
ssh root@178.156.170.161 "docker logs mimerc-agent --tail=50"
ssh root@178.156.170.161 "docker logs mimerc-telegram --tail=50"
ssh root@178.156.170.161 "docker logs mimerc-postgres --tail=50"
```

### Restart Services
```bash
# All services
./manage_vps.sh restart

# Specific service
./manage_vps.sh restart agent

# Or directly via SSH
ssh root@178.156.170.161 "cd /root/mimerc && docker-compose restart"
```

### Stop Services
```bash
./manage_vps.sh stop

# Or directly via SSH
ssh root@178.156.170.161 "cd /root/mimerc && docker-compose down"
```

### Start Services
```bash
./manage_vps.sh start

# Or directly via SSH
ssh root@178.156.170.161 "cd /root/mimerc && docker-compose up -d"
```

## Update Deployment

### Quick Update (Code Only)
```bash
# 1. Edit files locally in /Users/menedemestihas/Projects/demestihas-ai/mimerc-deployment

# 2. Copy updated files to VPS
scp agent.py root@178.156.170.161:/root/mimerc/
scp telegram_bot.py root@178.156.170.161:/root/mimerc/

# 3. Restart services
ssh root@178.156.170.161 "cd /root/mimerc && docker-compose restart"
```

### Full Redeployment
```bash
cd /Users/menedemestihas/Projects/demestihas-ai/mimerc-deployment
./deploy_to_vps.sh
```

## Monitoring

### Check Health Status
```bash
# API health check
curl http://178.156.170.161:8002/health

# Test API endpoint
curl -X POST http://178.156.170.161:8002/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Show my list","thread_id":"test"}'

# Check container health
ssh root@178.156.170.161 "docker ps --format 'table {{.Names}}\t{{.Status}}'"
```

### Monitor Resource Usage
```bash
# Check container resources
ssh root@178.156.170.161 "docker stats --no-stream"

# Check disk usage
ssh root@178.156.170.161 "df -h"

# Check memory usage
ssh root@178.156.170.161 "free -h"
```

## Troubleshooting

### Service Won't Start
```bash
# Check logs for errors
ssh root@178.156.170.161 "docker logs mimerc-agent --tail=100"
ssh root@178.156.170.161 "docker logs mimerc-telegram --tail=100"

# Check if ports are in use
ssh root@178.156.170.161 "netstat -tulpn | grep -E '8002|5432'"

# Rebuild and restart
ssh root@178.156.170.161 "cd /root/mimerc && docker-compose down"
ssh root@178.156.170.161 "cd /root/mimerc && docker-compose build --no-cache"
ssh root@178.156.170.161 "cd /root/mimerc && docker-compose up -d"
```

### Telegram Bot Issues
```bash
# Check bot logs
ssh root@178.156.170.161 "docker logs mimerc-telegram --tail=50 -f"

# Test API connectivity from bot container
ssh root@178.156.170.161 "docker exec mimerc-telegram ping -c 3 agent"

# Restart bot
ssh root@178.156.170.161 "docker restart mimerc-telegram"
```

### Database Issues
```bash
# Connect to PostgreSQL
ssh root@178.156.170.161 "docker exec -it mimerc-postgres psql -U mimerc -d mimerc_db"

# Check database tables
ssh root@178.156.170.161 "docker exec mimerc-postgres psql -U mimerc -d mimerc_db -c '\dt'"

# Reset database (WARNING: Deletes all data)
ssh root@178.156.170.161 "cd /root/mimerc && docker-compose down"
ssh root@178.156.170.161 "docker volume rm mimerc_postgres_data"
ssh root@178.156.170.161 "cd /root/mimerc && docker-compose up -d"
```

## Backup and Recovery

### Backup Database
```bash
# Create backup
ssh root@178.156.170.161 "docker exec mimerc-postgres pg_dump -U mimerc mimerc_db > /root/mimerc_backup_$(date +%Y%m%d).sql"

# Download backup
scp root@178.156.170.161:/root/mimerc_backup_*.sql ./backups/
```

### Restore Database
```bash
# Upload backup
scp backup.sql root@178.156.170.161:/root/

# Restore
ssh root@178.156.170.161 "docker exec -i mimerc-postgres psql -U mimerc mimerc_db < /root/backup.sql"
```

## Security Notes

1. **Environment Variables**: Stored in `/root/mimerc/.env`
   - OPENAI_API_KEY
   - TELEGRAM_BOT_TOKEN
   - POSTGRES_PASSWORD

2. **Exposed Ports**:
   - 8002: MiMerc API (HTTP)
   - 5432: PostgreSQL (should be firewalled in production)

3. **Recommendations**:
   - Add HTTPS with Let's Encrypt
   - Use firewall to restrict PostgreSQL access
   - Set up regular backups
   - Monitor logs for suspicious activity

## Local Cleanup

After confirming VPS deployment is working:

```bash
# Stop local containers
cd /Users/menedemestihas/Projects/demestihas-ai/mimerc-deployment
./stop_local.sh

# Remove local containers (optional)
docker rm mimerc-telegram mimerc-agent mimerc-postgres

# Remove local images (optional)
docker rmi mimerc_agent mimerc_telegram
```

## Quick Reference

- **SSH to VPS**: `ssh root@178.156.170.161`
- **VPS Directory**: `/root/mimerc`
- **Local Directory**: `/Users/menedemestihas/Projects/demestihas-ai/mimerc-deployment`
- **Management Script**: `./manage_vps.sh`
- **Telegram Bot**: @MiMercBot
- **API Test**: `curl http://178.156.170.161:8002/health`