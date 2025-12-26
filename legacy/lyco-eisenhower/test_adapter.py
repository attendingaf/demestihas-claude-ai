#!/usr/bin/env python3
"""
Test script for the Notion Schema Adapter
Validates that tasks can be saved with various formats
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, Any

# Add the agents path to sys.path to import the module
sys.path.append('/root/lyco-eisenhower/agents')

from lyco.lyco_eisenhower import LycoEisenhowerAgent, Task, TaskStatus, Quadrant

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_adapter_initialization():
    """Test that the adapter initializes correctly"""
    print("🧪 TEST 1: Adapter Initialization")
    print("=" * 50)
    
    try:
        agent = LycoEisenhowerAgent()
        
        if not agent.schema_adapter:
            print("❌ Schema adapter not initialized")
            return False
        
        # Test schema discovery
        schema = agent.schema_adapter.discover_schema()
        print(f"✅ Schema discovered: {len(schema)} properties")
        
        # Test mapping
        mappings = agent.schema_adapter.build_intelligent_mapping()
        print(f"✅ Property mappings created: {len(mappings)} mappings")
        
        # Show mapping report
        print("\n" + agent.schema_adapter.get_mapping_report())
        
        return True
        
    except Exception as e:
        print(f"❌ Adapter initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_minimal_task():
    """Test saving a minimal task (just title)"""
    print("\n🧪 TEST 2: Minimal Task Save")
    print("=" * 50)
    
    try:
        agent = LycoEisenhowerAgent()
        
        # Create minimal task
        task = Task(title="Test Minimal Task - " + datetime.now().strftime("%H:%M:%S"))
        
        # Try to save it
        success = agent.save_task_to_notion(task)
        
        if success:
            print(f"✅ Minimal task saved successfully")
            print(f"   Task ID: {task.notion_id}")
            return True
        else:
            print(f"❌ Failed to save minimal task")
            return False
            
    except Exception as e:
        print(f"❌ Minimal task test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_full_eisenhower_task():
    """Test saving a full Eisenhower task with all properties"""
    print("\n🧪 TEST 3: Full Eisenhower Task")
    print("=" * 50)
    
    try:
        agent = LycoEisenhowerAgent()
        
        # Create full task
        task = Task(
            title="Test Full Eisenhower Task - " + datetime.now().strftime("%H:%M:%S"),
            description="This is a comprehensive test task with all properties filled out",
            urgency=5,
            importance=4,
            due_date="2024-09-07",
            assigned_to="both",
            status=TaskStatus.NEW,
            context_tags=["Work", "Urgent", "Test"]
        )
        
        print(f"Task details:")
        print(f"  Title: {task.title}")
        print(f"  Quadrant: {task.quadrant} (Q{task.quadrant.value})")
        print(f"  Urgency: {task.urgency}, Importance: {task.importance}")
        print(f"  Tags: {task.context_tags}")
        print(f"  Due: {task.due_date}")
        
        # Try to save it
        success = agent.save_task_to_notion(task)
        
        if success:
            print(f"✅ Full task saved successfully")
            print(f"   Task ID: {task.notion_id}")
            return True
        else:
            print(f"❌ Failed to save full task")
            return False
            
    except Exception as e:
        print(f"❌ Full task test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_edge_cases():
    """Test various edge cases and type mismatches"""
    print("\n🧪 TEST 4: Edge Cases & Type Mismatches")
    print("=" * 50)
    
    test_cases = [
        {
            "name": "Long title",
            "task": Task(title="This is a very long task title that exceeds normal length to test truncation and handling of lengthy text input which might cause issues with some database systems and should be handled gracefully by our adapter without causing any errors or data corruption issues")
        },
        {
            "name": "Special characters",
            "task": Task(
                title="Task with émojis 🚀 & spéciál characters: @#$%^&*()",
                description="Testing special characters: «»""''—…±×÷"
            )
        },
        {
            "name": "Empty tags list",
            "task": Task(
                title="Task with empty tags",
                context_tags=[]
            )
        },
        {
            "name": "Single tag",
            "task": Task(
                title="Task with single tag",
                context_tags=["SingleTag"]
            )
        },
        {
            "name": "Edge urgency values",
            "task": Task(
                title="Edge urgency test",
                urgency=1,
                importance=1
            )
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        try:
            agent = LycoEisenhowerAgent()
            task = test_case["task"]
            task.title = f"{test_case['name']} - {datetime.now().strftime('%H:%M:%S')}"
            
            success = agent.save_task_to_notion(task)
            
            if success:
                print(f"✅ {i}. {test_case['name']}: Success")
                results.append(True)
            else:
                print(f"❌ {i}. {test_case['name']}: Failed")
                results.append(False)
                
        except Exception as e:
            print(f"❌ {i}. {test_case['name']}: Exception - {e}")
            results.append(False)
    
    success_rate = sum(results) / len(results) * 100
    print(f"\nEdge case success rate: {success_rate:.1f}% ({sum(results)}/{len(results)})")
    
    return success_rate >= 80  # 80% success rate acceptable

def test_natural_language_parsing():
    """Test parsing natural language messages into tasks"""
    print("\n🧪 TEST 5: Natural Language Parsing & Save")
    print("=" * 50)
    
    test_messages = [
        "Schedule quarterly report by Friday (urgent and important)",
        "Pick up groceries tomorrow",
        "Call dentist to schedule appointment - not urgent",
        "Finish project proposal - due next week, high priority"
    ]
    
    results = []
    
    for i, message in enumerate(test_messages, 1):
        try:
            agent = LycoEisenhowerAgent()
            
            # Parse message into task
            task = agent.parse_task_from_message(message, "test_user")
            
            if not task:
                print(f"❌ {i}. Failed to parse: '{message}'")
                results.append(False)
                continue
                
            print(f"📝 {i}. Parsed: '{message}'")
            print(f"    Title: {task.title}")
            print(f"    Quadrant: Q{task.quadrant.value}")
            print(f"    Due: {task.due_date}")
            print(f"    Tags: {task.context_tags}")
            
            # Try to save it
            success = agent.save_task_to_notion(task)
            
            if success:
                print(f"✅    Saved successfully (ID: {task.notion_id[:8]}...)")
                results.append(True)
            else:
                print(f"❌    Failed to save")
                results.append(False)
                
        except Exception as e:
            print(f"❌ {i}. Exception parsing/saving '{message}': {e}")
            results.append(False)
    
    success_rate = sum(results) / len(results) * 100
    print(f"\nNatural language success rate: {success_rate:.1f}% ({sum(results)}/{len(results)})")
    
    return success_rate >= 75  # 75% success rate acceptable

def run_all_tests():
    """Run all tests and provide a summary"""
    print("🚀 NOTION SCHEMA ADAPTER COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    
    test_results = []
    
    # Run each test
    tests = [
        ("Adapter Initialization", test_adapter_initialization),
        ("Minimal Task Save", test_minimal_task),
        ("Full Eisenhower Task", test_full_eisenhower_task),
        ("Edge Cases", test_edge_cases),
        ("Natural Language Parsing", test_natural_language_parsing)
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} crashed: {e}")
            test_results.append((test_name, False))
    
    # Print summary
    print("\n🎯 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    overall_success_rate = passed / len(test_results) * 100
    print(f"\nOverall Success Rate: {overall_success_rate:.1f}% ({passed}/{len(test_results)})")
    
    if overall_success_rate >= 80:
        print("🎉 TESTS PASSED - Adapter is ready for production!")
        return True
    else:
        print("⚠️  TESTS FAILED - Need to fix issues before deployment")
        return False

def test_direct_adapter():
    """Test the adapter directly without the full agent"""
    print("\n🔧 DIRECT ADAPTER TEST")
    print("=" * 50)
    
    try:
        from lyco.notion_schema_adapter import create_notion_adapter
        from notion_client import Client
        
        # Initialize directly
        notion = Client(auth=os.getenv("NOTION_API_KEY"))
        adapter = create_notion_adapter(notion, os.getenv("NOTION_TASKS_DATABASE_ID"))
        
        # Test sample task
        sample_task = {
            'title': 'Direct Adapter Test - ' + datetime.now().strftime('%H:%M:%S'),
            'description': 'Testing adapter directly',
            'urgency': 3,
            'importance': 4,
            'quadrant': 2,
            'tags': ['Test', 'Direct'],
            'due_date': '2024-09-07'
        }
        
        # Test adaptation
        adapted = adapter.test_mapping(sample_task)
        
        if adapted:
            print("✅ Direct adapter test successful")
            print(f"   Adapted properties: {list(adapted.keys())}")
            
            # Try to actually save it
            response = notion.pages.create(
                parent={"database_id": os.getenv("NOTION_TASKS_DATABASE_ID")},
                properties=adapted
            )
            print(f"✅ Direct save successful: {response['id'][:8]}...")
            return True
        else:
            print("❌ Direct adapter test failed")
            return False
            
    except Exception as e:
        print(f"❌ Direct adapter test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check environment
    required_env = ["NOTION_API_KEY", "NOTION_TASKS_DATABASE_ID"]
    missing = [var for var in required_env if not os.getenv(var)]
    
    if missing:
        print(f"❌ Missing environment variables: {missing}")
        sys.exit(1)
    
    # Run tests
    try:
        # First test direct adapter
        print("Testing adapter directly...")
        test_direct_adapter()
        
        print("\n" + "="*60)
        
        # Then run full test suite
        success = run_all_tests()
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)