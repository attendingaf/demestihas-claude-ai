#!/usr/bin/env python3
"""Debug all-day event conflict detection"""

import asyncio
from datetime import datetime, timedelta
from conflict_detector import ConflictDetector

async def main():
    detector = ConflictDetector()
    now = datetime.now()

    # Create all-day event
    event1 = {
        "id": "test_vacation_day",
        "summary": "Vacation Day",
        "start": now.replace(hour=0, minute=0).isoformat(),
        "end": now.replace(hour=23, minute=59).isoformat(),
        "calendar_id": "primary"
    }

    event2 = {
        "id": "test_afternoon_meeting",
        "summary": "Afternoon Meeting",
        "start": now.replace(hour=14, minute=0).isoformat(),
        "end": now.replace(hour=15, minute=0).isoformat(),
        "calendar_id": "primary"
    }

    print(f"Event 1: {event1['summary']}")
    print(f"  Start: {event1['start']}")
    print(f"  End: {event1['end']}")

    print(f"\nEvent 2: {event2['summary']}")
    print(f"  Start: {event2['start']}")
    print(f"  End: {event2['end']}")

    # Check overlap
    overlap = detector._events_overlap(event1, event2)
    print(f"\nEvents overlap: {overlap}")

    # Full detection
    result = await detector.detect_conflicts(
        [event1, event2],
        now,
        now + timedelta(days=1)
    )

    print(f"Conflicts found: {result['summary']['total_conflicts']}")
    if result['conflicts']:
        print(f"Severity: {result['conflicts'][0]['severity']}")

if __name__ == "__main__":
    asyncio.run(main())
