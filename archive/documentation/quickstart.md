# QUICKSTART - Demestihas.ai Quick Reference

## 🚀 Start Every Session Here

### Step 1: Load Context (30 seconds)
```bash
# Read these files FIRST - always
~/projects/demestihas-ai/current_state.md   # System status
~/projects/demestihas-ai/thread_log.md      # Recent work
~/projects/demestihas-ai/architecture.md    # System design
```

### Step 2: Check Production Health
```bash
# Quick health check - run from terminal
ssh root@178.156.170.161 "cd /root/lyco-ai && docker ps && docker logs 544c72011b31 --tail=10"

# If bot not responding, restart:
ssh root@178.156.170.161 "cd /root/lyco-ai && docker restart 544c72011b31"
```

### Step 3: Test Bot Response
```bash
# Send test message via Telegram
# Open Telegram → @LycurgusBot → Send "test"
# Should respond within 3 seconds
```

## 📋 Quick Command Reference

### VPS Operations
```bash
# SSH to server
ssh root@178.156.170.161

# Navigate to project
cd /root/lyco-ai

# View logs
docker logs 544c72011b31 --tail=50  # Last 50 lines
docker logs 544c72011b31 -f          # Follow live

# Restart services
docker-compose restart                # Restart all
docker restart 544c72011b31          # Restart bot only

# Check resource usage
docker stats --no-stream
```

### Local File Operations
```bash
# View project structure
ls -la ~/projects/demestihas-ai/

# Read current state
cat ~/projects/demestihas-ai/current_state.md

# Check recent threads
tail -30 ~/projects/demestihas-ai/thread_log.md

# View pending handoffs
ls ~/projects/demestihas-ai/handoffs/
```

### Testing Commands
```bash
# Test Anthropic connection
curl -X POST https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-3-haiku-20240307","messages":[{"role":"user","content":"Say test"}],"max_tokens":10}'

# Test Notion connection
curl -X GET https://api.notion.com/v1/databases/245413ec-f376-80f6-ac4b-c0e3bdd449c6 \
  -H "Authorization: Bearer $NOTION_TOKEN" \
  -H "Notion-Version: 2022-06-28"
```

## 🎯 Current Focus Areas

### Week 1 Priorities
1. ✅ Split architecture (Yanay + Lyco)
2. ⬜ Add conversation memory
3. ⬜ Test with family
4. ⬜ Fix health check

### Known Issues
- Bot shows "unhealthy" but works (cosmetic)
- No conversation memory (can't handle "that" references)
- Task extraction ~60% accurate (needs context)

### Quick Fixes

**Bot Not Responding:**
```bash
ssh root@178.156.170.161
cd /root/lyco-ai
docker-compose down
docker-compose up -d
```

**High Memory Usage:**
```bash
docker restart 544c72011b31
docker system prune -f  # Clean up
```

**Errors in Logs:**
```bash
# Check error patterns
docker logs 544c72011b31 2>&1 | grep ERROR | tail -20

# Check specific timeframe
docker logs 544c72011b31 --since="1h" 2>&1 | grep ERROR
```

## 📊 Key Metrics

### Check Performance
```bash
# Response time
time curl -s https://api.telegram.org/bot8324228035:AAHMqEelCy7HhIpXqnK1dWs24lqWcdq6LN4/getMe

# Memory usage
docker stats --no-stream 544c72011b31

# Task creation rate (last hour)
docker logs 544c72011b31 --since="1h" 2>&1 | grep -c "Created task"

# Error rate (last hour)
docker logs 544c72011b31 --since="1h" 2>&1 | grep -c ERROR
```

### Success Targets
- Response time: <3 seconds ✅
- Memory usage: <500MB ✅
- Error rate: <5% ⚠️
- Task accuracy: >85% ❌

## 🔄 Standard Workflows

### Adding New Feature
1. Read current_state.md
2. Design in architecture.md
3. Create handoff in handoffs/
4. Update thread_log.md
5. Test in isolation
6. Deploy side-by-side
7. Update current_state.md

### Debugging Issue
1. Check logs for errors
2. Identify component (Yanay/Lyco/Redis)
3. Test component in isolation
4. Fix and test locally
5. Deploy with monitoring
6. Document in thread_log.md

### Family Rollout
1. Test with Mene only
2. Add Viola for feedback
3. Include Cindy
4. Kid-safe testing
5. Full family launch

## 🚨 Emergency Procedures

### Bot Completely Down
```bash
# Full restart
ssh root@178.156.170.161
cd /root/lyco-ai
docker-compose down -v
docker-compose up -d --build
docker logs -f lyco-ai-bot-1
```

### Rollback to Previous Version
```bash
ssh root@178.156.170.161
cd /root/lyco-ai
git log --oneline -5
git checkout [LAST_WORKING_COMMIT]
docker-compose up -d --build
```

### API Cost Spike
1. Check Anthropic dashboard
2. Review logs for loop/retry issues
3. Implement rate limiting
4. Switch to Haiku from Sonnet

## 📝 File Update Protocol

### After Every Session
```python
# 1. Update current state
edit_file("~/projects/demestihas-ai/current_state.md", changes)

# 2. Append to thread log
append_to_file("~/projects/demestihas-ai/thread_log.md", new_entry)

# 3. Create handoff if needed
write_file("~/projects/demestihas-ai/handoffs/XXX_task.md", handoff)
```

## 🔗 Quick Links

### Production
- Server: `178.156.170.161`
- Bot: @LycurgusBot on Telegram
- Notion: [Workspace](https://www.notion.so/Lyco-ai-252413ecf37680acbbf7ecfd3d1693d1)

### Documentation
- Architecture: `~/projects/demestihas-ai/architecture.md`
- Family Context: `~/projects/demestihas-ai/family_context.md`
- Current State: `~/projects/demestihas-ai/current_state.md`

### Credentials (in .env on server)
- TELEGRAM_BOT_TOKEN
- ANTHROPIC_API_KEY
- NOTION_TOKEN
- NOTION_DATABASE_ID

## 💡 Pro Tips

1. **Always start by reading current_state.md**
2. **Test in isolation before deploying**
3. **Keep changes under 2 hours**
4. **Document everything in thread_log.md**
5. **When in doubt, ask the family**

---

**Remember:** This system is for a real family. Every change affects real people. Test thoroughly, fail gracefully, document completely.