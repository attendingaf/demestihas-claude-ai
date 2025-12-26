#!/usr/bin/env python3
"""Isolated test for critical severity"""

import asyncio
from datetime import datetime, timedelta
from conflict_detector import ConflictDetector

async def main():
    # Create fresh detector
    detector = ConflictDetector()
    now = datetime.now()

    # Only test critical severity events
    events_critical = [
        {
            "id": "test_doctor_appointment",
            "summary": "Doctor Appointment",
            "start": (now + timedelta(hours=3)).isoformat(),
            "end": (now + timedelta(hours=4)).isoformat(),
            "calendar_id": "appointments@demestihas.com"
        },
        {
            "id": "test_team_standup",
            "summary": "Team Standup",
            "start": (now + timedelta(hours=3)).isoformat(),
            "end": (now + timedelta(hours=3, minutes=30)).isoformat(),
            "calendar_id": "primary"
        }
    ]

    # Detect conflicts
    result = await detector.detect_conflicts(
        events_critical,
        now,
        now + timedelta(days=1)
    )

    print(f"Events passed: {len(events_critical)}")
    print(f"Conflicts found: {result['summary']['total_conflicts']}")

    if result['conflicts']:
        conflict = result['conflicts'][0]
        print(f"Severity: {conflict['severity']}")
        print("Events in conflict:")
        for e in conflict['events']:
            print(f"  - {e['summary']} ({e['calendar_id']})")

        assert conflict['severity'] == 'critical', f"Expected critical, got {conflict['severity']}"
        print("✅ Test PASSED: Health conflict is CRITICAL")
    else:
        print("❌ No conflicts detected")

if __name__ == "__main__":
    asyncio.run(main())
