# Au Pair Scheduling System Design
**Date:** 2025-08-26
**Type:** Strategic Architecture Document
**Priority:** Sprint 2 (After Yanay/Lyco split)

## Current State Analysis

The family currently manages Viola's schedule through a Google Sheet, requiring:
– Manual updates by parents
– Separate communication to Viola
– No integration with family task system
– High cognitive load to coordinate changes

## Proposed Multi-Agent Architecture

```
                   Natural Language Input
                 "Viola needs Thursday off"
                           │
                           ▼
                 ┌─────────────────┐
                 │     YANAY        │
                 │  (Orchestrator)  │
                 └─────────────────┘
                           │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
  ┌──────────┐    ┌──────────┐    ┌──────────┐
  │   LYCO   │    │  HUATA   │    │  DUEÑA   │
  │  (Tasks) │    │(Calendar)│    │(Schedule)│
  └──────────┘    └──────────┘    └──────────┘
        │                 │                 │
        ▼                 ▼                 ▼
    Notion DB      Google Cal       WhatsApp
```

## The Dueña Agent (New)

**Purpose:** Au pair schedule management specialist (Dueña = 'mistress of the house' in Spanish)

**Core Capabilities:**
– Schedule creation with defaults (M-F 7am-7pm baseline)
– Exception handling (days off, early release, late stays)
– Coverage gap detection and alerting
– Integration with school calendar
– Direct WhatsApp notifications to Viola

## Natural Language Workflows

### Scenario 1: Simple Day Off
```
Mene: "Viola has Thursday off"
↓
Yanay → Dueña Agent: mark_unavailable(thursday)
Dueña Agent → Checks coverage gaps
Dueña Agent → Updates schedule
Dueña Agent → WhatsApp to Viola: "Confirmed: Thursday 8/29 off"
Dueña Agent → Lyco: create_task("Arrange Thursday childcare")
↓
Response: "✅ Viola's Thursday off confirmed. Created childcare task."
```

### Scenario 2: Schedule Change with Conflict
```
Cindy: "Need Viola Saturday morning for soccer"
↓
Yanay → Dueña Agent: request_coverage(saturday_morning)
Dueña Agent → Checks: Saturday is normally off
Dueña Agent → Calculates: overtime or comp time needed
Dueña Agent → Creates options
↓
Response: "Viola normally has Saturday off. Options:
1. Request with overtime pay
2. Offer Monday afternoon off instead
3. Check if already planning to be home"
```

### Scenario 3: Weekly Planning
```
"What's Viola's schedule this week?"
↓
Yanay → Dueña Agent: get_weekly_schedule()
Yanay → Huata: get_family_calendar()
Yanay → Compiles integrated view
↓
Response: 
"📅 This Week:
Mon-Wed: Standard (7am-7pm)
Thu: Off (you have childcare task)
Fri: Extended to 8pm (date night)
Sat-Sun: Off
⚠️ Gap: Thu 3pm pickup needs coverage"
```

## ADHD-Optimized Features

### Smart Defaults
– Standard schedule pre-loaded
– Only track exceptions (reduce cognitive load)
– Visual week view with changes highlighted
– Automatic gap detection

### Proactive Notifications
– Sunday: "Week ahead schedule confirmed with Viola"
– Daily 7am: "Viola schedule today: [standard/modified]"
– Gaps: Immediate alert with suggested solutions
– Changes: Auto-notify all parties

### Natural Patterns
Instead of updating spreadsheets:
– "Viola early release Friday" → Done
– "Date night Saturday" → Checks coverage, confirms
– "Viola vacation next week" → Creates all coverage tasks

## Data Structure

```json
{
  "baseline_schedule": {
    "monday": {"start": "07:00", "end": "19:00"},
    "tuesday": {"start": "07:00", "end": "19:00"},
    // ... standard week
  },
  "exceptions": [
    {
      "date": "2025-08-29",
      "type": "day_off",
      "confirmed": true,
      "coverage": "parent_wfh"
    },
    {
      "date": "2025-08-30",
      "type": "extended",
      "end": "20:00",
      "reason": "date_night",
      "overtime": true
    }
  ],
  "recurring_exceptions": [
    {
      "pattern": "first_friday",
      "modification": {"end": "20:00"}
    }
  ]
}
```

## Integration Points

### With Lyco (Tasks):
– Auto-create coverage tasks for gaps
– Track childcare arrangements
– Handle backup sitter coordination

### With Huata (Calendar):
– School calendar integration
– Doctor appointments
– Activity schedules
– Parent work schedules

### With Yanay (Orchestration):
– Natural language processing
– Multi-agent coordination
– Context preservation ("give her tomorrow off too")

## Family Communication Flows

### To Viola (WhatsApp):
```
"Hi Viola! Schedule update:
✅ Thursday 8/29: Day off confirmed
📅 Friday 8/30: Extended to 8pm for date night
Normal schedule all other days.
Reply OK to confirm."
```

### To Parents (Telegram/Text):
```
"⚠️ Coverage needed Thu 3pm:
- School pickup: Persy (3:00), Stelios (3:15)
- Sitter available ($20/hr)
- Or WFH option?
Reply with choice"
```

### Weekly Summary (Sunday Evening):
```
"📋 Week Ahead Au Pair Schedule:
Standard: Mon, Tue, Wed (7a-7p)
OFF: Thursday (coverage arranged ✓)
Extended: Friday (until 8p)
Weekend: Off

All confirmed with Viola ✅"
```

## Implementation Phases

### Phase 1: Basic Schedule Tracking (Week 1)
– Viola agent with baseline schedule
– Simple exception handling
– Manual WhatsApp sends

### Phase 2: Integration (Week 2)
– Connect to Huata calendar
– Auto-gap detection
– Task creation in Lyco

### Phase 3: Automation (Week 3)
– WhatsApp API integration
– Proactive notifications
– Coverage suggestions

## Success Metrics
– Zero uncovered gaps (100% reliability)
– <30 seconds to update schedule (vs spreadsheet)
– Weekly confirmation rate >95%
– Viola satisfaction (clear communication)

## Emergency Handling

Quick commands for urgent situations:
– "Viola emergency today" → Activates backup plan
– "Need Viola now" → Sends immediate WhatsApp
– "Cancel Viola tomorrow" → Full cancellation flow

## Long-term Vision

Eventually, the system learns patterns:
– "Viola usually takes Thursdays off in summer"
– "Date nights are typically Saturday"
– "Soccer season needs Saturday coverage"

And suggests optimizations:
– "Based on patterns, pre-book Viola for next 3 Saturdays?"
– "Viola has worked extra 3 weeks, suggest comp day?"

---

**Next Steps:**
1. Complete Yanay/Lyco split (foundation needed)
2. Design Dueña agent API specification
3. Prototype WhatsApp integration
4. Test with one week of scheduling
