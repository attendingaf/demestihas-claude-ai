# Handoff 001: Yanay Orchestrator Implementation

## THREAD: Developer Thread #1 (Sonnet)
**ATOMIC SCOPE:** Create Yanay orchestrator that routes messages to Lyco task API
**TIME ESTIMATE:** 2 hours
**PRIORITY:** Critical - Blocks all other work

## Context

**Current State:**
- Monolithic bot.py handles everything (19KB file)
- No conversation memory
- Task extraction at ~60% accuracy
- Family frustrated with lack of context

**Target State:**
- Yanay handles conversation and routing
- Lyco becomes pure task API
- 20-message conversation memory
- Natural reference resolution

**Files to Reference:**
- Current bot: `/root/lyco-ai/bot.py`
- Architecture: `~/projects/demestihas-ai/architecture.md`
- Family needs: `~/projects/demestihas-ai/family_context.md`

## Implementation Steps

### Step 1: Create yanay.py (45 minutes)

Create `/root/lyco-ai/yanay.py` with this structure:

```python
import os
import json
import redis.asyncio as redis
from datetime import datetime
from typing import List, Dict, Optional
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

load_dotenv()

class YanayOrchestrator:
    """Conversational orchestrator for the Demestihas family AI system"""
    
    def __init__(self):
        self.anthropic = AsyncAnthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.redis_client = None
        self.conversation_ttl = 86400  # 24 hours
        
    async def initialize(self):
        """Initialize Redis connection"""
        self.redis_client = await redis.from_url(
            "redis://localhost:6379",
            encoding="utf-8",
            decode_responses=True
        )
    
    async def get_conversation_context(self, user_id: str) -> List[Dict]:
        """Retrieve last 20 messages from Redis"""
        key = f"conv:{user_id}"
        messages = await self.redis_client.lrange(key, 0, 19)
        return [json.loads(m) for m in messages] if messages else []
    
    async def save_message(self, user_id: str, role: str, content: str):
        """Save message to conversation history"""
        key = f"conv:{user_id}"
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        await self.redis_client.lpush(key, json.dumps(message))
        await self.redis_client.ltrim(key, 0, 19)  # Keep only 20 messages
        await self.redis_client.expire(key, self.conversation_ttl)
    
    async def classify_intent(self, message: str, context: List[Dict]) -> Dict:
        """Classify user intent using Claude"""
        
        system_prompt = """You are Yanay, the orchestrator for a family task management system.
        Classify the user's intent into one of these categories:
        1. create_task - User wants to add a new task
        2. update_task - User wants to modify an existing task
        3. query_tasks - User asking about existing tasks
        4. general_chat - General conversation
        
        Also identify if the message references something from earlier ("that", "it", etc.)
        
        Respond in JSON format:
        {
            "intent": "create_task|update_task|query_tasks|general_chat",
            "has_reference": true|false,
            "referenced_entity": "what 'that' or 'it' refers to",
            "confidence": 0.0-1.0
        }
        """
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation context
        for msg in context[-5:]:  # Last 5 messages for context
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        messages.append({"role": "user", "content": message})
        
        response = await self.anthropic.messages.create(
            model="claude-3-haiku-20240307",
            messages=messages,
            max_tokens=200
        )
        
        try:
            return json.loads(response.content[0].text)
        except:
            return {
                "intent": "general_chat",
                "has_reference": False,
                "confidence": 0.5
            }
    
    async def route_to_lyco(self, task_data: Dict) -> Dict:
        """Send task to Lyco API"""
        # For Phase 1, import directly
        from lyco_api import create_task, update_task, query_tasks
        
        if task_data["operation"] == "create":
            return await create_task(task_data["data"])
        elif task_data["operation"] == "update":
            return await update_task(task_data["id"], task_data["updates"])
        elif task_data["operation"] == "query":
            return await query_tasks(task_data["query"])
    
    async def process_message(self, user_message: str, user_id: str) -> str:
        """Main orchestration logic"""
        
        # Get conversation context
        context = await self.get_conversation_context(user_id)
        
        # Save user message
        await self.save_message(user_id, "user", user_message)
        
        # Classify intent
        intent = await self.classify_intent(user_message, context)
        
        # Route based on intent
        if intent["intent"] == "create_task":
            # Extract task data
            task_data = await self.extract_task_data(user_message, context)
            
            # Send to Lyco
            result = await self.route_to_lyco({
                "operation": "create",
                "data": task_data
            })
            
            response = f"✅ Task captured: {result.get('task_name', 'New task')}"
            
        elif intent["intent"] == "update_task":
            # Resolve reference
            if intent["has_reference"]:
                task_ref = await self.resolve_reference(intent, context)
                updates = await self.extract_updates(user_message)
                
                result = await self.route_to_lyco({
                    "operation": "update",
                    "id": task_ref,
                    "updates": updates
                })
                
                response = f"✅ Updated task: {updates}"
            else:
                response = "I'm not sure which task you want to update. Can you be more specific?"
        
        elif intent["intent"] == "query_tasks":
            query = await self.extract_query(user_message)
            results = await self.route_to_lyco({
                "operation": "query",
                "query": query
            })
            response = self.format_task_list(results)
        
        else:
            # General conversation
            response = await self.generate_response(user_message, context)
        
        # Save assistant response
        await self.save_message(user_id, "assistant", response)
        
        return response

# Telegram bot handlers
orchestrator = YanayOrchestrator()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text(
        "👋 Hi! I'm Yanay, your family's AI assistant. "
        "I can help you manage tasks, schedule activities, and coordinate with your family. "
        "Just tell me what you need!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all text messages"""
    user_id = str(update.effective_user.id)
    user_message = update.message.text
    
    # Process through orchestrator
    response = await orchestrator.process_message(user_message, user_id)
    
    await update.message.reply_text(response)

async def post_init(application: Application) -> None:
    """Initialize orchestrator after bot starts"""
    await orchestrator.initialize()

def main():
    """Run the bot"""
    application = Application.builder().token(
        os.getenv('TELEGRAM_BOT_TOKEN')
    ).post_init(post_init).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Run
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
```

### Step 2: Create lyco_api.py (45 minutes)

Extract task logic from bot.py into `/root/lyco-ai/lyco_api.py`:

```python
import os
import json
from typing import Dict, List, Optional
from datetime import datetime
from notion_client import AsyncClient
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

load_dotenv()

class LycoTaskAPI:
    """Pure task management API - no conversation logic"""
    
    def __init__(self):
        self.notion = AsyncClient(auth=os.getenv('NOTION_TOKEN'))
        self.anthropic = AsyncAnthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.database_id = os.getenv('NOTION_DATABASE_ID')
    
    async def extract_task_from_text(self, text: str) -> Dict:
        """Extract structured task data from natural language"""
        
        prompt = """Extract task information from this text.
        Return JSON with these fields:
        - task_name: Clear action item
        - eisenhower: "🔥 Do Now" | "📅 Schedule" | "👥 Delegate" | "🗄️ Someday/Maybe" | "🧠 Brain Dump"
        - energy_level: "Low" | "Medium" | "High"
        - time_estimate: "⚡ Quick (<15m)" | "📝 Short (15-30m)" | "🎯 Deep (>30m)" | "📅 Multi-hour"
        - context_tags: Array of relevant tags
        - assigned_to: Family member if mentioned
        - due_date: ISO date if mentioned
        """
        
        response = await self.anthropic.messages.create(
            model="claude-3-haiku-20240307",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text}
            ],
            max_tokens=300
        )
        
        try:
            return json.loads(response.content[0].text)
        except:
            return {
                "task_name": text[:100],
                "eisenhower": "🧠 Brain Dump",
                "energy_level": "Medium",
                "time_estimate": "📝 Short (15-30m)"
            }
    
    async def create_task(self, task_data: Dict) -> Dict:
        """Create task in Notion"""
        
        # Build Notion properties
        properties = {
            "Name": {"title": [{"text": {"content": task_data.get("task_name", "New Task")}}]},
            "Eisenhower": {"select": {"name": task_data.get("eisenhower", "🧠 Brain Dump")}},
            "Energy Level Required": {"select": {"name": task_data.get("energy_level", "Medium")}},
            "Time Estimate": {"select": {"name": task_data.get("time_estimate", "📝 Short (15-30m)")}},
            "Source": {"select": {"name": "Yanay"}},
            "RecordType": {"select": {"name": "Task"}}
        }
        
        # Add optional fields
        if task_data.get("context_tags"):
            properties["Context/Tags"] = {
                "multi_select": [{"name": tag} for tag in task_data["context_tags"]]
            }
        
        if task_data.get("due_date"):
            properties["Due Date"] = {"date": {"start": task_data["due_date"]}}
        
        # Create in Notion
        response = await self.notion.pages.create(
            parent={"database_id": self.database_id},
            properties=properties
        )
        
        return {
            "task_id": response["id"],
            "task_name": task_data.get("task_name"),
            "url": response.get("url"),
            "success": True
        }
    
    async def update_task(self, task_id: str, updates: Dict) -> Dict:
        """Update existing task"""
        
        properties = {}
        
        if "eisenhower" in updates:
            properties["Eisenhower"] = {"select": {"name": updates["eisenhower"]}}
        
        if "complete" in updates:
            properties["Complete"] = {"checkbox": updates["complete"]}
            if updates["complete"]:
                properties["Completed Date"] = {"date": {"start": datetime.now().isoformat()}}
        
        await self.notion.pages.update(
            page_id=task_id,
            properties=properties
        )
        
        return {"success": True, "updates": updates}
    
    async def query_tasks(self, query: Dict) -> List[Dict]:
        """Query tasks from Notion"""
        
        filter_obj = {"and": []}
        
        if query.get("assigned_to"):
            # This would need person ID mapping
            pass
        
        if query.get("complete") is not None:
            filter_obj["and"].append({
                "property": "Complete",
                "checkbox": {"equals": query["complete"]}
            })
        
        response = await self.notion.databases.query(
            database_id=self.database_id,
            filter=filter_obj if filter_obj["and"] else None,
            page_size=10
        )
        
        tasks = []
        for page in response["results"]:
            tasks.append({
                "id": page["id"],
                "name": page["properties"]["Name"]["title"][0]["text"]["content"] if page["properties"]["Name"]["title"] else "",
                "eisenhower": page["properties"].get("Eisenhower", {}).get("select", {}).get("name", ""),
                "complete": page["properties"].get("Complete", {}).get("checkbox", False)
            })
        
        return tasks

# Singleton instance
lyco_api = LycoTaskAPI()

# Export functions for easy import
async def create_task(data: Dict) -> Dict:
    if "text" in data:
        task_data = await lyco_api.extract_task_from_text(data["text"])
        task_data.update(data)  # Override with any explicit data
    else:
        task_data = data
    
    return await lyco_api.create_task(task_data)

async def update_task(task_id: str, updates: Dict) -> Dict:
    return await lyco_api.update_task(task_id, updates)

async def query_tasks(query: Dict) -> List[Dict]:
    return await lyco_api.query_tasks(query)
```

### Step 3: Update Docker Configuration (15 minutes)

Update `/root/lyco-ai/docker-compose.yml`:

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
  
  yanay:
    build: .
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
    restart: unless-stopped
    command: python yanay.py
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  redis_data:
```

### Step 4: Test Implementation (15 minutes)

```bash
# Test locally first
cd /root/lyco-ai

# Test Lyco API
python3 -c "
import asyncio
from lyco_api import create_task

async def test():
    result = await create_task({'text': 'Test task from Lyco API'})
    print(result)

asyncio.run(test())
"

# Test Yanay orchestrator
python3 -c "
import asyncio
from yanay import YanayOrchestrator

async def test():
    y = YanayOrchestrator()
    await y.initialize()
    intent = await y.classify_intent('Buy milk tomorrow', [])
    print(intent)

asyncio.run(test())
"

# If tests pass, deploy
docker-compose up -d --build

# Monitor logs
docker logs -f lyco-ai-yanay-1
```

## Success Test

```bash
# 1. Check services running
docker ps | grep -E "yanay|redis"

# 2. Test conversation memory
# Send to Telegram: "Review Consilium application"
# Then send: "Make that urgent"
# Bot should understand "that" refers to previous task

# 3. Check Redis has conversation
docker exec lyco-ai-redis-1 redis-cli KEYS "conv:*"

# 4. Verify Notion task created
# Check Notion database for new tasks with "Yanay" source
```

## Rollback Plan

If implementation fails:

```bash
# Stop new services
docker-compose stop yanay

# Restart old bot
docker start 544c72011b31

# Revert code changes
cd /root/lyco-ai
git checkout HEAD -- yanay.py lyco_api.py
rm yanay.py lyco_api.py

# Restore original docker-compose
git checkout HEAD -- docker-compose.yml
```

## Reporting

After completion, update:

1. **current_state.md** - Update Architecture Transition Plan section
2. **thread_log.md** - Add Thread #4 entry with outcome
3. Create next handoff: `002_conversation_memory_enhancement.md`

## Next Thread

After Yanay is working:
- Enhance conversation memory with reference resolution
- Add voice message support
- Implement validation layer
- Create family routing rules

---

**Success Criteria:**
- Yanay responds to messages ✓
- Conversation stored in Redis ✓
- "That/it" references work ✓
- Tasks created in Notion ✓
- No regression in basic functionality ✓