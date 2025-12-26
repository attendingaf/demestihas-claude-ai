#!/usr/bin/env python3
"""
Debug script to check why Rounds Mode isn't finding tasks
"""
import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Set up environment
from dotenv import load_dotenv
load_dotenv()

import asyncio
import httpx

async def debug_rounds():
    """Check what's happening with rounds queries"""
    
    # Connect to Supabase
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
    
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        print("🔍 ROUNDS MODE DEBUG")
        print("=" * 50)
        
        # 1. Check total tasks
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/tasks?select=id,content,energy_level,completed_at,skipped_at,deleted_at",
            headers=headers
        )
        all_tasks = response.json()
        
        print(f"\n📊 Total tasks in database: {len(all_tasks)}")
        
        # Count by status
        pending = [t for t in all_tasks if not t.get('completed_at') and not t.get('skipped_at') and not t.get('deleted_at')]
        print(f"   - Pending (not completed/skipped/deleted): {len(pending)}")
        
        # 2. Check task_categories table
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/task_categories?select=*",
            headers=headers
        )
        categories = response.json()
        print(f"\n📁 Task categories entries: {len(categories)}")
        
        # 3. Show sample of pending tasks
        if pending:
            print("\n✅ Sample pending tasks:")
            for task in pending[:3]:
                print(f"   - ID: {task['id']}")
                print(f"     Content: {task['content'][:60]}...")
                print(f"     Energy: {task.get('energy_level', 'NULL')}")
        
        # 4. Try the actual rounds queries
        print("\n🔬 Testing Rounds Queries:")
        
        # Morning rounds query (simplified)
        morning_query = f"{SUPABASE_URL}/rest/v1/tasks?select=*&completed_at=is.null&deleted_at=is.null&limit=20"
        response = await client.get(morning_query, headers=headers)
        morning_tasks = response.json()
        print(f"   - Morning query results: {len(morning_tasks)} tasks")
        
        # Evening rounds query
        evening_query = f"{SUPABASE_URL}/rest/v1/tasks?select=*&completed_at=is.null&deleted_at=is.null&energy_level=eq.low&limit=15"
        response = await client.get(evening_query, headers=headers)
        evening_tasks = response.json()
        print(f"   - Evening query results: {len(evening_tasks)} tasks")
        
        # 5. Check for missing columns
        print("\n⚠️  Potential Issues:")
        
        if pending and not categories:
            print("   - task_categories table is empty (tasks not categorized)")
            print("   - This is likely why rounds aren't finding tasks")
            
        sample_task = pending[0] if pending else {}
        missing_cols = []
        
        expected_cols = ['deleted_at', 'parked_at', 'energy_level']
        for col in expected_cols:
            if col not in sample_task:
                missing_cols.append(col)
        
        if missing_cols:
            print(f"   - Missing columns in tasks table: {missing_cols}")
            
        # 6. Show the fix
        if pending and not categories:
            print("\n🔧 FIX: Populate task_categories table")
            print("   Run this SQL in Supabase:")
            print("   ```sql")
            print("   -- Categorize all pending tasks")
            print("   INSERT INTO task_categories (task_id, energy_level, context, time_sensitivity)")
            print("   SELECT ")
            print("     id as task_id,")
            print("     COALESCE(energy_level, 'medium') as energy_level,")
            print("     'work' as context,")
            print("     'normal' as time_sensitivity")
            print("   FROM tasks")
            print("   WHERE completed_at IS NULL")
            print("     AND id NOT IN (SELECT task_id FROM task_categories);")
            print("   ```")

if __name__ == "__main__":
    asyncio.run(debug_rounds())
