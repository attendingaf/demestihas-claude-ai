"""
Rounds Mode - Medical-style task review system
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from uuid import UUID
import json

from src.database import DatabaseManager
from src.pattern_learner import PatternLearner


class RoundsMode:
    """Manages time-boxed task review sessions"""

    TASK_TIME_LIMIT = 30  # seconds per task

    def __init__(self):
        self.db = DatabaseManager()
        self.pattern_learner = PatternLearner()
        self.current_session = None

    async def start_rounds(self, rounds_type: str = "morning", energy_level: Optional[str] = None) -> Dict[str, Any]:
        """Start a new rounds session"""

        # Determine energy level based on time if not provided
        if not energy_level:
            current_hour = datetime.now().hour
            if 9 <= current_hour < 11:
                energy = "high"
            elif 14 <= current_hour < 16:
                energy = "medium"
            else:
                energy = "low"
        else:
            energy = energy_level

        # Get categorized tasks
        tasks = await self.get_categorized_tasks(energy, rounds_type)

        if not tasks:
            return {
                "status": "no_tasks",
                "message": "No tasks require review"
            }

        # Create session
        session_id = await self.db.execute(
            """
            INSERT INTO rounds_sessions (type, tasks_total, energy_level)
            VALUES ($1, $2, $3)
            RETURNING id
            """,
            rounds_type,
            len(tasks),
            energy
        )

        self.current_session = {
            "id": session_id,
            "type": rounds_type,
            "energy": energy,
            "tasks": tasks,
            "current_index": 0,
            "decisions": [],
            "started_at": datetime.now()
        }

        # Calculate estimated time
        estimated_minutes = (len(tasks) * self.TASK_TIME_LIMIT) / 60

        return {
            "session_id": session_id,
            "type": rounds_type,
            "energy_level": energy,
            "tasks_count": len(tasks),
            "estimated_time": f"{estimated_minutes:.1f} minutes",
            "tasks_by_category": self.group_tasks_by_category(tasks),
            "first_task": self.format_task_for_review(tasks[0]) if tasks else None
        }

    async def get_categorized_tasks(self, energy: str, rounds_type: str) -> List[Dict]:
        """Get tasks categorized for rounds review"""

        # Build query based on rounds type
        if rounds_type == "morning":
            # High-energy and urgent tasks
            query = """
                SELECT t.*, tc.energy_level, tc.context, tc.project,
                       tc.time_sensitivity, tc.skip_count, tc.pattern_detected
                FROM tasks t
                LEFT JOIN task_categories tc ON t.id = tc.task_id
                WHERE t.completed_at IS NULL
                  AND t.deleted_at IS NULL
                  AND (tc.energy_level = $1 OR tc.time_sensitivity = 'urgent'
                       OR t.deadline <= NOW() + INTERVAL '1 day')
                ORDER BY
                  CASE WHEN t.deadline <= NOW() + INTERVAL '1 day' THEN 0 ELSE 1 END,
                  CASE WHEN tc.energy_level = $1 THEN 0 ELSE 1 END,
                  tc.skip_count ASC,
                  t.created_at ASC
                LIMIT 20
            """
            params = [energy]

        elif rounds_type == "evening":
            # Admin and cleanup tasks
            query = """
                SELECT t.*, tc.energy_level, tc.context, tc.project,
                       tc.time_sensitivity, tc.skip_count, tc.pattern_detected
                FROM tasks t
                LEFT JOIN task_categories tc ON t.id = tc.task_id
                WHERE t.completed_at IS NULL
                  AND t.deleted_at IS NULL
                  AND (tc.energy_level = 'low' OR tc.context = 'admin')
                ORDER BY tc.skip_count DESC, t.created_at ASC
                LIMIT 15
            """
            params = []

        elif rounds_type == "weekly":
            # All pending tasks for weekly review
            query = """
                SELECT t.*, tc.energy_level, tc.context, tc.project,
                       tc.time_sensitivity, tc.skip_count, tc.pattern_detected
                FROM tasks t
                LEFT JOIN task_categories tc ON t.id = tc.task_id
                WHERE t.completed_at IS NULL
                  AND t.deleted_at IS NULL
                  AND t.parked_at IS NOT NULL
                ORDER BY t.parked_at ASC
                LIMIT 50
            """
            params = []

        else:  # emergency
            # Most urgent tasks only
            query = """
                SELECT t.*, tc.energy_level, tc.context, tc.project,
                       tc.time_sensitivity, tc.skip_count, tc.pattern_detected
                FROM tasks t
                LEFT JOIN task_categories tc ON t.id = tc.task_id
                WHERE t.completed_at IS NULL
                  AND t.deleted_at IS NULL
                  AND (t.deadline <= NOW() + INTERVAL '4 hours'
                       OR tc.time_sensitivity = 'critical')
                ORDER BY t.deadline ASC NULLS LAST
                LIMIT 10
            """
            params = []

        rows = await self.db.fetch_all(query, *params)

        # Ensure categories exist for all tasks
        tasks = []
        for row in rows:
            task_dict = dict(row)

            # Ensure category exists
            if not task_dict.get('energy_level'):
                await self.categorize_task(task_dict)

            tasks.append(task_dict)

        return tasks

    async def categorize_task(self, task: Dict) -> None:
        """Auto-categorize a task if not already categorized"""

        # Simple keyword-based categorization
        content_lower = task['content'].lower()

        # Energy level
        if any(word in content_lower for word in ['strategic', 'plan', 'review', 'analysis']):
            energy = 'high'
        elif any(word in content_lower for word in ['meeting', 'call', 'discuss']):
            energy = 'medium'
        else:
            energy = 'low'

        # Context
        if any(word in content_lower for word in ['team', 'staff', 'employee']):
            context = 'team'
        elif any(word in content_lower for word in ['budget', 'finance', 'expense']):
            context = 'finance'
        elif any(word in content_lower for word in ['email', 'reply', 'respond']):
            context = 'communication'
        else:
            context = 'work'

        # Time sensitivity
        if task.get('deadline'):
            deadline = task['deadline']
            if deadline <= datetime.now() + timedelta(hours=4):
                time_sensitivity = 'critical'
            elif deadline <= datetime.now() + timedelta(days=1):
                time_sensitivity = 'urgent'
            else:
                time_sensitivity = 'normal'
        else:
            time_sensitivity = 'flexible'

        # Store categorization
        await self.db.execute(
            """
            INSERT INTO task_categories
            (task_id, energy_level, context, time_sensitivity)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (task_id) DO UPDATE
            SET energy_level = $2, context = $3, time_sensitivity = $4,
                updated_at = NOW()
            """,
            task['id'],
            energy,
            context,
            time_sensitivity
        )

    def group_tasks_by_category(self, tasks: List[Dict]) -> Dict[str, List]:
        """Group tasks by energy level for display"""
        grouped = {
            'high': [],
            'medium': [],
            'low': [],
            'uncategorized': []
        }

        for task in tasks:
            energy = task.get('energy_level', 'uncategorized')
            if energy not in grouped:
                energy = 'uncategorized'

            grouped[energy].append({
                'id': str(task['id']),
                'content': task['content'][:100],
                'deadline': task.get('deadline'),
                'skip_count': task.get('skip_count', 0),
                'time_sensitivity': task.get('time_sensitivity', 'normal')
            })

        # Remove empty categories
        return {k: v for k, v in grouped.items() if v}

    def format_task_for_review(self, task: Dict) -> Dict:
        """Format a single task for rounds review"""
        # Safe datetime formatting
        def safe_isoformat(dt_value):
            if dt_value is None:
                return None
            if isinstance(dt_value, str):
                return dt_value  # Already formatted
            if hasattr(dt_value, 'isoformat'):
                return dt_value.isoformat()
            return str(dt_value)
            
        return {
            'id': str(task['id']),
            'content': task['content'],
            'energy_level': task.get('energy_level', 'unknown'),
            'context': task.get('context', 'general'),
            'project': task.get('project'),
            'deadline': safe_isoformat(task.get('deadline')),
            'time_estimate': task.get('time_estimate'),
            'skip_count': task.get('skip_count', 0),
            'pattern_detected': task.get('pattern_detected', False),
            'pattern_warning': self.get_pattern_warning(task),
            'suggested_decision': self.suggest_decision(task),
            'metadata': {
                'created': safe_isoformat(task.get('created_at')),
                'last_skipped': safe_isoformat(task.get('last_skipped'))
            }
        }

    def get_pattern_warning(self, task: Dict) -> Optional[str]:
        """Get warning if task shows problematic patterns"""
        skip_count = task.get('skip_count', 0)

        if skip_count >= 5:
            return f"Skipped {skip_count} times - consider deletion or delegation"
        elif skip_count >= 3:
            return f"Skipped {skip_count} times - pattern detected"
        elif task.get('pattern_detected'):
            return "Similar tasks frequently skipped"

        return None

    def suggest_decision(self, task: Dict) -> str:
        """AI-suggested decision based on patterns"""
        skip_count = task.get('skip_count', 0)
        energy = task.get('energy_level', 'medium')
        current_energy = self.current_session['energy'] if self.current_session else 'medium'

        # High skip count suggests deletion
        if skip_count >= 5:
            return 'delete'

        # Energy mismatch suggests deferral
        if energy == 'high' and current_energy == 'low':
            return 'defer'

        # Urgent tasks should be done or delegated
        if task.get('time_sensitivity') == 'critical':
            return 'do_now' if current_energy != 'low' else 'delegate'

        # Default suggestion
        return 'defer' if skip_count >= 3 else 'do_now'

    async def process_decision(
        self,
        task_id: str,
        decision: str,
        decision_time: int = None
    ) -> Dict[str, Any]:
        """Process a rounds decision for a task"""

        if not self.current_session:
            return {"error": "No active rounds session"}

        task_uuid = UUID(task_id)

        # Record decision
        await self.db.execute(
            """
            INSERT INTO rounds_decisions
            (session_id, task_id, decision, decision_time, energy_match)
            VALUES ($1, $2, $3, $4, $5)
            """,
            self.current_session['id'],
            task_uuid,
            decision,
            decision_time,
            self.check_energy_match(task_id)
        )

        # Apply decision
        result = await self.apply_decision(task_uuid, decision)

        # Update session
        self.current_session['decisions'].append({
            'task_id': task_id,
            'decision': decision,
            'time': decision_time
        })
        self.current_session['current_index'] += 1

        # Check if session complete
        if self.current_session['current_index'] >= len(self.current_session['tasks']):
            return await self.complete_rounds()

        # Return next task
        next_task = self.current_session['tasks'][self.current_session['current_index']]

        return {
            'decision_applied': result,
            'next_task': self.format_task_for_review(next_task),
            'progress': {
                'current': self.current_session['current_index'] + 1,
                'total': len(self.current_session['tasks']),
                'percentage': ((self.current_session['current_index'] + 1) /
                              len(self.current_session['tasks'])) * 100
            }
        }

    def check_energy_match(self, task_id: str) -> bool:
        """Check if task energy matches current energy"""
        if not self.current_session:
            return False

        task = next((t for t in self.current_session['tasks']
                    if str(t['id']) == task_id), None)

        if not task:
            return False

        return task.get('energy_level') == self.current_session['energy']

    async def apply_decision(self, task_id: UUID, decision: str) -> Dict:
        """Apply the rounds decision to the task"""

        if decision == 'do_now':
            # Mark for immediate action (could open in main UI)
            return {
                'action': 'marked_for_action',
                'task_id': str(task_id),
                'url': f'http://localhost:8000/?task={task_id}'
            }

        elif decision == 'delegate':
            # Mark task for delegation (update existing task)
            await self.db.execute(
                """
                UPDATE tasks 
                SET skip_reason = 'Delegated during rounds',
                    skipped_at = NOW()
                WHERE id = $1
                """,
                task_id
            )
            return {'action': 'delegation_marked'}

        elif decision == 'defer':
            # Smart reschedule based on energy
            next_high_energy = datetime.now().replace(hour=9, minute=0)
            if datetime.now().hour >= 9:
                next_high_energy += timedelta(days=1)

            await self.db.execute(
                """
                UPDATE tasks
                SET rescheduled_for = $1,
                    skip_reason = 'Deferred during rounds'
                WHERE id = $2
                """,
                next_high_energy,
                task_id
            )
            return {'action': 'rescheduled', 'for': next_high_energy.isoformat()}

        elif decision == 'delete':
            # Soft delete
            await self.db.execute(
                """
                UPDATE tasks
                SET deleted_at = NOW(),
                    skip_reason = 'Deleted during rounds'
                WHERE id = $1
                """,
                task_id
            )

            # Learn from deletion
            await self.pattern_learner.learn_from_deletion(task_id)

            return {'action': 'deleted'}

        return {'action': 'unknown'}

    async def complete_rounds(self) -> Dict[str, Any]:
        """Complete the current rounds session"""

        if not self.current_session:
            return {"error": "No active session"}

        # Calculate stats
        duration = (datetime.now() - self.current_session['started_at']).seconds
        avg_decision_time = duration / len(self.current_session['decisions']) if self.current_session['decisions'] else 0

        # Update session
        await self.db.execute(
            """
            UPDATE rounds_sessions
            SET completed_at = NOW(),
                tasks_reviewed = $1,
                decisions = $2,
                avg_decision_time = $3
            WHERE id = $4
            """,
            len(self.current_session['decisions']),
            json.dumps(self.current_session['decisions']),
            int(avg_decision_time),
            self.current_session['id']
        )

        # Generate summary
        decision_counts = {}
        for d in self.current_session['decisions']:
            decision_counts[d['decision']] = decision_counts.get(d['decision'], 0) + 1

        summary = {
            'session_id': self.current_session['id'],
            'type': self.current_session['type'],
            'duration_minutes': duration / 60,
            'tasks_reviewed': len(self.current_session['decisions']),
            'tasks_total': len(self.current_session['tasks']),
            'decisions': decision_counts,
            'avg_decision_seconds': avg_decision_time,
            'energy_level': self.current_session['energy']
        }

        # Clear session
        self.current_session = None

        return {
            'status': 'completed',
            'summary': summary,
            'message': 'Rounds completed successfully'
        }

    async def get_rounds_history(self, limit: int = 10) -> List[Dict]:
        """Get history of rounds sessions"""

        rows = await self.db.fetch_all(
            """
            SELECT * FROM rounds_sessions
            WHERE completed_at IS NOT NULL
            ORDER BY completed_at DESC
            LIMIT $1
            """,
            limit
        )

        return [dict(row) for row in rows]
