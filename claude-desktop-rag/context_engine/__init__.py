#!/usr/bin/env python3
"""Context Engine - High-performance context retrieval and management system.

The Context Engine provides:
- Multi-level caching (Memory, SQLite, Supabase)
- Project/family namespace isolation
- Real-time synchronization
- Intelligent context ranking
"""

import os
import time
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
import hashlib

from .cache import MultiLevelCache, get_cache
from .namespace import NamespaceManager, get_namespace_manager, NamespaceType, AccessLevel
from .sync import SyncEngine, get_sync_engine
from .ranker import ContextRanker, get_ranker, ContextItem

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@dataclass
class ContextRequest:
    """Request for context retrieval."""
    query: str
    profile_id: str
    namespace: Optional[str] = None
    limit: int = 15
    min_score: float = 0.1
    include_cross_namespace: bool = False

@dataclass
class ContextResponse:
    """Response from context retrieval."""
    contexts: List[ContextItem]
    total_found: int
    retrieval_time_ms: float
    cache_hits: Dict[str, int]
    namespace_info: Dict[str, Any]

class ContextEngine:
    """Main orchestrator for the Context Engine system."""
    
    def __init__(self,
                 cache_config: Optional[Dict] = None,
                 namespace_config: Optional[Dict] = None,
                 sync_config: Optional[Dict] = None,
                 ranker_config: Optional[Dict] = None):
        """Initialize the Context Engine.
        
        Args:
            cache_config: Configuration for cache system
            namespace_config: Configuration for namespace manager
            sync_config: Configuration for sync engine
            ranker_config: Configuration for ranker
        """
        # Initialize components
        self.cache = get_cache(**(cache_config or {}))
        self.namespace_manager = get_namespace_manager(**(namespace_config or {}))
        self.sync_engine = get_sync_engine(**(sync_config or {}))
        self.ranker = get_ranker(**(ranker_config or {}))
        
        # Current context
        self.current_profile = None
        self.current_namespace = None
        
        # Performance tracking
        self.stats = {
            "total_requests": 0,
            "avg_retrieval_ms": 0,
            "cache_hit_rate": 0
        }
        
        logger.info("Context Engine initialized")
    
    def set_profile(self, profile_id: str) -> bool:
        """Set the current user/agent profile.
        
        Args:
            profile_id: Profile ID (e.g., 'mene', 'nina')
            
        Returns:
            True if profile set successfully
        """
        if profile_id in self.namespace_manager.profiles:
            self.current_profile = profile_id
            
            # Get default namespace for profile
            namespaces = self.namespace_manager.get_accessible_namespaces(profile_id)
            if namespaces:
                # Use personal namespace or first available
                for ns in namespaces:
                    if ns.owner == profile_id:
                        self.current_namespace = ns.id
                        break
                else:
                    self.current_namespace = namespaces[0].id
            
            logger.info(f"Profile set to: {profile_id}")
            return True
        
        logger.error(f"Profile not found: {profile_id}")
        return False
    
    def switch_namespace(self, namespace_id: str) -> bool:
        """Switch to a different namespace.
        
        Args:
            namespace_id: Target namespace ID
            
        Returns:
            True if switch successful
        """
        if not self.current_profile:
            logger.error("No profile set")
            return False
        
        success = self.namespace_manager.switch_namespace(
            namespace_id, 
            self.current_profile
        )
        
        if success:
            self.current_namespace = namespace_id
            # Clear cache for old namespace to free memory
            self.cache.clear_namespace(self.current_namespace)
        
        return success
    
    def add_context(self,
                   content: str,
                   metadata: Optional[Dict[str, Any]] = None,
                   namespace: Optional[str] = None) -> str:
        """Add a new context to the engine.
        
        Args:
            content: Context content
            metadata: Additional metadata
            namespace: Override namespace (uses current if not provided)
            
        Returns:
            Context ID
        """
        namespace = namespace or self.current_namespace or "default"
        
        # Add to ranker for scoring
        context_id = self.ranker.add_context(content, namespace, metadata)
        
        # Cache the content
        cache_key = f"context:{context_id}"
        self.cache.set(
            cache_key,
            {
                "content": content,
                "metadata": metadata,
                "timestamp": time.time()
            },
            namespace=namespace,
            ttl=86400 * 30  # 30 days TTL
        )
        
        # Queue for sync if connected
        if self.sync_engine.supabase_client:
            self.sync_engine.queue_upload(
                table_name="context_memories",
                operation_type="insert",
                data={
                    "id": context_id,
                    "content": content,
                    "namespace": namespace,
                    "metadata": metadata,
                    "timestamp": time.time()
                },
                namespace=namespace
            )
        
        logger.debug(f"Added context: {context_id} to namespace: {namespace}")
        return context_id
    
    def retrieve_context(self, request: ContextRequest) -> ContextResponse:
        """Retrieve relevant contexts based on request.
        
        Args:
            request: Context retrieval request
            
        Returns:
            Context response with ranked results
        """
        start_time = time.perf_counter()
        self.stats["total_requests"] += 1
        
        # Validate access
        if not self._validate_access(request.profile_id, request.namespace):
            return ContextResponse(
                contexts=[],
                total_found=0,
                retrieval_time_ms=0,
                cache_hits={},
                namespace_info={}
            )
        
        # Determine namespace(s) to search
        search_namespaces = []
        
        if request.namespace:
            search_namespaces.append(request.namespace)
        elif request.include_cross_namespace:
            # Get all accessible namespaces
            accessible = self.namespace_manager.get_accessible_namespaces(request.profile_id)
            search_namespaces = [ns.id for ns in accessible]
        else:
            search_namespaces.append(self.current_namespace or "default")
        
        # Collect contexts from all namespaces
        all_contexts = []
        
        for namespace in search_namespaces:
            # Try cache first
            cache_key = f"search:{hashlib.md5(f'{request.query}:{namespace}'.encode()).hexdigest()}"
            cached_results = self.cache.get(cache_key, namespace)
            
            if cached_results:
                all_contexts.extend(cached_results)
                continue
            
            # Rank contexts
            ranked_contexts = self.ranker.rank_contexts(
                query=request.query,
                namespace=namespace,
                limit=request.limit * 2,  # Get more for cross-namespace filtering
                min_score=request.min_score
            )
            
            # Enhance with cached data
            for context in ranked_contexts:
                cache_key = f"context:{context.id}"
                cached_data = self.cache.get(cache_key, namespace)
                
                if cached_data:
                    context.metadata.update(cached_data.get("metadata", {}))
            
            all_contexts.extend(ranked_contexts)
            
            # Cache search results briefly
            self.cache.set(
                cache_key,
                ranked_contexts,
                namespace=namespace,
                ttl=300  # 5 minutes
            )
        
        # Re-rank combined results if multiple namespaces
        if len(search_namespaces) > 1:
            all_contexts.sort(key=lambda x: x.combined_score, reverse=True)
        
        # Apply final limit
        final_contexts = all_contexts[:request.limit]
        
        # Track retrieval time
        retrieval_time_ms = (time.perf_counter() - start_time) * 1000
        
        # Update stats
        self.stats["avg_retrieval_ms"] = (
            (self.stats["avg_retrieval_ms"] * (self.stats["total_requests"] - 1) + 
             retrieval_time_ms) / self.stats["total_requests"]
        )
        
        # Get namespace info
        namespace_info = {}
        if self.current_namespace:
            namespace_info = self.namespace_manager.get_namespace_context(self.current_namespace)
        
        return ContextResponse(
            contexts=final_contexts,
            total_found=len(all_contexts),
            retrieval_time_ms=retrieval_time_ms,
            cache_hits=self.cache.get_stats()["hits"],
            namespace_info=namespace_info
        )
    
    def _validate_access(self, profile_id: str, namespace: Optional[str]) -> bool:
        """Validate profile access to namespace.
        
        Args:
            profile_id: Profile requesting access
            namespace: Target namespace
            
        Returns:
            True if access allowed
        """
        if not namespace:
            return True  # Default namespace is public
        
        profile = self.namespace_manager.profiles.get(profile_id)
        if not profile:
            return False
        
        ns = self.namespace_manager.namespaces.get(namespace)
        if not ns:
            return False
        
        return ns.can_access(profile_id, profile.type)
    
    def pin_context(self, context_id: str):
        """Pin a context to always appear at top.
        
        Args:
            context_id: Context to pin
        """
        self.ranker.pin_context(context_id)
        
        # Sync pinned state
        if self.sync_engine.supabase_client:
            self.sync_engine.queue_upload(
                table_name="context_metadata",
                operation_type="update",
                data={
                    "context_id": context_id,
                    "is_pinned": True
                },
                namespace=self.current_namespace or "default"
            )
    
    def boost_context(self, context_id: str, factor: float = 2.0):
        """Boost a context's ranking.
        
        Args:
            context_id: Context to boost
            factor: Boost factor
        """
        self.ranker.boost_context(context_id, factor)
    
    def share_context(self, 
                     context_id: str,
                     target_namespace: str,
                     share_type: str = "link"):
        """Share context across namespaces.
        
        Args:
            context_id: Context to share
            target_namespace: Target namespace
            share_type: Type of sharing (link, copy, derive)
        """
        if not self.current_namespace:
            logger.error("No current namespace set")
            return
        
        success = self.namespace_manager.share_knowledge(
            self.current_namespace,
            target_namespace,
            share_type
        )
        
        if success and share_type == "copy":
            # Copy context to target namespace
            cache_key = f"context:{context_id}"
            context_data = self.cache.get(cache_key, self.current_namespace)
            
            if context_data:
                new_id = self.add_context(
                    content=context_data["content"],
                    metadata=context_data.get("metadata"),
                    namespace=target_namespace
                )
                logger.info(f"Copied context {context_id} to {target_namespace} as {new_id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive engine statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            "engine": self.stats,
            "cache": self.cache.get_stats(),
            "ranker": self.ranker.get_analytics(),
            "sync": self.sync_engine.get_sync_stats(),
            "current_profile": self.current_profile,
            "current_namespace": self.current_namespace
        }
    
    def optimize(self):
        """Run optimization routines."""
        # Clean old contexts
        self.ranker.cleanup_old_contexts()
        
        # Force sync
        self.sync_engine.force_sync()
        
        # Clear old cache entries
        if self.current_namespace:
            # Keep only frequently accessed items in memory
            stats = self.cache.get_stats()
            if stats["memory_usage_mb"] > 400:  # If using >400MB
                self.cache.clear_namespace("temp")  # Clear temporary items
        
        logger.info("Optimization complete")
    
    def close(self):
        """Clean up resources."""
        self.cache.close()
        self.namespace_manager.close()
        self.sync_engine.close()
        self.ranker.close()

# Global instance
_engine_instance = None

def get_context_engine(**config) -> ContextEngine:
    """Get or create the global Context Engine instance.
    
    Args:
        **config: Configuration parameters
        
    Returns:
        ContextEngine instance
    """
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = ContextEngine(**config)
    return _engine_instance

# Convenience exports
__all__ = [
    'ContextEngine',
    'get_context_engine',
    'ContextRequest',
    'ContextResponse',
    'MultiLevelCache',
    'NamespaceManager',
    'SyncEngine',
    'ContextRanker'
]