#!/usr/bin/env python3
"""
Simple test to verify conflict detection is working
"""

import asyncio
from datetime import datetime, timedelta
from conflict_detector import ConflictDetector

async def main():
    print("🧪 Simple Conflict Detection Test")
    print("="*50)

    detector = ConflictDetector()
    now = datetime.now()

    # Create test events
    events = [
        # Work meeting and family event - should be HIGH severity
        {
            'id': 'meeting1',
            'summary': 'Important Client Meeting',
            'start': (now + timedelta(hours=2)).isoformat(),
            'end': (now + timedelta(hours=3)).isoformat(),
            'calendar_id': 'primary'  # work calendar
        },
        {
            'id': 'family1',
            'summary': 'Family Dinner',
            'start': (now + timedelta(hours=2, minutes=30)).isoformat(),
            'end': (now + timedelta(hours=4)).isoformat(),
            'calendar_id': 'family@demestihas.com'
        },
        # Health appointment - should be CRITICAL
        {
            'id': 'health1',
            'summary': 'Doctor Appointment',
            'start': (now + timedelta(hours=5)).isoformat(),
            'end': (now + timedelta(hours=6)).isoformat(),
            'calendar_id': 'appointments@demestihas.com'
        },
        {
            'id': 'meeting2',
            'summary': 'Team Standup',
            'start': (now + timedelta(hours=5, minutes=30)).isoformat(),
            'end': (now + timedelta(hours=6)).isoformat(),
            'calendar_id': 'primary'
        }
    ]

    # Detect conflicts
    result = await detector.detect_conflicts(
        events,
        now,
        now + timedelta(days=1)
    )

    # Display results
    print(f"\n📊 RESULTS")
    print(f"Total conflicts found: {result['summary']['total_conflicts']}")
    print(f"  • Critical: {result['summary']['critical']}")
    print(f"  • High: {result['summary']['high']}")
    print(f"  • Medium: {result['summary']['medium']}")
    print(f"  • Low: {result['summary']['low']}")

    print(f"\n📋 CONFLICT DETAILS")
    for conflict in result['conflicts']:
        event1 = conflict['events'][0]
        event2 = conflict['events'][1]
        print(f"\n➤ {conflict['severity'].upper()} Severity Conflict")
        print(f"  Event 1: {event1['summary']} ({event1['calendar_id']})")
        print(f"  Event 2: {event2['summary']} ({event2['calendar_id']})")
        print(f"  Overlap: {conflict['overlap_minutes']} minutes")
        print(f"  Recommendations:")
        for rec in conflict['recommendations'][:2]:
            print(f"    • {rec}")

    # Test free slot finder
    print(f"\n🔍 FINDING FREE SLOTS")
    free_slots = await detector.find_conflict_free_slots(
        events,
        60,  # 60 minute slots
        now,
        now + timedelta(days=1),
        (9, 17)  # working hours
    )

    print(f"Found {len(free_slots)} free 60-minute slots")
    for slot in free_slots[:3]:
        start = datetime.fromisoformat(slot['start'])
        end = datetime.fromisoformat(slot['end'])
        print(f"  • {start.strftime('%H:%M')} - {end.strftime('%H:%M')} ({slot['duration_minutes']} min)")

    print("\n✅ Test completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
