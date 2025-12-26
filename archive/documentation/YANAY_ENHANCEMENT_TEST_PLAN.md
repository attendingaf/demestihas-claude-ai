# Yanay.ai Enhancement Test Plan - Post API Fix
**Date:** September 1, 2025  
**Status:** API Authentication ✅ Fixed | Enhancement ✅ Integrated

## Test Environment Setup

### Container Status Check
```bash
# Verify Yanay container running with enhancements
docker ps | grep yanay
# Expected: demestihas-yanay (8cb9291cf64a) - UP

# Check enhancement initialization
docker logs demestihas-yanay | grep -E "(Conversation enhancement|evaluate_response_mode|opus_conversation)"

# Verify API keys loaded
docker exec demestihas-yanay python -c "import os; print('Anthropic:', 'ANTHROPIC_API_KEY' in os.environ); print('Notion:', 'NOTION_TOKEN' in os.environ)"
```

## Test Scenarios

### 1. Conversational Mode Test
**Trigger:** Emotional or ambiguous message  
**Test Message:** "I am frustrated with my schedule today"

**Expected Behavior:**
- `evaluate_response_mode` returns "conversational"
- Opus model engaged for empathetic response
- Token tracking in Redis (`tokens:daily:*`)
- Natural multi-turn conversation capability

**Validation:**
```bash
# Check Redis for conversation state
docker exec lyco-redis redis-cli KEYS "conv:*"
docker exec lyco-redis redis-cli KEYS "tokens:*"

# Check logs for Opus activation
docker logs demestihas-yanay | grep -i "opus"
```

### 2. Task Delegation Test
**Trigger:** Clear task request  
**Test Message:** "Add task: Review Q3 financial reports by Friday"

**Expected Behavior:**
- `evaluate_response_mode` returns "task"
- Routes to Lyco agent for Notion integration
- Task created in Master Tasks database
- Quick confirmation response

**Validation:**
```bash
# Check routing decision
docker logs demestihas-yanay | grep "Routing to Lyco"

# Verify Notion creation
curl -X GET https://api.notion.com/v1/databases/245413ec-f376-80f6-ac4b-c0e3bdd449c6/query \
  -H "Authorization: Bearer ntn_175141651103KvPHb4808UU..." \
  -H "Notion-Version: 2022-06-28"
```

### 3. Mixed Mode Test
**Trigger:** Emotional context with embedded task  
**Test Message:** "I'm overwhelmed. Can you help me organize my meetings for tomorrow?"

**Expected Behavior:**
- Initial conversational response (empathy)
- Then delegation to Nina/Huata for calendar
- Seamless mode switching

**Validation:**
```bash
# Check dual-mode activation
docker logs demestihas-yanay | tail -50 | grep -E "(conversational|task|Nina|Huata)"
```

### 4. Educational Query Test
**Trigger:** Child-like "why" question  
**Test Message:** "Why is the sky blue?"

**Expected Behavior:**
- `evaluate_response_mode` returns "conversational"
- Age-appropriate Opus response
- Educational tone without delegation

### 5. Token Budget Test
**Trigger:** Multiple conversational messages  
**Test:** Send 10 emotional messages in sequence

**Expected Behavior:**
- Token tracking accumulates
- Warning at 80% of daily budget
- Fallback to Haiku at 90%

**Validation:**
```bash
# Check token accumulation
docker exec lyco-redis redis-cli GET "tokens:daily:$(date +%Y%m%d)"

# Monitor for budget warnings
docker logs demestihas-yanay | grep -i "budget"
```

## API Call Verification

### Test Anthropic API Directly
```bash
# From inside container
docker exec demestihas-yanay python -c "
import os
from anthropic import Anthropic
client = Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
response = client.messages.create(
    model='claude-3-haiku-20240307',
    max_tokens=100,
    messages=[{'role': 'user', 'content': 'Test message'}]
)
print('API Test Success:', response.content[0].text[:50])
"
```

### Test Notion API Directly
```bash
# From inside container
docker exec demestihas-yanay python -c "
import os
import requests
headers = {
    'Authorization': f\"Bearer {os.environ['NOTION_TOKEN']}\",
    'Notion-Version': '2022-06-28'
}
response = requests.get(
    f\"https://api.notion.com/v1/databases/{os.environ['NOTION_DATABASE_ID']}\",
    headers=headers
)
print('Notion Test:', response.status_code, response.json().get('object', 'failed'))
"
```

## Integration Test Checklist

- [ ] Yanay container running with new API keys
- [ ] Redis connection established
- [ ] Telegram polling active
- [ ] Anthropic API (Haiku) responding
- [ ] Anthropic API (Opus) responding
- [ ] Notion database accessible
- [ ] evaluate_response_mode method working
- [ ] opus_conversation method working
- [ ] Token tracking accumulating
- [ ] Conversation state persisting

## Family Testing Protocol

### Phase 1: Internal Testing (30 min)
1. Run all test scenarios above
2. Verify each response mode
3. Check token accumulation
4. Test error recovery

### Phase 2: Limited Family Testing (1 hour)
1. **Mene:** Test complex project task with emotional context
2. **Test Child Query:** Educational question handling
3. **Test Scheduling:** Calendar coordination request

### Phase 3: Full Family Rollout (ongoing)
1. **Cindy:** Spanish language support + ADHD considerations
2. **Viola:** German support + scheduling coordination
3. **Children:** Age-appropriate interactions

## Success Metrics

### Technical Success
- ✅ API authentication working (both Anthropic and Notion)
- ✅ Enhancement methods integrated
- [ ] Intelligent routing achieving 85%+ accuracy
- [ ] Token budget staying under $15/day
- [ ] 20-turn conversation memory working

### Family Success
- [ ] Natural conversations vs mechanical responses
- [ ] Reduced friction in AI interactions
- [ ] Appropriate agent specialization
- [ ] Multi-language support active

## Monitoring Commands

```bash
# Real-time container logs
docker logs -f demestihas-yanay

# Check conversation states
docker exec lyco-redis redis-cli --scan --pattern "conv:*"

# Monitor token usage
watch 'docker exec lyco-redis redis-cli GET "tokens:daily:$(date +%Y%m%d)"'

# Check error rate
docker logs demestihas-yanay 2>&1 | grep -i error | tail -20
```

## Rollback Plan

If issues arise:
```bash
# Quick rollback to stable version
cd /root/demestihas-ai
git checkout yanay.py.backup.20250901
docker-compose restart yanay

# Full system reset
docker-compose down
docker-compose up -d
```

---

**Ready for Testing:** System should now support intelligent conversational mode with working APIs