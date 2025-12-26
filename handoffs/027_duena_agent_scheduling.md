# HANDOFF #027: Nina Agent - Au Pair Scheduling System

**FROM**: PM-Opus  
**TO**: Claude Code / Dev (Sonnet)  
**DATE**: 2025-08-27T04:15:00Z  
**PRIORITY**: 🎯 Sprint 2 Priority  
**TYPE**: New Agent Implementation

## CONTEXT

With Yanay/Lyco successfully deployed and validated, we're ready for the next major family pain point: au pair scheduling.

### Current Pain Points
- Manual Google Sheets updates (high cognitive load)
- WhatsApp/text coordination scattered
- No coverage gap detection
- Schedule changes require multiple updates
- Viola doesn't get automatic notifications

### Family Context
- **Viola**: German au pair, M-F standard schedule 7am-7pm
- **Parents**: Variable ER shifts, need flexibility
- **Kids**: School schedules, activities, soccer practice
- **Goal**: Natural language scheduling with automatic gap detection

## OBJECTIVE

Create Nina - a scheduling specialist agent that manages au pair schedules through natural language commands and proactively identifies coverage gaps.

## ARCHITECTURE DESIGN

### System Integration
```
User Input → Yanay → Intent Router
                ↓
         "Viola has Thursday off"
                ↓
            Nina Agent
         ↙     ↓      ↘
     Redis  Schedule  WhatsApp
     State  Logic     Notifier
         ↘     ↓      ↙
          Notion Tasks
         (coverage gaps)
```

### Core Components

#### 1. Schedule State Manager
```python
class ScheduleState:
    baseline = {
        "monday": {"start": "07:00", "end": "19:00"},
        "tuesday": {"start": "07:00", "end": "19:00"},
        "wednesday": {"start": "07:00", "end": "19:00"},
        "thursday": {"start": "07:00", "end": "19:00"},
        "friday": {"start": "07:00", "end": "19:00"},
        "saturday": None,  # Off by default
        "sunday": None     # Off by default
    }
    
    exceptions = {}  # Date-specific overrides
    # Example: {"2025-08-28": {"off": True, "reason": "Viola sick"}}
```

#### 2. Natural Language Parser
```python
# Input: "Viola needs Friday afternoon off"
# Output: {"date": "2025-08-29", "start": "07:00", "end": "12:00"}

# Input: "We need coverage Saturday evening"
# Output: {"date": "2025-08-30", "start": "17:00", "end": "22:00", "overtime": True}

# Input: "Date night tomorrow 7-11pm"
# Output: {"coverage_needed": True, "date": "tomorrow", "time": "19:00-23:00"}
```

#### 3. Gap Detection Engine
```python
def detect_gaps():
    """Check for uncovered periods"""
    gaps = []
    for date in next_7_days:
        parent_availability = check_calendar()  
        viola_schedule = get_schedule(date)
        kid_needs = get_school_activities(date)
        
        if gap_exists(parent_availability, viola_schedule, kid_needs):
            gaps.append({
                "date": date,
                "time": gap_period,
                "urgency": calculate_urgency(),
                "solution": suggest_solution()
            })
    return gaps
```

## IMPLEMENTATION PHASES

### Phase 1: Basic Schedule Tracking (Week 1)
**[CLAUDE CODE]** implements:

1. **Create duena.py** - Core scheduling agent
   - Schedule state management in Redis
   - Baseline + exceptions model
   - Natural language date/time parsing
   
2. **Integration with Yanay**
   - Add "schedule" intent to classifier
   - Route scheduling commands to Nina
   - Return confirmations to user

3. **Basic Commands**
   - "Viola has [day] off"
   - "Need coverage [date] [time]"
   - "What's Viola's schedule this week?"
   - "Viola back to normal schedule"

4. **Data Storage**
   ```python
   # Redis keys:
   schedule:baseline - JSON of standard week
   schedule:exceptions:YYYY-MM-DD - Specific date overrides
   schedule:comp_time - Accumulated comp time
   ```

### Phase 2: Calendar Integration (Week 2)
**[Dev (Sonnet)]** implements:

1. **Google Calendar Integration**
   - Read parent calendars for availability
   - Check kid activity calendars
   - Identify automatic coverage needs

2. **Proactive Gap Detection**
   - Daily scan at 8am and 8pm
   - Create tasks for uncovered periods
   - Prioritize by urgency

3. **Smart Notifications**
   - "Gap detected: Thursday 3-5pm (soccer pickup)"
   - "Viola confirmed available for date night Saturday"

### Phase 3: WhatsApp Integration (Week 3)
**[Dev (Sonnet)]** implements:

1. **WhatsApp Business API**
   - Send schedule confirmations to Viola
   - Weekly schedule summary on Sunday
   - Real-time change notifications

2. **Two-Way Communication**
   - Viola can confirm/decline via WhatsApp
   - Parents get confirmations
   - Auto-update schedule based on responses

## SUCCESS CRITERIA

### Functional Requirements
- [ ] Natural language schedule updates working
- [ ] Schedule state persisted in Redis
- [ ] Basic gap detection operational
- [ ] Integration with Yanay router complete
- [ ] Notion tasks created for gaps

### Performance Requirements
- [ ] Schedule query: <1 second response
- [ ] Gap detection: <3 seconds
- [ ] State updates: Immediate
- [ ] Redis memory: <10MB for schedules

### User Experience
- [ ] Parents can update schedule in <30 seconds
- [ ] No more spreadsheet needed
- [ ] Viola gets instant notifications
- [ ] Zero uncovered childcare gaps

## TESTING SCENARIOS

1. **Basic Schedule Change**
   ```
   Input: "Viola has Thursday off"
   Expected: Schedule updated, task created for coverage
   ```

2. **Complex Request**
   ```
   Input: "Need Viola Saturday 5-9pm for date night"
   Expected: Overtime logged, confirmation sent, calendar blocked
   ```

3. **Gap Detection**
   ```
   Scenario: Parent adds 3pm meeting Thursday
   Expected: Alert about school pickup gap
   ```

4. **Comp Time Tracking**
   ```
   Input: "Viola worked extra 3 hours Saturday"
   Expected: Comp time bank updated, available for future use
   ```

## TECHNICAL SPECIFICATIONS

### File Structure
```
/root/demestihas-ai/
├── nina.py            # Main scheduling agent
├── schedule_parser.py  # Natural language processing
├── gap_detector.py    # Coverage analysis
├── whatsapp_client.py # WhatsApp integration (Phase 3)
└── test_nina.py       # Test scenarios
```

### Dependencies
```python
# requirements.txt additions
redis>=4.5.0
python-dateutil>=2.8.2
pytz>=2023.3
# twilio (for WhatsApp, Phase 3)
```

### Environment Variables
```bash
# Add to .env
VIOLA_PHONE="+49..."  # Viola's WhatsApp
SCHOOL_CALENDAR_ID="..." # Google Calendar
REDIS_SCHEDULE_DB=2  # Separate Redis DB for schedules
```

## ROLLBACK PLAN

If issues arise:
1. Disable Nina routing in Yanay (1 line change)
2. Revert to manual scheduling (spreadsheet backup)
3. Clear Redis schedule keys
4. Notify family of temporary reversion

## NEXT STEPS

**[CLAUDE CODE]** to:
1. Create nina.py with basic schedule management
2. Integrate with Yanay's intent router
3. Implement Phase 1 commands
4. Test with provided scenarios
5. Report readiness for family testing

**[USER]** to:
1. Provide Viola's availability preferences
2. Share typical schedule exceptions
3. Define comp time policies
4. Test with real schedule scenarios

---

**Estimated Time**: 4 hours for Phase 1  
**Complexity**: Medium (similar to Lyco extraction)  
**Family Impact**: High (eliminates major friction point)  

This will transform: "Update spreadsheet, text Viola, create reminder" → "Viola has Thursday off" (done!)