# 🗓️ Huata Calendar Agent

Natural language calendar intelligence for the Demestihas family AI system.

## Overview

Huata is an LLM-powered calendar assistant that understands natural language queries like:
- "Am I free Thursday afternoon?"
- "Schedule 90 minutes with the Consilium team next week"
- "Find 2 hours for deep work this week"
- "Block time for that project review"

No pattern matching - pure AI understanding powered by Claude Haiku.

## Features

- **Natural Language Understanding**: Ask questions naturally, get intelligent responses
- **Multi-Calendar Support**: Manage calendars for entire family
- **Smart Scheduling**: Find optimal meeting times considering all participants
- **Conflict Detection**: Automatic checking across multiple calendars
- **Time Blocking**: Reserve focus time for deep work
- **Family Context**: Understands school hours, work schedules, and family dynamics

## Quick Start

### 1. Setup Environment

```bash
# Clone and navigate to Huata
cd demestihas-ai/huata

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# Required: ANTHROPIC_API_KEY
# Optional: Google Calendar credentials
```

### 2. Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 3. Run Huata

#### Local Development
```bash
./deploy.sh local
```

#### Docker Deployment
```bash
./deploy.sh docker
```

#### VPS Deployment
```bash
./deploy.sh vps
```

## API Endpoints

### Natural Language Query
```bash
curl -X POST http://localhost:8003/calendar/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Am I free tomorrow afternoon?",
    "user": "mene"
  }'
```

### Schedule Event
```bash
curl -X POST http://localhost:8003/calendar/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Team Standup",
    "start_time": "2024-08-29T10:00:00",
    "end_time": "2024-08-29T10:30:00",
    "user": "mene"
  }'
```

### Check Availability
```bash
curl http://localhost:8003/calendar/availability?user=mene
```

### List Events
```bash
curl http://localhost:8003/calendar/events?user=mene&date=2024-08-29
```

## Google Calendar Setup

1. Create a Google Cloud Project
2. Enable Google Calendar API
3. Create Service Account credentials
4. Download JSON credentials to `credentials/huata-service-account.json`
5. Share your calendars with the service account email

## Architecture

```
huata/
├── huata.py               # Main agent logic
├── calendar_intents.py    # LLM intent classification
├── calendar_tools.py      # Google Calendar API wrapper
├── calendar_prompts.py    # LLM prompt templates
├── main.py               # FastAPI server
├── test_huata.py         # Test suite
└── deploy.sh             # Deployment script
```

## Integration Points

### With Yanay (Orchestrator)
```python
# Yanay routes calendar queries to Huata
if intent == "calendar_query":
    result = await huata.process_query(message, context)
```

### With Nina (Scheduler)
```python
# Nina can check for conflicts
conflicts = await huata.check_conflicts(
    start_time="2024-08-29T18:00:00",
    end_time="2024-08-29T21:00:00"
)
```

### With Lyco (Task Manager)
```python
# Create time-blocked tasks
await huata.block_time({
    "purpose": "Deep work: Code review",
    "duration_minutes": 120
})
```

## Testing

```bash
# Test components locally
python3 test_huata.py

# Test deployed API
python3 test_huata.py --api
```

## Monitoring

```bash
# View logs (Docker)
docker logs -f huata-calendar-agent

# Check health
curl http://localhost:8003/

# Redis CLI
docker exec -it huata-redis redis-cli
```

## Cost Analysis

- **Per Query**: ~500 tokens × $0.25/1M = $0.000125
- **Daily (50 queries)**: $0.00625
- **Monthly**: ~$0.19

Negligible cost for massive usability improvement.

## Rollback

If issues arise:
```bash
./deploy.sh stop
```

Then remove Huata routing from Yanay until fixed.

## Family Impact

Before: "Check calendar for Thursday 2-5pm"
After: "Am I free Thursday afternoon?"

**Natural language that just works.**