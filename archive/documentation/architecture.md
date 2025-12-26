# Demestihas.ai System Architecture

## System Overview

Multi-agent AI architecture with conversational orchestration layer, designed for ADHD-optimized family task management and coordination.

### Development Triad Structure

The system is built and maintained through a three-role AI development team:

```
┌─────────────────┐
│   PM (Opus)     │ Strategic planning, architecture design
│                 │ Creates atomic work packages
└────────┬────────┘
         │ Handoff Package
         ▼
┌─────────────────┐
│  Dev (Sonnet)   │ Tactical implementation
│                 │ Builds to specification
└────────┬────────┘
         │ QA Handoff
         ▼
┌─────────────────┐
│   QA (Claude)   │ Validation & testing
│                 │ Ensures family safety
└────────┬────────┘
         │
         ▼
    [Deployment]
```

**PM (Opus)**: Thinks deeply about family needs, makes architectural decisions, breaks work into 2-hour chunks
**Dev (Sonnet)**: Implements atomic tasks, writes clean code, documents changes
**QA (Claude)**: Tests thoroughly, protects family experience, validates performance

## Development Workflow

### Thread-Based Development
Each unit of work follows a numbered thread through the triad:

1. **PM Thread** (#1-100): Strategic decision, creates handoff package
2. **Dev Thread** (#101-200): Implementation from handoff, codes solution
3. **QA Thread** (#201-300): Validation of implementation, approval/rejection

All threads are logged in `thread_log.md` with complete handoff documentation.

### Handoff Packages
Structured documents in `/handoffs/` directory that ensure:
- Clear scope (ONE deliverable)
- Success criteria (testable)
- Implementation steps (specific)
- Rollback plan (safety)

## Architecture Principles

1. **Intelligence First:** Every agent (except Hermes) uses LLMs for natural understanding
2. **Single Responsibility:** Each agent does ONE thing excellently
3. **Loose Coupling:** Agents communicate through defined APIs
4. **Family First:** Every design decision optimizes for family usability
5. **ADHD Aware:** Low cognitive load, visual feedback, context preservation
6. **Fail Gracefully:** System degrades rather than breaks

### LLM Usage Philosophy
- **Agents, Not Workflows:** We build intelligent agents that understand natural language
- **Cost vs Capability:** $0.01 per interaction is acceptable for true understanding
- **Default to Intelligence:** Unless explicitly justified, every agent gets LLM capability
- **Hermes Exception:** Hermes is a processing pipeline, not an autonomous agent

## System Diagram

```
┌─────────────────────────────────────────────┐
│              USER INTERFACES                 │
├──────────┬────────────┬─────────────────────┤
│ Telegram │   Twilio   │   Web Dashboard     │
│  (Live)  │  (Future)  │    (Planned)        │
└──────────┴────────────┴─────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│         YANAY (Orchestration Layer)          │
├──────────────────────────────────────────────┤
│ • Conversation State Management (Redis)      │
│ • Intent Classification (Claude Haiku)       │
│ • Reference Resolution ("that", "it")        │
│ • Agent Routing & Coordination               │
│ • Response Generation & Formatting           │
└──────────────────────────────────────────────┘
               │
    ┌──────┼──────┼──────┬──────┬──────┐
    ▼      ▼      ▼      ▼      ▼
┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐
│ LYCO ││HUATA ││ NINA ││HEALTH││FAMILY│
│Tasks ││Calndr││AuPair││Agent ││Coord │
└──────┘└──────┘└──────┘└──────┘└──────┘
    │          │          │            │
    ▼          ▼          ▼            ▼
┌──────────────────────────────────────────────┐
│              DATA LAYER                      │
├──────────┬──────────┬──────────┬────────────┤
│  Notion  │ Supabase │  Google  │   Apple    │
│   API    │ (Future) │Workspace │  Health    │
└──────────┴──────────┴──────────┴────────────┘
```

## Agent Specifications

### Yanay (Orchestrator)
**Responsibility:** Conversation management and agent coordination
**Technology:** Python, Redis, Anthropic Claude
**Key Features:**
- 20-message conversation memory
- Intent classification with 90% accuracy
- Reference resolution for contextual understanding
- Multi-agent transaction coordination
- Natural language response generation

**API Endpoints:**
```
POST /message   - Process user message
GET  /context   - Retrieve conversation context
POST /feedback  - Handle user corrections
```

### Lyco (Task Management)
**Responsibility:** Task CRUD and intelligent categorization
**Technology:** Python, Notion API, Claude Haiku
**Key Features:**
- Eisenhower matrix auto-categorization
- Energy level assessment (Low/Medium/High)
- Time estimation (Quick/Short/Deep/Multi-hour)
- Family member assignment
- Context tag inference

**API Endpoints:**
```
POST   /task/create     - Create new task
GET    /task/{id}       - Retrieve task
PUT    /task/{id}       - Update task
DELETE /task/{id}       - Delete task
POST   /task/query      - Query tasks
POST   /task/extract    - Extract task from text
```

### Huata (Calendar) (Sprint 1 Priority)
**Responsibility:** Intelligent calendar management and scheduling
**Technology:** Google Calendar API, Python, Claude Haiku
**Architecture:** LLM-powered agent for natural calendar interactions
**Key Features:**
- Natural language calendar queries: "Am I free Thursday afternoon?"
- Intelligent conflict detection and resolution
- Availability analysis across family members
- Smart meeting scheduling with preferences
- Time blocking for tasks from Lyco
- Integration point for Nina's schedule data

**API Endpoints:**
```
GET  /availability   - Check free time slots
POST /event/create  - Schedule new event
GET  /conflicts     - Check scheduling conflicts
POST /block/time    - Block time for tasks
```

### Health Agent (Planned - Future)
**Responsibility:** Health tracking and optimization
**Technology:** Apple Health API, Supabase
**Key Features:**
- Sleep quality tracking
- Medication reminders
- Energy pattern learning
- ADHD symptom correlation

### Nina (Au Pair Scheduling) (Deployed - Needs LLM Upgrade)
**Responsibility:** Au pair schedule management and coverage coordination
**Technology:** Python, Redis, Claude Haiku (pending upgrade)
**Current State:** Rule-based parser failing on complex schedules
**Planned Upgrade:** LLM-powered natural language understanding
**Key Features:**
- Natural language schedule parsing (pending)
- Split shift support (pending)
- Coverage gap detection and alerting (working)
- Overtime/comp time calculation (working)
- Integration with Huata for calendar sync (pending)

### Family Coordinator (Planned - Future)
**Responsibility:** Multi-person task routing
**Technology:** Matrix/rules engine
**Key Features:**
- Age-appropriate task assignment
- Chore rotation
- Activity coordination
- Emergency escalation

## Communication Patterns

### Phase 1: Direct Function Calls (Current)
```python
# Yanay directly imports and calls Lyco
from lyco_api import LycoTaskAgent
lyco = LycoTaskAgent()
result = await lyco.create_task(task_data)
```

### Phase 2: HTTP REST APIs (Next)
```python
# Yanay calls Lyco via HTTP
response = await httpx.post(
    "http://localhost:8001/task/create",
    json=task_data
)
```

### Phase 3: Event-Driven (Future)
```python
# Redis pub/sub for async processing
await redis.publish("task.create", task_data)
# Lyco subscribes and processes
```

## Data Flow Examples

### Example 1: Simple Task Creation
```
1. User: "Buy milk tomorrow"
2. Telegram → Yanay
3. Yanay classifies: Intent = "create_task"
4. Yanay → Lyco: create_task({"text": "Buy milk", "due": "tomorrow"})
5. Lyco → Notion: Creates task with Eisenhower = "📅 Schedule"
6. Lyco → Yanay: Returns task_id and confirmation
7. Yanay → User: "✅ Task created: Buy milk (scheduled for tomorrow)"
```

### Example 2: Contextual Correction
```
1. User: "Review Consilium application"
2. Yanay: Creates task via Lyco
3. User: "Actually make that urgent"
4. Yanay: Resolves "that" to previous task
5. Yanay → Lyco: update_task(task_id, {"priority": "urgent"})
6. Lyco updates Notion
7. Yanay → User: "✅ Updated to urgent priority"
```

### Example 3: Multi-Agent Coordination
```
1. User: "Schedule dentist appointment next week"
2. Yanay detects: Task + Calendar needed
3. Yanay → Calendar: check_availability("next week")
4. Calendar returns: Available slots
5. Yanay → Lyco: create_task({"text": "Schedule dentist", "suggested_times": [...]})
6. Yanay → User: "Created task. You have these free slots: ..."
```

## State Management

### Conversation State (Redis)
```json
{
  "user_id": "telegram_123456",
  "messages": [
    {"role": "user", "content": "...", "timestamp": "..."},
    {"role": "assistant", "content": "...", "timestamp": "..."}
  ],
  "context": {
    "last_task_id": "uuid",
    "last_entity": "Consilium application",
    "family_member": "mene"
  },
  "ttl": 86400
}
```

### Task State (Notion)
```json
{
  "id": "notion_page_id",
  "properties": {
    "Name": "Task title",
    "Eisenhower": "🔥 Do Now",
    "Energy Level": "Medium",
    "Time Estimate": "🎯 Deep (>30m)",
    "Context": ["Work", "Deep Focus"],
    "Assigned To": "mene",
    "Due Date": "2025-08-20",
    "Complete": false
  }
}
```

## Deployment Architecture

### Current (Monolithic)
```yaml
services:
  bot:
    image: lyco-bot:v5
    ports: ["8000:8000"]
    environment:
      - All credentials
```

### Target (Microservices)
```yaml
services:
  yanay:
    image: yanay:v1
    ports: ["8000:8000"]
    depends_on: [redis, lyco]
  
  lyco:
    image: lyco-api:v1
    ports: ["8001:8001"]
  
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
```

## Security Considerations

1. **API Keys:** Environment variables only, never in code
2. **Family Data:** No PII in logs, encrypted at rest
3. **Child Safety:** Age-appropriate content filtering
4. **Rate Limiting:** Prevent runaway API costs
5. **Audit Logging:** Track all family member actions

## Performance Targets

| Metric | Current | Target | Maximum |
|--------|---------|---------|---------|
| Response Time | 2.5s | <2s | 3s |
| Task Extraction | 60% | 85% | 95% |
| Uptime | 95% | 99% | 99.9% |
| Concurrent Users | 1 | 6 | 20 |
| Memory Usage | 200MB | 150MB | 500MB |

## Migration Timeline

### Week 1: Foundation
- Day 1-2: Create Yanay orchestrator
- Day 3-4: Split Lyco into API
- Day 5: Integration testing

### Week 2: Enhancement
- Day 1-2: Add conversation memory
- Day 3-4: Implement voice support
- Day 5: Family beta testing

### Week 3: Expansion
- Add validation layer
- Create web dashboard
- Implement health agent

### Week 4: Polish
- Performance optimization
- Error handling improvements
- Documentation completion

## Technology Stack

### Core
- **Language:** Python 3.11+
- **Framework:** FastAPI (APIs), python-telegram-bot (interfaces)
- **AI:** Anthropic Claude (Haiku $0.25/M, Sonnet $3/M)
- **Database:** Notion API (tasks), Redis (cache), Supabase (future)

### Development Infrastructure
- **Local Development:** macOS, ~/Projects/demestihas-ai/
- **Version Control:** File-based state management
- **Documentation:** Markdown with strict update protocols
- **Testing:** pytest, performance profiling, family safety validation

### Infrastructure
- **Hosting:** VPS (Ubuntu 24.04)
- **Containers:** Docker + Docker Compose
- **Monitoring:** Prometheus + Grafana (planned)
- **Logging:** JSON structured logs

### Development
- **IDE:** Cursor (AI-assisted)
- **Version Control:** Git
- **Testing:** pytest + pytest-asyncio
- **Documentation:** Markdown + OpenAPI

## File Structure & State Management

### Project Directory
```
~/Projects/demestihas-ai/
├── PM_INSTRUCTIONS.md          # Strategic role guide
├── DEVELOPER_INSTRUCTIONS.md   # Implementation guide
├── QA_INSTRUCTIONS.md          # Validation guide
├── current_state.md            # System snapshot (always current)
├── thread_log.md               # Work history (append-only)
├── architecture.md             # This file
├── family_context.md           # Family profiles (read-only)
├── quickstart.md              # Quick reference
└── handoffs/                  # Work packages
    ├── 001_yanay_orchestrator.md
    ├── 002_lyco_api_split.md
    └── [active_handoffs].md
```

### State Management Protocol
1. **Before ANY work**: Read current_state.md and thread_log.md
2. **During work**: Update files locally first
3. **After work**: Update current_state.md, append to thread_log.md
4. **For deployment**: Create deployment package with exact changes

## Success Criteria

1. **Family Adoption:** 3+ active users in Week 1
2. **Task Success:** 85% extraction accuracy
3. **Performance:** <3 second response time
4. **Reliability:** <1 failure per day
5. **Cost:** <$50/month operational

---

**Note:** This architecture is designed for evolution. Start simple, measure everything, iterate based on family feedback.