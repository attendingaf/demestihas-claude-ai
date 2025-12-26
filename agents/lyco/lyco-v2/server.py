#!/usr/bin/env python3
"""
Lyco 2.0 Web Server
Serves the minimal UI and provides API endpoints
"""
import os
import logging
import json
from datetime import datetime
from typing import Optional, Any
from uuid import UUID
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import uvicorn

from src.database import DatabaseManager
from src.processor import IntelligenceEngine
from src.rounds_mode import RoundsMode
from src.cache_manager import TaskCache


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)
from src.skip_intelligence import SkipIntelligence
from src.pattern_learner import PatternLearner
from src.weekly_review import WeeklyReview
from src.performance_optimizer import PerformanceOptimizer
from src.adaptive_intelligence import AdaptiveIntelligence
from src.weekly_insights import WeeklyInsightsGenerator
from src.health_monitor import HealthMonitor

load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

app = FastAPI(title="Lyco 2.0", description="Cognitive Prosthetic with Adaptive Intelligence")

# Initialize Phase 4 components
performance_optimizer = None
adaptive_intelligence = None
rounds_mode = None
weekly_insights = None
health_monitor = None
task_cache = None

# Mount static files
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


class SkipRequest(BaseModel):
    reason: str


class StatusResponse(BaseModel):
    pending_count: int
    current_energy: str
    current_time: str
    system_health: str
    cache_status: str


class InsightsRequest(BaseModel):
    week_start: Optional[str] = None


class HealthResponse(BaseModel):
    overall_status: str
    components: dict
    uptime_stats: dict


@app.get("/")
async def root():
    """Serve the main UI"""
    index_path = static_path / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))


@app.on_event("startup")
async def startup_event():
    """Initialize Phase 4 systems on startup"""
    global performance_optimizer, adaptive_intelligence, weekly_insights, health_monitor, rounds_mode, task_cache

    try:
        # Initialize cache manager
        redis_host = os.environ.get('REDIS_HOST', 'redis')
        redis_port = int(os.environ.get('REDIS_PORT', 6379))
        task_cache = TaskCache(redis_host=redis_host, redis_port=redis_port)
        logger.info(f"Cache manager initialized with Redis at {redis_host}:{redis_port}")

        # Initialize performance optimizer
        performance_optimizer = PerformanceOptimizer()
        await performance_optimizer.initialize()

        # Initialize adaptive intelligence
        anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
        adaptive_intelligence = AdaptiveIntelligence(anthropic_key)

        # Initialize weekly insights
        weekly_insights = WeeklyInsightsGenerator()

        # Initialize health monitor
        health_monitor = HealthMonitor()
        await health_monitor.initialize()
        await health_monitor.start_monitoring()

        # Initialize rounds mode
        rounds_mode = RoundsMode()
        logger.info("Rounds mode initialized")

        logger.info("Phase 4 components initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize Phase 4 components: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global performance_optimizer, adaptive_intelligence, weekly_insights, health_monitor

    if performance_optimizer:
        await performance_optimizer.cleanup()
    if health_monitor:
        await health_monitor.cleanup()

    logger.info("Phase 4 components cleaned up")
    return {"message": "Lyco 2.0 API"}


@app.get("/api/next-task")
async def get_next_task():
    """Get the next task optimized for current energy"""
    db = DatabaseManager()

    # Determine current energy level
    current_hour = datetime.now().hour
    if 9 <= current_hour < 11:
        energy = "high"
    elif 14 <= current_hour < 16:
        energy = "medium"
    else:
        energy = "low"

    # Check cache first
    if task_cache:
        cached_tasks = task_cache.get_next_tasks(count=1)
        if cached_tasks and len(cached_tasks) > 0:
            task = cached_tasks[0]
            logger.info("Returning cached task")
            return task

    # If not in cache, fetch from database
    try:
        task = await db.get_next_task_optimized()
    except:
        # Fallback to original logic
        task = await db.get_next_task_by_energy(energy)
        if not task:
            task = await db.get_next_task()

    if task:
        task_dict = {
            "id": str(task.id),
            "content": task.content,
            "next_action": task.next_action,
            "energy_level": task.energy_level,
            "time_estimate": task.time_estimate,
            "context_required": task.context_required if task.context_required else [],
            "deadline": task.deadline.isoformat() if task.deadline else None
        }

        # Cache this task for quick access
        if task_cache:
            # Cache just this task as the next task list
            task_cache.set_next_tasks([task_dict])

        return task_dict

    return {}


@app.post("/api/tasks/{task_id}/complete")
async def complete_task(task_id: str):
    """Mark a task as completed"""
    try:
        db = DatabaseManager()
        await db.complete_task(UUID(task_id))

        # Invalidate cache after task completion
        if task_cache:
            task_cache.invalidate_task_cache()

        return {"status": "completed", "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/tasks/{task_id}/skip")
async def skip_task(task_id: str, skip_request: SkipRequest):
    """Skip a task with intelligent processing"""
    try:
        db = DatabaseManager()
        skip_intel = SkipIntelligence()

        # Get the task first
        task = await db.get_task(UUID(task_id))
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Process skip intelligently
        action = await skip_intel.process_skip(task, skip_request.reason)

        # Track pattern
        learner = PatternLearner()
        await learner.analyze_skip(task, skip_request.reason)

        # Mark as skipped in database
        await db.skip_task(UUID(task_id), skip_request.reason)

        # Invalidate cache after task skip
        if task_cache:
            task_cache.invalidate_task_cache()

        # Return what happened (for user transparency)
        return {
            "status": "skipped",
            "task_id": task_id,
            "reason": skip_request.reason,
            "action_taken": action.description,
            "action_type": action.action_type
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """Get system status"""
    db = DatabaseManager()
    pending_count = await db.get_pending_tasks_count()

    current_hour = datetime.now().hour
    if 9 <= current_hour < 11:
        energy = "high"
    elif 14 <= current_hour < 16:
        energy = "medium"
    else:
        energy = "low"

    # Get system health status
    system_health_status = "operational"
    cache_status_info = "active"

    # Check if cache is available and get its status
    if task_cache:
        cache_metrics = task_cache.get_metrics()
        if cache_metrics:
            hit_rate = cache_metrics.get('hit_rate', 0)
            if isinstance(hit_rate, (int, float)):
                cache_status_info = f"active ({hit_rate:.0%} hit rate)"
            else:
                cache_status_info = f"active"

    # Check if health monitor is available
    if health_monitor:
        try:
            health_data = await health_monitor.get_health_dashboard_data()
            system_health_status = health_data.get("overall_status", "operational")
        except:
            system_health_status = "degraded"

    return StatusResponse(
        pending_count=pending_count,
        current_energy=energy,
        current_time=datetime.now().strftime("%I:%M %p"),
        system_health=system_health_status,
        cache_status=cache_status_info
    )


@app.post("/api/signals")
async def create_signal(source: str, content: str):
    """Create a new signal (for testing)"""
    db = DatabaseManager()
    signal_id = await db.create_signal(source, content)
    return {"signal_id": str(signal_id)}


@app.post("/api/process")
async def process_signals():
    """Trigger signal processing"""
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")

    if not anthropic_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    engine = IntelligenceEngine(anthropic_key, openai_key)
    results = await engine.process_all_signals()

    return results




@app.get("/api/weekly-review")
async def generate_weekly_review():
    """Generate weekly review email"""
    try:
        review = WeeklyReview()
        email_html = await review.generate_weekly_email()

        return {"email_html": email_html}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/weekly-review/respond")
async def process_weekly_review_response(response: str):
    """Process weekly review email response"""
    try:
        review = WeeklyReview()
        result = await review.process_email_response(response)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Phase 4 API Endpoints

@app.get("/api/health", response_model=HealthResponse)
async def get_system_health():
    """Get detailed system health information"""
    try:
        if health_monitor:
            health_data = await health_monitor.get_health_dashboard_data()

            # Add cache metrics if available
            if task_cache:
                health_data["components"]["cache"] = task_cache.get_metrics()

            return HealthResponse(
                overall_status=health_data.get("overall_status", "unknown"),
                components=health_data.get("components", {}),
                uptime_stats=health_data.get("uptime_stats", {})
            )
        else:
            # Return basic health with cache metrics
            cache_metrics = {}
            if task_cache:
                cache_metrics = task_cache.get_metrics()

            return HealthResponse(
                overall_status="monitoring_disabled",
                components={"cache": cache_metrics},
                uptime_stats={}
            )
    except Exception as e:
        logger.error(f"Error getting health status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/performance")
async def get_performance_stats():
    """Get system performance statistics"""
    try:
        if performance_optimizer:
            stats = await performance_optimizer.get_performance_stats()
            return stats
        else:
            return {"performance_optimization": "disabled"}
    except Exception as e:
        logger.error(f"Error getting performance stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/queue-preview")
async def get_queue_preview():
    """Get preview of upcoming tasks"""
    try:
        if performance_optimizer:
            tasks = await performance_optimizer.get_task_queue_preview(5)
            queue_data = {
                "queue": [
                    {
                        "id": str(task.id),
                        "content": task.content[:100] + "..." if len(task.content) > 100 else task.content,
                        "energy_level": task.energy_level,
                        "time_estimate": task.time_estimate,
                        "deadline": task.deadline.isoformat() if task.deadline else None
                    }
                    for task in tasks
                ]
            }
            return JSONResponse(content=queue_data)
        else:
            return JSONResponse(content={"queue": [], "message": "Queue preview disabled"})
    except Exception as e:
        logger.error(f"Error getting queue preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze-patterns")
async def analyze_skip_patterns():
    """Trigger skip pattern analysis"""
    try:
        if adaptive_intelligence:
            analysis = await adaptive_intelligence.analyze_skip_patterns()
            return analysis
        else:
            return {"error": "Adaptive intelligence not available"}
    except Exception as e:
        logger.error(f"Error analyzing patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/adaptive-learning")
async def trigger_adaptive_learning():
    """Trigger adaptive learning process"""
    try:
        if adaptive_intelligence:
            # Analyze patterns
            analysis = await adaptive_intelligence.analyze_skip_patterns()

            if analysis.get("patterns_detected", 0) > 0:
                # Generate prompt adjustments
                adjustments = await adaptive_intelligence.generate_prompt_adjustments(analysis)

                # Apply adjustments
                update_results = await adaptive_intelligence.update_processor_prompts(adjustments)

                return {
                    "success": True,
                    "analysis": analysis,
                    "adjustments_applied": update_results["updated_prompts"],
                    "version_changes": update_results["version_changes"]
                }
            else:
                return {
                    "success": False,
                    "message": "Insufficient patterns detected for learning"
                }
        else:
            return {"error": "Adaptive intelligence not available"}
    except Exception as e:
        logger.error(f"Error in adaptive learning: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-insights")
async def generate_weekly_insights(request: InsightsRequest):
    """Generate and optionally send weekly insights"""
    try:
        if weekly_insights:
            week_start = None
            if request.week_start:
                week_start = datetime.fromisoformat(request.week_start)

            insights = await weekly_insights.generate_insights(week_start)

            if "error" not in insights:
                # Try to send email
                email_sent = await weekly_insights.send_insights_email(insights)
                insights["email_sent"] = email_sent

            return insights
        else:
            return {"error": "Weekly insights not available"}
    except Exception as e:
        logger.error(f"Error generating insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/weekly-insights-auto")
async def run_weekly_insights_generation():
    """Run automatic weekly insights generation"""
    try:
        if weekly_insights:
            result = await weekly_insights.run_weekly_generation()
            return result
        else:
            return {"error": "Weekly insights not available"}
    except Exception as e:
        logger.error(f"Error in weekly insights generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics/{date}")
async def get_daily_metrics(date: str):
    """Get cached daily metrics"""
    try:
        if performance_optimizer:
            metrics = await performance_optimizer.get_cached_metrics(date)
            return metrics
        else:
            # Fallback to database query
            db = DatabaseManager()
            query = """
            SELECT
                COUNT(*) FILTER (WHERE completed_at IS NOT NULL) as completed,
                COUNT(*) FILTER (WHERE skipped_at IS NOT NULL) as skipped,
                COUNT(*) FILTER (WHERE completed_at IS NULL AND skipped_at IS NULL) as pending
            FROM tasks
            WHERE DATE(created_at) = $1
            """
            result = await db.fetch_one(query, date)
            return dict(result) if result else {}
    except Exception as e:
        logger.error(f"Error getting daily metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Rounds Mode API Endpoints

@app.post("/api/rounds/start")
async def start_rounds(rounds_type: Optional[str] = "morning", energy_level: Optional[str] = None):
    """Start a new rounds session"""
    try:
        result = await rounds_mode.start_rounds(rounds_type, energy_level)
        # Ensure JSON serializable response
        json_str = json.dumps(result, cls=DateTimeEncoder)
        return JSONResponse(content=json.loads(json_str))
    except Exception as e:
        logger.error(f"Error starting rounds: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rounds/task/{task_id}/decision")
async def process_rounds_decision(
    task_id: str,
    decision: str,
    decision_time: Optional[int] = None
):
    """Process a decision during rounds"""
    try:
        if decision not in ['do_now', 'delegate', 'defer', 'delete']:
            raise HTTPException(status_code=400, detail="Invalid decision")

        result = await rounds_mode.process_decision(task_id, decision, decision_time)
        return result
    except Exception as e:
        logger.error(f"Error processing decision: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rounds/complete")
async def complete_rounds():
    """Complete current rounds session"""
    try:
        result = await rounds_mode.complete_rounds()
        return result
    except Exception as e:
        logger.error(f"Error completing rounds: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/rounds/history")
async def get_rounds_history(limit: int = 10):
    """Get rounds session history"""
    try:
        history = await rounds_mode.get_rounds_history(limit)
        return {"history": history}
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/rounds")
async def rounds_ui():
    """Serve rounds mode UI"""
    rounds_path = static_path / "rounds.html"
    if rounds_path.exists():
        return FileResponse(str(rounds_path))
    else:
        # Fallback to main UI
        return FileResponse(str(static_path / "index.html"))

# Admin View Endpoints

@app.get("/admin")
async def admin_view():
    """Serve admin view UI"""
    admin_path = static_path / "admin.html"
    if admin_path.exists():
        return FileResponse(str(admin_path))
    else:
        # Fallback to main UI
        return FileResponse(str(static_path / "index.html"))

@app.get("/api/tasks/all")
async def get_all_tasks(
    include_completed: bool = False,
    include_deleted: bool = False,
    sort_by: str = "created_at",
    filter_energy: Optional[str] = None,
    filter_status: Optional[str] = None
):
    """Get ALL tasks for admin view with comprehensive data"""
    try:
        db = DatabaseManager()

        # Build query with all relevant joins
        query = """
            SELECT
                t.id,
                t.content as title,
                t.content,
                t.energy_level,
                t.source_type,
                t.created_at,
                t.completed_at,
                t.deleted_at,
                t.deadline,
                t.time_estimate,
                t.parked_at as parked_until,
                t.rescheduled_for,
                t.skip_reason,
                COALESCE(tc.skip_count, 0) as skip_count,
                ds.reason as delegation_reason,
                CASE
                    WHEN t.deadline <= NOW() + INTERVAL '4 hours' THEN true
                    ELSE false
                END as is_urgent
            FROM tasks t
            LEFT JOIN task_categories tc ON t.id = tc.task_id
            LEFT JOIN delegation_signals ds ON t.id = ds.task_id
            WHERE 1=1
        """

        params = []
        param_count = 0

        if not include_completed:
            param_count += 1
            query += f" AND t.completed_at IS NULL"

        if not include_deleted:
            param_count += 1
            query += f" AND t.deleted_at IS NULL"

        if filter_energy:
            param_count += 1
            query += f" AND t.energy_level = ${param_count}"
            params.append(filter_energy)

        if filter_status:
            if filter_status == "parked":
                query += " AND t.parked_at IS NOT NULL"
            elif filter_status == "delegated":
                query += " AND ds.reason IS NOT NULL"
            elif filter_status == "active":
                query += " AND t.parked_at IS NULL AND ds.reason IS NULL"

        # Ensure valid sort_by column
        valid_sorts = ["created_at", "deadline", "energy_level", "skip_count"]
        if sort_by not in valid_sorts:
            sort_by = "created_at"

        query += f" ORDER BY {sort_by} DESC NULLS LAST"

        rows = await db.fetch_all(query, *params)

        # Convert to list of dicts with proper JSON encoding
        tasks = []
        for row in rows:
            task_dict = dict(row)
            # Convert datetime objects to ISO strings
            for key in ['created_at', 'completed_at', 'deleted_at', 'deadline', 'parked_until', 'rescheduled_for']:
                if key in task_dict and task_dict[key]:
                    # Check if it's already a string or datetime
                    if hasattr(task_dict[key], 'isoformat'):
                        task_dict[key] = task_dict[key].isoformat()
                    # else it's already a string, leave it as is
            # Convert UUID to string
            if 'id' in task_dict and task_dict['id']:
                # Check if it needs conversion
                if not isinstance(task_dict['id'], str):
                    task_dict['id'] = str(task_dict['id'])
            tasks.append(task_dict)

        return tasks

    except Exception as e:
        logger.error(f"Error getting all tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/task/{task_id}/energy")
async def update_task_energy(task_id: str, request: dict):
    """Update task energy level"""
    try:
        energy_level = request.get('energy_level')
        if energy_level not in ['high', 'medium', 'low']:
            raise HTTPException(status_code=400, detail="Invalid energy level")

        db = DatabaseManager()
        await db.execute(
            """
            UPDATE tasks
            SET energy_level = $1, updated_at = NOW()
            WHERE id = $2
            """,
            energy_level,
            UUID(task_id)
        )

        # Also update in task_categories if exists
        await db.execute(
            """
            UPDATE task_categories
            SET energy_level = $1, updated_at = NOW()
            WHERE task_id = $2
            """,
            energy_level,
            UUID(task_id)
        )

        return {"success": True, "energy_level": energy_level}

    except Exception as e:
        logger.error(f"Error updating task energy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/task/{task_id}")
async def delete_task_permanently(task_id: str):
    """Permanently delete a task"""
    try:
        db = DatabaseManager()

        # Soft delete by setting deleted_at
        await db.execute(
            """
            UPDATE tasks
            SET deleted_at = NOW(), skip_reason = 'Admin deletion'
            WHERE id = $1
            """,
            UUID(task_id)
        )

        return {"success": True, "message": "Task deleted"}

    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
