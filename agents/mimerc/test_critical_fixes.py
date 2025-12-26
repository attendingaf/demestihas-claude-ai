#!/usr/bin/env python3
"""
Test script to verify the critical fixes:
1. Item removal works correctly
2. No response duplication occurs
"""

import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

def test_removal_logic():
    """Test that items are properly removed from the dictionary"""
    print("Testing removal logic...")

    try:
        from agent import build_graph
        from langchain_core.messages import HumanMessage

        # Build the graph
        graph, pool = build_graph()

        # Test thread ID
        thread_id = "test_removal_123"
        config = {"configurable": {"thread_id": thread_id}}

        # Step 1: Add items
        print("\n1. Adding items to list...")
        add_input = {
            "messages": [HumanMessage(content="Add milk, bread, and eggs to my list")],
            "grocery_list": {},
            "final_response": "",
            "tool_calls": [],
            "next_action": ""
        }

        for chunk in graph.stream(add_input, config):
            if "responder" in chunk and "final_response" in chunk["responder"]:
                print(f"   Response: {chunk['responder']['final_response']}")
                break

        # Step 2: View list to confirm items added
        print("\n2. Viewing list before removal...")
        view_input = {
            "messages": [HumanMessage(content="Show me my list")],
            "grocery_list": {},
            "final_response": "",
            "tool_calls": [],
            "next_action": ""
        }

        list_before = ""
        for chunk in graph.stream(view_input, config):
            if "responder" in chunk and "final_response" in chunk["responder"]:
                list_before = chunk["responder"]["final_response"]
                print(f"   List: {list_before}")
                break

        # Step 3: Remove milk
        print("\n3. Removing milk from list...")
        remove_input = {
            "messages": [HumanMessage(content="Remove milk from my list")],
            "grocery_list": {},
            "final_response": "",
            "tool_calls": [],
            "next_action": ""
        }

        for chunk in graph.stream(remove_input, config):
            if "responder" in chunk and "final_response" in chunk["responder"]:
                print(f"   Response: {chunk['responder']['final_response']}")
                break

        # Step 4: View list to confirm removal
        print("\n4. Viewing list after removal...")
        view_input2 = {
            "messages": [HumanMessage(content="What's on my list?")],
            "grocery_list": {},
            "final_response": "",
            "tool_calls": [],
            "next_action": ""
        }

        list_after = ""
        for chunk in graph.stream(view_input2, config):
            if "responder" in chunk and "final_response" in chunk["responder"]:
                list_after = chunk["responder"]["final_response"]
                print(f"   List: {list_after}")
                break

        # Verify milk was removed
        if "milk" in list_before.lower() and "milk" not in list_after.lower():
            print("\n✅ Item removal works correctly!")
            success = True
        else:
            print("\n❌ Item removal failed - milk still in list")
            success = False

        pool.close()
        return success

    except Exception as e:
        print(f"❌ Error testing removal: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_response_deduplication():
    """Test that responses are not duplicated"""
    print("\nTesting response deduplication...")

    try:
        from telegram_bot import run_agent_sync

        # Test thread
        thread_id = "test_dedup_456"

        # Add items
        response1 = run_agent_sync("Add apples and oranges to my list", thread_id)
        print(f"\n1. Add response: {response1}")

        # View list
        response2 = run_agent_sync("Show me my grocery list", thread_id)
        print(f"\n2. View response:\n{response2}")

        # Count how many times "apples" appears in the response
        apple_count = response2.lower().count("apples")
        orange_count = response2.lower().count("oranges")

        # Each item should appear exactly once in the list
        if apple_count == 1 and orange_count == 1:
            print("\n✅ No response duplication detected!")

            # Also check that the response doesn't contain multiple list outputs
            list_header_count = response2.lower().count("your current grocery list")
            if list_header_count <= 1:
                print("✅ Single list output confirmed!")
                return True
            else:
                print(f"❌ Multiple list outputs detected: {list_header_count} occurrences")
                return False
        else:
            print(f"❌ Response duplication detected:")
            print(f"   'apples' appears {apple_count} times")
            print(f"   'oranges' appears {orange_count} times")
            return False

    except Exception as e:
        print(f"❌ Error testing deduplication: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all critical tests"""
    print("=" * 60)
    print("Critical Fixes Verification")
    print("=" * 60)

    tests = [
        ("Removal Logic", test_removal_logic),
        ("Response Deduplication", test_response_deduplication)
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"Running: {test_name}")
        print('='*60)
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
        print("\n🎉 All critical fixes verified successfully!")
        print("• Items are properly removed from the list")
        print("• No response duplication occurs")
    else:
        print("\n⚠️ Some tests failed. Review the fixes above.")

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
