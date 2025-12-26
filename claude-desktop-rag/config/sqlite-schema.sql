-- Local SQLite schema for fast caching
-- Note: SQLite doesn't have native vector support, we'll store as BLOB

-- Project memories cache
CREATE TABLE IF NOT EXISTS project_memories_cache (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL DEFAULT 'demestihas-mas',
  content TEXT NOT NULL,
  embedding BLOB,
  embedding_json TEXT, -- JSON array fallback for compatibility
  metadata TEXT DEFAULT '{}',
  interaction_type TEXT,
  tool_chain TEXT,
  file_paths TEXT,
  success_score REAL DEFAULT 1.0,
  created_at INTEGER DEFAULT (strftime('%s', 'now')),
  session_id TEXT,
  user_id TEXT,
  synced_to_cloud INTEGER DEFAULT 0,
  last_accessed INTEGER DEFAULT (strftime('%s', 'now'))
);

-- Workflow patterns cache
CREATE TABLE IF NOT EXISTS workflow_patterns_cache (
  id TEXT PRIMARY KEY,
  pattern_hash TEXT UNIQUE,
  pattern_name TEXT,
  trigger_embedding BLOB,
  trigger_embedding_json TEXT,
  action_sequence TEXT,
  occurrence_count INTEGER DEFAULT 1,
  success_rate REAL DEFAULT 1.0,
  last_used INTEGER,
  project_contexts TEXT,
  auto_apply INTEGER DEFAULT 0,
  synced_to_cloud INTEGER DEFAULT 0
);

-- Knowledge artifacts cache
CREATE TABLE IF NOT EXISTS knowledge_artifacts_cache (
  id TEXT PRIMARY KEY,
  artifact_type TEXT,
  title TEXT,
  content TEXT,
  embedding BLOB,
  embedding_json TEXT,
  source_file TEXT,
  tags TEXT,
  reference_ids TEXT,
  importance_score REAL DEFAULT 0.5,
  created_at INTEGER DEFAULT (strftime('%s', 'now')),
  updated_at INTEGER DEFAULT (strftime('%s', 'now')),
  synced_to_cloud INTEGER DEFAULT 0
);

-- Embedding cache for performance
CREATE TABLE IF NOT EXISTS embedding_cache (
  text_hash TEXT PRIMARY KEY,
  embedding BLOB,
  embedding_json TEXT,
  model TEXT,
  created_at INTEGER DEFAULT (strftime('%s', 'now')),
  accessed_count INTEGER DEFAULT 1,
  last_accessed INTEGER DEFAULT (strftime('%s', 'now'))
);

-- Sync queue for cloud persistence
CREATE TABLE IF NOT EXISTS sync_queue (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  table_name TEXT NOT NULL,
  record_id TEXT NOT NULL,
  operation TEXT NOT NULL, -- INSERT, UPDATE, DELETE
  payload TEXT NOT NULL,
  created_at INTEGER DEFAULT (strftime('%s', 'now')),
  retry_count INTEGER DEFAULT 0,
  last_retry INTEGER,
  status TEXT DEFAULT 'pending' -- pending, processing, completed, failed
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_memories_project ON project_memories_cache(project_id);
CREATE INDEX IF NOT EXISTS idx_memories_created ON project_memories_cache(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memories_accessed ON project_memories_cache(last_accessed DESC);
CREATE INDEX IF NOT EXISTS idx_memories_synced ON project_memories_cache(synced_to_cloud);
CREATE INDEX IF NOT EXISTS idx_patterns_count ON workflow_patterns_cache(occurrence_count DESC);
CREATE INDEX IF NOT EXISTS idx_patterns_success ON workflow_patterns_cache(success_rate DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_type ON knowledge_artifacts_cache(artifact_type);
CREATE INDEX IF NOT EXISTS idx_knowledge_importance ON knowledge_artifacts_cache(importance_score DESC);
CREATE INDEX IF NOT EXISTS idx_embedding_hash ON embedding_cache(text_hash);
CREATE INDEX IF NOT EXISTS idx_embedding_accessed ON embedding_cache(last_accessed DESC);
CREATE INDEX IF NOT EXISTS idx_sync_status ON sync_queue(status, created_at);