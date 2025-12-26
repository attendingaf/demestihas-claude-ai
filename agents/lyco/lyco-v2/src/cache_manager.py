"""
Cache Manager for Lyco 2.0
Provides Redis-based caching for frequently accessed data
"""
import redis
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TaskCache:
    """Redis-based cache for task operations"""

    def __init__(self, redis_host: str = 'redis', redis_port: int = 6379):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {redis_host}:{redis_port}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            # Fallback to no caching
            self.redis_client = None

        self.cache_ttl = 300  # 5 minutes
        self.metrics = {
            'hits': 0,
            'misses': 0,
            'errors': 0
        }

    def get_next_tasks(self, count: int = 5) -> Optional[List[Dict]]:
        """Get cached next tasks"""
        if not self.redis_client:
            self.metrics['misses'] += 1
            return None

        try:
            cached = self.redis_client.get('lyco:next_tasks')
            if cached:
                tasks = json.loads(cached)
                self.metrics['hits'] += 1
                logger.debug(f"Cache hit for next_tasks, returning {len(tasks[:count])} tasks")
                return tasks[:count]
            else:
                self.metrics['misses'] += 1
                logger.debug("Cache miss for next_tasks")
                return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            self.metrics['errors'] += 1
            return None

    def set_next_tasks(self, tasks: List[Dict]) -> None:
        """Cache next tasks with TTL"""
        if not self.redis_client or not tasks:
            return

        try:
            # Convert datetime objects to strings for JSON serialization
            serializable_tasks = []
            for task in tasks:
                task_copy = task.copy()
                for key, value in task_copy.items():
                    if isinstance(value, datetime):
                        task_copy[key] = value.isoformat()
                serializable_tasks.append(task_copy)

            self.redis_client.setex(
                'lyco:next_tasks',
                self.cache_ttl,
                json.dumps(serializable_tasks)
            )
            logger.debug(f"Cached {len(tasks)} tasks with {self.cache_ttl}s TTL")
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            self.metrics['errors'] += 1

    def invalidate_task_cache(self) -> None:
        """Clear task cache on completion/skip/update"""
        if not self.redis_client:
            return

        try:
            self.redis_client.delete('lyco:next_tasks')
            logger.debug("Task cache invalidated")
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
            self.metrics['errors'] += 1

    def get_task_by_id(self, task_id: int) -> Optional[Dict]:
        """Get a specific cached task by ID"""
        if not self.redis_client:
            return None

        try:
            cached = self.redis_client.get(f'lyco:task:{task_id}')
            if cached:
                self.metrics['hits'] += 1
                return json.loads(cached)
            else:
                self.metrics['misses'] += 1
                return None
        except Exception as e:
            logger.error(f"Cache get task error: {e}")
            self.metrics['errors'] += 1
            return None

    def set_task(self, task_id: int, task: Dict) -> None:
        """Cache a specific task"""
        if not self.redis_client:
            return

        try:
            # Convert datetime objects for serialization
            task_copy = task.copy()
            for key, value in task_copy.items():
                if isinstance(value, datetime):
                    task_copy[key] = value.isoformat()

            self.redis_client.setex(
                f'lyco:task:{task_id}',
                self.cache_ttl,
                json.dumps(task_copy)
            )
        except Exception as e:
            logger.error(f"Cache set task error: {e}")
            self.metrics['errors'] += 1

    def get_patterns(self) -> Optional[List[Dict]]:
        """Get cached patterns"""
        if not self.redis_client:
            return None

        try:
            cached = self.redis_client.get('lyco:patterns')
            if cached:
                self.metrics['hits'] += 1
                return json.loads(cached)
            else:
                self.metrics['misses'] += 1
                return None
        except Exception as e:
            logger.error(f"Cache get patterns error: {e}")
            self.metrics['errors'] += 1
            return None

    def set_patterns(self, patterns: List[Dict]) -> None:
        """Cache patterns with longer TTL (30 minutes)"""
        if not self.redis_client:
            return

        try:
            self.redis_client.setex(
                'lyco:patterns',
                1800,  # 30 minutes
                json.dumps(patterns)
            )
        except Exception as e:
            logger.error(f"Cache set patterns error: {e}")
            self.metrics['errors'] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get cache metrics"""
        total = self.metrics['hits'] + self.metrics['misses']
        hit_rate = self.metrics['hits'] / total if total > 0 else 0

        info = {'memory_used': 'N/A', 'connected_clients': 0}
        if self.redis_client:
            try:
                redis_info = self.redis_client.info('memory')
                info['memory_used'] = redis_info.get('used_memory_human', 'N/A')
                client_info = self.redis_client.info('clients')
                info['connected_clients'] = client_info.get('connected_clients', 0)
            except:
                pass

        return {
            'hits': self.metrics['hits'],
            'misses': self.metrics['misses'],
            'errors': self.metrics['errors'],
            'hit_rate': f"{hit_rate:.2%}",
            'total_requests': total,
            'redis_memory': info['memory_used'],
            'redis_clients': info['connected_clients']
        }

    def pre_fetch_tasks(self, db_manager, intelligence_engine) -> None:
        """Pre-fetch and cache tasks during idle time"""
        if not self.redis_client:
            return

        try:
            # Get next 10 tasks from database
            tasks = db_manager.get_next_tasks(limit=10)
            if tasks:
                self.set_next_tasks(tasks)
                logger.info(f"Pre-fetched and cached {len(tasks)} tasks")
        except Exception as e:
            logger.error(f"Pre-fetch error: {e}")
