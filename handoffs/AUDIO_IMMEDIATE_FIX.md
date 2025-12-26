# 🚨 IMMEDIATE: Get Audio Workflow Operational

**PM Thread**: #14
**Priority**: BLOCKING - Fix before any new development
**Time Estimate**: 30 minutes
**Created**: August 25, 2025, 15:30 UTC

---

## 🎯 Decision: Use Hermes Email Approach (Simpler)

The Google Drive permission issues are complex. Let's get Hermes email working - it's already deployed and just needs Gmail configuration.

---

## ⚡ Quick Fix Path (15 minutes)

### Step 1: Create Gmail Account (5 minutes)

1. Go to https://accounts.google.com/signup
2. Create account: `hermes.demestihas@gmail.com` (or similar)
3. Enable 2-factor authentication
4. Generate app password:
   - Go to https://myaccount.google.com/apppasswords
   - Select "Mail" 
   - Generate password
   - SAVE THIS PASSWORD

### Step 2: Configure VPS (5 minutes)

```bash
# SSH to VPS
ssh root@178.156.170.161

# Update environment variables
cd /root/lyco-ai
nano .env

# Add these lines:
HERMES_EMAIL_ADDRESS=hermes.demestihas@gmail.com
HERMES_EMAIL_PASSWORD=your-app-password-here
EMAIL_IMAP_SERVER=imap.gmail.com
EMAIL_IMAP_PORT=993

# Save and exit (Ctrl+X, Y, Enter)
```

### Step 3: Start Hermes Container (5 minutes)

```bash
# Check if Hermes files exist
ls -la /root/lyco-ai/hermes_audio/

# If files exist, add to docker-compose.yml:
nano docker-compose.yml

# Add this service:
  hermes:
    build: 
      context: ./hermes_audio
      dockerfile: Dockerfile
    environment:
      - HERMES_EMAIL_ADDRESS=${HERMES_EMAIL_ADDRESS}
      - HERMES_EMAIL_PASSWORD=${HERMES_EMAIL_PASSWORD}
      - EMAIL_IMAP_SERVER=${EMAIL_IMAP_SERVER}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - LYCO_API_URL=http://bot:8000
    volumes:
      - ./hermes_audio/working:/app/working
      - ./logs:/app/logs
    restart: unless-stopped
    depends_on:
      - redis

# Build and start
docker-compose up -d hermes

# Check logs
docker logs lyco-ai-hermes-1 --tail 50
```

---

## 🧪 Test the System

### Send Test Audio:

1. **From your phone**:
   - Record a voice memo (30 seconds)
   - Email to: hermes.demestihas@gmail.com
   - Subject: "Test audio processing"

2. **Watch the logs**:
```bash
docker logs lyco-ai-hermes-1 -f

# You should see:
# "Found 1 new email(s)"
# "Processing audio attachment..."
# "Compressing audio..."
# "Transcribing with Whisper..."
# "Formatting transcript..."
# "Analyzing content..."
```

3. **Check Results**:
   - Transcript and analysis sent back via email
   - Tasks automatically created in Notion

---

## 🔄 Alternative: Fix Google Drive Approach

If email setup fails, verify the Drive fix:

```bash
# Check if Thread #008 fix is deployed
ssh root@178.156.170.161
cd /root/lyco-ai/audio_workflow

# Check the search query in google_drive_monitor.py
grep -n "in parents" google_drive_monitor.py

# Should see:
# q = f"'{self.folder_id}' in parents and (mimeType contains 'audio' or mimeType='application/octet-stream')"

# If NOT present, apply the fix:
nano google_drive_monitor.py
# Find the check_for_new_files method
# Update the query as shown above

# Restart container
docker restart audio_workflow

# Upload test file to Google Drive folder and monitor:
docker logs audio_workflow -f
```

---

## ✅ Success Criteria

ONE of these must work:

**Hermes Email**:
- ✅ Email audio → Get transcript back in 5 minutes
- ✅ Tasks appear in Notion automatically

**Google Drive**:
- ✅ Upload to Audio Processing folder → Files detected
- ✅ Processed files appear in numbered folders

---

## 📊 Which Approach to Prioritize?

**Hermes Email** (Recommended):
- ✅ Simpler permissions (just email)
- ✅ Better family UX (everyone knows email)
- ✅ Works from any device
- ✅ No sharing/permission complexity

**Google Drive** (Fallback):
- ⚠️ Complex permission model
- ⚠️ Service account limitations
- ✅ Good for batch processing
- ✅ Visual folder organization

---

## 🚀 Next Actions

1. **TRY EMAIL FIRST** - Create Gmail account now
2. Configure and test Hermes (15 minutes)
3. If email works → Document for family
4. If email fails → Debug Google Drive approach
5. Once ONE works → Move to Yanay/Lyco split

---

## 📝 Family Instructions (Once Working)

### For Hermes Email:
```
To transcribe audio:
1. Record voice memo on your phone
2. Email to: hermes.demestihas@gmail.com
3. Get transcript + analysis in 5 minutes
4. Tasks automatically appear in Notion
```

### For Google Drive:
```
To transcribe audio:
1. Upload audio file to "Audio Processing" folder
2. Wait 5 minutes
3. Check numbered folders for results
```

---

**PM Decision**: Get Hermes email working first. It's simpler and better UX.

**Your Next Step**: Create the Gmail account and give me the email address. I'll help you configure the rest.