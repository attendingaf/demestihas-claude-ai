# THREAD: Developer Thread #006
## ATOMIC SCOPE: Deploy Audio Workflow System to VPS

**Priority:** IMMEDIATE
**Estimated Duration:** 2 hours
**Type:** Infrastructure Deployment

## CONTEXT

### Current State
- VPS is running at 178.156.170.161 with Docker infrastructure
- Bot container (544c72011b31) and Redis (6ec922216657) are operational
- Audio workflow system is fully designed in handoffs/004 and 005
- All Python modules are documented and ready for deployment

### What This Enables
- Automatic processing of meeting recordings from Google Drive
- Compression, chunking, transcription using Whisper API
- AI-powered formatting and analysis with Claude
- Family-friendly meeting summaries with actionable insights

## IMPLEMENTATION STEPS

### Step 1: SSH to VPS and Create Directory Structure
```bash
ssh root@178.156.170.161

# Create audio workflow directories
mkdir -p /root/lyco-ai/audio_workflow
mkdir -p /root/lyco-ai/credentials
mkdir -p /tmp/audio_work

# Create log directory if not exists
mkdir -p /root/lyco-ai/logs
```

### Step 2: Create Core Python Files

Create `/root/lyco-ai/audio_workflow/workflow.py`:
```python
# Copy the complete workflow.py from handoff 004
# This is the main orchestrator (see handoff 004 for full code)
```

Create `/root/lyco-ai/audio_workflow/audio_processor.py`:
```python
# Copy the audio_processor.py from handoff 004
# Handles compression and chunking
```

Create `/root/lyco-ai/audio_workflow/google_drive_monitor.py`:
```python
# Copy from handoff 005
# Monitors Drive folder and manages uploads
```

Create `/root/lyco-ai/audio_workflow/transcription_service.py`:
```python
# Copy from handoff 005
# Handles Whisper API transcription
```

Create `/root/lyco-ai/audio_workflow/ai_formatter.py`:
```python
# Copy from handoff 005
# Formats transcripts using Claude
```

Create `/root/lyco-ai/audio_workflow/ai_analyzer.py`:
```python
# Copy from handoff 005
# Analyzes meetings with 5-question framework
```

Create `/root/lyco-ai/audio_workflow/__init__.py`:
```python
# Empty file to make it a Python package
```

### Step 3: Create Docker Configuration

Create `/root/lyco-ai/Dockerfile.audio`:
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.audio.txt .
RUN pip install --no-cache-dir -r requirements.audio.txt

# Copy application code
COPY audio_workflow/ ./audio_workflow/

# Create necessary directories
RUN mkdir -p /app/logs /tmp/audio_work

# Run the workflow
CMD ["python", "-m", "audio_workflow.workflow"]
```

Create `/root/lyco-ai/requirements.audio.txt`:
```
# Core
aiohttp==3.9.0
aiofiles==23.2.1

# Google APIs  
google-api-python-client==2.88.0
google-auth==2.19.0
google-auth-oauthlib==1.0.0
google-auth-httplib2==0.1.0

# OpenAI
openai==1.12.0

# Anthropic
anthropic==0.18.1

# Supabase
supabase==2.0.3

# Utilities
python-dotenv==1.0.0
pydantic==2.5.0
httpx==0.25.0
tenacity==8.2.3
```

### Step 4: Update Docker Compose

Edit `/root/lyco-ai/docker-compose.yml` and ADD this service:
```yaml
  audio_workflow:
    build: 
      context: .
      dockerfile: Dockerfile.audio
    container_name: audio_workflow
    restart: unless-stopped
    volumes:
      - ./audio_workflow:/app/audio_workflow
      - ./logs:/app/logs
      - ./credentials:/app/credentials
      - /tmp/audio_work:/tmp/audio_work
    environment:
      - GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/google-service-account.json
      - GOOGLE_DRIVE_FOLDER_ID=${GOOGLE_DRIVE_FOLDER_ID}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_KEY=${SUPABASE_KEY}
    depends_on:
      - redis
    networks:
      - lyco-network
```

### Step 5: Update Environment Variables

Add to `/root/lyco-ai/.env`:
```bash
# Audio Workflow Configuration
GOOGLE_DRIVE_FOLDER_ID="1HuuRO8xMgCksqxf5Aj_-EWVMJJTR9sj7"
OPENAI_API_KEY="sk-proj-xxx"  # Get from user if not set
```

### Step 6: Google Service Account Setup

**IMPORTANT:** Request from user:
1. Google Cloud service account JSON file
2. Share these Google Drive folders with the service account email:
   - "Uploaded recordings" folder (for monitoring)
   - "Audio Processing" folder (for outputs)

```bash
# Once received, upload to VPS:
# scp google-service-account.json root@178.156.170.161:/root/lyco-ai/credentials/
```

### Step 7: Build and Deploy

```bash
cd /root/lyco-ai

# Build the new container
docker-compose build audio_workflow

# Start the service
docker-compose up -d audio_workflow

# Verify it's running
docker ps | grep audio_workflow

# Check initial logs
docker logs --tail 50 audio_workflow
```

## SUCCESS TEST

```bash
# 1. Verify container is running
docker ps | grep audio_workflow
# Should show: audio_workflow container with "Up" status

# 2. Check logs for successful initialization
docker logs audio_workflow | grep "Starting Audio Workflow System"
# Should show initialization message

# 3. Test Google Drive connection
docker logs audio_workflow | grep "Found"
# After 5 minutes, should show drive check activity

# 4. Upload a test audio file to Google Drive folder
# Then monitor processing:
docker logs -f audio_workflow
# Should show: Download -> Compress -> Transcribe -> Format -> Analyze
```

## ROLLBACK PLAN

If the deployment fails or causes issues:

```bash
# Stop the audio workflow service
docker stop audio_workflow
docker rm audio_workflow

# Remove the Docker image
docker rmi lyco-ai_audio_workflow

# Service can be re-enabled later without affecting main bot
```

## VALIDATION CHECKLIST

- [ ] All Python files created in `/root/lyco-ai/audio_workflow/`
- [ ] Docker configuration files created
- [ ] Environment variables added to `.env`
- [ ] Google service account configured (if available)
- [ ] Container builds successfully
- [ ] Container starts without errors
- [ ] Logs show "Starting Audio Workflow System"
- [ ] No impact on existing bot/Redis containers

## REPORTING

After deployment, update:

1. **current_state.md** - Add Audio Workflow section:
```markdown
### Audio Workflow System
* **Status:** Deployed and running
* **Container:** audio_workflow
* **Features:** Drive monitoring, compression, transcription, AI analysis
* **Polling Interval:** 5 minutes
* **Input Folder:** Google Drive "Uploaded recordings"
* **Output Structure:** 5-stage processing pipeline
```

2. **thread_log.md** - Add completion entry:
```markdown
## Thread #006 (Dev-Sonnet) - Audio Workflow Deployment
**Date**: [ISO timestamp]
**Duration**: [Actual time]
**Outcome**: Success/Partial/Failed
**Deliverables**:
- Deployed audio workflow container
- Configured Google Drive integration
- Set up 5-stage processing pipeline
**Issues**: [Any problems encountered]
**Next Thread**: Test with real audio file
```

## NOTES FOR DEVELOPER

1. **FFmpeg Required:** The Dockerfile installs ffmpeg for audio processing
2. **Async Architecture:** All modules use async/await for scalability
3. **Error Recovery:** System tracks processed files to avoid duplicates
4. **Parallel Structure:** Each stage saves to Drive for QA visibility
5. **Cost Optimization:** Uses Haiku for formatting, Sonnet only for deep analysis

## HANDOFF TO QA

Once deployed, QA should:
1. Upload a test audio file (any meeting recording)
2. Monitor the 5 output folders in Google Drive
3. Verify each stage produces expected output
4. Check meeting analysis for accuracy
5. Confirm no memory leaks or performance issues

---

**This is an atomic 2-hour task. Focus on deployment only. Testing and optimization are separate threads.**