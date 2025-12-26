#!/usr/bin/env python3
"""
Local test script for Lyco Eisenhower Matrix
Tests core functionality without Telegram
"""

import os
import sys
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.lyco.lyco_eisenhower import LycoEisenhowerAgent, Task, Quadrant

def test_task_parsing():
    """Test natural language task parsing"""
    print("\n📝 Testing Task Parsing")
    print("=" * 50)
    
    agent = LycoEisenhowerAgent()
    
    test_cases = [
        "Schedule Persy's soccer registration due Friday",
        "Review insurance documents urgent",
        "Pick up prescription tomorrow important",
        "Plan Q2 strategy meeting next week",
        "Buy milk",
        "Fix critical production bug ASAP",
    ]
    
    for message in test_cases:
        task = agent.parse_task_from_message(message, "mene")
        if task:
            quadrant_names = {
                Quadrant.DO_FIRST: "🔴 DO FIRST",
                Quadrant.SCHEDULE: "🟡 SCHEDULE", 
                Quadrant.DELEGATE: "🟢 DELEGATE",
                Quadrant.DONT_DO: "⚪ DON'T DO"
            }
            print(f"\n✅ '{message[:40]}...'")
            print(f"   Title: {task.title}")
            print(f"   Urgency: {task.urgency}/5, Importance: {task.importance}/5")
            print(f"   Quadrant: {quadrant_names[task.quadrant]}")
            print(f"   Due: {task.due_date or 'Not set'}")
            print(f"   Tags: {', '.join(task.context_tags)}")

def test_matrix_display():
    """Test Eisenhower Matrix display"""
    print("\n\n📊 Testing Matrix Display")
    print("=" * 50)
    
    agent = LycoEisenhowerAgent()
    
    # Create sample tasks
    sample_tasks = [
        Task(title="Emergency server fix", urgency=5, importance=5),
        Task(title="Plan team retreat", urgency=2, importance=5),
        Task(title="Reply to vendor email", urgency=4, importance=2),
        Task(title="Clean desk drawer", urgency=1, importance=1),
        Task(title="Doctor appointment", urgency=5, importance=4, due_date=datetime.now().isoformat()),
        Task(title="Review quarterly goals", urgency=3, importance=5),
    ]
    
    # Group by quadrant
    quadrants = {q: [] for q in Quadrant}
    for task in sample_tasks:
        quadrants[task.quadrant].append(task)
    
    # Display
    output = agent.format_matrix_display(quadrants)
    print(output)

def test_message_handling():
    """Test message handling"""
    print("\n\n💬 Testing Message Handling")
    print("=" * 50)
    
    agent = LycoEisenhowerAgent()
    
    test_messages = [
        ("Add task: Schedule dentist appointment next week", "Task addition"),
        ("Show today", "Today's tasks"),
        ("What's my matrix?", "Matrix view"),
        ("help", "Help command"),
        ("Random message that's actually a task", "Implicit task"),
    ]
    
    for message, description in test_messages:
        print(f"\n📨 {description}: '{message}'")
        response = agent.handle_message(message, "mene")
        print(f"🤖 Response:\n{response[:200]}...")

def test_date_parsing():
    """Test date parsing functionality"""
    print("\n\n📅 Testing Date Parsing")
    print("=" * 50)
    
    agent = LycoEisenhowerAgent()
    
    date_tests = [
        "Task due today",
        "Task due tomorrow",
        "Task due Friday",
        "Task due Monday",
        "Task due next week",
    ]
    
    for message in date_tests:
        task = agent.parse_task_from_message(message, "mene")
        if task and task.due_date:
            due = datetime.fromisoformat(task.due_date)
            days_until = (due.date() - datetime.now().date()).days
            print(f"'{message}' -> {task.due_date} ({days_until} days)")

def main():
    """Run all tests"""
    print("🧪 Lyco Eisenhower Matrix - Local Testing")
    print("=" * 60)
    
    # Check environment
    print("\n🔧 Environment Check:")
    env_vars = [
        "ANTHROPIC_API_KEY",
        "NOTION_API_KEY", 
        "NOTION_TASKS_DATABASE_ID",
        "TELEGRAM_BOT_TOKEN"
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}: {'*' * 8}{value[-4:]}")
        else:
            print(f"  ❌ {var}: Not set")
    
    # Run tests
    try:
        test_task_parsing()
        test_matrix_display()
        test_date_parsing()
        test_message_handling()
        
        print("\n\n✅ All tests completed!")
        print("\n💡 Next steps:")
        print("1. Set environment variables in .env file")
        print("2. Run ./deploy.sh to deploy to VPS")
        print("3. Test with @LycurgusBot on Telegram")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()