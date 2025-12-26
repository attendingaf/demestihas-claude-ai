# REQUIREMENTS.md - Three-Tier Agent Architecture Blueprint
*Generated: September 29, 2025 11:20 PM EDT*  
*Status: READY FOR IMPLEMENTATION*
*Based on: MiMerc VPS Success Pattern*

## 🎯 USER STORY
**As a** developer managing multiple AI agents  
**I want** a standardized three-tier architecture for all agents  
**So that** every agent follows the battle-tested MiMerc pattern

## 📊 PROVEN ARCHITECTURE PATTERN

### Core Success Factors from MiMerc
1. **Service Isolation** — Database, Agent, Frontend as separate containers
2. **Health-First Design** — Every service has health checks  
3. **Dependency Management** — Services start in correct order
4. **State Persistence** — Docker volumes for data survival
5. **Environment Configuration** — All secrets in .env files
6. **Automated Setup** — One-script deployment

## 🏗️ STANDARDIZED THREE-TIER MODEL

### Tier 1: Database Layer
```yaml
service_name-postgres:
  image: postgres:16-alpine  # Or Redis/MongoDB as needed
  environment:
    POSTGRES_USER: ${DB_USER}
    POSTGRES_PASSWORD: ${DB_PASSWORD}
    POSTGRES_DB: ${DB_NAME}
  volumes:
    - service_data:/var/lib/postgresql/data
    - ./init-tables.sql:/docker-entrypoint-initdb.d/init.sql
  healthcheck:
    test: ["CMD", "pg_isready", "-U", "${DB_USER}"]
    interval: 5s
    timeout: 5s
    retries: 5
  networks:
    - agent-network
```

### Tier 2: Agent Logic Layer  
```yaml
service_name-agent:
  build: 
    context: .
    dockerfile: Dockerfile
  ports:
    - "${AGENT_PORT}:8000"
  environment:
    DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@service_name-postgres:5432/${DB_NAME}
    OPENAI_API_KEY: ${OPENAI_API_KEY}
    PYTHONUNBUFFERED: 1
  depends_on:
    service_name-postgres:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 10s
    timeout: 5s
    retries: 3
  networks:
    - agent-network
```

### Tier 3: Interface Layer
```yaml
service_name-interface:  # Telegram bot, Web UI, API gateway
  build:
    context: ./interface
    dockerfile: Dockerfile
  environment:
    AGENT_URL: http://service_name-agent:8000
    TELEGRAM_TOKEN: ${TELEGRAM_TOKEN}  # Or other interface config
  depends_on:
    service_name-agent:
      condition: service_healthy
  restart: unless-stopped
  networks:
    - agent-network
```

## 🚀 IMPLEMENTATION CHECKLIST

### For Each Agent, Create:

#### 1. Project Structure
```
/agents/{agent-name}/
├── docker-compose.yml      # Three services defined
├── .env.template           # All required variables
├── .env                    # Actual secrets (gitignored)
├── Dockerfile              # Agent container definition
├── init-tables.sql         # Database schema
├── requirements.txt        # Python dependencies
├── agent.py                # Core logic (LangGraph)
├── interface/
│   ├── Dockerfile          # Interface container
│   └── bot.py              # Telegram/Web interface
├── deploy.sh               # Idempotent deployment
└── test.sh                 # Health verification
```

#### 2. Dockerfile Template (Alpine-based)
```dockerfile
FROM python:3.11-alpine

# System dependencies (adjust per agent needs)
RUN apk add --no-cache \
    gcc musl-dev postgresql-dev \
    python3-dev libffi-dev

# Non-root user for security
RUN adduser -D -u 1000 agent
WORKDIR /app

# Dependencies first (cache optimization)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY --chown=agent:agent . .
USER agent

# Health endpoint required
EXPOSE 8000
CMD ["python", "agent.py"]
```

#### 3. Deployment Script Template
```bash
#!/bin/bash
set -e

echo "🚀 Deploying ${AGENT_NAME}..."

# Handle any state gracefully
docker-compose down 2>/dev/null || true

# Clean rebuild with logging
docker-compose up --build -d > deploy.log 2>&1

# Wait for health
echo "⏳ Waiting for services..."
sleep 10

# Verify health
if docker-compose ps | grep -q "unhealthy\|Exit"; then
    echo "❌ Deployment failed - check deploy.log"
    docker-compose logs
    exit 1
fi

echo "✅ ${AGENT_NAME} deployed successfully!"
echo "📊 Test with: ./test.sh"
```

#### 4. Health Check Implementation
```python
# In agent.py - Required endpoint
@app.get("/health")
async def health_check():
    try:
        # Check database connection
        await db.execute("SELECT 1")
        # Check external dependencies
        await verify_openai_connection()
        return {"status": "healthy", "timestamp": datetime.now()}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )
```

## 🎯 ACCEPTANCE CRITERIA

### Must Have (Non-negotiable)
- [ ] Three distinct services in docker-compose
- [ ] Health checks on all services
- [ ] Service dependency ordering (depends_on + condition)
- [ ] Persistent volumes for stateful data
- [ ] Environment-based configuration
- [ ] Non-root container execution
- [ ] Graceful shutdown handling
- [ ] Idempotent deployment script

### Should Have
- [ ] Alpine-based images for size
- [ ] Connection retry logic
- [ ] Structured logging
- [ ] Resource limits defined
- [ ] Network isolation
- [ ] Backup/restore scripts

### Nice to Have
- [ ] Multi-stage builds
- [ ] Prometheus metrics endpoint
- [ ] OpenTelemetry tracing
- [ ] Auto-scaling configuration

## 🔄 MIGRATION PLAN FOR EXISTING AGENTS

### Phase 1: Lyco (Task Manager)
```bash
# Current: Single container with Redis
# Target: Three-tier with PostgreSQL

1. Create lyco-postgres service
2. Add lyco-telegram interface  
3. Implement health checks
4. Test full stack locally
5. Deploy to VPS
```

### Phase 2: Huata (Calendar)
```bash
# Current: Standalone container
# Target: Three-tier with persistence

1. Add persistence layer (SQLite/PostgreSQL)
2. Create REST API interface
3. Implement health checks
4. Standardize deployment
```

### Phase 3: New Agents
- Follow blueprint from day one
- Use cookiecutter template
- Automated testing included

## 🧪 VALIDATION TESTS

### Service Health Test
```bash
#!/bin/bash
# test-health.sh

echo "🔍 Testing ${AGENT_NAME} health..."

# Database health
docker exec ${AGENT_NAME}-postgres pg_isready || exit 1

# Agent health  
curl -f http://localhost:${AGENT_PORT}/health || exit 1

# Interface health (if applicable)
docker logs ${AGENT_NAME}-interface 2>&1 | grep -q "Connected" || exit 1

echo "✅ All services healthy!"
```

### Integration Test
```python
# test_integration.py
import requests
import time

def test_full_stack():
    # Test database connectivity
    response = requests.get(f"http://localhost:{AGENT_PORT}/health")
    assert response.status_code == 200
    
    # Test core functionality
    test_payload = {"message": "test", "thread_id": "test-thread"}
    response = requests.post(f"http://localhost:{AGENT_PORT}/chat", json=test_payload)
    assert response.status_code == 200
    
    # Test persistence
    container_restart()
    time.sleep(10)
    
    # Verify state survived restart
    response = requests.post(f"http://localhost:{AGENT_PORT}/chat", json=test_payload)
    assert "test" in response.json()["response"]
```

## 🎬 CLAUDE CODE PROMPT

```
Implement the three-tier architecture pattern for our AI agents based on the successful MiMerc deployment.

Create a cookiecutter template that generates:
1. docker-compose.yml with three services (database, agent, interface)
2. Dockerfiles optimized for Alpine Linux
3. Health check implementations for all services
4. Service dependency management with proper startup order
5. Idempotent deployment script
6. Environment configuration templates
7. Database initialization scripts
8. Integration test suite

Key requirements:
- Services must start in order: database → agent → interface
- All services require health checks
- Use non-root users (UID 1000) for security
- Persistent volumes for stateful data
- Graceful shutdown handling (30s grace period)
- Connection retry logic for database
- PYTHONUNBUFFERED=1 for real-time logs

The template should work for different agent types:
- Task managers (like Lyco) 
- List managers (like MiMerc)
- Calendar agents (like Huata)
- Communication agents (Telegram, Discord, Slack)

Include comprehensive documentation explaining:
- When to use PostgreSQL vs Redis vs MongoDB
- How to add custom health checks
- Debugging failed deployments
- Monitoring and logging best practices
```

## 📊 SUCCESS METRICS

### Deployment Success
- Zero-downtime deployments
- Services healthy within 30 seconds
- Automatic rollback on failure
- Clean logs with no errors

### Operational Excellence
- Response time <300ms (P95)
- 99.9% uptime per agent
- Graceful degradation on dependency failure
- Automatic recovery from crashes

## 🏆 PROVEN PATTERN BENEFITS

### From MiMerc Production Experience
1. **Isolation** — Failed database doesn't crash agent
2. **Scalability** — Each tier scales independently  
3. **Maintainability** — Clear separation of concerns
4. **Debuggability** — Logs isolated per service
5. **Portability** — Runs anywhere Docker runs
6. **Security** — Non-root, network isolation

## 💡 ARCHITECTURAL DECISIONS

### Database Selection Matrix
| Agent Type | Recommended DB | Why |
|------------|---------------|-----|
| Task/Workflow | PostgreSQL | Complex state, transactions |
| Cache/Sessions | Redis | Speed, TTL support |
| Documents | MongoDB | Flexible schema |
| Analytics | ClickHouse | Time-series data |
| Local-only | SQLite | Zero configuration |

### Interface Selection Guide
| Use Case | Interface Type | Implementation |
|----------|---------------|----------------|
| Chat | Telegram/Discord | Bot framework |
| Web | REST API | FastAPI + Swagger |
| Real-time | WebSocket | Socket.IO |
| Mobile | GraphQL | Apollo Server |
| CLI | gRPC | Proto definitions |

## 🎯 IMMEDIATE NEXT STEPS

1. **Create cookiecutter template** (30 min)
2. **Generate Lyco migration** (45 min)  
3. **Test three-tier Lyco** (15 min)
4. **Document patterns** (30 min)
5. **Create CI/CD pipeline** (45 min)

## 🚦 DECISION POINT

**Should we migrate Lyco first or create new agent with pattern?**

Option A: Migrate Lyco (prove pattern works with existing)  
Option B: Build Hermes with pattern (clean slate implementation)

**Recommendation**: Option A - Proves pattern works with real agent

---

**Ready for Implementation**: Three-tier architecture standardization based on MiMerc's production success!