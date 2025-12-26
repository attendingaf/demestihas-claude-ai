#!/usr/bin/env python3
"""
Nina Agent - Au Pair Scheduling Specialist
Manages Viola's schedule through natural language commands
"""

import os
import asyncio
import logging
import json
import redis.asyncio as redis
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Any
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta, MO, TU, WE, TH, FR, SA, SU
import pytz

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
TIMEZONE = pytz.timezone('America/New_York')  # Adjust to family timezone

class NinaSchedulingAgent:
    """Au pair scheduling specialist agent"""
    
    def __init__(self):
        self.redis_client = None
        self.baseline_schedule = {
            "monday": {"start": "07:00", "end": "19:00", "working": True},
            "tuesday": {"start": "07:00", "end": "19:00", "working": True},
            "wednesday": {"start": "07:00", "end": "19:00", "working": True},
            "thursday": {"start": "07:00", "end": "19:00", "working": True},
            "friday": {"start": "07:00", "end": "19:00", "working": True},
            "saturday": {"working": False},
            "sunday": {"working": False}
        }
    
    async def initialize(self):
        """Initialize Redis connection and load baseline schedule"""
        try:
            self.redis_client = await redis.from_url(REDIS_URL, decode_responses=True)
            await self.redis_client.ping()
            logger.info("✅ Nina: Redis connection established")
            
            # Load or create baseline schedule
            baseline = await self.redis_client.get("schedule:baseline")
            if not baseline:
                await self.redis_client.set(
                    "schedule:baseline", 
                    json.dumps(self.baseline_schedule)
                )
                logger.info("📅 Nina: Created baseline schedule")
            else:
                self.baseline_schedule = json.loads(baseline)
                logger.info("📅 Nina: Loaded existing baseline schedule")
                
        except Exception as e:
            logger.error(f"❌ Nina: Redis connection failed: {e}")
            self.redis_client = None
    
    def parse_date_from_text(self, text: str) -> Optional[datetime]:
        """Parse date from natural language"""
        text_lower = text.lower()
        today = datetime.now(TIMEZONE).date()
        
        # Day of week references
        weekdays = {
            'monday': MO, 'tuesday': TU, 'wednesday': WE,
            'thursday': TH, 'friday': FR, 'saturday': SA, 'sunday': SU
        }
        
        # Check for specific day names
        for day_name, day_const in weekdays.items():
            if day_name in text_lower:
                # Find next occurrence of this day
                next_day = today + relativedelta(weekday=day_const)
                if next_day <= today:
                    next_day = today + relativedelta(weekday=day_const, weeks=+1)
                return datetime.combine(next_day, time(0, 0), tzinfo=TIMEZONE)
        
        # Check for relative dates
        if 'tomorrow' in text_lower:
            return datetime.combine(today + timedelta(days=1), time(0, 0), tzinfo=TIMEZONE)
        elif 'today' in text_lower:
            return datetime.combine(today, time(0, 0), tzinfo=TIMEZONE)
        elif 'next week' in text_lower:
            return datetime.combine(today + timedelta(days=7), time(0, 0), tzinfo=TIMEZONE)
        elif 'this week' in text_lower:
            # Start of current week
            start_of_week = today - timedelta(days=today.weekday())
            return datetime.combine(start_of_week, time(0, 0), tzinfo=TIMEZONE)
        
        # Try to parse as date
        try:
            parsed = date_parser.parse(text, fuzzy=True)
            return TIMEZONE.localize(parsed) if parsed.tzinfo is None else parsed
        except:
            return None
    
    def parse_time_from_text(self, text: str) -> Optional[Dict[str, str]]:
        """Parse time or time range from text"""
        import re
        text_lower = text.lower()
        
        # Common time patterns
        time_patterns = [
            (r'(\d{1,2})\s*-\s*(\d{1,2})\s*([ap]m)', 'range_with_ampm'),
            (r'(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})', 'range_24h'),
            (r'(\d{1,2})\s*([ap]m)\s*-\s*(\d{1,2})\s*([ap]m)', 'range_both_ampm'),
            (r'from\s*(\d{1,2})\s*to\s*(\d{1,2})', 'range_from_to'),
            (r'afternoon', 'keyword'),
            (r'morning', 'keyword'),
            (r'evening', 'keyword'),
            (r'all day', 'keyword'),
            (r'off', 'keyword')
        ]
        
        for pattern, pattern_type in time_patterns:
            match = re.search(pattern, text_lower)
            if match:
                if pattern_type == 'keyword':
                    if 'afternoon' in text_lower:
                        return {"start": "12:00", "end": "17:00"}
                    elif 'morning' in text_lower:
                        return {"start": "07:00", "end": "12:00"}
                    elif 'evening' in text_lower:
                        return {"start": "17:00", "end": "22:00"}
                    elif 'all day' in text_lower:
                        return {"start": "07:00", "end": "19:00"}
                    elif 'off' in text_lower:
                        return {"off": True}
                elif pattern_type == 'range_with_ampm':
                    start_hour = int(match.group(1))
                    end_hour = int(match.group(2))
                    ampm = match.group(3)
                    if ampm == 'pm' and start_hour != 12:
                        start_hour += 12
                        end_hour += 12
                    return {"start": f"{start_hour:02d}:00", "end": f"{end_hour:02d}:00"}
                elif pattern_type == 'range_both_ampm':
                    start_hour = int(match.group(1))
                    start_ampm = match.group(2)
                    end_hour = int(match.group(3))
                    end_ampm = match.group(4)
                    if start_ampm == 'pm' and start_hour != 12:
                        start_hour += 12
                    if end_ampm == 'pm' and end_hour != 12:
                        end_hour += 12
                    return {"start": f"{start_hour:02d}:00", "end": f"{end_hour:02d}:00"}
        
        return None
    
    async def update_schedule(self, command: str, user_name: str = "User") -> Dict:
        """Process schedule update command"""
        command_lower = command.lower()
        
        # Parse date from command
        target_date = self.parse_date_from_text(command)
        
        # Parse time from command
        time_info = self.parse_time_from_text(command)
        
        # Determine action type
        if any(word in command_lower for word in ['off', 'away', 'vacation', 'sick']):
            return await self._mark_day_off(target_date, command, user_name)
        elif any(word in command_lower for word in ['coverage', 'need', 'babysitter', 'watch']):
            return await self._request_coverage(target_date, time_info, command, user_name)
        elif any(word in command_lower for word in ['normal', 'regular', 'clear', 'reset']):
            return await self._reset_schedule(user_name)
        elif any(word in command_lower for word in ['extra', 'overtime', 'worked']):
            return await self._log_overtime(target_date, time_info, command, user_name)
        else:
            return await self._update_hours(target_date, time_info, command, user_name)
    
    async def _mark_day_off(self, date: datetime, reason: str, user_name: str) -> Dict:
        """Mark a day as off"""
        if not date:
            return {"success": False, "message": "Could not determine which day to mark off"}
        
        date_str = date.strftime('%Y-%m-%d')
        exception = {
            "date": date_str,
            "working": False,
            "reason": reason,
            "updated_by": user_name,
            "updated_at": datetime.now(TIMEZONE).isoformat()
        }
        
        if self.redis_client:
            await self.redis_client.set(
                f"schedule:exceptions:{date_str}",
                json.dumps(exception),
                ex=86400 * 30  # Expire after 30 days
            )
        
        day_name = date.strftime('%A')
        return {
            "success": True,
            "message": f"✅ Marked {day_name} ({date_str}) as off for Viola",
            "exception": exception,
            "coverage_needed": True
        }
    
    async def _request_coverage(self, date: datetime, time_info: Dict, reason: str, user_name: str) -> Dict:
        """Request coverage for specific time"""
        if not date:
            date = datetime.now(TIMEZONE)
        
        date_str = date.strftime('%Y-%m-%d')
        coverage = {
            "date": date_str,
            "time": time_info or {"start": "TBD", "end": "TBD"},
            "reason": reason,
            "requested_by": user_name,
            "requested_at": datetime.now(TIMEZONE).isoformat(),
            "status": "pending"
        }
        
        if self.redis_client:
            await self.redis_client.set(
                f"schedule:coverage:{date_str}",
                json.dumps(coverage),
                ex=86400 * 7  # Expire after 7 days
            )
        
        time_str = f"{time_info.get('start', 'TBD')}-{time_info.get('end', 'TBD')}" if time_info else "time TBD"
        return {
            "success": True,
            "message": f"📋 Coverage requested for {date.strftime('%A')} ({date_str}) {time_str}",
            "coverage_request": coverage,
            "create_task": True,
            "task_title": f"Find coverage for {date_str} {time_str}"
        }
    
    async def _reset_schedule(self, user_name: str) -> Dict:
        """Reset to normal schedule"""
        if self.redis_client:
            # Clear all exceptions
            keys = await self.redis_client.keys("schedule:exceptions:*")
            if keys:
                await self.redis_client.delete(*keys)
        
        return {
            "success": True,
            "message": "🔄 Viola's schedule reset to normal (M-F 7am-7pm, weekends off)",
            "action": "reset",
            "updated_by": user_name
        }
    
    async def _log_overtime(self, date: datetime, time_info: Dict, description: str, user_name: str) -> Dict:
        """Log overtime/comp time"""
        if not date:
            date = datetime.now(TIMEZONE)
        
        # Calculate hours worked
        hours = 0
        if time_info and 'start' in time_info and 'end' in time_info:
            start = datetime.strptime(time_info['start'], '%H:%M')
            end = datetime.strptime(time_info['end'], '%H:%M')
            hours = (end - start).total_seconds() / 3600
        
        # Update comp time balance
        if self.redis_client:
            current = await self.redis_client.get("schedule:comp_time")
            comp_balance = float(current) if current else 0.0
            comp_balance += hours
            await self.redis_client.set("schedule:comp_time", str(comp_balance))
        
        return {
            "success": True,
            "message": f"✅ Logged {hours:.1f} hours overtime for {date.strftime('%Y-%m-%d')}",
            "overtime": {
                "date": date.strftime('%Y-%m-%d'),
                "hours": hours,
                "new_balance": comp_balance if self.redis_client else hours
            }
        }
    
    async def _update_hours(self, date: datetime, time_info: Dict, command: str, user_name: str) -> Dict:
        """Update working hours for a specific day"""
        if not date or not time_info:
            return {"success": False, "message": "Could not parse date or time from command"}
        
        date_str = date.strftime('%Y-%m-%d')
        exception = {
            "date": date_str,
            "working": True,
            "hours": time_info,
            "reason": command,
            "updated_by": user_name,
            "updated_at": datetime.now(TIMEZONE).isoformat()
        }
        
        if self.redis_client:
            await self.redis_client.set(
                f"schedule:exceptions:{date_str}",
                json.dumps(exception),
                ex=86400 * 30
            )
        
        return {
            "success": True,
            "message": f"✅ Updated schedule for {date.strftime('%A')} ({date_str}): {time_info.get('start')}-{time_info.get('end')}",
            "exception": exception
        }
    
    async def query_schedule(self, query: str) -> Dict:
        """Query schedule information"""
        query_lower = query.lower()
        
        if 'week' in query_lower or 'schedule' in query_lower:
            return await self._get_weekly_schedule()
        elif 'comp' in query_lower or 'overtime' in query_lower:
            return await self._get_comp_balance()
        elif 'coverage' in query_lower:
            return await self._get_coverage_requests()
        else:
            # Try to get specific day
            date = self.parse_date_from_text(query)
            if date:
                return await self._get_day_schedule(date)
            else:
                return await self._get_weekly_schedule()
    
    async def _get_weekly_schedule(self) -> Dict:
        """Get schedule for current week"""
        today = datetime.now(TIMEZONE).date()
        start_of_week = today - timedelta(days=today.weekday())
        
        schedule_text = "📅 **Viola's Schedule This Week**\n\n"
        
        for i in range(7):
            current_date = start_of_week + timedelta(days=i)
            date_str = current_date.strftime('%Y-%m-%d')
            day_name = current_date.strftime('%A')
            
            # Check for exceptions
            exception = None
            if self.redis_client:
                exception_data = await self.redis_client.get(f"schedule:exceptions:{date_str}")
                if exception_data:
                    exception = json.loads(exception_data)
            
            if exception:
                if not exception.get('working', True):
                    schedule_text += f"• {day_name}: OFF\n"
                else:
                    hours = exception.get('hours', {})
                    schedule_text += f"• {day_name}: {hours.get('start', '?')}-{hours.get('end', '?')}\n"
            else:
                # Use baseline
                baseline_day = self.baseline_schedule.get(day_name.lower())
                if baseline_day and baseline_day.get('working'):
                    schedule_text += f"• {day_name}: {baseline_day['start']}-{baseline_day['end']}\n"
                else:
                    schedule_text += f"• {day_name}: OFF\n"
        
        return {
            "success": True,
            "message": schedule_text,
            "type": "weekly_schedule"
        }
    
    async def _get_day_schedule(self, date: datetime) -> Dict:
        """Get schedule for specific day"""
        date_str = date.strftime('%Y-%m-%d')
        day_name = date.strftime('%A')
        
        # Check for exception
        exception = None
        if self.redis_client:
            exception_data = await self.redis_client.get(f"schedule:exceptions:{date_str}")
            if exception_data:
                exception = json.loads(exception_data)
        
        if exception:
            if not exception.get('working', True):
                message = f"Viola is OFF on {day_name} ({date_str})"
            else:
                hours = exception.get('hours', {})
                message = f"Viola works {hours.get('start', '?')}-{hours.get('end', '?')} on {day_name} ({date_str})"
        else:
            baseline_day = self.baseline_schedule.get(day_name.lower())
            if baseline_day and baseline_day.get('working'):
                message = f"Viola works {baseline_day['start']}-{baseline_day['end']} on {day_name} ({date_str})"
            else:
                message = f"Viola is OFF on {day_name} ({date_str})"
        
        return {
            "success": True,
            "message": message,
            "date": date_str
        }
    
    async def _get_comp_balance(self) -> Dict:
        """Get comp time balance"""
        balance = 0.0
        if self.redis_client:
            comp = await self.redis_client.get("schedule:comp_time")
            balance = float(comp) if comp else 0.0
        
        return {
            "success": True,
            "message": f"💰 Viola's comp time balance: {balance:.1f} hours",
            "comp_balance": balance
        }
    
    async def _get_coverage_requests(self) -> Dict:
        """Get pending coverage requests"""
        requests = []
        if self.redis_client:
            keys = await self.redis_client.keys("schedule:coverage:*")
            for key in keys:
                coverage_data = await self.redis_client.get(key)
                if coverage_data:
                    requests.append(json.loads(coverage_data))
        
        if requests:
            message = "📋 **Pending Coverage Requests**\n\n"
            for req in requests:
                message += f"• {req['date']}: {req.get('time', {}).get('start', 'TBD')}-{req.get('time', {}).get('end', 'TBD')}\n"
        else:
            message = "No pending coverage requests"
        
        return {
            "success": True,
            "message": message,
            "coverage_requests": requests
        }
    
    async def detect_gaps(self) -> List[Dict]:
        """Detect coverage gaps (for proactive alerts)"""
        gaps = []
        today = datetime.now(TIMEZONE).date()
        
        # Check next 7 days
        for i in range(7):
            check_date = today + timedelta(days=i)
            date_str = check_date.strftime('%Y-%m-%d')
            day_name = check_date.strftime('%A').lower()
            
            # Get schedule for this day
            exception = None
            if self.redis_client:
                exception_data = await self.redis_client.get(f"schedule:exceptions:{date_str}")
                if exception_data:
                    exception = json.loads(exception_data)
            
            # Check if Viola is off on a normally working day
            baseline_day = self.baseline_schedule.get(day_name)
            if baseline_day and baseline_day.get('working'):
                if exception and not exception.get('working', True):
                    # Gap detected - normally working but marked off
                    gaps.append({
                        "date": date_str,
                        "type": "no_coverage",
                        "normal_hours": f"{baseline_day['start']}-{baseline_day['end']}",
                        "reason": exception.get('reason', 'Day off')
                    })
        
        return gaps

# Create global instance
nina_agent = NinaSchedulingAgent()

# Export functions for Yanay integration
async def process_schedule_command(command: str, user_name: str = "User") -> Dict:
    """Process a schedule-related command"""
    if not nina_agent.redis_client:
        await nina_agent.initialize()
    
    command_lower = command.lower()
    
    # Determine if query or update
    if any(word in command_lower for word in ['what', 'show', 'check', 'when', 'schedule']):
        return await nina_agent.query_schedule(command)
    else:
        return await nina_agent.update_schedule(command, user_name)

async def check_coverage_gaps() -> List[Dict]:
    """Check for coverage gaps (called periodically)"""
    if not nina_agent.redis_client:
        await nina_agent.initialize()
    return await nina_agent.detect_gaps()
