#!/usr/bin/env python3
"""Context priority ranking system for intelligent retrieval.

Implements:
- Time decay with exponential falloff
- TF-IDF relevance scoring
- Frequency-based importance
- Manual pinning and boosting
"""

import math
import time
import json
import sqlite3
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import numpy as np
from pathlib import Path
import logging
import hashlib
import re

logger = logging.getLogger(__name__)

@dataclass
class ContextItem:
    """Represents a single context item for ranking."""
    id: str
    content: str
    namespace: str
    timestamp: float
    access_count: int = 0
    last_access: float = None
    relevance_score: float = 0.0
    decay_score: float = 1.0
    frequency_score: float = 0.0
    boost_factor: float = 1.0
    is_pinned: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.last_access is None:
            self.last_access = self.timestamp
    
    @property
    def combined_score(self) -> float:
        """Calculate combined priority score."""
        if self.is_pinned:
            return float('inf')  # Pinned items always rank highest
        
        # Weighted combination of scores
        score = (
            self.relevance_score * 0.4 +  # 40% relevance
            self.decay_score * 0.3 +       # 30% recency
            self.frequency_score * 0.3      # 30% frequency
        ) * self.boost_factor
        
        return score

class ContextRanker:
    """Intelligent context ranking system."""
    
    # Time decay parameters
    HALF_LIFE_DAYS = 7  # Context relevance half-life
    MAX_AGE_DAYS = 90   # Maximum age before heavy penalty
    
    # Frequency parameters
    FREQUENCY_WINDOW_HOURS = 24 * 7  # 1 week window for frequency calculation
    MIN_ACCESS_FOR_BOOST = 3  # Minimum accesses for frequency boost
    
    def __init__(self, db_path: str = "context_ranking.db"):
        """Initialize the context ranker.
        
        Args:
            db_path: Path to ranking database
        """
        self.db_path = db_path
        self.conn = self._init_db()
        
        # TF-IDF components
        self.document_frequencies: Dict[str, int] = {}
        self.total_documents = 0
        self.vocabulary: Set[str] = set()
        
        # Access pattern tracking
        self.access_history: Dict[str, List[float]] = defaultdict(list)
        
        # Manual overrides
        self.pinned_items: Set[str] = set()
        self.boost_factors: Dict[str, float] = {}
        
        # Load saved state
        self._load_state()
    
    def _init_db(self) -> sqlite3.Connection:
        """Initialize ranking database."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        
        # Create tables
        conn.execute("""
            CREATE TABLE IF NOT EXISTS context_items (
                id TEXT PRIMARY KEY,
                content TEXT,
                namespace TEXT,
                timestamp REAL,
                access_count INTEGER DEFAULT 0,
                last_access REAL,
                is_pinned BOOLEAN DEFAULT 0,
                boost_factor REAL DEFAULT 1.0,
                metadata TEXT
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS access_log (
                context_id TEXT,
                access_time REAL,
                query TEXT,
                score REAL,
                FOREIGN KEY (context_id) REFERENCES context_items(id)
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tf_idf_state (
                term TEXT PRIMARY KEY,
                document_frequency INTEGER,
                last_updated REAL
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ranking_preferences (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        # Create indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_access_time ON access_log(access_time)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_context_namespace ON context_items(namespace)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_context_timestamp ON context_items(timestamp)")
        
        conn.commit()
        return conn
    
    def _load_state(self):
        """Load saved ranking state from database."""
        # Load TF-IDF state
        cursor = self.conn.execute("SELECT term, document_frequency FROM tf_idf_state")
        for term, freq in cursor.fetchall():
            self.document_frequencies[term] = freq
            self.vocabulary.add(term)
        
        # Load document count
        cursor = self.conn.execute("SELECT COUNT(*) FROM context_items")
        self.total_documents = cursor.fetchone()[0]
        
        # Load pinned items
        cursor = self.conn.execute("SELECT id FROM context_items WHERE is_pinned = 1")
        self.pinned_items = {row[0] for row in cursor.fetchall()}
        
        # Load boost factors
        cursor = self.conn.execute("SELECT id, boost_factor FROM context_items WHERE boost_factor != 1.0")
        self.boost_factors = {row[0]: row[1] for row in cursor.fetchall()}
        
        logger.info(f"Loaded ranking state: {self.total_documents} documents, {len(self.vocabulary)} terms")
    
    def add_context(self, 
                   content: str,
                   namespace: str = "default",
                   metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add a new context item for ranking.
        
        Args:
            content: Context content
            namespace: Namespace for isolation
            metadata: Additional metadata
            
        Returns:
            Context item ID
        """
        # Generate ID
        context_id = hashlib.md5(f"{content}:{namespace}:{time.time()}".encode()).hexdigest()[:16]
        
        # Update TF-IDF model
        self._update_tfidf(content)
        
        # Store in database
        self.conn.execute("""
            INSERT OR REPLACE INTO context_items
            (id, content, namespace, timestamp, access_count, last_access, metadata)
            VALUES (?, ?, ?, ?, 0, ?, ?)
        """, (
            context_id,
            content,
            namespace,
            time.time(),
            time.time(),
            json.dumps(metadata or {})
        ))
        self.conn.commit()
        
        self.total_documents += 1
        
        return context_id
    
    def rank_contexts(self,
                     query: str,
                     namespace: Optional[str] = None,
                     limit: int = 15,
                     min_score: float = 0.1) -> List[ContextItem]:
        """Rank contexts based on query and multiple factors.
        
        Args:
            query: Search query
            namespace: Optional namespace filter
            limit: Maximum number of results
            min_score: Minimum score threshold
            
        Returns:
            Ranked list of context items
        """
        # Build base query
        sql = """
            SELECT id, content, namespace, timestamp, access_count, last_access,
                   is_pinned, boost_factor, metadata
            FROM context_items
        """
        
        params = []
        if namespace:
            sql += " WHERE namespace = ?"
            params.append(namespace)
        
        cursor = self.conn.execute(sql, params)
        
        # Score all contexts
        scored_items = []
        current_time = time.time()
        
        for row in cursor.fetchall():
            item = ContextItem(
                id=row[0],
                content=row[1],
                namespace=row[2],
                timestamp=row[3],
                access_count=row[4],
                last_access=row[5],
                is_pinned=bool(row[6]),
                boost_factor=row[7],
                metadata=json.loads(row[8] or "{}")
            )
            
            # Calculate scores
            item.relevance_score = self._calculate_relevance(query, item.content)
            item.decay_score = self._calculate_decay(item.timestamp, current_time)
            item.frequency_score = self._calculate_frequency(item.id, item.access_count)
            
            # Apply minimum score threshold
            if item.combined_score >= min_score or item.is_pinned:
                scored_items.append(item)
        
        # Sort by combined score (descending)
        scored_items.sort(key=lambda x: x.combined_score, reverse=True)
        
        # Return top results
        results = scored_items[:limit]
        
        # Log access for learning
        for item in results:
            self._log_access(item.id, query, item.combined_score)
        
        return results
    
    def _calculate_relevance(self, query: str, content: str) -> float:
        """Calculate TF-IDF relevance score.
        
        Args:
            query: Search query
            content: Context content
            
        Returns:
            Relevance score between 0 and 1
        """
        # Tokenize
        query_terms = self._tokenize(query.lower())
        content_terms = self._tokenize(content.lower())
        
        if not query_terms or not content_terms:
            return 0.0
        
        # Calculate term frequencies
        content_tf = Counter(content_terms)
        query_tf = Counter(query_terms)
        
        # Calculate TF-IDF vectors
        query_vector = []
        content_vector = []
        
        # Get union of terms
        all_terms = set(query_terms) | set(content_terms)
        
        for term in all_terms:
            # Query TF-IDF
            query_tf_val = query_tf.get(term, 0) / len(query_terms) if query_terms else 0
            query_idf = self._get_idf(term)
            query_vector.append(query_tf_val * query_idf)
            
            # Content TF-IDF
            content_tf_val = content_tf.get(term, 0) / len(content_terms) if content_terms else 0
            content_idf = self._get_idf(term)
            content_vector.append(content_tf_val * content_idf)
        
        # Cosine similarity
        if not query_vector or not content_vector:
            return 0.0
        
        dot_product = sum(q * c for q, c in zip(query_vector, content_vector))
        query_norm = math.sqrt(sum(q * q for q in query_vector))
        content_norm = math.sqrt(sum(c * c for c in content_vector))
        
        if query_norm == 0 or content_norm == 0:
            return 0.0
        
        similarity = dot_product / (query_norm * content_norm)
        
        # Normalize to 0-1 range
        return max(0.0, min(1.0, similarity))
    
    def _calculate_decay(self, timestamp: float, current_time: float) -> float:
        """Calculate time decay score using exponential decay.
        
        Args:
            timestamp: Item creation timestamp
            current_time: Current timestamp
            
        Returns:
            Decay score between 0 and 1
        """
        age_days = (current_time - timestamp) / (24 * 3600)
        
        # Exponential decay with half-life
        decay = math.exp(-math.log(2) * age_days / self.HALF_LIFE_DAYS)
        
        # Apply heavy penalty for very old items
        if age_days > self.MAX_AGE_DAYS:
            decay *= 0.1
        
        return max(0.0, min(1.0, decay))
    
    def _calculate_frequency(self, context_id: str, access_count: int) -> float:
        """Calculate frequency-based importance score.
        
        Args:
            context_id: Context item ID
            access_count: Total access count
            
        Returns:
            Frequency score between 0 and 1
        """
        # Get recent access history
        cursor = self.conn.execute("""
            SELECT COUNT(*) FROM access_log
            WHERE context_id = ? AND access_time > ?
        """, (
            context_id,
            time.time() - (self.FREQUENCY_WINDOW_HOURS * 3600)
        ))
        
        recent_accesses = cursor.fetchone()[0]
        
        # Calculate frequency score
        if recent_accesses < self.MIN_ACCESS_FOR_BOOST:
            base_score = recent_accesses / self.MIN_ACCESS_FOR_BOOST
        else:
            # Logarithmic growth after threshold
            base_score = 1.0 + math.log(recent_accesses / self.MIN_ACCESS_FOR_BOOST) / 10
        
        # Consider total access count with diminishing returns
        total_factor = math.log(access_count + 1) / 10 if access_count > 0 else 0
        
        score = base_score * 0.7 + total_factor * 0.3
        
        return max(0.0, min(1.0, score))
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for TF-IDF calculation.
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of tokens
        """
        # Simple tokenization - can be improved with NLTK or spaCy
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        tokens = text.split()
        
        # Remove stop words (simplified list)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                     'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be'}
        
        return [token for token in tokens if token not in stop_words and len(token) > 2]
    
    def _update_tfidf(self, content: str):
        """Update TF-IDF model with new document.
        
        Args:
            content: Document content
        """
        terms = self._tokenize(content.lower())
        unique_terms = set(terms)
        
        for term in unique_terms:
            if term not in self.document_frequencies:
                self.document_frequencies[term] = 0
            self.document_frequencies[term] += 1
            self.vocabulary.add(term)
            
            # Update database
            self.conn.execute("""
                INSERT OR REPLACE INTO tf_idf_state
                (term, document_frequency, last_updated)
                VALUES (?, ?, ?)
            """, (term, self.document_frequencies[term], time.time()))
        
        self.conn.commit()
    
    def _get_idf(self, term: str) -> float:
        """Get inverse document frequency for a term.
        
        Args:
            term: Term to get IDF for
            
        Returns:
            IDF value
        """
        if term not in self.document_frequencies or self.total_documents == 0:
            return 0.0
        
        df = self.document_frequencies[term]
        idf = math.log((self.total_documents + 1) / (df + 1))
        
        return idf
    
    def _log_access(self, context_id: str, query: str, score: float):
        """Log context access for learning.
        
        Args:
            context_id: Accessed context ID
            query: Query that led to access
            score: Relevance score
        """
        # Log to database
        self.conn.execute("""
            INSERT INTO access_log (context_id, access_time, query, score)
            VALUES (?, ?, ?, ?)
        """, (context_id, time.time(), query, score))
        
        # Update context item stats
        self.conn.execute("""
            UPDATE context_items
            SET access_count = access_count + 1, last_access = ?
            WHERE id = ?
        """, (time.time(), context_id))
        
        self.conn.commit()
        
        # Update in-memory history
        self.access_history[context_id].append(time.time())
        
        # Trim old history
        cutoff = time.time() - (self.FREQUENCY_WINDOW_HOURS * 3600)
        self.access_history[context_id] = [
            t for t in self.access_history[context_id] if t > cutoff
        ]
    
    def pin_context(self, context_id: str):
        """Pin a context to always appear at the top.
        
        Args:
            context_id: Context to pin
        """
        self.pinned_items.add(context_id)
        self.conn.execute(
            "UPDATE context_items SET is_pinned = 1 WHERE id = ?",
            (context_id,)
        )
        self.conn.commit()
    
    def unpin_context(self, context_id: str):
        """Unpin a context.
        
        Args:
            context_id: Context to unpin
        """
        self.pinned_items.discard(context_id)
        self.conn.execute(
            "UPDATE context_items SET is_pinned = 0 WHERE id = ?",
            (context_id,)
        )
        self.conn.commit()
    
    def boost_context(self, context_id: str, factor: float):
        """Apply a boost factor to a context.
        
        Args:
            context_id: Context to boost
            factor: Boost factor (>1 to boost, <1 to reduce)
        """
        self.boost_factors[context_id] = factor
        self.conn.execute(
            "UPDATE context_items SET boost_factor = ? WHERE id = ?",
            (factor, context_id)
        )
        self.conn.commit()
    
    def get_analytics(self) -> Dict[str, Any]:
        """Get ranking analytics and statistics.
        
        Returns:
            Analytics dictionary
        """
        # Get access patterns
        cursor = self.conn.execute("""
            SELECT 
                COUNT(*) as total_accesses,
                COUNT(DISTINCT context_id) as unique_contexts,
                COUNT(DISTINCT query) as unique_queries,
                AVG(score) as avg_score
            FROM access_log
            WHERE access_time > ?
        """, (time.time() - (24 * 3600),))  # Last 24 hours
        
        row = cursor.fetchone()
        
        # Get most accessed contexts
        cursor = self.conn.execute("""
            SELECT id, content, access_count
            FROM context_items
            ORDER BY access_count DESC
            LIMIT 10
        """)
        
        top_contexts = [
            {"id": row[0], "preview": row[1][:50], "count": row[2]}
            for row in cursor.fetchall()
        ]
        
        return {
            "total_contexts": self.total_documents,
            "vocabulary_size": len(self.vocabulary),
            "pinned_items": len(self.pinned_items),
            "boosted_items": len(self.boost_factors),
            "last_24h": {
                "total_accesses": row[0],
                "unique_contexts": row[1],
                "unique_queries": row[2],
                "avg_relevance_score": row[3]
            },
            "top_contexts": top_contexts
        }
    
    def cleanup_old_contexts(self, max_age_days: int = 180):
        """Remove very old contexts to maintain performance.
        
        Args:
            max_age_days: Maximum age in days
        """
        cutoff = time.time() - (max_age_days * 24 * 3600)
        
        # Delete old contexts
        self.conn.execute(
            "DELETE FROM context_items WHERE timestamp < ? AND is_pinned = 0",
            (cutoff,)
        )
        
        # Delete old access logs
        self.conn.execute(
            "DELETE FROM access_log WHERE access_time < ?",
            (cutoff,)
        )
        
        self.conn.commit()
        
        # Rebuild TF-IDF model
        self._rebuild_tfidf()
    
    def _rebuild_tfidf(self):
        """Rebuild TF-IDF model from scratch."""
        self.document_frequencies.clear()
        self.vocabulary.clear()
        
        cursor = self.conn.execute("SELECT content FROM context_items")
        for row in cursor.fetchall():
            self._update_tfidf(row[0])
        
        cursor = self.conn.execute("SELECT COUNT(*) FROM context_items")
        self.total_documents = cursor.fetchone()[0]
        
        logger.info(f"Rebuilt TF-IDF model: {self.total_documents} documents")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

# Singleton instance
_ranker_instance = None

def get_ranker() -> ContextRanker:
    """Get or create the global ranker instance."""
    global _ranker_instance
    if _ranker_instance is None:
        _ranker_instance = ContextRanker()
    return _ranker_instance