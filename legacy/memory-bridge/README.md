# Memory Bridge - LLM Extraction Bridge for Dual Memory System

## Overview

The Memory Bridge is an automated extraction layer that converts unstructured chat messages from Mem0/Qdrant into structured facts stored in FalkorDB, enabling the Memory UI to display relevant information from conversations.

## Architecture

```
Chat → Agent → Mem0/Qdrant (unstructured memories) ✅
            ↓
     [LLM Extractor] ← Memory Bridge
            ↓
         FalkorDB (structured triples) ✅
            ↑
    Memory UI (queries FalkorDB)
```

## What It Does

1. **Queries Qdrant** for recent chat messages (last 24 hours by default)
2. **Uses Claude API** (Sonnet 4.5) to extract structured facts from unstructured chat
3. **Converts facts** to subject-predicate-object triples
4. **Stores triples** in FalkorDB via the existing `/memory/store` endpoint
5. **Runs continuously** as a background service

## Components

### Files

- `extract_facts.py` - Main extraction script
- `config.yaml` - Configuration file
- `Dockerfile` - Container definition
- `docker-compose.yml` - Service orchestration
- `extraction.log` - Application logs

### Configuration (`config.yaml`)

```yaml
extraction:
  enabled: true
  interval_seconds: 300  # Run every 5 minutes
  batch_size: 20  # Process 20 messages at a time
  lookback_hours: 24  # Only process last 24h

anthropic:
  model: "claude-sonnet-4-20250514"
  max_tokens: 2000
  temperature: 0.1  # Low for consistency

filtering:
  min_confidence: 0.7  # Only store facts with >70% confidence
  min_importance: 5  # Only store importance >= 5
  exclude_contexts: ["greeting", "acknowledgment"]

storage:
  api_url: "http://localhost:8000"
  memory_type: "system"  # Store extracted facts as system memories
  deduplicate: true  # Check for existing facts before storing

qdrant:
  host: "qdrant"
  port: 6333
  collection_name: "demestihas_memories"

logging:
  level: "INFO"
  file: "/root/memory-bridge/extraction.log"
  max_size_mb: 100
```

## Installation & Deployment

### Prerequisites

- Docker installed
- Access to the `root_demestihas-network` Docker network
- `ANTHROPIC_API_KEY` environment variable set
- JWT token file (`mene-jwt-token.json`)

### Quick Start

1. **Build the Docker image:**
   ```bash
   cd /root/memory-bridge
   docker build -t memory-bridge:latest .
   ```

2. **Run with Docker Compose:**
   ```bash
   export ANTHROPIC_API_KEY=<your-key>
   docker-compose up -d
   ```

3. **Check logs:**
   ```bash
   docker logs -f demestihas-memory-bridge
   ```

### Manual Docker Run

```bash
docker run -d \
  --name demestihas-memory-bridge \
  --network root_demestihas-network \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  -v /root/memory-bridge/extraction.log:/app/extraction.log \
  --restart unless-stopped \
  memory-bridge:latest
```

## Usage

### Test Single Message Extraction

```bash
docker run --rm \
  --network root_demestihas-network \
  -v /root/memory-bridge:/app \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  python:3.12-slim bash -c \
  "cd /app && pip install -q anthropic qdrant-client pyyaml requests && \
  python3 extract_facts.py --test-message 'Dr. Chen wants me to check blood pressure before meals'"
```

Expected output:
```
=== Extracted Facts ===

1. Subject: Dr. Chen
   Predicate: wants patient to
   Object: check blood pressure before meals
   Context: medical
   Importance: 9
   Confidence: 0.95
```

### Dry Run (No Storage)

```bash
docker run --rm \
  --network root_demestihas-network \
  -v /root/memory-bridge:/app \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  python:3.12-slim bash -c \
  "cd /app && pip install -q anthropic qdrant-client pyyaml requests && \
  python3 extract_facts.py --dry-run --once --hours 24"
```

### Run Once (No Loop)

```bash
docker run --rm \
  --network root_demestihas-network \
  -v /root/memory-bridge:/app \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  python:3.12-slim bash -c \
  "cd /app && pip install -q anthropic qdrant-client pyyaml requests && \
  python3 extract_facts.py --once --hours 24"
```

## Monitoring

### View Logs

```bash
# Docker logs
docker logs -f demestihas-memory-bridge

# Log file
tail -f /root/memory-bridge/extraction.log
```

### Check Statistics

Logs show:
- Messages processed
- Facts extracted
- Facts stored
- Duplicates skipped
- API calls
- Errors
- Estimated API cost

Example:
```
Statistics:
  Messages processed: 15
  Facts extracted: 23
  Facts stored: 20
  Duplicates skipped: 3
  API calls: 15
  Errors: 0
  Estimated API cost: $0.0045
```

### Container Status

```bash
docker ps | grep memory-bridge
docker inspect demestihas-memory-bridge
```

## Fact Extraction Rules

The Claude API extracts facts based on these rules:

1. **Only extract verifiable facts**, not opinions or questions
2. **Medical information** = importance 9-10
3. **Family information** = importance 7-8
4. **Preferences** = importance 5-6
5. **Context** must be one of: `medical`, `family`, `project`, `schedule`, `preference`, `adhd-optimization`
6. **Confidence** = how certain the extraction is (0.0-1.0)
7. **Ignore** greetings, acknowledgments, and meta-conversation

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs demestihas-memory-bridge

# Verify network
docker network inspect root_demestihas-network

# Check environment variables
docker exec demestihas-memory-bridge env | grep ANTHROPIC
```

### No Messages Found

- Check if Qdrant has data: `docker logs demestihas-qdrant`
- Verify collection name in `config.yaml`
- Try different `lookback_hours` value

### API Errors

- Verify `ANTHROPIC_API_KEY` is set
- Check API rate limits
- Review `extraction.log` for error details

### JWT Token Issues

- Ensure `mene-jwt-token.json` exists in `/root/memory-bridge/`
- Token must be valid (not expired)
- Regenerate if needed: `curl -X POST http://localhost:8000/auth/login ...`

## Cost Monitoring

The system tracks Claude API usage:

- **Model**: Claude Sonnet 4 (~$3 per million input tokens, ~$15 per million output tokens)
- **Estimated cost per call**: ~$0.0003
- **Daily estimate** (288 runs at 5min intervals): ~$0.09/day
- **Monthly estimate**: ~$2.70/month

Actual costs depend on:
- Number of messages processed
- Message length
- Extraction complexity

## Maintenance

### Update Configuration

1. Edit `config.yaml`
2. Restart container:
   ```bash
   docker restart demestihas-memory-bridge
   ```

### Update Code

1. Edit `extract_facts.py`
2. Rebuild and restart:
   ```bash
   cd /root/memory-bridge
   docker build -t memory-bridge:latest .
   docker-compose down
   docker-compose up -d
   ```

### View Extraction Quality

Check FalkorDB for stored facts:
```bash
docker exec demestihas-graphdb redis-cli GRAPH.QUERY mene_memory "MATCH (n:Memory) RETURN count(n)"
```

### Stop Service

```bash
docker-compose down
# or
docker stop demestihas-memory-bridge
docker rm demestihas-memory-bridge
```

## Success Criteria

✅ Script queries Qdrant successfully  
✅ Claude API extracts facts accurately  
✅ Facts stored in FalkorDB via API  
✅ Deduplication working  
✅ Service runs continuously  
✅ Logs are clear and useful  
✅ Cost under $0.20/day  
✅ Docker container operational  

## Support

For issues or questions:
1. Check logs: `/root/memory-bridge/extraction.log`
2. Review container status: `docker ps`
3. Validate configuration: `cat /root/memory-bridge/config.yaml`
4. Test extraction: Use `--test-message` flag

## Architecture Diagram

```
┌─────────────────┐
│   User Chat     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   AI Agent      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│  Mem0/Qdrant    │      │  Memory Bridge   │
│  (Unstructured) │◄─────│  (This Service)  │
└─────────────────┘      └────────┬─────────┘
                                  │
                                  │ Claude API
                                  │ Extraction
                                  ▼
                         ┌─────────────────┐
                         │    FalkorDB     │
                         │   (Structured)  │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │   Memory UI     │
                         │  (Streamlit)    │
                         └─────────────────┘
```

## License

Internal tool for Demestihas AI system.
