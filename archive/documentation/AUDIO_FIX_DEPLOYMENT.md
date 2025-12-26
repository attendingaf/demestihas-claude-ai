# Audio File Detection Fix - Deployment Instructions

**Thread**: #008 (Dev-Sonnet Implementation)  
**Date**: 2025-08-24T10:15:00Z  
**Files Modified**: 2 files  
**Estimated Deployment Time**: 10 minutes  

## Changes Made

### 1. google_drive_monitor.py
**Fixed `check_for_new_files()` method**:
- Added fallback MIME type: `application/octet-stream` for unrecognized audio files
- Added shared drive support flags: `supportsAllDrives=True`, `includeItemsFromAllDrives=True`
- Enhanced debug logging to show exact query and file details
- Added `trashed = false` filter for completeness

**Added `check_all_files()` method**:
- Debug method to list ALL files in folder (no time restriction)
- Uses same enhanced query and shared drive support
- Helps identify permission/sharing issues

### 2. workflow.py
**Enhanced startup sequence**:
- Added initial folder scan on startup
- Logs all files found in the Audio Processing folder
- Helps debug file visibility issues immediately

## VPS Deployment Steps

### Step 1: Upload Modified Files
```bash
# From local machine
scp ~/Projects/demestihas-ai/audio_workflow/google_drive_monitor.py root@178.156.170.161:/root/lyco-ai/audio_workflow/
scp ~/Projects/demestihas-ai/audio_workflow/workflow.py root@178.156.170.161:/root/lyco-ai/audio_workflow/
```

### Step 2: Rebuild Container
```bash
# SSH to VPS
ssh root@178.156.170.161
cd /root/lyco-ai/

# Rebuild the audio workflow container
docker-compose -f docker-compose.yml build audio_workflow

# Restart the container
docker-compose -f docker-compose.yml up -d audio_workflow
```

### Step 3: Monitor Logs
```bash
# Watch logs for the fix in action
docker logs -f audio_workflow

# Look for these key log lines:
# "Performing initial folder scan..."
# "Debug search query: '1yqOmzpnOSYTZjdlbfSYTGii4Ne9P3YsR' in parents..."
# "Found X total files in Audio Processing folder"
# "  - Audio_08_22_2025_17_33_59.mp3 (ID: 1eofNOGbiyqux05qrWQ4CxxmbNvzGVUzA..."
```

## Success Tests

### Test 1: Verify Enhanced Query
```bash
docker logs audio_workflow --tail 20 | grep "Debug search query"
```
**Expected**: Should show folder-scoped query with fallback MIME types

### Test 2: Check Existing File Detection
```bash
docker logs audio_workflow --tail 50 | grep "Audio_08_22_2025"
```
**Expected**: Should show the test file being detected

### Test 3: Verify Shared Drive Support
```bash
docker logs audio_workflow --tail 30 | grep "supportsAllDrives"
```
**Expected**: No errors related to shared drives

### Test 4: End-to-End Test
1. Upload a new audio file to the Audio Processing folder
2. Wait 5 minutes (polling interval)
3. Check for processing activity in logs
4. Verify file appears in 01_compressed folder

## Rollback Plan

If the container fails to start or errors occur:

```bash
# SSH to VPS
ssh root@178.156.170.161
cd /root/lyco-ai/

# Check container status
docker ps -a | grep audio_workflow

# If container is failing, rollback
git checkout HEAD~1 audio_workflow/google_drive_monitor.py
git checkout HEAD~1 audio_workflow/workflow.py

# Rebuild with previous version
docker-compose -f docker-compose.yml build audio_workflow
docker-compose -f docker-compose.yml up -d audio_workflow
```

## Technical Details

### Query Changes
**Before**:
```
'{folder_id}' in parents and mimeType contains 'audio/' and modifiedTime > '{last_check}'
```

**After**:
```
'{folder_id}' in parents and (mimeType contains 'audio' or mimeType = 'application/octet-stream') and modifiedTime > '{last_check}' and trashed = false
```

### Added Parameters
```python
supportsAllDrives=True,
includeItemsFromAllDrives=True
```

### Debug Logging Added
- Exact query being used
- Number of files found
- Individual file details (name, ID, MIME type)
- Initial folder scan on startup

## Expected Outcomes

1. **Immediate**: Container starts successfully with enhanced logging
2. **Within 5 minutes**: Test file `Audio_08_22_2025_17_33_59.mp3` should be detected
3. **Within 10 minutes**: File should begin processing through the pipeline
4. **Within 15 minutes**: Compressed version should appear in `01_compressed` folder

## Next Steps

If this fix resolves the issue:
- Update current_state.md to mark Audio Workflow as "OPERATIONAL"
- Remove "Current Blocker" note
- Add thread log entry with success details

If this doesn't resolve the issue:
- Review logs for permission errors
- Consider OAuth2 implementation as fallback
- Escalate to PM for service account permission review

## Notes

- All changes maintain backward compatibility
- No breaking changes to existing functionality
- Enhanced logging helps with future debugging
- Shared drive support future-proofs the implementation
