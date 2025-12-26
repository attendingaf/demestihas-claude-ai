# Calendar ID Registry
## Google Calendar Integration Configuration

### PRIMARY CALENDARS
```yaml
CALENDAR_REGISTRY:
  lys_familia:
    id: "7dia35946hir6rbq10stda8hk4@group.calendar.google.com"
    name: "LyS Familia"
    type: "family"
    priority: 1
    use_for:
      - family_events
      - shared_activities
      - birthdays
      - anniversaries
      - family_meetings
    color: "#7986CB"
    
  beltline:
    id: "mene@beltlineconsulting.co"
    name: "Beltline Consulting"
    type: "work"
    priority: 2
    use_for:
      - client_meetings
      - work_deadlines
      - consulting_sessions
      - professional_events
    color: "#33B679"
    
  primary:
    id: "menelaos4@gmail.com"
    name: "Primary Personal"
    type: "personal"
    priority: 3
    use_for:
      - personal_appointments
      - default_calendar
      - reminders
      - personal_tasks
    color: "#039BE5"
    
  limon_y_sal:
    id: "e46i6ac3ipii8b7iugsqfeh2j8@group.calendar.google.com"
    name: "Limon y Sal"
    type: "business"
    priority: 4
    use_for:
      - restaurant_events
      - business_meetings
      - supplier_appointments
      - staff_schedules
    color: "#F6BF26"
    
  cindy:
    id: "c4djl5q698b556jqliablah9uk@group.calendar.google.com"
    name: "Cindy's Calendar"
    type: "family_member"
    priority: 5
    use_for:
      - cindy_appointments
      - cindy_activities
      - shared_events
    color: "#E67C73"
    
  au_pair:
    id: "up5jrbrsng5le7qmu0uhi6pedo@group.calendar.google.com"
    name: "Au Pair Schedule"
    type: "household"
    priority: 6
    use_for:
      - au_pair_schedule
      - childcare_coverage
      - days_off
      - vacation_planning
    color: "#8E24AA"
```

### ROUTING RULES
```yaml
CALENDAR_SELECTION:
  by_keyword:
    family:
      keywords: ["family", "kids", "children", "angela", "wife"]
      calendar: "lys_familia"
      
    work:
      keywords: ["client", "meeting", "consulting", "beltline", "work"]
      calendar: "beltline"
      
    restaurant:
      keywords: ["restaurant", "limon", "sal", "supplier", "staff"]
      calendar: "limon_y_sal"
      
    cindy:
      keywords: ["cindy"]
      calendar: "cindy"
      
    au_pair:
      keywords: ["au pair", "childcare", "babysitter", "nanny"]
      calendar: "au_pair"
      
    default:
      calendar: "primary"
      
  by_time:
    business_hours:
      time: "9:00-17:00"
      weekdays: ["Mon", "Tue", "Wed", "Thu", "Fri"]
      prefer: "beltline"
      
    evening:
      time: "17:00-21:00"
      prefer: "lys_familia"
      
    weekend:
      days: ["Sat", "Sun"]
      prefer: "lys_familia"
```

### CONFLICT RESOLUTION
```yaml
CONFLICT_HANDLING:
  detection:
    check_calendars:
      - all  # Check all calendars for conflicts
    buffer_time: "15_minutes"
    travel_time: "30_minutes"
    
  priority_rules:
    1: "lys_familia"     # Family always wins
    2: "beltline"        # Work is second
    3: "limon_y_sal"     # Business third
    4: "primary"         # Personal fourth
    5: "cindy"           # Individual calendars
    6: "au_pair"         # Support schedules
    
  resolution_strategies:
    same_priority:
      action: "suggest_reschedule"
      notify: true
      
    different_priority:
      action: "honor_higher_priority"
      suggest_alternative: true
      
    overlap_detected:
      action: "alert_user"
      provide_options: true
```

### TIME BLOCKING RULES
```yaml
TIME_BLOCKS:
  standard_duration: "15_minutes"
  
  meeting_types:
    quick_sync:
      duration: "15_minutes"
      buffer: "0_minutes"
      
    standard_meeting:
      duration: "30_minutes"
      buffer: "5_minutes"
      
    extended_meeting:
      duration: "60_minutes"
      buffer: "10_minutes"
      
    workshop:
      duration: "120_minutes"
      buffer: "15_minutes"
      
  auto_blocking:
    focus_time:
      calendar: "primary"
      duration: "90_minutes"
      recurrence: "daily"
      time: "09:00-10:30"
      
    family_time:
      calendar: "lys_familia"
      duration: "120_minutes"
      recurrence: "daily"
      time: "18:00-20:00"
```

### INTEGRATION SETTINGS
```yaml
CALENDAR_SYNC:
  sync_interval: "5_minutes"
  
  cache_policy:
    availability: "no_cache"  # Always real-time
    events: "5_minute_cache"
    conflicts: "1_minute_cache"
    
  notifications:
    upcoming_event: "15_minutes_before"
    conflict_detected: "immediate"
    calendar_updated: "silent"
    
  permissions:
    read: "all_calendars"
    write: "authorized_only"
    modify: "owner_only"
    delete: "confirmation_required"
```

### CALENDAR QUERIES
```yaml
QUERY_TEMPLATES:
  check_availability:
    calendars: ["all"]
    time_range: "next_2_weeks"
    exclude: ["all_day_events"]
    
  find_slot:
    duration: "30_minutes"
    calendars: ["beltline", "primary"]
    constraints:
      - "business_hours"
      - "no_conflicts"
      - "buffer_time"
      
  daily_agenda:
    calendars: ["all"]
    time_range: "today"
    include:
      - "events"
      - "reminders"
      - "tasks"
      
  conflict_check:
    calendars: ["all"]
    buffer: "15_minutes"
    include_travel: true
```

### CALENDAR COLORS
```yaml
COLOR_CODING:
  by_priority:
    high: "#D50000"      # Red
    medium: "#F57C00"    # Orange
    low: "#0B8043"       # Green
    
  by_type:
    meeting: "#039BE5"   # Blue
    personal: "#7986CB"  # Lavender
    family: "#33B679"    # Green
    work: "#616161"      # Grey
    
  by_status:
    confirmed: "#0B8043" # Green
    tentative: "#F6BF26" # Yellow
    cancelled: "#D50000" # Red
```

### API CONFIGURATION
```yaml
GOOGLE_CALENDAR_API:
  version: "v3"
  
  endpoints:
    list_events: "/calendars/{calendarId}/events"
    create_event: "/calendars/{calendarId}/events"
    update_event: "/calendars/{calendarId}/events/{eventId}"
    delete_event: "/calendars/{calendarId}/events/{eventId}"
    
  auth:
    type: "OAuth2"
    scopes:
      - "https://www.googleapis.com/auth/calendar"
      - "https://www.googleapis.com/auth/calendar.events"
      
  rate_limits:
    requests_per_second: 10
    daily_quota: 1000000
```

### MONITORING
```yaml
CALENDAR_METRICS:
  track:
    - events_created
    - conflicts_detected
    - availability_queries
    - sync_failures
    - api_latency
    
  alerts:
    - sync_failure
    - conflict_unresolved
    - quota_exceeded
    - calendar_unreachable
```