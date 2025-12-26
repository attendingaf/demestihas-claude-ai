-- Initialize Demestihas AI Database Schema
-- This script runs automatically on first PostgreSQL container startup

-- Ensure database exists (note: this runs after DB creation, so primarily for documentation)
-- The database is created by Docker environment variables

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(255) PRIMARY KEY,
    chat_id VARCHAR(255) UNIQUE,
    email VARCHAR(255),
    display_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    chat_id VARCHAR(255),
    message TEXT NOT NULL,
    response TEXT,
    agent_type VARCHAR(100),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create index on user_id for faster conversation queries
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);

-- Create index on timestamp for chronological queries
CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp DESC);

-- Create index on chat_id for session-based queries
CREATE INDEX IF NOT EXISTS idx_conversations_chat_id ON conversations(chat_id);

-- Create agents table for tracking specialized agent interactions
CREATE TABLE IF NOT EXISTS agents (
    id SERIAL PRIMARY KEY,
    agent_type VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    capabilities JSONB DEFAULT '[]'::jsonb,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create agent_interactions table for detailed agent usage tracking
CREATE TABLE IF NOT EXISTS agent_interactions (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL,
    agent_type VARCHAR(100) NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    execution_time_ms INTEGER,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (agent_type) REFERENCES agents(agent_type) ON DELETE CASCADE
);

-- Create memory_snapshots table for storing mem0 backup data
CREATE TABLE IF NOT EXISTS memory_snapshots (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    memory_data JSONB NOT NULL,
    snapshot_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create knowledge_graph_cache table for storing graphiti query results
CREATE TABLE IF NOT EXISTS knowledge_graph_cache (
    id SERIAL PRIMARY KEY,
    query_hash VARCHAR(64) UNIQUE NOT NULL,
    query_text TEXT NOT NULL,
    result_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

-- Create index on knowledge graph cache expiration
CREATE INDEX IF NOT EXISTS idx_kg_cache_expires ON knowledge_graph_cache(expires_at);

-- Insert default specialized agents
INSERT INTO agents (agent_type, description, capabilities) VALUES
    ('general_agent', 'General-purpose conversational agent', '["conversation", "general_queries"]'::jsonb),
    ('code_agent', 'Specialized agent for programming and debugging', '["code_generation", "debugging", "code_review"]'::jsonb),
    ('research_agent', 'Specialized agent for research and information gathering', '["web_search", "data_analysis", "summarization"]'::jsonb),
    ('creative_agent', 'Specialized agent for creative content generation', '["writing", "storytelling", "creative_ideation"]'::jsonb),
    ('planning_agent', 'Specialized agent for task planning and organization', '["task_planning", "scheduling", "project_management"]'::jsonb)
ON CONFLICT (agent_type) DO NOTHING;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-update updated_at on users table
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default test user (optional, for development)
INSERT INTO users (id, chat_id, display_name, email) VALUES
    ('default_user', 'default_chat', 'Test User', 'test@demestihas.ai')
ON CONFLICT (id) DO NOTHING;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Demestihas AI database schema initialized successfully';
END $$;

-- Sprint 1: Session-based Conversation History
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS conversation_sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) REFERENCES users(id),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    message_count INT DEFAULT 0,
    summary TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255) REFERENCES conversation_sessions(session_id),
    user_id VARCHAR(255) REFERENCES users(id),
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    routing_agent VARCHAR(50),
    confidence_score FLOAT,
    tool_calls JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON conversation_sessions(user_id, started_at DESC);
