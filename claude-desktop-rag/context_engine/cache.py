#!/usr/bin/env python3
"""Multi-level cache implementation for Context Engine.

Implements a three-tier caching system:
- L1: In-memory LRU cache with Redis backing
- L2: SQLite for persistent local storage
- L3: Supabase for cloud storage
"""

import time
import json
import sqlite3
import hashlib
import msgpack
import lz4.frame
import mmap
import os
from pathlib import Path
from typing import Any, Dict, Optional, List, Tuple, Set
from collections import OrderedDict
from datetime import datetime, timedelta
from functools import lru_cache
import redis
import asyncio
from dataclasses import dataclass, asdict
import logging
from threading import Lock, Thread
from queue import Queue, Empty
import pickle

# Try to import bloom filter, fall back if not available
try:
    from pybloom_live import BloomFilter
    BLOOM_AVAILABLE = True
except ImportError:
    BLOOM_AVAILABLE = False
    BloomFilter = None

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Represents a single cache entry."""
    key: str
    value: Any
    timestamp: float
    access_count: int = 0
    last_access: float = None
    size_bytes: int = 0
    namespace: str = "default"
    ttl: Optional[int] = None
    
    def __post_init__(self):
        if self.last_access is None:
            self.last_access = self.timestamp
        if self.size_bytes == 0:
            self.size_bytes = len(msgpack.packb(self.value))

class MultiLevelCache:
    """High-performance multi-level cache with predictive prefetching."""
    
    def __init__(self, 
                 redis_host: str = "localhost",
                 redis_port: int = 6379,
                 sqlite_path: str = "context_cache.db",
                 max_memory_mb: int = 512,
                 enable_mmap: bool = True,
                 enable_prefetch: bool = True):
        """Initialize the multi-level cache system.
        
        Args:
            redis_host: Redis server host
            redis_port: Redis server port
            sqlite_path: Path to SQLite database
            max_memory_mb: Maximum memory usage in MB
            enable_mmap: Enable memory-mapped file access
            enable_prefetch: Enable predictive prefetching
        """
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.current_memory_usage = 0
        self.enable_mmap = enable_mmap
        self.enable_prefetch = enable_prefetch
        
        # L1: Memory cache with LRU eviction
        self.memory_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.memory_lock = Lock()
        
        # L1: Redis connection (optional)
        self.redis_client = self._init_redis(redis_host, redis_port)
        
        # L2: SQLite connection
        self.sqlite_path = sqlite_path
        self.sqlite_conn = self._init_sqlite()
        
        # Memory-mapped file for hot data
        self.mmap_file = None
        self.mmap_index = {}
        if enable_mmap:
            self._init_mmap()
        
        # Bloom filter for existence checks
        if BLOOM_AVAILABLE:
            self.bloom_filter = BloomFilter(capacity=100000, error_rate=0.001)
        else:
            self.bloom_filter = None
        
        # Access pattern tracking for prefetching
        self.access_patterns = OrderedDict()
        self.prefetch_queue = Queue()
        if enable_prefetch:
            self.prefetch_thread = Thread(target=self._prefetch_worker, daemon=True)
            self.prefetch_thread.start()
        
        # Performance metrics
        self.stats = {
            "hits": {"L1": 0, "L2": 0, "L3": 0},
            "misses": 0,
            "evictions": 0,
            "prefetch_success": 0
        }
    
    def _init_redis(self, host: str, port: int) -> Optional[redis.Redis]:
        """Initialize Redis connection."""
        try:
            client = redis.Redis(
                host=host, 
                port=port, 
                decode_responses=False,
                socket_keepalive=True,
                socket_connect_timeout=1
            )
            client.ping()
            logger.info("Redis L1 cache connected")
            return client
        except Exception as e:
            logger.warning(f"Redis not available, using memory-only L1: {e}")
            return None
    
    def _init_sqlite(self) -> sqlite3.Connection:
        """Initialize SQLite database for L2 cache."""
        conn = sqlite3.connect(self.sqlite_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=MEMORY")
        
        # Create cache table with indexes
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                namespace TEXT,
                value BLOB,
                timestamp REAL,
                access_count INTEGER DEFAULT 0,
                last_access REAL,
                size_bytes INTEGER,
                ttl INTEGER
            )
        """)
        
        conn.execute("CREATE INDEX IF NOT EXISTS idx_namespace ON cache(namespace)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON cache(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_last_access ON cache(last_access)")
        
        conn.commit()
        logger.info("SQLite L2 cache initialized")
        return conn
    
    def _init_mmap(self):
        """Initialize memory-mapped file for ultra-fast access."""
        mmap_path = Path("cache_mmap.bin")
        mmap_size = 100 * 1024 * 1024  # 100MB
        
        if not mmap_path.exists():
            with open(mmap_path, "wb") as f:
                f.write(b'\0' * mmap_size)
        
        with open(mmap_path, "r+b") as f:
            self.mmap_file = mmap.mmap(f.fileno(), mmap_size)
        
        logger.info("Memory-mapped file initialized")
    
    def _prefetch_worker(self):
        """Background worker for predictive prefetching."""
        while True:
            try:
                patterns = self.prefetch_queue.get(timeout=1)
                if patterns:
                    self._execute_prefetch(patterns)
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Prefetch error: {e}")
    
    def _execute_prefetch(self, patterns: List[str]):
        """Execute prefetch based on access patterns."""
        for pattern in patterns:
            # Look for related keys in L2/L3
            cursor = self.sqlite_conn.execute(
                "SELECT key FROM cache WHERE key LIKE ? LIMIT 10",
                (f"{pattern}%",)
            )
            
            for row in cursor:
                key = row[0]
                if key not in self.memory_cache:
                    # Preload into memory
                    self._load_from_sqlite(key)
                    self.stats["prefetch_success"] += 1
    
    def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """Get value from cache with multi-level lookup.
        
        Args:
            key: Cache key
            namespace: Namespace for isolation
            
        Returns:
            Cached value or None if not found
        """
        start_time = time.perf_counter()
        full_key = f"{namespace}:{key}"
        
        # Check bloom filter first (if available)
        if self.bloom_filter and full_key not in self.bloom_filter:
            self.stats["misses"] += 1
            return None
        
        # L1: Memory cache
        with self.memory_lock:
            if full_key in self.memory_cache:
                entry = self.memory_cache.pop(full_key)
                entry.access_count += 1
                entry.last_access = time.time()
                self.memory_cache[full_key] = entry  # Move to end (LRU)
                self.stats["hits"]["L1"] += 1
                self._track_access_pattern(full_key)
                return entry.value
        
        # L1: Redis cache
        if self.redis_client:
            try:
                data = self.redis_client.get(full_key)
                if data:
                    value = msgpack.unpackb(lz4.frame.decompress(data), raw=False)
                    self._update_memory_cache(full_key, value, namespace)
                    self.stats["hits"]["L1"] += 1
                    return value
            except Exception as e:
                logger.debug(f"Redis get error: {e}")
        
        # L2: SQLite
        value = self._load_from_sqlite(full_key)
        if value is not None:
            self.stats["hits"]["L2"] += 1
            return value
        
        # L3: Would be Supabase lookup (implemented in sync.py)
        
        self.stats["misses"] += 1
        return None
    
    def _load_from_sqlite(self, full_key: str) -> Optional[Any]:
        """Load value from SQLite cache."""
        cursor = self.sqlite_conn.execute(
            "SELECT value, timestamp, ttl FROM cache WHERE key = ?",
            (full_key,)
        )
        row = cursor.fetchone()
        
        if row:
            value_blob, timestamp, ttl = row
            
            # Check TTL
            if ttl and (time.time() - timestamp) > ttl:
                self.sqlite_conn.execute("DELETE FROM cache WHERE key = ?", (full_key,))
                self.sqlite_conn.commit()
                return None
            
            value = msgpack.unpackb(lz4.frame.decompress(value_blob), raw=False)
            
            # Update access stats
            self.sqlite_conn.execute(
                "UPDATE cache SET access_count = access_count + 1, last_access = ? WHERE key = ?",
                (time.time(), full_key)
            )
            
            # Promote to memory cache
            namespace = full_key.split(":", 1)[0] if ":" in full_key else "default"
            self._update_memory_cache(full_key, value, namespace)
            
            return value
        
        return None
    
    def set(self, key: str, value: Any, namespace: str = "default", ttl: Optional[int] = None):
        """Set value in cache across all levels.
        
        Args:
            key: Cache key
            value: Value to cache
            namespace: Namespace for isolation
            ttl: Time-to-live in seconds
        """
        full_key = f"{namespace}:{key}"
        timestamp = time.time()
        
        # Serialize and compress
        serialized = msgpack.packb(value)
        compressed = lz4.frame.compress(serialized)
        size_bytes = len(compressed)
        
        # Update bloom filter
        if self.bloom_filter:
            self.bloom_filter.add(full_key)
        
        # L1: Memory cache
        entry = CacheEntry(
            key=full_key,
            value=value,
            timestamp=timestamp,
            size_bytes=size_bytes,
            namespace=namespace,
            ttl=ttl
        )
        self._update_memory_cache(full_key, value, namespace, ttl)
        
        # L1: Redis
        if self.redis_client:
            try:
                pipe = self.redis_client.pipeline()
                pipe.set(full_key, compressed)
                if ttl:
                    pipe.expire(full_key, ttl)
                pipe.execute()
            except Exception as e:
                logger.debug(f"Redis set error: {e}")
        
        # L2: SQLite
        self.sqlite_conn.execute("""
            INSERT OR REPLACE INTO cache 
            (key, namespace, value, timestamp, access_count, last_access, size_bytes, ttl)
            VALUES (?, ?, ?, ?, 0, ?, ?, ?)
        """, (full_key, namespace, compressed, timestamp, timestamp, size_bytes, ttl))
        self.sqlite_conn.commit()
    
    def _update_memory_cache(self, key: str, value: Any, namespace: str, ttl: Optional[int] = None):
        """Update memory cache with LRU eviction."""
        with self.memory_lock:
            entry = CacheEntry(
                key=key,
                value=value,
                timestamp=time.time(),
                namespace=namespace,
                ttl=ttl
            )
            
            # Check memory pressure
            while self.current_memory_usage + entry.size_bytes > self.max_memory_bytes:
                if not self.memory_cache:
                    break
                    
                # Evict oldest entry
                evicted_key, evicted_entry = self.memory_cache.popitem(last=False)
                self.current_memory_usage -= evicted_entry.size_bytes
                self.stats["evictions"] += 1
                
                # Write back to Redis if available
                if self.redis_client:
                    try:
                        serialized = msgpack.packb(evicted_entry.value)
                        compressed = lz4.frame.compress(serialized)
                        self.redis_client.set(evicted_key, compressed)
                    except Exception:
                        pass
            
            # Add new entry
            if key in self.memory_cache:
                self.current_memory_usage -= self.memory_cache[key].size_bytes
            
            self.memory_cache[key] = entry
            self.current_memory_usage += entry.size_bytes
    
    def _track_access_pattern(self, key: str):
        """Track access patterns for predictive prefetching."""
        if not self.enable_prefetch:
            return
        
        # Simple pattern: track key prefixes
        prefix = key.rsplit("_", 1)[0] if "_" in key else key
        
        if prefix not in self.access_patterns:
            self.access_patterns[prefix] = 0
        self.access_patterns[prefix] += 1
        
        # Trigger prefetch if pattern is hot
        if self.access_patterns[prefix] > 3:
            self.prefetch_queue.put([prefix])
    
    def delete(self, key: str, namespace: str = "default"):
        """Delete entry from all cache levels."""
        full_key = f"{namespace}:{key}"
        
        # Remove from memory
        with self.memory_lock:
            if full_key in self.memory_cache:
                entry = self.memory_cache.pop(full_key)
                self.current_memory_usage -= entry.size_bytes
        
        # Remove from Redis
        if self.redis_client:
            try:
                self.redis_client.delete(full_key)
            except Exception:
                pass
        
        # Remove from SQLite
        self.sqlite_conn.execute("DELETE FROM cache WHERE key = ?", (full_key,))
        self.sqlite_conn.commit()
    
    def clear_namespace(self, namespace: str):
        """Clear all entries in a namespace."""
        # Clear memory cache
        with self.memory_lock:
            keys_to_remove = [k for k in self.memory_cache if k.startswith(f"{namespace}:")]
            for key in keys_to_remove:
                entry = self.memory_cache.pop(key)
                self.current_memory_usage -= entry.size_bytes
        
        # Clear Redis
        if self.redis_client:
            try:
                cursor = 0
                while True:
                    cursor, keys = self.redis_client.scan(cursor, match=f"{namespace}:*", count=100)
                    if keys:
                        self.redis_client.delete(*keys)
                    if cursor == 0:
                        break
            except Exception:
                pass
        
        # Clear SQLite
        self.sqlite_conn.execute("DELETE FROM cache WHERE namespace = ?", (namespace,))
        self.sqlite_conn.commit()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_hits = sum(self.stats["hits"].values())
        total_requests = total_hits + self.stats["misses"]
        hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate": f"{hit_rate:.2f}%",
            "evictions": self.stats["evictions"],
            "memory_usage_mb": self.current_memory_usage / (1024 * 1024),
            "memory_entries": len(self.memory_cache),
            "prefetch_success": self.stats["prefetch_success"]
        }
    
    def close(self):
        """Clean up resources."""
        if self.mmap_file:
            self.mmap_file.close()
        if self.sqlite_conn:
            self.sqlite_conn.close()
        if self.redis_client:
            self.redis_client.close()

# Singleton instance
_cache_instance = None

def get_cache() -> MultiLevelCache:
    """Get or create the global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = MultiLevelCache()
    return _cache_instance