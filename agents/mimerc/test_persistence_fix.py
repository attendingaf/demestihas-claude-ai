#!/usr/bin/env python3
"""
Test script to verify the state persistence fix.
This tests that the grocery_list persists across multiple invocations.
"""

import os
import sys
import time
from dotenv import load_dotenv

# Load environment
load_dotenv()

def test_state_persistence():
    """Test that grocery list persists across multiple agent invocations"""
    print("Testing state persistence...")

    try:
        from agent import build_graph
        from langchain_core.messages import HumanMessage

        # Build the graph
        graph, pool = build_graph()

        # Test thread ID for persistence
        thread_id = "test_persistence_789"
        config = {"configurable": {"thread_id": thread_id}}

        # Step 1: Add first item
        print("\n1. Adding first item (apples)...")
        input1 = {
            "messages": [HumanMessage(content="Add apples to my list")],
            # NOT initializing grocery_list - let checkpointer load it
            "final_response": "",
            "tool_calls": [],
            "next_action": ""
        }

        for chunk in graph.stream(input1, config):
            if "responder" in chunk and "final_response" in chunk["responder"]:
                print(f"   Response: {chunk['responder']['final_response']}")
                break

        # Step 2: Add second item (should remember apples)
        print("\n2. Adding second item (bananas)...")
        input2 = {
            "messages": [HumanMessage(content="Add bananas to my list")],
            # NOT initializing grocery_list
            "final_response": "",
            "tool_calls": [],
            "next_action": ""
        }

        for chunk in graph.stream(input2, config):
            if "responder" in chunk and "final_response" in chunk["responder"]:
                print(f"   Response: {chunk['responder']['final_response']}")
                break

        # Step 3: View list - should have BOTH items
        print("\n3. Viewing list (should have both apples and bananas)...")
        input3 = {
            "messages": [HumanMessage(content="Show me my list")],
            # NOT initializing grocery_list
            "final_response": "",
            "tool_calls": [],
            "next_action": ""
        }

        list_response = ""
        for chunk in graph.stream(input3, config):
            if "responder" in chunk and "final_response" in chunk["responder"]:
                list_response = chunk["responder"]["final_response"]
                print(f"   List: {list_response}")
                break

        # Verify both items are in the list
        has_apples = "apples" in list_response.lower() or "apple" in list_response.lower()
        has_bananas = "bananas" in list_response.lower() or "banana" in list_response.lower()

        if has_apples and has_bananas:
            print("\n✅ State persistence works! Both items are in the list.")
            success = True
        else:
            print("\n❌ State persistence failed!")
            print(f"   Has apples: {has_apples}")
            print(f"   Has bananas: {has_bananas}")
            success = False

        pool.close()
        return success

    except Exception as e:
        print(f"❌ Error testing persistence: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_persistence_with_telegram_bot():
    """Test persistence through the telegram bot interface"""
    print("\nTesting persistence through telegram bot...")

    try:
        from telegram_bot import run_agent_sync

        # Test thread
        thread_id = "test_telegram_persist_999"

        # Add first item
        print("\n1. Adding milk via telegram bot...")
        response1 = run_agent_sync("Add milk to my list", thread_id)
        print(f"   Response: {response1}")

        # Add second item
        print("\n2. Adding bread via telegram bot...")
        response2 = run_agent_sync("Add bread to my list", thread_id)
        print(f"   Response: {response2}")

        # View list - should have both
        print("\n3. Viewing list via telegram bot...")
        response3 = run_agent_sync("What's on my grocery list?", thread_id)
        print(f"   List:\n{response3}")

        # Check both items are present
        has_milk = "milk" in response3.lower()
        has_bread = "bread" in response3.lower()

        if has_milk and has_bread:
            print("\n✅ Telegram bot persistence works correctly!")
            return True
        else:
            print("\n❌ Telegram bot persistence failed!")
            print(f"   Has milk: {has_milk}")
            print(f"   Has bread: {has_bread}")
            return False

    except Exception as e:
        print(f"❌ Error testing telegram persistence: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_persistence_across_restarts():
    """Test that state persists even across agent restarts"""
    print("\nTesting persistence across agent restarts...")

    try:
        from agent import build_graph
        from langchain_core.messages import HumanMessage

        thread_id = "test_restart_persist_555"
        config = {"configurable": {"thread_id": thread_id}}

        # First session - add items
        print("\n=== First Session ===")
        graph1, pool1 = build_graph()

        print("1. Adding cheese...")
        input1 = {
            "messages": [HumanMessage(content="Add cheese to my list")],
            "final_response": "",
            "tool_calls": [],
            "next_action": ""
        }

        for chunk in graph1.stream(input1, config):
            if "responder" in chunk and "final_response" in chunk["responder"]:
                print(f"   Response: {chunk['responder']['final_response']}")
                break

        # Close first session
        pool1.close()
        print("   Session closed.")

        # Simulate restart - create new graph instance
        time.sleep(1)
        print("\n=== New Session (simulated restart) ===")
        graph2, pool2 = build_graph()

        print("2. Viewing list in new session...")
        input2 = {
            "messages": [HumanMessage(content="Show me my list")],
            "final_response": "",
            "tool_calls": [],
            "next_action": ""
        }

        list_response = ""
        for chunk in graph2.stream(input2, config):
            if "responder" in chunk and "final_response" in chunk["responder"]:
                list_response = chunk["responder"]["final_response"]
                print(f"   List: {list_response}")
                break

        # Verify cheese is still there
        has_cheese = "cheese" in list_response.lower()

        pool2.close()

        if has_cheese:
            print("\n✅ State persists across restarts!")
            return True
        else:
            print("\n❌ State lost after restart!")
            return False

    except Exception as e:
        print(f"❌ Error testing restart persistence: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all persistence tests"""
    print("=" * 60)
    print("State Persistence Fix Verification")
    print("=" * 60)

    tests = [
        ("Basic State Persistence", test_state_persistence),
        ("Telegram Bot Persistence", test_persistence_with_telegram_bot),
        ("Persistence Across Restarts", test_persistence_across_restarts)
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
        print("\n🎉 All persistence tests passed!")
        print("• Items persist across multiple invocations")
        print("• State is maintained through telegram bot")
        print("• Data survives agent restarts")
    else:
        print("\n⚠️ Some persistence tests failed.")
        print("Check that:")
        print("• telegram_bot.py doesn't initialize grocery_list as empty")
        print("• tool_executor returns the updated_list")
        print("• PostgreSQL checkpointer is properly configured")

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
