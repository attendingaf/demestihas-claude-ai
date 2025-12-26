# Demestihas.ai Agent Philosophy

## Core Principle: Build Intelligent Agents, Not Deterministic Workflows

### The Lesson from Nina

The Nina scheduling agent's failure to parse "6a-9a and 2p-9p Tuesday through Friday" revealed a fundamental architectural flaw: we were building **workflows** when we needed **agents**.

**Workflow Approach (Failed):**
- Regex patterns for time parsing
- Hard-coded day mappings
- Rigid if/then logic
- Breaks on natural variations

**Agent Approach (Required):**
- LLM understands intent
- Natural language processing
- Context-aware decisions
- Handles any reasonable input

## Mandatory LLM Integration

### Every Agent Gets Intelligence
Unless explicitly justified otherwise, every agent in the Demestihas.ai system MUST incorporate LLM capabilities for its core decision-making.

**Required Components:**
```python
class AnyDemestihasAgent:
    def __init__(self):
        self.llm = Claude(model="haiku")  # Mandatory
        self.domain_tools = DomainAPI()   # Specific functionality
        self.state = Redis()               # Memory/context
```

### Cost vs Capability Trade-off

**Accepted Costs:**
- $0.01 per complex interaction
- $0.001 per simple query
- $0.25 per 1M tokens baseline

**Unacceptable Compromises:**
- Rigid command formats
- Pattern matching failures  
- "Command not recognized" errors
- High cognitive load for users

## Agent Architecture Pattern

### Standard Three-Layer Design

1. **Understanding Layer (LLM)**
   - Parse natural language input
   - Extract intent and entities
   - Handle variations gracefully

2. **Execution Layer (Tools)**
   - Domain-specific operations
   - API integrations
   - State management

3. **Response Layer (LLM)**
   - Generate natural responses
   - Explain actions taken
   - Suggest next steps

### Example Implementation
```python
async def process(self, user_input: str):
    # Layer 1: Understanding
    intent = await self.llm.understand(user_input)
    
    # Layer 2: Execution
    result = await self.execute_domain_action(intent)
    
    # Layer 3: Response
    response = await self.llm.generate_response(result)
    
    return response
```

## The Hermes Exception

Hermes is NOT an agent – it's a processing pipeline for audio transcription and analysis. It doesn't make autonomous decisions or interact conversationally.

**Pipelines (like Hermes):**
- Fixed processing stages
- Deterministic transformation
- No conversation state
- No decision-making

**Agents (everyone else):**
- Natural language understanding
- Contextual decision-making
- Conversational interaction
- Adaptive behavior

## Design Checklist for New Agents

Before building any new agent, ask:

- [ ] Does it need to understand natural language? → **Add LLM**
- [ ] Will users interact with it conversationally? → **Add LLM**  
- [ ] Does it need to handle variations in input? → **Add LLM**
- [ ] Should it make contextual decisions? → **Add LLM**
- [ ] Is it just transforming data? → **Consider pipeline instead**

## Family Impact

### What This Means for Users

**Before (Workflow):**
```
User: "Set Viola's schedule for next week"
Bot: "Please use format: SET DAY START_TIME END_TIME"
User: "SET MONDAY 7:00 19:00"
Bot: "Please specify AM or PM"
User: [Frustration increases, ADHD friction high]
```

**After (Agent):**
```
User: "Viola works her usual schedule but off Thursday"
Bot: "Got it! Viola's working Monday-Wednesday and Friday, 
      7am-7pm, with Thursday off. Should I notify her?"
User: "Yes"
Bot: "Done! I've also created a coverage task for Thursday."
```

## Implementation Priority

### Sprint 1: Huata (Calendar Agent)
Must be LLM-powered from day one. No regex. No patterns. Pure understanding.

### Sprint 2: Nina Upgrade
Fix the schedule parsing with LLM integration. This is the proof point.

### Sprint 3: Validation Agent
New agent for task validation – must use LLM to understand context.

### Future: All New Agents
Default to LLM integration. Justify any exceptions in writing.

## Metrics for Success

**Qualitative:**
- Every interaction feels natural
- No "command not recognized" errors
- Family actually uses the system
- Reduced cognitive load

**Quantitative:**
- 95% intent recognition accuracy
- <5% retry rate on commands
- 3+ family members active daily
- <3 second response time

## The Bottom Line

We're not building a command-line interface with natural language lipstick. We're building truly intelligent agents that understand and adapt to how humans naturally communicate.

**Every agent is a conversation, not a form.**

---

*This document establishes architectural law for the Demestihas.ai system. Violations require PM-level approval and written justification.*
