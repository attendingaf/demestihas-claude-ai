# Handoff 020: Audio Workflow Diagnostic & Status Verification

## THREAD: Developer Thread #020 (Sonnet)
**ATOMIC SCOPE:** Verify and fix Google Drive folder monitoring for audio processing
**TIME ESTIMATE:** 30 minutes
**PRIORITY:** HIGH - User expects folder-based processing to work

## Context

**User Question**: "Is the Hermes workflow successfully pulling audio files dropped in a certain folder?"

**Current Status Uncertainty**:
- Thread #008 claimed to fix Google Drive file detection
- Current state shows "file detection still problematic"
- Docker-compose shows `audio_workflow` container should be running
- Family may be dropping files expecting automatic processing

**Expected Behavior**:
Files dropped in Google Drive folder → Auto-detected → Transcribed → Tasks created

## Implementation Steps

### Step 1: Check Container Status (5 minutes)

```bash
# SSH to VPS
ssh root@178.156.170.161

# Check what containers are actually running
docker ps

# Check if audio_workflow container exists
docker ps -a | grep audio_workflow

# If running, check logs
docker logs audio_workflow --tail 50

# If not running, check why
docker logs audio_workflow --tail 100
```

### Step 2: Verify Google Drive Integration (10 minutes)

```bash
# Check if credentials file exists
ls -la /root/lyco-ai/credentials/

# Test Google Drive API access
docker exec audio_workflow python -c "
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

creds = service_account.Credentials.from_service_account_file(
    '/app/credentials/google-service-account.json'
)
service = build('drive', 'v3', credentials=creds)
folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
print(f'Testing access to folder: {folder_id}')

results = service.files().list(
    q=f\"'{folder_id}' in parents\",
    pageSize=10
).execute()

files = results.get('files', [])
print(f'Found {len(files)} files in folder')
for file in files:
    print(f'- {file[\"name\"]} ({file[\"mimeType\"]})')
"

# Check environment variables
docker exec audio_workflow printenv | grep -E "(GOOGLE|DRIVE|AUDIO)"
```

### Step 3: Fix Issues