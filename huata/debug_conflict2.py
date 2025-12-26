#!/usr/bin/env python3
"""Debug script to test conflict detection categorization"""

import asyncio
from datetime import datetime, timedelta
from conflict_detector import ConflictDetector, EventCategory

async def main():
    detector = ConflictDetector()

    # Create test events
    event1 = {
        "id": "test_doctor",
        "summary": "Doctor Appointment",
        "start": datetime.now().isoformat(),
        "end": (datetime.now() + timedelta(hours=1)).isoformat(),
        "calendar_id": "appointments@demestihas.com"
    }

    event2 = {
        "id": "test_meeting",
        "summary": "Team Standup",
        "start": datetime.now().isoformat(),
        "end": (datetime.now() + timedelta(hours=1)).isoformat(),
        "calendar_id": "primary"
    }

    # Test categorization
    cat1 = detector._categorize_event(event1)
    cat2 = detector._categorize_event(event2)

    print(f"Event 1: {event1['summary']} (calendar: {event1['calendar_id']})")
    print(f"  Category: {cat1}")
    print(f"Event 2: {event2['summary']} (calendar: {event2['calendar_id']})")
    print(f"  Category: {cat2}")

    # Test severity calculation
    severity = detector._calculate_severity(event1, event2)
    print(f"\nSeverity: {severity}")
    print(f"Expected: ConflictSeverity.CRITICAL")

    # Full conflict detection
    events = [event1, event2]
    result = await detector.detect_conflicts(
        events,
        datetime.now(),
        datetime.now() + timedelta(days=1)
    )

    if result['conflicts']:
        print(f"\nFull Detection Result:")
        print(f"  Severity: {result['conflicts'][0]['severity']}")

if __name__ == "__main__":
    asyncio.run(main())
