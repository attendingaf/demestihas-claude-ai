#!/usr/bin/env python3
"""
Test suite for Calendar Conflict Detection
Tests conflict detection, severity calculation, and recommendations
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List
import redis.asyncio as redis

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from conflict_detector import ConflictDetector, ConflictSeverity, EventCategory

class ConflictTestSuite:
    """Comprehensive test suite for conflict detection"""

    def __init__(self):
        self.detector = None
        self.redis_client = None
        self.test_results = []

    async def setup(self):
        """Initialize test environment"""
        print("🔧 Setting up test environment...")

        # Try to connect to Redis
        try:
            redis_host = os.environ.get('REDIS_HOST', 'localhost')
            redis_port = int(os.environ.get('REDIS_PORT', 6379))
            self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            await self.redis_client.ping()
            print(f"✅ Connected to Redis at {redis_host}:{redis_port}")
        except Exception as e:
            print(f"⚠️  Redis not available: {e} (tests will run without caching)")
            self.redis_client = None

        # Initialize detector
        self.detector = ConflictDetector(redis_client=self.redis_client)
        print("✅ Conflict detector initialized")

    async def teardown(self):
        """Clean up test environment"""
        if self.redis_client:
            await self.redis_client.close()
        print("🧹 Test environment cleaned up")

    def create_test_event(self, title: str, start: datetime, end: datetime,
                         calendar_id: str = "primary") -> Dict:
        """Create a test event"""
        return {
            "id": f"test_{title.replace(' ', '_').lower()}",
            "summary": title,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "calendar_id": calendar_id
        }

    async def test_basic_conflict_detection(self):
        """Test basic overlap detection between two events"""
        print("\n📋 Test: Basic Conflict Detection")

        now = datetime.now()
        events = [
            self.create_test_event(
                "Team Meeting",
                now + timedelta(hours=1),
                now + timedelta(hours=2),
                "primary"
            ),
            self.create_test_event(
                "Client Call",
                now + timedelta(hours=1, minutes=30),
                now + timedelta(hours=2, minutes=30),
                "primary"
            )
        ]

        result = await self.detector.detect_conflicts(
            events,
            now,
            now + timedelta(days=1)
        )

        assert result['summary']['total_conflicts'] == 1, "Should detect 1 conflict"
        assert result['conflicts'][0]['overlap_minutes'] == 30, "Should have 30 minute overlap"

        print(f"  ✅ Detected {result['summary']['total_conflicts']} conflict(s)")
        print(f"  ✅ Overlap duration: {result['conflicts'][0]['overlap_minutes']} minutes")

        self.test_results.append(("Basic Conflict Detection", True))

    async def test_severity_levels(self):
        """Test different severity level calculations"""
        print("\n📋 Test: Severity Level Calculation")

        now = datetime.now()

        # Test HIGH severity: Work-Family conflict
        events_high = [
            self.create_test_event(
                "Important Client Meeting",
                now + timedelta(hours=1),
                now + timedelta(hours=2),
                "primary"
            ),
            self.create_test_event(
                "Persy's School Play",
                now + timedelta(hours=1),
                now + timedelta(hours=2, minutes=30),
                "family@demestihas.com"
            )
        ]

        result_high = await self.detector.detect_conflicts(
            events_high,
            now,
            now + timedelta(days=1)
        )

        assert result_high['conflicts'][0]['severity'] == 'high', "Work-Family should be HIGH"
        print(f"  ✅ Work-Family conflict: {result_high['conflicts'][0]['severity'].upper()}")

        # Test CRITICAL severity: Health appointment
        events_critical = [
            self.create_test_event(
                "Doctor Appointment",
                now + timedelta(hours=3),
                now + timedelta(hours=4),
                "appointments@demestihas.com"
            ),
            self.create_test_event(
                "Team Standup",
                now + timedelta(hours=3),
                now + timedelta(hours=3, minutes=30),
                "primary"
            )
        ]

        # Debug: print the events being tested
        print(f"  Debug: Testing events:")
        for e in events_critical:
            cat = self.detector._categorize_event(e)
            print(f"    - {e['summary']}: calendar={e['calendar_id']}, category={cat}")

        # Debug: Check severity calculation directly
        sev_direct = self.detector._calculate_severity(events_critical[0], events_critical[1])
        print(f"  Debug: Direct severity calc = {sev_direct}")

        result_critical = await self.detector.detect_conflicts(
            events_critical,
            now,
            now + timedelta(days=1)
        )

        # Debug output
        if result_critical['conflicts']:
            actual_severity = result_critical['conflicts'][0]['severity']
            conflict_events = result_critical['conflicts'][0]['events']
            print(f"  Debug: Health conflict severity = {actual_severity}")
            print(f"  Debug: Conflicting events:")
            for ce in conflict_events:
                cat = self.detector._categorize_event(ce)
                print(f"    - {ce['summary']}: {ce['calendar_id']} -> {cat}")
            assert actual_severity == 'critical', f"Health should be CRITICAL, got {actual_severity}"
            print(f"  ✅ Health conflict: {actual_severity.upper()}")
        else:
            assert False, "No conflicts detected for health appointment"

        # Test LOW severity: Personal events
        events_low = [
            self.create_test_event(
                "Lunch with friend",
                now + timedelta(hours=5),
                now + timedelta(hours=6),
                "mene.personal@gmail.com"
            ),
            self.create_test_event(
                "Gym session",
                now + timedelta(hours=5, minutes=30),
                now + timedelta(hours=6, minutes=30),
                "mene.personal@gmail.com"
            )
        ]

        result_low = await self.detector.detect_conflicts(
            events_low,
            now,
            now + timedelta(days=1)
        )

        assert result_low['conflicts'][0]['severity'] == 'low', "Personal should be LOW"
        print(f"  ✅ Personal conflict: {result_low['conflicts'][0]['severity'].upper()}")

        self.test_results.append(("Severity Level Calculation", True))

    async def test_recommendations(self):
        """Test recommendation generation"""
        print("\n📋 Test: Recommendation Generation")

        now = datetime.now()
        events = [
            self.create_test_event(
                "Executive Review",
                now + timedelta(hours=2),
                now + timedelta(hours=3),
                "primary"
            ),
            self.create_test_event(
                "Family Dinner",
                now + timedelta(hours=2, minutes=30),
                now + timedelta(hours=4),
                "family@demestihas.com"
            )
        ]

        result = await self.detector.detect_conflicts(
            events,
            now,
            now + timedelta(days=1)
        )

        recommendations = result['conflicts'][0]['recommendations']
        assert len(recommendations) > 0, "Should generate recommendations"

        print(f"  ✅ Generated {len(recommendations)} recommendations:")
        for rec in recommendations[:3]:
            print(f"    • {rec}")

        self.test_results.append(("Recommendation Generation", True))

    async def test_free_slot_finder(self):
        """Test finding conflict-free time slots"""
        print("\n📋 Test: Free Slot Finder")

        now = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        events = [
            self.create_test_event(
                "Morning Meeting",
                now,
                now + timedelta(hours=1),
                "primary"
            ),
            self.create_test_event(
                "Lunch Meeting",
                now + timedelta(hours=3),
                now + timedelta(hours=4),
                "primary"
            ),
            self.create_test_event(
                "Afternoon Review",
                now + timedelta(hours=6),
                now + timedelta(hours=7),
                "primary"
            )
        ]

        # Find 60-minute free slots
        free_slots = await self.detector.find_conflict_free_slots(
            events,
            60,  # 60 minutes
            now,
            now + timedelta(days=1),
            (9, 17)  # Working hours
        )

        assert len(free_slots) > 0, "Should find free slots"

        print(f"  ✅ Found {len(free_slots)} free slots:")
        for slot in free_slots[:3]:
            start_time = datetime.fromisoformat(slot['start'])
            print(f"    • {start_time.strftime('%H:%M')} - {slot['duration_minutes']} minutes")

        self.test_results.append(("Free Slot Finder", True))

    async def test_cache_performance(self):
        """Test Redis caching performance"""
        print("\n📋 Test: Cache Performance")

        if not self.redis_client:
            print("  ⚠️  Skipped (Redis not available)")
            self.test_results.append(("Cache Performance", "Skipped"))
            return

        now = datetime.now()
        events = [
            self.create_test_event(
                f"Event {i}",
                now + timedelta(hours=i),
                now + timedelta(hours=i+1),
                "primary"
            )
            for i in range(10)
        ]

        # First call (cache miss)
        start_time = datetime.now()
        result1 = await self.detector.detect_conflicts(
            events,
            now,
            now + timedelta(days=1)
        )
        first_call_time = (datetime.now() - start_time).total_seconds()

        # Second call (cache hit)
        start_time = datetime.now()
        result2 = await self.detector.detect_conflicts(
            events,
            now,
            now + timedelta(days=1)
        )
        second_call_time = (datetime.now() - start_time).total_seconds()

        assert second_call_time < first_call_time, "Cached call should be faster"

        print(f"  ✅ First call: {first_call_time:.3f}s")
        print(f"  ✅ Cached call: {second_call_time:.3f}s")
        print(f"  ✅ Speed improvement: {(first_call_time/second_call_time):.1f}x faster")

        self.test_results.append(("Cache Performance", True))

    async def test_multiple_conflicts(self):
        """Test detection of multiple simultaneous conflicts"""
        print("\n📋 Test: Multiple Simultaneous Conflicts")

        now = datetime.now()

        # Create a triple-booking scenario
        events = [
            self.create_test_event(
                "CEO Meeting",
                now + timedelta(hours=2),
                now + timedelta(hours=3),
                "primary"
            ),
            self.create_test_event(
                "Investor Call",
                now + timedelta(hours=2),
                now + timedelta(hours=3),
                "primary"
            ),
            self.create_test_event(
                "Persy's Parent-Teacher Conference",
                now + timedelta(hours=2, minutes=15),
                now + timedelta(hours=2, minutes=45),
                "persy.school@edu.org"
            )
        ]

        result = await self.detector.detect_conflicts(
            events,
            now,
            now + timedelta(days=1)
        )

        # Should detect 3 conflicts: CEO-Investor, CEO-School, Investor-School
        assert result['summary']['total_conflicts'] == 3, "Should detect 3 conflicts"

        print(f"  ✅ Detected {result['summary']['total_conflicts']} conflicts in triple-booking")
        print(f"  ✅ Severity breakdown:")
        print(f"    • Critical: {result['summary']['critical']}")
        print(f"    • High: {result['summary']['high']}")
        print(f"    • Medium: {result['summary']['medium']}")
        print(f"    • Low: {result['summary']['low']}")

        self.test_results.append(("Multiple Simultaneous Conflicts", True))

    async def test_edge_cases(self):
        """Test edge cases and boundary conditions"""
        print("\n📋 Test: Edge Cases")

        now = datetime.now()

        # Test exact boundary (events end/start at same time - no conflict)
        events_boundary = [
            self.create_test_event(
                "Meeting 1",
                now + timedelta(hours=1),
                now + timedelta(hours=2),
                "primary"
            ),
            self.create_test_event(
                "Meeting 2",
                now + timedelta(hours=2),  # Starts exactly when first ends
                now + timedelta(hours=3),
                "primary"
            )
        ]

        result_boundary = await self.detector.detect_conflicts(
            events_boundary,
            now,
            now + timedelta(days=1)
        )

        assert result_boundary['summary']['total_conflicts'] == 0, "Adjacent events should not conflict"
        print(f"  ✅ Adjacent events: No conflict detected")

        # Test all-day event
        events_allday = [
            self.create_test_event(
                "Vacation Day",
                now.replace(hour=0, minute=0, second=0, microsecond=0),
                now.replace(hour=23, minute=59, second=0, microsecond=0),
                "primary"
            ),
            self.create_test_event(
                "Team Sync",
                now.replace(hour=14, minute=0, second=0, microsecond=0),
                now.replace(hour=15, minute=0, second=0, microsecond=0),
                "primary"
            )
        ]

        result_allday = await self.detector.detect_conflicts(
            events_allday,
            now,
            now + timedelta(days=1)
        )

        print(f"  Debug: All-day test found {result_allday['summary']['total_conflicts']} conflicts")
        if result_allday['conflicts']:
            for c in result_allday['conflicts']:
                print(f"    - {c['events'][0]['summary']} vs {c['events'][1]['summary']}")

        assert result_allday['summary']['total_conflicts'] == 1, f"All-day event should conflict, got {result_allday['summary']['total_conflicts']} conflicts"
        print(f"  ✅ All-day event: Conflict detected")

        self.test_results.append(("Edge Cases", True))

    async def run_all_tests(self):
        """Run all tests in the suite"""
        print("\n" + "="*60)
        print("🧪 CALENDAR CONFLICT DETECTION TEST SUITE")
        print("="*60)

        await self.setup()

        try:
            await self.test_basic_conflict_detection()
            await self.test_severity_levels()
            await self.test_recommendations()
            await self.test_free_slot_finder()
            await self.test_cache_performance()
            await self.test_multiple_conflicts()
            await self.test_edge_cases()

        except AssertionError as e:
            print(f"\n❌ Test failed: {e}")
            self.test_results.append(("Failed Test", False))
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            self.test_results.append(("Error", False))
        finally:
            await self.teardown()

        # Print summary
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)

        passed = sum(1 for _, result in self.test_results if result is True)
        failed = sum(1 for _, result in self.test_results if result is False)
        skipped = sum(1 for _, result in self.test_results if result == "Skipped")

        for test_name, result in self.test_results:
            if result is True:
                status = "✅ PASSED"
            elif result is False:
                status = "❌ FAILED"
            else:
                status = "⚠️  SKIPPED"
            print(f"{status:12} | {test_name}")

        print("-"*60)
        print(f"Total: {len(self.test_results)} tests")
        print(f"Passed: {passed} | Failed: {failed} | Skipped: {skipped}")

        if failed == 0:
            print("\n🎉 ALL TESTS PASSED!")
            return 0
        else:
            print(f"\n❌ {failed} test(s) failed")
            return 1

async def main():
    """Main test runner"""
    test_suite = ConflictTestSuite()
    exit_code = await test_suite.run_all_tests()
    sys.exit(exit_code)

if __name__ == "__main__":
    asyncio.run(main())
