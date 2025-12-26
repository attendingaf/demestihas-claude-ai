-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Vantage Tasks Table
-- Represents the stateful items in the system.
CREATE TABLE IF NOT EXISTS vantage_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    quadrant TEXT CHECK (quadrant IN ('do_now', 'schedule', 'delegate', 'defer', 'inbox')),
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'archived')),
    owner TEXT DEFAULT 'Mene',
    deadline TIMESTAMPTZ,
    time_estimate_minutes INTEGER,
    context TEXT, -- The "Why" or detailed description
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Vantage Changelog Table
-- An immutable history of every change to a task, including the "Why".
CREATE TABLE IF NOT EXISTS vantage_changelog (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES vantage_tasks(id) ON DELETE CASCADE,
    changed_at TIMESTAMPTZ DEFAULT NOW(),
    agent_id TEXT NOT NULL, -- e.g., 'Claude', 'Lyco', 'User'
    change_type TEXT NOT NULL, -- e.g., 'move_quadrant', 'update_context', 'creation'
    previous_value JSONB, -- Snapshot of changed fields before update
    new_value JSONB, -- Snapshot of changed fields after update
    reason TEXT -- The crucial context: Why was this changed?
);

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for vantage_tasks
DROP TRIGGER IF EXISTS update_vantage_tasks_updated_at ON vantage_tasks;
CREATE TRIGGER update_vantage_tasks_updated_at
    BEFORE UPDATE ON vantage_tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_vantage_tasks_quadrant ON vantage_tasks(quadrant);
CREATE INDEX IF NOT EXISTS idx_vantage_tasks_status ON vantage_tasks(status);
CREATE INDEX IF NOT EXISTS idx_vantage_changelog_task_id ON vantage_changelog(task_id);
