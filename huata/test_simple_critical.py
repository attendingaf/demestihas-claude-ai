#!/usr/bin/env python3
"""Simple test just for critical severity"""

import asyncio
from datetime import datetime, timedelta
from conflict_detector import ConflictDetector

async def main():
    detector = ConflictDetector()
    now = datetime.now()

    # Create health and work event that overlap
    events = [
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

    result = await detector.detect_conflicts(events, now, now + timedelta(days=1))

    print(f"Number of conflicts: {result['summary']['total_conflicts']}")
    if result['conflicts']:
        print(f"Severity: {result['conflicts'][0]['severity']}")
        assert result['conflicts'][0]['severity'] == 'critical', f"Expected critical, got {result['conflicts'][0]['severity']}"
        print("✅ Test passed: Health conflict detected as CRITICAL")
    else:
        print("❌ No conflicts detected")

    await asyncio.sleep(0.1)  # Give time for any async cleanup

if __name__ == "__main__":
    asyncio.run(main())
