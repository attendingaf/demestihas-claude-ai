# EMERGENCY HANDOFF: System Rollback
**Thread**: Emergency Response #041
**Type**: CRITICAL SYSTEM FAILURE RESPONSE  
**Priority**: 🚨 IMMEDIATE - Family blocked from core functionality
**Executor**: Claude Code (Direct VPS Access Required)

## CRITICAL SITUATION
- **Failure**: Calendar routing fix broke task routing - core bot functionality down
- **Evidence**: "show my tasks" → "Failed to query tasks: 400" 
- **Impact**: Family cannot create, view, or manage tasks
- **Timeline**: Occurred after Thread #040 deployment (2 hours ago)

## ATOMIC SCOPE
**ONE DELIVERABLE**: Restore task routing functionality by rolling back yanay.py to last known working state

## CONTEXT
- **Last Working State**: Thread #028 (before calendar routing changes)
- **Broken Deployment**: Thread #039-040 calendar routing fix
- **VPS Location**: /root/demestihas-ai/yanay.py
- **Container**: demestihas-yanay (currently running but broken)

## IMPLEMENTATION STEPS

### Step 1: Emergency Assessment (5 min)
```bash
ssh root@178.156.170.161
cd /root/demestihas-ai
# Backup broken state for analysis
cp yanay.py yanay_broken_after_calendar_fix.py
# Check container logs
docker logs demestihas-yanay --tail 50 > emergency_failure_logs.txt
```

### Step 2: Identify Rollback Point (5 min)
```bash
# Find last known working commit/version
git log --oneline | head -10
# Target: State before Thread #039 calendar routing changes
# Working state: Task routing functional, calendar may return 400
```

### Step 3: Emergency Rollback (10 min)
```bash
# Option A: Git rollback (if commits available)
git checkout [commit_before_calendar_fix] -- yanay.py

# Option B: Manual restoration
# Remove/comment out calendar routing logic that broke task routing
# Ensure intent classification properly routes to Lyco API
```

### Step 4: Container Rebuild & Deploy (5 min)
```bash
docker-compose down yanay
docker-compose build yanay --no-cache
docker-compose up -d yanay
# Verify container running
docker ps | grep yanay
```

### Step 5: Emergency Validation (5 min)
**Critical Tests via @LycurgusBot**:
1. "show my tasks" → MUST return task list (not 400 error)
2. "create task test emergency" → MUST create task successfully
3. "what on calendar" → Can return 400 (acceptable temporarily)

## SUCCESS CRITERIA
- ✅ Task routing restored: "show my tasks" works
- ✅ Task creation works: Can create new tasks
- ✅ Response time maintained: <3 seconds
- ⚠️ Calendar queries can return 400 errors temporarily

## ROLLBACK PLAN
If rollback fails:
1. Try alternative git commit
2. Manual yanay.py restoration from Thread #028 backup
3. Full container restart if necessary
4. Escalate to PM if >30 minutes

## FAMILY COMMUNICATION
After successful rollback:
"System restored - task management working. Calendar features temporarily unavailable while we fix the integration safely."

## POST-ROLLBACK ANALYSIS
1. **Root Cause**: Examine yanay_broken_after_calendar_fix.py to understand what broke task routing
2. **Better Approach**: Design calendar routing that DOES NOT interfere with task routing
3. **Testing**: Validate BOTH calendar AND task functionality before any future deployment

## REPORTING
Update current_state.md:
- Change status from "EMERGENCY" to "RESTORED - Task routing working"
- Add "Calendar routing fix delayed pending proper implementation"
- Log incident in thread_log.md

**CRITICAL SUCCESS METRIC**: Family can use bot for task management within 30 minutes