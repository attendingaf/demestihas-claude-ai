# Handoff 001: Yanay/Lyco Split Implementation

## EXECUTION: Claude Code (Direct Implementation)
**ATOMIC SCOPE:** Split monolithic bot.py into Yanay orchestrator and Lyco API
**TIME ESTIMATE:** 2 hours
**PRIORITY:** Critical - Foundation for all multi-agent work

## Context & Current State

**VPS Infrastructure:**
- Server: 178.156.170.161 (SSH as root)
- Current bot: `/root/lyco-ai/bot.py` (monolithic, 19KB)
- Running container: ID 544c72011b31 (keep as backup during transition)
- Redis: Already running on port 6379

**Problems to Solve:**
- No conversation memory (can't handle "that" or "it" references)
- Task extraction at ~60% accuracy (no context awareness)
- All logic mixed in single file (hard to test/scale)

## Implementation Plan

### Phase 1: Directory Rename (5 minutes)
```bash
# SSH to VPS
ssh root@178.156.170.161

# Rename directory to match local project name
cd /root
mv lyco-ai demestihas-ai
cd demestihas-ai

# Update any hardcoded paths in docker-compose.yml
# Update systemd services if any exist
```

### Phase 2: Create Yanay Orchestrator (45 minutes)

Create `/root/demestihas-ai/yanay.py`:

**Key Components:**
1. **Conversation Memory Manager**
   - Redis-backed 20-message history per user
   - TTL: 24 hours for privacy
   - Stores: role, content, timestamp

2. **Intent Classifier**
   - Uses Claude Haiku for speed ($0.25/M tokens)
   - Classifies: create_task, update_task, query_tasks, general_chat
   - Identifies references: "that", "it", "the last one"

3. **Reference Resolver**
   - Scans conversation history for entities
   - Maps pronouns to previous tasks/topics
   - Returns task_id or entity for operations

4. **Agent Router**
   - Phase 1: Direct Python imports (lyco_api)
   - Phase 2: HTTP calls to localhost:8001
   - Phase 3: Event-driven via Redis pub/sub

5. **Telegram Interface**
   - Maintains existing bot interface
   - Adds typing indicators for better UX
   - Preserves all current commands

**Code Structure:**
```python
class YanayOrchestrator:
    def __init__(self):
        self.anthropic = AsyncAnthropic()
        self.redis_client = None
        self.conversation_ttl = 86400
    
    async def initialize(self):
        # Connect to Redis
        
    async def get_conversation_context(self, user_id: str) -> List[Dict]:
        # Retrieve last 20 messages
        
    async def save_message(self, user_id: str, role: str, content: str):
        # Store in Redis with TTL
        
    async def classify_intent(self, message: str, context: List[Dict]) -> Dict:
        # Claude Haiku classification
        
    async def resolve_reference(self, intent: Dict, context: List[Dict]) -> str:
        # Find what "that" refers to
        
    async def route_to_lyco(self, operation: str, data: Dict) -> Dict:
        # Call Lyco API
        
    async def process_message(self, user_message: str, user_id: str) -> str:
        # Main orchestration logic
```

### Phase 3: Extract Lyco API (45 minutes)

Create `/root/demestihas-ai/lyco_api.py`:

**Extract from bot.py:**
1. Task extraction logic (Claude prompts)
2. Notion API interactions
3. Eisenhower matrix categorization
4. Energy level assessment
5. Time estimation logic

**Clean API Interface:**
```python
class LycoTaskAPI:
    async def extract_task_from_text(self, text: str) -> Dict:
        # Pure task extraction, no conversation logic
        
    async def create_task(self, task_data: Dict) -> Dict:
        # Create in Notion, return task_id
        
    async def update_task(self, task_id: str, updates: Dict) -> Dict:
        # Update existing task
        
    async def query_tasks(self, filters: Dict) -> List[Dict]:
        # Search tasks with filters
        
    async def get_task_by_id(self, task_id: str) -> Dict:
        # Retrieve specific task

# Export simple functions for Phase 1 imports
async def create_task(data: Dict) -> Dict:
    return await lyco_api.create_task(data)
```

### Phase 4: Docker Configuration (15 minutes)

Update `/root/demestihas-ai/docker-compose.yml`:

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: demestihas-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    networks:
      - demestihas-network
  
  yanay:
    build: 
      context: .
      dockerfile: Dockerfile.yanay
    container_name: demestihas-yanay
    ports:
      - "8000:8000"
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - NOTION_TOKEN=${NOTION_TOKEN}
      - NOTION_DATABASE_ID=${NOTION_DATABASE_ID}
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    volumes:
      - ./logs:/app/logs
      - ./.env:/app/.env
    restart: unless-stopped
    command: python yanay.py
    networks:
      - demestihas-network
  
  # Keep old bot running during transition
  legacy-bot:
    build: .
    container_name: demestihas-legacy
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN_OLD}
    volumes:
      - ./bot.py:/app/bot.py
    restart: unless-stopped
    command: python bot.py
    networks:
      - demestihas-network

networks:
  demestihas-network:
    driver: bridge

volumes:
  redis_data:
```

Create `/root/demestihas-ai/Dockerfile.yanay`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY yanay.py .
COPY lyco_api.py .

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

CMD ["python", "yanay.py"]
```

### Phase 5: Testing & Validation (15 minutes)

**Test Sequence:**

1. **Unit Tests (Local)**
```python
# test_yanay.py
import asyncio
import pytest
from yanay import YanayOrchestrator

async def test_intent_classification():
    yanay = YanayOrchestrator()
    intent = await yanay.classify_intent("Buy milk tomorrow", [])
    assert intent["intent"] == "create_task"
    assert intent["confidence"] > 0.7

async def test_reference_resolution():
    yanay = YanayOrchestrator()
    context = [
        {"role": "user", "content": "Review Consilium application"},
        {"role": "assistant", "content": "Task created: Review Consilium application"}
    ]
    intent = {"has_reference": True, "referenced_entity": "that"}
    ref = await yanay.resolve_reference(intent, context)
    assert "Consilium" in ref
```

2. **Integration Test (VPS)**
```bash
# Start new services alongside old bot
docker-compose up -d yanay redis

# Test conversation memory
curl -X POST http://localhost:8000/test \
  -H "Content-Type: application/json" \
  -d '{"message": "Review Consilium application", "user_id": "test123"}'

curl -X POST http://localhost:8000/test \
  -H "Content-Type: application/json" \
  -d '{"message": "Make that urgent", "user_id": "test123"}'

# Check Redis
docker exec demestihas-redis redis-cli
> KEYS conv:*
> LRANGE conv:test123 0 -1
```

3. **End-to-End Test**
- Send to new bot: "Buy milk tomorrow"
- Verify task appears in Notion
- Send: "Actually make that urgent"
- Verify task updated to 🔥 Do Now

### Phase 6: Deployment & Cutover (10 minutes)

```bash
# Build and deploy
cd /root/demestihas-ai
docker-compose build yanay
docker-compose up -d yanay

# Monitor logs
docker logs -f demestihas-yanay

# Once verified working:
# 1. Update Telegram webhook to point to Yanay
# 2. Stop legacy bot
docker stop demestihas-legacy

# If issues, immediate rollback:
docker stop demestihas-yanay
docker start demestihas-legacy
```

## Success Criteria

- [ ] Yanay container running without errors
- [ ] Redis storing conversation history
- [ ] "That/it" references correctly resolved
- [ ] Tasks created in Notion with proper categorization
- [ ] Response time <3 seconds
- [ ] No regression in basic functionality

## Known Challenges & Solutions

1. **Redis Connection Issues**
   - Ensure Redis is on same Docker network
   - Use container name not localhost

2. **Import Errors**
   - Ensure lyco_api.py is in same directory
   - Add `/app` to PYTHONPATH if needed

3. **Telegram Polling Conflicts**
   - Use different bot token for testing
   - Or stop old bot before starting new

## Post-Implementation

1. **Update Documentation:**
   - current_state.md → v7.0 (Yanay deployed)
   - architecture.md → Mark Yanay as "Implemented"
   - thread_log.md → Add implementation outcome

2. **Monitor for 24 Hours:**
   - Check Redis memory usage
   - Monitor API costs (Haiku usage)
   - Track task creation accuracy

3. **Next Handoff:**
   - 002_conversation_memory_enhancement.md
   - Add semantic similarity for better reference resolution
   - Implement multi-turn task refinement

## Emergency Contacts

If critical issues during implementation:
- Rollback immediately (commands provided above)
- Document issue in thread_log.md
- Create diagnostic handoff for PM review

---

**FOR CLAUDE CODE:**
This implementation requires direct filesystem access and coordinated changes across multiple files. Please:
1. Start with directory rename
2. Implement incrementally with testing between phases
3. Keep legacy bot running until new system verified
4. Focus on conversation memory as the key differentiator