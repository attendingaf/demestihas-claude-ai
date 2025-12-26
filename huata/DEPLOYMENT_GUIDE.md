# Huata Calendar Integration - Deployment Guide

## 🎯 What Was Fixed

1. **Credentials Path Issue** ✅
   - Changed from hardcoded `/root/` path to environment-aware `/app/` path
   - Added environment variable support: `GOOGLE_CREDENTIALS_PATH`

2. **Enhanced Debug Logging** ✅
   - Added detailed credential checking with file existence verification
   - Shows which service account is being used
   - Tests connection to Google Calendar on startup

3. **Claude Desktop Interface** ✅
   - Created `claude_interface.py` for simple command-line access
   - No need for complex Python imports or async handling
   - Clean JSON output for easy parsing

4. **Docker Integration** ✅
   - Added `huata` alias in container for quick access
   - Made interface script executable
   - Proper volume mounting for credentials

## 📦 Deployment Steps

### Step 1: Verify Setup
```bash
cd ~/Projects/demestihas-ai/huata
python3 verify_setup.py
```

### Step 2: Deploy with Docker
```bash
# Stop any existing containers
docker-compose down

# Rebuild with all fixes
docker-compose build --no-cache huata

# Start services
docker-compose up -d

# Wait for initialization
sleep 10

# Check logs for connection status
docker logs huata-calendar-agent --tail 50
```

### Step 3: Verify Google Calendar Connection
```bash
# Should show "✅ Google Calendar connected" if successful
docker exec huata-calendar-agent python claude_interface.py check
```

## 🧪 Testing Commands

### Check Connection Status
```bash
docker exec huata-calendar-agent python claude_interface.py check
```

### Query Calendar (Natural Language)
```bash
docker exec huata-calendar-agent python claude_interface.py query --text "What's on my calendar today?"
docker exec huata-calendar-agent python claude_interface.py query --text "Am I free tomorrow at 2pm?"
docker exec huata-calendar-agent python claude_interface.py query --text "What meetings do I have this week?"
```

### List Events for Specific Date
```bash
docker exec huata-calendar-agent python claude_interface.py list --date 2025-09-19
```

### Schedule New Event
```bash
docker exec huata-calendar-agent python claude_interface.py schedule \
  --title "Team Meeting" \
  --date "2025-09-20" \
  --time "14:00" \
  --duration 60
```

## 🔍 Troubleshooting

### Check Container Logs
```bash
# Full logs
docker logs huata-calendar-agent

# Just connection status
docker logs huata-calendar-agent | grep -E "(Google Calendar|credentials|✅|❌)"
```

### Verify Credentials File
```bash
# Check if credentials are mounted correctly
docker exec huata-calendar-agent ls -la /app/credentials/

# Check credentials content (be careful not to expose secrets)
docker exec huata-calendar-agent python -c "import json; f=open('/app/credentials/huata-service-account.json'); d=json.load(f); print('Service account:', d.get('client_email', 'Not found'))"
```

### Test Inside Container
```bash
# Get shell access
docker exec -it huata-calendar-agent bash

# Run Python to test imports
python
>>> from calendar_tools import GoogleCalendarAPI
>>> api = GoogleCalendarAPI()
>>> print("Service available:", api.service is not None)
```

## 📊 Expected Output

### Successful Connection
```
🔍 Checking for credentials at: /app/credentials/huata-service-account.json
✅ Found credentials file
✅ Credentials valid for: huata-agent@your-project.iam.gserviceaccount.com
✅ Google Calendar connected! Found 1 calendars
```

### Mock Mode (No Credentials)
```
🔍 Checking for credentials at: /app/credentials/huata-service-account.json
❌ Credentials not found at /app/credentials/huata-service-account.json
📁 Directory contents: []
```

## 🚀 Quick Deployment Script

Run this all-in-one command:
```bash
bash test_fixes.sh
```

## 🔌 Integration with Claude Desktop

In Claude Desktop, you can now call Huata like this:

```python
import subprocess
import json

# Query calendar
result = subprocess.run(
    ['docker', 'exec', 'huata-calendar-agent', 'python', 'claude_interface.py', 'query', '--text', 'What is on my calendar today?'],
    capture_output=True,
    text=True
)
calendar_data = json.loads(result.stdout)

# Schedule event
result = subprocess.run(
    ['docker', 'exec', 'huata-calendar-agent', 'python', 'claude_interface.py', 'schedule',
     '--title', 'Deep Work Session',
     '--date', '2025-09-20',
     '--time', '09:00',
     '--duration', '120'],
    capture_output=True,
    text=True
)
event_data = json.loads(result.stdout)
```

## ✅ Success Criteria Checklist

- [ ] Container starts without errors
- [ ] Logs show "✅ Google Calendar connected"
- [ ] `check` command returns "✅ Google Calendar connected"
- [ ] `query` command returns real calendar events (not mock data)
- [ ] `schedule` command creates actual calendar entries
- [ ] Events appear in your Google Calendar

## 📝 Notes

- The service account needs to be shared with your calendar
- Calendar ID defaults to 'primary' but can be changed
- All times are in America/New_York timezone (configurable)
- Mock mode activates automatically if credentials are missing