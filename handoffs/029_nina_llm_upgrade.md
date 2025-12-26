# Handoff #029: Nina LLM Upgrade - Natural Schedule Understanding

## THREAD: Sprint 2 - Fix Nina's Schedule Parsing with LLM Intelligence
**ATOMIC SCOPE:** Upgrade Nina from rule-based to LLM-powered schedule parsing

## CONTEXT
- **Current Problem:** Nina can't parse "6a-9a and 2p-9p Tuesday through Friday"
- **Root Cause:** Using regex patterns instead of natural understanding
- **Dependencies:** Huata must be deployed first (calendar integration)
- **Impact:** Currently giving wrong schedule information to family

## FAILURE ANALYSIS

### What's Breaking
```python
# User says:
"Viola is scheduled 6a-9a and 2p-9p Tuesday through Friday"

# Nina shows (WRONG):
Monday: 07:00-19:00     # Should be OFF
Tuesday: 07:00-19:00    # Should be split shift
Thursday: OFF           # Should be working
```

### Why It's Breaking
Current code uses rigid patterns:
```python
# Current (BROKEN) approach
time_pattern = r'(\d{1,2}):?(\d{2})?\s*(am|pm)?'
day_pattern = r'(monday|tuesday|wednesday|...)'

# Can't handle:
- "6a-9a and 2p-9p" (split shifts)
- "Tuesday through Friday" (ranges)
- "off next Monday and Wednesday" (multiple exceptions)
- "usual schedule but starting at 8" (modifications)
```

## SOLUTION: LLM-POWERED UNDERSTANDING

### New Architecture
```python
class NinaScheduleAgent:
    def __init__(self):
        self.llm = Claude(model="haiku")     # ADD THIS
        self.huata = HuataCalendarAgent()    # Integration
        self.redis = Redis()                 # Keep state
    
    async def process_schedule_command(self, command: str):
        # Step 1: LLM understands the schedule change
        schedule_data = await self.llm.parse_schedule_command(command)
        
        # Step 2: Update Redis state
        await self.update_schedule_state(schedule_data)
        
        # Step 3: Detect gaps and conflicts
        gaps = await self.detect_coverage_gaps(schedule_data)
        conflicts = await self.huata.check_conflicts(schedule_data)
        
        # Step 4: Generate response
        response = await self.llm.generate_schedule_response(
            schedule_data, gaps, conflicts
        )
        return response
```

### LLM Prompt for Schedule Parsing
```python
SCHEDULE_PARSING_PROMPT = """
You are Nina, the au pair scheduling assistant. Parse this schedule command:

Command: {command}
Current date: {current_date}
Baseline schedule: Monday-Friday 7:00-19:00, Weekends off

Extract the schedule information:
1. Days affected (use ISO format: 2024-08-29)
2. Time blocks for each day (support split shifts)
3. Type of change (exception/permanent/temporary)
4. Duration (one-time/recurring/date range)

Examples of what you must handle:
- "6a-9a and 2p-9p" → two time blocks: 06:00-09:00, 14:00-21:00
- "Tuesday through Friday" → 2024-08-27 through 2024-08-30
- "off Monday" → Monday is OFF (no time blocks)
- "usual hours but until 8pm" → 07:00-20:00
- "covering Saturday morning" → Saturday 07:00-12:00

Return as JSON:
{
  "days": [
    {
      "date": "2024-08-29",
      "day_name": "Thursday", 
      "shifts": [
        {"start": "06:00", "end": "09:00"},
        {"start": "14:00", "end": "21:00"}
      ]
    }
  ],
  "change_type": "exception|permanent",
  "reason": "extracted reason if mentioned"
}
"""
```

## IMPLEMENTATION CHANGES

### 1. Update nina.py
```python
# OLD (remove)
def parse_schedule_time(self, time_str):
    pattern = r'(\d{1,2}):?(\d{2})?\s*(am|pm)?'
    # Brittle regex logic...

# NEW (add)
async def parse_schedule_with_llm(self, command, context):
    prompt = SCHEDULE_PARSING_PROMPT.format(
        command=command,
        current_date=datetime.now().isoformat()
    )
    
    response = await self.llm.complete(
        prompt=prompt,
        max_tokens=500,
        temperature=0.2  # Low temp for consistency
    )
    
    return json.loads(response)
```

### 2. Enhanced Schedule State
```python
# Support split shifts in Redis
{
  "baseline_schedule": {
    "monday": [{"start": "07:00", "end": "19:00"}],
    "tuesday": [
      {"start": "06:00", "end": "09:00"},
      {"start": "14:00", "end": "21:00"}
    ],
    # ...
  },
  "exceptions": {
    "2024-08-29": "OFF",
    "2024-09-05": [{"start": "08:00", "end": "17:00"}]
  }
}
```

### 3. Huata Integration
```python
async def sync_to_calendar(self, schedule_data):
    """Push schedule to Google Calendar via Huata"""
    
    for day in schedule_data["days"]:
        if not day["shifts"]:  # Day off
            await self.huata.block_time(
                date=day["date"],
                title="Viola OFF - Coverage Needed",
                all_day=True,
                alert=True
            )
        else:  # Working shifts
            for shift in day["shifts"]:
                await self.huata.create_event(
                    date=day["date"],
                    start=shift["start"],
                    end=shift["end"],
                    title="Viola Coverage",
                    calendar="family"
                )
```

## TEST CASES

### Test 1: Split Shift Parsing
```python
# Input
"Viola works 6am-9am and 2pm-9pm Tuesday through Friday"

# Expected Output
Tuesday: [06:00-09:00, 14:00-21:00] ✓
Wednesday: [06:00-09:00, 14:00-21:00] ✓
Thursday: [06:00-09:00, 14:00-21:00] ✓
Friday: [06:00-09:00, 14:00-21:00] ✓
```

### Test 2: Complex Exceptions
```python
# Input
"Viola off Thursday, working Saturday 10-4, and Friday ends at 3pm"

# Expected Output
Thursday: OFF
Friday: [07:00-15:00]
Saturday: [10:00-16:00]
```

### Test 3: Natural Variations
```python
# All should work:
"Regular schedule next week"
"She's off Monday"
"Can she come in early tomorrow?"
"Need coverage Thursday afternoon"
"Viola has a doctor's appointment Tuesday morning"
```

## MIGRATION PATH

### Phase 1: Parallel Processing (Safe)
```python
async def process_schedule(self, command):
    # Try both approaches
    llm_result = await self.parse_schedule_with_llm(command)
    regex_result = self.old_parse_schedule(command)  # Keep old
    
    # Log differences for validation
    if llm_result != regex_result:
        logger.info(f"Parse difference: LLM={llm_result}, Regex={regex_result}")
    
    # Use LLM but fall back if it fails
    return llm_result or regex_result
```

### Phase 2: LLM Primary (After Validation)
```python
async def process_schedule(self, command):
    try:
        return await self.parse_schedule_with_llm(command)
    except Exception as e:
        logger.error(f"LLM parsing failed: {e}")
        # Fallback to basic baseline
        return self.get_baseline_schedule()
```

### Phase 3: Remove Old Parser (After 1 Week)
- Delete all regex patterns
- Remove old parsing functions
- Pure LLM implementation

## SUCCESS METRICS

1. **Accuracy:** 95% correct schedule parsing
2. **Split Shifts:** Properly handled in all cases
3. **Day Ranges:** "Tuesday through Friday" works
4. **Calendar Sync:** Schedule appears in Google Calendar
5. **Gap Detection:** Coverage tasks auto-created

## ROLLBACK PLAN

If LLM parsing fails:
1. Revert nina.py to regex version
2. Disable Huata integration temporarily
3. Log all failed parses for analysis
4. Fall back to baseline schedule

## DEPLOYMENT

1. **Update nina.py** (30 min)
   - Add LLM integration
   - Keep parallel processing initially
   - Add comprehensive logging

2. **Test Locally** (30 min)
   - Run all test cases
   - Verify Huata integration
   - Check Redis state updates

3. **Deploy to VPS** (15 min)
   - Update container
   - Run smoke tests
   - Monitor first 10 real commands

4. **Validation** (1 day)
   - Track accuracy metrics
   - Gather family feedback
   - Tune prompts if needed

## COST IMPACT

- **Per Schedule Command:** ~800 tokens = $0.0002
- **Daily (10 changes):** $0.002
- **Monthly:** $0.06
- **Worth it:** Absolutely yes for accuracy

## REPORTING

Update thread_log.md after deployment:
```markdown
## Thread #[N] - Nina LLM Upgrade
**Problem Solved:** Split shift parsing now works
**Accuracy:** 95% schedule understanding
**Family Impact:** Viola's actual schedule reflected correctly
```

## THE CRITICAL FIX

From broken:
```
"6a-9a and 2p-9p Tuesday through Friday"
→ Shows Monday working, Thursday off (WRONG)
```

To working:
```
"6a-9a and 2p-9p Tuesday through Friday"
→ Correct split shifts Tuesday-Friday
→ Monday correctly shows OFF
→ Syncs to family calendar
→ Coverage gaps detected
```

**This is why we build agents, not workflows.**
