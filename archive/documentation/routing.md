# EA-AI Tool Routing Matrix

## Agent Assignments

### Pluma (Email Agent)
Keywords: email, gmail, draft, reply, send, inbox, message
Operations:
- fetch_emails
- generate_reply
- create_draft
- search_messages

### Huata (Calendar Agent)
Keywords: calendar, schedule, meeting, appointment, event, conflict
Operations:
- check_conflicts
- find_free_time
- list_events
- schedule_meeting

### Lyco (Task Agent)
Keywords: task, todo, priority, deadline, project, milestone
Operations:
- create_task
- prioritize
- break_down
- track_progress

### Kairos (Time Agent)
Keywords: time, reminder, duration, timer, alert, notification
Operations:
- set_reminder
- time_block
- track_time
- schedule_alert

## Routing Rules
1. Check keywords first
2. If multiple matches, prioritize by operation type
3. Default to Lyco for ambiguous requests
4. Use context from state.md for user preferences
