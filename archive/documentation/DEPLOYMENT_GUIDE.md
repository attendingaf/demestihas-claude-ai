# Demestihas.ai Deployment Guide

## Overview

This guide explains the file synchronization between local development (macOS) and production VPS, plus the deployment process for the PM > Dev > QA triad workflow.

## File Locations

### Local Development (macOS)
**Path**: `~/Projects/demestihas-ai/`

These files stay LOCAL only (never upload to VPS):
- `PM_INSTRUCTIONS.md` - Strategic planning guide
- `DEVELOPER_INSTRUCTIONS.md` - Implementation guide  
- `QA_INSTRUCTIONS.md` - Validation guide
- `current_state.md` - System state tracking
- `thread_log.md` - Work history
- `architecture.md` - System design
- `family_context.md` - Family information
- `handoffs/*.md` - Work packages

### Production VPS
**Server**: `178.156.170.161`
**Path**: `/root/demestihas-ai/`

These files are deployed to VPS:
- `bot.py` - Main bot logic (to be split)
- `demestihas.py` - Orchestrator (when created)
- `lyco_api.py` - Task API (when created)
- `ai_task_parser.py` - Task extraction
- `docker-compose.yml` - Container configuration
- `Dockerfile` - Container build
- `.env` - Environment variables (already there)
- `requirements.txt` - Python dependencies

## Deployment Workflow

### 1. Local Development Phase

```bash
# PM creates handoff
vim ~/Projects/demestihas-ai/handoffs/006_implement_health_check.md

# Developer implements locally
cd ~/Projects/demestihas-ai/
# Creates or modifies files
python -m pytest tests/  # Local testing

# QA validates locally
python qa_test_suite.py
```

### 2. File Upload Process

After QA approval, upload changed files to VPS:

```bash
# Example: Upload modified bot.py
scp ~/Projects/demestihas-ai/bot.py root@178.156.170.161:/root/lyco-ai/

# Example: Upload new yanay.py
scp ~/Projects/demestihas-ai/yanay.py root@178.156.170.161:/root/lyco-ai/

# Example: Upload docker-compose changes
scp ~/Projects/demestihas-ai/docker-compose.yml root@178.156.170.161:/root/lyco-ai/
```

### 3. VPS Deployment

```bash
# SSH to VPS
ssh root@178.156.170.161

# Navigate to project
cd /root/lyco-ai/

# Rebuild and restart containers
docker-compose down
docker-compose up -d --build

# Check logs
docker logs -f [container_id]

# Verify health
curl http://178.156.170.161:8000/health
```

## Files to Create/Upload

### Immediate Priority

1. **Create Locally First** (Week 1)
   ```
   ~/Projects/demestihas-ai/
   ├── yanay.py                 # New orchestrator
   ├── lyco_api.py              # Split from bot.py
   ├── tests/
   │   ├── test_yanay.py
   │   ├── test_lyco.py
   │   └── test_integration.py
   └── deployment_notes.md     # Track what needs uploading
   ```

2. **Upload to VPS After QA**
   ```bash
   # After QA approves yanay.py
   scp yanay.py root@178.156.170.161:/root/lyco-ai/
   
   # After QA approves lyco_api.py  
   scp lyco_api.py root@178.156.170.161:/root/lyco-ai/
   
   # Update docker-compose.yml for new services
   scp docker-compose.yml root@178.156.170.161:/root/lyco-ai/
   ```

### File Synchronization Rules

| File Type | Local Only | Upload to VPS | When to Upload |
|-----------|------------|---------------|----------------|
| Instructions (*.md) | ✅ | ❌ | Never |
| State tracking | ✅ | ❌ | Never |
| Handoffs | ✅ | ❌ | Never |
| Python code | Develop | ✅ | After QA approval |
| Docker config | Edit | ✅ | After QA approval |
| Tests | ✅ | Optional | If VPS testing needed |
| .env | ❌ | Already there | Update carefully |

## Suggested Upload Script

Create `~/Projects/demestihas-ai/deploy.sh`:

```bash
#!/bin/bash
# Deploy approved changes to VPS

if [ "$1" == "" ]; then
    echo "Usage: ./deploy.sh <file_or_directory>"
    exit 1
fi

# Configuration
VPS_IP="178.156.170.161"
VPS_PATH="/root/lyco-ai/"
LOCAL_PATH="~/Projects/demestihas-ai/"

# Check if file exists locally
if [ ! -e "$1" ]; then
    echo "Error: $1 not found"
    exit 1
fi

# Upload file
echo "Uploading $1 to VPS..."
scp "$1" root@${VPS_IP}:${VPS_PATH}

# Restart services if docker-compose changed
if [ "$1" == "docker-compose.yml" ]; then
    echo "Restarting Docker services..."
    ssh root@${VPS_IP} "cd ${VPS_PATH} && docker-compose up -d --build"
fi

echo "Deployment complete!"
```

## State File Management

### What Stays Local
These files track the development process and should NEVER be uploaded:

```markdown
current_state.md     - Tracks what's deployed, versions, issues
thread_log.md        - History of all work done
family_context.md    - Sensitive family information
handoffs/*.md        - Work specifications
```

### How to Track Deployments

After each deployment, update `current_state.md`:

```markdown
## Latest Deployment
**Date**: 2025-08-24
**Version**: v7
**Files Updated**:
- yanay.py (new)
- bot.py (modified - added health check)
- docker-compose.yml (added yanay service)
**VPS Status**: Running, healthy
**Next Deployment**: lyco_api.py split
```

## Emergency Procedures

### Quick Rollback

```bash
# On VPS
cd /root/lyco-ai/

# Restore previous version
git checkout HEAD~1 bot.py  # If using git
# OR restore from backup
cp bot.py.backup bot.py

# Restart
docker-compose up -d --build
```

### Check System Health

```bash
# Local check (what should be deployed)
cat ~/Projects/demestihas-ai/current_state.md | grep "Version"

# VPS check (what is deployed)
ssh root@178.156.170.161 "docker ps && docker logs --tail 20 [container_id]"
```

## Communication Between Triad

### PM → Dev Handoff
- Created in: `~/Projects/demestihas-ai/handoffs/`
- Never uploaded to VPS
- Contains exact specifications

### Dev → QA Handoff  
- Documented in: `thread_log.md`
- Code changes in: Local files
- Test commands included

### QA → Deployment
- Approval in: `thread_log.md`
- Upload list in: QA report
- Deployment commands documented

## Best Practices

1. **Never upload state files** - They track work, not code
2. **Always QA locally first** - Catch issues before VPS
3. **Document every upload** - Update current_state.md
4. **Keep VPS minimal** - Only production code
5. **Backup before major changes** - Can rollback quickly

## Quick Reference Commands

```bash
# Check local state
cat ~/Projects/demestihas-ai/current_state.md

# Upload single file
scp [file] root@178.156.170.161:/root/lyco-ai/

# SSH to VPS
ssh root@178.156.170.161

# Restart services (on VPS)
docker-compose up -d --build

# View logs (on VPS)
docker logs -f [container_id]

# Test bot
# Send message to @LycurgusBot on Telegram
```

---

**Remember**: Local = Development & Planning, VPS = Production Code Only