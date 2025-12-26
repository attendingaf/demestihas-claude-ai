# 📋 PM Sprint 1 (Revised): Foundation Architecture
## Getting Yanay Live with Memory

**Created**: August 25, 2025, 15:00 UTC
**PM Thread**: #13
**Sprint Duration**: 5 days
**Priority**: IMMEDIATE - Family experiencing daily friction

---

## 🎯 Sprint Objectives

### Primary Goal
Complete the Yanay/Lyco architectural split and add basic conversation memory to immediately improve family experience from 60% to 85% task extraction accuracy.

### Success Criteria
1. ✅ Yanay orchestrator handling all conversations
2. ✅ Lyco API providing clean task interface  
3. ✅ Redis storing 20-message conversation context
4. ✅ "That/it" reference resolution working
5. ✅ Side-by-side deployment with current bot

---

## 📊 Current Pain Points (From Family)

- **"It doesn't remember what I just said"** - No conversation context
- **"I have to repeat everything"** - No reference resolution
- **"It misses half my tasks"** - Single-shot processing
- **Response times vary wildly** - Monolithic architecture

---

## 🏗️ Technical Plan

### Day 1-2: Yanay Orchestrator
**Owner**: Dev-Sonnet from handoff #001
**Deliverable**: yanay.py with conversation management

Key Features:
```python
- Message reception from Telegram
- Redis conversation storage (20 messages)
- Intent classification (task/query/correction)
- Reference resolution ("that", "it", "the meeting")
- Agent routing logic
```

### Day 2-3: Lyco API Split
**Owner**: Dev-Sonnet from handoff #002
**Deliverable**: lyco_api.py with clean task interface

API Endpoints:
```python
POST /task/create     - Create task from text
POST /task/extract    - Extract tasks from conversation
PUT  /task/{id}       - Update existing task
GET  /task/{id}       - Retrieve task details
```

### Day 3-4: Integration & Memory
**Owner**: Dev-Sonnet from handoff #003
**Deliverable**: Full conversation memory system

Memory Features:
```python
- Store user_id + last 20 messages
- Include task_ids in context
- Track entities mentioned
- 24-hour TTL on conversations
```

### Day 4-5: Testing & Deployment
**Owner**: QA-Claude
**Deliverable**: Validated system ready for family

Test Scenarios:
```
1. "Schedule dentist appointment" → Creates task
2. "Actually make that urgent" → Updates previous task
3. "What did I just ask you to do?" → Retrieves context
4. Multi-task messages → Extracts all tasks
```

---

## 📦 Atomic Handoffs Ready

### Already Created
1. **001_yanay_orchestrator.md** - Ready for implementation
2. **002_lyco_api_split.md** - Ready for implementation  
3. **003_conversation_memory.md** - Ready for implementation

### Deployment Strategy
- Deploy Yanay on port 8000 alongside current bot
- Test with Mene first (1 day)
- Migrate family members gradually
- Keep old bot as fallback for 1 week

---

## 🚀 Immediate Next Action

**For Developer (Sonnet)**: 
1. Read handoff #001 for Yanay orchestrator
2. Implement exactly as specified
3. Report completion in thread_log.md
4. Move to handoff #002

**Success Looks Like**:
```
User: "Book flight to Denver next month"
Yanay: "✅ Created task: Book flight to Denver (Due: September)"
User: "Make that October instead"
Yanay: "✅ Updated: Book flight to Denver (Due: October)"
```

---

## 📊 Measuring Success

### Sprint 1 Metrics
- Task extraction: 60% → 85%
- Response time: 2.5s → <2s
- Context retention: 0 → 20 messages
- Reference resolution: 0% → 90%

### Family Validation
- Mene: Test all workflows
- Get specific feedback on improvements
- Document remaining gaps for Sprint 2

---

## 🔄 Then What? (Sprint 2 Preview)

Once we have working Yanay + memory:
1. Add Hermes email integration (audio already built)
2. Implement validation layer for accuracy
3. Begin Supabase RAG if patterns emerge
4. Add web dashboard on port 8000

But FIRST, we need the foundation working.

---

## 🚦 Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaks existing bot | Deploy side-by-side, gradual migration |
| Memory overhead | Redis with TTL, max 20 messages |
| Complex integration | Atomic handoffs, clear interfaces |
| Family confusion | Test with Mene first, clear communication |

---

## ✅ PM Decision

**Path Forward**: Execute revised Sprint 1 focusing on immediate family value through architectural completion and basic memory.

**Rationale**: 
- Solves TODAY's problems
- Builds correct foundation
- Enables future RAG addition
- Maintains family trust

**Next Thread**: Developer to implement handoff #001 (Yanay Orchestrator)

---

*"Perfect memory can wait. Good-enough memory that works TODAY is what the family needs."*
