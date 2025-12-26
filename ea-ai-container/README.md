# EA-AI Containerized Subagent

A containerized implementation of the EA-AI toolset for the Demestihas Family AI Assistant.

## Overview

This container provides the EA-AI toolset as a microservice with an HTTP API, enabling:
- Memory management with persistence
- Intelligent agent routing (Pluma, Huata, Lyco, Kairos)
- Family context management
- Calendar integration
- ADHD-optimized task management

## Architecture

```
Claude Desktop
     ↓
MCP Tools (via claude-integration.js)
     ↓
EA-AI Container (Port 8080)
     ↓
├── Memory System (Redis-backed)
├── Agent Router
├── Family Context
├── Calendar Proxy → Huata Container
└── ADHD Task Manager
```

## Quick Start

### 1. Deploy the Container

```bash
chmod +x deploy.sh
./deploy.sh
```

### 2. Verify Health

```bash
curl http://localhost:8080/health
```

### 3. Test Integration

```bash
node test-integration.js
```

## API Endpoints

### Health Check
```bash
GET /health
```

### Memory Operations
```bash
POST /memory
{
  "operation": "set|get|search|persist",
  "key": "string",
  "value": "any",
  "metadata": "object"
}
```

### Agent Routing
```bash
POST /route
{
  "agent": "auto|pluma|huata|lyco|kairos",
  "query": "string"
}
```

### Family Context
```bash
GET /family/:member
# :member = auto|mene|cindy
```

### Calendar Operations
```bash
POST /calendar/check
{
  "operation": "check_conflicts|find_free_time|next_event",
  "params": "object"
}
```

### ADHD Task Management
```bash
POST /task/adhd
{
  "operation": "break_down|prioritize|energy_match",
  "task": "string"
}
```

## Claude Desktop Integration

Use the provided `claude-integration.js` module in your MCP tools:

```javascript
const EAAIBridge = require('./ea-ai-container/claude-integration');

const bridge = new EAAIBridge();

// Memory operations
await bridge.memory('set', 'key', 'value');
const value = await bridge.memory('get', 'key');

// Route to agents
const agent = await bridge.route('auto', 'schedule a meeting');

// Get family context
const context = await bridge.family('mene');

// ADHD task management
const chunks = await bridge.taskADHD('break_down', 'complex task');
```

## Docker Commands

### View logs
```bash
docker logs ea-ai-agent
```

### Stop services
```bash
docker-compose down
```

### Restart services
```bash
docker-compose restart
```

### Clear state
```bash
rm -rf state/* logs/* cache/*
docker-compose down -v
docker-compose up -d
```

## Environment Variables

- `PORT`: HTTP server port (default: 8080)
- `HUATA_URL`: Huata calendar agent URL
- `LYCO_URL`: Lyco task manager URL
- `REDIS_URL`: Redis connection URL

## File Structure

```
ea-ai-container/
├── Dockerfile           # Container definition
├── docker-compose.yml   # Service orchestration
├── server.js           # Main server application
├── claude-integration.js # Claude Desktop bridge
├── healthcheck.js      # Health check script
├── test-integration.js # Integration tests
├── package.json        # Dependencies
├── deploy.sh          # Deployment script
├── state/             # Persistent state
├── logs/              # Application logs
└── cache/             # Cache directory
```

## Features

### Memory System
- Persistent storage with Redis backing
- Search capabilities
- Automatic synchronization
- Session state management

### Agent Routing
- **Pluma**: Email operations
- **Huata**: Calendar management
- **Lyco**: Task and time management
- **Kairos**: Networking and professional development
- **Auto**: Intelligent routing based on query analysis

### ADHD Optimizations
- Break tasks into 15-minute chunks
- Energy-based task matching
- Priority assessment
- Time-boxed execution

### Family Context
- Personal preferences
- Schedule awareness
- Context-aware responses

## Troubleshooting

### Container won't start
```bash
# Check Docker status
docker info

# View detailed logs
docker-compose logs -f
```

### Connection refused
```bash
# Verify container is running
docker ps

# Check port binding
netstat -an | grep 8080
```

### Memory not persisting
```bash
# Check state directory permissions
ls -la state/

# Verify Redis connection
docker exec ea-ai-agent redis-cli ping
```

## Performance Targets

- Bootstrap: <300ms
- Memory operations: <50ms
- Agent routing: <100ms
- HTTP response: <200ms
- Cache hit rate: >80%

## Integration with Other Services

The EA-AI container integrates with:
- **Huata Calendar Agent** (port 8003)
- **Lyco Task Manager** (port 8000)
- **Redis Cache** (port 6379)
- **Smart Memory System** (port 7777)

## Support

For issues or questions:
1. Check logs: `docker logs ea-ai-agent`
2. Run tests: `node test-integration.js`
3. Review health: `curl http://localhost:8080/health`