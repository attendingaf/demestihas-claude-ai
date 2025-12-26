# URGENT FIX: Calendar Intent Routing Issue
# QA Thread #035 - Critical Integration Bug Found

## PROBLEM IDENTIFIED
Live testing shows 2/3 calendar queries failing with "Failed to query tasks: 400"

**Working Query**: "Am I free on thursday afternoon?" → ✅ Routed to Huata correctly
**Failing Queries**: 
- "what on my calendar tomorrow?" → ❌ Routed to Lyco, returns 400 error
- "whats on my calendar today?" → ❌ Routed to Lyco, returns 400 error

## ROOT CAUSE
Intent classification in yanay.py is inconsistent - some calendar queries route to Huata, others to Lyco.

## REQUIRED FIXES

### 1. Debug Intent Routing Logic
```bash
ssh root@178.156.170.161
cd /root/demestihas-ai

# Check current intent routing logic
grep -A 10 -B 5 "contains_calendar_intent" yanay.py

# Check for any competing routing logic
grep -A 5 -B 5 "calendar" yanay.py
```

### 2. Fix Calendar Keyword Detection
The `contains_calendar_intent()` method may need expansion:

```python
def contains_calendar_intent(self, message):
    calendar_keywords = [
        'free', 'available', 'busy', 'schedule', 'calendar', 'meeting',
        'appointment', 'today', 'tomorrow', 'thursday', 'afternoon',
        'morning', 'evening', 'next week', 'time', 'when', 'what time',
        # ADD THESE MISSING KEYWORDS:
        'what on my calendar', 'whats on my calendar', 'my calendar',
        'calendar today', 'calendar tomorrow', 'events today', 'events tomorrow'
    ]
```

### 3. Fix Error Message Quality
Replace technical "400" errors with family-friendly messages:

```python
except Exception as e:
    if "400" in str(e) or "query tasks" in str(e):
        error_msg = "I'm having trouble checking your calendar right now. Could you try asking in a different way? 📅"
    else:
        error_msg = "I had trouble with that calendar request. Could you try rephrasing it? 📅"
```

### 4. Test All Calendar Query Patterns
```bash
# Test queries that should ALL route to Huata:
- "Am I free today?"
- "What's on my calendar today?"  
- "What's on my calendar tomorrow?"
- "What events do I have today?"
- "Show me today's schedule"
- "Am I busy this afternoon?"
```

## DEPLOYMENT BLOCKER
This integration bug must be fixed before family rollout.

**Impact**: Family will get confusing technical errors for basic calendar questions.

**Fix Timeline**: 15-30 minutes to debug and patch intent routing.

## QA RE-TEST REQUIRED
After fix is applied:
1. Test all calendar query variations 
2. Verify consistent routing to Huata
3. Confirm family-friendly error messages
4. Validate 95%+ calendar query success rate

---
**QA Status**: BLOCKED until integration routing fixed
**Family Rollout**: DELAYED until fix validated
