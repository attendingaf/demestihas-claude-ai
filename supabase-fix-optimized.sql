-- Supabase Schema Fix for Memory RAG System (MEMORY-OPTIMIZED VERSION)
-- Run this in Supabase SQL Editor
-- Date: January 14, 2025
-- Optimized for Supabase free tier memory limits

-- PART 1: Enable Extension
-- Run this first, then continue
CREATE EXTENSION IF NOT EXISTS vector;

-- PART 2: Add Embedding Column
-- This is the critical fix needed
ALTER TABLE project_memories 
ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- PART 3: Create Simple Index (Memory-Optimized)
-- Using fewer lists (10 instead of 100) to stay within memory limits
CREATE INDEX IF NOT EXISTS project_memories_embedding_idx 
ON project_memories 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 10);

-- PART 4: Create Memory Search Function
CREATE OR REPLACE FUNCTION match_memories(
  query_embedding vector(1536),
  similarity_threshold float,
  match_count int,
  filter_project_id text DEFAULT NULL
)
RETURNS TABLE(
  id uuid,
  content text,
  similarity float,
  metadata jsonb,
  created_at timestamp with time zone,
  file_paths text[],
  tool_chain text[],
  interaction_type text,
  success_score float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    pm.id,
    pm.content,
    1 - (pm.embedding <=> query_embedding) as similarity,
    pm.metadata,
    pm.created_at,
    pm.file_paths,
    pm.tool_chain,
    pm.interaction_type,
    pm.success_score
  FROM project_memories pm
  WHERE 
    pm.embedding IS NOT NULL
    AND 1 - (pm.embedding <=> query_embedding) > similarity_threshold
    AND (filter_project_id IS NULL OR pm.project_id = filter_project_id)
  ORDER BY pm.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- PART 5: Verify Setup
SELECT 
  column_name, 
  data_type,
  CASE 
    WHEN column_name = 'embedding' THEN '✅ Ready for cloud sync!'
    ELSE 'Standard column'
  END as status
FROM information_schema.columns 
WHERE table_name = 'project_memories' 
  AND column_name IN ('id', 'content', 'embedding', 'metadata')
ORDER BY ordinal_position;

-- Success message
SELECT 'Memory-optimized setup complete!' as status, 
       'Ready for cloud sync with vector embeddings' as message;