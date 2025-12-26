"""
Lyco 2.0 Phase 3: Pattern Learning
Learn from skip patterns to improve classification
"""
import os
from datetime import datetime
from typing import Optional
from uuid import UUID
import logging

from .models import Task
from .database import DatabaseManager

logger = logging.getLogger(__name__)


class PatternLearner:
    """Learn from skip patterns to improve classification"""
    
    def __init__(self, anthropic_api_key: Optional[str] = None):
        self.anthropic_api_key = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.db = DatabaseManager()
    
    async def analyze_skip(self, task: Task, reason: str):
        """Analyze skip pattern and potentially adjust behavior"""
        try:
            # Extract pattern from task
            pattern = await self._extract_pattern(task)
            
            # Check if pattern exists
            existing = await self._get_skip_pattern(pattern, reason)
            
            if existing and existing.get('skip_count', 0) >= 2:
                # Third similar skip - auto-adjust
                await self._auto_adjust_behavior(pattern, reason)
            else:
                # Track the pattern
                await self._increment_skip_pattern(pattern, reason)
                
        except Exception as e:
            logger.error(f"Error analyzing skip pattern: {e}")
    
    async def _extract_pattern(self, task: Task) -> str:
        """Extract a general pattern from this task"""
        content_lower = task.content.lower()
        
        # Simple pattern extraction based on keywords
        if any(word in content_lower for word in ['email', 'reply', 'respond']):
            return "Email response"
        elif any(word in content_lower for word in ['meeting', 'call', 'zoom']):
            return "Meeting preparation"
        elif any(word in content_lower for word in ['report', 'document', 'write']):
            return "Document creation"
        elif any(word in content_lower for word in ['review', 'read', 'check']):
            return "Review task"
        elif any(word in content_lower for word in ['schedule', 'appointment', 'book']):
            return "Scheduling task"
        else:
            return "General task"
    
    async def _get_skip_pattern(self, pattern: str, reason: str) -> Optional[dict]:
        """Get existing skip pattern"""
        try:
            result = self.db.client.table('skip_patterns')                .select("*")                .eq('task_pattern', pattern)                .eq('skip_reason', reason)                .execute()
            
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting skip pattern: {e}")
            return None
    
    async def _increment_skip_pattern(self, pattern: str, reason: str):
        """Increment or create skip pattern count"""
        try:
            existing = await self._get_skip_pattern(pattern, reason)
            
            if existing:
                # Update existing pattern
                self.db.client.table('skip_patterns')                    .update({
                        'skip_count': existing['skip_count'] + 1,
                        'last_seen': datetime.now().isoformat()
                    })                    .eq('id', existing['id'])                    .execute()
            else:
                # Create new pattern
                new_pattern = {
                    'task_pattern': pattern,
                    'skip_reason': reason,
                    'skip_count': 1,
                    'user_id': 'mene@beltlineconsulting.co'
                }
                self.db.client.table('skip_patterns').insert(new_pattern).execute()
                
        except Exception as e:
            logger.error(f"Error incrementing skip pattern: {e}")
    
    async def _auto_adjust_behavior(self, pattern: str, reason: str):
        """Auto-adjust behavior after 3 similar skips"""
        try:
            logger.info(f"Auto-adjusting behavior for pattern: {pattern}, reason: {reason}")
            
            # Set auto-action based on reason
            auto_action = None
            if reason in ['low-energy', 'wrong-time']:
                auto_action = 'auto_reschedule'
            elif reason == 'not-important':
                auto_action = 'auto_skip'
            elif reason == 'missing-context':
                auto_action = 'auto_delegate'
            
            if auto_action:
                # Update pattern with auto-action
                self.db.client.table('skip_patterns')                    .update({'auto_action': auto_action})                    .eq('task_pattern', pattern)                    .eq('skip_reason', reason)                    .execute()
                
                logger.info(f"Set auto-action {auto_action} for pattern {pattern}")
                
        except Exception as e:
            logger.error(f"Error auto-adjusting behavior: {e}")
    
    async def get_auto_action_for_task(self, task: Task) -> Optional[str]:
        """Check if task matches a pattern with auto-action"""
        try:
            pattern = await self._extract_pattern(task)
            
            result = self.db.client.table('skip_patterns')                .select("auto_action")                .eq('task_pattern', pattern)                .not_.is_('auto_action', 'null')                .execute()
            
            if result.data:
                return result.data[0]['auto_action']
                
            return None
            
        except Exception as e:
            logger.error(f"Error getting auto-action: {e}")
            return None
