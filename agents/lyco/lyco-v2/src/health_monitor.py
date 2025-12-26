"""
Lyco 2.0 Phase 4: Health Monitor
Ensures autonomous operation with self-healing capabilities
"""
import asyncio
import logging
import time
import psutil
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import redis.asyncio as redis
import aiohttp

from .database import DatabaseManager

logger = logging.getLogger(__name__)


class HealthStatus:
    """Health status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


class ComponentHealth:
    """Individual component health tracking"""
    def __init__(self, name: str):
        self.name = name
        self.status = HealthStatus.HEALTHY
        self.response_time_ms = 0
        self.last_check = datetime.now()
        self.error_message = ""
        self.metadata = {}
        self.consecutive_failures = 0


class HealthMonitor:
    """System health monitoring and self-healing"""

    def __init__(self, redis_url: Optional[str] = None):
        import os
        self.db = DatabaseManager()
        if not redis_url:
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = os.getenv("REDIS_PORT", "6379")
            redis_url = f"redis://{redis_host}:{redis_port}"
        self.redis_url = redis_url
        self.redis = None

        # Health check intervals (seconds)
        self.CHECK_INTERVAL = 300  # 5 minutes
        self.CRITICAL_CHECK_INTERVAL = 60  # 1 minute for critical components

        # Failure thresholds
        self.MAX_CONSECUTIVE_FAILURES = 3
        self.RESPONSE_TIME_WARNING_MS = 1000  # 1 second
        self.RESPONSE_TIME_CRITICAL_MS = 5000  # 5 seconds

        # Component tracking
        self.components = {
            "database": ComponentHealth("database"),
            "redis": ComponentHealth("redis"),
            "llm_api": ComponentHealth("llm_api"),
            "queue_processor": ComponentHealth("queue_processor"),
            "disk_space": ComponentHealth("disk_space"),
            "memory": ComponentHealth("memory"),
            "cpu": ComponentHealth("cpu")
        }

        # Self-healing actions
        self.healing_actions = {
            "redis": self._heal_redis,
            "queue_processor": self._heal_queue_processor,
            "memory": self._heal_memory_issues,
            "disk_space": self._heal_disk_space
        }

        self.monitoring_active = False

    async def initialize(self):
        """Initialize health monitoring system"""
        try:
            self.redis = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis.ping()
            logger.info("Health monitor initialized successfully")

            # Perform initial health check
            await self.perform_health_check()

        except Exception as e:
            logger.error(f"Failed to initialize health monitor: {e}")
            raise

    async def start_monitoring(self):
        """Start continuous health monitoring"""
        if self.monitoring_active:
            logger.warning("Health monitoring already active")
            return

        self.monitoring_active = True
        logger.info("Starting continuous health monitoring")

        # Start monitoring tasks
        asyncio.create_task(self._monitor_critical_components())
        asyncio.create_task(self._monitor_system_resources())
        asyncio.create_task(self._monitor_application_health())

    async def stop_monitoring(self):
        """Stop health monitoring"""
        self.monitoring_active = False
        if self.redis:
            await self.redis.close()
        logger.info("Health monitoring stopped")

    async def perform_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        logger.debug("Performing health check")
        start_time = time.time()

        health_results = {}

        # Check each component
        for component_name, component in self.components.items():
            try:
                if component_name == "database":
                    health_results[component_name] = await self._check_database_health()
                elif component_name == "redis":
                    health_results[component_name] = await self._check_redis_health()
                elif component_name == "llm_api":
                    health_results[component_name] = await self._check_llm_api_health()
                elif component_name == "queue_processor":
                    health_results[component_name] = await self._check_queue_processor_health()
                elif component_name == "disk_space":
                    health_results[component_name] = await self._check_disk_space()
                elif component_name == "memory":
                    health_results[component_name] = await self._check_memory_usage()
                elif component_name == "cpu":
                    health_results[component_name] = await self._check_cpu_usage()

            except Exception as e:
                logger.error(f"Health check failed for {component_name}: {e}")
                health_results[component_name] = {
                    "status": HealthStatus.DOWN,
                    "error": str(e),
                    "response_time_ms": 0
                }

        # Update component statuses
        await self._update_component_statuses(health_results)

        # Store health check results
        await self._store_health_results(health_results)

        total_time = (time.time() - start_time) * 1000

        # Generate overall system status
        overall_status = self._calculate_overall_status(health_results)

        result = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "components": health_results,
            "check_duration_ms": round(total_time, 2),
            "healthy_components": sum(1 for r in health_results.values() if r["status"] == HealthStatus.HEALTHY),
            "total_components": len(health_results)
        }

        logger.info(f"Health check completed: {overall_status} ({result['healthy_components']}/{result['total_components']} healthy)")

        return result

    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and performance"""
        start_time = time.time()

        try:
            # Test connection with simple query
            result = await self.db.fetch_one("SELECT 1 as test")
            response_time = (time.time() - start_time) * 1000

            if not result or result["test"] != 1:
                return {
                    "status": HealthStatus.DOWN,
                    "error": "Database query returned unexpected result",
                    "response_time_ms": response_time
                }

            # Check connection pool stats
            pool_info = {
                "size": self.db.pool.get_size() if hasattr(self.db, 'pool') else 0,
                "free": self.db.pool.get_idle_size() if hasattr(self.db, 'pool') else 0
            }

            status = HealthStatus.HEALTHY
            if response_time > self.RESPONSE_TIME_CRITICAL_MS:
                status = HealthStatus.DOWN
            elif response_time > self.RESPONSE_TIME_WARNING_MS:
                status = HealthStatus.DEGRADED

            return {
                "status": status,
                "response_time_ms": round(response_time, 2),
                "metadata": {
                    "pool_info": pool_info,
                    "query_test": "passed"
                }
            }

        except Exception as e:
            return {
                "status": HealthStatus.DOWN,
                "error": str(e),
                "response_time_ms": (time.time() - start_time) * 1000
            }

    async def _check_redis_health(self) -> Dict[str, Any]:
        """Check Redis connectivity and performance"""
        start_time = time.time()

        try:
            if not self.redis:
                self.redis = redis.from_url(self.redis_url, decode_responses=True)

            # Test basic operations
            await self.redis.ping()
            await self.redis.set("health_check", "test", ex=60)
            test_value = await self.redis.get("health_check")
            await self.redis.delete("health_check")

            response_time = (time.time() - start_time) * 1000

            if test_value != "test":
                return {
                    "status": HealthStatus.DOWN,
                    "error": "Redis operations failed",
                    "response_time_ms": response_time
                }

            # Get Redis info
            info = await self.redis.info()
            memory_usage = info.get("used_memory_human", "Unknown")

            status = HealthStatus.HEALTHY
            if response_time > self.RESPONSE_TIME_CRITICAL_MS:
                status = HealthStatus.DOWN
            elif response_time > self.RESPONSE_TIME_WARNING_MS:
                status = HealthStatus.DEGRADED

            return {
                "status": status,
                "response_time_ms": round(response_time, 2),
                "metadata": {
                    "memory_usage": memory_usage,
                    "connected_clients": info.get("connected_clients", 0),
                    "operations_test": "passed"
                }
            }

        except Exception as e:
            return {
                "status": HealthStatus.DOWN,
                "error": str(e),
                "response_time_ms": (time.time() - start_time) * 1000
            }

    async def _check_llm_api_health(self) -> Dict[str, Any]:
        """Check LLM API availability and response time"""
        start_time = time.time()

        try:
            # Test with a simple API call (mock for now)
            # In real implementation, this would make a minimal API call
            await asyncio.sleep(0.1)  # Simulate API call

            response_time = (time.time() - start_time) * 1000

            # For now, assume healthy if no exception
            status = HealthStatus.HEALTHY
            if response_time > self.RESPONSE_TIME_CRITICAL_MS:
                status = HealthStatus.DEGRADED

            return {
                "status": status,
                "response_time_ms": round(response_time, 2),
                "metadata": {
                    "provider": "anthropic",
                    "test_call": "simulated"
                }
            }

        except Exception as e:
            return {
                "status": HealthStatus.DOWN,
                "error": str(e),
                "response_time_ms": (time.time() - start_time) * 1000
            }

    async def _check_queue_processor_health(self) -> Dict[str, Any]:
        """Check background queue processing health"""
        try:
            # Check for stalled tasks (tasks created >2 hours ago but not processed)
            stalled_query = """
            SELECT COUNT(*) as count FROM task_signals
            WHERE processed = false
            AND created_at < NOW() - INTERVAL '2 hours'
            """

            result = await self.db.fetch_one(stalled_query)
            stalled_count = result["count"] if result else 0

            # Check recent processing activity
            recent_query = """
            SELECT COUNT(*) as count FROM task_signals
            WHERE processed = true
            AND created_at >= NOW() - INTERVAL '1 hour'
            """

            recent_result = await self.db.fetch_one(recent_query)
            recent_processed = recent_result["count"] if recent_result else 0

            status = HealthStatus.HEALTHY
            error_message = ""

            if stalled_count > 10:
                status = HealthStatus.DOWN
                error_message = f"Too many stalled tasks: {stalled_count}"
            elif stalled_count > 5:
                status = HealthStatus.DEGRADED
                error_message = f"Some stalled tasks: {stalled_count}"

            return {
                "status": status,
                "error": error_message,
                "response_time_ms": 50,  # Estimated query time
                "metadata": {
                    "stalled_tasks": stalled_count,
                    "recent_processed": recent_processed,
                    "queue_health": "normal" if stalled_count < 5 else "concerning"
                }
            }

        except Exception as e:
            return {
                "status": HealthStatus.DOWN,
                "error": str(e),
                "response_time_ms": 0
            }

    async def _check_disk_space(self) -> Dict[str, Any]:
        """Check disk space usage"""
        try:
            disk_usage = psutil.disk_usage('/')
            free_percentage = (disk_usage.free / disk_usage.total) * 100
            used_percentage = 100 - free_percentage

            status = HealthStatus.HEALTHY
            error_message = ""

            if free_percentage < 5:  # Less than 5% free
                status = HealthStatus.DOWN
                error_message = f"Critical disk space: {free_percentage:.1f}% free"
            elif free_percentage < 15:  # Less than 15% free
                status = HealthStatus.DEGRADED
                error_message = f"Low disk space: {free_percentage:.1f}% free"

            return {
                "status": status,
                "error": error_message,
                "response_time_ms": 10,
                "metadata": {
                    "free_percentage": round(free_percentage, 1),
                    "used_percentage": round(used_percentage, 1),
                    "free_gb": round(disk_usage.free / (1024**3), 2),
                    "total_gb": round(disk_usage.total / (1024**3), 2)
                }
            }

        except Exception as e:
            return {
                "status": HealthStatus.DOWN,
                "error": str(e),
                "response_time_ms": 0
            }

    async def _check_memory_usage(self) -> Dict[str, Any]:
        """Check system memory usage"""
        try:
            memory = psutil.virtual_memory()
            used_percentage = memory.percent

            status = HealthStatus.HEALTHY
            error_message = ""

            if used_percentage > 90:
                status = HealthStatus.DOWN
                error_message = f"Critical memory usage: {used_percentage:.1f}%"
            elif used_percentage > 80:
                status = HealthStatus.DEGRADED
                error_message = f"High memory usage: {used_percentage:.1f}%"

            return {
                "status": status,
                "error": error_message,
                "response_time_ms": 5,
                "metadata": {
                    "used_percentage": round(used_percentage, 1),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "total_gb": round(memory.total / (1024**3), 2)
                }
            }

        except Exception as e:
            return {
                "status": HealthStatus.DOWN,
                "error": str(e),
                "response_time_ms": 0
            }

    async def _check_cpu_usage(self) -> Dict[str, Any]:
        """Check CPU usage"""
        try:
            # Get CPU usage over 1 second interval
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()

            status = HealthStatus.HEALTHY
            error_message = ""

            if cpu_percent > 95:
                status = HealthStatus.DOWN
                error_message = f"Critical CPU usage: {cpu_percent:.1f}%"
            elif cpu_percent > 85:
                status = HealthStatus.DEGRADED
                error_message = f"High CPU usage: {cpu_percent:.1f}%"

            return {
                "status": status,
                "error": error_message,
                "response_time_ms": 1000,  # 1 second for CPU measurement
                "metadata": {
                    "usage_percentage": round(cpu_percent, 1),
                    "cpu_count": cpu_count,
                    "load_average": psutil.getloadavg()[:3] if hasattr(psutil, 'getloadavg') else None
                }
            }

        except Exception as e:
            return {
                "status": HealthStatus.DOWN,
                "error": str(e),
                "response_time_ms": 0
            }

    async def _update_component_statuses(self, health_results: Dict[str, Any]):
        """Update component health tracking"""
        for component_name, result in health_results.items():
            if component_name in self.components:
                component = self.components[component_name]
                component.status = result["status"]
                component.response_time_ms = result.get("response_time_ms", 0)
                component.last_check = datetime.now()
                component.error_message = result.get("error", "")
                component.metadata = result.get("metadata", {})

                # Track consecutive failures
                if result["status"] == HealthStatus.DOWN:
                    component.consecutive_failures += 1
                else:
                    component.consecutive_failures = 0

                # Trigger self-healing if needed
                if (component.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES
                    and component_name in self.healing_actions):
                    asyncio.create_task(self._attempt_self_healing(component_name))

    async def _attempt_self_healing(self, component_name: str):
        """Attempt self-healing for failed component"""
        logger.warning(f"Attempting self-healing for {component_name}")

        try:
            healing_action = self.healing_actions[component_name]
            success = await healing_action()

            if success:
                logger.info(f"Self-healing successful for {component_name}")
                self.components[component_name].consecutive_failures = 0
            else:
                logger.error(f"Self-healing failed for {component_name}")

        except Exception as e:
            logger.error(f"Self-healing attempt failed for {component_name}: {e}")

    async def _heal_redis(self) -> bool:
        """Attempt to heal Redis connection issues"""
        try:
            if self.redis:
                await self.redis.close()

            self.redis = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis.ping()

            logger.info("Redis connection restored")
            return True

        except Exception as e:
            logger.error(f"Redis healing failed: {e}")
            return False

    async def _heal_queue_processor(self) -> bool:
        """Attempt to heal queue processor issues"""
        try:
            # Clear any stuck processing flags
            await self.db.execute("""
                UPDATE task_signals
                SET processed = false
                WHERE processed = true
                AND created_at < NOW() - INTERVAL '2 hours'
                AND id NOT IN (SELECT DISTINCT signal_id FROM tasks WHERE signal_id IS NOT NULL)
            """)

            logger.info("Queue processor healing attempted")
            return True

        except Exception as e:
            logger.error(f"Queue processor healing failed: {e}")
            return False

    async def _heal_memory_issues(self) -> bool:
        """Attempt to heal memory issues"""
        try:
            # Clear Redis cache to free memory
            if self.redis:
                keys = await self.redis.keys("lyco:cache:*")
                if keys:
                    await self.redis.delete(*keys)
                    logger.info(f"Cleared {len(keys)} cache keys to free memory")

            return True

        except Exception as e:
            logger.error(f"Memory healing failed: {e}")
            return False

    async def _heal_disk_space(self) -> bool:
        """Attempt to heal disk space issues"""
        try:
            # Clean old log files
            import os
            import glob

            log_files = glob.glob("*.log.*") + glob.glob("*.log.old")
            cleaned_count = 0

            for log_file in log_files:
                try:
                    os.remove(log_file)
                    cleaned_count += 1
                except:
                    pass

            logger.info(f"Cleaned {cleaned_count} old log files")
            return cleaned_count > 0

        except Exception as e:
            logger.error(f"Disk space healing failed: {e}")
            return False

    def _calculate_overall_status(self, health_results: Dict[str, Any]) -> str:
        """Calculate overall system status"""
        statuses = [result["status"] for result in health_results.values()]

        if any(status == HealthStatus.DOWN for status in statuses):
            return HealthStatus.DOWN
        elif any(status == HealthStatus.DEGRADED for status in statuses):
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

    async def _store_health_results(self, health_results: Dict[str, Any]):
        """Store health check results in database"""
        try:
            for component_name, result in health_results.items():
                await self.db.execute("""
                    INSERT INTO system_health (component, status, response_time_ms, error_message, metadata)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (component) DO UPDATE SET
                        status = $2,
                        response_time_ms = $3,
                        error_message = $4,
                        metadata = $5,
                        last_check = NOW()
                """,
                component_name,
                result["status"],
                result.get("response_time_ms", 0),
                result.get("error", ""),
                json.dumps(result.get("metadata", {}))
                )

        except Exception as e:
            logger.error(f"Failed to store health results: {e}")

    async def _monitor_critical_components(self):
        """Monitor critical components more frequently"""
        while self.monitoring_active:
            try:
                # Check critical components (database, redis)
                critical_components = ["database", "redis"]

                for component_name in critical_components:
                    component = self.components[component_name]
                    if component.status != HealthStatus.HEALTHY:
                        # Perform immediate health check
                        await self.perform_health_check()
                        break

                await asyncio.sleep(self.CRITICAL_CHECK_INTERVAL)

            except Exception as e:
                logger.error(f"Critical monitoring error: {e}")
                await asyncio.sleep(self.CRITICAL_CHECK_INTERVAL)

    async def _monitor_system_resources(self):
        """Monitor system resources continuously"""
        while self.monitoring_active:
            try:
                # Check system resources
                await self._check_memory_usage()
                await self._check_cpu_usage()
                await self._check_disk_space()

                await asyncio.sleep(self.CHECK_INTERVAL)

            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                await asyncio.sleep(self.CHECK_INTERVAL)

    async def _monitor_application_health(self):
        """Monitor application-specific health"""
        while self.monitoring_active:
            try:
                # Full health check
                await self.perform_health_check()

                await asyncio.sleep(self.CHECK_INTERVAL)

            except Exception as e:
                logger.error(f"Application monitoring error: {e}")
                await asyncio.sleep(self.CHECK_INTERVAL)

    async def get_health_dashboard_data(self) -> Dict[str, Any]:
        """Get health data for dashboard display"""
        try:
            # Get current component statuses
            components_status = {}
            for name, component in self.components.items():
                components_status[name] = {
                    "status": component.status,
                    "response_time_ms": component.response_time_ms,
                    "last_check": component.last_check.isoformat(),
                    "error": component.error_message,
                    "consecutive_failures": component.consecutive_failures
                }

            # Get historical health data
            historical_query = """
            SELECT component, status, last_check, response_time_ms
            FROM system_health
            WHERE last_check >= NOW() - INTERVAL '24 hours'
            ORDER BY component, last_check DESC
            """

            historical_data = await self.db.fetch_all(historical_query)

            # Calculate uptime statistics
            uptime_stats = await self._calculate_uptime_stats()

            overall_status = self._calculate_overall_status(
                {name: {"status": comp.status} for name, comp in self.components.items()}
            )

            return {
                "overall_status": overall_status,
                "components": components_status,
                "uptime_stats": uptime_stats,
                "historical_data": [dict(row) for row in historical_data],
                "monitoring_active": self.monitoring_active,
                "last_updated": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to get health dashboard data: {e}")
            return {
                "overall_status": HealthStatus.DOWN,
                "error": str(e),
                "last_updated": datetime.now().isoformat()
            }

    async def _calculate_uptime_stats(self) -> Dict[str, Any]:
        """Calculate uptime statistics for the last 24 hours"""
        try:
            query = """
            SELECT
                component,
                COUNT(*) as total_checks,
                COUNT(*) FILTER (WHERE status = 'healthy') as healthy_checks,
                AVG(response_time_ms) as avg_response_time
            FROM system_health
            WHERE last_check >= NOW() - INTERVAL '24 hours'
            GROUP BY component
            """

            results = await self.db.fetch_all(query)

            uptime_stats = {}
            for row in results:
                uptime_percentage = (row["healthy_checks"] / row["total_checks"]) * 100 if row["total_checks"] > 0 else 0
                uptime_stats[row["component"]] = {
                    "uptime_percentage": round(uptime_percentage, 2),
                    "avg_response_time_ms": round(row["avg_response_time"] or 0, 2),
                    "total_checks": row["total_checks"]
                }

            return uptime_stats

        except Exception as e:
            logger.error(f"Failed to calculate uptime stats: {e}")
            return {}

    async def cleanup(self):
        """Cleanup resources"""
        await self.stop_monitoring()
        logger.info("Health monitor cleanup completed")
