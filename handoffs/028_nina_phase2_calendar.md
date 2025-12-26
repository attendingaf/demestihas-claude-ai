# Handoff #028: Nina Agent Phase 2 - Google Calendar Integration

## THREAD: Developer Thread #028
**ATOMIC SCOPE**: Add Google Calendar integration to Nina for automatic conflict detection and visual schedule representation

## CONTEXT

### Current State
- **Version**: v7.1-nina-phase1 (Au Pair Scheduling Active)
- **Nina Phase 1**: ✅ COMPLETE - Schedule state management working
- **Redis Storage**: Baseline schedules, exceptions, comp time all functional
- **Gap Detection**: Automatic coverage task creation working
- **Natural Language**: Date/time parsing operational

### Phase 1 Capabilities (Working)
```python
# Current commands that work:
"Viola has Thursday off"           # Marks exception
"Need coverage tomorrow 3-5pm"     # Creates coverage request
"What's Viola's schedule?"        # Shows weekly view
"Viola worked extra 3 hours"      # Tracks comp time
```

### Phase 2 Goals
- Visual calendar representation of Viola's schedule
- Automatic conflict detection with family events
- Proactive gap alerts based on calendar analysis
- Integration with existing Huata (when available) or direct GCal API

## IMPLEMENTATION

### Step 1: Add Google Calendar API Setup (15 min)

**File**: `/root/lyco-ai/nina.py`

Add Google Calendar imports and initialization:
```python
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os

class NinaSchedulingAgent:
    def __init__(self, redis_client=None, lyco_agent=None):
        # ... existing init code ...
        
        # Initialize Google Calendar
        self.calendar_service = None
        self.viola_calendar_id = None
        self.family_calendar_id = 'primary'
        self._init_calendar()
    
    def _init_calendar(self):
        """Initialize Google Calendar API connection"""
        try:
            creds_path = os.getenv('GOOGLE_CALENDAR_CREDS_PATH', '/root/lyco-ai/credentials/gcal_service_account.json')
            if os.path.exists(creds_path):
                creds = service_account.Credentials.from_service_account_file(
                    creds_path,
                    scopes=['https://www.googleapis.com/auth/calendar']
                )
                self.calendar_service = build('calendar', 'v3', credentials=creds)
                
                # Find or create Viola's calendar
                self._setup_viola_calendar()
        except Exception as e:
            logger.warning(f"Google Calendar initialization failed: {e}")
            # Continue without calendar - graceful degradation
```

### Step 2: Create Viola's Calendar Management (20 min)

Add methods to manage Viola's dedicated calendar:
```python
def _setup_viola_calendar(self):
    """Find or create a calendar for Viola's schedule"""
    try:
        # List all calendars
        calendars = self.calendar_service.calendarList().list().execute()
        
        # Look for Viola's calendar
        for cal in calendars.get('items', []):
            if cal.get('summary') == 'Viola Schedule':
                self.viola_calendar_id = cal['id']
                return
        
        # Create if not found
        viola_calendar = {
            'summary': 'Viola Schedule',
            'description': 'Au pair work schedule and availability',
            'timeZone': 'America/New_York'
        }
        created = self.calendar_service.calendars().insert(body=viola_calendar).execute()
        self.viola_calendar_id = created['id']
        
        # Share with family members
        self._share_calendar_with_family()
        
    except Exception as e:
        logger.error(f"Failed to setup Viola calendar: {e}")

def sync_schedule_to_calendar(self, week_offset=0):
    """Sync Redis schedule state to Google Calendar"""
    if not self.calendar_service or not self.viola_calendar_id:
        return "Calendar sync not available"
    
    try:
        # Get the week's schedule from Redis
        schedule = self.get_weekly_schedule(week_offset)
        
        # Clear existing events for this week (to avoid duplicates)
        self._clear_week_events(week_offset)
        
        # Create calendar events for each work day
        for day_info in schedule:
            if day_info['working']:
                event = {
                    'summary': f"Viola Working: {day_info['hours']}",
                    'start': {
                        'dateTime': day_info['start_datetime'],
                        'timeZone': 'America/New_York',
                    },
                    'end': {
                        'dateTime': day_info['end_datetime'],
                        'timeZone': 'America/New_York',
                    },
                    'description': 'Au pair on duty',
                    'colorId': '2'  # Green for working
                }
            else:
                # Mark as unavailable
                event = {
                    'summary': 'Viola Off',
                    'start': {'date': day_info['date']},
                    'end': {'date': day_info['date']},
                    'description': day_info.get('reason', 'Scheduled day off'),
                    'colorId': '11'  # Red for off
                }
            
            self.calendar_service.events().insert(
                calendarId=self.viola_calendar_id,
                body=event
            ).execute()
        
        return "✅ Calendar synced successfully"
        
    except Exception as e:
        logger.error(f"Calendar sync failed: {e}")
        return f"⚠️ Calendar sync failed: {str(e)}"
```

### Step 3: Add Conflict Detection (20 min)

Implement automatic conflict detection with family calendar:
```python
def check_calendar_conflicts(self, date, time_range=None):
    """Check for conflicts between Viola's schedule and family events"""
    if not self.calendar_service:
        return []
    
    conflicts = []
    
    try:
        # Parse the date and time range
        target_date = self._parse_date(date)
        
        # Set time bounds for the query
        if time_range:
            start_time, end_time = self._parse_time_range(time_range)
            time_min = f"{target_date}T{start_time}:00-04:00"
            time_max = f"{target_date}T{end_time}:00-04:00"
        else:
            time_min = f"{target_date}T00:00:00-04:00"
            time_max = f"{target_date}T23:59:59-04:00"
        
        # Check family calendar for events needing childcare
        family_events = self.calendar_service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        for event in family_events.get('items', []):
            summary = event.get('summary', '').lower()
            
            # Detect events that need childcare
            childcare_keywords = ['date night', 'dinner', 'meeting', 'appointment', 
                                 'work', 'conference', 'travel', 'out']
            
            if any(keyword in summary for keyword in childcare_keywords):
                # Check if Viola is available
                viola_available = self._check_viola_availability(target_date, event)
                
                if not viola_available:
                    conflicts.append({
                        'event': event.get('summary'),
                        'time': event.get('start', {}).get('dateTime', 'All day'),
                        'conflict': 'Viola unavailable - coverage needed'
                    })
        
        return conflicts
        
    except Exception as e:
        logger.error(f"Conflict detection failed: {e}")
        return []

def proactive_gap_detection(self):
    """Scan next 2 weeks for potential coverage gaps"""
    if not self.calendar_service:
        return "Calendar integration not available"
    
    gaps = []
    
    try:
        # Check next 14 days
        for day_offset in range(14):
            target_date = (datetime.now() + timedelta(days=day_offset)).strftime('%Y-%m-%d')
            
            # Get Viola's schedule for that day
            viola_working = self._is_viola_working(target_date)
            
            # Get family events requiring childcare
            family_needs = self._get_childcare_needs(target_date)
            
            # Detect gaps
            for need in family_needs:
                if not viola_working:
                    gaps.append({
                        'date': target_date,
                        'event': need['event'],
                        'time': need['time'],
                        'action': 'Need to arrange coverage'
                    })
        
        # Create tasks for gaps
        if gaps and self.lyco_agent:
            for gap in gaps:
                task_text = f"Find childcare coverage for {gap['date']} - {gap['event']} at {gap['time']}"
                self.lyco_agent.create_task({
                    'text': task_text,
                    'priority': 'urgent',
                    'due_date': gap['date']
                })
        
        return f"Detected {len(gaps)} coverage gaps, tasks created" if gaps else "No gaps detected"
        
    except Exception as e:
        logger.error(f"Gap detection failed: {e}")
        return "Gap detection encountered an error"
```

### Step 4: Update Yanay Integration (10 min)

**File**: `/root/lyco-ai/yanay.py`

Add new calendar-aware commands:
```python
# In process_schedule_command method, add:

elif 'sync' in command_lower and 'calendar' in command_lower:
    # Sync schedule to Google Calendar
    result = self.nina.sync_schedule_to_calendar()
    return result

elif 'conflict' in command_lower or 'check calendar' in command_lower:
    # Check for calendar conflicts
    # Extract date from command
    date = self._extract_date_from_command(command)
    conflicts = self.nina.check_calendar_conflicts(date)
    
    if conflicts:
        response = "⚠️ Calendar conflicts detected:\n"
        for conflict in conflicts:
            response += f"• {conflict['event']} at {conflict['time']}: {conflict['conflict']}\n"
        return response
    else:
        return "✅ No calendar conflicts found"

elif 'gap' in command_lower or 'coverage check' in command_lower:
    # Run proactive gap detection
    result = self.nina.proactive_gap_detection()
    return result
```

### Step 5: Environment Configuration (5 min)

Add to `.env`:
```bash
GOOGLE_CALENDAR_CREDS_PATH=/root/lyco-ai/credentials/gcal_service_account.json
VIOLA_CALENDAR_NAME=Viola Schedule
FAMILY_CALENDAR_ID=primary
```

### Step 6: Testing Protocol (15 min)

Run these tests via Telegram:

```bash
# 1. Test calendar sync
"Sync Viola's schedule to calendar"
# Verify: Check Google Calendar for Viola's schedule

# 2. Test conflict detection  
"Viola has Friday off"
"Check calendar conflicts for Friday"
# Verify: Should detect any family events needing coverage

# 3. Test proactive gaps
"Check for coverage gaps"
# Verify: Should scan 2 weeks and create tasks

# 4. Test visual schedule
"Show Viola's calendar"
# Verify: Returns link to Viola's Google Calendar
```

## SUCCESS CRITERIA

1. **Calendar Creation**: Viola's calendar created and shared with family
2. **Schedule Sync**: Redis schedule state visible in Google Calendar
3. **Conflict Detection**: Family events checked against Viola's availability
4. **Gap Alerts**: Proactive tasks created for coverage needs
5. **Performance**: All operations complete in <3 seconds

## ROLLBACK PLAN

If calendar integration causes issues:

1. **Disable calendar features**:
```python
# In nina.py __init__:
self.calendar_enabled = False  # Add flag
```

2. **Continue with Phase 1 features** - Nina works without calendar

3. **Debug offline** - Check logs for API errors

4. **Gradual re-enable** - Test with single family member first

## ERROR HANDLING

```python
# Wrap all calendar operations:
try:
    # Calendar operation
except Exception as e:
    logger.error(f"Calendar operation failed: {e}")
    # Continue without calendar - graceful degradation
    return "Calendar feature temporarily unavailable, schedule tracked in system"
```

## REPORTING

After implementation, update:

**current_state.md**:
- Version: v7.2-nina-phase2
- New feature: Google Calendar integration active
- Status: Visual schedule representation working

**thread_log.md**:
- Add Thread #031 entry
- Document calendar sync success
- Note any issues encountered

## DEPENDENCIES

- Google Calendar API credentials (service account)
- google-api-python-client library
- Existing Nina Phase 1 implementation
- Redis for state management
- Lyco agent for task creation

## ESTIMATED TIME: 1.5 hours

---

**Note**: This is Phase 2 of 3. Phase 3 will add WhatsApp notifications to complete the au pair scheduling system.