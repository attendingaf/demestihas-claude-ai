# Demestihas AI - Unified Docker System

## 🚀 Quick Start

```bash
# Start all services
./start-system.sh

# Test all services
./test-all-services.sh

# View status dashboard
open http://localhost:9999
```

## 📊 Service Architecture

All services run in Docker containers on a shared network (`demestihas-network`) with proper health checks and automatic restarts.

### Services and Ports

| Service | Port | Description | Health Check |
|---------|------|-------------|--------------|
| **Redis** | 6379 | In-memory data store | `/ping` |
| **MCP Memory** | 7777 | Smart memory management | `/health` |
| **Huata Calendar** | 8003 | Calendar orchestration | `/health` |
| **Lyco v2** | 8000 | Task & time management | `/api/health` |
| **EA-AI Bridge** | 8080 | HTTP bridge to EA-AI tools | `/health` |
| **Status Dashboard** | 9999 | Unified monitoring UI | `/health` |

## 🔧 Configuration

### Environment Variables

Copy `.env.shared` to `.env` and configure:

```bash
cp .env.shared .env
# Edit .env with your API keys
```

Required variables:
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `USER_WORK_EMAIL`
- `USER_HOME_EMAIL`

### Directory Structure

```
demestihas-ai/
├── docker-compose.yml          # Unified configuration
├── .env                        # Environment variables
├── .env.shared                 # Template environment
├── dockerfiles/                # Service Dockerfiles
│   ├── mcp-memory.Dockerfile
│   ├── ea-ai-bridge.Dockerfile
│   └── status-dashboard.Dockerfile
├── services/                   # Service code
│   └── status-dashboard/
├── logs/                       # Centralized logging
│   ├── lyco-v2/
│   ├── huata/
│   ├── mcp-memory/
│   ├── ea-ai-bridge/
│   └── status-dashboard/
└── credentials/                # Service credentials
```

## 🎯 Key Features

### Unified Networking
- All services communicate via Docker network
- No more `localhost` confusion
- Service discovery by container name

### Health Monitoring
- Each service has health check endpoint
- Automatic restart on failure
- Status dashboard shows real-time health

### Dependency Management
- Services start in correct order
- Health checks ensure dependencies are ready
- Graceful degradation on service failure

## 📝 Common Commands

### Docker Compose Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f [service-name]

# Restart specific service
docker-compose restart [service-name]

# Rebuild and restart
docker-compose up -d --build [service-name]

# Check status
docker-compose ps

# Execute command in container
docker-compose exec [service-name] [command]
```

### Service-Specific Commands

```bash
# Check Redis
docker-compose exec redis redis-cli ping

# View Lyco logs
docker-compose logs -f lyco-v2

# Restart Huata
docker-compose restart huata

# Check EA-AI Bridge health
curl http://localhost:8080/health | jq

# Monitor all services
watch -n 2 docker-compose ps
```

## 🔍 Troubleshooting

### Service Won't Start

1. Check logs: `docker-compose logs [service-name]`
2. Verify credentials: Ensure `.env` file has all required keys
3. Check port conflicts: `lsof -i :[port-number]`
4. Rebuild image: `docker-compose build --no-cache [service-name]`

### Redis Connection Issues

```bash
# Test Redis connectivity
docker-compose exec redis redis-cli ping

# Check Redis logs
docker-compose logs redis

# Verify network
docker network inspect demestihas-ai_demestihas-network
```

### Health Check Failures

```bash
# Manual health check
curl http://localhost:[port]/health

# Check service logs
docker-compose logs [service-name] | tail -50

# Restart service
docker-compose restart [service-name]
```

## 🌐 Inter-Service Communication

Services communicate using Docker container names:

```python
# Python example (Lyco)
redis_host = os.getenv('REDIS_HOST', 'redis')
redis_url = f"redis://{redis_host}:6379"
```

```javascript
// JavaScript example (EA-AI Bridge)
const LYCO_URL = process.env.LYCO_URL || 'http://lyco-v2:8000';
const HUATA_URL = process.env.HUATA_URL || 'http://huata:8003';
```

## 📊 Status Dashboard

Access at: http://localhost:9999

Features:
- Real-time service health monitoring
- Response time metrics
- Auto-refresh every 10 seconds
- Click service for detailed logs
- Mobile-responsive design

## 🔄 Service Dependencies

```
Redis (no dependencies)
  ├── MCP Memory
  ├── Huata Calendar
  └── Lyco v2
       └── EA-AI Bridge
            └── Status Dashboard
```

## 🚦 Health Check Endpoints

Each service implements a standardized health check:

```json
{
  "service": "service-name",
  "status": "healthy|unhealthy|degraded",
  "uptime": 12345,
  "dependencies": {
    "redis": "connected",
    "database": "connected"
  }
}
```

## 📈 Monitoring & Logs

### Centralized Logging

All logs are stored in `./logs/[service-name]/`

```bash
# Tail all logs
tail -f logs/*/*.log

# Search logs
grep -r "ERROR" logs/

# Archive old logs
tar -czf logs-$(date +%Y%m%d).tar.gz logs/
```

### Performance Monitoring

```bash
# Check resource usage
docker stats

# Monitor specific service
docker stats [container-name]

# Check disk usage
docker system df
```

## 🔐 Security Considerations

1. **Credentials**: Store in `.env` file (never commit to git)
2. **Network**: Internal Docker network isolates services
3. **Volumes**: Mount credentials as read-only where possible
4. **Updates**: Regularly update base images

## 🎯 Next Steps

1. Set up automated backups for Redis data
2. Implement log rotation
3. Add Prometheus/Grafana for metrics
4. Set up alerts for service failures
5. Create CI/CD pipeline for deployments

## 📞 Support

- Check logs first: `docker-compose logs [service-name]`
- Run health check: `./test-all-services.sh`
- View dashboard: http://localhost:9999
- Restart everything: `docker-compose down && ./start-system.sh`