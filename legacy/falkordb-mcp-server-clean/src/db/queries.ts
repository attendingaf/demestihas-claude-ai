/**
 * Cypher query templates for FalkorDB operations
 *
 * These queries handle memory storage and retrieval with vector embeddings
 * for semantic search capabilities.
 */

/**
 * Save a private memory for a specific user
 *
 * Creates or merges:
 * - User node with user_id
 * - Memory node with text, embedding vector, and metadata
 * - OWNS relationship between user and memory
 *
 * Parameters:
 * - user_id: string
 * - text: string
 * - vector: number[] (embedding vector)
 * - confidence: number | null
 * - subject: string | null
 * - predicate: string | null
 * - object: string | null
 * - metadata: object | null
 */
export const SAVE_PRIVATE_MEMORY = `
  MERGE (u:User {user_id: $user_id})
  CREATE (m:Memory {
    text: $text,
    vector: vecf32($vector),
    memory_type: 'private',
    created_at: timestamp()
  })
  CREATE (u)-[:OWNS]->(m)
  RETURN m.text AS text, m.memory_type AS memory_type, m.created_at AS created_at
`;

/**
 * Save a system memory (shared across all users)
 *
 * Creates:
 * - Memory node with text, embedding vector, and metadata
 * - Tagged as 'system' type
 *
 * Parameters:
 * - text: string
 * - vector: number[] (embedding vector)
 * - confidence: number | null
 * - subject: string | null
 * - predicate: string | null
 * - object: string | null
 * - metadata: object | null
 */
export const SAVE_SYSTEM_MEMORY = `
  CREATE (m:Memory {
    text: $text,
    vector: vecf32($vector),
    memory_type: 'system',
    created_at: timestamp()
  })
  RETURN m.text AS text, m.memory_type AS memory_type, m.created_at AS created_at
`;

/**
 * Search memories using vector similarity
 *
 * Finds memories similar to the query vector using vector similarity search.
 * Can filter by user_id (for private memories) and optionally include system memories.
 *
 * Parameters:
 * - user_id: string
 * - query_vector: number[] (embedding vector of the search query)
 * - include_system: boolean
 * - similarity_threshold: number (0-1)
 *
 * Returns memories sorted by similarity score (cosine similarity)
 */
export const SEARCH_MEMORIES = `
  MATCH (m:Memory)
  OPTIONAL MATCH (u:User {user_id: $user_id})-[:OWNS]->(m)
  WHERE
    m.memory_type = 'system' OR
    (m.memory_type = 'private' AND u IS NOT NULL)
  WITH m, vec.euclideanDistance(m.vector, vecf32($query_vector)) AS distance
  WITH m, (1.0 / (1.0 + distance)) AS similarity
  WHERE similarity >= $similarity_threshold
  RETURN m.text AS text,
         m.memory_type AS memory_type,
         m.created_at AS created_at,
         m.subject AS subject,
         m.predicate AS predicate,
         m.object AS object,
         similarity
  ORDER BY similarity DESC
`;

/**
 * Get all memories for a user
 *
 * Retrieves all memories owned by a specific user, optionally including system memories.
 *
 * Parameters:
 * - user_id: string
 * - include_system: boolean
 * - limit: number (maximum number of memories to return)
 *
 * Returns memories ordered by creation date (newest first)
 */
export const GET_ALL_MEMORIES = `
  MATCH (m:Memory)
  OPTIONAL MATCH (u:User {user_id: $user_id})-[:OWNS]->(m)
  WHERE
    m.memory_type = 'system' OR
    (m.memory_type = 'private' AND u IS NOT NULL)
  RETURN m.text AS text,
         m.memory_type AS memory_type,
         m.created_at AS created_at,
         m.subject AS subject,
         m.predicate AS predicate,
         m.object AS object
  ORDER BY m.created_at DESC
  LIMIT $limit
`;
