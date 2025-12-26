#!/usr/bin/env python3
"""
Quick diagnostic script to check Lyco database status
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database import DatabaseManager
from datetime import datetime, timedelta

async def check_database():
    """Check what's in the database"""
    db = DatabaseManager()
    
    print("🔍 LYCO 2.0 DATABASE STATUS")
    print("=" * 50)
    
    # Check signals
    signals_count = await db.fetch_one(
        "SELECT COUNT(*) as count FROM signals WHERE processed = false"
    )
    print(f"\n📥 Unprocessed Signals: {signals_count['count'] if signals_count else 0}")
    
    # Check recent signals
    recent_signals = await db.fetch_all(
        """
        SELECT source, content, created_at 
        FROM signals 
        ORDER BY created_at DESC 
        LIMIT 5
        """
    )
    
    if recent_signals:
        print("\nRecent signals:")
        for sig in recent_signals:
            print(f"  - {sig['source']}: {sig['content'][:50]}... ({sig['created_at']})")
    
    # Check tasks
    tasks_count = await db.fetch_one(
        """
        SELECT 
            COUNT(*) FILTER (WHERE completed_at IS NULL AND skipped_at IS NULL) as pending,
            COUNT(*) FILTER (WHERE completed_at IS NOT NULL) as completed,
            COUNT(*) FILTER (WHERE skipped_at IS NOT NULL) as skipped,
            COUNT(*) as total
        FROM tasks
        """
    )
    
    if tasks_count:
        print(f"\n📋 Tasks Status:")
        print(f"  - Pending: {tasks_count['pending']}")
        print(f"  - Completed: {tasks_count['completed']}")
        print(f"  - Skipped: {tasks_count['skipped']}")
        print(f"  - Total: {tasks_count['total']}")
    else:
        print("\n📋 No tasks in database yet")
    
    # Check recent tasks
    recent_tasks = await db.fetch_all(
        """
        SELECT id, content, energy_level, created_at 
        FROM tasks 
        WHERE completed_at IS NULL AND skipped_at IS NULL
        ORDER BY created_at DESC 
        LIMIT 5
        """
    )
    
    if recent_tasks:
        print("\n✅ Available tasks for rounds:")
        for task in recent_tasks:
            energy = task['energy_level'] or 'uncategorized'
            print(f"  - [{energy}] {task['content'][:60]}...")
    else:
        print("\n⚠️ No pending tasks available")
    
    # Check if ambient capture is working
    last_signal = await db.fetch_one(
        "SELECT MAX(created_at) as last FROM signals"
    )
    
    if last_signal and last_signal['last']:
        time_since = datetime.now() - last_signal['last']
        print(f"\n⏰ Last signal captured: {int(time_since.total_seconds() / 60)} minutes ago")
        if time_since > timedelta(minutes=10):
            print("  ⚠️ Ambient capture may be stuck (should run every 5 min)")

if __name__ == "__main__":
    asyncio.run(check_database())
