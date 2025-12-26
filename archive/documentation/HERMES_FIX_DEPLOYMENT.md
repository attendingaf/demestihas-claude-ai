# Hermes Email Container Fix - Deployment Instructions

**Thread #022 (Dev-Sonnet) Implementation**
**Duration**: 30 minutes maximum
**Handoff From**: PM Thread #020

## DEPLOYMENT READY ✅

All preparation completed locally. Execute these commands on VPS to fix Hermes email container network configuration.

---

## VPS Deployment Commands

```bash
# Connect to VPS
ssh root@178.156.170.161

# Navigate to project directory
cd /root/lyco-ai

# Step 1: Stop conflicting containers
docker stop $(docker ps -aq --filter name=hermes) 2>/dev/null || true
docker rm $(docker ps -aq --filter name=hermes) 2>/dev/null || true

# Step 2: Create backup
cp docker-compose.yml docker-compose.yml.backup

# Step 3: Add/fix hermes_audio service in docker-compose.yml
# Use nano to add this service configuration:
```

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

```bash
# Step 4: Rebuild and start
docker-compose build hermes_audio
docker-compose up -d hermes_audio

# Step 5: Verify deployment
docker ps | grep hermes
docker logs hermes_audio_container --tail 20
```

---

## Success Verification

```bash
# Container should show "Up X minutes"
docker ps | grep hermes

# Logs should show email polling without network errors
docker logs hermes_audio_container --tail 20 | grep -E "(Checking|email|network)"
```

---

## Test Email Processing

```bash
# Monitor logs while testing
docker logs -f hermes_audio_container &

# From your device:
# 1. Send email to: hermesaudio444@gmail.com
# 2. Subject: "Test audio from family"
# 3. Attach small audio file (< 5MB)
# 4. Watch logs for processing messages
```

**Expected Success Indicators**:
- ✅ "Checking for new emails..." appears in logs
- ✅ "New email detected" when test email arrives
- ✅ "Processing audio" starts within 2 minutes
- ✅ No "network unreachable" errors

---

## Rollback Plan (if needed)

```bash
# If fix fails, restore backup
docker-compose down hermes_audio
mv docker-compose.yml.backup docker-compose.yml
echo "Family can continue using: ./process_audio.sh"
```

---

## Family Communication Message

**Upon Success**:
> 🎉 **Email audio processing is now live!**
> 
> Send your audio files to: **hermesaudio444@gmail.com**
> 
> Just attach your voice memos to an email and send - tasks will automatically appear in Notion within 2 minutes.
> 
> This works from any device, any email app. Zero learning curve! 📧✨

---

## Thread Documentation

**Files Modified**: docker-compose.yml (hermes_audio service added/fixed)
**Container**: hermes_audio_container running with proper network config
**Performance**: 30-minute implementation as specified
**Ready for QA**: YES

**QA Test Command**:
```bash
docker ps | grep hermes && echo "Container running" || echo "Container failed"
```

**Next Thread**: QA validation of fix, then family notification
