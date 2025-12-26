# DemestiChat Statefulness Roadmap
**Generated:** October 29, 2025  
**Current Score:** 65/100  
**Target Score:** 87/100  
**Timeline:** 6-8 weeks (4 sprints)

---

## Strategic Vision

Transform DemestiChat from a **partial stateful system** (65/100) to a **production-grade stateful AI** (87/100) by:

1. **Eliminating critical bugs** (stub data, unused PostgreSQL)
2. **Implementing temporal reasoning** (date-based queries)
3. **Enabling episodic memory** (conversation history tracking)
4. **Building working memory** (attention and context management)

---

## Sprint 1: Critical Bugs and Foundation (Week 1-2)

**Goal:** Fix production bugs, establish PostgreSQL schema, enable real FalkorDB queries  
**Score Impact:** 65 → 75 (+10 points)

### 1.1 Remove FalkorDB Stub Data ⚠️ CRITICAL

**Problem:** `main.py:901-928` returns hardcoded data instead of real graph queries

**Current Code:**
```python
# TODO: Replace with actual FalkorDB queries
knowledge_graph_evidence = [
    "General agent handles conversational queries",
    "Code agent specializes in programming tasks",
]
```

**Fix:**
```python
async def stub_retrieve_memory(state: AgentState, chat_request: ChatRequest) -> AgentState:
    # ... existing Mem0 code ...
    
    # STEP 2: Query FalkorDB for real user knowledge
    knowledge_graph_evidence = []
    
    try:
        global falkordb_manager
        if not falkordb_manager.is_connected():
            await falkordb_manager.connect()
        
        # Retrieve user's knowledge triples
        triples = await falkordb_manager.get_user_knowledge_triples(
            user_id=chat_request.user_id,
            limit=5
        )
        
        # Format for orchestrator context
        knowledge_graph_evidence = [
            f"{t['subject']} {t['predicate']} {t['object']} (confidence: {t['confidence']:.2f})"
            for t in triples
        ]
        
        logger.info(f"✅ Retrieved {len(triples)} real knowledge triples from FalkorDB")
        
    except Exception as e:
        logger.error(f"FalkorDB query failed: {str(e)}")
        knowledge_graph_evidence = []
    
    state["knowledge_graph_data"] = {
        "triples": knowledge_graph_evidence,
        "source": "FalkorDB (live query)"
    }
    
    return state
```

**Test Command:**
```bash
# Verify fix
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"user_id": "executive_mene", "message": "What do you know about me?"}'

# Expected: Response includes real family members (Mene, Cindy, Persy, etc.)
```

**Acceptance Criteria:**
- [ ] Remove all stub data from `main.py`
- [ ] Orchestrator receives real FalkorDB triples
- [ ] Logs show "Retrieved X real knowledge triples"
- [ ] Test with multiple users, verify user-scoped queries

**Estimated Effort:** 2 hours  
**Priority:** P0 (Critical Bug)

---

### 1.2 Implement PostgreSQL Conversation Storage

**Problem:** PostgreSQL exists but is completely unused (no conversation history)

**Schema Design:**
```sql
-- postgres/init-tables.sql

CREATE TABLE users (
    id VARCHAR(255) PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    last_seen TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE conversation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) REFERENCES users(id),
    session_id VARCHAR(255) UNIQUE NOT NULL,
    started_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP,
    message_count INT DEFAULT 0,
    summary TEXT,
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255) REFERENCES conversation_sessions(session_id),
    user_id VARCHAR(255) REFERENCES users(id),
    role VARCHAR(20) NOT NULL, -- 'user' or 'assistant'
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    routing_agent VARCHAR(50),  -- 'general', 'code', 'research', etc.
    confidence_score FLOAT,
    tool_calls JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_messages_session ON messages(session_id, timestamp);
CREATE INDEX idx_messages_user ON messages(user_id, timestamp DESC);
CREATE INDEX idx_sessions_user ON conversation_sessions(user_id, started_at DESC);
```

**Implementation in `main.py`:**
```python
import psycopg2
from psycopg2.extras import RealDictCursor

# Connection pool (add to startup)
postgres_conn = None

@app.on_event("startup")
async def startup_event():
    global postgres_conn
    postgres_conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        database=os.getenv("POSTGRES_DB", "demestihas"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD")
    )
    logger.info("✅ PostgreSQL connection established")

def store_message_in_postgres(
    user_id: str,
    session_id: str,
    role: str,
    content: str,
    routing_agent: Optional[str] = None,
    confidence_score: Optional[float] = None
):
    """Store a single message in PostgreSQL."""
    try:
        with postgres_conn.cursor() as cursor:
            # Ensure session exists
            cursor.execute("""
                INSERT INTO conversation_sessions (session_id, user_id)
                VALUES (%s, %s)
                ON CONFLICT (session_id) DO UPDATE
                SET message_count = conversation_sessions.message_count + 1,
                    ended_at = NOW()
            """, (session_id, user_id))
            
            # Insert message
            cursor.execute("""
                INSERT INTO messages (session_id, user_id, role, content, routing_agent, confidence_score)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (session_id, user_id, role, content, routing_agent, confidence_score))
            
            postgres_conn.commit()
            logger.debug(f"Stored {role} message in PostgreSQL session {session_id}")
    
    except Exception as e:
        logger.error(f"Failed to store message in PostgreSQL: {str(e)}")
        postgres_conn.rollback()

def get_session_history(
    user_id: str,
    session_id: str,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Retrieve conversation history for a session."""
    try:
        with postgres_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT role, content, timestamp, routing_agent
                FROM messages
                WHERE user_id = %s AND session_id = %s
                ORDER BY timestamp ASC
                LIMIT %s
            """, (user_id, session_id, limit))
            
            return cursor.fetchall()
    
    except Exception as e:
        logger.error(f"Failed to retrieve session history: {str(e)}")
        return []
```

**Integration in Chat Endpoint:**
```python
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    chat_request: ChatRequest,
    user_id: str = Depends(get_current_user_id)
):
    # Generate session_id if not provided
    session_id = chat_request.chat_id or str(uuid.uuid4())
    
    # Store user message
    store_message_in_postgres(
        user_id=user_id,
        session_id=session_id,
        role="user",
        content=chat_request.message
    )
    
    # ... existing agent logic ...
    
    # Store assistant response
    store_message_in_postgres(
        user_id=user_id,
        session_id=session_id,
        role="assistant",
        content=final_response,
        routing_agent=state["routing_decision"].selected_agent,
        confidence_score=state["routing_decision"].confidence_score
    )
    
    return ChatResponse(response=final_response, ...)
```

**Acceptance Criteria:**
- [ ] Schema created in PostgreSQL
- [ ] Every chat message stored with timestamp
- [ ] Session tracking works across requests
- [ ] Can query conversation history by session_id
- [ ] Indexes improve query performance

**Estimated Effort:** 6 hours  
**Priority:** P0 (Critical Infrastructure)

---

### 1.3 Add Session History Retrieval to Memory Context

**Goal:** Include PostgreSQL session history in orchestrator context

**Implementation:**
```python
async def stub_retrieve_memory(state: AgentState, chat_request: ChatRequest) -> AgentState:
    # Existing Mem0 and FalkorDB queries...
    
    # STEP 3: Retrieve session history from PostgreSQL
    session_history = []
    if chat_request.chat_id:
        try:
            messages = get_session_history(
                user_id=chat_request.user_id,
                session_id=chat_request.chat_id,
                limit=10
            )
            
            session_history = [
                f"{msg['role'].capitalize()}: {msg['content'][:100]}..."
                for msg in messages[-10:]  # Last 10 messages
            ]
            
            logger.info(f"Retrieved {len(messages)} messages from PostgreSQL session history")
        
        except Exception as e:
            logger.error(f"Failed to retrieve session history: {str(e)}")
    
    state["memory_context"]["session_history"] = session_history
    return state
```

**Orchestrator Integration:**
```python
# In orchestrator_router(), add to system prompt:
session_context = state["memory_context"].get("session_history", [])
if session_context:
    system_prompt += f"""

## SESSION HISTORY (This Conversation)

{chr(10).join(session_context)}

Use this immediate context to maintain conversation continuity.
"""
```

**Acceptance Criteria:**
- [ ] Orchestrator receives session-specific history
- [ ] Multi-turn conversations maintain context
- [ ] History includes last 10 messages from current session
- [ ] Logs differentiate between Mem0 (cross-session) and PostgreSQL (current session)

**Estimated Effort:** 3 hours  
**Priority:** P1 (High)

---

### 1.4 Sprint 1 Testing and Validation

**Integration Tests:**
```bash
# Test 1: Multi-turn conversation with session continuity
SESSION_ID=$(uuidgen)
curl -X POST http://localhost:8000/chat -d "{\"user_id\": \"test_user\", \"chat_id\": \"$SESSION_ID\", \"message\": \"My favorite color is blue\"}"
curl -X POST http://localhost:8000/chat -d "{\"user_id\": \"test_user\", \"chat_id\": \"$SESSION_ID\", \"message\": \"What's my favorite color?\"}"
# Expected: "Your favorite color is blue"

# Test 2: Cross-session knowledge retrieval
curl -X POST http://localhost:8000/chat -d "{\"user_id\": \"test_user\", \"chat_id\": \"session2\", \"message\": \"What's my favorite color?\"}"
# Expected: Still knows "blue" from previous session

# Test 3: Verify PostgreSQL storage
docker exec demestihas-postgres psql -U postgres -d demestihas -c \
  "SELECT role, content, timestamp FROM messages WHERE user_id='test_user' ORDER BY timestamp DESC LIMIT 5;"
```

**Success Metrics:**
- [ ] All tests pass
- [ ] No stub data in responses
- [ ] PostgreSQL shows all messages
- [ ] FalkorDB queries return real data

---

## Sprint 2: Temporal Reasoning and Document Integration (Week 3-4)

**Goal:** Enable date-based queries, integrate Document RAG into chat flow  
**Score Impact:** 75 → 82 (+7 points)

### 2.1 Implement Temporal Query Support

**Goal:** Allow users to ask "What did we discuss yesterday?"

**PostgreSQL Temporal Queries:**
```python
def get_messages_by_date_range(
    user_id: str,
    start_date: datetime,
    end_date: datetime,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Retrieve messages within a date range."""
    try:
        with postgres_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT m.role, m.content, m.timestamp, m.routing_agent, cs.session_id
                FROM messages m
                JOIN conversation_sessions cs ON m.session_id = cs.session_id
                WHERE m.user_id = %s 
                  AND m.timestamp >= %s 
                  AND m.timestamp <= %s
                ORDER BY m.timestamp ASC
                LIMIT %s
            """, (user_id, start_date, end_date, limit))
            
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Temporal query failed: {str(e)}")
        return []

def parse_temporal_expression(query: str) -> Optional[Tuple[datetime, datetime]]:
    """Parse natural language temporal expressions."""
    query_lower = query.lower()
    now = datetime.utcnow()
    
    if "yesterday" in query_lower:
        start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0)
        end = start + timedelta(days=1)
        return (start, end)
    
    elif "last week" in query_lower:
        start = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0)
        end = now
        return (start, end)
    
    elif "today" in query_lower:
        start = now.replace(hour=0, minute=0, second=0)
        end = now
        return (start, end)
    
    # Add more patterns: "last month", "october 15", "this morning", etc.
    return None
```

**FalkorDB Temporal Queries:**
```python
async def get_knowledge_by_date_range(
    user_id: str,
    start_date: str,  # ISO 8601
    end_date: str
) -> List[Dict[str, Any]]:
    """Retrieve knowledge triples created within date range."""
    query = """
    MATCH (u:User {id: $user_id})-[:KNOWS_ABOUT]->(e1:Entity)-[r]->(e2:Entity)
    WHERE r.timestamp >= $start_date AND r.timestamp <= $end_date
    RETURN e1.name AS subject,
           type(r) AS predicate,
           e2.name AS object,
           r.timestamp AS timestamp,
           r.confidence AS confidence
    ORDER BY r.timestamp ASC
    """
    
    result = await falkordb_manager.execute_query(
        query,
        {"user_id": user_id, "start_date": start_date, "end_date": end_date},
        readonly=True
    )
    
    return [
        {
            "subject": row[0],
            "predicate": row[1],
            "object": row[2],
            "timestamp": row[3],
            "confidence": row[4]
        }
        for row in result
    ]
```

**Integration in Orchestrator:**
```python
async def stub_retrieve_memory(state: AgentState, chat_request: ChatRequest) -> AgentState:
    # Existing queries...
    
    # STEP 4: Temporal query detection
    temporal_range = parse_temporal_expression(chat_request.message)
    
    if temporal_range:
        start_date, end_date = temporal_range
        
        # Query PostgreSQL for messages in range
        temporal_messages = get_messages_by_date_range(
            user_id=chat_request.user_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Query FalkorDB for knowledge in range
        temporal_knowledge = await get_knowledge_by_date_range(
            user_id=chat_request.user_id,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )
        
        state["memory_context"]["temporal_messages"] = temporal_messages
        state["knowledge_graph_data"]["temporal_triples"] = temporal_knowledge
        
        logger.info(f"Temporal query: {len(temporal_messages)} messages, {len(temporal_knowledge)} triples")
    
    return state
```

**Acceptance Criteria:**
- [ ] "yesterday", "last week", "today" queries work
- [ ] Returns messages and knowledge from correct date range
- [ ] Handles timezone correctly (UTC)
- [ ] Empty results gracefully handled

**Estimated Effort:** 8 hours  
**Priority:** P1 (High Value)

---

### 2.2 Integrate Document RAG into Chat Flow

**Problem:** Documents uploaded but never queried during conversations

**Implementation:**
```python
def should_use_document_rag(query: str) -> bool:
    """Heuristic: Detect if query likely needs document context."""
    doc_keywords = [
        "document", "file", "uploaded", "pdf", "according to",
        "in the manual", "documentation says", "the file shows"
    ]
    return any(keyword in query.lower() for keyword in doc_keywords)

async def stub_retrieve_memory(state: AgentState, chat_request: ChatRequest) -> AgentState:
    # Existing queries...
    
    # STEP 5: Document RAG (conditional)
    document_chunks = []
    
    if should_use_document_rag(chat_request.message):
        try:
            doc_processor = get_document_processor()
            results = doc_processor.search_documents(
                query=chat_request.message,
                user_id=chat_request.user_id,
                limit=3
            )
            
            document_chunks = [
                {
                    "text": result["text"][:500],
                    "source": result["metadata"].get("filename", "unknown"),
                    "score": result["score"]
                }
                for result in results
            ]
            
            logger.info(f"Retrieved {len(document_chunks)} relevant document chunks")
        
        except Exception as e:
            logger.error(f"Document RAG failed: {str(e)}")
    
    state["memory_context"]["document_chunks"] = document_chunks
    return state
```

**Orchestrator Context Injection:**
```python
# In orchestrator_router()
document_context = state["memory_context"].get("document_chunks", [])

if document_context:
    doc_text = "\n\n".join([
        f"**From {chunk['source']}** (relevance: {chunk['score']:.2f}):\n{chunk['text']}"
        for chunk in document_context
    ])
    
    system_prompt += f"""

## RELEVANT DOCUMENT EXCERPTS

{doc_text}

Use this document context to answer the user's question.
"""
```

**Acceptance Criteria:**
- [ ] Document-related queries trigger RAG search
- [ ] Top 3 relevant chunks retrieved
- [ ] Source attribution included in context
- [ ] Works with PDF, DOCX, TXT uploads

**Estimated Effort:** 5 hours  
**Priority:** P1 (High Value)

---

### 2.3 Add Conversation Episode Grouping

**Goal:** Group messages into logical conversation episodes

**Implementation:**
```python
def detect_episode_boundary(
    previous_message: Dict[str, Any],
    current_message: Dict[str, Any],
    time_threshold_minutes: int = 30
) -> bool:
    """Detect if messages should be in different episodes."""
    time_gap = (current_message["timestamp"] - previous_message["timestamp"]).total_seconds() / 60
    
    # Episode boundary: 30+ minute gap OR topic shift
    if time_gap > time_threshold_minutes:
        return True
    
    # TODO: Add topic similarity check using embeddings
    return False

def update_episode_summaries():
    """Background task: Generate summaries for closed episodes."""
    try:
        with postgres_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Find episodes without summaries
            cursor.execute("""
                SELECT session_id, user_id, started_at, ended_at
                FROM conversation_sessions
                WHERE summary IS NULL
                  AND ended_at < NOW() - INTERVAL '1 hour'
                  AND message_count > 3
                LIMIT 10
            """)
            
            episodes = cursor.fetchall()
            
            for episode in episodes:
                # Get all messages
                messages = get_session_history(
                    user_id=episode["user_id"],
                    session_id=episode["session_id"],
                    limit=100
                )
                
                # Generate summary with LLM
                conversation_text = "\n".join([
                    f"{msg['role']}: {msg['content']}"
                    for msg in messages
                ])
                
                summary = generate_episode_summary(conversation_text)
                
                # Update database
                cursor.execute("""
                    UPDATE conversation_sessions
                    SET summary = %s
                    WHERE session_id = %s
                """, (summary, episode["session_id"]))
                
                postgres_conn.commit()
                logger.info(f"Generated summary for episode {episode['session_id']}")
    
    except Exception as e:
        logger.error(f"Episode summary generation failed: {str(e)}")

def generate_episode_summary(conversation_text: str) -> str:
    """Use LLM to generate concise episode summary."""
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "Summarize this conversation in 2-3 sentences. Focus on main topics and outcomes."
                },
                {"role": "user", "content": conversation_text[:4000]}
            ],
            "temperature": 0.3,
            "max_tokens": 150
        }
    )
    
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return "Summary generation failed"
```

**Background Task (add to startup):**
```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduler.add_job(update_episode_summaries, 'interval', hours=1)
scheduler.start()
```

**Acceptance Criteria:**
- [ ] Episodes auto-grouped by time gaps
- [ ] Summaries generated for closed episodes
- [ ] Can query "show me our conversation about Python"

**Estimated Effort:** 6 hours  
**Priority:** P2 (Medium)

---

## Sprint 3: Knowledge Evolution and Working Memory (Week 5-6)

**Goal:** Implement contradiction detection, add working memory system  
**Score Impact:** 82 → 88 (+6 points)

### 3.1 Contradiction Detection and Resolution

**Goal:** Detect conflicting facts and resolve them

**Implementation:**
```python
async def detect_contradictions(
    user_id: str,
    new_triple: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Check if new triple contradicts existing knowledge.
    
    Example contradiction:
    Existing: (User, LIVES_IN, San Francisco)
    New: (User, LIVES_IN, New York)
    """
    subject = new_triple["subject"]
    predicate = new_triple["predicate"]
    new_object = new_triple["object"]
    
    # Define mutually exclusive predicates
    exclusive_predicates = {
        "LIVES_IN", "WORKS_AT", "IS", "HAS_AGE",
        "IS_MARRIED_TO", "IS_EMPLOYED_BY"
    }
    
    if predicate not in exclusive_predicates:
        return []  # Non-exclusive predicate, no contradiction
    
    # Query existing facts with same subject + predicate
    query = """
    MATCH (e1:Entity {name: $subject})-[r:$predicate]->(e2:Entity)
    WHERE e2.name <> $new_object
    RETURN e2.name AS existing_object,
           r.timestamp AS timestamp,
           r.confidence AS confidence,
           r.context AS context
    """
    
    # Note: FalkorDB doesn't support parameterized relationship types directly
    # Workaround: Query all relationships and filter
    query = f"""
    MATCH (e1:Entity {{name: $subject}})-[r:{predicate}]->(e2:Entity)
    WHERE e2.name <> $new_object
    RETURN e2.name AS existing_object,
           r.timestamp AS timestamp,
           r.confidence AS confidence,
           r.context AS context
    """
    
    result = await falkordb_manager.execute_query(
        query,
        {"subject": subject, "new_object": new_object},
        readonly=True
    )
    
    contradictions = [
        {
            "existing_object": row[0],
            "timestamp": row[1],
            "confidence": row[2],
            "context": row[3]
        }
        for row in result
    ]
    
    return contradictions

async def resolve_contradiction(
    user_id: str,
    subject: str,
    predicate: str,
    old_object: str,
    new_object: str,
    new_confidence: float
):
    """
    Resolve contradiction by marking old fact as superseded.
    
    Strategy:
    1. Add 'superseded_by' property to old relationship
    2. Add 'supersedes' property to new relationship
    3. Keep both for audit trail
    """
    # Update old relationship
    update_query = f"""
    MATCH (e1:Entity {{name: $subject}})-[r:{predicate}]->(e2:Entity {{name: $old_object}})
    SET r.superseded_by = $new_object,
        r.superseded_at = $timestamp,
        r.active = false
    RETURN r
    """
    
    await falkordb_manager.execute_query(
        update_query,
        {
            "subject": subject,
            "old_object": old_object,
            "new_object": new_object,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    logger.info(f"✅ Resolved contradiction: {subject} {predicate} {old_object} → {new_object}")

async def write_knowledge_with_contradiction_check(
    user_id: str,
    triples: List[Dict[str, Any]],
    context: Optional[str] = None
) -> Dict[str, Any]:
    """Enhanced version of write_knowledge_to_falkordb with contradiction handling."""
    
    contradictions_resolved = 0
    
    for triple in triples:
        # Check for contradictions
        conflicts = await detect_contradictions(user_id, triple)
        
        if conflicts:
            logger.warning(f"⚠️ Contradiction detected for: {triple['subject']} {triple['predicate']} {triple['object']}")
            
            for conflict in conflicts:
                # Resolve if new fact has higher confidence
                if triple.get("confidence", 0.5) > conflict["confidence"]:
                    await resolve_contradiction(
                        user_id=user_id,
                        subject=triple["subject"],
                        predicate=triple["predicate"],
                        old_object=conflict["existing_object"],
                        new_object=triple["object"],
                        new_confidence=triple["confidence"]
                    )
                    contradictions_resolved += 1
        
        # Write new triple (using existing function)
        # ... existing write logic ...
    
    return {
        "success": True,
        "contradictions_resolved": contradictions_resolved
    }
```

**Integration:**
Replace `write_knowledge_to_falkordb` calls with `write_knowledge_with_contradiction_check`

**Acceptance Criteria:**
- [ ] Detects contradicting LIVES_IN, WORKS_AT facts
- [ ] Keeps audit trail of superseded facts
- [ ] New facts with higher confidence replace old ones
- [ ] Query results exclude superseded facts by default

**Estimated Effort:** 10 hours  
**Priority:** P1 (High Value)

---

### 3.2 Working Memory System

**Goal:** Track active topics and attention focus across conversation

**Implementation:**
```python
from typing import Dict, List, Tuple
from datetime import datetime, timedelta

class WorkingMemoryManager:
    """
    Manages short-term working memory with attention and decay.
    
    Working memory stores:
    - Active topics (with attention scores)
    - Recent entities mentioned
    - Current task/goal context
    """
    
    def __init__(self, decay_minutes: int = 15):
        self.memory: Dict[str, Dict[str, Any]] = {}  # user_id -> working memory
        self.decay_minutes = decay_minutes
    
    def update_focus(self, user_id: str, topics: List[str], entities: List[str]):
        """Update working memory with new topics and entities."""
        now = datetime.utcnow()
        
        if user_id not in self.memory:
            self.memory[user_id] = {
                "topics": {},
                "entities": {},
                "last_updated": now
            }
        
        # Update topics with attention boosting
        for topic in topics:
            if topic in self.memory[user_id]["topics"]:
                # Boost attention (repeated mention = higher importance)
                self.memory[user_id]["topics"][topic]["attention"] += 0.2
                self.memory[user_id]["topics"][topic]["last_mentioned"] = now
            else:
                self.memory[user_id]["topics"][topic] = {
                    "attention": 1.0,
                    "first_mentioned": now,
                    "last_mentioned": now
                }
        
        # Update entities
        for entity in entities:
            if entity in self.memory[user_id]["entities"]:
                self.memory[user_id]["entities"][entity]["count"] += 1
                self.memory[user_id]["entities"][entity]["last_mentioned"] = now
            else:
                self.memory[user_id]["entities"][entity] = {
                    "count": 1,
                    "first_mentioned": now,
                    "last_mentioned": now
                }
        
        self.memory[user_id]["last_updated"] = now
    
    def get_active_context(self, user_id: str) -> Dict[str, Any]:
        """Get current working memory context with decay applied."""
        if user_id not in self.memory:
            return {"topics": [], "entities": [], "focus": None}
        
        now = datetime.utcnow()
        decay_threshold = now - timedelta(minutes=self.decay_minutes)
        
        # Apply time decay to attention scores
        active_topics = []
        for topic, data in self.memory[user_id]["topics"].items():
            if data["last_mentioned"] > decay_threshold:
                # Time decay factor
                minutes_ago = (now - data["last_mentioned"]).total_seconds() / 60
                decay_factor = max(0.1, 1.0 - (minutes_ago / self.decay_minutes))
                
                active_topics.append({
                    "topic": topic,
                    "attention": data["attention"] * decay_factor,
                    "age_minutes": minutes_ago
                })
        
        # Sort by attention score
        active_topics.sort(key=lambda x: x["attention"], reverse=True)
        
        # Get recent entities
        active_entities = [
            entity for entity, data in self.memory[user_id]["entities"].items()
            if data["last_mentioned"] > decay_threshold
        ]
        
        return {
            "topics": [t["topic"] for t in active_topics[:3]],  # Top 3 topics
            "primary_focus": active_topics[0]["topic"] if active_topics else None,
            "entities": active_entities[:5],  # Top 5 entities
            "attention_scores": {t["topic"]: t["attention"] for t in active_topics}
        }
    
    def clear_user_memory(self, user_id: str):
        """Clear working memory for a user (explicit reset)."""
        if user_id in self.memory:
            del self.memory[user_id]

# Global instance
working_memory = WorkingMemoryManager(decay_minutes=15)

# Integration in orchestrator
async def stub_retrieve_memory(state: AgentState, chat_request: ChatRequest) -> AgentState:
    # ... existing queries ...
    
    # STEP 6: Get working memory context
    working_context = working_memory.get_active_context(chat_request.user_id)
    state["memory_context"]["working_memory"] = working_context
    
    return state

# Update working memory after response
def knowledge_consolidation_node(state: AgentState) -> AgentState:
    # ... existing extraction ...
    
    # Extract topics and entities from conversation
    user_query = state.get("user_query", "")
    agent_response = state.get("agent_response", "")
    
    # Simple keyword extraction (could use NER later)
    topics = extract_topics(user_query + " " + agent_response)
    entities = [triple["subject"] for triple in triples] + [triple["object"] for triple in triples]
    
    # Update working memory
    working_memory.update_focus(
        user_id=state["user_id"],
        topics=topics,
        entities=entities
    )
    
    return state

def extract_topics(text: str) -> List[str]:
    """Extract topics using simple keyword extraction."""
    # Placeholder: Could use spaCy NER or LLM extraction
    keywords = {
        "planning", "code", "debug", "research", "document",
        "api", "database", "frontend", "backend", "deployment"
    }
    
    words = text.lower().split()
    return list(set(word for word in words if word in keywords))
```

**Orchestrator Integration:**
```python
# In orchestrator_router()
working_context = state["memory_context"].get("working_memory", {})

if working_context and working_context.get("primary_focus"):
    system_prompt += f"""

## WORKING MEMORY (Current Conversation Focus)

**Primary Focus:** {working_context["primary_focus"]}
**Active Topics:** {", ".join(working_context.get("topics", []))}
**Recent Entities:** {", ".join(working_context.get("entities", []))}

This shows what the user is currently focused on. Use this to maintain conversation coherence.
"""
```

**Acceptance Criteria:**
- [ ] Topics tracked across conversation
- [ ] Attention scores decay over time (15 min)
- [ ] Primary focus identified
- [ ] Helps agent maintain context across turns

**Estimated Effort:** 8 hours  
**Priority:** P2 (Medium-High)

---

## Sprint 4: Prospective Memory and Polish (Week 7-8)

**Goal:** Add future intentions tracking, optimize performance  
**Score Impact:** 88 → 90+ (+2-5 points)

### 4.1 Prospective Memory System

**Schema:**
```sql
CREATE TABLE intentions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) REFERENCES users(id),
    description TEXT NOT NULL,
    due_date TIMESTAMP,
    priority VARCHAR(20) DEFAULT 'medium', -- 'low', 'medium', 'high', 'urgent'
    status VARCHAR(20) DEFAULT 'pending',   -- 'pending', 'completed', 'cancelled'
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_intentions_user_status ON intentions(user_id, status, due_date);
```

**Implementation:**
```python
def store_intention(
    user_id: str,
    description: str,
    due_date: Optional[datetime] = None,
    priority: str = "medium"
):
    """Store a future intention or reminder."""
    try:
        with postgres_conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO intentions (user_id, description, due_date, priority)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (user_id, description, due_date, priority))
            
            intention_id = cursor.fetchone()[0]
            postgres_conn.commit()
            
            logger.info(f"Stored intention {intention_id} for user {user_id}")
            return intention_id
    
    except Exception as e:
        logger.error(f"Failed to store intention: {str(e)}")
        return None

def get_due_intentions(user_id: str) -> List[Dict[str, Any]]:
    """Get intentions that are due or overdue."""
    try:
        with postgres_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, description, due_date, priority
                FROM intentions
                WHERE user_id = %s
                  AND status = 'pending'
                  AND due_date <= NOW()
                ORDER BY priority DESC, due_date ASC
            """, (user_id,))
            
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Failed to retrieve intentions: {str(e)}")
        return []

# Check intentions at session start
async def check_pending_intentions(user_id: str) -> List[str]:
    """Check for due intentions and return reminders."""
    intentions = get_due_intentions(user_id)
    
    reminders = []
    for intention in intentions:
        reminders.append(
            f"📌 Reminder: {intention['description']} (due: {intention['due_date'].strftime('%Y-%m-%d')})"
        )
    
    return reminders

# Integration in chat endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(chat_request: ChatRequest, user_id: str = Depends(get_current_user_id)):
    # Check for pending reminders
    reminders = await check_pending_intentions(user_id)
    
    if reminders:
        reminder_text = "\n".join(reminders)
        # Inject reminders into response or state
        logger.info(f"User {user_id} has {len(reminders)} pending reminders")
    
    # ... existing chat logic ...
```

**Natural Language Intent Detection:**
```python
def detect_intention_request(message: str) -> Optional[Dict[str, Any]]:
    """Detect if user is setting a future intention."""
    patterns = [
        (r"remind me (?:to )?(.*?)(?:on|in|at|next) (.*)", "reminder"),
        (r"follow up (?:on )?(.*?)(?:in|at|next) (.*)", "follow_up"),
        (r"i need to (.*?)(?:by|before) (.*)", "task"),
    ]
    
    import re
    from dateutil import parser
    
    for pattern, intent_type in patterns:
        match = re.search(pattern, message.lower())
        if match:
            description = match.group(1).strip()
            time_expr = match.group(2).strip()
            
            # Parse time expression
            try:
                due_date = parser.parse(time_expr, fuzzy=True)
                return {
                    "type": intent_type,
                    "description": description,
                    "due_date": due_date
                }
            except:
                pass
    
    return None
```

**Acceptance Criteria:**
- [ ] Users can set reminders with natural language
- [ ] Reminders shown at login or due date
- [ ] Can mark intentions as completed
- [ ] Priority levels work correctly

**Estimated Effort:** 6 hours  
**Priority:** P2 (Nice to Have)

---

### 4.2 Performance Optimization

**Caching Layer:**
```python
import redis
from functools import wraps
import json

redis_client = redis.Redis(host='graph_db', port=6379, db=1, decode_responses=True)

def cache_memory_query(ttl_seconds: int = 300):
    """Cache decorator for memory queries."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"mem_cache:{func.__name__}:{json.dumps(args)}:{json.dumps(kwargs)}"
            
            # Check cache
            cached = redis_client.get(cache_key)
            if cached:
                logger.debug(f"Cache hit: {func.__name__}")
                return json.loads(cached)
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            redis_client.setex(cache_key, ttl_seconds, json.dumps(result))
            
            return result
        return wrapper
    return decorator

# Apply to expensive queries
@cache_memory_query(ttl_seconds=300)
def get_user_knowledge_cached(user_id: str, limit: int = 10) -> List[Dict]:
    return asyncio.run(falkordb_manager.get_user_knowledge_triples(user_id, limit))
```

**Batch FalkorDB Writes:**
```python
async def write_knowledge_batch(
    user_id: str,
    triples: List[Dict[str, Any]],
    context: Optional[str] = None
) -> Dict[str, Any]:
    """Optimized batch write using Cypher multi-statement."""
    
    # Build single parameterized query for all triples
    queries = []
    params = {"user_id": user_id, "timestamp": datetime.utcnow().isoformat()}
    
    for idx, triple in enumerate(triples):
        queries.append(f"""
            MERGE (s{idx}:Entity {{name: $subject{idx}}})
            MERGE (o{idx}:Entity {{name: $object{idx}}})
            MERGE (s{idx})-[r{idx}:{triple['predicate']}]->(o{idx})
            SET r{idx}.confidence = $confidence{idx},
                r{idx}.timestamp = $timestamp
        """)
        
        params[f"subject{idx}"] = triple["subject"]
        params[f"object{idx}"] = triple["object"]
        params[f"confidence{idx}"] = triple.get("confidence", 0.8)
    
    combined_query = "\n".join(queries)
    
    await falkordb_manager.execute_query(combined_query, params)
    
    logger.info(f"Batch wrote {len(triples)} triples in single query")
```

**Acceptance Criteria:**
- [ ] Memory queries 50% faster with caching
- [ ] Batch writes reduce FalkorDB latency
- [ ] Cache invalidation works correctly

**Estimated Effort:** 4 hours  
**Priority:** P3 (Optimization)

---

## Final Testing and Validation

### End-to-End Test Suite

```bash
#!/bin/bash
# comprehensive_memory_test.sh

echo "=== DemestiChat Memory System Test Suite ==="

# Test 1: Persistence across restarts
echo "Test 1: Container restart persistence"
curl -X POST http://localhost:8000/chat -H "Authorization: Bearer $TOKEN" \
  -d '{"user_id": "test_user", "message": "Remember: my API key is test123"}'

docker-compose restart agent mem0 graph_db
sleep 10

RESPONSE=$(curl -s -X POST http://localhost:8000/chat -H "Authorization: Bearer $TOKEN" \
  -d '{"user_id": "test_user", "message": "What is my API key?"}')

echo "$RESPONSE" | grep -q "test123" && echo "✅ PASS" || echo "❌ FAIL"

# Test 2: Temporal queries
echo "Test 2: Temporal query (yesterday)"
curl -X POST http://localhost:8000/chat -d '{"user_id": "test_user", "message": "What did we discuss yesterday?"}'
echo "Check manually - should return yesterday's messages"

# Test 3: Cross-modal integration
echo "Test 3: Document + Knowledge Graph + Conversation"
curl -X POST http://localhost:8000/api/documents/upload -F "file=@test.pdf"
curl -X POST http://localhost:8000/chat \
  -d '{"user_id": "test_user", "message": "According to the document, what are the requirements?"}'
echo "Should retrieve from Qdrant AND cite source"

# Test 4: Contradiction resolution
echo "Test 4: Contradiction handling"
curl -X POST http://localhost:8000/chat -d '{"user_id": "test_user", "message": "I live in San Francisco"}'
sleep 2
curl -X POST http://localhost:8000/chat -d '{"user_id": "test_user", "message": "I moved to New York"}'
sleep 2
curl -X POST http://localhost:8000/chat -d '{"user_id": "test_user", "message": "Where do I live?"}'
echo "Should say New York (old fact superseded)"

# Test 5: Working memory
echo "Test 5: Working memory focus tracking"
SESSION_ID=$(uuidgen)
curl -X POST http://localhost:8000/chat -d "{\"user_id\": \"test_user\", \"chat_id\": \"$SESSION_ID\", \"message\": \"Let's plan a vacation to Japan\"}"
curl -X POST http://localhost:8000/chat -d "{\"user_id\": \"test_user\", \"chat_id\": \"$SESSION_ID\", \"message\": \"What's the weather like?\"}"
echo "Should understand weather query is about Japan (working memory context)"

# Test 6: Prospective memory
echo "Test 6: Reminder system"
curl -X POST http://localhost:8000/chat -d '{"user_id": "test_user", "message": "Remind me to review the budget next Monday"}'
echo "Check PostgreSQL intentions table for stored reminder"

echo "=== Test Suite Complete ==="
```

---

## Success Metrics

| Sprint | Target Score | Key Deliverable |
|--------|--------------|-----------------|
| Sprint 1 | 75/100 | FalkorDB stub removed, PostgreSQL working |
| Sprint 2 | 82/100 | Temporal queries, Document RAG |
| Sprint 3 | 88/100 | Contradiction resolution, Working memory |
| Sprint 4 | 90/100 | Prospective memory, Performance optimization |

**Final Target: 87-90/100 (Production-Ready Stateful AI)**

---

## Maintenance and Monitoring

### Ongoing Tasks

1. **Daily:**
   - Monitor FalkorDB size growth
   - Check PostgreSQL disk usage
   - Review error logs for memory failures

2. **Weekly:**
   - Generate episode summaries (background job)
   - Clean up old working memory (> 24 hours)
   - Audit contradiction resolutions

3. **Monthly:**
   - Backup all databases (PostgreSQL, FalkorDB, Qdrant)
   - Review memory retrieval performance
   - Analyze user interaction patterns

### Alerts

```python
# Add health check alerts
@app.get("/health/memory")
async def memory_health_check():
    """Comprehensive memory system health check."""
    health = {
        "timestamp": datetime.utcnow().isoformat(),
        "status": "healthy",
        "components": {}
    }
    
    # FalkorDB check
    try:
        node_count = await falkordb_manager.execute_query(
            "MATCH (n) RETURN count(n) AS count",
            readonly=True
        )
        health["components"]["falkordb"] = {
            "status": "healthy",
            "node_count": node_count[0][0] if node_count else 0
        }
    except:
        health["components"]["falkordb"] = {"status": "unhealthy"}
        health["status"] = "degraded"
    
    # PostgreSQL check
    try:
        with postgres_conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM messages")
            message_count = cursor.fetchone()[0]
            health["components"]["postgres"] = {
                "status": "healthy",
                "message_count": message_count
            }
    except:
        health["components"]["postgres"] = {"status": "unhealthy"}
        health["status"] = "degraded"
    
    # Mem0/Qdrant check
    try:
        mem0_response = requests.get("http://mem0:8080/health", timeout=2)
        health["components"]["mem0"] = {
            "status": "healthy" if mem0_response.status_code == 200 else "unhealthy"
        }
    except:
        health["components"]["mem0"] = {"status": "unhealthy"}
        health["status"] = "degraded"
    
    return health
```

---

**END OF STATEFULNESS_ROADMAP.MD**

*This roadmap provides a concrete, sprint-by-sprint plan to achieve 87+ statefulness score within 6-8 weeks.*
