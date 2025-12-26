# Handoff #008: Fix Audio File Detection Query

**Thread Type**: Dev-Sonnet Implementation
**Created**: 2025-08-24T09:45:00Z  
**Priority**: IMMEDIATE - Family Blocked
**Estimated Time**: 30 minutes
**Atomic Scope**: Fix Google Drive search query to detect audio files

---

## 🎯 SINGLE DELIVERABLE

Modify the Google Drive search query in `google_drive_monitor.py` to properly detect audio files in the Audio Processing folder.

---

## 📋 CONTEXT

**Current State**: 
- Audio workflow container running on VPS
- Service account authenticated successfully
- Files uploaded to folder but NOT detected
- Folder ID: `1yqOmzpnOSYTZjdlbfSYTGii4Ne9P3YsR`

**Problem**: Search query is unscoped, looking across entire Drive instead of specific folder

---

## 🔧 IMPLEMENTATION STEPS

### Step 1: SSH to VPS
```bash
ssh root@178.156.170.161
cd /root/lyco-ai/audio_workflow
```

### Step 2: Modify google_drive_monitor.py

**FIND** (around line 35-40):
```python
# List audio files
results = self.service.files().list(
    q="mimeType contains 'audio' and trashed = false",
    pageSize=10,
    fields="nextPageToken, files(id, name, mimeType, modifiedTime)"
).execute()
```

**REPLACE WITH**:
```python
# List audio files in the specific folder
folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
results = self.service.files().list(
    q=f"'{folder_id}' in parents and (mimeType contains 'audio' or mimeType = 'application/octet-stream') and trashed = false",
    pageSize=10,
    fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
    supportsAllDrives=True,
    includeItemsFromAllDrives=True
).execute()
```

**Changes Made**:
1. Added folder scope: `'{folder_id}' in parents`
2. Added fallback MIME type for unrecognized audio
3. Added shared drive support flags

### Step 3: Add Debug Logging

**ADD** after the results line:
```python
# Debug logging
files = results.get('files', [])
logger.info(f"Search query: '{folder_id}' in parents and (mimeType contains 'audio' or mimeType = 'application/octet-stream') and trashed = false")
logger.info(f"Found {len(files)} files in Audio Processing folder")
if files:
    for file in files:
        logger.info(f"  - {file['name']} (ID: {file['id']}, Type: {file['mimeType']})")
```

### Step 4: Rebuild and Restart Container
```bash
# Rebuild the container with changes
docker-compose -f docker-compose.yml build audio_workflow

# Restart the container
docker-compose -f docker-compose.yml up -d audio_workflow

# Watch logs to verify
docker logs -f audio_workflow
```

---

## ✅ SUCCESS TEST

```bash
# Test 1: Verify query change in logs
docker logs audio_workflow --tail 20 | grep "Search query"
# Should show: "Search query: '1yqOmzpnOSYTZjdlbfSYTGii4Ne9P3YsR' in parents..."

# Test 2: Check if test file is detected
docker logs audio_workflow --tail 50 | grep "Audio_08_22_2025"
# Should show: "- Audio_08_22_2025_17_33_59.mp3 (ID: 1eofNOGbiyqux05qrWQ4CxxmbNvzGVUzA..."

# Test 3: End-to-end processing
# Upload a new test audio file to the folder and wait 5 minutes
# Check for compressed file in 01_compressed folder
```

---

## 🔄 ROLLBACK PLAN

If the fix breaks the container:
```bash
# Restore original code
cd /root/lyco-ai/audio_workflow
git checkout google_drive_monitor.py

# Restart container
docker-compose -f docker-compose.yml restart audio_workflow
```

---

## 📊 REPORTING

After implementation:
1. Update `current_state.md`:
   - Change Audio Workflow Status from "NEEDS FINAL CONFIG" to "OPERATIONAL"
   - Remove "Current Blocker" note
   
2. Add to `thread_log.md`:
   ```markdown
   ## Thread #008 (Dev-Sonnet) - Fix Audio File Detection
   **Date**: [timestamp]
   **Duration**: [actual time]
   **Outcome**: Success/Failed
   **Changes**: Fixed Google Drive search query to be folder-scoped
   **Test Results**: [File detection working/not working]
   **Next Thread**: [If failed, what's next approach]
   ```

---

## ⚠️ ESCALATION

If this doesn't work after implementation:
1. The service account may need different permissions
2. Consider Phase 2: OAuth2 implementation
3. Alert PM for strategic decision on authentication approach

**Success Criteria**: Test audio file is detected and processed within 5 minutes