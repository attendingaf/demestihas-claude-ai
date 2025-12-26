# 🚨 EMERGENCY ROLLBACK PLAN
**Date**: August 28, 2025, 00:40 UTC
**Trigger**: Calendar fix broke task routing - family cannot use core bot functionality
**Priority**: IMMEDIATE ACTION REQUIRED

## Current Broken State
- **Tasks**: "show my tasks" → "Failed to query tasks: 400" ❌
- **Calendar**: "what on my calendar" → Placeholder response ✅
- **Family Impact**: Cannot create, view, or manage tasks (core functionality)

## Rollback Target
- **Restore**: Thread #028 state (before calendar routing changes)
- **Container**: Last known working yanay.py configuration
- **Evidence**: Task routing was working before Thread #039-040 deployment

## Emergency Rollback Steps

### Step 1: VPS Access & Container Status
```bash
ssh root@178.156.170.161
cd /root/demestihas-ai
docker ps | grep yanay
# Target: demestihas-yanay container
```

### Step 2: Backup Current (Broken) State
```bash
# Preserve broken state for analysis
cp yanay.py yanay_broken_calendar_fix.py
docker logs demestihas-yanay > logs/failure_after_calendar_fix.log
```

### Step 3: Emergency Rollback to Working yanay.py
```bash
# Option A: Restore from git (if available)
git log --oneline | head -10
git checkout [commit_before_calendar_fix] -- yanay.py

# Option B: Manual rollback of calendar routing changes
# Remove contains_calendar_intent() method additions
# Restore original intent classification logic
```

### Step 4: Rebuild & Deploy Container
```bash
docker-compose down yanay
docker-compose build yanay
docker-compose up -d yanay
```

### Step 5: Emergency Validation
```bash
# Test via @LycurgusBot immediately:
# 1. "show my tasks" → Should work (not 400 error)
# 2. "create task buy milk" → Should create task successfully
# 3. "what on calendar" → Can return 400 (acceptable for rollback)
```

## Success Criteria for Rollback
- ✅ Task creation and management restored
- ✅ "show my tasks" returns task list (not 400 error) 
- ✅ System response time <3 seconds
- ⚠️ Calendar queries may return 400 errors (temporary acceptable)

## Post-Rollback Actions
1. **Family Communication**: Notify system restored, calendar features temporarily unavailable
2. **Root Cause Analysis**: Examine yanay_broken_calendar_fix.py to understand what broke task routing
3. **Careful Re-implementation**: Fix calendar routing WITHOUT breaking task routing
4. **Better Testing**: Validate BOTH calendar AND task functionality before deployment

## Escalation Criteria
- If rollback fails within 30 minutes → STOP ALL CHANGES
- If task functionality cannot be restored → Restore from earlier backup
- If system becomes completely unresponsive → Container restart required

---
**FAMILY SAFETY FIRST**: Restore working task management before attempting calendar fixes
