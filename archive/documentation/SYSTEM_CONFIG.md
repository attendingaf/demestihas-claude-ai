# Demestihas AI System Configuration - MULTI-AGENT ARCHITECTURE
**Last Updated:** September 1, 2025, 18:00 UTC  
**Purpose:** Dynamic configuration for multi-agent AI system - CORRECTED AFTER ARCHITECTURE DISCOVERY  
**CRITICAL:** Previous documentation incorrectly assumed single bot - this reflects actual containerized multi-agent reality

## Infrastructure Configuration

### VPS Production Environment
```yaml
Server IP: 178.156.170.161
SSH User: root
OS: Ubuntu 24.04 LTS
Project Path: /root/demestihas-ai/
Architecture: Docker-based multi-agent system with orchestration layer
Deployment: docker-compose.yml managed containers
```

### Multi-Agent Architecture (ACTUAL SYSTEM)
```yaml
Orchestration Layer:
  - Yanay.ai: Container-based orchestration agent
  - Status: ❌ EXITED 14 hours ago (PRIMARY ISSUE)
  - Container: demestihas-yanay (f312e9b26dc6)
  - Role: Routes Telegram messages to specialized agents

Specialized Agents:
  - Nina (Scheduler): /root/demestihas-ai/nina.py (21.8KB)
  - Huata (Calendar): /root/demestihas-ai/huata.py (18.8KB)
  - Lyco (Project Manager): /root/demestihas-ai/lyco_api.py (13.5KB)
  - Status: ⚠️ Files present, integration via Yanay.ai

Audio Processing:
  - Hermes Audio: ✅ Running (Container: e05d6640d542)
  - Audio Workflow: ✅ Running (Container: 75e7798bd89e)
  - Audio Process: ✅ Running (PID: 677462, 581569)

Infrastructure:
  - Redis: ✅ Running (Container: 121ccc450311, Port: 6379)
  - Telegram Bot: ❌ Container exited 5 days ago (lyco-telegram-bot)
```

### Correct Message Flow
```yaml
Telegram Message → Yanay.ai (orchestrator) → Specialized Agent (Nina/Huata/Lyco) → Tools (Notion/API) → Response
```

### Previous Misunderstanding
```yaml
WRONG: Direct Telegram → Single Bot → Notion
CORRECT: Telegram → Yanay.ai → Agent Selection → Tool Usage → Response
```

## Container Status (Current Reality)
```yaml
Running Containers:
  ✅ hermes_audio (e05d6640d542) - Up 6 days
  ✅ audio_workflow (75e7798bd89e) - Up 7 days  
  ✅ lyco-redis (121ccc450311) - Up 13 days

Failed/Exited Containers:
  ❌ demestihas-yanay (f312e9b26dc6) - Exited 14 hours ago
  ❌ lyco-telegram-bot (df4782aef61a) - Exited 5 days ago

Management:
  - docker-compose.yml: Primary deployment file
  - Location: /root/demestihas-ai/docker-compose.yml (3.9KB)
  - Restart: docker-compose up -d [service]
```

## Agent Files (Discovered)
```yaml
Core Agents:
  yanay.py: 14.5KB - Orchestration logic
  nina.py: 21.8KB - Scheduling and calendar coordination
  huata.py: 18.8KB - Calendar management
  lyco_api.py: 13.5KB - Project and task management

Supporting Files:
  ai_task_parser.py: 13.1KB - Task extraction
  calendar_tools.py: 14.9KB - Calendar integration
  calendar_prompts.py: 12.2KB - Calendar AI prompts
  bot_*.py: Various bot implementations (legacy/testing)

Configuration:
  docker-compose.yml: 3.9KB - Container orchestration
  Dockerfile.yanay: 563 bytes - Yanay container config
  .env: 1KB - Environment variables
```

## API Integrations
```yaml
Notion Configuration:
  Workspace: https://www.notion.so/Lyco-ai-252413ecf37680acbbf7ecfd3d1693d1
  Database: 245413ec-f376-80f6-ac4b-c0e3bdd449c6
  Integration: Via specialized agents through Yanay.ai

Anthropic Configuration:
  Primary: Claude 3 Haiku (routine tasks)
  Complex: Claude 3 Sonnet (complex parsing)  
  Integration: Multiple agents can use AI services

Calendar Integration:
  Google Calendar: Via Huata.ai agent
  Tools: calendar_tools.py, calendar_prompts.py

Telegram Integration:
  Bot Token: Configured in .env
  Interface: Through Yanay.ai orchestration
  Bot Handle: @LycurgusBot
```

## Deployment Protocols (CORRECTED)

### Multi-Agent System Startup
```bash
# Navigate to project
cd /root/demestihas-ai

# Start all services via docker-compose
docker-compose up -d

# Verify critical containers
docker ps | grep -E "(yanay|lyco|hermes|redis)"

# Check Yanay.ai orchestration logs
docker logs demestihas-yanay

# Test Telegram → Yanay.ai → Agent flow
```

### Individual Agent Management
```bash
# Restart specific agent
docker-compose restart yanay
docker-compose restart lyco-telegram-bot

# Check agent logs
docker logs [container-name]

# View agent files
ls -la /root/demestihas-ai/{yanay,nina,huata,lyco_api}.py
```

### Emergency Recovery
```bash
# Full system restart
docker-compose down
docker-compose up -d

# Individual agent restart
docker-compose up -d yanay
docker-compose up -d lyco-telegram-bot
```

## Current System Status

### PRIMARY ISSUE IDENTIFIED
```yaml
Root Cause: Yanay.ai orchestration container exited 14 hours ago
Impact: Telegram messages not routing to specialized agents
Solution: Restart Yanay.ai container and verify agent communication

Secondary: Telegram bot container also exited 5 days ago
Impact: No Telegram interface active
Solution: Restart lyco-telegram-bot container
```

### Architecture Correction Required
```yaml
Previous Focus: Single bot health check deployment
Correct Focus: Multi-agent orchestration system restoration
Files Affected: All documentation assuming single bot architecture
Claude Desktop: May need instructions updated for multi-agent system
```

## Family Context (Multi-Agent)
```yaml
Primary Users:
  - Mene: Project owner, physician executive, ADHD
  - Cindy: ER physician, ADHD inattentive, Spanish
  - Viola: Au pair, coordination tasks, German

Agent Specialization:
  - Nina: Scheduling coordination (good for Viola)
  - Huata: Calendar management (good for all family)
  - Lyco: Task and project management (good for Mene)
  - Yanay: Intelligent routing between agents
```

## System Recovery Priority
```yaml
1. Restart Yanay.ai orchestration (docker-compose up -d yanay)
2. Restart Telegram interface (docker-compose up -d lyco-telegram-bot)  
3. Test message routing: Telegram → Yanay → Agent → Response
4. Verify all agent integrations working
5. Update all documentation to reflect multi-agent reality

BEFORE ANY CHANGES: Update all .md files to reflect multi-agent architecture
```

---

**CRITICAL DISCOVERY:** This system is far more sophisticated than previously documented. All previous documentation assumed single bot when reality is containerized multi-agent system with orchestration layer.

**UPDATE ALL DOCUMENTATION BEFORE ANY SYSTEM CHANGES**
