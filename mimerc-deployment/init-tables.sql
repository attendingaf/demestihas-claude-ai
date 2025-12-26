-- LangGraph PostgresSaver Schema (Corrected Version)
-- Based on actual error messages from PostgresSaver

-- Drop existing tables if they exist (for clean restart)
DROP TABLE IF EXISTS checkpoint_writes CASCADE;
DROP TABLE IF EXISTS checkpoint_blobs CASCADE;
DROP TABLE IF EXISTS checkpoints CASCADE;

-- Main checkpoints table with correct columns
CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

-- Checkpoint blobs for channel data
CREATE TABLE IF NOT EXISTS checkpoint_blobs (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    channel TEXT NOT NULL,
    version TEXT NOT NULL,
    type TEXT NOT NULL,
    blob BYTEA,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
);

-- Checkpoint writes with task_path column
CREATE TABLE IF NOT EXISTS checkpoint_writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    task_path TEXT,  -- This column was missing!
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    type TEXT,
    blob BYTEA,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_checkpoints_thread_id 
    ON checkpoints(thread_id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_created_at 
    ON checkpoints(created_at);
CREATE INDEX IF NOT EXISTS idx_checkpoint_blobs_thread 
    ON checkpoint_blobs(thread_id, checkpoint_ns);
CREATE INDEX IF NOT EXISTS idx_checkpoint_writes_thread 
    ON checkpoint_writes(thread_id, checkpoint_ns, checkpoint_id);

-- Grant permissions to mimerc user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO mimerc;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO mimerc;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'PostgresSaver tables created successfully with correct schema';
END $$;
