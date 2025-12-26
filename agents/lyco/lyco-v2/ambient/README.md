# Lyco 2.0 - Ambient Signal Capture

Phase 2 implementation that automates signal collection from Gmail and Google Calendar, eliminating manual task creation.

## 🎯 What It Does

- **Email Monitoring**: Captures commitments from sent emails and requests from received emails
- **Calendar Prep**: Generates preparation tasks for upcoming meetings
- **5-Minute Cycles**: Runs continuously, checking for new signals every 5 minutes
- **Smart Deduplication**: Prevents duplicate signals using 24-hour cache
- **Energy Classification**: Auto-assigns energy levels based on content and time

## 📋 Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Google APIs

Run the setup script to configure Gmail and Calendar access:

```bash
python setup_google_auth.py
```

Follow the instructions to:
1. Enable Gmail API and Calendar API in Google Cloud Console
2. Create OAuth 2.0 credentials
3. Save credentials to `credentials/` directory

### 3. Test Components

Run the test suite to verify everything works:

```bash
python test_ambient.py
```

### 4. Run Ambient Capture

**Local Development:**
```bash
python ambient/ambient_capture.py
```

**Docker Deployment:**
```bash
docker-compose up -d lyco-ambient-capture
```

## 🔍 How It Works

### Email Signal Detection

Looks for commitment patterns in your sent emails:
- "I will..." / "I'll..."
- "Let me..." / "I can..."
- "By [date]" / "Before [time]"
- Action verbs: send, review, prepare, schedule, call

And request patterns in received emails:
- "Can you..." / "Could you..."
- "Please..." / "Need you to..."
- Questions that imply requests

### Calendar Signal Generation

Creates prep tasks for:
- **Board meetings** → "Review board deck and quarterly metrics"
- **Interviews** → "Review candidate resume and prepare questions"
- **1:1s** → "Review notes and prepare agenda"
- **Large meetings** (>3 attendees) → "Prepare agenda and materials"
- **Recurring meetings** → "Review notes for meeting"

### Energy Level Assignment

Content-based classification:
- **High Energy**: strategic, planning, design, create, analyze
- **Medium Energy**: review, meeting, email, respond, discuss
- **Low Energy**: read, organize, file, document, note

Falls back to time-based defaults:
- 9-11am → High
- 2-4pm → Medium
- After 4pm → Low

## 📊 Monitoring

### Check Logs

**Docker:**
```bash
docker-compose logs -f lyco-ambient-capture
```

**Local:**
Check console output for capture cycle status

### Redis Monitoring

Monitor real-time events:
```bash
redis-cli monitor | grep lyco:
```

Subscribe to channels:
```bash
redis-cli
> SUBSCRIBE lyco:signal_created lyco:task_ready
```

## 🔧 Configuration

### Email Accounts

Configure in `.env`:
```env
USER_WORK_EMAIL=mene@beltlineconsulting.co
USER_HOME_EMAIL=menelaos4@gmail.com
```

### Calendar IDs

Update in `ambient_capture.py`:
```python
calendar_ids = [
    'primary',  # Main calendar
    'work@company.com',  # Work calendar
    'family_calendar_id@group.calendar.google.com'  # Shared calendar
]
```

### Polling Interval

Default is 5 minutes. To change, edit `ambient_capture.py`:
```python
await asyncio.sleep(300)  # Change 300 to desired seconds
```

## 🚨 Troubleshooting

### "Gmail service not initialized"

1. Run `python setup_google_auth.py`
2. Ensure `credentials/gmail_credentials.json` exists
3. Delete `credentials/gmail_token.json` and re-authenticate

### "Calendar API error"

1. Check calendar ID is correct
2. Ensure calendar is accessible by authenticated account
3. Try with 'primary' calendar first

### Duplicate Signals

- Cache persists for 24 hours
- Check `signal_cache` in logs
- Restart to clear in-memory cache

### No Tasks Created

1. Check LLM processing in logs
2. Verify ANTHROPIC_API_KEY is set
3. Test with manual signal: `python cli.py signal "I'll do this"`

## 📈 Success Metrics

After running for 24 hours, you should see:
- **90%+ commitments captured** from email
- **All meetings with prep tasks** created
- **Zero manual signals needed**
- **Tasks appear within 5 minutes** of email/calendar event

## 🔄 Integration Points

### Redis Channels

**Subscribes to:**
- `pluma:new_email` - Email from Pluma agent
- `huata:new_event` - Calendar from Huata agent
- `yanay:command` - Commands from orchestrator

**Publishes to:**
- `lyco:signal_created` - When new signal created
- `lyco:task_ready` - When tasks are ready
- `lyco:email_to_process` - Email needs processing
- `lyco:calendar_to_process` - Event needs processing

### Database Tables

**Writes to:**
- `task_signals` - Raw signals from reality
- `tasks` - Processed actionable tasks (via processor)

**Reads from:**
- `task_signals` - For deduplication check

## 🎯 Next Steps

Once ambient capture is working:

1. **Monitor capture rate** for first day
2. **Tune patterns** if missing commitments
3. **Add Slack integration** if needed
4. **Reduce polling** to 3 minutes if stable
5. **Add voice capture** for verbal commitments

---

**Phase 2 Complete!** Lyco now captures signals automatically from your reality.