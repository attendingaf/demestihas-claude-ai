-- Quick fix SQL for Supabase
-- Run this in your Supabase SQL Editor to make the tables compatible

-- Option 1: Add missing columns to project_memories
ALTER TABLE project_memories 
ADD COLUMN IF NOT EXISTS embedding vector(1536),
ADD COLUMN IF NOT EXISTS content TEXT,
ADD COLUMN IF NOT EXISTS interaction_type TEXT DEFAULT 'general',
ADD COLUMN IF NOT EXISTS success_score FLOAT DEFAULT 1.0,
ADD COLUMN IF NOT EXISTS project_id TEXT,
ADD COLUMN IF NOT EXISTS user_id TEXT,
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Option 2: Create a memories view that points to project_memories
CREATE OR REPLACE VIEW memories AS 
SELECT * FROM project_memories;

-- Test insert
INSERT INTO project_memories (content, interaction_type, project_id, user_id)
VALUES ('Supabase reconnected after unpause', 'system', 'mcp-smart-memory', 'system')
ON CONFLICT DO NOTHING;

-- Check the result
SELECT COUNT(*) as total_memories FROM project_memories;
