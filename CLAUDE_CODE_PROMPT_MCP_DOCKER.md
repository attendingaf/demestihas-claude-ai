# CLAUDE_CODE_PROMPT - Switch MCP Memory to Docker Container

## 🎯 Objective
Switch MCP Memory service from local Node.js process to Docker container while preserving all 66 stored memories and maintaining service availability.

## 📊 Current State
- MCP Memory is running as a **local Node.js process** on port 7777 (PID visible via `lsof -i :7777`)
- Docker container `demestihas-mcp-memory` exists but is stopped (last started 3 days ago)
- Service is healthy with 66 memories stored and 95.5% embedding coverage
- Other services depend on MCP Memory at localhost:7777

## 📋 Requirements
1. Gracefully stop the local Node.js process
2. Ensure memory data is preserved
3. Start the Docker container
4. Verify health and data integrity
5. Ensure all dependent services can still connect

## 🔧 Implementation Steps

### Step 1: Backup Current Data
```bash
# First, check where the local process stores its data
# Look in:
# - ./mcp-smart-memory/data/
# - ./mcp-smart-memory/memories.json
# - Any SQLite or JSON files in the mcp-smart-memory directory

# Create backup
cp -r ./mcp-smart-memory/data ./mcp-smart-memory/data.backup.$(date +%Y%m%d_%H%M%S)
```

### Step 2: Identify and Document Local Process
```bash
# Find the process
lsof -i :7777

# Get process details
ps aux | grep -E "node|npm" | grep -E "mcp|memory|7777"

# Check how it was started (look for start scripts)
ls -la ./mcp-smart-memory/*.sh
cat ./start-memory-server.sh
```

### Step 3: Stop Local Process Gracefully
```bash
# Get PID
PID=$(lsof -ti :7777)

# Send SIGTERM for graceful shutdown (allows saving state)
kill -TERM $PID

# Wait a moment
sleep 3

# Verify it's stopped
lsof -i :7777 || echo "Port 7777 is now free"
```

### Step 4: Ensure Docker Container Has Correct Configuration
Check `docker-compose.yml` for mcp-memory service has:
- Correct volume mounts for data persistence
- Environment variables from .env file
- Health check configured

### Step 5: Start Docker Container
```bash
# Start just the MCP memory container
docker-compose up -d mcp-memory

# Or if using docker directly:
docker start demestihas-mcp-memory

# Wait for it to initialize
sleep 5

# Check logs
docker logs demestihas-mcp-memory --tail 30
```

### Step 6: Verify Health and Data
```bash
# Check health endpoint
curl http://localhost:7777/health

# Should see:
# - "status": "healthy"
# - "totalMemories": 66 (or close to it)
# - "embeddingCoverage": "95.5%" (or similar)

# Test memory retrieval
curl -X POST http://localhost:7777/api/memory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'
```

### Step 7: Test Dependent Services
```bash
# Test EA-AI Bridge can connect
curl -X POST http://localhost:8081/route \
  -H "Content-Type: application/json" \
  -d '{"agent": "memory", "operation": "get", "params": {"query": "system"}}'

# Check container connectivity
docker exec demestihas-ea-ai-bridge curl http://mcp-memory:7777/health
```

### Step 8: Create Auto-Start Script
Create `ensure-mcp-docker.sh`:
```bash
#!/bin/bash
# Ensure MCP Memory runs in Docker, not locally

# Check if local process is running
if lsof -i :7777 > /dev/null 2>&1; then
    echo "Local process detected on port 7777, stopping..."
    kill -TERM $(lsof -ti :7777)
    sleep 3
fi

# Start Docker container
docker-compose up -d mcp-memory

# Verify
sleep 5
curl -s http://localhost:7777/health | jq .
```

## 🧪 Test Commands
```bash
# Full system test
./test-all-services.sh

# Specific MCP Memory test
node test-memory-integration.js

# Check all containers are healthy
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

## ⚠️ Important Considerations
1. **Data Persistence**: The Docker container should mount `./mcp-smart-memory/data` as a volume
2. **Environment Variables**: Ensure all required env vars are in docker-compose.yml or .env
3. **Network**: Container must be on `demestihas-network` for other services to connect
4. **Graceful Shutdown**: Use SIGTERM not SIGKILL to allow the local process to save state

## 🔄 Rollback Plan
If the Docker container doesn't work:
```bash
# Stop the container
docker stop demestihas-mcp-memory

# Restart the local service
cd ./mcp-smart-memory
npm start  # or whatever command was used originally

# Or use the start script if it exists
./start-memory-server.sh
```

## ✅ Success Criteria
- [ ] Local Node.js process stopped cleanly
- [ ] Docker container `demestihas-mcp-memory` running
- [ ] Health endpoint returns 66+ memories
- [ ] EA-AI Bridge can connect to MCP Memory
- [ ] No data loss (same number of memories)
- [ ] Docker Desktop shows green dot for mcp-memory

## 📝 Files to Check/Modify
- `/Users/menedemestihas/Projects/demestihas-ai/docker-compose.yml` (mcp-memory service definition)
- `/Users/menedemestihas/Projects/demestihas-ai/mcp-smart-memory/data/` (data persistence)
- `/Users/menedemestihas/Projects/demestihas-ai/start-memory-server.sh` (local start script)
- `/Users/menedemestihas/Projects/demestihas-ai/.env` (environment variables)

## 🚨 DO NOT
- Kill the process with `kill -9` (causes data loss)
- Delete any data directories
- Change port 7777 (other services depend on it)
- Restart all containers (unnecessary disruption)

---

**Copy this entire prompt to Claude Code to execute the migration from local process to Docker container.**
