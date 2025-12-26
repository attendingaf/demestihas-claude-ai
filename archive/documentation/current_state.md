# Demestihas.ai Current State
**Last Updated:** August 31, 2025, 15:00 UTC
**System Version:** v7.5-emergency-stable (Core Task Management Restored - NEEDS VALIDATION)

## Infrastructure Status ✅

### VPS Access
* **Server IP:** `178.156.170.161` (SSH as root)
* **Provider:** DigitalOcean/Linode equivalent
* **OS:** Ubuntu 24.04 LTS
* **Project Path:** `/root/lyco-ai/`

### Running Services
* **Yanay Container:** Running (Fixed) - Status: Healthy ✅ - Emergency rollback applied
* **Redis Container:** Running (ID: 121ccc450311) - Port 6379 ✅
* **Nina Agent:** Active - Phase 2 simplified (calendar commands recognized) ✅
* **Bot Version:** v7.2-nina - Multi-agent with scheduling + calendar readiness
* **Telegram Bot:** @LycurgusBot (Token: 8324228035:AAH...)
* **Legacy Bot:** Stopped (docker stop lyco-telegram-bot executed)
* **Status:** Conversation memory active, date parsing fixed

### Access Points
* **SSH:** `ssh root@178.156.170.161`
* **Web Dashboard:** http://178.156.170.161:8000 (not yet implemented)
* **Redis:** Port 6379 exposed
* **Notion Workspace:** https://www.notion.so/Lyco-ai-252413ecf37680acbbf7ecfd3d1693d1
* **Notion Tasks DB:** 245413ec-f376-80f6-ac4b-c0e3bdd449c6 (LIVE with real data)

## Architecture Transition Plan

### Current State (Multi-Agent) ✅ DEPLOYED
```
Telegram → Yanay → Intent Classification → Lyco API → Notion
         ↘ Redis (conversation memory - 20 messages)
         ↘ Nina (schedule management - Phase 1 active)
```

### Target State (Specialized)
```
Telegram → Yanay → Lyco API → Notion
         ↘ Redis (conversation memory)
```

### Migration Status
- [x] Split bot.py into yanay.py and lyco_api.py ✅
- [x] Implement conversation memory in Yanay ✅
- [x] Create clean Lyco task API ✅
- [x] Test multi-agent coordination ✅
- [x] Deploy and cutover from legacy bot ✅
- [x] Fix date parsing bug (tomorrow → ISO format) ✅

## Current Configuration

### Environment Variables (Configured)
```
TELEGRAM_BOT_TOKEN     ✅ (in .env)
ANTHROPIC_API_KEY      ✅ (in .env)
NOTION_TOKEN           ✅ (in .env)
NOTION_DATABASE_ID     ✅ (in .env)
SUPABASE_URL           ❌ (Not configured)
SUPABASE_KEY           ❌ (Not configured)
```

### Project Files
```
/root/lyco-ai/
├── bot.py (19KB) - Main bot file (to be split)
├── ai_task_parser.py (17KB) - AI task extraction (moves to Lyco)
├── docker-compose.yml - Container orchestration
├── Dockerfile - Container build
├── .env - Environment configuration
├── logs/ - Application logs
└── [Multiple test variants]
```

## Family Context Summary

* **Active Users:** 1 (Mene testing)
* **Pending Users:** 5 (Cindy, Persy, Stelios, Franci, Viola)
* **Daily Task Volume:** ~10-20 tasks
* **Response Time:** 2-3 seconds average
* **Success Rate:** ~60% accurate task extraction

## Technical Stack

### Core Technologies (Locked)
* **LLM:** Anthropic Claude (Haiku for tasks, Sonnet for complex)
* **Database:** Notion API (primary), Supabase (pending for RAG)
* **Cache:** Redis (running, underutilized)
* **Framework:** Python telegram-bot library → FastAPI (planned)
* **Deployment:** Docker Compose on VPS

### Budget & Performance
* **Monthly Budget:** <$200 acceptable
* **Current Spend:** ~$5-10/month
* **API Costs:** ~$0.25/M tokens (Haiku)
* **Performance Target:** <3s response time

## Implementation Status

### ✅ Completed Components
* [x] VPS Docker setup with Redis
* [x] Basic Telegram bot responding
* [x] Notion integration (create/update)
* [x] AI task parsing with Anthropic
* [x] Basic error handling
* [x] Yanay/Lyco split architecture
* [x] Conversation memory (20 messages)
* [x] Nina Agent Phase 1 (schedule management)
* [x] Nina Agent Phase 2 - Simplified (calendar command recognition)

### 🚧 In Progress
* [ ] System stability validation (Handoff #044)
* [ ] Health check endpoint implementation (Handoff #045)
* [ ] Calendar routing architecture redesign (Handoff #046)

### ❌ Pending Implementation
* [ ] Supabase integration for RAG
* [ ] Voice message support
* [ ] Advanced validation layer
* [ ] Family routing logic
* [ ] Energy-based scheduling
* [ ] Apple Health integration
* [ ] Web dashboard on port 8000
* [ ] Twilio migration prep

## Known Issues

1. **Calendar Routing Conflict** - NEW ROOT CAUSE IDENTIFIED
   - Cause: Calendar intent checking intercepts task queries
   - Impact: Calendar routing breaks task routing to Lyco API  
   - Fix: Redesign calendar routing to NOT interfere with tasks
   - Priority: High - needs architectural solution

2. **Notion API Query Bug** - FIXED
   - Cause: Null filter in query causing 400 errors
   - Impact: Task queries failed
   - Fix: ✅ Applied - removed problematic filter

3. **Task Extraction Accuracy:** ~60%
   - Cause: Single-shot processing, no context
   - Impact: Family frustration with corrections
   - Fix: Add conversation context to prompts

## ✅ EMERGENCY ROLLBACK COMPLETED

**Resolution Time**: August 28, 2025, 01:00 UTC
**Status**: Core functionality RESTORED
**Evidence**: "show my tasks" now returns task list (not 400 error)
**Impact**: Family can use task management immediately
**Trade-off**: Calendar queries temporarily unavailable (acceptable)

1. **SYSTEM STABILITY VALIDATION** - CRITICAL IMMEDIATE
   - **Issue**: Post-emergency rollback, system claims stable but unverified
   - **Evidence**: QA found no health checks, calendar removed to restore tasks
   - **Status**: 🚨 Awaiting validation via Handoff #044
   - **Action**: Complete test suite validation immediately
   - **Priority**: BLOCKING - Must complete before ANY new features
   - **Success**: All task operations verified working

2. **HEALTH CHECK IMPLEMENTATION** - HIGH PRIORITY
   - **Issue**: No automated health monitoring exists
   - **Evidence**: Thread #5 mentioned but never implemented
   - **Status**: 📋 Handoff #045 created for implementation
   - **Action**: Implement after stability validation
   - **Priority**: Complete within 24 hours
   - **Success**: /health endpoint returns system status

3. **CALENDAR ROUTING REDESIGN** - ARCHITECTURE REQUIRED
   - **Issue**: Calendar intent checking cannot coexist with task routing
   - **Evidence**: Emergency rollback proved architectural conflict
   - **Status**: 🏗️ Architecture designed in Handoff #046
   - **Action**: Implement parallel intent scoring system
   - **Priority**: Sprint 2 - after system stability confirmed
   - **Success**: Both calendar AND task queries work simultaneously
   
2. **HUATA AGENT (Calendar Intelligence)** 📅 ⚠️ CONDITIONAL PASS - ONE BUG AWAY FROM SUCCESS
   - Status: ⚠️ DEPLOYED, WORKS WHEN ROUTED CORRECTLY - Thread #035 QA validation
   - Architecture: ✅ LLM-powered using Claude Haiku ($0.000125/query)
   - When Working: ✅ Beautiful natural language responses in <1 second
   - Proven Query: ✅ "Am I free thursday afternoon?" works perfectly
   - Problem: ❌ Most calendar queries misrouted due to keyword detection bug
   - Next Step: Execute handoff #036 → QA re-test → Family deployment TODAY

2. **NINA AGENT LLM UPGRADE** 🤖 SPRINT 2 (After Huata)
   - Status: Rule-based implementation failing on complex schedules
   - Fix: Add Claude Haiku for natural language schedule parsing
   - Dependencies: Huata for calendar integration
   - Impact: Accurate split shift parsing, natural schedule commands
   - Timeline: Week 2 (requires Huata completion)
   - Success: Handle "6a-9a and 2p-9p Tuesday through Friday" naturally

3. **FAMILY ROLLOUT** 📱 ONGOING
   - Status: Hermes email LIVE at hermesaudio444@gmail.com
   - Current: Testing with Mene, monitoring stability
   - Next: Add Cindy after Huata deployment
   - Timeline: Gradual rollout over 2 weeks
   - Success: 3+ active family members

4. **ARCHITECTURE PRINCIPLE** 🧠 ESTABLISHED
   - Decision: All agents (except Hermes) must use LLMs
   - Rationale: Building intelligent agents, not deterministic workflows
   - Impact: Every new agent gets Claude Haiku/Sonnet by default
   - Cost: Acceptable trade-off for true natural language understanding

4. **AUDIO SYSTEM MONITORING** 📊 BACKGROUND TASK
   - Yanay orchestrator implementation (Day 1-2)
   - Lyco API split (Day 2-3)
   - Conversation memory (Day 3-4)
   - Testing & deployment (Day 4-5)

4. **Test with full family** (After Sprint 1)
5. **Add validation layer** (Sprint 2)
6. **Consider Supabase RAG** (Sprint 3+)

## Development Infrastructure Status

### Development Triad Established (August 24, 2025)
- **PM Instructions:** ✅ Created (PM_INSTRUCTIONS.md)
- **Developer Instructions:** ✅ Created (DEVELOPER_INSTRUCTIONS.md)
- **QA Instructions:** ✅ Created (QA_INSTRUCTIONS.md)
- **Deployment Guide:** ✅ Created (DEPLOYMENT_GUIDE.md)
- **Architecture Updated:** ✅ Includes triad workflow
- **README:** ✅ Complete quick-start guide

### Beta Testing Environment (August 27, 2025)
- **Claude Desktop Project:** ✅ Instructions created
- **Self-Learning System:** ✅ Documentation framework established
- **Beta Location:** ~/Projects/demestihas-ai/claude-desktop/
- **Key Innovation:** Self-aware AI that documents learnings
- **Purpose:** Test locally, learn patterns, improve VPS deployment
- **Status:** Ready for family testing

### Development Workflow
```
PM (Opus) → Dev (Sonnet) → QA (Claude) → Deployment
```
- Handoffs in `/handoffs/` directory
- All work logged in `thread_log.md`
- State tracked in `current_state.md`

## Audio Processing System 🔄

### Multi-Agent Architecture: Hermes + Lyco ✅
**Hermes** = Communication specialist (audio, email, messaging)  
**Lyco** = Task management specialist (tasks, scheduling, Notion)

### Current Status: PRODUCTION READY ✅ - FAMILY DEPLOYMENT APPROVED

#### Direct Transcription (WORKING) 🎉
- **Status:** ✅ OpenAI Whisper installed on VPS (--break-system-packages)
- **Status:** ✅ Successfully transcribed Audio_08_22_2025_12_01_43.mp3 
- **Location:** Audio files in ~/Projects/demestihas-ai/Audio-Inbox/
- **Processing Time:** ~30-45 seconds per 5-minute audio
- **Last Success:** August 25, 2025, 23:00 UTC (working after debugging)

#### Batch Processor (PRODUCTION) ✅
- **Status:** ✅ Complete implementation with 6-stage pipeline (Thread #017)
- **Status:** ✅ Family launcher: `./process_audio.sh` (755 permissions)
- **QA Status:** ✅ APPROVED - All validation tests passed
- **Features:** Upload → Transcribe → Download → Extract → Summarize → Store
- **Location:** ~/Projects/demestihas-ai/batch_process_audio.py (285 lines)
- **Results:** Audio-Inbox/processed/ with markdown summaries
- **Family Interface:** `cd ~/Projects/demestihas-ai && ./process_audio.sh`
- **Performance:** 60-90 seconds per 5-minute file (family-acceptable)

#### Hermes Email Approach (PRODUCTION) ✅
- **Status:** ✅ Container deployed and running on VPS (Thread #023)
- **Status:** ✅ Gmail integration: hermesaudio444@gmail.com (AUTHENTICATION WORKING)
- **Status:** ✅ Environment configured and container stable
- **QA Status:** ✅ APPROVED - Thread #023 deployment successful
- **VPS Location:** `/root/lyco-ai/hermes_audio/` ✅ Running container (ID: e05d6640d542)
- **Family Interface:** Email audio files → automatic processing → tasks in Notion
- **Deployment:** August 26, 2025, 13:27 UTC (Thread #023 execution)
- **Authentication Fix:** August 26, 2025, 14:45 UTC (Thread #025 completion)
- **LIVE FOR FAMILY USE:** Email to hermesaudio444@gmail.com for voice memo processing

#### Google Drive Approach (Fallback)
- **Status:** Thread #008 fixes deployed to VPS, file detection still problematic
- **VPS Location:** `/root/lyco-ai/audio_workflow/` ✅ Enhanced with folder scope
- **Issue:** Service account permission challenges persist

### Processing Pipeline (Both Systems) ✅
- **Stage 1:** Compress audio (mono 16kHz, 75% size reduction)
- **Stage 2:** Chunk if >25MB (20MB chunks for API compatibility)
- **Stage 3:** Transcribe with OpenAI Whisper API
- **Stage 4:** Format transcript with Claude Haiku (cost-optimized)
- **Stage 5:** Analyze with Claude Sonnet (5-question framework)
- **Results:** Upload to Google Drive folders for family access
- **Task Integration:** Hermes → Lyco for automatic Notion task creation

### Implementation Details
- **Container:** audio_workflow with FFmpeg and Python 3.11
- **Dependencies:** Google Drive API, OpenAI Whisper, Anthropic Claude
- **Volume mounts:** credentials, working directories
- **Environment:** All variables documented in env-additions.txt
- **Polling:** 5-minute interval for Google Drive monitoring
- **Processing Pipeline:** 5-stage (compress → chunk → transcribe → format → analyze)

## Quick Commands Reference

```bash
# SSH to VPS
ssh root@178.156.170.161

# View logs
docker logs 544c72011b31 --tail 50

# Restart bot
docker restart 544c72011b31

# Edit and rebuild
nano /root/lyco-ai/bot.py
docker-compose up -d --build

# Check status
docker ps
docker stats --no-stream
```

## Architecture Decision Log

1. **Specialized Architecture Chosen** (Aug 19, 2025)
   - Reason: Scalability, clarity, testability
   - Impact: Initial complexity, long-term flexibility

2. **Yanay as Orchestrator** (Aug 19, 2025)
   - Reason: Separate conversation from task logic
   - Impact: Cleaner APIs, easier testing

3. **Keep Notion as Primary DB** (Maintained)
   - Reason: Family familiarity, existing UI
   - Impact: Some latency, excellent UX

---

**Note:** This is a living document. Update after each significant change.