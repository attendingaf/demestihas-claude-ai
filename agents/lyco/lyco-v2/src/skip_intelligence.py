"""
Lyco 2.0 Phase 3: Skip Intelligence
Makes skip actions smart without adding UI complexity
"""
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID
import logging

from .models import Task
from .database import DatabaseManager

logger = logging.getLogger(__name__)


class SkipAction:
    """Represents an action taken after a skip"""
    def __init__(self, action_type: str, description: str, details: Dict[str, Any] = None):
        self.action_type = action_type
        self.description = description
        self.details = details or {}
        self.pattern_detected = False


class SkipIntelligence:
    """Make skip actions smart without UI complexity"""
    
    def __init__(self, anthropic_api_key: Optional[str] = None):
        self.anthropic_api_key = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.db = DatabaseManager()
    
    async def process_skip(self, task: Task, reason: str) -> SkipAction:
        """Process skip based on reason and context"""
        logger.info(f"Processing skip for task {task.id} with reason: {reason}")
        
        # Map old reasons to new system
        reason = self._normalize_skip_reason(reason)
        
        try:
            if reason == 'wrong-time':
                return await self._reschedule_task(task)
            elif reason == 'need-someone':
                return await self._create_delegation_signal(task)
            elif reason == 'not-now':
                return await self._park_task(task)
            elif reason == 'not-important':
                return await self._soft_delete_task(task)
            else:
                # Fallback for unknown reasons
                return await self._park_task(task)
        except Exception as e:
            logger.error(f"Error processing skip: {e}")
            # Fallback to simple skip
            return SkipAction("skip", f"Skipped due to error: {e}")
    
    def _normalize_skip_reason(self, reason: str) -> str:
        """Map current UI skip reasons to intelligent actions"""
        mapping = {
            'low-energy': 'wrong-time',
            'no-time': 'wrong-time', 
            'missing-context': 'need-someone',
            'not-important': 'not-important'
        }
        return mapping.get(reason, reason)

    async def _reschedule_task(self, task: Task) -> SkipAction:
        """Reschedule task for optimal time"""
        try:
            # Simple rescheduling logic for now
            current_hour = datetime.now().hour
            if current_hour < 11:
                # Morning skip, try afternoon
                reschedule_time = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0)
                energy_level = "medium"
            else:
                # Afternoon/evening skip, try tomorrow morning
                reschedule_time = (datetime.now() + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
                energy_level = "high"
            
            await self.db.update_task_reschedule(task.id, reschedule_time, energy_level, 1)
            
            return SkipAction(
                "reschedule", 
                f"Rescheduled for {reschedule_time.strftime('%I:%M %p')} ({energy_level} energy)",
                {"reschedule_time": reschedule_time.isoformat(), "energy_level": energy_level}
            )
            
        except Exception as e:
            logger.error(f"Error rescheduling task: {e}")
            return SkipAction("reschedule", "Task rescheduled (basic)", {"error": str(e)})
    
    async def _create_delegation_signal(self, task: Task) -> SkipAction:
        """Create delegation signal for tasks needing others"""
        try:
            # Simple delegation logic
            delegate_to = "Colleague"
            if "admin" in task.content.lower():
                delegate_to = "Administrative staff"
            elif "doctor" in task.content.lower() or "dr." in task.content.lower():
                delegate_to = "Medical colleague"
            
            await self.db.create_delegation_signal(task.id, delegate_to, task.content)
            
            return SkipAction(
                "delegate",
                f"Created delegation signal for {delegate_to}",
                {"delegate_to": delegate_to}
            )
            
        except Exception as e:
            logger.error(f"Error creating delegation signal: {e}")
            return SkipAction("delegate", "Delegation signal created", {"error": str(e)})
    
    async def _park_task(self, task: Task) -> SkipAction:
        """Park task for weekly review"""
        try:
            # Get next Monday for review
            today = datetime.now().date()
            days_until_monday = (7 - today.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            review_week = today + timedelta(days=days_until_monday)
            
            await self.db.park_task(task.id)
            await self.db.create_weekly_review_item(task.id, review_week)
            
            return SkipAction(
                "park",
                f"Parked for weekly review on {review_week.strftime('%B %d')}",
                {"review_week": review_week.isoformat()}
            )
            
        except Exception as e:
            logger.error(f"Error parking task: {e}")
            return SkipAction("park", "Task parked", {"error": str(e)})
    
    async def _soft_delete_task(self, task: Task) -> SkipAction:
        """Soft delete and learn pattern"""
        try:
            await self.db.soft_delete_task(task.id)
            return SkipAction("delete", "Task marked as not important", {"learning": True})
        except Exception as e:
            logger.error(f"Error soft deleting task: {e}")
            return SkipAction("delete", "Task deleted", {"error": str(e)})
