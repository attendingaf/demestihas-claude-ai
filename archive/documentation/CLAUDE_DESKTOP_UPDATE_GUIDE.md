# Claude Desktop Instructions - Single Full-Stack AI Role

## What to Replace in Claude Desktop

Replace your current role instructions with the comprehensive single-agent approach:

### REPLACE All Existing Role Instructions WITH:
```
You are the Full-Stack Family AI Developer for the Demestihas family AI ecosystem. You handle strategy, implementation, and quality assurance in a single comprehensive role.

## BEFORE Starting Any Work:

1. Read System Configuration (MANDATORY - Always First):
   read_file("~/Projects/demestihas-ai/SYSTEM_CONFIG.md")

2. Check for handoff from previous thread:
   read_file("~/handoffs/[latest_handoff].md")

3. Verify current state:
   read_file("~/CURRENT_STATE.md")
   read_file("~/THREAD_LOG.md")

## Thread Management:
- When thread gets long (~40+ messages): Create handoff document
- Opus threads: Strategic planning, architecture decisions
- Sonnet threads: Implementation, coding, testing
- Always preserve context via handoff documents

[Full role details in ~/Projects/demestihas-ai/FULL_STACK_AI_ROLE.md]
```

### Key Changes from Previous Approach:
- **Single Role:** No separate PM/Dev/QA instructions - one comprehensive role
- **Manual Model Selection:** You choose Opus vs Sonnet based on task type
- **Handoff Management:** Structured context preservation across thread switches
- **Configuration-Driven:** Always reads SYSTEM_CONFIG.md for current infrastructure

## Benefits of Single Comprehensive Role

✅ **Unified Context** - All project knowledge in one conversation thread  
✅ **ADHD-Friendly** - No context switching between different agent personalities  
✅ **Thread Management** - Handoffs handle Claude's thread length limits elegantly  
✅ **Model Optimization** - You choose Opus for strategy, Sonnet for implementation  
✅ **Simpler Maintenance** - One role instruction file instead of three  
✅ **Quality Preservation** - Handoff documents maintain structured approach

## Files Created for Hybrid System

1. **FULL_STACK_AI_ROLE.md** - Comprehensive single-agent instructions
2. **SYSTEM_CONFIG.md** - Master configuration (paths, IDs, service status)  
3. **This file** - Quick update guide

## Testing the New Hybrid System

After updating Claude Desktop instructions:

1. **Test config reading:**
   ```bash
   read_file("~/Projects/demestihas-ai/SYSTEM_CONFIG.md")
   # Should show current VPS path: /root/demestihas-ai/
   ```

2. **Test handoff creation:**
   ```bash
   # When thread gets long, should create structured handoff
   create_handoff_opus_to_sonnet()
   ```

3. **Test thread continuity:**
   ```bash  
   # New thread should read handoff and continue seamlessly
   read_file("~/handoffs/latest.md")
   ```

## Thread Management Strategy

### When to Hand Off:
- **Thread Length:** ~40+ messages approaching limits  
- **Task Transition:** Strategic planning → Implementation (Opus → Sonnet)  
- **Complexity Shift:** Implementation → Strategic decisions (Sonnet → Opus)  

### Handoff Quality:
- Complete context preservation  
- Clear success criteria  
- Atomic task boundaries  
- Resource documentation  

### Model Selection Guide:
- **Opus:** Architecture, planning, complex decisions, multi-step design  
- **Sonnet:** Coding, testing, deployment, file modifications, debugging

## Current Health Check Status

With this new hybrid system:
- ✅ Single comprehensive role created
- ✅ SYSTEM_CONFIG.md contains correct VPS paths  
- ✅ Health check code uploaded to `/root/demestihas-ai/`  
- ⏳ Ready to complete health check using new configuration system

**Next Step:** Update Claude Desktop with single role instructions, then complete health check deployment using structured handoff approach.

## Example Handoff Workflow

### Scenario: Complex Feature Development

**Thread 1 (Opus - Strategic):**
1. Analyze requirements and constraints
2. Design architecture approach
3. Plan implementation phases
4. Create handoff: "Implement health check endpoint"

**Thread 2 (Sonnet - Implementation):**
1. Read handoff and configuration  
2. Code health check functionality
3. Test and validate
4. Deploy to VPS
5. Document results in thread log

**Thread 3 (Opus - Next Phase):**
1. Review implementation results
2. Plan next strategic phase
3. Continue with broader architecture

This preserves the structured quality of separate roles while maintaining context continuity and respecting thread length limits.
