# DEPLOYMENT HANDOFF #023: Execute Hermes Email Fix

**THREAD**: Production Deployment #023
**ATOMIC SCOPE**: Deploy Thread #022 Hermes fix to VPS and verify email processing
**PRIORITY**: IMMEDIATE - Family waiting for audio processing capability

## CONTEXT
- **Previous Work**: Thread #022 implemented docker network fix for Hermes email
- **QA Status**: ✅ CONDITIONAL PASS - Ready for deployment with verification requirement
- **Current State**: hermesaudio444@gmail.com configured, container built but not running
- **Family Impact**: Unlocks intuitive email interface for audio processing

## IMPLEMENTATION STEPS

### 1. Deploy to VPS (Execute on VPS: 178.156.170.161)
```bash
# SSH to VPS
ssh root@178.156.170.161
cd /root/lyco-ai

# Safety: Backup current compose file
cp docker-compose.yml docker-compose.yml.backup

# Stop any existing hermes containers
docker stop $(docker ps -aq --filter name=hermes) 2>/dev/null || true
docker rm $(docker ps -aq --filter name=hermes) 2>/dev/null || true

# Add hermes_audio service to docker-compose.yml
# Copy service definition from Thread #022 files:
cat << 'EOF' >> docker-compose.yml

  hermes_audio:
    build:
      context: .
      dockerfile: Dockerfile.hermes
    container_name: hermes_audio
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - HERMES_EMAIL_ADDRESS=hermesaudio444@gmail.com
      - HERMES_EMAIL_PASSWORD=${HERMES_EMAIL_PASSWORD}
      - EMAIL_IMAP_SERVER=imap.gmail.com
      - EMAIL_IMAP_PORT=993
      - LYCO_WEBHOOK_URL=http://bot:8000/webhook
    volumes:
      - ./hermes_audio/:/app/
      - ./logs:/app/logs
    networks:
      - default
    depends_on:
      - bot
    restart: unless-stopped
EOF

# Build and start hermes container
docker-compose build hermes_audio
docker-compose up -d hermes_audio
```

### 2. Immediate Verification (MUST complete within 30 minutes)
```bash
# Check container status
docker ps | grep hermes

# Verify container is running (should show "Up X seconds")
# Expected: hermes_audio container with "Up" status

# Check logs for successful startup
docker logs hermes_audio --tail 20

# Expected log entries:
# - "Connecting to IMAP server..."
# - "Checking for new emails..."
# - No network connection errors
```

### 3. End-to-End Test (MUST complete within 2 hours of deployment)
```bash
# Test email processing capability
# 1. Send test email with audio attachment to hermesaudio444@gmail.com
# 2. Monitor logs: docker logs hermes_audio --follow
# 3. Expected: Email received, audio processed, tasks extracted
# 4. Verify: Processing completes within 2 minutes
```

## SUCCESS CRITERIA

### ✅ Container Running
- `docker ps` shows hermes_audio with "Up X minutes" status
- No restart loops or exit codes

### ✅ Email Connectivity
- Logs show "Checking for new emails..." without errors
- IMAP connection successful to Gmail

### ✅ Processing Pipeline
- Test email triggers audio processing
- Tasks extracted and formatted correctly
- Results delivered within 2 minutes

## ROLLBACK PLAN
```bash
# If deployment fails:
docker-compose down hermes_audio
cp docker-compose.yml.backup docker-compose.yml
docker-compose up -d --build

# If email processing fails:
# Family can still use: cd ~/Projects/demestihas-ai && ./process_audio.sh
```

## FAMILY COMMUNICATION

### Upon Successful Verification:
```
🎉 Email audio processing is now live!

Send your audio files to: hermesaudio444@gmail.com
Just attach your voice memos to an email and send - tasks will automatically appear in Notion within 2 minutes.

This works from any device, any email app. Zero learning curve! 📧✨
```

### If Verification Fails:
```
Audio processing available via: cd ~/Projects/demestihas-ai && ./process_audio.sh
Email processing coming soon - technical fix in progress.
```

## DEPLOYMENT SUCCESS MARKERS
1. Container shows healthy status within 5 minutes
2. Email polling works without network errors within 10 minutes
3. Test email processes successfully within 2 hours
4. Family notification sent upon verification

**DEPLOYMENT WINDOW**: Execute immediately, verify within 2 hours
**SUCCESS THRESHOLD**: 95% - If any step fails, execute rollback and notify PM

---

**Note**: This deployment unlocks the most intuitive interface for family audio processing. Email is universal and requires zero learning curve.
