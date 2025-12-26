# Handoff #007: Fix Audio Workflow File Detection

**Created**: 2025-08-25T01:30:00Z  
**Priority**: IMMEDIATE  
**Type**: Bug Fix  
**Estimated Time**: 30 minutes  
**Assigned To**: Next PM Session (Opus)

---

## 🎯 Problem Statement

The audio workflow system is **fully functional** but cannot detect uploaded audio files. The processing pipeline works perfectly when files are found:
- ✅ Downloads files
- ✅ Compresses audio (75% reduction)
- ✅ Ready for transcription/analysis

**Blocker**: Service account can't see/access uploaded audio files

---

## 📊 Current System State

### What's Working:
- Container `audio_workflow` running on VPS
- Google Drive authentication successful
- Folder structure created in user's Drive:
  - Audio Processing (ID: 1yqOmzpnOSYTZjdlbfSYTGii4Ne9P3YsR)
  - 01_compressed, 02_chunks, 03_transcripts, 04_formatted, 05_analysis
- Service account has Editor permissions on Audio Processing folder
- Processing pipeline validated and working

### What's Not Working:
- Files uploaded to Audio Processing folder are NOT detected
- Service account can't see files even when directly shared
- Workflow reports "No new audio files found" every 5 minutes

---

## 🔍 Technical Details

### Service Account:
```
Email: transcription-bot@meeting-transcription-467715.iam.gserviceaccount.com
Project: meeting-transcription-467715
Credentials: /root/lyco-ai/credentials/google-service-account.json
```

### Environment Configuration:
```bash
GOOGLE_DRIVE_FOLDER_ID=1yqOmzpnOSYTZjdlbfSYTGii4Ne9P3YsR
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/google-service-account.json
OPENAI_API_KEY=✅ Configured
ANTHROPIC_API_KEY=✅ Configured
```

### Search Query Used:
```python
# Current search in google_drive_monitor.py
q = "mimeType contains 'audio' and trashed = false"
```

---

## 🛠️ Potential Solutions

### Option 1: Fix File Visibility (Recommended)
1. Modify search query to look in specific folder:
```python
q = f"'{folder_id}' in parents and mimeType contains 'audio' and trashed = false"
```

2. Add shared drive support if available

3. Implement OAuth2 flow instead of service account

### Option 2: Change Upload Process
1. Create an "inbox" folder with different permissions
2. Have users share files directly with service account
3. Move processed files to archive

### Option 3: Use Different Authentication
1. Switch from service account to OAuth2
2. Use user delegation
3. Implement impersonation

---

## 📝 Test Files

Test file uploaded but not detected:
- File ID: 1eofNOGbiyqux05qrWQ4CxxmbNvzGVUzA
- Name: Audio_08_22_2025_17_33_59.mp3
- Location: Audio Processing folder
- Shared with: Service account (Viewer)

---

## ✅ Acceptance Criteria

1. Service account can detect audio files uploaded to Audio Processing folder
2. Processing pipeline runs end-to-end:
   - File detected → Downloaded → Compressed → Transcribed → Formatted → Analyzed
3. Results appear in numbered folders within 5 minutes of upload
4. No manual sharing required for each file

---

## 🔧 Quick Commands

```bash
# SSH to VPS
ssh root@178.156.170.161

# Check container status
docker ps | grep audio_workflow

# View logs
docker logs audio_workflow --tail 50

# Restart container
docker restart audio_workflow

# Test file visibility
docker exec audio_workflow python3 -c "
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

creds = service_account.Credentials.from_service_account_file(
    '/app/credentials/google-service-account.json',
    scopes=['https://www.googleapis.com/auth/drive']
)
service = build('drive', 'v3', credentials=creds)

results = service.files().list(
    q=\"mimeType contains 'audio' and trashed = false\",
    pageSize=10
).execute()

files = results.get('files', [])
print(f'Found {len(files)} audio files')
for f in files:
    print(f'  - {f.get(\"name\")}')
"
```

---

## 📚 References

- Google Drive API: https://developers.google.com/drive/api/v3/reference
- Service Account Limitations: https://developers.google.com/drive/api/guides/about-auth
- Shared Drives: https://developers.google.com/drive/api/guides/about-shareddrives

---

## 🎯 Next Steps

1. Debug why service account can't see files
2. Implement solution (likely Option 1)
3. Test with multiple file uploads
4. Document usage instructions for family
5. Create monitoring dashboard

**Success looks like**: Upload audio file → See transcript in 5 minutes