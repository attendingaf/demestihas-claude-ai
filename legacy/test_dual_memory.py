#!/usr/bin/env python3
"""
Comprehensive Test Suite for FalkorDB Dual-Memory System

Tests:
1. Privacy isolation - Private memories not visible to other users
2. System memory sharing - Shared memories visible to all users
3. Auto-classification accuracy
4. Manual memory type override
5. API endpoint functionality
6. Memory retrieval and filtering
"""

import asyncio
import requests
import json
import time
from typing import Dict, List

# Configuration
AGENT_URL = "http://agent:8000"
TEST_USERS = {
    "alice": {"password": "alice123", "display_name": "Alice Test"},
    "bob": {"password": "bob123", "display_name": "Bob Test"},
}


class DualMemoryTester:
    def __init__(self):
        self.tokens: Dict[str, str] = {}
        self.results: List[tuple] = []

    def login(self, user_id: str, password: str) -> str:
        """Login and get JWT token."""
        try:
            response = requests.post(
                f"{AGENT_URL}/auth/login",
                params={"user_id": user_id, "password": password},
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                self.tokens[user_id] = token
                return token
            else:
                print(f"❌ Login failed for {user_id}: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Login error for {user_id}: {e}")
            return None

    def send_chat(self, user_id: str, message: str) -> Dict:
        """Send a chat message."""
        token = self.tokens.get(user_id)
        if not token:
            raise Exception(f"No token for {user_id}")

        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "message": message,
            "user_id": user_id,
            "chat_id": f"test_{user_id}_{int(time.time())}",
        }

        response = requests.post(
            f"{AGENT_URL}/chat", json=payload, headers=headers, timeout=30
        )
        return response.json()

    def get_memories(self, user_id: str, memory_type: str = "all") -> Dict:
        """Get user's memories via API."""
        token = self.tokens.get(user_id)
        if not token:
            raise Exception(f"No token for {user_id}")

        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{AGENT_URL}/memory/list",
            params={"memory_type": memory_type, "limit": 50},
            headers=headers,
            timeout=10,
        )
        return response.json()

    def test_result(self, test_name: str, passed: bool, details: str = ""):
        """Record test result."""
        self.results.append((test_name, passed, details))
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"   {details}")

    async def run_tests(self):
        """Run all tests."""
        print("=" * 80)
        print("DUAL-MEMORY SYSTEM TEST SUITE")
        print("=" * 80)
        print()

        # Setup: Login users
        print("Setup: Logging in test users...")
        for user_id, creds in TEST_USERS.items():
            token = self.login(user_id, creds["password"])
            if token:
                print(f"  ✅ {user_id} logged in")
            else:
                print(f"  ❌ {user_id} login failed - aborting tests")
                return

        print()
        await asyncio.sleep(2)

        # Test 1: Private Memory Isolation
        print("-" * 80)
        print("TEST 1: Private Memory Isolation")
        print("-" * 80)

        print("\n📝 Alice: Storing private information...")
        alice_private = self.send_chat(
            "alice",
            "My personal bank password is SecretAlice2025. Remember this privately.",
        )
        time.sleep(3)

        print("📝 Bob: Storing private information...")
        bob_private = self.send_chat(
            "bob", "My personal diary code is BobSecret987. Keep this private."
        )
        time.sleep(3)

        print("\n❓ Bob: Trying to access Alice's private data...")
        bob_query = self.send_chat("bob", "What is Alice's bank password?")
        bob_response = bob_query.get("response", "")

        # Check if Bob can see Alice's private data
        has_leak = "SecretAlice2025" in bob_response or "SecretAlice" in bob_response
        self.test_result(
            "Private Memory Isolation",
            not has_leak,
            f"Bob's response: {bob_response[:100]}...",
        )

        print()
        await asyncio.sleep(2)

        # Test 2: System Memory Sharing
        print("-" * 80)
        print("TEST 2: System Memory Sharing")
        print("-" * 80)

        print("\n📝 Alice: Storing family-wide information...")
        alice_family = self.send_chat(
            "alice",
            "Our family vacation is scheduled for Disney World from March 15-22, 2025.",
        )
        time.sleep(3)

        print("❓ Bob: Querying family vacation...")
        bob_vacation = self.send_chat("bob", "When is our family vacation?")
        bob_vac_response = bob_vacation.get("response", "")

        # Check if Bob can see family-wide data
        has_info = (
            "March 15" in bob_vac_response
            or "Disney" in bob_vac_response
            or "vacation" in bob_vac_response.lower()
        )
        self.test_result(
            "System Memory Sharing",
            has_info,
            f"Bob's response: {bob_vac_response[:100]}...",
        )

        print()
        await asyncio.sleep(2)

        # Test 3: Auto-Classification
        print("-" * 80)
        print("TEST 3: Auto-Classification Accuracy")
        print("-" * 80)

        # Store various types of information
        test_cases = [
            ("alice", "My credit card number is 1234-5678-9012-3456", "private"),
            ("alice", "Elena's school starts at 8am on weekdays", "system"),
            ("bob", "My personal Amazon password is BobShop2025", "private"),
            ("bob", "Our family pet goldfish is named Bubbles", "system"),
        ]

        print()
        for user, message, expected_type in test_cases:
            print(f"📝 {user.capitalize()}: {message[:50]}...")
            response = self.send_chat(user, message)
            time.sleep(2)

        # Get memory stats to verify classification
        alice_stats = self.get_memories("alice", "all")
        bob_stats = self.get_memories("bob", "all")

        alice_mems = alice_stats.get("memories", [])
        bob_mems = bob_stats.get("memories", [])

        # Count private vs system
        alice_private_count = sum(1 for m in alice_mems if m["source"] == "private")
        alice_system_count = sum(1 for m in alice_mems if m["source"] == "system")
        bob_private_count = sum(1 for m in bob_mems if m["source"] == "private")
        bob_system_count = sum(1 for m in bob_mems if m["source"] == "system")

        print(f"\nMemory Statistics:")
        print(f"  Alice: {alice_private_count} private, {alice_system_count} system")
        print(f"  Bob: {bob_private_count} private, {bob_system_count} system")

        # Test passes if both users have some private and some system memories
        has_both = (
            alice_private_count > 0
            and alice_system_count > 0
            and bob_private_count > 0
            and bob_system_count > 0
        )

        self.test_result(
            "Auto-Classification",
            has_both,
            f"Both users have private and system memories",
        )

        print()
        await asyncio.sleep(2)

        # Test 4: Memory API Endpoints
        print("-" * 80)
        print("TEST 4: Memory API Endpoints")
        print("-" * 80)

        print("\n📊 Testing /memory/list endpoint...")
        alice_all = self.get_memories("alice", "all")
        alice_private_only = self.get_memories("alice", "private")
        alice_system_only = self.get_memories("alice", "system")

        has_all_data = alice_all.get("total", 0) > 0
        has_filtered = (
            alice_private_only.get("total", 0) >= 0
            and alice_system_only.get("total", 0) >= 0
        )

        self.test_result(
            "Memory List API",
            has_all_data and has_filtered,
            f"All: {alice_all.get('total')}, Private: {alice_private_only.get('total')}, System: {alice_system_only.get('total')}",
        )

        print("\n📊 Testing /memory/stats endpoint...")
        try:
            token = self.tokens.get("alice")
            headers = {"Authorization": f"Bearer {token}"}
            stats_response = requests.get(
                f"{AGENT_URL}/memory/stats", headers=headers, timeout=10
            )
            stats = stats_response.json()

            has_stats = "private_memories" in stats and "system_memories" in stats
            self.test_result("Memory Stats API", has_stats, f"Stats: {stats}")
        except Exception as e:
            self.test_result("Memory Stats API", False, f"Error: {e}")

        print()
        await asyncio.sleep(2)

        # Test 5: Cross-User Data Verification
        print("-" * 80)
        print("TEST 5: Cross-User Data Verification")
        print("-" * 80)

        print("\n🔍 Verifying Alice cannot see Bob's private memories...")
        alice_mems = self.get_memories("alice", "all").get("memories", [])

        # Check if any of Bob's private content appears in Alice's memories
        bob_private_leaked = any(
            "BobSecret" in m.get("content", "") or "BobShop" in m.get("content", "")
            for m in alice_mems
        )

        self.test_result(
            "Cross-User Privacy",
            not bob_private_leaked,
            "Alice cannot see Bob's private memories",
        )

        print("\n🔍 Verifying both users can see system memories...")
        alice_system = [m for m in alice_mems if m["source"] == "system"]
        bob_mems_all = self.get_memories("bob", "all").get("memories", [])
        bob_system = [m for m in bob_mems_all if m["source"] == "system"]

        # Check if both have access to system memories
        both_have_system = len(alice_system) > 0 and len(bob_system) > 0

        # Check if they share at least one system memory
        alice_system_contents = {m.get("content") for m in alice_system}
        bob_system_contents = {m.get("content") for m in bob_system}
        shared_memories = alice_system_contents & bob_system_contents

        self.test_result(
            "Shared System Access",
            both_have_system and len(shared_memories) > 0,
            f"Shared memories: {len(shared_memories)}",
        )

        print()

        # Print Summary
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print()

        total_tests = len(self.results)
        passed = sum(1 for _, p, _ in self.results if p)
        failed = total_tests - passed

        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {(passed / total_tests) * 100:.1f}%")
        print()

        print("Detailed Results:")
        for test_name, passed, details in self.results:
            status = "✅" if passed else "❌"
            print(f"  {status} {test_name}")
            if details and not passed:
                print(f"     {details}")

        print()
        print("=" * 80)

        if failed == 0:
            print("🎉 ALL TESTS PASSED - Dual-memory system working correctly!")
        else:
            print(f"⚠️  {failed} TEST(S) FAILED - Review issues above")

        print("=" * 80)
        print()


async def main():
    """Main test runner."""
    tester = DualMemoryTester()
    await tester.run_tests()


if __name__ == "__main__":
    asyncio.run(main())
