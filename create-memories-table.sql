-- SQL to create the memories table that RAG system expects
-- Run this in your Supabase SQL Editor

CREATE TABLE IF NOT EXISTS memories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content TEXT NOT NULL,
  embedding vector(1536),
  metadata JSONB DEFAULT '{}',
  interaction_type TEXT,
  success_score FLOAT DEFAULT 0.5,
  project_id TEXT,
  user_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_memories_created_at ON memories(created_at DESC);
CREATE INDEX idx_memories_project_id ON memories(project_id);
CREATE INDEX idx_memories_user_id ON memories(user_id);
CREATE INDEX idx_memories_interaction_type ON memories(interaction_type);

-- Enable Row Level Security (optional but recommended)
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;

-- Create a policy to allow all operations (adjust as needed)
CREATE POLICY "Allow all operations" ON memories
  FOR ALL USING (true)
  WITH CHECK (true);

-- Test insert to verify table works
INSERT INTO memories (content, interaction_type, project_id, user_id)
VALUES ('Initial memory: RAG system connected successfully', 'system', 'mcp-smart-memory', 'system');
