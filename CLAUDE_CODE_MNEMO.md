# Claude Code Prompt: Implement Mnemo Memory Orchestration Agent

## Context
I need you to implement Mnemo, an agentic memory orchestration layer that unifies access to multiple memory systems. This agent will provide intelligent routing, auto-classification, and cross-memory correlation.

## Current Infrastructure
- Redis on port 6379 (working memory)
- MCP Smart Memory on port 7777 (pattern storage)
- Multiple SQLite DBs for persistence
- All containers on `demestihas-network`
- Docker compose structure already exists

## Your Task
Create the Mnemo agent with the following structure:

### 1. Directory Structure
Create `/agents/mnemo/` with:
- `src/` - Core implementation files
- `adapters/` - Memory store interfaces
- `data/` - SQLite databases
- `config/` - Configuration files
- `Dockerfile` and `package.json`

### 2. Core Implementation

#### Main Server (src/index.js)
```javascript
import express from 'express';
import cors from 'cors';
import { MemoryClassifier } from './classifier.js';
import { MemoryRouter } from './router.js';
import { MemoryConsolidator } from './consolidator.js';

const app = express();
app.use(cors());
app.use(express.json());

const classifier = new MemoryClassifier();
const router = new MemoryRouter();
const consolidator = new MemoryConsolidator();

// POST /remember - Store memory with auto-classification
app.post('/remember', async (req, res) => {
  const { content, type = 'auto', metadata = {} } = req.body;
  
  const memoryType = type === 'auto' 
    ? await classifier.classify(content, metadata)
    : type;
  
  const result = await router.store(content, memoryType, metadata);
  res.json({ success: true, id: result.id, type: memoryType });
});

// GET /recall - Search across all memory stores
app.get('/recall', async (req, res) => {
  const { query, types = ['all'], limit = 10 } = req.query;
  
  const memories = await router.search(query, types, { limit });
  const correlated = await consolidator.correlate(memories, query);
  
  res.json({ 
    query,
    results: correlated,
    sources: [...new Set(correlated.map(m => m.source))],
    count: correlated.length
  });
});

// GET /health - Health check
app.get('/health', async (req, res) => {
  const stores = await router.checkStores();
  res.json({
    status: 'healthy',
    agent: 'mnemo',
    version: '1.0.0',
    stores,
    timestamp: new Date().toISOString()
  });
});

app.listen(8004, () => {
  console.log('Mnemo agent running on port 8004');
});
```

#### Memory Classifier (src/classifier.js)
Implement pattern-based classification:
- Episodic: Events with timestamps
- Semantic: Solutions and procedures
- Pattern: Recurring behaviors
- Working: Temporary session data

#### Memory Router (src/router.js)
Route to appropriate stores:
- Working → Redis
- Episodic → SQLite (episodic.db)
- Semantic → SQLite (semantic.db)
- Pattern → MCP Memory API

#### Adapters
Create adapters for each store:
- `redis-adapter.js` - Connect to demestihas-redis:6379
- `sqlite-adapter.js` - Handle local SQLite databases
- `mcp-adapter.js` - Interface with http://demestihas-mcp-memory:7777

### 3. Docker Configuration

#### Dockerfile
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 8004
HEALTHCHECK --interval=30s --timeout=3s \
  CMD wget --no-verbose --tries=1 --spider http://localhost:8004/health || exit 1
CMD ["node", "src/index.js"]
```

#### Docker Compose Addition
Add to the existing docker-compose.yml:
```yaml
mnemo:
  container_name: demestihas-mnemo
  build:
    context: ./agents/mnemo
    dockerfile: Dockerfile
  ports:
    - "8004:8004"
  volumes:
    - ./agents/mnemo/data:/data
    - ./agents/mnemo/config:/config
  environment:
    - NODE_ENV=production
    - REDIS_HOST=demestihas-redis
    - MCP_MEMORY_URL=http://demestihas-mcp-memory:7777
  networks:
    - demestihas-network
  restart: unless-stopped
  depends_on:
    - redis
    - mcp-memory
```

### 4. Package.json Dependencies
```json
{
  "name": "mnemo-agent",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "start": "node src/index.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "cors": "^2.8.5",
    "redis": "^4.6.5",
    "sqlite3": "^5.1.6",
    "axios": "^1.4.0"
  }
}
```

## Success Criteria
1. Container runs on port 8004
2. Health endpoint returns all stores connected
3. Can store memories with auto-classification
4. Can search across multiple memory stores
5. Returns results in <200ms

## Test Commands
After implementation:
```bash
# Build and start
docker-compose up -d mnemo

# Check health
curl http://localhost:8004/health

# Store a memory
curl -X POST http://localhost:8004/remember \
  -H "Content-Type: application/json" \
  -d '{"content": "Fixed OAuth redirect URL issue"}'

# Recall memories
curl "http://localhost:8004/recall?query=oauth"
```

## Implementation Order
1. Create directory structure
2. Implement basic Express server with health endpoint
3. Add memory classifier
4. Build store adapters
5. Implement router and consolidator
6. Create Dockerfile
7. Add to docker-compose.yml
8. Test all endpoints

Please implement this step by step, creating all necessary files and ensuring the container runs successfully with all health checks passing.