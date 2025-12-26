-- Enable pgvector extension for semantic search
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column to memories table
ALTER TABLE memories
ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- Create index for fast similarity search
CREATE INDEX IF NOT EXISTS memories_embedding_idx
ON memories
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Add similarity search function
CREATE OR REPLACE FUNCTION search_memories_semantic(
  query_embedding vector(1536),
  match_count int DEFAULT 10,
  similarity_threshold float DEFAULT 0.7
)
RETURNS TABLE (
  id text,
  content text,
  similarity float,
  metadata jsonb,
  category text,
  importance text,
  timestamp bigint
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    m.id,
    m.content,
    1 - (m.embedding <=> query_embedding) as similarity,
    m.metadata,
    m.category,
    m.importance,
    m.timestamp
  FROM memories m
  WHERE m.embedding IS NOT NULL
  AND 1 - (m.embedding <=> query_embedding) > similarity_threshold
  ORDER BY m.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Optional: Function to check if pgvector is working
CREATE OR REPLACE FUNCTION test_pgvector()
RETURNS bool
LANGUAGE plpgsql
AS $$
DECLARE
  test_vec vector(1536);
BEGIN
  -- Create a test vector with 1536 dimensions
  test_vec := array_fill(0.1, ARRAY[1536])::vector;
  RETURN test_vec IS NOT NULL;
EXCEPTION
  WHEN OTHERS THEN
    RETURN FALSE;
END;
$$;

-- Test the installation
SELECT test_pgvector() as pgvector_enabled;
