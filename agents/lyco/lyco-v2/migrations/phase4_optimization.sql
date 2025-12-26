-- Phase 4: Performance Optimization Database Migration
-- Adds composite indexes and materialized views for sub-second response times

-- Composite index for optimized task fetching (most critical query)
CREATE INDEX IF NOT EXISTS idx_tasks_next_fetch
ON tasks(completed_at, skipped_at, energy_level, created_at)
WHERE completed_at IS NULL AND skipped_at IS NULL AND deleted_at IS NULL;

-- Index for rescheduled task priority
CREATE INDEX IF NOT EXISTS idx_tasks_rescheduled
ON tasks(rescheduled_for, created_at)
WHERE rescheduled_for IS NOT NULL AND completed_at IS NULL;

-- Index for energy-level based queries
CREATE INDEX IF NOT EXISTS idx_tasks_energy_active
ON tasks(energy_level, created_at)
WHERE completed_at IS NULL AND deleted_at IS NULL;

-- Index for skip pattern analysis
CREATE INDEX IF NOT EXISTS idx_tasks_skip_patterns
ON tasks(skipped_at, skipped_reason, energy_level)
WHERE skipped_at IS NOT NULL;

-- Index for delegation signals
CREATE INDEX IF NOT EXISTS idx_delegation_signals_status
ON delegation_signals(status, created_at);

-- Index for weekly review items
CREATE INDEX IF NOT EXISTS idx_weekly_review_pending
ON weekly_review_items(review_week, status)
WHERE status = 'pending';

-- Materialized view for daily metrics (refreshed periodically)
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_metrics AS
SELECT
    DATE(created_at) as date,
    COUNT(*) FILTER (WHERE completed_at IS NOT NULL) as completed,
    COUNT(*) FILTER (WHERE skipped_at IS NOT NULL) as skipped,
    COUNT(*) FILTER (WHERE completed_at IS NULL AND skipped_at IS NULL AND deleted_at IS NULL) as pending,
    AVG(EXTRACT(EPOCH FROM (completed_at - created_at))/60) FILTER (WHERE completed_at IS NOT NULL) as avg_time_to_complete,
    COUNT(*) FILTER (WHERE energy_level = 'high') as high_energy_tasks,
    COUNT(*) FILTER (WHERE energy_level = 'medium') as medium_energy_tasks,
    COUNT(*) FILTER (WHERE energy_level = 'low') as low_energy_tasks
FROM tasks
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Create unique index on materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_metrics_date
ON daily_metrics(date);

-- Materialized view for skip pattern analysis (for adaptive intelligence)
CREATE MATERIALIZED VIEW IF NOT EXISTS skip_analysis AS
SELECT
    DATE_TRUNC('week', skipped_at) as week,
    skipped_reason,
    energy_level,
    COUNT(*) as skip_count,
    AVG(time_estimate) as avg_time_estimate,
    ARRAY_AGG(DISTINCT LEFT(content, 50)) as sample_tasks
FROM tasks
WHERE skipped_at IS NOT NULL
  AND skipped_at >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY DATE_TRUNC('week', skipped_at), skipped_reason, energy_level
ORDER BY week DESC, skip_count DESC;

-- Add prompt versioning table for adaptive intelligence
CREATE TABLE IF NOT EXISTS prompt_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_name TEXT NOT NULL,
    prompt_type TEXT NOT NULL, -- 'task_processing', 'energy_assessment', etc.
    prompt_content TEXT NOT NULL,
    performance_metrics JSONB,
    is_active BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    activated_at TIMESTAMP WITH TIME ZONE,
    deactivated_at TIMESTAMP WITH TIME ZONE
);

-- Index for active prompts
CREATE INDEX IF NOT EXISTS idx_prompt_versions_active
ON prompt_versions(prompt_type, is_active, activated_at)
WHERE is_active = true;

-- Add performance metrics table
CREATE TABLE IF NOT EXISTS performance_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_type TEXT NOT NULL, -- 'response_time', 'cache_hit_rate', 'completion_rate'
    metric_value NUMERIC NOT NULL,
    measurement_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    context JSONB, -- Additional context like energy_level, hour_of_day, etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for performance metrics queries
CREATE INDEX IF NOT EXISTS idx_performance_metrics_type_time
ON performance_metrics(metric_type, measurement_time DESC);

-- Add system health monitoring table
CREATE TABLE IF NOT EXISTS system_health (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    component TEXT NOT NULL, -- 'database', 'redis', 'llm_api', 'queue_processor'
    status TEXT NOT NULL CHECK (status IN ('healthy', 'degraded', 'down')),
    response_time_ms INTEGER,
    error_message TEXT,
    last_check TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB
);

-- Unique constraint to keep only latest status per component
CREATE UNIQUE INDEX IF NOT EXISTS idx_system_health_latest
ON system_health(component);

-- Function to refresh materialized views (called by cron or background task)
CREATE OR REPLACE FUNCTION refresh_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY daily_metrics;
    REFRESH MATERIALIZED VIEW CONCURRENTLY skip_analysis;
END;
$$ LANGUAGE plpgsql;

-- Add columns for adaptive intelligence tracking
ALTER TABLE tasks
ADD COLUMN IF NOT EXISTS prompt_version TEXT,
ADD COLUMN IF NOT EXISTS processing_time_ms INTEGER,
ADD COLUMN IF NOT EXISTS confidence_score NUMERIC(3,2);

-- Add weekly insights generation tracking
CREATE TABLE IF NOT EXISTS weekly_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    week_start DATE NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    insights_data JSONB NOT NULL,
    email_sent BOOLEAN DEFAULT false,
    email_sent_at TIMESTAMP WITH TIME ZONE,
    user_feedback TEXT,
    feedback_received_at TIMESTAMP WITH TIME ZONE
);

-- Index for weekly insights
CREATE INDEX IF NOT EXISTS idx_weekly_insights_week
ON weekly_insights(week_start DESC);

-- Performance optimization: Partial indexes for common WHERE clauses
CREATE INDEX IF NOT EXISTS idx_tasks_active_today
ON tasks(created_at DESC)
WHERE completed_at IS NULL
  AND skipped_at IS NULL
  AND deleted_at IS NULL
  AND DATE(created_at) = CURRENT_DATE;

CREATE INDEX IF NOT EXISTS idx_tasks_completed_today
ON tasks(completed_at DESC)
WHERE completed_at IS NOT NULL
  AND DATE(completed_at) = CURRENT_DATE;

-- Add cache invalidation triggers (for Redis cache management)
CREATE OR REPLACE FUNCTION notify_cache_invalidation()
RETURNS trigger AS $$
BEGIN
    PERFORM pg_notify('cache_invalidate', json_build_object(
        'table', TG_TABLE_NAME,
        'operation', TG_OP,
        'id', COALESCE(NEW.id, OLD.id)
    )::text);
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Add triggers for cache invalidation
DROP TRIGGER IF EXISTS tasks_cache_invalidation ON tasks;
CREATE TRIGGER tasks_cache_invalidation
    AFTER INSERT OR UPDATE OR DELETE ON tasks
    FOR EACH ROW EXECUTE FUNCTION notify_cache_invalidation();

-- Grant necessary permissions
GRANT SELECT ON daily_metrics TO PUBLIC;
GRANT SELECT ON skip_analysis TO PUBLIC;
