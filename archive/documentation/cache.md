# EA-AI Cache System

## Three-Tier Cache Architecture

### L1 Cache (Hot - Memory)
- Size: 100 items max
- TTL: Session lifetime
- Contents: Recent operations, active patterns

### L2 Cache (Warm - Patterns)
- Size: 500 items max
- TTL: 24 hours
- Contents: Common patterns, frequent requests

### L3 Cache (Cold - Disk)
- Size: Unlimited
- TTL: 7 days
- Contents: Historical data, rarely accessed

## Cached Patterns
- check_calendar -> Use list_gcal_events
- fetch_emails -> Use search_gmail_messages
- list_tasks -> Check Notion
- family_schedule -> Multi-calendar check

## Performance Metrics
- Cache hit rate target: >80%
- Warmup time: <30ms
- Pattern recognition: <10ms
