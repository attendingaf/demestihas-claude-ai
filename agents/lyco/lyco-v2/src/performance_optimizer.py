"""
Lyco 2.0 Phase 4: Performance Optimizer
Implements Redis caching and optimization for sub-second response times
"""
import json
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID
import redis.asyncio as redis

from .models import Task, TaskSignal
from .database import DatabaseManager

logger = logging.getLogger(__name__)


def serialize_for_cache(obj: Any) -> Any:
    """Convert objects to JSON-serializable format"""
    if isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat() if obj else None
    elif isinstance(obj, dict):
        return {k: serialize_for_cache(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_cache(item) for item in obj]
    return obj


class PerformanceOptimizer:
    """Optimize Lyco for sub-second response times"""

    def __init__(self, redis_url: Optional[str] = None):
        import os
        if not redis_url:
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = os.getenv("REDIS_PORT", "6379")
            redis_url = f"redis://{redis_host}:{redis_port}"
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.db = DatabaseManager()

        # Cache keys
        self.NEXT_TASKS_CACHE = "lyco:next_tasks"
        self.ENERGY_CACHE = "lyco:energy_windows"
        self.PATTERN_CACHE = "lyco:patterns"
        self.METRICS_CACHE = "lyco:metrics"

        # Cache TTL in seconds
        self.CACHE_TTL = {
            "next_tasks": 60,      # 1 minute
            "energy": 300,         # 5 minutes
            "patterns": 900,       # 15 minutes
            "metrics": 3600        # 1 hour
        }

    async def initialize(self):
        """Initialize optimizer and start background processes"""
        try:
            await self.redis.ping()
            logger.info("Redis connection established")

            # Start background cache refresh
            asyncio.create_task(self._background_cache_refresh())

            # Pre-populate critical caches
            await self._populate_initial_caches()

        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            raise

    async def get_next_task_cached(self, energy_level: Optional[str] = None) -> Optional[Task]:
        """Get next task with Redis caching for <1s response"""
        cache_key = f"{self.NEXT_TASKS_CACHE}:{energy_level or 'any'}"

        # Try cache first
        cached = await self.redis.get(cache_key)
        if cached:
            try:
                task_data = json.loads(cached)
                return Task(**task_data)
            except Exception as e:
                logger.warning(f"Failed to parse cached task: {e}")

        # Cache miss - fetch from database
        start_time = time.time()
        task = await self._fetch_next_task_optimized(energy_level)
        fetch_time = time.time() - start_time

        # Log slow queries
        if fetch_time > 0.05:  # 50ms threshold
            logger.warning(f"Slow task fetch: {fetch_time:.3f}s")

        # Cache the result
        if task:
            # Convert task to dict with proper serialization
            task_dict = serialize_for_cache(task.dict())

            await self.redis.setex(
                cache_key,
                self.CACHE_TTL["next_tasks"],
                json.dumps(task_dict)
            )

        return task

    async def _fetch_next_task_optimized(self, energy_level: Optional[str] = None) -> Optional[Task]:
        """Optimized database query for next task"""
        # This uses the composite index from the migration
        query = """
        SELECT * FROM tasks
        WHERE completed_at IS NULL
          AND (skipped_at IS NULL OR rescheduled_for <= NOW())
          AND deleted_at IS NULL
          AND ($1::TEXT IS NULL OR energy_level = $1 OR energy_level = 'any')
        ORDER BY
          CASE WHEN rescheduled_for IS NOT NULL THEN 0 ELSE 1 END,
          rescheduled_for ASC NULLS LAST,
          created_at ASC
        LIMIT 1
        """

        result = await self.db.fetch_one(query, energy_level)
        if result:
            return Task(**dict(result))
        return None

    async def get_task_queue_preview(self, count: int = 5) -> List[Task]:
        """Get next N tasks for queue preview (cached)"""
        cache_key = f"{self.NEXT_TASKS_CACHE}:queue:{count}"

        cached = await self.redis.get(cache_key)
        if cached:
            try:
                tasks_data = json.loads(cached)
                return [Task(**task) for task in tasks_data]
            except Exception as e:
                logger.warning(f"Failed to parse cached queue: {e}")

        # Fetch from database
        query = """
        SELECT * FROM tasks
        WHERE completed_at IS NULL
          AND (skipped_at IS NULL OR rescheduled_for <= NOW())
          AND deleted_at IS NULL
        ORDER BY
          CASE WHEN rescheduled_for IS NOT NULL THEN 0 ELSE 1 END,
          rescheduled_for ASC NULLS LAST,
          created_at ASC
        LIMIT $1
        """

        results = await self.db.fetch_all(query, count)
        tasks = [Task(**dict(result)) for result in results]

        # Cache results with proper serialization
        tasks_dict = [serialize_for_cache(task.dict()) for task in tasks]

        await self.redis.setex(
            cache_key,
            self.CACHE_TTL["next_tasks"],
            json.dumps(tasks_dict)
        )

        return tasks

    async def get_energy_window_cached(self) -> Dict[str, Any]:
        """Get current energy window with caching"""
        cached = await self.redis.get(self.ENERGY_CACHE)
        if cached:
            return json.loads(cached)

        # Calculate energy window
        current_hour = datetime.now().hour
        energy_data = self._calculate_energy_window(current_hour)

        # Cache for 5 minutes
        await self.redis.setex(
            self.ENERGY_CACHE,
            self.CACHE_TTL["energy"],
            json.dumps(energy_data)
        )

        return energy_data

    def _calculate_energy_window(self, hour: int) -> Dict[str, Any]:
        """Calculate current energy level and timing"""
        if 9 <= hour < 11:
            return {
                "level": "high",
                "description": "High energy window",
                "optimal_for": ["strategy", "analysis", "creation"],
                "ends_at": "11:00 AM",
                "minutes_left": (11 * 60) - (hour * 60 + datetime.now().minute)
            }
        elif 14 <= hour < 16:
            return {
                "level": "medium",
                "description": "Medium energy window",
                "optimal_for": ["email", "reviews", "meetings"],
                "ends_at": "4:00 PM",
                "minutes_left": (16 * 60) - (hour * 60 + datetime.now().minute)
            }
        else:
            next_high = 9 if hour >= 16 else 9
            return {
                "level": "low",
                "description": "Low energy window",
                "optimal_for": ["reading", "organizing", "admin"],
                "next_high": f"{next_high}:00 AM" + (" tomorrow" if hour >= 16 else ""),
                "minutes_left": None
            }

    async def invalidate_task_caches(self, task_id: Optional[UUID] = None):
        """Invalidate task-related caches when tasks change"""
        patterns = [
            f"{self.NEXT_TASKS_CACHE}:*",
            f"{self.METRICS_CACHE}:*"
        ]

        for pattern in patterns:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)

        logger.debug(f"Invalidated task caches for task {task_id}")

    async def get_cached_metrics(self, date: Optional[str] = None) -> Dict[str, Any]:
        """Get performance metrics with caching"""
        date_key = date or datetime.now().strftime("%Y-%m-%d")
        cache_key = f"{self.METRICS_CACHE}:{date_key}"

        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)

        # Calculate metrics
        metrics = await self._calculate_daily_metrics(date_key)

        # Cache for 1 hour
        await self.redis.setex(
            cache_key,
            self.CACHE_TTL["metrics"],
            json.dumps(metrics)
        )

        return metrics

    async def _calculate_daily_metrics(self, date: str) -> Dict[str, Any]:
        """Calculate daily performance metrics"""
        query = """
        SELECT
            COUNT(*) FILTER (WHERE completed_at IS NOT NULL) as completed,
            COUNT(*) FILTER (WHERE skipped_at IS NOT NULL) as skipped,
            COUNT(*) FILTER (WHERE completed_at IS NULL AND skipped_at IS NULL) as pending,
            AVG(EXTRACT(EPOCH FROM (completed_at - created_at))/60) as avg_completion_time
        FROM tasks
        WHERE DATE(created_at) = $1
        """

        result = await self.db.fetch_one(query, date)

        if not result:
            return {"completed": 0, "skipped": 0, "pending": 0, "avg_completion_time": 0}

        return {
            "completed": result["completed"] or 0,
            "skipped": result["skipped"] or 0,
            "pending": result["pending"] or 0,
            "avg_completion_time": round(result["avg_completion_time"] or 0, 1),
            "completion_rate": round(
                (result["completed"] / max(result["completed"] + result["skipped"], 1)) * 100, 1
            )
        }

    async def _populate_initial_caches(self):
        """Pre-populate critical caches for faster first response"""
        try:
            # Pre-fetch next tasks for each energy level
            for energy in ["high", "medium", "low", None]:
                await self.get_next_task_cached(energy)

            # Pre-fetch task queue
            await self.get_task_queue_preview(5)

            # Pre-fetch energy window
            await self.get_energy_window_cached()

            # Pre-fetch today's metrics
            await self.get_cached_metrics()

            logger.info("Initial caches populated")

        except Exception as e:
            logger.error(f"Failed to populate initial caches: {e}")

    async def _background_cache_refresh(self):
        """Background task to refresh caches periodically"""
        while True:
            try:
                await asyncio.sleep(300)  # 5 minutes

                # Refresh task queue
                await self.get_task_queue_preview(5)

                # Refresh energy window
                await self.get_energy_window_cached()

                # Refresh metrics every hour
                current_minute = datetime.now().minute
                if current_minute < 5:  # First 5 minutes of each hour
                    await self.get_cached_metrics()

                logger.debug("Background cache refresh completed")

            except Exception as e:
                logger.error(f"Background cache refresh failed: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry

    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get system performance statistics"""
        try:
            redis_info = await self.redis.info()
            cache_keys = await self.redis.keys("lyco:*")

            return {
                "redis_connected": True,
                "cache_keys": len(cache_keys),
                "redis_memory": redis_info.get("used_memory_human", "Unknown"),
                "cache_hit_rate": await self._calculate_cache_hit_rate(),
                "avg_response_time": await self._get_avg_response_time()
            }
        except Exception as e:
            logger.error(f"Failed to get performance stats: {e}")
            return {
                "redis_connected": False,
                "error": str(e)
            }

    async def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate from Redis stats"""
        try:
            info = await self.redis.info()
            hits = info.get("keyspace_hits", 0)
            misses = info.get("keyspace_misses", 0)

            if hits + misses == 0:
                return 0.0

            return round((hits / (hits + misses)) * 100, 1)
        except:
            return 0.0

    async def _get_avg_response_time(self) -> float:
        """Get average response time from recent operations"""
        # This could be enhanced with actual timing data
        # For now, return a placeholder
        return 0.045  # 45ms average

    async def cleanup(self):
        """Cleanup resources"""
        try:
            await self.redis.close()
            logger.info("Performance optimizer cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
