# FalkorDB Memory Architecture Analysis

**Analysis Date**: 2025-10-29  
**Current State**: Single shared graph, no user isolation  
**Target State**: Dual-memory with private + system spaces

---

## Current State Analysis

### Graph Structure
```cypher
Current Labels:
- User (15 nodes)
- Entity (91 nodes)
Total Nodes: 106

Current Relationships:
- KNOWS_ABOUT (primary relationship type)
- User -> Entity connections

Example Data:
executive_mene -[KNOWS_ABOUT]-> Mene
executive_mene -[KNOWS_ABOUT]-> Cindy
executive_mene -[KNOWS_ABOUT]-> Persy
```

### Key Findings

**✅ Strengths**:
1. FalkorDB connection working properly
2. Persistent graph storage implemented
3. Knowledge writeback function exists (`write_knowledge_to_falkordb`)
4. Async/sync wrappers available

**🚨 Critical Issues**:
1. **NO USER ISOLATION** - All entities shared across users
2. No distinction between private and system-wide knowledge
3. All relationships use same `KNOWS_ABOUT` predicate
4. No `user_id` property on Entity nodes

### Current Storage Flow

```python
# main.py Line 1772-1905
async def write_knowledge_to_falkordb(user_id, triples, context):
    # 1. Create User node
    # 2. Create Entity nodes (no user_id!)
    # 3. Create relationships: User -[KNOWS_ABOUT]-> Entity
    # 4. Store metadata on relationships
```

**Problem**: If user A stores "My password is 12345" and user B queries, they can see it!

### Relationship Structure

```cypher
// Current (INSECURE):
(User {id: 'alice'})-[:KNOWS_ABOUT]->(Entity {name: 'password', value: '12345'})
(User {id: 'bob'})-[:KNOWS_ABOUT]->(Entity {name: 'password', value: 'xyz'})

// Issue: Both users share Entity nodes, causing conflicts
```

---

## Proposed Dual-Memory Architecture

### Schema Design

```cypher
// PRIVATE MEMORY (user-specific, default)
(User {id: 'alice'})-[:PRIVATE_KNOWS]->(UserMemory {
    subject: 'my_password',
    predicate: 'is',
    object: '12345',
    content: 'my password is 12345',
    timestamp: '2025-10-29T...',
    metadata: '{...}'
})

// SYSTEM MEMORY (family-wide, shared)
(System {id: 'family_system', type: 'shared_memory_store'})
    -[:SHARED_KNOWS]->
(SystemMemory {
    subject: 'family_vacation',
    predicate: 'scheduled_for',
    object: 'Disney World March 15-22',
    content: 'family vacation scheduled for Disney World March 15-22',
    timestamp: '2025-10-29T...',
    added_by: 'alice',
    metadata: '{...}'
})

// ACCESS TRACKING
(User {id: 'bob'})-[:CAN_ACCESS]->(SystemMemory)
```

### Node Types

| Node Type | Label | Purpose | Properties |
|-----------|-------|---------|------------|
| User | `User` | Individual family members | id, last_updated |
| System | `System` | Family-wide memory store | id='family_system', type, description |
| Private Memory | `UserMemory` | User-specific facts | subject, predicate, object, content, timestamp, metadata |
| Shared Memory | `SystemMemory` | Family-wide facts | subject, predicate, object, content, timestamp, added_by, metadata |

### Relationship Types

| Relationship | Source | Target | Purpose |
|--------------|--------|--------|---------|
| `PRIVATE_KNOWS` | User | UserMemory | Links user to private memories |
| `SHARED_KNOWS` | System | SystemMemory | Links system to shared memories |
| `CONTRIBUTED` | User | SystemMemory | Tracks who added shared memory |
| `CAN_ACCESS` | User | SystemMemory | Access control for shared memories |

---

## Classification Logic

### Automatic Memory Type Detection

```python
def determine_memory_type(content: str) -> Literal['private', 'system']:
    """Intelligently classify memory as private or system-wide"""
    
    # SYSTEM-WIDE keywords (family relevant)
    system_keywords = [
        'family', 'everyone', 'house', 'home address', 'wifi',
        'emergency', 'doctor', 'school', 'vacation', 'trip',
        'car', 'pet', 'dog', 'cat', 'birthday', 'anniversary',
        'elena', 'aris', 'persy', 'stelios', 'franci'  # family names
    ]
    
    # PRIVATE keywords (personal, sensitive)
    private_keywords = [
        'my password', 'my secret', 'my private', 'don\'t tell',
        'personal', 'confidential', 'my account', 'my login',
        'my credit card', 'my ssn', 'my bank', 'diary'
    ]
    
    content_lower = content.lower()
    
    # Explicit privacy markers take precedence
    if any(kw in content_lower for kw in private_keywords):
        return 'private'
    
    # Family-wide relevance
    if any(kw in content_lower for kw in system_keywords):
        return 'system'
    
    # Default to private for safety
    return 'private'
```

### Manual Override Commands

Users can explicitly control memory type:

```
# Force private storage
/private: My secret thoughts about work

# Force system-wide storage  
/family: WiFi password is Home2025Network

# Query specific memory space
/my memories          # Show only private
/family memories      # Show only shared
```

---

## Migration Strategy

### Phase 1: Create Dual-Memory Structure

1. Add `System` node for family-wide memory
2. Create new node types: `UserMemory`, `SystemMemory`
3. Add new relationship types: `PRIVATE_KNOWS`, `SHARED_KNOWS`

### Phase 2: Migrate Existing Data

```python
# For each existing Entity node:
1. Analyze content for privacy classification
2. Create new UserMemory or SystemMemory node
3. Establish appropriate relationships
4. Mark as migrated (metadata flag)
5. Keep old nodes for backup
```

### Phase 3: Update Write Path

```python
# Modify write_knowledge_to_falkordb():
1. Accept memory_type parameter
2. Auto-classify if not specified
3. Create UserMemory or SystemMemory nodes
4. Use PRIVATE_KNOWS or SHARED_KNOWS relationships
```

### Phase 4: Update Read Path

```python
# Modify knowledge retrieval:
1. Query PRIVATE_KNOWS relationships for user's private memories
2. Query SHARED_KNOWS relationships for system memories
3. Merge and sort by timestamp
4. Indicate source ([Private] or [Shared])
```

---

## Backward Compatibility

### Approach

1. **Keep old structure intact** during migration
2. **Add new structure in parallel** 
3. **Update write path** to use new structure
4. **Update read path** to check both structures
5. **Gradual deprecation** of old Entity nodes

### Transition Period

```cypher
// Old structure (deprecated but functional)
(User)-[:KNOWS_ABOUT]->(Entity)

// New structure (active)
(User)-[:PRIVATE_KNOWS]->(UserMemory)
(System)-[:SHARED_KNOWS]->(SystemMemory)

// Both are queryable during transition
```

---

## Security Guarantees

### Privacy Enforcement

✅ **Private memories are NEVER returned for other users**
```cypher
// Alice's query only sees her UserMemory nodes
MATCH (u:User {id: 'alice'})-[:PRIVATE_KNOWS]->(m:UserMemory)
RETURN m
// Bob cannot access Alice's private memories
```

✅ **System memories are visible to all family members**
```cypher
// Any user can access SystemMemory nodes
MATCH (s:System {id: 'family_system'})-[:SHARED_KNOWS]->(m:SystemMemory)
RETURN m
```

✅ **Default to private for safety**
- If classification uncertain, store as private
- User can manually share later if needed

### Access Control

- Private memories: Only owning user
- System memories: All authenticated family members
- Admin: Can view all memories (future feature)

---

## Performance Considerations

### Query Optimization

```cypher
// Efficient dual-query approach
// Query 1: Private memories (indexed by user_id)
MATCH (u:User {id: $user_id})-[:PRIVATE_KNOWS]->(m:UserMemory)
WHERE m.timestamp > $since
RETURN m ORDER BY m.timestamp DESC LIMIT 10

// Query 2: System memories (indexed by System node)
MATCH (s:System {id: 'family_system'})-[:SHARED_KNOWS]->(m:SystemMemory)
WHERE m.timestamp > $since  
RETURN m ORDER BY m.timestamp DESC LIMIT 10

// Merge in application layer
```

### Indexes Required

```cypher
// Create indexes for performance
CREATE INDEX FOR (u:User) ON (u.id)
CREATE INDEX FOR (m:UserMemory) ON (m.timestamp)
CREATE INDEX FOR (m:SystemMemory) ON (m.timestamp)
CREATE INDEX FOR (m:UserMemory) ON (m.content)
CREATE INDEX FOR (m:SystemMemory) ON (m.content)
```

---

## Testing Strategy

### Test Cases

1. **Privacy Isolation**
   - User A stores private memory
   - User B queries → should NOT see A's private memory
   - User B should see shared system memories

2. **System Memory Sharing**
   - User A stores family-wide fact
   - User B queries → should see the shared memory
   - Both users see same system memories

3. **Classification Accuracy**
   - "My password is xyz" → classified as private
   - "Family vacation in March" → classified as system
   - Ambiguous content → defaults to private

4. **Manual Override**
   - `/private: content` → always stored as private
   - `/family: content` → always stored as system
   - Overrides automatic classification

5. **Migration Integrity**
   - All existing memories migrated
   - No data loss during migration
   - Old structure still queryable

6. **Backward Compatibility**
   - Old write path still works
   - Old read path returns new memories
   - Gradual transition without breaking changes

---

## Implementation Checklist

- [ ] Create `FalkorDBDualMemory` manager class
- [ ] Implement `store_memory()` with memory_type parameter
- [ ] Implement `get_memories()` with dual-query logic
- [ ] Implement `determine_memory_type()` classifier
- [ ] Update `write_knowledge_to_falkordb()` to use dual-memory
- [ ] Add memory management API endpoints
- [ ] Implement chat command handlers (/private, /family, etc.)
- [ ] Create migration script for existing data
- [ ] Create comprehensive test suite
- [ ] Document user-facing features
- [ ] Performance testing and optimization

---

## Success Criteria

✅ **Functional Requirements**:
1. Private memories completely isolated per user
2. System memories accessible to all family members
3. Automatic classification working with >90% accuracy
4. Manual override commands functional
5. Migration completed without data loss

✅ **Security Requirements**:
1. Zero cross-user private memory leakage
2. All system memories properly shared
3. Default to private for safety
4. Audit trail of memory contributions

✅ **Performance Requirements**:
1. Query latency < 100ms for typical queries
2. No degradation with dual-memory structure
3. Efficient indexing for large memory sets

---

## Next Steps

1. Implement `FalkorDBDualMemory` class (dual_memory_manager.py)
2. Update main.py integration
3. Create migration script
4. Run comprehensive tests
5. Deploy and monitor
