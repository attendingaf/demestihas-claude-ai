#!/usr/bin/env python3
"""
Test script to verify state persistence fix
Run this after applying the patch to confirm grocery lists persist
"""

import os
import sys
from agent import build_graph
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_state_persistence():
    """Test that grocery list state persists across messages"""
    print("=" * 60)
    print("STATE PERSISTENCE TEST")
    print("=" * 60)
    
    # Build the graph
    print("\n1. Initializing agent...")
    app, pool = build_graph()
    
    # Use a test thread ID
    thread_id = "test_persistence_123"
    config = {"configurable": {"thread_id": thread_id}}
    
    print(f"   Thread ID: {thread_id}")
    print("   ✓ Agent initialized\n")
    
    # Test 1: Add first item
    print("2. Adding first item...")
    input1 = {
        "messages": [HumanMessage(content="Add milk to my list")],
        "final_response": "",
        "tool_calls": [],
        "next_action": ""
    }
    
    for chunk in app.stream(input1, config):
        if "responder" in chunk and "final_response" in chunk["responder"]:
            print(f"   Response: {chunk['responder']['final_response']}")
    print("   ✓ First item added\n")
    
    # Test 2: Add second item (should persist first)
    print("3. Adding second item (testing persistence)...")
    input2 = {
        "messages": [HumanMessage(content="Add eggs to my list")],
        "final_response": "",
        "tool_calls": [],
        "next_action": ""
    }
    
    for chunk in app.stream(input2, config):
        if "responder" in chunk and "final_response" in chunk["responder"]:
            print(f"   Response: {chunk['responder']['final_response']}")
    print("   ✓ Second item added\n")
    
    # Test 3: View list (should show both items)
    print("4. Viewing list (should show BOTH items)...")
    input3 = {
        "messages": [HumanMessage(content="What's on my list?")],
        "final_response": "",
        "tool_calls": [],
        "next_action": ""
    }
    
    list_response = ""
    for chunk in app.stream(input3, config):
        if "responder" in chunk and "final_response" in chunk["responder"]:
            list_response = chunk["responder"]["final_response"]
            print(f"   Response:\n{list_response}")
    
    # Verify both items are present
    print("\n5. Verification:")
    if "milk" in list_response.lower() and "eggs" in list_response.lower():
        print("   ✅ SUCCESS: Both items persisted!")
        print("   State persistence is working correctly.")
        return True
    else:
        print("   ❌ FAILURE: Items not persisted")
        print("   State persistence is still broken.")
        return False
    
    # Clean up
    pool.close()

if __name__ == "__main__":
    try:
        success = test_state_persistence()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
