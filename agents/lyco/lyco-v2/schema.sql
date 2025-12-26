-- Lyco 2.0 Database Schema for Supabase
-- Run this in the Supabase SQL editor to create the tables

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop existing tables if they exist (for clean setup)
DROP TABLE IF EXISTS tasks CASCADE;
DROP TABLE IF EXISTS task_signals CASCADE;

-- Signals: Raw capture from reality
CREATE TABLE task_signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source TEXT NOT NULL CHECK (source IN ('gmail', 'calendar', 'slack', 'pluma', 'huata', 'manual', 'test')),
  raw_content TEXT NOT NULL,
  processed BOOLEAN DEFAULT FALSE,
  processor_version TEXT DEFAULT '2.0.0',
  confidence_score FLOAT DEFAULT 0,
  timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  metadata JSONB DEFAULT '{}',
  user_id TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tasks: Processed, actionable items
CREATE TABLE tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  signal_id UUID REFERENCES task_signals(id) ON DELETE SET NULL,
  content TEXT NOT NULL,
  next_action TEXT NOT NULL, -- Single concrete micro-step
  energy_level TEXT CHECK (energy_level IN ('high', 'medium', 'low', 'any')) DEFAULT 'any',
  time_estimate INTEGER DEFAULT 15, -- minutes
  context_required JSONB DEFAULT '[]',
  deadline TIMESTAMP WITH TIME ZONE,
  completed_at TIMESTAMP WITH TIME ZONE,
  skipped_at TIMESTAMP WITH TIME ZONE,
  skipped_reason TEXT, -- Critical for learning
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_tasks_pending ON tasks(completed_at, skipped_at)
  WHERE completed_at IS NULL AND skipped_at IS NULL;
CREATE INDEX idx_signals_unprocessed ON task_signals(processed)
  WHERE processed = FALSE;
CREATE INDEX idx_tasks_energy ON tasks(energy_level)
  WHERE completed_at IS NULL AND skipped_at IS NULL;
CREATE INDEX idx_tasks_created ON tasks(created_at DESC);
CREATE INDEX idx_signals_source ON task_signals(source);
CREATE INDEX idx_signals_timestamp ON task_signals(timestamp DESC);

-- Row Level Security (RLS)
ALTER TABLE task_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

-- Policies for task_signals
CREATE POLICY "Enable all access for authenticated users" ON task_signals
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- Policies for tasks
CREATE POLICY "Enable all access for authenticated users" ON tasks
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at
CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Views for analytics (optional but useful)

-- View for pending tasks
CREATE OR REPLACE VIEW pending_tasks AS
SELECT
  id,
  content,
  next_action,
  energy_level,
  time_estimate,
  context_required,
  deadline,
  created_at,
  EXTRACT(EPOCH FROM (NOW() - created_at))/3600 as hours_pending
FROM tasks
WHERE completed_at IS NULL AND skipped_at IS NULL
ORDER BY deadline ASC NULLS LAST, created_at ASC;

-- View for task completion stats
CREATE OR REPLACE VIEW task_stats AS
SELECT
  DATE(created_at) as date,
  COUNT(*) as total_tasks,
  COUNT(completed_at) as completed_tasks,
  COUNT(skipped_at) as skipped_tasks,
  AVG(EXTRACT(EPOCH FROM (COALESCE(completed_at, skipped_at) - created_at))/60) as avg_time_to_action_minutes,
  COUNT(CASE WHEN energy_level = 'high' THEN 1 END) as high_energy_tasks,
  COUNT(CASE WHEN energy_level = 'medium' THEN 1 END) as medium_energy_tasks,
  COUNT(CASE WHEN energy_level = 'low' THEN 1 END) as low_energy_tasks
FROM tasks
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- View for skip reason analysis
CREATE OR REPLACE VIEW skip_analysis AS
SELECT
  skipped_reason,
  COUNT(*) as count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM tasks
WHERE skipped_at IS NOT NULL
GROUP BY skipped_reason
ORDER BY count DESC;

-- Sample data for testing (optional)
-- INSERT INTO task_signals (source, raw_content) VALUES
--   ('manual', 'Send Q3 report to the board by Friday'),
--   ('manual', 'Review patient outcome metrics'),
--   ('manual', 'Schedule 1:1 with Dr. Johnson about new protocol');

-- Grant permissions (adjust based on your Supabase setup)
GRANT ALL ON task_signals TO authenticated;
GRANT ALL ON tasks TO authenticated;
GRANT SELECT ON pending_tasks TO authenticated;
GRANT SELECT ON task_stats TO authenticated;
GRANT SELECT ON skip_analysis TO authenticated;
