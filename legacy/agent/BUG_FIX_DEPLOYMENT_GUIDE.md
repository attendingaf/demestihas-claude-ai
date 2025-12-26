# Bug Fix Deployment Guide: General Agent Knowledge Retrieval

**Date:** October 2, 2025  
**Bug ID:** CRITICAL - General Agent Knowledge Blindness  
**Status:** ✅ FIXED - Ready for Deployment

---

## Executive Summary

### Problem
The general agent claimed it didn't know anything about users despite having persistent knowledge available in FalkorDB. This was caused by:
1. **Agent Logic Flaw**: The general agent used a pure conversational LLM without tool access
2. **Data Contamination**: Stale test data (incorrect dates) persisted in FalkorDB

### Solution
1. **Implemented Tool-First Approach**: General agent now uses ReAct pattern with knowledge retrieval tools
2. **Created Cleanup Scripts**: Utilities to purge contaminated data from FalkorDB and Mem0

---

## Files Modified/Created

### New Files
1. `/root/agent/knowledge_tools.py` - Knowledge retrieval tool wrappers
2. `/root/agent/cleanup_db.py` - FalkorDB data purge utility
3. `/root/agent/cleanup_mem0.py` - Mem0 semantic memory purge utility
4. `/root/agent/BUG_FIX_DEPLOYMENT_GUIDE.md` - This guide

### Modified Files
1. `/root/agent/main.py` - Refactored `general_agent_logic()` with tool support

---

## Deployment Steps

### Step 1: Backup Current State

```bash
# Backup current agent code
cp /root/agent/main.py /root/agent/main.py.backup.$(date +%Y%m%d)

# Backup FalkorDB data (optional, if export available)
docker exec graph_db redis-cli SAVE
```

### Step 2: Clean Contaminated Data

#### Option A: Clean Specific Pattern (Recommended)

```bash
cd /root/agent

# Preview what will be deleted
python cleanup_db.py --pattern "February 5, 2025" --dry-run

# Execute deletion (requires confirmation)
python cleanup_db.py --pattern "February 5, 2025"
```

#### Option B: Clean Specific User

```bash
# If you know the test user ID
python cleanup_db.py --user "test_user_123" --dry-run
python cleanup_db.py --user "test_user_123"
```

#### Clean Mem0 Cache

```bash
# Clean semantic memory for the test user
python cleanup_mem0.py --user "default_user" --dry-run
python cleanup_mem0.py --user "default_user"
```

### Step 3: Deploy Updated Code

The code has already been modified in place. Restart the agent service to load changes:

```bash
cd /root
docker-compose restart agent
```

Wait for the service to be healthy:

```bash
# Watch logs for successful startup
docker logs -f demestihas-agent --tail 50

# Look for:
# ✅ FalkorDB Manager initialized successfully
# ✅ Arcade Client initialized successfully (or fallback mode)
```

### Step 4: Verify the Fix

#### Test 1: Knowledge Retrieval Query

```bash
# Use the Streamlit UI or curl to test
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "message": "Tell me three random things you know about me",
    "user_id": "default_user"
  }'
```

**Expected Behavior:**
- Agent should call `get_user_knowledge` tool
- Should return actual knowledge triples from FalkorDB
- Should NOT say "I don't know anything about you"

#### Test 2: Tool Call Logging

Check logs for tool execution:

```bash
docker logs demestihas-agent --tail 100 | grep "🛠️"
```

Expected log output:
```
🛠️  General agent requesting 1 tool call(s)
Executing tool: get_user_knowledge with args: {'user_id': 'default_user', 'limit': 3}
✅ Retrieved 3 knowledge facts for user default_user
✅ General agent (tool-augmented): Here's what I know about you...
```

#### Test 3: Conversational Fallback

Test that normal conversation still works:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "message": "What is the meaning of life?",
    "user_id": "default_user"
  }'
```

**Expected Behavior:**
- Agent should NOT call tools (philosophical question doesn't need knowledge graph)
- Should return thoughtful conversational response
- Log should show: "General agent (conversational)"

---

## Technical Details

### Tool-First Architecture

The refactored `general_agent_logic()` now follows this flow:

```
1. User Query → General Agent
2. LLM Call #1 with tool binding (tools: GENERAL_AGENT_TOOLS)
3. LLM decides if tools needed:
   
   a. If tool call requested:
      → Execute get_user_knowledge(user_id, limit)
      → Query FalkorDB via falkordb_manager
      → Format results
      → LLM Call #2 with tool results
      → Return conversational response with facts
   
   b. If no tool call:
      → Return conversational response directly
```

### Available Tools

#### 1. `get_user_knowledge`
- **Purpose**: Retrieve knowledge triples about the user
- **Arguments**: `user_id` (required), `limit` (optional, default 10)
- **Queries**: `falkordb_manager.get_user_knowledge_triples()`
- **Returns**: Formatted list of knowledge statements

#### 2. `search_knowledge_entities`
- **Purpose**: Search entities by keyword
- **Arguments**: `keyword` (required), `limit` (optional, default 5)
- **Queries**: `falkordb_manager.search_entities_by_keyword()`
- **Returns**: List of matching entities with relationships

### System Prompt Changes

**OLD (BROKEN):**
```
## CONSTRAINTS
- Do NOT generate tool calls or function invocations
- Do focus on genuine dialogue
```

**NEW (FIXED):**
```
## TOOL-FIRST MANDATE
**WHEN THE USER ASKS ABOUT STORED KNOWLEDGE**, you MUST use the available tools:
- If the user asks "What do you know about me?" → MUST CALL get_user_knowledge
**DO NOT** claim you don't know anything without checking the knowledge graph first.
```

---

## Cleanup Script Usage

### FalkorDB Cleanup (`cleanup_db.py`)

#### Usage Patterns

```bash
# Preview deletion (safe)
python cleanup_db.py --pattern "bad_data" --dry-run

# Delete by pattern
python cleanup_db.py --pattern "February 5, 2025"

# Delete user data
python cleanup_db.py --user "test_user_123"

# DANGER: Delete everything (requires "DELETE ALL DATA" confirmation)
python cleanup_db.py --all
```

#### What It Does

1. Connects to FalkorDB at `graph_db:6379`
2. Searches for nodes matching criteria
3. Shows preview of what will be deleted
4. Requires explicit "DELETE" confirmation
5. Executes `DETACH DELETE` Cypher query
6. Reports nodes and relationships deleted

### Mem0 Cleanup (`cleanup_mem0.py`)

#### Usage Patterns

```bash
# Preview deletion
python cleanup_mem0.py --user "default_user" --dry-run

# Delete user memories
python cleanup_mem0.py --user "default_user"

# Use direct Qdrant access (if Mem0 API doesn't support deletion)
python cleanup_mem0.py --user "default_user" --direct-qdrant

# DANGER: Delete all memories
python cleanup_mem0.py --all
```

#### What It Does

1. Connects to Mem0 service at `http://mem0:8080`
2. Retrieves current memories to show what will be deleted
3. Requires explicit "DELETE" confirmation
4. Calls Mem0 API to delete memories
5. Falls back to direct Qdrant access if needed

---

## Rollback Plan

If the fix causes issues, rollback with:

```bash
# Restore original code
cp /root/agent/main.py.backup.YYYYMMDD /root/agent/main.py

# Restart service
docker-compose restart agent

# Verify rollback
docker logs demestihas-agent --tail 20
```

---

## Testing Checklist

### Pre-Deployment Tests ✅

- [x] Code compiles without syntax errors
- [x] knowledge_tools.py imports successfully
- [x] FalkorDBManager methods exist and are callable
- [x] Tool definitions are valid OpenAI function format
- [x] Cleanup scripts have proper error handling

### Post-Deployment Tests

- [ ] Agent service starts successfully
- [ ] Health check endpoint returns 200
- [ ] Query "What do you know about me?" triggers tool call
- [ ] Tool call successfully queries FalkorDB
- [ ] Tool results are formatted correctly
- [ ] Agent returns actual knowledge (not "I don't know")
- [ ] Normal conversation still works (no tools called)
- [ ] Shadow mode logging still active
- [ ] No increase in error rates

### Data Integrity Tests

- [ ] Stale date "February 5, 2025" removed from FalkorDB
- [ ] Valid user data still intact after cleanup
- [ ] Mem0 semantic memory cleared for test users
- [ ] New knowledge writes still work correctly
- [ ] No orphaned relationships in graph

---

## Monitoring

### Key Metrics to Watch

1. **Tool Call Rate**: Should increase for knowledge queries
2. **FalkorDB Query Latency**: Should remain <100ms
3. **Error Rate**: Should not increase
4. **User Satisfaction**: Test with "What do you know about me?" queries

### Log Patterns to Monitor

**Success:**
```
🛠️  General agent requesting 1 tool call(s)
Executing tool: get_user_knowledge
✅ Retrieved N knowledge facts for user USER_ID
✅ General agent (tool-augmented): Here's what I know...
```

**Failure:**
```
❌ Tool execution failed: [ERROR MESSAGE]
❌ FalkorDB not connected - cannot retrieve knowledge
```

### Grafana Queries (if available)

```promql
# Tool call rate
rate(agent_tool_calls_total{tool="get_user_knowledge"}[5m])

# FalkorDB query latency
histogram_quantile(0.95, rate(falkordb_query_duration_seconds_bucket[5m]))

# Error rate
rate(agent_errors_total{agent="general"}[5m])
```

---

## Known Issues and Limitations

### Issue 1: Tool Call Overhead

**Symptom**: Responses are slightly slower for knowledge queries  
**Cause**: Two LLM calls (tool decision + final response)  
**Impact**: +1-2 seconds latency  
**Mitigation**: Acceptable tradeoff for correctness

### Issue 2: Mem0 API Limitations

**Symptom**: `cleanup_mem0.py` may fail with "action not supported"  
**Cause**: Mem0 service may not expose delete_all endpoint  
**Workaround**: Use `--direct-qdrant` flag to bypass Mem0 service

### Issue 3: FalkorDB Connection Race

**Symptom**: First tool call fails with "not connected"  
**Cause**: Lazy connection initialization  
**Mitigation**: FalkorDBManager auto-connects on first query

---

## Success Criteria

The fix is considered successful when:

1. ✅ Query "Tell me three things you know about me" returns actual knowledge
2. ✅ Logs show tool calls being executed for knowledge queries
3. ✅ Normal conversation works without unnecessary tool calls
4. ✅ No stale data (February 5, 2025) found in FalkorDB
5. ✅ Error rates remain stable or decrease
6. ✅ User satisfaction with knowledge retrieval improves

---

## Contact and Support

**Developer**: AI Agent Development Team  
**Date Deployed**: October 2, 2025  
**Deployment Status**: ✅ Ready for Production

**Related Documentation**:
- Phase 3 Implementation Summary: `/root/PHASE_3_IMPLEMENTATION_SUMMARY.md`
- FalkorDB Manager: `/root/agent/falkordb_manager.py`
- Test Suite: `/root/agent/test_falkordb_reads.py`

---

## Quick Reference Commands

```bash
# Deploy
docker-compose restart agent

# Clean FalkorDB
python /root/agent/cleanup_db.py --pattern "February 5, 2025"

# Clean Mem0
python /root/agent/cleanup_mem0.py --user "default_user"

# Test
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"message": "What do you know about me?", "user_id": "default_user"}'

# Monitor
docker logs -f demestihas-agent | grep -E "(🛠️|✅|❌)"

# Rollback
cp /root/agent/main.py.backup.* /root/agent/main.py
docker-compose restart agent
```

---

**END OF DEPLOYMENT GUIDE**
