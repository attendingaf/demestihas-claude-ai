# Manual Test Scenarios for FalkorDB MCP Server

## Prerequisites

Before running these tests, ensure:

1. ✅ FalkorDB is running on localhost:6379 (VERIFIED - container is running)
2. ❗ OPENAI_API_KEY is set in .env file (REQUIRED for embedding generation)
3. ✅ Server dependencies are installed (npm install)

## Test Execution

### Option 1: Using the Test Script (Recommended)

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="your-actual-api-key"

# Or add it to .env file
echo "OPENAI_API_KEY=your-actual-api-key" > .env

# Run the test suite
npm run dev -- test-scenarios.ts
```

### Option 2: Manual Testing via MCP Client

If you have an MCP client configured, you can test each tool individually:

## Test Scenario 1: Save Private Memory

**Tool:** `save_memory`

**Input:**
```json
{
  "user_id": "test_user_1",
  "text": "My favorite color is blue.",
  "memory_type": "auto"
}
```

**Expected Output:**
```json
{
  "success": true,
  "memory_type": "private",
  "content": "My favorite color is blue.",
  "user_id": "test_user_1",
  "embedding_dimensions": 1536,
  "saved_at": "2025-01-10T..."
}
```

**Verification:** The memory should be classified as "private" because it contains "My" (personal indicator).

---

## Test Scenario 2: Save System Memory

**Tool:** `save_memory`

**Input:**
```json
{
  "user_id": "test_user_1",
  "text": "The weekly grocery list is on the fridge.",
  "memory_type": "system"
}
```

**Expected Output:**
```json
{
  "success": true,
  "memory_type": "system",
  "content": "The weekly grocery list is on the fridge.",
  "user_id": "test_user_1",
  "embedding_dimensions": 1536,
  "saved_at": "2025-01-10T..."
}
```

**Verification:** The memory should be stored as "system" type, making it accessible to all users.

---

## Test Scenario 3: Search Test - User's Own Memory

**Tool:** `search_memories`

**Input:**
```json
{
  "user_id": "test_user_1",
  "query_text": "What is my preferred color?",
  "similarity_threshold": 0.7
}
```

**Expected Output:**
```json
{
  "success": true,
  "query": "What is my preferred color?",
  "user_id": "test_user_1",
  "count": 1,
  "threshold": 0.7,
  "results": [
    {
      "text": "My favorite color is blue.",
      "memory_type": "private",
      "similarity": 0.85,
      "created_at": 1234567890
    }
  ]
}
```

**Verification:** 
- Should return the "favorite color is blue" memory
- Similarity score should be high (>0.7)
- Only test_user_1's private memory

---

## Test Scenario 4: Privacy Test - Different User

**Tool:** `search_memories`

**Input:**
```json
{
  "user_id": "test_user_2",
  "query_text": "What is my preferred color?",
  "include_system": false,
  "similarity_threshold": 0.7
}
```

**Expected Output:**
```json
{
  "success": true,
  "query": "What is my preferred color?",
  "user_id": "test_user_2",
  "count": 0,
  "threshold": 0.7,
  "results": []
}
```

**Verification:** 
- ✅ **CRITICAL:** Should return 0 results
- test_user_2 should NOT see test_user_1's private memory
- This validates privacy/security

---

## Test Scenario 5: System Memory Test - Shared Access

**Tool:** `search_memories`

**Input:**
```json
{
  "user_id": "test_user_2",
  "query_text": "Where is the grocery list?",
  "include_system": true,
  "similarity_threshold": 0.7
}
```

**Expected Output:**
```json
{
  "success": true,
  "query": "Where is the grocery list?",
  "user_id": "test_user_2",
  "count": 1,
  "threshold": 0.7,
  "results": [
    {
      "text": "The weekly grocery list is on the fridge.",
      "memory_type": "system",
      "similarity": 0.82,
      "created_at": 1234567890
    }
  ]
}
```

**Verification:** 
- ✅ **IMPORTANT:** test_user_2 CAN see the system memory
- This validates that system memories are shared across users
- Similarity score should be high

---

## Test Scenario 6: Get All Memories

**Tool:** `get_all_memories`

**Input:**
```json
{
  "user_id": "test_user_1",
  "include_system": true,
  "limit": 100
}
```

**Expected Output:**
```json
{
  "success": true,
  "user_id": "test_user_1",
  "count": 2,
  "limit": 100,
  "include_system": true,
  "memories": [
    {
      "text": "The weekly grocery list is on the fridge.",
      "memory_type": "system",
      "created_at": 1234567891
    },
    {
      "text": "My favorite color is blue.",
      "memory_type": "private",
      "created_at": 1234567890
    }
  ]
}
```

**Verification:**
- Should return both private and system memories
- Ordered by created_at DESC (newest first)
- Count should be 2

---

## Validation Queries

After running all tests, execute these Cypher queries directly against FalkorDB:

### Query 1: Count memories with embeddings

```cypher
MATCH (m:Memory) 
WHERE m.vector IS NOT NULL 
RETURN count(m) AS memories_with_embeddings
```

**Expected:** `2` (one private, one system)

---

### Query 2: Private memory count per user

```cypher
MATCH (u:User)-[:OWNS]->(m:Memory) 
WHERE m.memory_type = 'private' 
RETURN u.user_id AS user_id, count(m) AS private_memory_count
```

**Expected:**
```
user_id         | private_memory_count
----------------|---------------------
test_user_1     | 1
```

---

### Query 3: System memory count

```cypher
MATCH (m:Memory) 
WHERE m.memory_type = 'system' 
RETURN count(m) AS system_memory_count
```

**Expected:** `1`

---

### Query 4: All memories overview

```cypher
MATCH (m:Memory) 
RETURN m.text AS text, 
       m.memory_type AS type, 
       m.created_at AS created 
ORDER BY m.created_at DESC 
LIMIT 10
```

**Expected:** Shows all saved memories with their types

---

## Running Validation Queries

### Using redis-cli (FalkorDB is Redis-compatible):

```bash
# Connect to FalkorDB
docker exec -it demestihas-graphdb redis-cli

# Select the graph
GRAPH.QUERY memory_graph "MATCH (m:Memory) WHERE m.vector IS NOT NULL RETURN count(m)"

# List all memories
GRAPH.QUERY memory_graph "MATCH (m:Memory) RETURN m.text, m.memory_type, m.created_at LIMIT 10"
```

---

## Test Summary Checklist

- [ ] Test 1: Save private memory - SUCCESS
- [ ] Test 2: Save system memory - SUCCESS
- [ ] Test 3: Search own memory - SUCCESS (high similarity)
- [ ] Test 4: Privacy test - SUCCESS (0 results for other user)
- [ ] Test 5: System memory shared - SUCCESS (accessible to all)
- [ ] Test 6: Get all memories - SUCCESS (both types returned)
- [ ] Validation: Memories have embeddings
- [ ] Validation: Private memories have correct ownership
- [ ] Validation: System memories accessible to all

---

## Expected Behavior Summary

### ✅ What Should Work:

1. **Memory Storage:** Both private and system memories are saved with embeddings
2. **Semantic Search:** Queries find relevant memories by meaning, not just keywords
3. **Privacy:** Users can only see their own private memories
4. **Sharing:** All users can see system memories
5. **Classification:** Auto mode correctly identifies private vs system content
6. **Ranking:** Search results sorted by similarity score
7. **Filtering:** Threshold and include_system flags work correctly

### ⚠️ Current Status:

- ✅ FalkorDB is running and accessible
- ✅ All code is implemented and ready
- ❗ **OPENAI_API_KEY required** - Set this before running tests
- ✅ Test script is prepared and ready to execute

---

## Next Steps

1. Add your OpenAI API key to `.env`
2. Run: `tsx test-scenarios.ts`
3. Review output for all 6 tests
4. Verify validation queries show expected counts
5. Confirm all checkboxes above are marked ✅
