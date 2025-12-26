#!/usr/bin/env python3
"""Namespace management for project and family member isolation.

Provides context isolation for:
- Family members: Mene, Cindy, Viola, Kids
- AI Agents: Nina, Huata, Lyco, Pluma
- Projects: Different work contexts
"""

import json
import time
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
import hashlib
import logging
from pathlib import Path
import sqlite3
from threading import Lock

logger = logging.getLogger(__name__)

class AccessLevel(Enum):
    """Access control levels for namespaces."""
    PRIVATE = "private"      # Only owner can access
    FAMILY = "family"        # Family members can access
    AGENTS = "agents"        # AI agents can access
    SHARED = "shared"        # Everyone can access
    PUBLIC = "public"        # Public knowledge pool

class NamespaceType(Enum):
    """Types of namespaces."""
    USER = "user"           # Individual family member
    AGENT = "agent"         # AI agent
    PROJECT = "project"     # Project workspace
    SHARED = "shared"       # Shared knowledge

@dataclass
class Profile:
    """User or agent profile."""
    id: str
    name: str
    type: NamespaceType
    created_at: float = field(default_factory=time.time)
    preferences: Dict[str, Any] = field(default_factory=dict)
    access_patterns: List[str] = field(default_factory=list)
    allowed_namespaces: Set[str] = field(default_factory=set)
    
    def to_dict(self) -> Dict:
        """Convert profile to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "created_at": self.created_at,
            "preferences": self.preferences,
            "access_patterns": self.access_patterns,
            "allowed_namespaces": list(self.allowed_namespaces)
        }

@dataclass
class Namespace:
    """Represents an isolated context namespace."""
    id: str
    name: str
    type: NamespaceType
    owner: str
    access_level: AccessLevel = AccessLevel.PRIVATE
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    allowed_users: Set[str] = field(default_factory=set)
    allowed_agents: Set[str] = field(default_factory=set)
    parent_namespace: Optional[str] = None
    children_namespaces: Set[str] = field(default_factory=set)
    
    def can_access(self, profile_id: str, profile_type: NamespaceType) -> bool:
        """Check if a profile can access this namespace."""
        # Owner always has access
        if profile_id == self.owner:
            return True
        
        # Check access level
        if self.access_level == AccessLevel.PUBLIC:
            return True
        
        if self.access_level == AccessLevel.SHARED:
            return profile_id in self.allowed_users or profile_id in self.allowed_agents
        
        if self.access_level == AccessLevel.FAMILY and profile_type == NamespaceType.USER:
            return profile_id in self.allowed_users
        
        if self.access_level == AccessLevel.AGENTS and profile_type == NamespaceType.AGENT:
            return profile_id in self.allowed_agents
        
        return False
    
    def to_dict(self) -> Dict:
        """Convert namespace to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "owner": self.owner,
            "access_level": self.access_level.value,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "metadata": self.metadata,
            "allowed_users": list(self.allowed_users),
            "allowed_agents": list(self.allowed_agents),
            "parent_namespace": self.parent_namespace,
            "children_namespaces": list(self.children_namespaces)
        }

class NamespaceManager:
    """Manages namespace isolation and access control."""
    
    # Predefined family members
    FAMILY_MEMBERS = {
        "mene": Profile("mene", "Mene", NamespaceType.USER),
        "cindy": Profile("cindy", "Cindy", NamespaceType.USER),
        "viola": Profile("viola", "Viola", NamespaceType.USER),
        "kids": Profile("kids", "Kids", NamespaceType.USER)
    }
    
    # Predefined AI agents
    AI_AGENTS = {
        "nina": Profile("nina", "Nina", NamespaceType.AGENT),
        "huata": Profile("huata", "Huata", NamespaceType.AGENT),
        "lyco": Profile("lyco", "Lyco", NamespaceType.AGENT),
        "pluma": Profile("pluma", "Pluma", NamespaceType.AGENT)
    }
    
    def __init__(self, db_path: str = "namespaces.db"):
        """Initialize namespace manager.
        
        Args:
            db_path: Path to namespace database
        """
        self.db_path = db_path
        self.conn = self._init_db()
        self.lock = Lock()
        
        # In-memory cache
        self.namespaces: Dict[str, Namespace] = {}
        self.profiles: Dict[str, Profile] = {}
        
        # Load predefined profiles
        self._init_default_profiles()
        
        # Context switching optimization
        self.current_namespace: Optional[str] = None
        self.namespace_cache: Dict[str, List[str]] = {}
    
    def _init_db(self) -> sqlite3.Connection:
        """Initialize database for namespace persistence."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        
        # Create tables
        conn.execute("""
            CREATE TABLE IF NOT EXISTS namespaces (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                owner TEXT NOT NULL,
                access_level TEXT DEFAULT 'private',
                created_at REAL,
                last_accessed REAL,
                metadata TEXT,
                allowed_users TEXT,
                allowed_agents TEXT,
                parent_namespace TEXT,
                children_namespaces TEXT
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                created_at REAL,
                preferences TEXT,
                access_patterns TEXT,
                allowed_namespaces TEXT
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cross_references (
                source_namespace TEXT,
                target_namespace TEXT,
                reference_type TEXT,
                created_at REAL,
                metadata TEXT,
                PRIMARY KEY (source_namespace, target_namespace)
            )
        """)
        
        # Create indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_namespace_owner ON namespaces(owner)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_namespace_type ON namespaces(type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_profile_type ON profiles(type)")
        
        conn.commit()
        return conn
    
    def _init_default_profiles(self):
        """Initialize default family and agent profiles."""
        # Load family members
        for member_id, profile in self.FAMILY_MEMBERS.items():
            self._load_or_create_profile(profile)
            # Create personal namespace
            self.create_namespace(
                name=f"{profile.name}'s Space",
                type=NamespaceType.USER,
                owner=profile.id,
                access_level=AccessLevel.PRIVATE
            )
        
        # Load AI agents
        for agent_id, profile in self.AI_AGENTS.items():
            self._load_or_create_profile(profile)
            # Create agent workspace
            self.create_namespace(
                name=f"{profile.name} Workspace",
                type=NamespaceType.AGENT,
                owner=profile.id,
                access_level=AccessLevel.AGENTS
            )
        
        # Create shared spaces
        self.create_namespace(
            name="Family Shared",
            type=NamespaceType.SHARED,
            owner="family",
            access_level=AccessLevel.FAMILY,
            allowed_users=set(self.FAMILY_MEMBERS.keys())
        )
        
        self.create_namespace(
            name="AI Shared Knowledge",
            type=NamespaceType.SHARED,
            owner="system",
            access_level=AccessLevel.AGENTS,
            allowed_agents=set(self.AI_AGENTS.keys())
        )
    
    def _load_or_create_profile(self, profile: Profile):
        """Load profile from database or create if not exists."""
        with self.lock:
            # Check database
            cursor = self.conn.execute(
                "SELECT * FROM profiles WHERE id = ?",
                (profile.id,)
            )
            row = cursor.fetchone()
            
            if row:
                # Load existing profile
                self.profiles[profile.id] = Profile(
                    id=row[0],
                    name=row[1],
                    type=NamespaceType(row[2]),
                    created_at=row[3],
                    preferences=json.loads(row[4] or "{}"),
                    access_patterns=json.loads(row[5] or "[]"),
                    allowed_namespaces=set(json.loads(row[6] or "[]"))
                )
            else:
                # Create new profile
                self.profiles[profile.id] = profile
                self.conn.execute("""
                    INSERT INTO profiles 
                    (id, name, type, created_at, preferences, access_patterns, allowed_namespaces)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    profile.id,
                    profile.name,
                    profile.type.value,
                    profile.created_at,
                    json.dumps(profile.preferences),
                    json.dumps(profile.access_patterns),
                    json.dumps(list(profile.allowed_namespaces))
                ))
                self.conn.commit()
    
    def create_namespace(self, 
                        name: str,
                        type: NamespaceType,
                        owner: str,
                        access_level: AccessLevel = AccessLevel.PRIVATE,
                        allowed_users: Optional[Set[str]] = None,
                        allowed_agents: Optional[Set[str]] = None,
                        parent_namespace: Optional[str] = None) -> str:
        """Create a new namespace.
        
        Args:
            name: Namespace name
            type: Type of namespace
            owner: Owner profile ID
            access_level: Access control level
            allowed_users: Set of allowed user IDs
            allowed_agents: Set of allowed agent IDs
            parent_namespace: Parent namespace ID for hierarchical organization
            
        Returns:
            Namespace ID
        """
        # Generate namespace ID
        namespace_id = hashlib.md5(f"{owner}:{name}:{time.time()}".encode()).hexdigest()[:16]
        
        namespace = Namespace(
            id=namespace_id,
            name=name,
            type=type,
            owner=owner,
            access_level=access_level,
            allowed_users=allowed_users or set(),
            allowed_agents=allowed_agents or set(),
            parent_namespace=parent_namespace
        )
        
        with self.lock:
            # Check for duplicates
            cursor = self.conn.execute(
                "SELECT id FROM namespaces WHERE owner = ? AND name = ?",
                (owner, name)
            )
            if cursor.fetchone():
                return cursor.fetchone()[0]  # Return existing namespace
            
            # Store in memory and database
            self.namespaces[namespace_id] = namespace
            
            self.conn.execute("""
                INSERT INTO namespaces 
                (id, name, type, owner, access_level, created_at, last_accessed,
                 metadata, allowed_users, allowed_agents, parent_namespace, children_namespaces)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                namespace.id,
                namespace.name,
                namespace.type.value,
                namespace.owner,
                namespace.access_level.value,
                namespace.created_at,
                namespace.last_accessed,
                json.dumps(namespace.metadata),
                json.dumps(list(namespace.allowed_users)),
                json.dumps(list(namespace.allowed_agents)),
                namespace.parent_namespace,
                json.dumps(list(namespace.children_namespaces))
            ))
            
            # Update parent namespace if exists
            if parent_namespace and parent_namespace in self.namespaces:
                parent = self.namespaces[parent_namespace]
                parent.children_namespaces.add(namespace_id)
                self._update_namespace(parent)
            
            self.conn.commit()
        
        logger.info(f"Created namespace: {name} (ID: {namespace_id})")
        return namespace_id
    
    def switch_namespace(self, namespace_id: str, profile_id: str) -> bool:
        """Switch to a different namespace context.
        
        Args:
            namespace_id: Target namespace ID
            profile_id: Profile requesting the switch
            
        Returns:
            True if switch successful, False otherwise
        """
        if namespace_id not in self.namespaces:
            logger.error(f"Namespace not found: {namespace_id}")
            return False
        
        namespace = self.namespaces[namespace_id]
        profile = self.profiles.get(profile_id)
        
        if not profile:
            logger.error(f"Profile not found: {profile_id}")
            return False
        
        # Check access permissions
        if not namespace.can_access(profile_id, profile.type):
            logger.warning(f"Access denied for {profile_id} to namespace {namespace_id}")
            return False
        
        # Update current namespace
        self.current_namespace = namespace_id
        
        # Update last accessed time
        namespace.last_accessed = time.time()
        self._update_namespace(namespace)
        
        # Track access pattern
        profile.access_patterns.append(namespace_id)
        if len(profile.access_patterns) > 100:
            profile.access_patterns = profile.access_patterns[-100:]
        
        logger.info(f"Switched to namespace: {namespace.name} for profile: {profile.name}")
        return True
    
    def get_accessible_namespaces(self, profile_id: str) -> List[Namespace]:
        """Get all namespaces accessible to a profile.
        
        Args:
            profile_id: Profile ID
            
        Returns:
            List of accessible namespaces
        """
        profile = self.profiles.get(profile_id)
        if not profile:
            return []
        
        accessible = []
        for namespace in self.namespaces.values():
            if namespace.can_access(profile_id, profile.type):
                accessible.append(namespace)
        
        return accessible
    
    def share_knowledge(self, 
                       source_namespace: str,
                       target_namespace: str,
                       reference_type: str = "link") -> bool:
        """Create cross-namespace knowledge sharing.
        
        Args:
            source_namespace: Source namespace ID
            target_namespace: Target namespace ID
            reference_type: Type of reference (link, copy, derive)
            
        Returns:
            True if sharing successful
        """
        if source_namespace not in self.namespaces or target_namespace not in self.namespaces:
            return False
        
        with self.lock:
            self.conn.execute("""
                INSERT OR REPLACE INTO cross_references
                (source_namespace, target_namespace, reference_type, created_at, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (
                source_namespace,
                target_namespace,
                reference_type,
                time.time(),
                json.dumps({})
            ))
            self.conn.commit()
        
        logger.info(f"Created knowledge share: {source_namespace} -> {target_namespace}")
        return True
    
    def get_namespace_context(self, namespace_id: str) -> Dict[str, Any]:
        """Get full context for a namespace including relationships.
        
        Args:
            namespace_id: Namespace ID
            
        Returns:
            Context dictionary with namespace info and relationships
        """
        if namespace_id not in self.namespaces:
            return {}
        
        namespace = self.namespaces[namespace_id]
        
        # Get cross-references
        cursor = self.conn.execute("""
            SELECT target_namespace, reference_type 
            FROM cross_references 
            WHERE source_namespace = ?
        """, (namespace_id,))
        
        references = [
            {"target": row[0], "type": row[1]}
            for row in cursor.fetchall()
        ]
        
        return {
            "namespace": namespace.to_dict(),
            "references": references,
            "parent": self.namespaces.get(namespace.parent_namespace).to_dict() 
                     if namespace.parent_namespace else None,
            "children": [
                self.namespaces[child_id].to_dict()
                for child_id in namespace.children_namespaces
                if child_id in self.namespaces
            ]
        }
    
    def _update_namespace(self, namespace: Namespace):
        """Update namespace in database."""
        self.conn.execute("""
            UPDATE namespaces
            SET last_accessed = ?, metadata = ?, children_namespaces = ?
            WHERE id = ?
        """, (
            namespace.last_accessed,
            json.dumps(namespace.metadata),
            json.dumps(list(namespace.children_namespaces)),
            namespace.id
        ))
        self.conn.commit()
    
    def get_profile_preferences(self, profile_id: str) -> Dict[str, Any]:
        """Get profile preferences for personalization."""
        profile = self.profiles.get(profile_id)
        return profile.preferences if profile else {}
    
    def update_profile_preferences(self, profile_id: str, preferences: Dict[str, Any]):
        """Update profile preferences."""
        if profile_id in self.profiles:
            profile = self.profiles[profile_id]
            profile.preferences.update(preferences)
            
            self.conn.execute("""
                UPDATE profiles
                SET preferences = ?
                WHERE id = ?
            """, (json.dumps(profile.preferences), profile_id))
            self.conn.commit()
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

# Singleton instance
_namespace_manager = None

def get_namespace_manager() -> NamespaceManager:
    """Get or create the global namespace manager."""
    global _namespace_manager
    if _namespace_manager is None:
        _namespace_manager = NamespaceManager()
    return _namespace_manager