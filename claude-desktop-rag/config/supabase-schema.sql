-- Enable vector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Project memories table for storing interaction context
CREATE TABLE project_memories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id TEXT NOT NULL DEFAULT 'demestihas-mas',
  content TEXT NOT NULL,
  embedding vector(1536),
  metadata JSONB DEFAULT '{}',
  interaction_type TEXT,
  tool_chain TEXT[],
  file_paths TEXT[],
  success_score FLOAT DEFAULT 1.0,
  created_at TIMESTAMP DEFAULT NOW(),
  session_id UUID,
  user_id TEXT
);

-- Workflow patterns table for pattern detection and automation
CREATE TABLE workflow_patterns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pattern_hash TEXT UNIQUE,
  pattern_name TEXT,
  trigger_embedding vector(1536),
  action_sequence JSONB,
  occurrence_count INTEGER DEFAULT 1,
  success_rate FLOAT DEFAULT 1.0,
  last_used TIMESTAMP,
  project_contexts TEXT[],
  auto_apply BOOLEAN DEFAULT false
);

-- Knowledge artifacts for storing extracted knowledge
CREATE TABLE knowledge_artifacts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  artifact_type TEXT,
  title TEXT,
  content TEXT,
  embedding vector(1536),
  source_file TEXT,
  tags TEXT[],
  references UUID[],
  importance_score FLOAT DEFAULT 0.5,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for efficient vector similarity search
CREATE INDEX idx_memories_embedding ON project_memories 
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
  
CREATE INDEX idx_patterns_embedding ON workflow_patterns 
  USING ivfflat (trigger_embedding vector_cosine_ops) WITH (lists = 50);
  
CREATE INDEX idx_knowledge_embedding ON knowledge_artifacts 
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Additional indexes for filtering and sorting
CREATE INDEX idx_memories_project ON project_memories(project_id);
CREATE INDEX idx_memories_created ON project_memories(created_at DESC);
CREATE INDEX idx_memories_session ON project_memories(session_id);
CREATE INDEX idx_patterns_count ON workflow_patterns(occurrence_count DESC);
CREATE INDEX idx_patterns_success ON workflow_patterns(success_rate DESC);
CREATE INDEX idx_knowledge_type ON knowledge_artifacts(artifact_type);
CREATE INDEX idx_knowledge_importance ON knowledge_artifacts(importance_score DESC);