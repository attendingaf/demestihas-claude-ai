# Handoff #015: Complete Hermes Audio Setup
## Thread Continuation from PM Thread #14

**Created**: August 25, 2025, 17:00 UTC
**Type**: Implementation Completion
**Priority**: IMMEDIATE - User actively waiting
**Estimated Time**: 15 minutes
**Current Status**: 90% Complete - Just needs container start

---

## 🎯 Current State

### What's Been Done (Thread #14):
1. ✅ Gmail account created: `hermesaudio444@gmail.com`
2. ✅ Password configured: `ahd5egm2gvf!akr9UPY`
3. ✅ Environment variables added to VPS `.env`:
   - HERMES_EMAIL_ADDRESS
   - HERMES_EMAIL_PASSWORD
   - EMAIL_IMAP_SERVER
   - EMAIL_IMAP_PORT
   - LYCO_API_URL
4. ✅ Clean `docker-compose.yml` created locally and pushed to VPS
5. ✅ Hermes service properly added to docker-compose.yml

### What's Left to Do:
1. ⏳ Build and start Hermes container on VPS
2. ⏳ Verify container is running
3. ⏳ Test with actual audio email
4. ⏳ Verify transcript processing

---

## 📍 Where We Are

### Terminal State:
- **Terminal 1**: SSH'd into VPS at `root@178.156.170.161`
- **Terminal 2**: Local terminal (used for scp)
- **Current Directory**: `/root/lyco-ai/` on VPS
- **Last Command**: Successfully copied docker-compose.yml to VPS

### File Status:
- **docker-compose.yml**: Clean version with Hermes service (verified on VPS)
- **hermes_audio_processor.py**: Already on VPS at `/root/lyco-ai/hermes_audio/`
- **Dockerfile.audio**: Should exist (used by audio_workflow)
- **.env**: Updated with all Hermes credentials

---

## 🚀 Immediate Next Steps

### Step 1: Build and Start Hermes Container
```bash
# On VPS (Terminal 1 - already SSH'd in)
cd /root/lyco-ai

# Build and start the Hermes container
docker-compose up -d --build hermes_audio

# Expected output:
# Building hermes_audio...
# Successfully built [image_id]
# Creating hermes_audio ... done
```

### Step 2: Verify Container Running
```bash
# Check container status
docker ps | grep hermes

# Check logs for successful startup
docker logs hermes_audio --tail 50

# Expected in logs:
# "Starting Hermes Audio Processor..."
# "Connected to email server successfully"
# "Monitoring hermesaudio444@gmail.com for audio files..."
```

### Step 3: Test Email Processing
```bash
# From your phone or computer:
1. Record a 30-second voice memo
2. Email to: hermesaudio444@gmail.com
3. Subject: "Test audio"

# Monitor logs on VPS:
docker logs hermes_audio -f

# Expected sequence:
# "Found 1 new email(s)"
# "Processing audio attachment: [filename]"
# "Compressing audio..."
# "Transcribing with Whisper API..."
# "Formatting transcript..."
# "Analyzing with Claude..."
# "Sending response email..."
```

### Step 4: Verify End-to-End
```bash
# Check your email for:
1. Reply from Hermes with transcript
2. Analysis with 5 key points

# Check Notion for:
1. New tasks created from audio content
2. Proper categorization (Eisenhower matrix)
```

---

## 🔧 Troubleshooting Guide

### If Container Won't Start:
```bash
# Check for port conflicts
docker ps -a

# Check Dockerfile.audio exists
ls -la Dockerfile.audio

# View detailed error
docker-compose logs hermes_audio
```

### If Email Connection Fails:
```bash
# Verify credentials in .env
grep HERMES .env

# Test email manually
python3 -c "
import imaplib
imap = imaplib.IMAP4_SSL('imap.gmail.com')
imap.login('hermesaudio444@gmail.com', 'ahd5egm2gvf!akr9UPY')
print('Success!')
"
```

### If Audio Processing Fails:
```bash
# Check API keys
grep -E 'OPENAI|ANTHROPIC' .env

# Check audio workflow components
ls -la audio_workflow/

# Test Whisper API
curl https://api.openai.com/v1/audio/transcriptions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -F model="whisper-1" \
  -F file="@test.mp3"
```

---

## ✅ Success Criteria

1. **Container Running**: `docker ps` shows hermes_audio container
2. **Email Connected**: Logs show "Connected to email server"
3. **Audio Processed**: Test audio email returns transcript
4. **Tasks Created**: Notion shows new tasks from audio
5. **Response Time**: Complete processing in <5 minutes

---

## 📊 Rollback Plan

If anything fails:
```bash
# Stop Hermes (leaves other services running)
docker-compose stop hermes_audio

# Remove container
docker-compose rm hermes_audio

# Revert docker-compose.yml if needed
cp docker-compose.broken docker-compose.yml

# Continue using Google Drive workflow
docker logs audio_workflow -f
```

---

## 📝 Important Context

### Lessons Learned (Thread #14):
1. **Always edit locally**: Use Cursor IDE, not nano on VPS
2. **Use scp for deployment**: Edit locally, push to VPS
3. **Open new terminals**: Can't scp from within SSH session
4. **Keep backups**: Always backup files before changes
5. **Use sed for simple edits**: Better than nano for small changes
6. **Python for complex operations**: Like YAML editing

### Current Architecture:
- **Hermes**: Email ingestion and audio processing
- **Lyco**: Task management and Notion integration
- **Audio Workflow**: Shared processing components
- **Redis**: Shared data store

### Gmail Setup:
- **Email**: hermesaudio444@gmail.com
- **App Password**: Already configured (not regular password)
- **IMAP**: Enabled by default for Gmail

---

## 🎯 Next Thread Actions

1. **Start this thread** by running docker-compose command
2. **Monitor logs** for successful startup
3. **Test with audio** email immediately
4. **Document results** in thread_log.md
5. **Update current_state.md** with Hermes operational status

---

## 🚨 IMPORTANT NOTES

- **Don't create new Gmail**: Already done (hermesaudio444@gmail.com)
- **Don't edit on VPS**: docker-compose.yml already fixed and uploaded
- **Don't worry about Google Drive**: Hermes is separate/better solution
- **Keep old bot running**: This doesn't affect current Telegram bot

---

**Thread Handoff**: Ready for immediate execution. Container should start in <1 minute.

**Success looks like**: 
```
You: [Email audio to hermesaudio444@gmail.com]
Hermes: [Returns transcript in 3-5 minutes]
Notion: [Shows new tasks from audio content]
Family: "This is amazing!"
```