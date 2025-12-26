-- Supabase Schema Fix for Memory RAG System
-- Run this in Supabase SQL Editor
-- Date: January 14, 2025

-- 1. Enable vector extension if not already enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Add embedding column to project_memories table
ALTER TABLE project_memories 
ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- 3. Create index for vector similarity search
CREATE INDEX IF NOT EXISTS project_memories_embedding_idx 
ON project_memories 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 4. Create RPC function for memory search
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

-- 5. Create workflow_patterns table if not exists
CREATE TABLE IF NOT EXISTS workflow_patterns (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  project_id text NOT NULL,
  pattern_name text NOT NULL,
  pattern_hash text UNIQUE NOT NULL,
  trigger_embedding vector(1536),
  action_sequence jsonb NOT NULL,
  occurrence_count int DEFAULT 1,
  success_rate float DEFAULT 1.0,
  metadata jsonb DEFAULT '{}',
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

-- 6. Create index for workflow patterns
CREATE INDEX IF NOT EXISTS workflow_patterns_embedding_idx 
ON workflow_patterns 
USING ivfflat (trigger_embedding vector_cosine_ops)
WITH (lists = 100);

-- 7. Create RPC function for pattern search
CREATE OR REPLACE FUNCTION match_patterns(
  query_embedding vector(1536),
  similarity_threshold float,
  match_count int,
  min_occurrences int DEFAULT 1
)
RETURNS TABLE(
  id uuid,
  pattern_name text,
  similarity float,
  action_sequence jsonb,
  occurrence_count int,
  success_rate float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    wp.id,
    wp.pattern_name,
    1 - (wp.trigger_embedding <=> query_embedding) as similarity,
    wp.action_sequence,
    wp.occurrence_count,
    wp.success_rate
  FROM workflow_patterns wp
  WHERE 
    wp.trigger_embedding IS NOT NULL
    AND 1 - (wp.trigger_embedding <=> query_embedding) > similarity_threshold
    AND wp.occurrence_count >= min_occurrences
  ORDER BY wp.trigger_embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- 8. Create knowledge_artifacts table if not exists
CREATE TABLE IF NOT EXISTS knowledge_artifacts (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  project_id text NOT NULL,
  title text NOT NULL,
  content text NOT NULL,
  embedding vector(1536),
  artifact_type text NOT NULL,
  importance_score float DEFAULT 0.5,
  metadata jsonb DEFAULT '{}',
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

-- 9. Create index for knowledge artifacts
CREATE INDEX IF NOT EXISTS knowledge_artifacts_embedding_idx 
ON knowledge_artifacts 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 10. Create RPC function for knowledge search
CREATE OR REPLACE FUNCTION match_knowledge(
  query_embedding vector(1536),
  similarity_threshold float,
  match_count int
)
RETURNS TABLE(
  id uuid,
  title text,
  content text,
  similarity float,
  artifact_type text,
  importance_score float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    ka.id,
    ka.title,
    ka.content,
    1 - (ka.embedding <=> query_embedding) as similarity,
    ka.artifact_type,
    ka.importance_score
  FROM knowledge_artifacts ka
  WHERE 
    ka.embedding IS NOT NULL
    AND 1 - (ka.embedding <=> query_embedding) > similarity_threshold
  ORDER BY ka.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- 11. Verify tables and functions
SELECT 'Tables created:' as status;
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('project_memories', 'workflow_patterns', 'knowledge_artifacts');

SELECT 'Functions created:' as status;
SELECT routine_name FROM information_schema.routines 
WHERE routine_schema = 'public' 
AND routine_name IN ('match_memories', 'match_patterns', 'match_knowledge');

-- 12. Show table structure for verification
SELECT 'project_memories columns:' as status;
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'project_memories' 
ORDER BY ordinal_position;

-- Success message
SELECT 'Supabase schema setup complete!' as status, 
       'Ready for cloud sync with vector embeddings' as message;
