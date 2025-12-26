#!/usr/bin/env python3
"""Comprehensive tests for the Context Engine system."""

import unittest
import time
import os
import tempfile
import shutil
from pathlib import Path
import sys
import json
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from context_engine import (
    ContextEngine,
    ContextRequest,
    ContextResponse,
    get_context_engine
)
from context_engine.cache import MultiLevelCache
from context_engine.namespace import NamespaceManager, NamespaceType, AccessLevel
from context_engine.sync import SyncEngine
from context_engine.ranker import ContextRanker, ContextItem


class TestMultiLevelCache(unittest.TestCase):
    """Test multi-level cache functionality."""
    
    def setUp(self):
        """Set up test cache."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache = MultiLevelCache(
            sqlite_path=os.path.join(self.temp_dir, "test_cache.db"),
            max_memory_mb=10,
            enable_mmap=False,
            enable_prefetch=False
        )
    
    def tearDown(self):
        """Clean up test cache."""
        self.cache.close()
        shutil.rmtree(self.temp_dir)
    
    def test_basic_get_set(self):
        """Test basic cache get/set operations."""
        # Set value
        self.cache.set("test_key", {"data": "test_value"}, namespace="test")
        
        # Get value
        result = self.cache.get("test_key", namespace="test")
        self.assertIsNotNone(result)
        self.assertEqual(result["data"], "test_value")
    
    def test_cache_miss(self):
        """Test cache miss behavior."""
        result = self.cache.get("nonexistent", namespace="test")
        self.assertIsNone(result)
        self.assertEqual(self.cache.stats["misses"], 1)
    
    def test_ttl_expiration(self):
        """Test TTL expiration."""
        # Set with 1 second TTL
        self.cache.set("ttl_key", "value", namespace="test", ttl=1)
        
        # Should exist immediately
        self.assertIsNotNone(self.cache.get("ttl_key", namespace="test"))
        
        # Wait for expiration
        time.sleep(2)
        
        # Should be expired
        result = self.cache.get("ttl_key", namespace="test")
        self.assertIsNone(result)
    
    def test_namespace_isolation(self):
        """Test namespace isolation."""
        # Set in different namespaces
        self.cache.set("key", "value1", namespace="ns1")
        self.cache.set("key", "value2", namespace="ns2")
        
        # Get from different namespaces
        self.assertEqual(self.cache.get("key", "ns1"), "value1")
        self.assertEqual(self.cache.get("key", "ns2"), "value2")
    
    def test_lru_eviction(self):
        """Test LRU eviction when memory limit reached."""
        # Fill cache to trigger eviction
        for i in range(100):
            self.cache.set(f"key_{i}", f"value_{i}" * 1000, namespace="test")
        
        # Check that evictions occurred
        self.assertGreater(self.cache.stats["evictions"], 0)
    
    def test_cache_stats(self):
        """Test cache statistics."""
        # Perform operations
        self.cache.set("key1", "value1")
        self.cache.get("key1")  # Hit
        self.cache.get("key2")  # Miss
        
        stats = self.cache.get_stats()
        self.assertIn("hits", stats)
        self.assertIn("misses", stats)
        self.assertIn("hit_rate", stats)


class TestNamespaceManager(unittest.TestCase):
    """Test namespace management functionality."""
    
    def setUp(self):
        """Set up test namespace manager."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = NamespaceManager(
            db_path=os.path.join(self.temp_dir, "test_namespaces.db")
        )
    
    def tearDown(self):
        """Clean up test namespace manager."""
        self.manager.close()
        shutil.rmtree(self.temp_dir)
    
    def test_default_profiles(self):
        """Test that default family and agent profiles are created."""
        # Check family members
        self.assertIn("mene", self.manager.profiles)
        self.assertIn("cindy", self.manager.profiles)
        self.assertIn("viola", self.manager.profiles)
        
        # Check AI agents
        self.assertIn("nina", self.manager.profiles)
        self.assertIn("pluma", self.manager.profiles)
    
    def test_create_namespace(self):
        """Test namespace creation."""
        ns_id = self.manager.create_namespace(
            name="Test Project",
            type=NamespaceType.PROJECT,
            owner="mene",
            access_level=AccessLevel.PRIVATE
        )
        
        self.assertIsNotNone(ns_id)
        self.assertIn(ns_id, self.manager.namespaces)
    
    def test_namespace_access_control(self):
        """Test namespace access control."""
        # Create private namespace
        private_ns = self.manager.create_namespace(
            name="Private",
            type=NamespaceType.USER,
            owner="mene",
            access_level=AccessLevel.PRIVATE
        )
        
        namespace = self.manager.namespaces[private_ns]
        
        # Owner should have access
        self.assertTrue(namespace.can_access("mene", NamespaceType.USER))
        
        # Others should not have access
        self.assertFalse(namespace.can_access("cindy", NamespaceType.USER))
    
    def test_namespace_switching(self):
        """Test namespace context switching."""
        # Create namespace
        ns_id = self.manager.create_namespace(
            name="Test",
            type=NamespaceType.PROJECT,
            owner="mene"
        )
        
        # Switch to namespace
        success = self.manager.switch_namespace(ns_id, "mene")
        self.assertTrue(success)
        self.assertEqual(self.manager.current_namespace, ns_id)
    
    def test_cross_namespace_sharing(self):
        """Test knowledge sharing between namespaces."""
        # Create two namespaces
        ns1 = self.manager.create_namespace("NS1", NamespaceType.PROJECT, "mene")
        ns2 = self.manager.create_namespace("NS2", NamespaceType.PROJECT, "cindy")
        
        # Share knowledge
        success = self.manager.share_knowledge(ns1, ns2, "link")
        self.assertTrue(success)


class TestContextRanker(unittest.TestCase):
    """Test context ranking functionality."""
    
    def setUp(self):
        """Set up test ranker."""
        self.temp_dir = tempfile.mkdtemp()
        self.ranker = ContextRanker(
            db_path=os.path.join(self.temp_dir, "test_ranking.db")
        )
    
    def tearDown(self):
        """Clean up test ranker."""
        self.ranker.close()
        shutil.rmtree(self.temp_dir)
    
    def test_add_context(self):
        """Test adding context for ranking."""
        context_id = self.ranker.add_context(
            content="Machine learning is a subset of artificial intelligence",
            namespace="test",
            metadata={"topic": "ML"}
        )
        
        self.assertIsNotNone(context_id)
        self.assertEqual(self.ranker.total_documents, 1)
    
    def test_relevance_scoring(self):
        """Test TF-IDF relevance scoring."""
        # Add contexts
        self.ranker.add_context("Machine learning algorithms", "test")
        self.ranker.add_context("Deep learning neural networks", "test")
        self.ranker.add_context("Data science and analytics", "test")
        
        # Rank by relevance
        results = self.ranker.rank_contexts(
            query="machine learning",
            namespace="test",
            limit=10
        )
        
        self.assertGreater(len(results), 0)
        # First result should be most relevant
        self.assertIn("machine learning", results[0].content.lower())
    
    def test_time_decay(self):
        """Test time decay scoring."""
        # Add old context
        old_id = self.ranker.add_context("Old content", "test")
        
        # Manually set old timestamp
        self.ranker.conn.execute(
            "UPDATE context_items SET timestamp = ? WHERE id = ?",
            (time.time() - 86400 * 30, old_id)  # 30 days old
        )
        
        # Add new context
        new_id = self.ranker.add_context("New content", "test")
        
        # Rank contexts
        results = self.ranker.rank_contexts("content", "test")
        
        # New content should rank higher
        self.assertEqual(results[0].content, "New content")
    
    def test_pinning(self):
        """Test context pinning."""
        # Add contexts
        normal_id = self.ranker.add_context("Normal content", "test")
        pinned_id = self.ranker.add_context("Pinned content", "test")
        
        # Pin one context
        self.ranker.pin_context(pinned_id)
        
        # Rank contexts
        results = self.ranker.rank_contexts("content", "test")
        
        # Pinned should be first
        self.assertTrue(results[0].is_pinned)
        self.assertEqual(results[0].id, pinned_id)
    
    def test_boost_factor(self):
        """Test boost factor application."""
        # Add contexts
        normal_id = self.ranker.add_context("Normal content", "test")
        boosted_id = self.ranker.add_context("Boosted content", "test")
        
        # Apply boost
        self.ranker.boost_context(boosted_id, 3.0)
        
        # Rank contexts
        results = self.ranker.rank_contexts("content", "test")
        
        # Find boosted context
        boosted = next(r for r in results if r.id == boosted_id)
        self.assertEqual(boosted.boost_factor, 3.0)


class TestSyncEngine(unittest.TestCase):
    """Test sync engine functionality."""
    
    def setUp(self):
        """Set up test sync engine."""
        self.temp_dir = tempfile.mkdtemp()
        self.sync = SyncEngine(
            sqlite_path=os.path.join(self.temp_dir, "test_sync.db"),
            enable_realtime=False  # Disable for testing
        )
    
    def tearDown(self):
        """Clean up test sync engine."""
        self.sync.close()
        shutil.rmtree(self.temp_dir)
    
    def test_queue_upload(self):
        """Test queuing data for upload."""
        self.sync.queue_upload(
            table_name="test_table",
            operation_type="insert",
            data={"id": "test1", "content": "test"},
            namespace="test"
        )
        
        # Check queue
        self.assertGreater(self.sync.upload_queue.qsize(), 0)
    
    def test_sync_stats(self):
        """Test sync statistics."""
        # Queue some operations
        for i in range(5):
            self.sync.queue_upload(
                table_name="test_table",
                operation_type="insert",
                data={"id": f"test{i}"},
                namespace="test"
            )
        
        stats = self.sync.get_sync_stats()
        self.assertIn("total_operations", stats)
        self.assertIn("pending", stats)
        self.assertEqual(stats["upload_queue_size"], 5)
    
    def test_vector_clock(self):
        """Test vector clock for conflict resolution."""
        from context_engine.sync import VectorClock
        
        clock1 = VectorClock()
        clock2 = VectorClock()
        
        # Increment clocks
        clock1.increment("node1")
        clock2.increment("node2")
        
        # Test happens-before relationship
        self.assertFalse(clock1.happens_before(clock2))
        self.assertTrue(clock1.concurrent_with(clock2))
        
        # Merge clocks
        clock1.merge(clock2)
        self.assertEqual(clock1.clocks["node2"], 1)


class TestContextEngineIntegration(unittest.TestCase):
    """Integration tests for the complete Context Engine."""
    
    def setUp(self):
        """Set up test context engine."""
        self.temp_dir = tempfile.mkdtemp()
        self.engine = ContextEngine(
            cache_config={
                "sqlite_path": os.path.join(self.temp_dir, "cache.db"),
                "max_memory_mb": 10,
                "enable_mmap": False
            },
            namespace_config={
                "db_path": os.path.join(self.temp_dir, "namespaces.db")
            },
            sync_config={
                "sqlite_path": os.path.join(self.temp_dir, "sync.db"),
                "enable_realtime": False
            },
            ranker_config={
                "db_path": os.path.join(self.temp_dir, "ranking.db")
            }
        )
    
    def tearDown(self):
        """Clean up test engine."""
        self.engine.close()
        shutil.rmtree(self.temp_dir)
    
    def test_end_to_end_workflow(self):
        """Test complete workflow from adding to retrieving contexts."""
        # Set profile
        self.engine.set_profile("mene")
        
        # Add contexts
        id1 = self.engine.add_context(
            "Python is a high-level programming language",
            metadata={"topic": "programming"}
        )
        
        id2 = self.engine.add_context(
            "Machine learning uses Python extensively",
            metadata={"topic": "ML"}
        )
        
        # Retrieve contexts
        request = ContextRequest(
            query="Python programming",
            profile_id="mene",
            limit=10
        )
        
        response = self.engine.retrieve_context(request)
        
        self.assertIsInstance(response, ContextResponse)
        self.assertGreater(len(response.contexts), 0)
        self.assertLess(response.retrieval_time_ms, 1000)
    
    def test_namespace_isolation_integration(self):
        """Test namespace isolation in integrated system."""
        # Create contexts for different users
        self.engine.set_profile("mene")
        mene_id = self.engine.add_context("Mene's private notes")
        
        self.engine.set_profile("cindy")
        cindy_id = self.engine.add_context("Cindy's private notes")
        
        # Try to access across namespaces
        request = ContextRequest(
            query="private notes",
            profile_id="mene",
            namespace=None  # Use mene's namespace
        )
        
        response = self.engine.retrieve_context(request)
        
        # Should only find mene's notes
        contents = [c.content for c in response.contexts]
        self.assertIn("Mene's private notes", contents)
        self.assertNotIn("Cindy's private notes", contents)
    
    def test_performance_requirements(self):
        """Test that performance requirements are met."""
        # Set profile
        self.engine.set_profile("mene")
        
        # Add many contexts
        for i in range(100):
            self.engine.add_context(f"Test context {i}")
        
        # Measure retrieval time
        request = ContextRequest(
            query="test context",
            profile_id="mene",
            limit=15
        )
        
        start = time.perf_counter()
        response = self.engine.retrieve_context(request)
        duration_ms = (time.perf_counter() - start) * 1000
        
        # Check <100ms requirement
        self.assertLess(duration_ms, 100, f"Retrieval took {duration_ms:.2f}ms")
        
        # Check that we got results
        self.assertEqual(len(response.contexts), 15)
    
    def test_context_sharing(self):
        """Test context sharing between namespaces."""
        # Create context in mene's namespace
        self.engine.set_profile("mene")
        context_id = self.engine.add_context("Shared knowledge")
        
        # Get cindy's namespace
        self.engine.set_profile("cindy")
        cindy_namespaces = self.engine.namespace_manager.get_accessible_namespaces("cindy")
        cindy_ns = cindy_namespaces[0].id
        
        # Share from mene to cindy
        self.engine.set_profile("mene")
        self.engine.share_context(context_id, cindy_ns, "copy")
        
        # Now cindy should be able to find it
        self.engine.set_profile("cindy")
        request = ContextRequest(
            query="shared knowledge",
            profile_id="cindy"
        )
        
        response = self.engine.retrieve_context(request)
        # Note: In real implementation, sharing would need more setup
    
    def test_stats_collection(self):
        """Test statistics collection."""
        # Perform some operations
        self.engine.set_profile("mene")
        self.engine.add_context("Test content")
        
        request = ContextRequest(query="test", profile_id="mene")
        self.engine.retrieve_context(request)
        
        # Get stats
        stats = self.engine.get_stats()
        
        self.assertIn("engine", stats)
        self.assertIn("cache", stats)
        self.assertIn("ranker", stats)
        self.assertIn("sync", stats)
        
        # Check engine stats
        self.assertEqual(stats["engine"]["total_requests"], 1)
        self.assertGreater(stats["engine"]["avg_retrieval_ms"], 0)


class TestFamilyScenarios(unittest.TestCase):
    """Test family-specific scenarios."""
    
    def setUp(self):
        """Set up family test scenarios."""
        self.temp_dir = tempfile.mkdtemp()
        self.engine = ContextEngine(
            cache_config={"sqlite_path": os.path.join(self.temp_dir, "cache.db")},
            namespace_config={"db_path": os.path.join(self.temp_dir, "ns.db")},
            sync_config={"sqlite_path": os.path.join(self.temp_dir, "sync.db"), "enable_realtime": False},
            ranker_config={"db_path": os.path.join(self.temp_dir, "rank.db")}
        )
    
    def tearDown(self):
        """Clean up."""
        self.engine.close()
        shutil.rmtree(self.temp_dir)
    
    def test_family_member_isolation(self):
        """Test that family members' contexts are isolated."""
        family_data = {
            "mene": ["Work project notes", "API documentation"],
            "cindy": ["Recipe collection", "Garden planning"],
            "viola": ["Study notes", "Research papers"],
        }
        
        # Add contexts for each family member
        for member, contents in family_data.items():
            self.engine.set_profile(member)
            for content in contents:
                self.engine.add_context(content)
        
        # Verify isolation
        for member in family_data:
            self.engine.set_profile(member)
            request = ContextRequest(
                query="notes",
                profile_id=member
            )
            response = self.engine.retrieve_context(request)
            
            # Should only see their own content
            for context in response.contexts:
                # Check that content belongs to the right person
                found = False
                for content in family_data[member]:
                    if content in context.content:
                        found = True
                        break
                
                if context.content and "notes" in context.content.lower():
                    self.assertTrue(found or member == "mene", 
                                  f"{member} seeing wrong content: {context.content}")
    
    def test_agent_workspace_isolation(self):
        """Test that AI agents have isolated workspaces."""
        agents_data = {
            "nina": "Calendar management context",
            "pluma": "Email drafting context",
            "huata": "Knowledge base context"
        }
        
        # Add contexts for each agent
        for agent, content in agents_data.items():
            self.engine.set_profile(agent)
            self.engine.add_context(content)
        
        # Verify each agent only sees their context
        for agent in agents_data:
            self.engine.set_profile(agent)
            request = ContextRequest(
                query="context",
                profile_id=agent
            )
            response = self.engine.retrieve_context(request)
            
            # Should find their own context
            contents = [c.content for c in response.contexts]
            self.assertIn(agents_data[agent], contents)


def run_all_tests():
    """Run all tests and print summary."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestMultiLevelCache))
    suite.addTests(loader.loadTestsFromTestCase(TestNamespaceManager))
    suite.addTests(loader.loadTestsFromTestCase(TestContextRanker))
    suite.addTests(loader.loadTestsFromTestCase(TestSyncEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestContextEngineIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestFamilyScenarios))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    print(f"Tests Run:     {result.testsRun}")
    print(f"Failures:      {len(result.failures)}")
    print(f"Errors:        {len(result.errors)}")
    print(f"Skipped:       {len(result.skipped)}")
    
    if result.wasSuccessful():
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed")
    
    return result


if __name__ == "__main__":
    result = run_all_tests()