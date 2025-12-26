# Handoff #044: System Stability Validation

**Thread Type**: QA-Claude Validation
**Priority**: CRITICAL - Execute Immediately
**Duration**: 30 minutes
**Context**: Emergency rollback completed, need to verify core functionality

## Atomic Scope
Validate that core task management functionality is fully operational after emergency rollback

## Context
- Emergency rollback removed calendar routing that was breaking task queries (Thread #042)
- System reports v7.5-emergency-stable but needs verification
- Family cannot use system if tasks don't work
- Calendar features temporarily disabled (acceptable)

## Validation Requirements

### 1. Live Telegram Testing via @LycurgusBot
Execute these commands and verify responses:

```
Test Suite A: Basic Task Operations
1. "show my tasks" 
   → MUST return actual task list, NOT "Failed to query tasks: 400"
   
2. "create task buy groceries tomorrow"
   → MUST create task successfully
   
3. "make that urgent"
   → MUST update previous task using context memory
   
4. "what did I just ask you to do?"
   → MUST reference conversation memory
```

```
Test Suite B: Date Parsing
1. "create task meeting tomorrow at 2pm"
   → MUST parse "tomorrow" correctly
   
2. "add task call mom next Monday"
   → MUST parse "next Monday" correctly
   
3. "remind me to exercise in 3 days"
   → MUST calculate date correctly
```

```
Test Suite C: Performance
1. Measure response time for 10 different queries
   → MUST be <3 seconds for all
   
2. Send 5 rapid messages
   → MUST handle without errors
```

```
Test Suite D: Calendar Queries (Expected to Fail Gracefully)
1. "what's on my calendar today?"
   → DOCUMENT current behavior (likely returns task-related response or error)
   
2. "am I free Thursday afternoon?"
   → DOCUMENT current behavior for future fix
```

### 2. Container Health Verification

SSH to VPS and check:
```bash
ssh root@178.156.170.161

# Check all containers running
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Verify Yanay logs (last 50 lines)
docker logs demestihas-yanay --tail 50 | grep -E "ERROR|WARNING|Starting"

# Check Redis memory usage
docker exec lyco-redis redis-cli INFO memory | grep used_memory_human

# Verify Hermes audio system still working
docker ps | grep hermes
```

### 3. Notion Database Verification

Via Telegram:
1. Create a test task
2. Verify it appears in Notion within 10 seconds
3. Update the task 
4. Verify update reflects in Notion

## Success Criteria

**MUST PASS (Blocking)**:
- ✅ All task operations work without 400 errors
- ✅ Response time <3 seconds maintained
- ✅ Context memory ("make that urgent") works
- ✅ Date parsing for common formats works
- ✅ All containers healthy and running

**SHOULD PASS (Non-blocking)**:
- ⚠️ Calendar queries fail gracefully (not with technical errors)
- ⚠️ No concerning errors in logs
- ⚠️ Redis memory usage reasonable (<100MB)

## Documentation Required

Create validation report:
```markdown
## Stability Validation Report
**Date**: [timestamp]
**Tester**: [who]
**Duration**: [time spent]

### Test Results
- Task Operations: [PASS/FAIL] - [details]
- Date Parsing: [PASS/FAIL] - [details]
- Performance: [PASS/FAIL] - [avg response time]
- Calendar Behavior: [current behavior documented]

### Container Status
[paste docker ps output]

### Issues Found
1. [any issues with severity]

### Recommendation
[STABLE/UNSTABLE] - [reasoning]
```

## Rollback Plan
If critical issues found:
- Document exact failure
- Check Thread #042 for rollback files
- Restore yanay_BROKEN_after_calendar_fix backup if needed
- Alert PM immediately

## Next Steps
After validation:
- If STABLE → Proceed to health check implementation
- If UNSTABLE → Emergency escalation to PM for architecture review
