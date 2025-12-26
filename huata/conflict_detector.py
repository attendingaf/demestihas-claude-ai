"""
Calendar Conflict Detection Engine
Detects and manages calendar conflicts across family calendars
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import redis.asyncio as redis
import hashlib
import os

class ConflictSeverity(Enum):
    """Conflict severity levels"""
    LOW = "low"          # Both personal events
    MEDIUM = "medium"    # One work/school event
    HIGH = "high"        # Work-family conflict or double-booked work
    CRITICAL = "critical" # Multiple high-priority conflicts

class EventCategory(Enum):
    """Event categories for conflict analysis"""
    WORK = "work"
    FAMILY = "family"
    PERSONAL = "personal"
    SCHOOL = "school"
    HEALTH = "health"
    TRAVEL = "travel"

class ConflictDetector:
    """
    Core conflict detection engine for calendar events
    Analyzes overlapping events across 6 family calendars
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """Initialize conflict detector with optional Redis caching"""
        self.redis = redis_client
        self.cache_ttl = 300  # 5 minute cache TTL

        # Calendar configurations
        self.calendars = {
            "mene_work": {
                "id": "primary",
                "owner": "mene",
                "type": "work",
                "priority": 9
            },
            "mene_personal": {
                "id": "mene.personal@gmail.com",
                "owner": "mene",
                "type": "personal",
                "priority": 5
            },
            "cindy_work": {
                "id": "cindy.work@hospital.org",
                "owner": "cindy",
                "type": "work",
                "priority": 9
            },
            "family": {
                "id": "family@demestihas.com",
                "owner": "shared",
                "type": "family",
                "priority": 8
            },
            "persy_school": {
                "id": "persy.school@edu.org",
                "owner": "persy",
                "type": "school",
                "priority": 7
            },
            "shared_appointments": {
                "id": "appointments@demestihas.com",
                "owner": "shared",
                "type": "health",
                "priority": 10
            }
        }

    def _get_cache_key(self, start: datetime, end: datetime, events: List[Dict]) -> str:
        """Generate cache key for conflict query"""
        # Include event IDs in cache key to differentiate between different event sets
        event_ids = sorted([e.get('id', '') for e in events])
        key_data = f"conflicts:{start.isoformat()}:{end.isoformat()}:{':'.join(event_ids)}"
        return hashlib.md5(key_data.encode()).hexdigest()

    async def _get_cached_conflicts(self, start: datetime, end: datetime, events: List[Dict]) -> Optional[Dict]:
        """Retrieve cached conflicts if available"""
        if not self.redis:
            return None

        try:
            cache_key = self._get_cache_key(start, end, events)
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            print(f"Cache retrieval error: {e}")
        return None

    async def _cache_conflicts(self, start: datetime, end: datetime, events: List[Dict], conflicts: Dict):
        """Cache conflict results"""
        if not self.redis:
            return

        try:
            cache_key = self._get_cache_key(start, end, events)
            await self.redis.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(conflicts, default=str)
            )
        except Exception as e:
            print(f"Cache storage error: {e}")

    def _categorize_event(self, event: Dict) -> EventCategory:
        """Categorize event based on calendar, title, and content"""
        title = event.get('summary', '').lower()
        calendar_id = event.get('calendar_id', '')

        # Work-related keywords
        work_keywords = ['meeting', 'call', 'interview', 'presentation',
                        'review', 'standup', 'sprint', 'client', 'project']

        # Family keywords
        family_keywords = ['family', 'birthday', 'anniversary', 'dinner',
                          'vacation', 'holiday', 'kids', 'persy', 'viola']

        # School keywords
        school_keywords = ['school', 'class', 'exam', 'test', 'homework',
                          'teacher', 'pta', 'field trip']

        # Health keywords
        health_keywords = ['doctor', 'dentist', 'appointment', 'checkup',
                          'therapy', 'medical', 'hospital']

        # Check calendar ID patterns first (more specific)
        calendar_id_lower = calendar_id.lower()
        if 'appointment' in calendar_id_lower or 'health' in calendar_id_lower:
            return EventCategory.HEALTH
        elif 'family' in calendar_id_lower:
            return EventCategory.FAMILY
        elif 'school' in calendar_id_lower:
            return EventCategory.SCHOOL
        elif 'work' in calendar_id_lower or 'hospital' in calendar_id_lower:
            return EventCategory.WORK
        elif 'personal' in calendar_id_lower:
            return EventCategory.PERSONAL

        # Check calendar type from config
        for cal_name, cal_info in self.calendars.items():
            if calendar_id == cal_info['id']:
                if cal_info['type'] == 'work':
                    return EventCategory.WORK
                elif cal_info['type'] == 'school':
                    return EventCategory.SCHOOL
                elif cal_info['type'] == 'family':
                    return EventCategory.FAMILY
                elif cal_info['type'] == 'health':
                    return EventCategory.HEALTH

        # Check event title for keywords
        if any(keyword in title for keyword in work_keywords):
            return EventCategory.WORK
        elif any(keyword in title for keyword in family_keywords):
            return EventCategory.FAMILY
        elif any(keyword in title for keyword in school_keywords):
            return EventCategory.SCHOOL
        elif any(keyword in title for keyword in health_keywords):
            return EventCategory.HEALTH
        elif 'travel' in title or 'flight' in title:
            return EventCategory.TRAVEL

        return EventCategory.PERSONAL

    def _calculate_severity(self, event1: Dict, event2: Dict) -> ConflictSeverity:
        """Calculate conflict severity based on event categories"""
        cat1 = self._categorize_event(event1)
        cat2 = self._categorize_event(event2)

        # Critical: Health appointments conflict with anything
        if cat1 == EventCategory.HEALTH or cat2 == EventCategory.HEALTH:
            return ConflictSeverity.CRITICAL

        # High: Work-family conflicts
        if (cat1 == EventCategory.WORK and cat2 == EventCategory.FAMILY) or \
           (cat1 == EventCategory.FAMILY and cat2 == EventCategory.WORK):
            return ConflictSeverity.HIGH

        # High: Double-booked work events
        if cat1 == EventCategory.WORK and cat2 == EventCategory.WORK:
            return ConflictSeverity.HIGH

        # High: School conflicts with work
        if (cat1 == EventCategory.SCHOOL and cat2 == EventCategory.WORK) or \
           (cat1 == EventCategory.WORK and cat2 == EventCategory.SCHOOL):
            return ConflictSeverity.HIGH

        # Medium: One work/school event
        if cat1 == EventCategory.WORK or cat2 == EventCategory.WORK or \
           cat1 == EventCategory.SCHOOL or cat2 == EventCategory.SCHOOL:
            return ConflictSeverity.MEDIUM

        # Low: Both personal events
        return ConflictSeverity.LOW

    def _events_overlap(self, event1: Dict, event2: Dict) -> bool:
        """Check if two events overlap in time"""
        start1 = datetime.fromisoformat(event1['start'].replace('Z', '+00:00'))
        end1 = datetime.fromisoformat(event1['end'].replace('Z', '+00:00'))
        start2 = datetime.fromisoformat(event2['start'].replace('Z', '+00:00'))
        end2 = datetime.fromisoformat(event2['end'].replace('Z', '+00:00'))

        # Events overlap if one starts before the other ends
        return start1 < end2 and start2 < end1

    def _generate_recommendations(self, conflict: Dict) -> List[str]:
        """Generate actionable recommendations for conflict resolution"""
        recommendations = []
        severity = conflict['severity']
        events = conflict['events']

        # Analyze event categories
        categories = [self._categorize_event(e) for e in events]

        if severity == ConflictSeverity.CRITICAL.value:
            recommendations.append("🚨 Immediate action required - health appointment conflict")
            recommendations.append("Reschedule non-health events immediately")

        elif severity == ConflictSeverity.HIGH.value:
            if EventCategory.WORK in categories and EventCategory.FAMILY in categories:
                recommendations.append("Consider delegating work meeting or joining remotely")
                recommendations.append("Explore flexible work arrangement for family commitment")
            elif all(cat == EventCategory.WORK for cat in categories):
                recommendations.append("Prioritize by importance - defer or delegate one meeting")
                recommendations.append("Consider combining meetings if topics overlap")

        elif severity == ConflictSeverity.MEDIUM.value:
            recommendations.append("Review if personal event can be rescheduled")
            recommendations.append("Consider shorter duration for flexible event")

        else:  # LOW
            recommendations.append("Minor conflict - consider if both are necessary")
            recommendations.append("Could combine activities if related")

        # Time-based recommendations
        overlap_duration = self._calculate_overlap_duration(events[0], events[1])
        if overlap_duration < 30:
            recommendations.append(f"Only {overlap_duration} minute overlap - might manage with adjusted times")

        return recommendations

    def _calculate_overlap_duration(self, event1: Dict, event2: Dict) -> int:
        """Calculate overlap duration in minutes"""
        start1 = datetime.fromisoformat(event1['start'].replace('Z', '+00:00'))
        end1 = datetime.fromisoformat(event1['end'].replace('Z', '+00:00'))
        start2 = datetime.fromisoformat(event2['start'].replace('Z', '+00:00'))
        end2 = datetime.fromisoformat(event2['end'].replace('Z', '+00:00'))

        overlap_start = max(start1, start2)
        overlap_end = min(end1, end2)

        if overlap_start < overlap_end:
            return int((overlap_end - overlap_start).total_seconds() / 60)
        return 0

    async def detect_conflicts(self, events: List[Dict],
                              start_date: datetime,
                              end_date: datetime) -> Dict:
        """
        Main conflict detection method

        Args:
            events: List of calendar events with calendar_id
            start_date: Start of detection period
            end_date: End of detection period

        Returns:
            Dict with conflicts organized by severity and recommendations
        """
        # Check cache first
        cached = await self._get_cached_conflicts(start_date, end_date, events)
        if cached:
            return cached

        conflicts = []

        # Compare all event pairs for conflicts
        for i, event1 in enumerate(events):
            for event2 in events[i+1:]:
                if self._events_overlap(event1, event2):
                    severity = self._calculate_severity(event1, event2)

                    conflict = {
                        "id": hashlib.md5(
                            f"{event1.get('id', '')}:{event2.get('id', '')}".encode()
                        ).hexdigest()[:8],
                        "severity": severity.value,
                        "events": [event1, event2],
                        "overlap_minutes": self._calculate_overlap_duration(event1, event2),
                        "recommendations": [],
                        "detected_at": datetime.now().isoformat()
                    }

                    # Add recommendations
                    conflict["recommendations"] = self._generate_recommendations(conflict)
                    conflicts.append(conflict)

        # Organize conflicts by severity
        result = {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "total_conflicts": len(conflicts),
                "critical": sum(1 for c in conflicts if c['severity'] == 'critical'),
                "high": sum(1 for c in conflicts if c['severity'] == 'high'),
                "medium": sum(1 for c in conflicts if c['severity'] == 'medium'),
                "low": sum(1 for c in conflicts if c['severity'] == 'low')
            },
            "conflicts": sorted(conflicts,
                              key=lambda x: ['critical', 'high', 'medium', 'low'].index(x['severity'])),
            "generated_at": datetime.now().isoformat()
        }

        # Cache results
        await self._cache_conflicts(start_date, end_date, events, result)

        return result

    async def find_conflict_free_slots(self, events: List[Dict],
                                      duration_minutes: int,
                                      start_date: datetime,
                                      end_date: datetime,
                                      working_hours: Tuple[int, int] = (9, 17)) -> List[Dict]:
        """
        Find available time slots without conflicts

        Args:
            events: List of existing events
            duration_minutes: Required duration for new event
            start_date: Start of search period
            end_date: End of search period
            working_hours: Tuple of (start_hour, end_hour) for working hours

        Returns:
            List of available time slots
        """
        available_slots = []

        # Sort events by start time
        sorted_events = sorted(events,
                              key=lambda x: datetime.fromisoformat(x['start'].replace('Z', '+00:00')))

        # Check each day in the period
        current_day = start_date.date()
        end_day = end_date.date()

        while current_day <= end_day:
            # Set working hours for the day
            day_start = datetime.combine(current_day,
                                        datetime.min.time().replace(hour=working_hours[0]))
            day_end = datetime.combine(current_day,
                                      datetime.min.time().replace(hour=working_hours[1]))

            # Get events for this day
            day_events = [
                e for e in sorted_events
                if datetime.fromisoformat(e['start'].replace('Z', '+00:00')).date() == current_day
            ]

            # Find gaps between events
            if not day_events:
                # Entire day is free
                if (day_end - day_start).total_seconds() / 60 >= duration_minutes:
                    available_slots.append({
                        "start": day_start.isoformat(),
                        "end": day_end.isoformat(),
                        "duration_minutes": int((day_end - day_start).total_seconds() / 60)
                    })
            else:
                # Check gap before first event
                first_event_start = datetime.fromisoformat(
                    day_events[0]['start'].replace('Z', '+00:00')
                )
                if first_event_start > day_start:
                    gap_minutes = (first_event_start - day_start).total_seconds() / 60
                    if gap_minutes >= duration_minutes:
                        available_slots.append({
                            "start": day_start.isoformat(),
                            "end": first_event_start.isoformat(),
                            "duration_minutes": int(gap_minutes)
                        })

                # Check gaps between events
                for i in range(len(day_events) - 1):
                    event_end = datetime.fromisoformat(
                        day_events[i]['end'].replace('Z', '+00:00')
                    )
                    next_event_start = datetime.fromisoformat(
                        day_events[i+1]['start'].replace('Z', '+00:00')
                    )

                    gap_minutes = (next_event_start - event_end).total_seconds() / 60
                    if gap_minutes >= duration_minutes:
                        available_slots.append({
                            "start": event_end.isoformat(),
                            "end": next_event_start.isoformat(),
                            "duration_minutes": int(gap_minutes)
                        })

                # Check gap after last event
                last_event_end = datetime.fromisoformat(
                    day_events[-1]['end'].replace('Z', '+00:00')
                )
                if last_event_end < day_end:
                    gap_minutes = (day_end - last_event_end).total_seconds() / 60
                    if gap_minutes >= duration_minutes:
                        available_slots.append({
                            "start": last_event_end.isoformat(),
                            "end": day_end.isoformat(),
                            "duration_minutes": int(gap_minutes)
                        })

            current_day += timedelta(days=1)

        return available_slots
