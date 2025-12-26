#!/usr/bin/env python3
"""Emergency validation test for Yanay task routing"""

import asyncio
import aiohttp
import json
import sys
from datetime import datetime

async def test_task_routing():
    """Test that task queries are properly routed to Lyco"""
    
    # Test messages that should go to Lyco
    test_queries = [
        "show my tasks",
        "what tasks do I have",
        "list all my tasks",
        "show urgent tasks"
    ]
    
    print("=" * 60)
    print("EMERGENCY VALIDATION TEST - YANAY TASK ROUTING")
    print("=" * 60)
    print(f"Time: {datetime.now().isoformat()}")
    print()
    
    # Import Yanay components
    try:
        from yanay import YanayOrchestrator
        orchestrator = YanayOrchestrator()
        await orchestrator.initialize()
        print("✅ Yanay Orchestrator initialized")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return False
    
    success_count = 0
    failure_count = 0
    
    for query in test_queries:
        print(f"\n📝 Testing: '{query}'")
        try:
            # Process through Yanay
            response = await orchestrator.process_message(
                user_message=query,
                user_id="test_user",
                user_name="TestUser"
            )
            
            # Check if response indicates proper routing
            if "Failed to query tasks: 400" in response:
                print(f"   ❌ FAILED - Got 400 error (calendar routing issue)")
                failure_count += 1
            elif "tasks" in response.lower() or "fetching" in response.lower():
                print(f"   ✅ SUCCESS - Properly routed to task handler")
                print(f"   Response: {response[:100]}")
                success_count += 1
            else:
                print(f"   ⚠️  UNCLEAR - Response: {response[:100]}")
                failure_count += 1
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            failure_count += 1
    
    print("\n" + "=" * 60)
    print("VALIDATION RESULTS:")
    print(f"✅ Successful: {success_count}/{len(test_queries)}")
    print(f"❌ Failed: {failure_count}/{len(test_queries)}")
    
    if failure_count == 0:
        print("\n🎉 ALL TESTS PASSED - TASK ROUTING RESTORED!")
        return True
    else:
        print("\n⚠️  SOME TESTS FAILED - REVIEW NEEDED")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_task_routing())
    sys.exit(0 if result else 1)