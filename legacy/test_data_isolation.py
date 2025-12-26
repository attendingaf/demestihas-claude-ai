#!/usr/bin/env python3
"""
Test Data Isolation Between Users
Tests if DemestiChat properly isolates user data across storage systems.
"""

import requests
import json
import time
from typing import Dict, List

# Configuration
AGENT_URL = "http://agent:8000"
TEST_USERS = ["alice_test", "bob_test", "charlie_test"]


class IsolationTester:
    def __init__(self):
        self.tokens: Dict[str, str] = {}
        self.results = []

    def get_token(self, user_id: str) -> str:
        """Get JWT token for a user."""
        response = requests.post(f"{AGENT_URL}/auth/token", params={"user_id": user_id})
        if response.status_code == 200:
            return response.json()["access_token"]
        raise Exception(f"Failed to get token for {user_id}: {response.status_code}")

    def send_message(self, user_id: str, message: str) -> Dict:
        """Send a chat message as a specific user."""
        token = self.tokens.get(user_id)
        if not token:
            token = self.get_token(user_id)
            self.tokens[user_id] = token

        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "message": message,
            "user_id": user_id,
            "chat_id": f"test_{user_id}_{int(time.time())}",
        }

        response = requests.post(f"{AGENT_URL}/chat", json=payload, headers=headers)
        return response.json()

    def test_conversation_isolation(self):
        """Test if conversations are isolated per user."""
        print("\n" + "=" * 60)
        print("TEST 1: Conversation Isolation")
        print("=" * 60)

        # Alice adds personal information
        print("\n📝 Alice: Adding personal information...")
        alice_response = self.send_message(
            "alice_test",
            "My name is Alice and my favorite color is blue. Remember this.",
        )
        print(f"   Response: {alice_response.get('response', '')[:100]}...")

        time.sleep(2)

        # Bob adds different personal information
        print("\n📝 Bob: Adding personal information...")
        bob_response = self.send_message(
            "bob_test", "My name is Bob and my favorite color is red. Remember this."
        )
        print(f"   Response: {bob_response.get('response', '')[:100]}...")

        time.sleep(2)

        # Alice asks about her own information
        print("\n❓ Alice: Asking about own information...")
        alice_query = self.send_message("alice_test", "What is my favorite color?")
        alice_answer = alice_query.get("response", "")
        print(f"   Response: {alice_answer[:200]}...")

        # Check if Alice gets her own data
        if "blue" in alice_answer.lower() and "red" not in alice_answer.lower():
            print("   ✅ PASS: Alice received her own data")
            self.results.append(("Conversation Isolation - Alice", True))
        else:
            print("   ❌ FAIL: Alice did not receive correct data")
            self.results.append(("Conversation Isolation - Alice", False))

        time.sleep(2)

        # Bob asks about his own information
        print("\n❓ Bob: Asking about own information...")
        bob_query = self.send_message("bob_test", "What is my favorite color?")
        bob_answer = bob_query.get("response", "")
        print(f"   Response: {bob_answer[:200]}...")

        # Check if Bob gets his own data
        if "red" in bob_answer.lower() and "blue" not in bob_answer.lower():
            print("   ✅ PASS: Bob received his own data")
            self.results.append(("Conversation Isolation - Bob", True))
        else:
            print("   ❌ FAIL: Bob did not receive correct data")
            self.results.append(("Conversation Isolation - Bob", False))

        time.sleep(2)

        # Alice asks about Bob's information (should not know)
        print("\n❓ Alice: Trying to access Bob's information...")
        alice_cross_query = self.send_message(
            "alice_test", "What is Bob's favorite color?"
        )
        alice_cross_answer = alice_cross_query.get("response", "")
        print(f"   Response: {alice_cross_answer[:200]}...")

        # Check if Alice can't access Bob's data
        if "red" in alice_cross_answer.lower():
            print("   ❌ FAIL: Alice can access Bob's data (PRIVACY LEAK)")
            self.results.append(("Cross-User Privacy", False))
        else:
            print("   ✅ PASS: Alice cannot access Bob's data")
            self.results.append(("Cross-User Privacy", True))

    def test_knowledge_graph_isolation(self):
        """Test if knowledge graph isolates facts by user."""
        print("\n" + "=" * 60)
        print("TEST 2: Knowledge Graph Isolation")
        print("=" * 60)

        # Alice adds a fact about her mother
        print("\n📝 Alice: Adding fact about mother...")
        alice_fact = self.send_message(
            "alice_test", "My mother's name is Margaret and she lives in London."
        )
        print(f"   Response: {alice_fact.get('response', '')[:100]}...")

        time.sleep(2)

        # Bob adds a different fact about his mother
        print("\n📝 Bob: Adding fact about mother...")
        bob_fact = self.send_message(
            "bob_test", "My mother's name is Susan and she lives in Tokyo."
        )
        print(f"   Response: {bob_fact.get('response', '')[:100]}...")

        time.sleep(2)

        # Alice queries about her mother
        print("\n❓ Alice: Asking about her mother...")
        alice_mother_query = self.send_message(
            "alice_test", "Where does my mother live?"
        )
        alice_mother_answer = alice_mother_query.get("response", "")
        print(f"   Response: {alice_mother_answer[:200]}...")

        # Check if Alice gets correct mother information
        if (
            "london" in alice_mother_answer.lower()
            and "tokyo" not in alice_mother_answer.lower()
        ):
            print("   ✅ PASS: Alice knows her mother is in London")
            self.results.append(("Knowledge Graph - Alice's Mother", True))
        elif (
            "margaret" in alice_mother_answer.lower()
            or "london" in alice_mother_answer.lower()
        ):
            print("   ⚠️  PARTIAL: Alice got some correct info")
            self.results.append(("Knowledge Graph - Alice's Mother", True))
        else:
            print("   ❌ FAIL: Alice doesn't know her mother's location")
            self.results.append(("Knowledge Graph - Alice's Mother", False))

        time.sleep(2)

        # Bob queries about his mother
        print("\n❓ Bob: Asking about his mother...")
        bob_mother_query = self.send_message("bob_test", "What is my mother's name?")
        bob_mother_answer = bob_mother_query.get("response", "")
        print(f"   Response: {bob_mother_answer[:200]}...")

        # Check if Bob gets correct mother information
        if "susan" in bob_mother_answer.lower():
            print("   ✅ PASS: Bob knows his mother is Susan")
            self.results.append(("Knowledge Graph - Bob's Mother", True))
        else:
            print("   ❌ FAIL: Bob doesn't know his mother's name")
            self.results.append(("Knowledge Graph - Bob's Mother", False))

        # Critical test: Check for knowledge graph leakage
        if (
            "margaret" in bob_mother_answer.lower()
            or "london" in bob_mother_answer.lower()
        ):
            print(
                "   🚨 CRITICAL: Bob can see Alice's mother info (KNOWLEDGE GRAPH LEAK)"
            )
            self.results.append(("Knowledge Graph Isolation", False))
        elif (
            "susan" in alice_mother_answer.lower()
            or "tokyo" in alice_mother_answer.lower()
        ):
            print(
                "   🚨 CRITICAL: Alice can see Bob's mother info (KNOWLEDGE GRAPH LEAK)"
            )
            self.results.append(("Knowledge Graph Isolation", False))
        else:
            print("   ✅ PASS: No cross-user knowledge graph leakage detected")
            self.results.append(("Knowledge Graph Isolation", True))

    def test_temporal_queries(self):
        """Test if temporal queries respect user boundaries."""
        print("\n" + "=" * 60)
        print("TEST 3: Temporal Query Isolation")
        print("=" * 60)

        # Alice has a conversation
        print("\n📝 Alice: Having a conversation...")
        self.send_message("alice_test", "Today I went to the gym and ran 5 miles.")
        time.sleep(1)
        self.send_message("alice_test", "I also had a salad for lunch.")

        time.sleep(2)

        # Bob has a different conversation
        print("\n📝 Bob: Having a conversation...")
        self.send_message(
            "bob_test", "Today I worked from home and had three meetings."
        )
        time.sleep(1)
        self.send_message("bob_test", "I ordered pizza for dinner.")

        time.sleep(2)

        # Alice queries about today
        print("\n❓ Alice: Asking about today...")
        alice_today = self.send_message("alice_test", "What did I do today?")
        alice_today_answer = alice_today.get("response", "")
        print(f"   Response: {alice_today_answer[:200]}...")

        # Check if Alice sees only her activities
        has_gym = (
            "gym" in alice_today_answer.lower()
            or "ran" in alice_today_answer.lower()
            or "miles" in alice_today_answer.lower()
        )
        has_meetings = (
            "meeting" in alice_today_answer.lower()
            or "pizza" in alice_today_answer.lower()
        )

        if has_gym and not has_meetings:
            print("   ✅ PASS: Alice sees only her own activities")
            self.results.append(("Temporal Isolation - Alice", True))
        elif has_gym:
            print("   ⚠️  PARTIAL: Alice sees her activities but also others")
            self.results.append(("Temporal Isolation - Alice", False))
        else:
            print("   ❌ FAIL: Alice doesn't see her own activities")
            self.results.append(("Temporal Isolation - Alice", False))

        time.sleep(2)

        # Bob queries about today
        print("\n❓ Bob: Asking about today...")
        bob_today = self.send_message("bob_test", "What did I do today?")
        bob_today_answer = bob_today.get("response", "")
        print(f"   Response: {bob_today_answer[:200]}...")

        # Check if Bob sees only his activities
        has_work = (
            "work" in bob_today_answer.lower()
            or "meeting" in bob_today_answer.lower()
            or "pizza" in bob_today_answer.lower()
        )
        has_gym_bob = (
            "gym" in bob_today_answer.lower() or "salad" in bob_today_answer.lower()
        )

        if has_work and not has_gym_bob:
            print("   ✅ PASS: Bob sees only his own activities")
            self.results.append(("Temporal Isolation - Bob", True))
        elif has_work:
            print("   ⚠️  PARTIAL: Bob sees his activities but also others")
            self.results.append(("Temporal Isolation - Bob", False))
        else:
            print("   ❌ FAIL: Bob doesn't see his own activities")
            self.results.append(("Temporal Isolation - Bob", False))

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)

        passed = sum(1 for _, result in self.results if result)
        failed = sum(1 for _, result in self.results if not result)
        total = len(self.results)

        print(f"\nTotal Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {(passed / total) * 100:.1f}%")

        print("\nDetailed Results:")
        for test_name, result in self.results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {status}: {test_name}")

        # Critical findings
        print("\n" + "=" * 60)
        print("CRITICAL FINDINGS")
        print("=" * 60)

        kg_isolation = next(
            (r for t, r in self.results if "Knowledge Graph Isolation" in t), None
        )
        if kg_isolation is False:
            print("🚨 CRITICAL: Knowledge Graph shares data across users!")
            print("   Recommendation: Add user_id property to all FalkorDB entities")
        elif kg_isolation is True:
            print("✅ Knowledge Graph properly isolates user data")

        cross_privacy = next(
            (r for t, r in self.results if "Cross-User Privacy" in t), None
        )
        if cross_privacy is False:
            print("🚨 CRITICAL: Users can access each other's private data!")
            print("   Recommendation: Fix conversation memory isolation")
        elif cross_privacy is True:
            print("✅ Users cannot access each other's conversations")

        print("\n" + "=" * 60)


def main():
    """Run all data isolation tests."""
    print("=" * 60)
    print("DemestiChat Data Isolation Test Suite")
    print("=" * 60)
    print(f"Agent URL: {AGENT_URL}")
    print(f"Test Users: {', '.join(TEST_USERS)}")
    print("\nThis will test if user data is properly isolated across:")
    print("  - Conversation memory (Mem0)")
    print("  - Knowledge graph (FalkorDB)")
    print("  - Temporal queries (PostgreSQL)")
    print("\n⏳ Starting tests in 2 seconds...")
    time.sleep(2)

    tester = IsolationTester()

    try:
        tester.test_conversation_isolation()
        time.sleep(3)

        tester.test_knowledge_graph_isolation()
        time.sleep(3)

        tester.test_temporal_queries()

    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        tester.print_summary()


if __name__ == "__main__":
    main()
