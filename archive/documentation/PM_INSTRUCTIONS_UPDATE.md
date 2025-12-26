# PM Instructions Update: Executor Clarity Requirements

**Effective Date:** August 26, 2025  
**Thread:** PM Update #001

## MANDATORY: Executor Designation Protocol

Every handoff, instruction, and next step MUST explicitly identify WHO executes the action.

### Executor Types

**[USER]** = Mene directly at terminal/SSH
- SSH commands
- Docker operations
- System administration
- Direct testing

**[CLAUDE DESKTOP - PM (Opus)]** = Strategic/Architecture
- System design decisions
- Handoff creation
- Architecture updates
- Strategic analysis

**[CLAUDE DESKTOP - Dev (Sonnet)]** = Implementation
- Code writing from handoffs
- Configuration updates
- Bug fixes
- Feature implementation

**[CLAUDE DESKTOP - QA (Claude)]** = Validation
- Testing protocols
- Family safety checks
- Performance validation
- Deployment approval

**[CLAUDE CODE]** = Complex Multi-File Operations
- Large refactoring (>3 files)
- System-wide changes
- Architecture migrations
- Complex debugging

### Format Requirements

#### In Handoffs:
```
NEXT STEP: [EXECUTOR] → Action description
Example: [USER] → SSH to VPS and run docker stop command
Example: [CLAUDE DESKTOP - Dev (Sonnet)] → Implement handoff #026
```

#### In Thread Logs:
```
**Next Thread**: [EXECUTOR] executes [specific action]
Example: [CLAUDE CODE] executes Yanay/Lyco split
Example: [USER] tests conversation memory with family
```

#### In Decision Points:
```
Option A: [USER] stops legacy bot via SSH
Option B: [CLAUDE DESKTOP - PM (Opus)] creates new bot token strategy
```

### Examples of Clear Instructions

✅ GOOD:
- "[USER] → SSH to 178.156.170.161 and run: docker stop lyco-telegram-bot"
- "[CLAUDE DESKTOP - Dev (Sonnet)] → Read handoff #027 and implement Redis optimization"
- "[CLAUDE CODE] → Execute complete directory restructure from handoff #028"

❌ BAD:
- "Stop the legacy bot" (Who?)
- "Next, implement the changes" (Who? What tool?)
- "Test the system" (Who? How?)

### Multi-Step Sequences

For complex operations, number steps with executor:

1. **[USER]** → SSH to VPS
2. **[USER]** → Run: `docker stop lyco-telegram-bot`
3. **[USER]** → Verify with: `docker ps`
4. **[USER]** → Test: Send "Buy milk" to bot
5. **[CLAUDE DESKTOP - PM (Opus)]** → Update current_state.md with results
6. **[USER]** → If stable, notify family in Telegram

### Handoff Chains

When work passes between executors:

```
[CLAUDE DESKTOP - PM (Opus)] creates handoff #029
    ↓
[CLAUDE DESKTOP - Dev (Sonnet)] implements handoff #029
    ↓
[CLAUDE DESKTOP - QA (Claude)] validates implementation
    ↓
[USER] deploys to production
    ↓
[CLAUDE DESKTOP - PM (Opus)] updates system state
```

---

This protocol ensures zero ambiguity about who does what, reducing cognitive load and preventing execution errors.