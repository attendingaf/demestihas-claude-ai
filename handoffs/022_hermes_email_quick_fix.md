# Handoff #022: Hermes Email Container Quick Fix

## ATOMIC SCOPE
Fix Hermes email container docker network configuration issue (30 minutes maximum)

## CONTEXT
- **Current State**: Hermes container defined but failing to start
- **Root Cause**: Docker network configuration conflict
- **Impact**: Family cannot use email interface for audio processing
- **Email Account**: hermesaudio444@gmail.com (already configured)
- **VPS Location**: /root/lyco-ai/hermes_audio/

## IMPLEMENTATION STEPS

### Step 1: Diagnose Network Issue (5 minutes)
```bash
# SSH to VPS
ssh root@178.156.170.161

# Check current network configuration
docker network ls
docker inspect lyco-ai_default

# Check existing container conflicts
docker ps -a | grep hermes
```

### Step 2: Fix Network Configuration (10 minutes)
```bash
# Stop and remove any conflicting containers
docker stop $(docker ps -aq --filter name=hermes) 2>/dev/null || true
docker rm $(docker ps -aq --filter name=hermes) 2>/dev/null || true

# Edit docker-compose.yml to fix network
cd /root/lyco-ai
cp docker-compose.yml docker-compose.yml.backup

# Add explicit network configuration to hermes_audio service
nano docker-compose.yml
```

Add/modify hermes_audio service:
```yaml
  hermes_audio:
    build:
      context: ./hermes_audio
      dockerfile: Dockerfile
    container_name: hermes_audio_container
    environment:
      - HERMES_EMAIL_ADDRESS=hermesaudio444@gmail.com
      - HERMES_EMAIL_PASSWORD=${HERMES_EMAIL_PASSWORD}
      - EMAIL_IMAP_SERVER=imap.gmail.com
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - LYCO_API_URL=http://bot:8000
    volumes:
      - ./hermes_audio:/app
      - ./logs:/app/logs
    networks:
      - default
    restart: unless-stopped
    depends_on:
      - bot
```

### Step 3: Rebuild and Start (10 minutes)
```bash
# Rebuild with proper network
docker-compose build hermes_audio

# Start the service
docker-compose up -d hermes_audio

# Verify it's running
docker ps | grep hermes
docker logs hermes_audio_container --tail 50
```

### Step 4: Test Email Processing (5 minutes)
```bash
# Monitor logs while sending test email
docker logs -f hermes_audio_container &

# From your phone/computer:
# Send a test audio file to hermesaudio444@gmail.com
# Subject: "Test audio from family"

# Watch for processing in logs
# Should see: "New email detected", "Processing audio", "Tasks extracted"
```

## SUCCESS CRITERIA
```bash
# Container running without errors
docker ps | grep hermes  # Should show "Up X minutes"

# Logs show email polling
docker logs hermes_audio_container --tail 20 | grep "Checking"

# Test email processed
# Send audio to hermesaudio444@gmail.com
# Check Notion for new task within 2 minutes
```

## ROLLBACK PLAN
```bash
# If breaks, restore and use batch processor
docker-compose down hermes_audio
mv docker-compose.yml.backup docker-compose.yml
# Family continues with ./process_audio.sh
```

## REPORTING
- Update current_state.md: Hermes Email section to "✅ WORKING"
- Add thread_log.md entry: Thread #022 (Dev-Sonnet)
- Message family: "Email audio processing now available at hermesaudio444@gmail.com"
