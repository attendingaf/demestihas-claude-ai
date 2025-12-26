#!/usr/bin/env python3
"""Debug script to test exact test conditions"""

import asyncio
from datetime import datetime, timedelta
from conflict_detector import ConflictDetector, EventCategory

async def main():
    detector = ConflictDetector()

    now = datetime.now()

    # Exact same events as in test
    event1 = {
        "id": "test_doctor_appointment",
        "summary": "Doctor Appointment",
        "start": (now + timedelta(hours=3)).isoformat(),
        "end": (now + timedelta(hours=4)).isoformat(),
        "calendar_id": "appointments@demestihas.com"
    }

    event2 = {
        "id": "test_team_standup",
        "summary": "Team Standup",
        "start": (now + timedelta(hours=3)).isoformat(),
        "end": (now + timedelta(hours=3, minutes=30)).isoformat(),
        "calendar_id": "primary"
    }

    # Check if they overlap
    overlap = detector._events_overlap(event1, event2)
    print(f"Events overlap: {overlap}")

    # Test categorization
    cat1 = detector._categorize_event(event1)
    cat2 = detector._categorize_event(event2)

    print(f"\nEvent 1: {event1['summary']} (calendar: {event1['calendar_id']})")
    print(f"  Start: {event1['start']}")
    print(f"  End: {event1['end']}")
    print(f"  Category: {cat1}")

    print(f"\nEvent 2: {event2['summary']} (calendar: {event2['calendar_id']})")
    print(f"  Start: {event2['start']}")
    print(f"  End: {event2['end']}")
    print(f"  Category: {cat2}")

    # Test severity calculation directly
    severity = detector._calculate_severity(event1, event2)
    print(f"\nDirect severity calculation: {severity}")

    # Full conflict detection (same as test)
    events = [event1, event2]
    result = await detector.detect_conflicts(
        events,
        now,
        now + timedelta(days=1)
    )

    print(f"\nConflict detection result:")
    if result['conflicts']:
        conflict = result['conflicts'][0]
        print(f"  Number of conflicts: {len(result['conflicts'])}")
        print(f"  Severity: {conflict['severity']}")
        print(f"  Event IDs in conflict: {[e['id'] for e in conflict['events']]}")
    else:
        print("  No conflicts detected!")

if __name__ == "__main__":
    asyncio.run(main())
