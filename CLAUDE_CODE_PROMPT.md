# Claude Code Prompt: Lyco Integration Enhancement & Bridge Fix

Copy and paste this entire message into Claude Code:

---

## Task: Fix EA-AI Bridge and Enhance Lyco Integration

I need you to implement 4 critical improvements to the Demestihas AI system. The full specification is in `/Users/menedemestihas/Projects/demestihas-ai/REQUIREMENTS.md`.

### Priority Order:
1. **FIRST**: Fix the EA-AI Bridge health check failures (port 8081)
2. **SECOND**: Implement Redis caching for Lyco v2
3. **THIRD**: Expand Lyco operations in Bootstrap.js
4. **FOURTH**: Create a dedicated Lyco MCP server

### Context:
- System has 7 Docker containers, 5 are healthy, 2 are failing (EA-AI Bridge and Status Dashboard)
- Redis is already running and healthy at port 6379
- Lyco v2 is operational at port 8000 but needs performance optimization
- The EA-AI Bridge failure is blocking multi-agent coordination

### Key Files to Check First:
- `/Users/menedemestihas/Projects/demestihas-ai/ea-ai-container/server.js` (Bridge issue)
- `/Users/menedemestihas/Projects/demestihas-ai/docker-compose.yml` (Container config)
- `/Users/menedemestihas/Projects/demestihas-ai/agents/lyco/lyco-v2/server.py` (Lyco server)
- `/Users/menedemestihas/Projects/demestihas-ai/bootstrap.js` (Router logic)

### Start with Diagnostics:
```bash
# Check what's wrong with the bridge
docker logs demestihas-ea-ai-bridge --tail 100

# Test the health endpoint
curl -v http://localhost:8081/health

# Check if the process is actually listening
docker exec demestihas-ea-ai-bridge netstat -tulpn
```

### Implementation Approach:

#### Part 1: Fix EA-AI Bridge
The health check is failing but the container is running. The issue is likely:
- Express app not listening before health check runs
- Async initialization blocking the health endpoint
- Port binding issue inside the container

Fix the `/health` endpoint to respond immediately, even during initialization.

#### Part 2: Add Redis Caching to Lyco
- Lyco already has Redis connection configured
- Cache the next 5 tasks to reduce database queries
- Invalidate cache on task completion/skip
- Add cache metrics to the health endpoint

#### Part 3: Expand Bootstrap.js
Add these Lyco operations to the handleTaskOperation function:
- signal_capture
- process_signals
- get_patterns
- weekly_review
- update_energy
- get_delegation_signals
- rounds_summary

#### Part 4: Create Lyco MCP Server
Create a new MCP server at `/Users/menedemestihas/Projects/demestihas-ai/agents/lyco/mcp-server/` that provides direct Claude Desktop integration for Lyco, bypassing the EA-AI bridge for lower latency.

### Testing:
After each fix, run the test commands from REQUIREMENTS.md to verify the implementation.

### Update Documentation:
After successful implementation, update:
- `/Users/menedemestihas/Projects/demestihas-ai/SYSTEM_STATE.md`
- Mark completed items in ROADMAP.md

### Success Criteria:
- All 7 containers show as healthy
- `curl http://localhost:8081/health` returns 200 OK
- Lyco operations work through both EA-AI tools and direct MCP
- Response time for "next task" < 300ms

Begin with Part 1 (Bridge Fix) as it's blocking other services. Show me the diagnostic results first, then implement the fix.

---

End of Claude Code prompt. Copy everything between the horizontal lines.