"""
Working Memory Module for Demestihas-AI

Commercial Parity Feature: Tracks current conversation focus and attention.

This module implements a working memory system that:
1. Tracks currently-discussed entities
2. Weights facts by recency and relevance
3. Decays attention over time
4. Prioritizes retrieval based on current focus
"""

import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta


class WorkingMemory:
    """
    Tracks current conversation focus and attention weights.
    
    Commercial Parity Feature: Enables the agent to distinguish between
    "current task" and "background knowledge".
    """
    
    def __init__(self, decay_minutes: int = 5):
        """
        Initialize working memory.
        
        Args:
            decay_minutes: Minutes before attention decays to zero
        """
        self.current_topic: Optional[str] = None
        self.attention_weights: Dict[str, float] = {}  # entity_id -> timestamp
        self.decay_seconds = decay_minutes * 60
        self.entity_mentions: Dict[str, int] = {}  # entity_id -> mention count
    
    def update_attention(self, entities: List[str], topic: Optional[str] = None):
        """
        Update attention weights for recently mentioned entities.
        
        Args:
            entities: List of entity names/IDs mentioned
            topic: Optional topic label for current conversation
        """
        current_time = time.time()
        
        # Update topic if provided
        if topic:
            self.current_topic = topic
        
        # Boost attention for mentioned entities
        for entity in entities:
            self.attention_weights[entity] = current_time
            self.entity_mentions[entity] = self.entity_mentions.get(entity, 0) + 1
        
        # Decay old attention
        self._decay_attention()
    
    def _decay_attention(self):
        """Remove entities that haven't been mentioned recently."""
        cutoff_time = time.time() - self.decay_seconds
        
        # Remove decayed entities
        self.attention_weights = {
            entity: timestamp
            for entity, timestamp in self.attention_weights.items()
            if timestamp > cutoff_time
        }
        
        # Clean up mention counts for removed entities
        active_entities = set(self.attention_weights.keys())
        self.entity_mentions = {
            entity: count
            for entity, count in self.entity_mentions.items()
            if entity in active_entities
        }
    
    def get_attention_score(self, entity: str) -> float:
        """
        Get attention score for an entity (0.0 to 1.0).
        
        Args:
            entity: Entity name/ID
        
        Returns:
            Attention score (higher = more relevant to current conversation)
        """
        if entity not in self.attention_weights:
            return 0.0
        
        # Calculate recency score (0.0 to 1.0)
        timestamp = self.attention_weights[entity]
        age_seconds = time.time() - timestamp
        recency_score = max(0.0, 1.0 - (age_seconds / self.decay_seconds))
        
        # Calculate frequency score (normalized by max mentions)
        mention_count = self.entity_mentions.get(entity, 0)
        max_mentions = max(self.entity_mentions.values()) if self.entity_mentions else 1
        frequency_score = mention_count / max_mentions
        
        # Combine scores (weighted average)
        attention_score = (0.7 * recency_score) + (0.3 * frequency_score)
        
        return attention_score
    
    def get_focused_entities(self, top_k: int = 5) -> List[str]:
        """
        Get the top K entities currently in focus.
        
        Args:
            top_k: Number of entities to return
        
        Returns:
            List of entity names, sorted by attention score
        """
        self._decay_attention()
        
        # Score all entities
        scored_entities = [
            (entity, self.get_attention_score(entity))
            for entity in self.attention_weights.keys()
        ]
        
        # Sort by score and return top K
        scored_entities.sort(key=lambda x: x[1], reverse=True)
        return [entity for entity, score in scored_entities[:top_k]]
    
    def is_relevant(self, entity: str, threshold: float = 0.3) -> bool:
        """
        Check if an entity is relevant to current conversation.
        
        Args:
            entity: Entity name/ID
            threshold: Minimum attention score to be considered relevant
        
        Returns:
            True if entity is currently relevant
        """
        return self.get_attention_score(entity) >= threshold
    
    def clear(self):
        """Clear all working memory (start fresh conversation)."""
        self.current_topic = None
        self.attention_weights.clear()
        self.entity_mentions.clear()
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current working memory status.
        
        Returns:
            Dictionary with current topic, focused entities, and stats
        """
        self._decay_attention()
        
        focused = self.get_focused_entities(top_k=5)
        
        return {
            "current_topic": self.current_topic,
            "focused_entities": focused,
            "total_entities_tracked": len(self.attention_weights),
            "total_mentions": sum(self.entity_mentions.values()),
            "attention_scores": {
                entity: round(self.get_attention_score(entity), 3)
                for entity in focused
            }
        }


# Global working memory instance (per-user instances managed by agent)
_working_memory_instances: Dict[str, WorkingMemory] = {}


def get_working_memory(user_id: str) -> WorkingMemory:
    """
    Get or create working memory instance for a user.
    
    Args:
        user_id: User ID
    
    Returns:
        WorkingMemory instance for this user
    """
    if user_id not in _working_memory_instances:
        _working_memory_instances[user_id] = WorkingMemory(decay_minutes=5)
    
    return _working_memory_instances[user_id]


def extract_entities_from_query(query: str) -> List[str]:
    """
    Extract entity mentions from a user query.
    
    Simple implementation: extracts capitalized words and common nouns.
    For production, use NER (Named Entity Recognition) model.
    
    Args:
        query: User query text
    
    Returns:
        List of potential entity mentions
    """
    import re
    
    # Extract capitalized words (potential proper nouns)
    capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query)
    
    # Extract quoted phrases (explicit entity references)
    quoted = re.findall(r'"([^"]+)"', query)
    quoted += re.findall(r"'([^']+)'", query)
    
    # Combine and deduplicate
    entities = list(set(capitalized + quoted))
    
    return entities
