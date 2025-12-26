-- Supabase Schema Fix - MINIMAL VERSION (No Indexes)
-- Use this if the optimized version still fails
-- This will work on any Supabase tier

-- Step 1: Enable vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Step 2: Add embedding column to existing table
ALTER TABLE project_memories 
ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- Step 3: Create search function (no index needed)
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
    AND (filter_project_id IS NULL OR pm.project_id = filter_project_id)
  ORDER BY pm.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Step 4: Verify the critical column exists
SELECT 
  CASE 
    WHEN EXISTS (
      SELECT 1 FROM information_schema.columns 
      WHERE table_name = 'project_memories' 
      AND column_name = 'embedding'
    ) THEN '✅ SUCCESS: Embedding column added! Cloud sync will work!'
    ELSE '❌ FAILED: Embedding column not added'
  END as status;

-- Done! The system will work without indexes (just slightly slower)