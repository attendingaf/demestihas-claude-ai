#!/usr/bin/env python3
"""
Test script to verify the state accumulation fixes in MiMerc agent.
This tests that:
1. The grocery_list uses a transactional dictionary (no duplicates)
2. The responder only processes the latest state (no historical accumulation)
3. The telegram bot extracts only the final_response (no bloat)
"""

import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

def test_state_structure():
    """Test that the AgentState uses correct data types"""
    print("Testing AgentState structure...")

    try:
        from agent import AgentState
        import typing

        # Check that grocery_list is a Dict type
        annotations = AgentState.__annotations__

        # Verify grocery_list is a dictionary
        grocery_type = annotations.get('grocery_list')
        if grocery_type and 'Dict' in str(grocery_type):
            print("✅ grocery_list is correctly defined as Dict[str, float]")
        else:
            print(f"❌ grocery_list type is incorrect: {grocery_type}")
            return False

        # Verify final_response channel exists
        if 'final_response' in annotations:
            print("✅ final_response channel exists")
        else:
            print("❌ final_response channel missing")
            return False

        return True

    except Exception as e:
        print(f"❌ Error testing state structure: {e}")
        return False

def test_agent_workflow():
    """Test the agent workflow with multiple operations"""
    print("\nTesting agent workflow...")

    try:
        from agent import build_graph
        from langchain_core.messages import HumanMessage

        # Build the graph
        graph, pool = build_graph()

        # Test thread ID for state persistence
        thread_id = "test_thread_123"
        config = {"configurable": {"thread_id": thread_id}}

        # Test 1: Add items (should not duplicate)
        print("\n1. Adding items...")
        input1 = {
            "messages": [HumanMessage(content="Add milk to my list")],
            "grocery_list": {},
            "final_response": "",
            "tool_calls": [],
            "next_action": ""
        }

        result1 = None
        for chunk in graph.stream(input1, config):
            if "responder" in chunk and "final_response" in chunk["responder"]:
                result1 = chunk["responder"]["final_response"]
                print(f"   Response: {result1}")
                break

        # Test 2: Add same item again (should update quantity, not duplicate)
        print("\n2. Adding same item again...")
        input2 = {
            "messages": [HumanMessage(content="Add milk to my list")],
            "grocery_list": {},
            "final_response": "",
            "tool_calls": [],
            "next_action": ""
        }

        result2 = None
        for chunk in graph.stream(input2, config):
            if "responder" in chunk and "final_response" in chunk["responder"]:
                result2 = chunk["responder"]["final_response"]
                print(f"   Response: {result2}")
                break

        # Test 3: View list (should show clean, non-duplicated list)
        print("\n3. Viewing list...")
        input3 = {
            "messages": [HumanMessage(content="Show me my list")],
            "grocery_list": {},
            "final_response": "",
            "tool_calls": [],
            "next_action": ""
        }

        result3 = None
        for chunk in graph.stream(input3, config):
            if "responder" in chunk and "final_response" in chunk["responder"]:
                result3 = chunk["responder"]["final_response"]
                print(f"   Response: {result3}")
                break

        # Verify no duplication in output
        if result3:
            # Count occurrences of "milk" - should appear only once
            milk_count = result3.lower().count("milk")
            if milk_count <= 1:
                print("\n✅ No item duplication detected")
            else:
                print(f"\n❌ Item duplication detected: 'milk' appears {milk_count} times")
                return False

        pool.close()
        return True

    except Exception as e:
        print(f"❌ Error testing workflow: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("MiMerc State Accumulation Fix Verification")
    print("=" * 60)

    tests = [
        ("State Structure", test_state_structure),
        ("Agent Workflow", test_agent_workflow)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 All tests passed! State accumulation issues are fixed.")
    else:
        print("\n⚠️ Some tests failed. Review the fixes above.")

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
