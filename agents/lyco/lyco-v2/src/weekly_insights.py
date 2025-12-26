"""
Lyco 2.0 Phase 4: Weekly Insights Generator
Generates personalized weekly analysis emails with actionable recommendations
"""
import json
import logging
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any, Tuple
import os

from .database import DatabaseManager
from .models import Task

logger = logging.getLogger(__name__)


class WeeklyInsightsGenerator:
    """Generate personalized weekly productivity insights"""

    def __init__(self):
        self.db = DatabaseManager()

        # Email configuration
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        self.email_user = os.environ.get('EMAIL_USER', '')
        self.email_password = os.environ.get('EMAIL_PASSWORD', '')
        self.recipient_email = os.environ.get('USER_EMAIL', 'mene@beltlineconsulting.co')

        # Generation thresholds
        self.MIN_TASKS_THRESHOLD = 10
        self.MIN_PATTERNS_THRESHOLD = 2

    async def should_generate_insights(self, week_start: datetime) -> bool:
        """Check if we should generate insights for this week"""
        # Check if already generated
        existing = await self.db.fetch_one("""
            SELECT id FROM weekly_insights
            WHERE week_start = $1
        """, week_start.date())

        if existing:
            logger.info(f"Insights already generated for week {week_start.date()}")
            return False

        # Check activity threshold
        week_end = week_start + timedelta(days=7)
        task_count = await self.db.fetch_one("""
            SELECT COUNT(*) as count FROM tasks
            WHERE created_at >= $1 AND created_at < $2
            AND (completed_at IS NOT NULL OR skipped_at IS NOT NULL)
        """, week_start, week_end)

        if not task_count or task_count["count"] < self.MIN_TASKS_THRESHOLD:
            logger.info(f"Insufficient activity ({task_count['count'] if task_count else 0} tasks) for insights")
            return False

        return True

    async def generate_insights(self, week_start: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate comprehensive weekly insights"""
        if not week_start:
            # Default to last Monday
            today = datetime.now().date()
            days_since_monday = today.weekday()
            week_start = datetime.combine(
                today - timedelta(days=days_since_monday + 7),
                datetime.min.time()
            )

        logger.info(f"Generating insights for week starting {week_start.date()}")

        try:
            week_end = week_start + timedelta(days=7)

            # Calculate core metrics
            metrics = await self._calculate_weekly_metrics(week_start, week_end)

            # Analyze patterns
            patterns = await self._analyze_weekly_patterns(week_start, week_end)

            # Generate recommendations
            recommendations = await self._generate_recommendations(metrics, patterns)

            # Get achievements
            achievements = await self._identify_achievements(metrics, patterns)

            # Compare with previous weeks
            comparison = await self._compare_with_previous_weeks(metrics, week_start)

            insights_data = {
                "week_start": week_start.isoformat(),
                "generation_date": datetime.now().isoformat(),
                "metrics": metrics,
                "patterns": patterns,
                "recommendations": recommendations,
                "achievements": achievements,
                "comparison": comparison,
                "valuable_rating": None  # Will be set when user provides feedback
            }

            # Store insights
            insights_id = await self._store_insights(insights_data)
            insights_data["id"] = str(insights_id)

            logger.info(f"Generated insights with {len(recommendations)} recommendations")
            return insights_data

        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return {"error": str(e)}

    async def _calculate_weekly_metrics(self, week_start: datetime, week_end: datetime) -> Dict[str, Any]:
        """Calculate weekly productivity metrics"""
        query = """
        SELECT
            COUNT(*) as total_tasks,
            COUNT(*) FILTER (WHERE completed_at IS NOT NULL) as completed,
            COUNT(*) FILTER (WHERE skipped_at IS NOT NULL) as skipped,
            COUNT(*) FILTER (WHERE completed_at IS NOT NULL AND energy_level = 'high') as high_energy_completed,
            COUNT(*) FILTER (WHERE energy_level = 'high') as high_energy_total,
            AVG(EXTRACT(EPOCH FROM (completed_at - created_at))/60) FILTER (WHERE completed_at IS NOT NULL) as avg_completion_minutes,
            AVG(time_estimate) FILTER (WHERE completed_at IS NOT NULL) as avg_estimated_minutes,
            EXTRACT(HOUR FROM completed_at) as completion_hours,
            MODE() WITHIN GROUP (ORDER BY EXTRACT(HOUR FROM completed_at)) FILTER (WHERE completed_at IS NOT NULL) as peak_hour
        FROM tasks
        WHERE created_at >= $1 AND created_at < $2
        """

        result = await self.db.fetch_one(query, week_start, week_end)

        if not result or result["total_tasks"] == 0:
            return self._empty_metrics()

        # Calculate additional metrics
        completion_rate = result["completed"] / result["total_tasks"] if result["total_tasks"] > 0 else 0
        energy_alignment = (result["high_energy_completed"] / max(result["high_energy_total"], 1))

        # Get hourly breakdown
        hourly_completion = await self._get_hourly_completion_data(week_start, week_end)

        return {
            "total_tasks": result["total_tasks"],
            "completed": result["completed"],
            "skipped": result["skipped"],
            "completion_rate": round(completion_rate * 100, 1),
            "energy_alignment": round(energy_alignment * 100, 1),
            "avg_completion_time": round(result["avg_completion_minutes"] or 0, 1),
            "avg_estimated_time": round(result["avg_estimated_minutes"] or 0, 1),
            "peak_productivity_hour": int(result["peak_hour"]) if result["peak_hour"] else 10,
            "hourly_breakdown": hourly_completion
        }

    def _empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics structure"""
        return {
            "total_tasks": 0,
            "completed": 0,
            "skipped": 0,
            "completion_rate": 0,
            "energy_alignment": 0,
            "avg_completion_time": 0,
            "avg_estimated_time": 0,
            "peak_productivity_hour": 10,
            "hourly_breakdown": {}
        }

    async def _get_hourly_completion_data(self, week_start: datetime, week_end: datetime) -> Dict[int, int]:
        """Get task completion count by hour"""
        query = """
        SELECT
            EXTRACT(HOUR FROM completed_at) as hour,
            COUNT(*) as count
        FROM tasks
        WHERE completed_at >= $1 AND completed_at < $2
        GROUP BY EXTRACT(HOUR FROM completed_at)
        ORDER BY hour
        """

        results = await self.db.fetch_all(query, week_start, week_end)
        return {int(row["hour"]): row["count"] for row in results}

    async def _analyze_weekly_patterns(self, week_start: datetime, week_end: datetime) -> Dict[str, Any]:
        """Analyze behavioral patterns for the week"""
        patterns = {
            "skip_patterns": await self._analyze_skip_patterns_weekly(week_start, week_end),
            "energy_patterns": await self._analyze_energy_patterns_weekly(week_start, week_end),
            "timing_patterns": await self._analyze_timing_patterns_weekly(week_start, week_end),
            "delegation_patterns": await self._analyze_delegation_patterns_weekly(week_start, week_end)
        }

        return patterns

    async def _analyze_skip_patterns_weekly(self, week_start: datetime, week_end: datetime) -> Dict[str, Any]:
        """Analyze skip patterns for the week"""
        query = """
        SELECT
            skipped_reason,
            COUNT(*) as count,
            AVG(time_estimate) as avg_time_estimate,
            ARRAY_AGG(LEFT(content, 30)) as sample_tasks
        FROM tasks
        WHERE skipped_at >= $1 AND skipped_at < $2
        GROUP BY skipped_reason
        ORDER BY count DESC
        """

        results = await self.db.fetch_all(query, week_start, week_end)

        return {
            "most_common_reason": results[0]["skipped_reason"] if results else None,
            "reasons_breakdown": [
                {
                    "reason": row["skipped_reason"],
                    "count": row["count"],
                    "avg_time": round(row["avg_time_estimate"] or 0, 1)
                }
                for row in results
            ],
            "total_skips": sum(row["count"] for row in results)
        }

    async def _analyze_energy_patterns_weekly(self, week_start: datetime, week_end: datetime) -> Dict[str, Any]:
        """Analyze energy level effectiveness for the week"""
        query = """
        SELECT
            energy_level,
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE completed_at IS NOT NULL) as completed,
            AVG(EXTRACT(EPOCH FROM (completed_at - created_at))/60) FILTER (WHERE completed_at IS NOT NULL) as avg_time
        FROM tasks
        WHERE created_at >= $1 AND created_at < $2
        GROUP BY energy_level
        """

        results = await self.db.fetch_all(query, week_start, week_end)

        energy_effectiveness = {}
        for row in results:
            completion_rate = row["completed"] / row["total"] if row["total"] > 0 else 0
            energy_effectiveness[row["energy_level"]] = {
                "completion_rate": round(completion_rate * 100, 1),
                "avg_completion_time": round(row["avg_time"] or 0, 1),
                "total_tasks": row["total"]
            }

        return energy_effectiveness

    async def _analyze_timing_patterns_weekly(self, week_start: datetime, week_end: datetime) -> Dict[str, Any]:
        """Analyze timing and scheduling patterns"""
        query = """
        SELECT
            EXTRACT(DOW FROM created_at) as day_of_week,
            EXTRACT(HOUR FROM created_at) as hour,
            COUNT(*) as created_count,
            COUNT(*) FILTER (WHERE completed_at IS NOT NULL) as completed_count
        FROM tasks
        WHERE created_at >= $1 AND created_at < $2
        GROUP BY EXTRACT(DOW FROM created_at), EXTRACT(HOUR FROM created_at)
        ORDER BY created_count DESC
        LIMIT 5
        """

        results = await self.db.fetch_all(query, week_start, week_end)

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        return {
            "peak_creation_times": [
                {
                    "day": day_names[int(row["day_of_week"])],
                    "hour": f"{int(row['hour']):02d}:00",
                    "tasks_created": row["created_count"],
                    "completion_rate": round((row["completed_count"] / row["created_count"]) * 100, 1) if row["created_count"] > 0 else 0
                }
                for row in results
            ]
        }

    async def _analyze_delegation_patterns_weekly(self, week_start: datetime, week_end: datetime) -> Dict[str, Any]:
        """Analyze delegation patterns for the week"""
        query = """
        SELECT
            COUNT(*) as delegation_signals,
            COUNT(*) FILTER (WHERE status = 'completed') as completed_delegations,
            AVG(EXTRACT(EPOCH FROM (completed_at - created_at))/3600) FILTER (WHERE completed_at IS NOT NULL) as avg_delegation_hours
        FROM delegation_signals ds
        JOIN tasks t ON ds.task_id = t.id
        WHERE ds.created_at >= $1 AND ds.created_at < $2
        """

        result = await self.db.fetch_one(query, week_start, week_end)

        return {
            "delegation_signals": result["delegation_signals"] if result else 0,
            "delegation_success_rate": round((result["completed_delegations"] / max(result["delegation_signals"], 1)) * 100, 1) if result else 0,
            "avg_delegation_time": round(result["avg_delegation_hours"] or 0, 1) if result else 0
        }

    async def _generate_recommendations(self, metrics: Dict, patterns: Dict) -> List[Dict[str, Any]]:
        """Generate actionable recommendations based on analysis"""
        recommendations = []

        # Completion rate recommendations
        if metrics["completion_rate"] < 60:
            recommendations.append({
                "category": "productivity",
                "priority": "high",
                "title": "Improve Task Completion Rate",
                "description": f"Your completion rate is {metrics['completion_rate']}%. Focus on smaller, more manageable tasks.",
                "specific_action": "Break down complex tasks into 10-15 minute chunks",
                "expected_impact": "20-30% improvement in completion rate"
            })

        # Energy alignment recommendations
        if metrics["energy_alignment"] < 70:
            recommendations.append({
                "category": "energy",
                "priority": "medium",
                "title": "Better Energy-Task Alignment",
                "description": f"Only {metrics['energy_alignment']}% of high-energy tasks are being completed optimally.",
                "specific_action": "Schedule strategic work between 9-11 AM",
                "expected_impact": "Improved focus and task completion"
            })

        # Skip pattern recommendations
        skip_patterns = patterns.get("skip_patterns", {})
        if skip_patterns.get("total_skips", 0) > metrics["completed"]:
            most_common = skip_patterns.get("most_common_reason")
            recommendations.append({
                "category": "skip_reduction",
                "priority": "high",
                "title": f"Address {most_common} Issues",
                "description": f"Most tasks are skipped due to '{most_common}' - this is your biggest opportunity.",
                "specific_action": self._get_skip_reason_action(most_common),
                "expected_impact": "Reduce skips by 30-40%"
            })

        # Timing recommendations
        peak_hour = metrics.get("peak_productivity_hour", 10)
        if peak_hour > 14:  # Peak productivity after 2 PM
            recommendations.append({
                "category": "timing",
                "priority": "low",
                "title": "Optimize Morning Productivity",
                "description": f"Your peak hour is {peak_hour}:00, but mornings offer highest cognitive capacity.",
                "specific_action": "Schedule one important task before 11 AM daily",
                "expected_impact": "Better energy utilization"
            })

        # Delegation recommendations
        delegation = patterns.get("delegation_patterns", {})
        if delegation.get("delegation_signals", 0) > 0 and delegation.get("delegation_success_rate", 0) < 50:
            recommendations.append({
                "category": "delegation",
                "priority": "medium",
                "title": "Improve Delegation Follow-through",
                "description": f"Only {delegation['delegation_success_rate']}% of delegated tasks are completed.",
                "specific_action": "Set up weekly delegation review meetings",
                "expected_impact": "Higher delegation success rate"
            })

        return sorted(recommendations, key=lambda x: {"high": 3, "medium": 2, "low": 1}[x["priority"]], reverse=True)

    def _get_skip_reason_action(self, reason: str) -> str:
        """Get specific action for skip reason"""
        actions = {
            "low-energy": "Use energy windows: high-energy tasks 9-11 AM, low-energy after 4 PM",
            "no-time": "Break tasks into 10-minute micro-sessions",
            "missing-context": "Create context checklists before starting tasks",
            "not-important": "Use weekly review to eliminate unimportant tasks",
            "need-someone": "Set up delegation templates and follow-up systems"
        }
        return actions.get(reason, "Analyze this skip reason and create a systematic approach")

    async def _identify_achievements(self, metrics: Dict, patterns: Dict) -> List[Dict[str, Any]]:
        """Identify and highlight achievements"""
        achievements = []

        # High completion rate achievement
        if metrics["completion_rate"] >= 70:
            achievements.append({
                "title": "🎯 Completion Champion",
                "description": f"Excellent {metrics['completion_rate']}% task completion rate!",
                "impact": "Strong execution and follow-through"
            })

        # Energy alignment achievement
        if metrics["energy_alignment"] >= 80:
            achievements.append({
                "title": "⚡ Energy Optimizer",
                "description": f"Great energy-task alignment at {metrics['energy_alignment']}%",
                "impact": "Working smarter, not harder"
            })

        # Consistency achievement
        if metrics["total_tasks"] >= 25:
            achievements.append({
                "title": "📈 Consistency Master",
                "description": f"Processed {metrics['total_tasks']} tasks this week",
                "impact": "Building strong productivity habits"
            })

        # Low skip rate achievement
        skip_rate = (metrics["skipped"] / max(metrics["total_tasks"], 1)) * 100
        if skip_rate <= 20:
            achievements.append({
                "title": "🎪 Skip Minimizer",
                "description": f"Only {skip_rate:.1f}% skip rate - excellent focus!",
                "impact": "High task engagement and clarity"
            })

        return achievements

    async def _compare_with_previous_weeks(self, current_metrics: Dict, week_start: datetime) -> Dict[str, Any]:
        """Compare current week with previous weeks"""
        try:
            # Get previous 4 weeks for trend analysis
            previous_weeks = []
            for i in range(1, 5):
                prev_start = week_start - timedelta(weeks=i)
                prev_end = prev_start + timedelta(days=7)
                prev_metrics = await self._calculate_weekly_metrics(prev_start, prev_end)
                if prev_metrics["total_tasks"] > 0:
                    previous_weeks.append(prev_metrics)

            if not previous_weeks:
                return {"available": False, "reason": "Insufficient historical data"}

            # Calculate averages
            avg_completion_rate = sum(w["completion_rate"] for w in previous_weeks) / len(previous_weeks)
            avg_energy_alignment = sum(w["energy_alignment"] for w in previous_weeks) / len(previous_weeks)

            return {
                "available": True,
                "completion_rate_change": round(current_metrics["completion_rate"] - avg_completion_rate, 1),
                "energy_alignment_change": round(current_metrics["energy_alignment"] - avg_energy_alignment, 1),
                "trend_direction": "improving" if current_metrics["completion_rate"] > avg_completion_rate else "declining",
                "weeks_compared": len(previous_weeks)
            }

        except Exception as e:
            logger.error(f"Error comparing with previous weeks: {e}")
            return {"available": False, "reason": "Comparison error"}

    async def send_insights_email(self, insights_data: Dict[str, Any]) -> bool:
        """Send insights as beautiful HTML email"""
        try:
            if not all([self.email_user, self.email_password, self.recipient_email]):
                logger.warning("Email credentials not configured, skipping email send")
                return False

            # Generate HTML email
            html_content = self._generate_html_email(insights_data)

            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"🧠 Your Weekly Lyco Insights - {datetime.now().strftime('%B %d')}"
            msg['From'] = self.email_user
            msg['To'] = self.recipient_email

            # Add HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
                server.send_message(msg)

            # Mark as sent
            await self.db.execute("""
                UPDATE weekly_insights
                SET email_sent = true, email_sent_at = NOW()
                WHERE id = $1
            """, insights_data.get("id"))

            logger.info(f"Weekly insights email sent to {self.recipient_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send insights email: {e}")
            return False

    def _generate_html_email(self, insights: Dict[str, Any]) -> str:
        """Generate beautiful HTML email content"""
        metrics = insights.get("metrics", {})
        recommendations = insights.get("recommendations", [])
        achievements = insights.get("achievements", [])

        week_date = datetime.fromisoformat(insights["week_start"]).strftime("%B %d")

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; text-align: center; }}
                .metric-card {{ background: #f8f9fa; padding: 20px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #667eea; }}
                .metric-value {{ font-size: 2em; font-weight: bold; color: #667eea; }}
                .achievement {{ background: linear-gradient(45deg, #FEE140 0%, #FA709A 100%); color: white; padding: 15px; margin: 10px 0; border-radius: 8px; }}
                .recommendation {{ background: #e3f2fd; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #2196f3; }}
                .chart {{ width: 100%; height: 30px; background: #eee; border-radius: 15px; margin: 10px 0; }}
                .chart-fill {{ height: 100%; background: linear-gradient(90deg, #4caf50, #8bc34a); border-radius: 15px; transition: width 0.3s; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🧠 Weekly Lyco Insights</h1>
                    <p>Week of {week_date} • 2-minute read</p>
                </div>
        """

        # Metrics section
        html += f"""
                <h2>📊 This Week's Metrics</h2>
                <div class="metric-card">
                    <div class="metric-value">{metrics.get('completion_rate', 0):.1f}%</div>
                    <div>Task Completion Rate</div>
                    <div class="chart">
                        <div class="chart-fill" style="width: {min(metrics.get('completion_rate', 0), 100)}%"></div>
                    </div>
                </div>

                <div class="metric-card">
                    <div class="metric-value">{metrics.get('total_tasks', 0)}</div>
                    <div>Total Tasks Processed</div>
                </div>

                <div class="metric-card">
                    <div class="metric-value">{metrics.get('energy_alignment', 0):.1f}%</div>
                    <div>Energy-Task Alignment</div>
                    <div class="chart">
                        <div class="chart-fill" style="width: {min(metrics.get('energy_alignment', 0), 100)}%"></div>
                    </div>
                </div>
        """

        # Achievements section
        if achievements:
            html += "<h2>🏆 This Week's Achievements</h2>"
            for achievement in achievements[:3]:  # Top 3 achievements
                html += f"""
                <div class="achievement">
                    <h3>{achievement['title']}</h3>
                    <p>{achievement['description']}</p>
                    <small>Impact: {achievement['impact']}</small>
                </div>
                """

        # Recommendations section
        if recommendations:
            html += "<h2>🎯 Recommendations for Next Week</h2>"
            for rec in recommendations[:3]:  # Top 3 recommendations
                priority_color = {"high": "#f44336", "medium": "#ff9800", "low": "#4caf50"}[rec["priority"]]
                html += f"""
                <div class="recommendation" style="border-left-color: {priority_color}">
                    <h3>{rec['title']} <span style="background: {priority_color}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.7em;">{rec['priority'].upper()}</span></h3>
                    <p>{rec['description']}</p>
                    <p><strong>Action:</strong> {rec['specific_action']}</p>
                    <small>Expected impact: {rec['expected_impact']}</small>
                </div>
                """

        html += """
                <div style="text-align: center; margin-top: 40px; color: #666;">
                    <p>Keep building your cognitive prosthetic! 🚀</p>
                    <small>Generated by Lyco 2.0 • Designed to make you more effective</small>
                </div>
            </div>
        </body>
        </html>
        """

        return html

    async def _store_insights(self, insights_data: Dict[str, Any]) -> str:
        """Store insights in database"""
        query = """
        INSERT INTO weekly_insights (week_start, insights_data)
        VALUES ($1, $2)
        RETURNING id
        """

        week_start = datetime.fromisoformat(insights_data["week_start"]).date()
        result = await self.db.fetch_one(query, week_start, json.dumps(insights_data))
        return result["id"]

    async def run_weekly_generation(self) -> Dict[str, Any]:
        """Main method to run weekly insights generation"""
        logger.info("Starting weekly insights generation")

        # Calculate last week's start date (Monday)
        today = datetime.now().date()
        days_since_monday = today.weekday()
        last_monday = today - timedelta(days=days_since_monday + 7)
        week_start = datetime.combine(last_monday, datetime.min.time())

        # Check if we should generate insights
        if not await self.should_generate_insights(week_start):
            return {"generated": False, "reason": "Criteria not met"}

        try:
            # Generate insights
            insights = await self.generate_insights(week_start)

            if "error" in insights:
                return {"generated": False, "error": insights["error"]}

            # Send email if configured
            email_sent = await self.send_insights_email(insights)

            return {
                "generated": True,
                "week_start": week_start.isoformat(),
                "insights_id": insights.get("id"),
                "email_sent": email_sent,
                "recommendations_count": len(insights.get("recommendations", [])),
                "achievements_count": len(insights.get("achievements", []))
            }

        except Exception as e:
            logger.error(f"Weekly insights generation failed: {e}")
            return {"generated": False, "error": str(e)}
