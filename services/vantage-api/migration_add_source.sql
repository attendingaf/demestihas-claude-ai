-- Add source_ref column to track external IDs (e.g., Google Task ID)
ALTER TABLE vantage_tasks 
ADD COLUMN IF NOT EXISTS source_ref TEXT;

-- Create index for faster lookups during sync
CREATE INDEX IF NOT EXISTS idx_vantage_tasks_source_ref ON vantage_tasks(source_ref);
