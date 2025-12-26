# Handoff #028: Huata Calendar Agent Implementation

## THREAD: Sprint 1 - Intelligent Calendar Management
**ATOMIC SCOPE:** Create LLM-powered Huata agent for natural language calendar interactions

## CONTEXT
- **Current State:** No calendar agent exists, Nina needs calendar integration
- **Architecture Decision:** All agents must use LLMs for intelligence
- **Dependencies:** Google Calendar API, Claude Haiku, Redis
- **Integration:** Will be used by Nina for schedule-to-calendar sync

## ARCHITECTURE REQUIREMENTS

### Core Principle: Intelligence First
Huata must understand natural language calendar queries WITHOUT rigid patterns:
- "Am I free Thursday afternoon?"
- "Schedule a meeting with Dr. Smith next week"
- "What's my day look like tomorrow?"
- "Find 2 hours for deep work this week"
- "When is Persy's next soccer game?"
- "Block time for that Consilium project review"

### LLM Integration Pattern
```python
class HuataCalendarAgent:
    def __init__(self):
        self.llm = Claude(model="haiku")  # Natural understanding
        self.gcal = GoogleCalendarAPI()    # Calendar operations
        self.redis = Redis()               # State management
    
    async def process_query(self, query: str, user_context: dict):
        # Step 1: LLM understands intent and extracts parameters
        intent = await self.llm.classify_calendar_intent(query)
        params = await self.llm.extract_calendar_params(query, user_context)
        
        # Step 2: Execute calendar operation
        result = await self.execute_calendar_action(intent, params)
        
        # Step 3: LLM generates natural response
        response = await self.llm.generate_calendar_response(result, query)
        return response
```

## IMPLEMENTATION SPEC

### File Structure
```
/root/demestihas-ai/
├── huata.py              # Main calendar agent
├── calendar_intents.py   # Intent classification system
├── calendar_tools.py     # Google Calendar API wrapper
└── calendar_prompts.py   # LLM prompt templates
```

### Core Features (Phase 1)

1. **Natural Query Understanding**
```python
CALENDAR_INTENTS = [
    "check_availability",    # Am I free? When can I meet?
    "schedule_event",        # Book a meeting, Schedule appointment
    "list_events",          # What's on my calendar? Show my day
    "find_time_slot",       # Find time for X, When can I do Y?
    "check_conflicts",      # Any conflicts? Double-booked?
    "block_time",          # Block time for, Reserve hours for
    "modify_event",        # Move meeting, Cancel appointment
    "event_details"        # Tell me about X meeting
]
```

2. **Time Expression Parsing (via LLM)**
```python
# LLM handles ALL variations naturally:
"next Thursday at 2"          → 2024-09-05T14:00:00
"tomorrow afternoon"           → 2024-08-28T15:00:00
"early next week"             → 2024-09-02T09:00:00
"after Persy gets home"       → 2024-08-27T15:30:00
"during Viola's shift"        → (check Nina for schedule)
```

3. **Family Context Awareness**
```python
FAMILY_CONTEXT = {
    "mene": {"calendar_id": "primary", "work_hours": "9-5"},
    "cindy": {"calendar_id": "cindy@...", "shift_pattern": "variable"},
    "persy": {"calendar_id": "family", "school_hours": "8-3"},
    "viola": {"source": "nina_agent", "schedule_type": "au_pair"}
}
```

4. **Integration Points**

**FROM Yanay:**
```python
# Yanay routes calendar intents to Huata
if intent == "calendar_query":
    result = await huata.process_query(message, context)
```

**TO Nina:**
```python
# Nina can check Huata for conflicts
conflicts = await huata.check_conflicts(
    start_time="2024-08-29T18:00:00",
    end_time="2024-08-29T21:00:00",
    calendars=["mene", "cindy"]
)
```

**TO Lyco:**
```python
# Huata can create time-blocked tasks
await lyco.create_task({
    "title": "Deep work: Consilium review",
    "calendar_blocked": True,
    "start_time": slot["start"],
    "duration": "2 hours"
})
```

### API Endpoints
```python
POST /calendar/query        # Natural language calendar query
POST /calendar/schedule     # Create calendar event
GET  /calendar/availability # Check free/busy times
POST /calendar/conflicts    # Check for conflicts
GET  /calendar/events       # List events (with NL filters)
POST /calendar/block        # Block time for tasks
```

### LLM Prompts Structure
```python
CALENDAR_UNDERSTANDING_PROMPT = """
You are Huata, the family's calendar assistant. Parse this calendar query:
Query: {query}

Current date/time: {current_time}
User context: {user_context}
Family members: {family_members}

Extract:
1. Intent (check_availability/schedule/list/find_slot/etc)
2. Time expressions (convert to ISO format)
3. Participants (who is involved)
4. Duration (if applicable)
5. Location (if mentioned)
6. Priority/urgency markers

Return as JSON.
"""

RESPONSE_GENERATION_PROMPT = """
Generate a natural, friendly response about this calendar result:
Query: {original_query}
Result: {calendar_result}

Guidelines:
- Be conversational and helpful
- Mention specific times in human-friendly format
- Flag any conflicts or concerns
- Suggest alternatives if needed
- Keep it concise but complete
"""
```

## GOOGLE CALENDAR SETUP

### Required Scopes
```python
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events'
]
```

### Service Account Configuration
```bash
# Create service account credentials
gcloud iam service-accounts create huata-calendar \
    --display-name="Huata Calendar Agent"

# Download credentials
gcloud iam service-accounts keys create \
    /root/demestihas-ai/credentials/huata-service-account.json \
    --iam-account=huata-calendar@project.iam.gserviceaccount.com

# Grant calendar access (domain-wide delegation needed)
# This must be done in Google Workspace Admin Console
```

## SUCCESS TESTS

### Test 1: Natural Availability Check
```python
# Input
"Am I free Thursday afternoon?"

# Expected Flow
1. LLM extracts: intent=check_availability, time=Thursday PM
2. Calendar API checks 2024-08-29 12:00-17:00
3. Returns: "You're free Thursday afternoon except for a 30-minute call at 2pm"
```

### Test 2: Complex Scheduling
```python
# Input
"Schedule 90 minutes with the Consilium team next week when both Cindy and I are free"

# Expected Flow
1. LLM extracts: intent=schedule, duration=90min, participants=[mene,cindy]
2. Checks both calendars for common free slots
3. Suggests: "I found these times when you're both free:
   - Tuesday 10-11:30am
   - Wednesday 2-3:30pm
   - Friday 9-10:30am"
```

### Test 3: Nina Integration
```python
# Input (to Nina)
"Viola needs Thursday off"

# Nina → Huata Flow
1. Nina marks exception in schedule
2. Nina calls Huata: "Block Thursday 7am-7pm as 'Viola off - need coverage'"
3. Huata creates calendar event with alert
```

## ROLLBACK PLAN

If Huata fails:
1. Stop container: `docker stop huata-agent`
2. Yanay continues without calendar routing
3. Nina continues with current scheduling (no calendar sync)
4. Remove huata.py imports from yanay.py

## DEPLOYMENT STEPS

1. **Local Development** (1 hour)
   - Create huata.py with LLM integration
   - Test with mock calendar data
   - Validate natural language understanding

2. **Google Calendar Setup** (30 min)
   - Configure service account
   - Test API access
   - Verify calendar read/write

3. **Integration** (30 min)
   - Add Huata routing to Yanay
   - Test end-to-end flow
   - Verify response formatting

4. **Deployment** (15 min)
   - Deploy to VPS
   - Run integration tests
   - Monitor first queries

## REPORTING

Update current_state.md:
```markdown
### Huata Agent
**Status:** Deployed
**Version:** v1.0-llm-powered
**Response Time:** <2 seconds
**Accuracy:** 95% intent classification
**Integration:** Yanay routing, Nina scheduling, Lyco tasks
```

Add to thread_log.md:
```markdown
## Thread #[N] - Huata Calendar Agent Deployment
**Outcome:** Success
**Key Achievement:** Natural language calendar understanding
**Family Impact:** "Am I free?" actually works now
```

## COST ANALYSIS

- **Per Query:** ~500 tokens × $0.25/1M = $0.000125
- **Daily (50 queries):** $0.00625
- **Monthly:** ~$0.19
- **Verdict:** Negligible cost for massive usability gain

## KEY SUCCESS METRIC

**Family can ask calendar questions naturally and get intelligent responses**

Not pattern matching. Not rigid commands. Real understanding.
