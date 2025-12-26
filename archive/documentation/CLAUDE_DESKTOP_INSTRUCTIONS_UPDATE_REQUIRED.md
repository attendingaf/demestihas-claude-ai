# CRITICAL: Claude Desktop Instructions Update Required

**Date:** September 1, 2025  
**Issue:** Architecture discovery reveals multi-agent container system, not single bot  
**Impact:** Current instructions assume wrong deployment patterns  

## Architecture Discovery Summary

**Previous Understanding (WRONG):**
- Single bot.py process management
- Direct Python execution deployment  
- Health check endpoint additions
- Simple file modifications and restarts

**Actual Reality (DISCOVERED):**
- Containerized multi-agent system with docker-compose.yml
- Yanay.ai orchestration layer routing messages
- Specialized agents: Nina (scheduler), Huata (calendar), Lyco (project manager)
- Container management deployment patterns

## Documentation Status After Updates

### ✅ CORRECTED - Major Files
- **SYSTEM_CONFIG.md** → Rewritten for multi-agent container architecture
- **CURRENT_STATE.md** → Rewritten showing Yanay/Nina/Huata/Lyco agents  
- **THREAD_LOG.md** → Updated with architecture discovery documentation

### ⚠️ NEEDS REVIEW - Claude Desktop Instructions

**Current Instructions Likely Wrong For:**
1. **Deployment Commands** 
   - May show single bot restart patterns
   - Should show `docker-compose up -d [service]` patterns
   - Container management vs. direct Python process

2. **File Path Assumptions**
   - May reference `/root/lyco-ai/` (not found on VPS)
   - Should reference `/root/demestihas-ai/` (actual location)
   - May assume direct bot.py modification vs. agent files

3. **Service Management**
   - May show direct Python process handling
   - Should show container orchestration patterns
   - May miss Yanay.ai orchestration layer importance

4. **Troubleshooting Patterns**
   - May focus on single bot debugging
   - Should focus on container logs and agent routing
   - May miss orchestration layer failure diagnosis

### ⚠️ NEEDS REVIEW - Handoff Documents

**Files Requiring Multi-Agent Review:**
- `~/handoffs/005_langchain_base_agent.md` → Assumes `/root/lyco-ai/` paths
- `~/handoffs/006_notion_langchain_integration.md` → May assume single bot integration
- `~/handoffs/QA_004_health_check.md` → Assumes direct bot health endpoint

**Common Issues in Handoffs:**
- Wrong file paths (lyco-ai vs. demestihas-ai)  
- Single bot deployment assumptions
- Direct Python process management
- Missing container orchestration context

## Recommended Claude Desktop Instruction Updates

### Add Container Management Section
```markdown
## Multi-Agent Container Management

### System Architecture
The Demestihas AI system uses containerized multi-agent architecture:
- Yanay.ai: Orchestration layer (routes messages to agents)
- Nina: Scheduling agent  
- Huata: Calendar agent
- Lyco: Project management agent
- Hermes: Audio processing (running)

### Container Operations
```bash
# Check system status
docker ps -a
docker-compose ps

# Restart orchestration (most common fix)
docker-compose up -d yanay

# Restart Telegram interface
docker-compose up -d lyco-telegram-bot

# View agent logs
docker logs demestihas-yanay
docker logs lyco-telegram-bot
```

### Deployment Patterns
```bash
# Navigate to project
cd /root/demestihas-ai

# Deploy configuration changes
docker-compose up -d --build

# Agent-specific updates
# Edit agent files: yanay.py, nina.py, huata.py, lyco_api.py
# Then: docker-compose restart [service]
```
```

### Update File Path References
```markdown
### Correct File Paths
- VPS Project Directory: `/root/demestihas-ai/` (NOT /root/lyco-ai/)
- Agent Files: yanay.py, nina.py, huata.py, lyco_api.py
- Configuration: docker-compose.yml, .env
- Legacy Files: bot_*.py (various single bot implementations)
```

### Add Troubleshooting Section
```markdown
### Multi-Agent Troubleshooting

#### Family Bot Not Responding
1. Check Yanay.ai orchestration: `docker ps | grep yanay`
2. If exited: `docker-compose up -d yanay`  
3. Check Telegram interface: `docker ps | grep telegram`
4. If exited: `docker-compose up -d lyco-telegram-bot`
5. Test message routing through @LycurgusBot

#### Agent-Specific Issues
- Nina scheduling problems: `docker logs demestihas-yanay | grep nina`
- Calendar integration issues: Check huata.py, calendar_tools.py
- Project management problems: Check lyco_api.py, Notion integration
```

## Required Action Items

### 1. Review Current Claude Desktop Instructions
- Check for single bot assumptions
- Update file paths from lyco-ai to demestihas-ai  
- Add container management commands
- Update troubleshooting for multi-agent system

### 2. Review All Handoff Documents  
- Update file paths in existing handoffs
- Check deployment assumptions in handoffs
- Flag handoffs that assume single bot architecture
- Create new multi-agent handoff templates

### 3. Test Updated Instructions
- Verify container management commands work
- Test multi-agent deployment patterns  
- Validate troubleshooting procedures
- Ensure paths match VPS reality

## Priority Assessment

**HIGH PRIORITY:**
- Claude Desktop instruction file path corrections
- Container management command additions  
- Multi-agent troubleshooting procedures

**MEDIUM PRIORITY:**  
- Handoff document path corrections
- Single bot assumption reviews
- Agent-specific deployment patterns

**LOW PRIORITY:**
- Legacy handoff document updates (unless actively used)
- Historical thread documentation corrections
- Non-critical file reference updates

## Testing Plan

After Claude Desktop instruction updates:
1. Test multi-agent system recovery procedures
2. Verify container management commands  
3. Validate agent-specific troubleshooting
4. Test deployment patterns with docker-compose
5. Ensure family bot response through orchestration layer

---

**Bottom Line:** The sophisticated multi-agent system requires completely different deployment and management patterns than single bot architecture. Claude Desktop instructions must be updated before any system recovery attempts.

