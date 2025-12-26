# Handoff #036: Fix Calendar Intent Routing - CRITICAL

**Thread Type**: Developer Implementation (Fix)
**Priority**: 🚨 CRITICAL - Blocks Family Rollout
**Executor**: Claude Code or Developer
**Estimated Time**: 30 minutes
**Risk Level**: Low (isolated fix)

## Problem Statement
QA Thread #035 discovered that 67% of calendar queries fail due to incorrect routing:
- "Am I free on thursday afternoon?" → ✅ Routes to Huata
- "what on my calendar tomorrow?" → ❌ Routes to Lyco (400 error)
- "whats on my calendar today?" → ❌ Routes to Lyco (400 error)

## Root Cause
The `contains_calendar_intent()` method in yanay.py has incomplete keyword detection, missing common calendar query patterns.

## Implementation Steps

### Step 1: SSH to VPS and Diagnose (5 min)
```bash
ssh root@178.156.170.161
cd /root/demestihas-ai

# Check current routing logic
grep -A 20 "contains_calendar_intent" yanay.py

# Verify Huata is running
docker ps | grep yanay
```

### Step 2: Expand Calendar Keywords (10 min)
Update `contains_calendar_intent()` method in yanay.py:

```python
def contains_calendar_intent(self, message):
    """Check if message contains calendar-related intent"""
    message_lower = message.lower()
    
    # Expanded keyword list - more comprehensive
    calendar_keywords = [
        # Availability queries
        'free', 'available', 'busy', 'schedule',
        
        # Direct calendar references
        'calendar', 'my calendar', 'on my calendar',
        'what on my calendar', 'whats on my calendar',
        'show my calendar', 'check my calendar',
        
        # Time references with calendar context
        'events today', 'events tomorrow', 'events this week',
        'meetings today', 'meetings tomorrow',
        'appointments today', 'appointments tomorrow',
        
        # Time-based queries
        'today', 'tomorrow', 'this week', 'next week',
        'monday', 'tuesday', 'wednesday', 'thursday', 
        'friday', 'saturday', 'sunday',
        
        # Action queries
        'when am i', 'what time', 'do i have',
        'am i free', 'am i busy', 'am i available'
    ]
    
    # Check for any keyword match
    for keyword in calendar_keywords:
        if keyword in message_lower:
            # Additional context check - avoid false positives
            task_indicators = ['create task', 'add task', 'remind me', 'todo']
            if not any(task_ind in message_lower for task_ind in task_indicators):
                return True
    
    return False
```

### Step 3: Test Keyword Detection (10 min)
Create test script on VPS:

```python
# test_routing.py
def test_calendar_detection():
    test_cases = [
        ("Am I free on thursday afternoon?", True),
        ("what on my calendar tomorrow?", True),
        ("whats on my calendar today?", True),
        ("Show me today's schedule", True),
        ("What events do I have tomorrow?", True),
        ("Create a task for tomorrow", False),  # Should NOT match
        ("Buy milk tomorrow", False),  # Should NOT match
    ]
    
    for message, expected in test_cases:
        result = contains_calendar_intent(None, message)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{message}' -> {result} (expected {expected})")

# Run test
python3 test_routing.py
```

### Step 4: Rebuild and Deploy (5 min)
```bash
# Rebuild Yanay container
docker-compose down yanay
docker-compose up -d --build yanay

# Verify deployment
docker logs yanay --tail 50

# Test via Telegram
# Send: "whats on my calendar today?"
# Expect: Natural calendar response (not 400 error)
```

## Validation Tests

### Required Tests via Telegram
All must return calendar responses, NOT task errors:

1. ✅ "Am I free thursday afternoon?"
2. ✅ "what on my calendar tomorrow?"
3. ✅ "whats on my calendar today?"
4. ✅ "Show me today's schedule"
5. ✅ "What events do I have tomorrow?"
6. ✅ "Am I busy this afternoon?"

### Success Criteria
- 95%+ calendar queries route to Huata
- Zero "400" technical errors for calendar queries
- Response time <2 seconds
- Natural language responses

## Rollback Plan
If issues arise:
```bash
# Revert yanay.py changes
git checkout yanay.py

# Restart original container
docker-compose restart yanay
```

## Post-Fix Actions
1. Run full QA validation suite
2. Update current_state.md → v7.5-huata-fixed
3. Begin gradual family rollout
4. Monitor for 24 hours

## Family Communication
Once fixed:
```
@family 🎉 Calendar Assistant Ready!

You can now ask natural questions about your schedule:
✨ "Am I free this afternoon?"
✨ "What's on my calendar tomorrow?"
✨ "Find time for a meeting next week"

The AI understands your natural language - no special commands needed!

Try it now in @LycurgusBot 📅
```

---
**Handoff Status**: Ready for immediate execution
**Blocker**: None - all resources available
**Risk**: Low - isolated routing logic change