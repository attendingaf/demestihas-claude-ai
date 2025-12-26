
"""
Lyco 2.0 Phase 3: Weekly Review
Generate weekly review email for parked tasks
"""
import os
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID
import logging

from .models import Task
from .database import DatabaseManager

logger = logging.getLogger(__name__)


class WeeklyReview:
    """Generate weekly review email for parked tasks"""
    
    def __init__(self):
        self.db = DatabaseManager()
    
    async def generate_weekly_email(self) -> str:
        """Generate weekly review email HTML"""
        try:
            result = self.db.client.table('tasks')                .select("*")                .not_.is_('parked_at', 'null')                .execute()
            
            tasks = [Task(**row) for row in result.data] if result.data else []
            
            if not tasks:
                return self._generate_empty_email()
            
            return self._generate_task_email(tasks)
            
        except Exception as e:
            logger.error(f"Error generating weekly email: {e}")
            return f"<html><body>Error: {e}</body></html>"
    
    def _generate_task_email(self, tasks: List[Task]) -> str:
        """Generate email with parked tasks"""
        html = f"""<html>
<body style="font-family: system-ui, sans-serif;">
<div style="background: #667eea; color: white; padding: 20px; text-align: center;">
<h2>🗓️ Lyco Weekly Review</h2>
</div>
<div style="padding: 20px;">
<p>You have <strong>{len(tasks)}</strong> parked tasks to review.</p>
"""
        
        for i, task in enumerate(tasks, 1):
            html += f"""<div style="border: 1px solid #ccc; padding: 10px; margin: 10px 0;">
<strong>{i}. {task.content}</strong><br>
Energy: {task.energy_level} | Time: {task.time_estimate} min
</div>"""
        
        html += """
<p><strong>Reply with task numbers</strong> to activate (e.g., "1, 3, 5")</p>
<p><strong>Reply "keep all"</strong> to keep all tasks parked</p>
</div>
</body>
</html>"""
        
        return html
    
    def _generate_empty_email(self) -> str:
        """Generate email when no tasks need review"""
        return """<html>
<body style="font-family: system-ui, sans-serif;">
<div style="background: #10b981; color: white; padding: 20px; text-align: center;">
<h2>✨ Lyco Weekly Review - All Clear!</h2>
<p>No parked tasks this week!</p>
</div>
</body>
</html>"""
