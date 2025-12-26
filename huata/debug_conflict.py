#!/usr/bin/env python3
"""Debug script to test conflict detection categorization"""

import asyncio
from datetime import datetime, timedelta
from conflict_detector import ConflictDetector, EventCategory

async def main():
    detector = ConflictDetector()

    # Create test event
    test_event = {
        "id": "test_doctor",
        "summary": "Doctor Appointment",
        "start": datetime.now().isoformat(),
        "end": (datetime.now() + timedelta(hours=1)).isoformat(),
        "calendar_id": "appointments@demestihas.com"
    }

    # Test categorization
    category = detector._categorize_event(test_event)
    print(f"Event: {test_event['summary']}")
    print(f"Calendar ID: {test_event['calendar_id']}")
    print(f"Detected Category: {category}")
    print(f"Expected: {EventCategory.HEALTH}")
    print(f"Match: {category == EventCategory.HEALTH}")

    # Test with two events
    events = [
        test_event,
        {
            "id": "test_meeting",
            "summary": "Team Meeting",
            "start": datetime.now().isoformat(),
            "end": (datetime.now() + timedelta(hours=1)).isoformat(),
            "calendar_id": "primary"
        }
    ]

    result = await detector.detect_conflicts(
        events,
        datetime.now(),
        datetime.now() + timedelta(days=1)
    )

    if result['conflicts']:
        print(f"\nConflict Severity: {result['conflicts'][0]['severity']}")
        print(f"Expected: critical")

if __name__ == "__main__":
    asyncio.run(main())
