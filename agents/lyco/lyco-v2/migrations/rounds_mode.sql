-- Rounds Mode Migration
-- Creates tables for medical-style task review sessions

-- Rounds session tracking
CREATE TABLE IF NOT EXISTS rounds_sessions (
    id SERIAL PRIMARY KEY,
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    type VARCHAR(50) NOT NULL, -- 'morning', 'evening', 'weekly', 'emergency'
    tasks_reviewed INTEGER DEFAULT 0,
    tasks_total INTEGER DEFAULT 0,
    decisions JSONB DEFAULT '{}',
    avg_decision_time INTEGER, -- seconds per task
    energy_level VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Task categorization cache for rounds
CREATE TABLE IF NOT EXISTS task_categories (
    task_id UUID PRIMARY KEY REFERENCES tasks(id) ON DELETE CASCADE,
    energy_level VARCHAR(20),
    context VARCHAR(50),
    project VARCHAR(100),
    delegation_target VARCHAR(100),
    time_sensitivity VARCHAR(20),
    skip_count INTEGER DEFAULT 0,
    last_skipped TIMESTAMP,
    pattern_detected BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Rounds decisions log
CREATE TABLE IF NOT EXISTS rounds_decisions (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES rounds_sessions(id),
    task_id UUID REFERENCES tasks(id),
    decision VARCHAR(50), -- 'do_now', 'delegate', 'defer', 'delete'
    decision_time INTEGER, -- milliseconds
    energy_match BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Delegation signals table
CREATE TABLE IF NOT EXISTS delegation_signals (
    id SERIAL PRIMARY KEY,
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    reason TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_task_categories_energy ON task_categories(energy_level);
CREATE INDEX IF NOT EXISTS idx_task_categories_time ON task_categories(time_sensitivity);
CREATE INDEX IF NOT EXISTS idx_rounds_sessions_type ON rounds_sessions(type);
CREATE INDEX IF NOT EXISTS idx_rounds_decisions_session ON rounds_decisions(session_id);
CREATE INDEX IF NOT EXISTS idx_delegation_signals_task ON delegation_signals(task_id);

-- Add missing columns to tasks table if they don't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'tasks' AND column_name = 'parked_at') THEN
        ALTER TABLE tasks ADD COLUMN parked_at TIMESTAMP;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'tasks' AND column_name = 'rescheduled_for') THEN
        ALTER TABLE tasks ADD COLUMN rescheduled_for TIMESTAMP;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'tasks' AND column_name = 'deleted_at') THEN
        ALTER TABLE tasks ADD COLUMN deleted_at TIMESTAMP;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'tasks' AND column_name = 'skip_reason') THEN
        ALTER TABLE tasks ADD COLUMN skip_reason TEXT;
    END IF;
END $$;
