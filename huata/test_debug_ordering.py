#!/usr/bin/env python3
"""Test event ordering effect on severity"""

import asyncio
from datetime import datetime, timedelta
from conflict_detector import ConflictDetector

async def main():
    detector = ConflictDetector()
    now = datetime.now()

    health_event = {
        "id": "test_doctor",
        "summary": "Doctor Appointment",
        "start": (now + timedelta(hours=3)).isoformat(),
        "end": (now + timedelta(hours=4)).isoformat(),
        "calendar_id": "appointments@demestihas.com"
    }

    work_event = {
        "id": "test_standup",
        "summary": "Team Standup",
        "start": (now + timedelta(hours=3)).isoformat(),
        "end": (now + timedelta(hours=3, minutes=30)).isoformat(),
        "calendar_id": "primary"
    }

    # Test with health first
    print("Testing with health event first:")
    result1 = await detector.detect_conflicts(
        [health_event, work_event],
        now,
        now + timedelta(days=1)
    )
    print(f"  Severity: {result1['conflicts'][0]['severity'] if result1['conflicts'] else 'No conflict'}")

    # Test with work first
    print("\nTesting with work event first:")
    result2 = await detector.detect_conflicts(
        [work_event, health_event],
        now,
        now + timedelta(days=1)
    )
    print(f"  Severity: {result2['conflicts'][0]['severity'] if result2['conflicts'] else 'No conflict'}")

    # Direct severity test both orders
    print("\nDirect severity calculation:")
    sev1 = detector._calculate_severity(health_event, work_event)
    sev2 = detector._calculate_severity(work_event, health_event)
    print(f"  health, work: {sev1}")
    print(f"  work, health: {sev2}")

if __name__ == "__main__":
    asyncio.run(main())
