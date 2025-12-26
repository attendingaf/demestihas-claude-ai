#!/usr/bin/env python3
"""Real-time synchronization engine for Context Engine.

Handles bidirectional sync between local SQLite and Supabase with:
- WebSocket real-time updates
- Conflict resolution
- Delta sync
- Offline resilience
"""

import asyncio
import json
import time
import hashlib
import sqlite3
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from queue import Queue, Empty, PriorityQueue
import threading
import logging
import os
from pathlib import Path
import msgpack
import lz4.frame

# Optional imports for Supabase
try:
    from supabase import create_client, Client
    import websockets
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None

logger = logging.getLogger(__name__)

@dataclass
class SyncOperation:
    """Represents a sync operation."""
    id: str
    operation_type: str  # insert, update, delete
    table_name: str
    data: Dict[str, Any]
    timestamp: float
    namespace: str
    priority: int = 5
    retry_count: int = 0
    max_retries: int = 3
    
    def __lt__(self, other):
        """For priority queue comparison."""
        return self.priority < other.priority

@dataclass
class VectorClock:
    """Vector clock for distributed conflict resolution."""
    clocks: Dict[str, int] = field(default_factory=dict)
    
    def increment(self, node_id: str):
        """Increment clock for a node."""
        self.clocks[node_id] = self.clocks.get(node_id, 0) + 1
    
    def merge(self, other: 'VectorClock'):
        """Merge with another vector clock."""
        for node_id, clock in other.clocks.items():
            self.clocks[node_id] = max(self.clocks.get(node_id, 0), clock)
    
    def happens_before(self, other: 'VectorClock') -> bool:
        """Check if this clock happens before another."""
        for node_id, clock in self.clocks.items():
            if clock > other.clocks.get(node_id, 0):
                return False
        return True
    
    def concurrent_with(self, other: 'VectorClock') -> bool:
        """Check if clocks are concurrent."""
        return not self.happens_before(other) and not other.happens_before(self)

class SyncEngine:
    """Real-time synchronization engine."""
    
    def __init__(self,
                 supabase_url: Optional[str] = None,
                 supabase_key: Optional[str] = None,
                 sqlite_path: str = "sync_state.db",
                 node_id: str = "local",
                 enable_realtime: bool = True):
        """Initialize sync engine.
        
        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase API key
            sqlite_path: Path to local sync state database
            node_id: Unique identifier for this node
            enable_realtime: Enable WebSocket real-time sync
        """
        self.node_id = node_id
        self.enable_realtime = enable_realtime
        
        # Supabase client
        self.supabase_client = None
        if SUPABASE_AVAILABLE and supabase_url and supabase_key:
            try:
                self.supabase_client = create_client(supabase_url, supabase_key)
                logger.info("Supabase client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase: {e}")
        
        # Local database for sync state
        self.sqlite_path = sqlite_path
        self.conn = self._init_sync_db()
        
        # Sync queues
        self.upload_queue = PriorityQueue()
        self.download_queue = PriorityQueue()
        self.conflict_queue = Queue()
        
        # Vector clocks for conflict resolution
        self.vector_clocks: Dict[str, VectorClock] = {}
        
        # Sync state
        self.is_syncing = False
        self.last_sync_time = 0
        self.sync_lock = threading.Lock()
        
        # WebSocket connection
        self.ws_connection = None
        self.ws_task = None
        
        # Start sync workers
        self._start_sync_workers()
        
        # Start real-time listener if enabled
        if enable_realtime and self.supabase_client:
            self._start_realtime_listener()
    
    def _init_sync_db(self) -> sqlite3.Connection:
        """Initialize local sync state database."""
        conn = sqlite3.connect(self.sqlite_path, check_same_thread=False)
        
        # Create tables for sync state
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_log (
                id TEXT PRIMARY KEY,
                operation_type TEXT,
                table_name TEXT,
                data TEXT,
                timestamp REAL,
                namespace TEXT,
                synced BOOLEAN DEFAULT 0,
                sync_time REAL,
                vector_clock TEXT
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_state (
                table_name TEXT PRIMARY KEY,
                last_sync_time REAL,
                last_sync_id TEXT,
                vector_clock TEXT
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conflict_log (
                id TEXT PRIMARY KEY,
                local_data TEXT,
                remote_data TEXT,
                timestamp REAL,
                resolution TEXT,
                resolved BOOLEAN DEFAULT 0
            )
        """)
        
        # Create indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sync_log_synced ON sync_log(synced)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sync_log_timestamp ON sync_log(timestamp)")
        
        conn.commit()
        return conn
    
    def _start_sync_workers(self):
        """Start background workers for sync operations."""
        # Upload worker
        upload_thread = threading.Thread(target=self._upload_worker, daemon=True)
        upload_thread.start()
        
        # Download worker
        download_thread = threading.Thread(target=self._download_worker, daemon=True)
        download_thread.start()
        
        # Conflict resolver
        conflict_thread = threading.Thread(target=self._conflict_resolver, daemon=True)
        conflict_thread.start()
        
        logger.info("Sync workers started")
    
    def _start_realtime_listener(self):
        """Start WebSocket listener for real-time updates."""
        if not self.enable_realtime or not self.supabase_client:
            return
        
        # Start async event loop in thread
        def run_async_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._realtime_listener())
        
        realtime_thread = threading.Thread(target=run_async_loop, daemon=True)
        realtime_thread.start()
    
    async def _realtime_listener(self):
        """WebSocket listener for real-time Supabase changes."""
        while True:
            try:
                # Subscribe to changes
                channel = self.supabase_client.channel('context_changes')
                
                # Subscribe to all tables
                channel.on('postgres_changes', 
                          event='*',
                          schema='public',
                          callback=self._handle_realtime_change)
                
                await channel.subscribe()
                logger.info("Real-time listener subscribed")
                
                # Keep connection alive
                while True:
                    await asyncio.sleep(30)
                    
            except Exception as e:
                logger.error(f"Real-time listener error: {e}")
                await asyncio.sleep(5)  # Retry after 5 seconds
    
    def _handle_realtime_change(self, payload):
        """Handle real-time change from Supabase."""
        try:
            event_type = payload.get('eventType', '')
            table = payload.get('table', '')
            record = payload.get('record', {})
            
            # Skip if change originated from this node
            if record.get('node_id') == self.node_id:
                return
            
            # Create sync operation
            operation = SyncOperation(
                id=hashlib.md5(f"{table}:{record.get('id', '')}:{time.time()}".encode()).hexdigest(),
                operation_type=event_type.lower(),
                table_name=table,
                data=record,
                timestamp=time.time(),
                namespace=record.get('namespace', 'default'),
                priority=2  # High priority for real-time changes
            )
            
            # Add to download queue
            self.download_queue.put(operation)
            
        except Exception as e:
            logger.error(f"Error handling real-time change: {e}")
    
    def _upload_worker(self):
        """Background worker for uploading local changes."""
        while True:
            try:
                operation = self.upload_queue.get(timeout=1)
                self._execute_upload(operation)
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Upload worker error: {e}")
    
    def _execute_upload(self, operation: SyncOperation):
        """Execute upload operation to Supabase."""
        if not self.supabase_client:
            return
        
        try:
            table = self.supabase_client.table(operation.table_name)
            
            # Add node ID and timestamp
            data = operation.data.copy()
            data['node_id'] = self.node_id
            data['sync_timestamp'] = operation.timestamp
            
            # Execute operation
            if operation.operation_type == 'insert':
                result = table.insert(data).execute()
            elif operation.operation_type == 'update':
                result = table.update(data).eq('id', data['id']).execute()
            elif operation.operation_type == 'delete':
                result = table.delete().eq('id', data['id']).execute()
            
            # Mark as synced
            self._mark_synced(operation.id)
            
            logger.debug(f"Uploaded: {operation.operation_type} to {operation.table_name}")
            
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            
            # Retry logic
            operation.retry_count += 1
            if operation.retry_count < operation.max_retries:
                operation.priority += 1  # Lower priority for retry
                self.upload_queue.put(operation)
    
    def _download_worker(self):
        """Background worker for downloading remote changes."""
        while True:
            try:
                operation = self.download_queue.get(timeout=1)
                self._execute_download(operation)
            except Empty:
                # Periodic sync check
                if time.time() - self.last_sync_time > 60:  # Every minute
                    self._sync_with_remote()
                continue
            except Exception as e:
                logger.error(f"Download worker error: {e}")
    
    def _execute_download(self, operation: SyncOperation):
        """Execute download operation from Supabase."""
        try:
            # Check for conflicts
            local_data = self._get_local_data(operation.table_name, operation.data.get('id'))
            
            if local_data and self._has_conflict(local_data, operation.data):
                # Add to conflict queue
                self.conflict_queue.put({
                    'operation': operation,
                    'local_data': local_data
                })
                return
            
            # Apply remote change locally
            self._apply_local_change(operation)
            
            logger.debug(f"Downloaded: {operation.operation_type} from {operation.table_name}")
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
    
    def _conflict_resolver(self):
        """Background worker for resolving conflicts."""
        while True:
            try:
                conflict = self.conflict_queue.get(timeout=1)
                self._resolve_conflict(conflict)
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Conflict resolver error: {e}")
    
    def _resolve_conflict(self, conflict: Dict):
        """Resolve a sync conflict.
        
        Uses last-write-wins with vector clock comparison.
        """
        operation = conflict['operation']
        local_data = conflict['local_data']
        remote_data = operation.data
        
        # Get vector clocks
        local_clock = self._get_vector_clock(local_data.get('id', ''))
        remote_clock = self._get_vector_clock(remote_data.get('id', ''))
        
        # Determine winner
        if local_clock.happens_before(remote_clock):
            # Remote wins
            self._apply_local_change(operation)
            resolution = 'remote_wins'
        elif remote_clock.happens_before(local_clock):
            # Local wins - re-upload
            upload_op = SyncOperation(
                id=operation.id,
                operation_type='update',
                table_name=operation.table_name,
                data=local_data,
                timestamp=time.time(),
                namespace=operation.namespace,
                priority=1
            )
            self.upload_queue.put(upload_op)
            resolution = 'local_wins'
        else:
            # Concurrent - use timestamp
            if local_data.get('timestamp', 0) > remote_data.get('timestamp', 0):
                # Local wins
                resolution = 'local_wins_concurrent'
            else:
                # Remote wins
                self._apply_local_change(operation)
                resolution = 'remote_wins_concurrent'
        
        # Log conflict resolution
        self.conn.execute("""
            INSERT INTO conflict_log 
            (id, local_data, remote_data, timestamp, resolution, resolved)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (
            operation.id,
            json.dumps(local_data),
            json.dumps(remote_data),
            time.time(),
            resolution
        ))
        self.conn.commit()
        
        logger.info(f"Conflict resolved: {resolution} for {operation.table_name}")
    
    def _sync_with_remote(self):
        """Perform full sync with remote Supabase."""
        if not self.supabase_client or self.is_syncing:
            return
        
        with self.sync_lock:
            self.is_syncing = True
            self.last_sync_time = time.time()
            
            try:
                # Get tables to sync
                tables = ['context_memories', 'context_metadata', 'context_embeddings']
                
                for table_name in tables:
                    self._sync_table(table_name)
                
            except Exception as e:
                logger.error(f"Sync failed: {e}")
            finally:
                self.is_syncing = False
    
    def _sync_table(self, table_name: str):
        """Sync a specific table with remote."""
        # Get last sync state
        cursor = self.conn.execute(
            "SELECT last_sync_time, last_sync_id FROM sync_state WHERE table_name = ?",
            (table_name,)
        )
        row = cursor.fetchone()
        
        last_sync_time = row[0] if row else 0
        last_sync_id = row[1] if row else None
        
        # Fetch changes from remote
        table = self.supabase_client.table(table_name)
        query = table.select('*')
        
        if last_sync_time > 0:
            # Delta sync - only changes since last sync
            query = query.gt('sync_timestamp', last_sync_time)
        
        result = query.execute()
        
        for record in result.data:
            operation = SyncOperation(
                id=record.get('id', ''),
                operation_type='update',
                table_name=table_name,
                data=record,
                timestamp=time.time(),
                namespace=record.get('namespace', 'default')
            )
            self.download_queue.put(operation)
        
        # Update sync state
        self.conn.execute("""
            INSERT OR REPLACE INTO sync_state 
            (table_name, last_sync_time, last_sync_id, vector_clock)
            VALUES (?, ?, ?, ?)
        """, (
            table_name,
            time.time(),
            result.data[-1].get('id') if result.data else last_sync_id,
            json.dumps({})
        ))
        self.conn.commit()
    
    def queue_upload(self, 
                     table_name: str,
                     operation_type: str,
                     data: Dict[str, Any],
                     namespace: str = "default",
                     priority: int = 5):
        """Queue a change for upload to Supabase.
        
        Args:
            table_name: Table to sync to
            operation_type: Type of operation (insert, update, delete)
            data: Data to sync
            namespace: Namespace for isolation
            priority: Priority for sync (1=highest, 10=lowest)
        """
        operation = SyncOperation(
            id=hashlib.md5(f"{table_name}:{data.get('id', '')}:{time.time()}".encode()).hexdigest(),
            operation_type=operation_type,
            table_name=table_name,
            data=data,
            timestamp=time.time(),
            namespace=namespace,
            priority=priority
        )
        
        # Log to sync database
        self.conn.execute("""
            INSERT INTO sync_log 
            (id, operation_type, table_name, data, timestamp, namespace, synced, vector_clock)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?)
        """, (
            operation.id,
            operation.operation_type,
            operation.table_name,
            json.dumps(operation.data),
            operation.timestamp,
            operation.namespace,
            json.dumps({})
        ))
        self.conn.commit()
        
        # Add to upload queue
        self.upload_queue.put(operation)
    
    def _get_local_data(self, table_name: str, record_id: str) -> Optional[Dict]:
        """Get local data for conflict detection."""
        # This would query the actual local database
        # For now, return None (no local data)
        return None
    
    def _has_conflict(self, local_data: Dict, remote_data: Dict) -> bool:
        """Check if there's a conflict between local and remote data."""
        # Simple timestamp-based conflict detection
        local_timestamp = local_data.get('timestamp', 0)
        remote_timestamp = remote_data.get('timestamp', 0)
        
        # If both have been modified since last sync
        return abs(local_timestamp - remote_timestamp) < 1
    
    def _apply_local_change(self, operation: SyncOperation):
        """Apply a remote change to local database."""
        # This would update the actual local database
        # Implementation depends on your local storage structure
        pass
    
    def _mark_synced(self, operation_id: str):
        """Mark an operation as synced."""
        self.conn.execute(
            "UPDATE sync_log SET synced = 1, sync_time = ? WHERE id = ?",
            (time.time(), operation_id)
        )
        self.conn.commit()
    
    def _get_vector_clock(self, record_id: str) -> VectorClock:
        """Get vector clock for a record."""
        if record_id not in self.vector_clocks:
            self.vector_clocks[record_id] = VectorClock()
        return self.vector_clocks[record_id]
    
    def get_sync_stats(self) -> Dict[str, Any]:
        """Get synchronization statistics."""
        cursor = self.conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN synced = 1 THEN 1 ELSE 0 END) as synced,
                SUM(CASE WHEN synced = 0 THEN 1 ELSE 0 END) as pending
            FROM sync_log
        """)
        row = cursor.fetchone()
        
        conflicts = self.conn.execute(
            "SELECT COUNT(*) FROM conflict_log WHERE resolved = 0"
        ).fetchone()[0]
        
        return {
            "total_operations": row[0],
            "synced": row[1],
            "pending": row[2],
            "unresolved_conflicts": conflicts,
            "upload_queue_size": self.upload_queue.qsize(),
            "download_queue_size": self.download_queue.qsize(),
            "last_sync_time": self.last_sync_time,
            "is_syncing": self.is_syncing
        }
    
    def force_sync(self):
        """Force immediate sync with remote."""
        self._sync_with_remote()
    
    def close(self):
        """Close sync engine and clean up resources."""
        if self.ws_connection:
            asyncio.create_task(self.ws_connection.close())
        if self.conn:
            self.conn.close()

# Singleton instance
_sync_engine = None

def get_sync_engine(supabase_url: Optional[str] = None,
                   supabase_key: Optional[str] = None) -> SyncEngine:
    """Get or create the global sync engine."""
    global _sync_engine
    if _sync_engine is None:
        # Try to get from environment
        if not supabase_url:
            supabase_url = os.getenv('SUPABASE_URL')
        if not supabase_key:
            supabase_key = os.getenv('SUPABASE_KEY')
        
        _sync_engine = SyncEngine(
            supabase_url=supabase_url,
            supabase_key=supabase_key
        )
    return _sync_engine