#!/usr/bin/env python3
"""
Manual task creation for Lyco 2.0
Adds test tasks directly to the database
"""
import os
import sys
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
import json

# Try to use the existing database module
try:
    from src.database import DatabaseManager
    use_db_manager = True
except:
    # Fallback to direct psycopg2 if imports fail
    use_db_manager = False
    import psycopg2
    from psycopg2.extras import RealDictCursor

async def add_test_tasks():
    """Add test tasks to the database"""
    
    # Test tasks with different energy levels
    test_tasks = [
        {
            "content": "Review Q1 financial reports and prepare executive summary",
            "energy_level": "high",
            "time_estimate": 45,
            "next_action": "Open financial dashboard and export Q1 data",
            "context_required": ["financial_reports", "dashboard_access"]
        },
        {
            "content": "Reply to Sarah's email about partnership proposal",
            "energy_level": "medium",
            "time_estimate": 15,
            "next_action": "Read proposal document and draft initial thoughts",
            "context_required": ["email"]
        },
        {
            "content": "Schedule team 1:1s for next week",
            "energy_level": "low",
            "time_estimate": 10,
            "next_action": "Check team calendar availability",
            "context_required": ["calendar"]
        },
        {
            "content": "Analyze competitor's new product launch strategy",
            "energy_level": "high",
            "time_estimate": 60,
            "next_action": "Gather market intelligence reports",
            "context_required": ["research", "market_data"]
        },
        {
            "content": "Update LinkedIn profile with recent achievements",
            "energy_level": "low",
            "time_estimate": 20,
            "next_action": "Login to LinkedIn and navigate to profile",
            "context_required": ["linkedin"]
        },
        {
            "content": "Prepare for board meeting presentation",
            "energy_level": "high",
            "time_estimate": 90,
            "next_action": "Review last quarter's deck and update metrics",
            "context_required": ["presentation", "metrics"],
            "deadline": datetime.now() + timedelta(days=2)
        },
        {
            "content": "Call dentist to reschedule appointment",
            "energy_level": "low",
            "time_estimate": 5,
            "next_action": "Find dentist phone number",
            "context_required": ["phone"]
        },
        {
            "content": "Review and approve marketing budget allocation",
            "energy_level": "medium",
            "time_estimate": 30,
            "next_action": "Open budget spreadsheet",
            "context_required": ["budget", "spreadsheet"],
            "deadline": datetime.now() + timedelta(days=1)
        }
    ]
    
    if use_db_manager:
        db = DatabaseManager()
        
        print("Adding test tasks using DatabaseManager...")
        for task in test_tasks:
            task_id = await db.create_task(
                content=task["content"],
                energy_level=task["energy_level"],
                time_estimate=task.get("time_estimate"),
                next_action=task.get("next_action"),
                context_required=task.get("context_required"),
                deadline=task.get("deadline")
            )
            print(f"✅ Added: {task['content'][:50]}... (ID: {task_id})")
    else:
        # Direct database connection
        print("Connecting directly to Supabase...")
        
        # Get connection info from environment
        from dotenv import load_dotenv
        load_dotenv()
        
        # Build connection string
        db_host = "db.oletgdpevhdxbywrqeyh.supabase.co"
        db_name = "postgres"
        db_user = "postgres"
        db_pass = input("Enter Supabase database password: ")
        
        conn_string = f"host={db_host} dbname={db_name} user={db_user} password={db_pass}"
        
        conn = psycopg2.connect(conn_string)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        for task in test_tasks:
            task_id = str(uuid4())
            
            cur.execute("""
                INSERT INTO tasks (
                    id, content, energy_level, time_estimate, 
                    next_action, context_required, deadline, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, NOW()
                )
            """, (
                task_id,
                task["content"],
                task["energy_level"],
                task.get("time_estimate"),
                task.get("next_action"),
                json.dumps(task.get("context_required", [])),
                task.get("deadline")
            ))
            
            print(f"✅ Added: {task['content'][:50]}...")
        
        conn.commit()
        cur.close()
        conn.close()
    
    print(f"\n🎉 Added {len(test_tasks)} test tasks!")
    print("\n📋 Tasks by energy level:")
    print("  - High energy: 3 tasks (strategic/analytical)")
    print("  - Medium energy: 2 tasks (communication)")
    print("  - Low energy: 3 tasks (admin/routine)")
    print("\n🚀 Next steps:")
    print("1. Open main UI: http://localhost:8000")
    print("2. Try Rounds Mode: http://localhost:8000/rounds")

if __name__ == "__main__":
    if use_db_manager:
        asyncio.run(add_test_tasks())
    else:
        # Run synchronously with psycopg2
        import asyncio
        asyncio.run(add_test_tasks())
