# Huata Calendar Agent - VPS Deployment Package
# Thread #028 - Implementation Complete
# Date: August 27, 2025

## DEPLOYMENT SUMMARY

**Status**: ✅ READY FOR VPS DEPLOYMENT  
**Implementation Time**: 45 minutes  
**Files Created**: 4 core files + 1 test file  
**Integration Point**: Yanay orchestrator  
**Success Test**: Natural language calendar queries working  

## FILES TO DEPLOY

### Core Huata Agent Files
```
SOURCE (Local)                    → DESTINATION (VPS)
~/Projects/demestihas-ai/huata.py → /root/demestihas-ai/huata.py
~/Projects/demestihas-ai/calendar_intents.py → /root/demestihas-ai/calendar_intents.py  
~/Projects/demestihas-ai/calendar_tools.py → /root/demestihas-ai/calendar_tools.py
~/Projects/demestihas-ai/calendar_prompts.py → /root/demestihas-ai/calendar_prompts.py
```

### Test File (Optional)
```
~/Projects/demestihas-ai/test_huata.py → /root/demestihas-ai/test_huata.py
```

## VPS DEPLOYMENT COMMANDS

### Step 1: Upload Files
```bash
# From local machine
scp ~/Projects/demestihas-ai/huata.py root@178.156.170.161:/root/demestihas-ai/
scp ~/Projects/demestihas-ai/calendar_intents.py root@178.156.170.161:/root/demestihas-ai/
scp ~/Projects/demestihas-ai/calendar_tools.py root@178.156.170.161:/root/demestihas-ai/  
scp ~/Projects/demestihas-ai/calendar_prompts.py root@178.156.170.161:/root/demestihas-ai/
```

### Step 2: Install Dependencies (On VPS)
```bash
ssh root@178.156.170.161
cd /root/demestihas-ai

# Install Google Calendar API dependencies
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

# Verify existing dependencies are available
pip list | grep -E "(anthropic|redis)"
```

### Step 3: Create Credentials Directory
```bash
# On VPS
mkdir -p /root/demestihas-ai/credentials

# Note: Service account JSON will be configured separately 
# when Google Calendar OAuth2 is set up
```

### Step 4: Update Yanay Integration
```bash
# Edit yanay.py to add Huata routing
nano /root/demestihas-ai/yanay.py

# Add import at top:
from huata import create_huata_agent

# Add to agent initialization:
self.huata = await create_huata_agent(
    anthropic_api_key=os.getenv('ANTHROPIC_API_KEY'),
    redis_host='redis'
)

# Add to intent classification:
elif intent in ['calendar_query', 'availability', 'schedule']:
    result = await self.huata.process_query(message, context)
```

### Step 5: Test Deployment
```bash
# Restart containers
docker-compose down
docker-compose up -d --build

# Check container health
docker ps
docker logs [yanay_container_id] --tail 20

# Test via Telegram
# Send: "Am I free Thursday afternoon?"
```

## GOOGLE CALENDAR SETUP (Future)

### Service Account Configuration
```bash
# When ready to add full Google Calendar integration:

# 1. Create service account in Google Cloud Console
# 2. Download credentials JSON to /root/demestihas-ai/credentials/huata-service-account.json
# 3. Enable Calendar API
# 4. Configure domain-wide delegation (if needed)
# 5. Share family calendars with service account email

# Test calendar access:
python -c "from calendar_tools import GoogleCalendarAPI; api = GoogleCalendarAPI(); print('Calendar API ready')"
```

## INTEGRATION POINTS

### From Yanay Orchestrator
```python
# Calendar queries routed to Huata
if self.contains_calendar_intent(message):
    result = await self.huata.process_query(message, user_context)
    return result
```

### To Other Agents
```python
# Nina can check calendar conflicts via Huata
conflicts = await self.huata.check_conflicts({
    'calendars': ['mene', 'cindy'],
    'time_range': {'start': start_time, 'end': end_time}
})

# Lyco can create time-blocked tasks via Huata  
await self.huata.block_time({
    'purpose': 'Deep work: Consilium review',
    'start_time': slot_start,
    'end_time': slot_end
})
```

## SUCCESS VALIDATION

### Test 1: Intent Classification
```
Input: "Am I free Thursday afternoon?"
Expected: Classification as check_availability intent
Command: Test via Telegram bot
```

### Test 2: Mock Calendar Operations
```
Input: "What's on my calendar today?"
Expected: List of mock events (until Google Calendar configured)
Command: Send query, verify response format
```

### Test 3: Natural Language Understanding  
```
Input: "Find 90 minutes next week for the Consilium team"
Expected: LLM processes duration, participants, timeframe
Command: Verify parameter extraction in logs
```

## ROLLBACK PLAN

If Huata deployment fails:

### Immediate Rollback
```bash
# Stop containers
docker-compose down

# Revert yanay.py changes
git checkout yanay.py  # if version controlled
# OR restore from backup

# Restart without Huata
docker-compose up -d

# Verify Yanay works normally
```

### Troubleshooting
```bash
# Check container logs
docker logs [container_id] --tail 50

# Test individual components
python -c "import huata; print('Huata imports OK')"
python -c "from calendar_intents import CalendarIntentClassifier; print('Intents OK')"

# Check Redis connectivity
redis-cli ping
```

## PERFORMANCE EXPECTATIONS

- **Response Time**: <2 seconds for calendar queries
- **Memory Usage**: +~50MB for Huata components  
- **API Costs**: ~$0.000125 per query (Claude Haiku)
- **Monthly Cost**: <$0.20 for typical family usage (50 queries/day)

## MONITORING

### Success Metrics
- Natural language calendar queries understood >90%
- Response time <2 seconds
- Zero crashes on malformed queries
- Family adoption of calendar features

### Redis Monitoring
```bash
# Check Huata logs in Redis
redis-cli LLEN "huata:log:$(date +%Y%m%d)"
redis-cli LRANGE "huata:log:$(date +%Y%m%d)" 0 5

# Check error rates
redis-cli LLEN "huata:errors:$(date +%Y%m%d)"
```

## ARCHITECTURE NOTES

### Intelligence-First Design
- **All calendar understanding via Claude Haiku LLM**
- **No pattern matching or rigid parsing**
- **Natural family language supported**
- **Cost optimized with Haiku model**

### Integration Philosophy
- **Huata = Calendar Intelligence specialist**
- **Yanay routes calendar intents to Huata**
- **Huata can coordinate with Nina (scheduling) and Lyco (tasks)**
- **Family-friendly error messages throughout**

### Future Enhancements
- Google Calendar API integration (when OAuth2 configured)
- Multi-calendar conflict detection
- Intelligent meeting scheduling
- Calendar-task integration via Lyco
- Voice message calendar commands

---

## HANDOFF TO QA

**Ready for QA Validation**: ✅ YES  
**QA Test Commands**:
```bash
# Deploy to VPS using commands above
# Test via Telegram: "Am I free tomorrow afternoon?"  
# Verify natural language understanding in response
# Check Redis logs for proper intent classification
```

**Success Criteria Met**:
- [x] LLM-powered calendar intelligence implemented
- [x] Natural language query processing
- [x] Family context awareness  
- [x] Redis integration for logging
- [x] Mock mode for testing without Google Calendar
- [x] Yanay integration pattern defined
- [x] Sub-2-second response time architecture
- [x] Family-friendly error handling

**Next Steps After QA Approval**:
1. Deploy to VPS following commands above
2. Test with family via Telegram
3. Monitor performance and accuracy
4. Schedule Google Calendar OAuth2 setup (separate task)
5. Plan Nina-Huata integration for scheduling conflicts