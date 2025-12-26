"""
Phase 3: Comprehensive Verification Test Suite for FalkorDB Read-Path

This test suite validates the correctness of the new FalkorDB-based
knowledge retrieval functions against a known test dataset.

Test Categories:
1. Connection and Configuration Tests
2. User Critique Retrieval Tests
3. User Constraint Retrieval Tests
4. Knowledge Triple Retrieval Tests
5. Entity Search Tests
6. Shadow Mode Validation Tests
7. Integration Tests with Agent Workflow

Setup:
- Uses initialize_db.py to populate test data
- Runs against dedicated test FalkorDB instance
- Validates data structures, query correctness, and edge cases

Usage:
    python test_falkordb_reads.py
    pytest test_falkordb_reads.py -v
"""

import os
import sys
import asyncio
import pytest
from typing import List, Dict, Any
from datetime import datetime

# Add parent directory to path to import agent modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from falkordb_manager import FalkorDBManager

# ============================================================================
# TEST CONFIGURATION
# ============================================================================

# Override environment variables for test instance
TEST_FALKORDB_HOST = os.getenv("TEST_FALKORDB_HOST", "graph_db")
TEST_FALKORDB_PORT = int(os.getenv("TEST_FALKORDB_PORT", "6379"))
TEST_GRAPH_NAME = "test_demestihas_knowledge"

# Test data constants
TEST_USER_ID = "test_user_EA"
TEST_USER_ID_2 = "test_user_guest"


# ============================================================================
# PYTEST FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
async def falkordb_manager():
    """
    Session-scoped FalkorDB manager for tests.

    Yields:
        FalkorDBManager instance connected to test database
    """
    # Override environment for test instance
    os.environ["FALKORDB_HOST"] = TEST_FALKORDB_HOST
    os.environ["FALKORDB_PORT"] = str(TEST_FALKORDB_PORT)
    os.environ["FALKORDB_GRAPH_NAME"] = TEST_GRAPH_NAME

    manager = FalkorDBManager()
    await manager.connect()

    yield manager

    await manager.disconnect()


@pytest.fixture(scope="session")
async def populated_test_db(falkordb_manager):
    """
    Populate test database with known dataset.

    This fixture runs once per test session to set up the test data.

    Test Data Schema:
    - User nodes: test_user_EA, test_user_guest
    - Critique nodes: 3 critiques for test_user_EA (tone, formatting, routing)
    - Constraint nodes: 2 constraints for test_user_EA (active and inactive)
    - Entity nodes: Python, Database, FalkorDB, Backend, API
    - Knowledge relationships: Multiple triples linking entities

    Args:
        falkordb_manager: FalkorDB manager instance

    Yields:
        Dict with counts of created test data
    """
    print("\n🏗️  POPULATING TEST DATABASE...")

    timestamp = datetime.utcnow().isoformat()

    # Clear existing test data
    await falkordb_manager.execute_query("MATCH (n) DETACH DELETE n")
    print("✅ Cleared existing test data")

    # Create test users
    await falkordb_manager.merge_node(
        "User",
        {"id": TEST_USER_ID, "name": "Test EA User", "created_at": timestamp},
        match_properties=["id"],
    )

    await falkordb_manager.merge_node(
        "User",
        {"id": TEST_USER_ID_2, "name": "Test Guest User", "created_at": timestamp},
        match_properties=["id"],
    )
    print(f"✅ Created 2 test users")

    # Create RLHF critiques for test_user_EA
    critiques_data = [
        {
            "id": "critique_1",
            "text": "Response was too formal and lacked conversational tone",
            "category": "tone",
            "timestamp": "2025-10-01T10:00:00Z",
            "confidence": 0.85,
        },
        {
            "id": "critique_2",
            "text": "Code formatting was inconsistent with Python PEP8 standards",
            "category": "formatting",
            "timestamp": "2025-10-01T11:30:00Z",
            "confidence": 0.92,
        },
        {
            "id": "critique_3",
            "text": "Wrong agent selected - should have routed to code agent instead of research",
            "category": "routing",
            "timestamp": "2025-10-01T14:15:00Z",
            "confidence": 0.78,
        },
    ]

    for critique in critiques_data:
        await falkordb_manager.merge_node("Critique", critique, match_properties=["id"])

        # Link critique to user
        await falkordb_manager.merge_relationship(
            "User",
            {"id": TEST_USER_ID},
            "RECEIVED_CRITIQUE",
            "Critique",
            {"id": critique["id"]},
            {"timestamp": critique["timestamp"]},
        )

    print(f"✅ Created {len(critiques_data)} test critiques")

    # Create constraints for test_user_EA
    constraints_data = [
        {
            "id": "constraint_1",
            "text": "Always use concise responses, maximum 3 paragraphs",
            "type": "formatting",
            "profile": TEST_USER_ID,
            "active": True,
            "created_at": timestamp,
        },
        {
            "id": "constraint_2",
            "text": "Never use emojis in technical responses",
            "type": "tone",
            "profile": TEST_USER_ID,
            "active": True,
            "created_at": timestamp,
        },
        {
            "id": "constraint_3",
            "text": "Deprecated constraint - no longer applies",
            "type": "general",
            "profile": TEST_USER_ID,
            "active": False,
            "created_at": "2025-09-01T00:00:00Z",
        },
    ]

    for constraint in constraints_data:
        await falkordb_manager.merge_node(
            "Constraint", constraint, match_properties=["id"]
        )

    print(f"✅ Created {len(constraints_data)} test constraints")

    # Create entity nodes and knowledge triples
    entities_data = [
        {"name": "Python", "type": "programming_language"},
        {"name": "Database Integration", "type": "project"},
        {"name": "FalkorDB", "type": "technology"},
        {"name": "Backend Development", "type": "domain"},
        {"name": "REST API", "type": "concept"},
    ]

    for entity in entities_data:
        await falkordb_manager.merge_node(
            "Entity",
            {**entity, "created_by": TEST_USER_ID, "created_at": timestamp},
            match_properties=["name"],
        )

    print(f"✅ Created {len(entities_data)} test entities")

    # Create knowledge relationships
    relationships_data = [
        ("Python", "USED_FOR", "Backend Development", 0.95),
        ("Database Integration", "USES_TECHNOLOGY", "FalkorDB", 0.90),
        ("FalkorDB", "IS_TYPE_OF", "Database", 1.0),
        ("Backend Development", "IMPLEMENTS", "REST API", 0.88),
        ("Python", "SUITABLE_FOR", "Database Integration", 0.85),
    ]

    for subject, predicate, obj, confidence in relationships_data:
        await falkordb_manager.merge_relationship(
            "Entity",
            {"name": subject},
            predicate,
            "Entity",
            {"name": obj},
            {"confidence": confidence, "timestamp": timestamp, "user_id": TEST_USER_ID},
        )

        # Link user to entities
        await falkordb_manager.merge_relationship(
            "User", {"id": TEST_USER_ID}, "KNOWS_ABOUT", "Entity", {"name": subject}
        )

        await falkordb_manager.merge_relationship(
            "User", {"id": TEST_USER_ID}, "KNOWS_ABOUT", "Entity", {"name": obj}
        )

    print(f"✅ Created {len(relationships_data)} test relationships")

    # Verify counts
    result = await falkordb_manager.execute_query(
        """
        MATCH (u:User)
        OPTIONAL MATCH (c:Critique)
        OPTIONAL MATCH (con:Constraint)
        OPTIONAL MATCH (e:Entity)
        RETURN count(DISTINCT u) AS users,
               count(DISTINCT c) AS critiques,
               count(DISTINCT con) AS constraints,
               count(DISTINCT e) AS entities
        """,
        readonly=True,
    )

    counts = {
        "users": result[0][0] if result else 0,
        "critiques": result[0][1] if result else 0,
        "constraints": result[0][2] if result else 0,
        "entities": result[0][3] if result else 0,
    }

    print(f"\n📊 TEST DATABASE POPULATED:")
    print(f"   Users: {counts['users']}")
    print(f"   Critiques: {counts['critiques']}")
    print(f"   Constraints: {counts['constraints']}")
    print(f"   Entities: {counts['entities']}")
    print()

    yield counts


# ============================================================================
# TEST SUITE 1: CONNECTION AND CONFIGURATION
# ============================================================================


@pytest.mark.asyncio
async def test_connection_establishment():
    """Test that FalkorDB manager can establish connection."""
    manager = FalkorDBManager()
    await manager.connect()

    assert manager.is_connected(), "Manager should report connected status"
    assert manager.graph is not None, "Graph instance should be initialized"

    await manager.disconnect()


@pytest.mark.asyncio
async def test_connection_info():
    """Test that connection info is correctly reported."""
    manager = FalkorDBManager()
    await manager.connect()

    info = manager.get_connection_info()

    assert info["host"] == TEST_FALKORDB_HOST
    assert info["port"] == TEST_FALKORDB_PORT
    assert info["graph_name"] == TEST_GRAPH_NAME
    assert info["connected"] is True

    await manager.disconnect()


# ============================================================================
# TEST SUITE 2: USER CRITIQUE RETRIEVAL
# ============================================================================


@pytest.mark.asyncio
async def test_get_user_critiques_basic(falkordb_manager, populated_test_db):
    """Test basic critique retrieval for a user."""
    critiques = await falkordb_manager.get_user_critiques(user_id=TEST_USER_ID, limit=5)

    assert len(critiques) == 3, "Should retrieve all 3 critiques"

    # Verify structure
    for critique in critiques:
        assert "text" in critique
        assert "category" in critique
        assert "timestamp" in critique
        assert "confidence" in critique


@pytest.mark.asyncio
async def test_get_user_critiques_category_filter(falkordb_manager, populated_test_db):
    """Test critique retrieval with category filter."""
    tone_critiques = await falkordb_manager.get_user_critiques(
        user_id=TEST_USER_ID, limit=5, category="tone"
    )

    assert len(tone_critiques) == 1, "Should retrieve only tone critique"
    assert tone_critiques[0]["category"] == "tone"


@pytest.mark.asyncio
async def test_get_user_critiques_limit(falkordb_manager, populated_test_db):
    """Test critique retrieval respects limit parameter."""
    critiques = await falkordb_manager.get_user_critiques(user_id=TEST_USER_ID, limit=2)

    assert len(critiques) == 2, "Should respect limit of 2"


@pytest.mark.asyncio
async def test_get_user_critiques_ordering(falkordb_manager, populated_test_db):
    """Test that critiques are returned in reverse chronological order."""
    critiques = await falkordb_manager.get_user_critiques(user_id=TEST_USER_ID, limit=5)

    # Verify timestamps are descending
    timestamps = [c["timestamp"] for c in critiques]
    assert timestamps == sorted(timestamps, reverse=True), (
        "Critiques should be ordered by timestamp DESC"
    )


@pytest.mark.asyncio
async def test_get_user_critiques_empty(falkordb_manager, populated_test_db):
    """Test critique retrieval for user with no critiques."""
    critiques = await falkordb_manager.get_user_critiques(
        user_id=TEST_USER_ID_2, limit=5
    )

    assert len(critiques) == 0, "Guest user should have no critiques"


# ============================================================================
# TEST SUITE 3: USER CONSTRAINT RETRIEVAL
# ============================================================================


@pytest.mark.asyncio
async def test_get_user_constraints_active_only(falkordb_manager, populated_test_db):
    """Test constraint retrieval with active_only filter."""
    constraints = await falkordb_manager.get_user_constraints(
        user_id=TEST_USER_ID, active_only=True
    )

    assert len(constraints) == 2, "Should retrieve only 2 active constraints"

    # Verify all returned constraints are active
    for constraint in constraints:
        assert constraint["active"] is True


@pytest.mark.asyncio
async def test_get_user_constraints_all(falkordb_manager, populated_test_db):
    """Test constraint retrieval without active filter."""
    constraints = await falkordb_manager.get_user_constraints(
        user_id=TEST_USER_ID, active_only=False
    )

    assert len(constraints) == 3, (
        "Should retrieve all 3 constraints (including inactive)"
    )


@pytest.mark.asyncio
async def test_get_user_constraints_structure(falkordb_manager, populated_test_db):
    """Test that constraint data structure is correct."""
    constraints = await falkordb_manager.get_user_constraints(
        user_id=TEST_USER_ID, active_only=True
    )

    # Verify structure
    for constraint in constraints:
        assert "text" in constraint
        assert "type" in constraint
        assert "profile" in constraint
        assert "active" in constraint
        assert constraint["profile"] == TEST_USER_ID


# ============================================================================
# TEST SUITE 4: KNOWLEDGE TRIPLE RETRIEVAL
# ============================================================================


@pytest.mark.asyncio
async def test_get_user_knowledge_triples(falkordb_manager, populated_test_db):
    """Test knowledge triple retrieval for a user."""
    triples = await falkordb_manager.get_user_knowledge_triples(
        user_id=TEST_USER_ID, limit=10
    )

    assert len(triples) > 0, "Should retrieve knowledge triples"

    # Verify structure
    for triple in triples:
        assert "subject" in triple
        assert "predicate" in triple
        assert "object" in triple
        assert "confidence" in triple


@pytest.mark.asyncio
async def test_get_user_knowledge_triples_limit(falkordb_manager, populated_test_db):
    """Test that triple retrieval respects limit."""
    triples = await falkordb_manager.get_user_knowledge_triples(
        user_id=TEST_USER_ID, limit=3
    )

    assert len(triples) <= 3, "Should respect limit of 3"


# ============================================================================
# TEST SUITE 5: ENTITY SEARCH
# ============================================================================


@pytest.mark.asyncio
async def test_search_entities_by_keyword(falkordb_manager, populated_test_db):
    """Test entity search by keyword."""
    entities = await falkordb_manager.search_entities_by_keyword(
        keyword="python", limit=5
    )

    assert len(entities) >= 1, "Should find Python entity"

    # Verify Python entity is in results
    entity_names = [e["name"] for e in entities]
    assert "Python" in entity_names


@pytest.mark.asyncio
async def test_search_entities_case_insensitive(falkordb_manager, populated_test_db):
    """Test that entity search is case-insensitive."""
    entities_lower = await falkordb_manager.search_entities_by_keyword(
        keyword="database", limit=5
    )

    entities_upper = await falkordb_manager.search_entities_by_keyword(
        keyword="DATABASE", limit=5
    )

    assert len(entities_lower) == len(entities_upper), (
        "Search should be case-insensitive"
    )


@pytest.mark.asyncio
async def test_search_entities_no_results(falkordb_manager, populated_test_db):
    """Test entity search with no matching results."""
    entities = await falkordb_manager.search_entities_by_keyword(
        keyword="nonexistent_entity_xyz", limit=5
    )

    assert len(entities) == 0, "Should return empty list for no matches"


# ============================================================================
# TEST SUITE 6: INTEGRATION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_reflection_context_retrieval(falkordb_manager, populated_test_db):
    """
    Integration test: Simulate reflection_node context retrieval.

    This test validates the complete workflow for retrieving
    critiques and constraints used by the reflection_node.
    """
    # Retrieve both critiques and constraints (as reflection_node does)
    critiques = await falkordb_manager.get_user_critiques(
        user_id=TEST_USER_ID, limit=5, category=None
    )

    constraints = await falkordb_manager.get_user_constraints(
        user_id=TEST_USER_ID, active_only=True
    )

    # Verify both retrieval operations succeeded
    assert len(critiques) > 0, "Reflection should have critique context"
    assert len(constraints) > 0, "Reflection should have constraint context"

    # Verify critique categories are diverse
    categories = set(c["category"] for c in critiques)
    assert len(categories) >= 2, "Should have multiple critique categories"


@pytest.mark.asyncio
async def test_orchestrator_context_retrieval(falkordb_manager, populated_test_db):
    """
    Integration test: Simulate orchestrator context retrieval.

    This test validates the workflow for retrieving knowledge
    triples and entity searches used by the orchestrator.
    """
    # Simulate orchestrator query: "How do I use Python for database integration?"
    query_keyword = "database"

    # Retrieve user's knowledge base
    triples = await falkordb_manager.get_user_knowledge_triples(
        user_id=TEST_USER_ID, limit=10
    )

    # Search for query-relevant entities
    entities = await falkordb_manager.search_entities_by_keyword(
        keyword=query_keyword, limit=5
    )

    assert len(triples) > 0, "Should have knowledge context"
    assert len(entities) > 0, "Should find relevant entities"


# ============================================================================
# TEST SUITE 7: ERROR HANDLING AND EDGE CASES
# ============================================================================


@pytest.mark.asyncio
async def test_query_with_nonexistent_user(falkordb_manager, populated_test_db):
    """Test that queries gracefully handle non-existent users."""
    critiques = await falkordb_manager.get_user_critiques(
        user_id="nonexistent_user_12345", limit=5
    )

    assert len(critiques) == 0, "Should return empty list for non-existent user"


@pytest.mark.asyncio
async def test_concurrent_read_operations(falkordb_manager, populated_test_db):
    """Test that multiple read operations can execute concurrently."""
    # Execute multiple read operations in parallel
    results = await asyncio.gather(
        falkordb_manager.get_user_critiques(TEST_USER_ID, 5),
        falkordb_manager.get_user_constraints(TEST_USER_ID, True),
        falkordb_manager.get_user_knowledge_triples(TEST_USER_ID, 10),
        falkordb_manager.search_entities_by_keyword("python", 5),
    )

    critiques, constraints, triples, entities = results

    # Verify all operations completed successfully
    assert len(critiques) > 0
    assert len(constraints) > 0
    assert len(triples) > 0
    assert len(entities) > 0


# ============================================================================
# MAIN EXECUTION
# ============================================================================


if __name__ == "__main__":
    """
    Run tests directly with asyncio (alternative to pytest).

    Usage:
        python test_falkordb_reads.py
    """
    import sys

    async def run_all_tests():
        """Execute all tests sequentially."""
        print("\n" + "=" * 80)
        print("FALKORDB READ-PATH VERIFICATION TEST SUITE")
        print("Phase 3: Shadow Mode Integration & Validation")
        print("=" * 80 + "\n")

        # Initialize manager and populate test DB
        os.environ["FALKORDB_HOST"] = TEST_FALKORDB_HOST
        os.environ["FALKORDB_PORT"] = str(TEST_FALKORDB_PORT)
        os.environ["FALKORDB_GRAPH_NAME"] = TEST_GRAPH_NAME

        manager = FalkorDBManager()
        await manager.connect()

        # Populate test database (inline for direct execution)
        print("🏗️  Populating test database...")
        await manager.execute_query("MATCH (n) DETACH DELETE n")

        timestamp = datetime.utcnow().isoformat()

        # Create test users
        await manager.merge_node(
            "User",
            {"id": TEST_USER_ID, "name": "Test EA User", "created_at": timestamp},
            match_properties=["id"],
        )

        # Create test critiques
        critiques_data = [
            {
                "id": "critique_1",
                "text": "Response was too formal",
                "category": "tone",
                "timestamp": "2025-10-01T10:00:00Z",
                "confidence": 0.85,
            },
            {
                "id": "critique_2",
                "text": "Code formatting inconsistent",
                "category": "formatting",
                "timestamp": "2025-10-01T11:30:00Z",
                "confidence": 0.92,
            },
        ]

        for critique in critiques_data:
            await manager.merge_node("Critique", critique, match_properties=["id"])
            await manager.merge_relationship(
                "User",
                {"id": TEST_USER_ID},
                "RECEIVED_CRITIQUE",
                "Critique",
                {"id": critique["id"]},
                {"timestamp": critique["timestamp"]},
            )

        print("✅ Test database populated\n")

        # Run tests
        tests_passed = 0
        tests_failed = 0

        try:
            print("TEST: Connection establishment")
            assert manager.is_connected()
            print("✅ PASSED\n")
            tests_passed += 1
        except AssertionError as e:
            print(f"❌ FAILED: {e}\n")
            tests_failed += 1

        try:
            print("TEST: Retrieve user critiques")
            critiques = await manager.get_user_critiques(TEST_USER_ID, limit=5)
            assert len(critiques) == 2
            print(f"✅ PASSED - Retrieved {len(critiques)} critiques\n")
            tests_passed += 1
        except AssertionError as e:
            print(f"❌ FAILED: {e}\n")
            tests_failed += 1

        await manager.disconnect()

        print("=" * 80)
        print(f"TEST RESULTS: {tests_passed} passed, {tests_failed} failed")
        print("=" * 80 + "\n")

        return tests_failed == 0

    # Run tests
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
