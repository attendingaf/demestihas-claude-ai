-- Phase 3: Skip Intelligence Database Additions
-- Run this after the main schema.sql

-- Add intelligent skip columns to tasks table
ALTER TABLE tasks 
ADD COLUMN IF NOT EXISTS rescheduled_for TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS rescheduled_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS parked_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS skip_action TEXT;

-- Skip patterns table for learning
CREATE TABLE IF NOT EXISTS skip_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_pattern TEXT NOT NULL,
    skip_reason TEXT NOT NULL,
    skip_count INTEGER DEFAULT 1,
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    auto_action TEXT,
    user_id TEXT DEFAULT 'mene@beltlineconsulting.co',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Delegation signals table
CREATE TABLE IF NOT EXISTS delegation_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    delegate_to TEXT,
    context TEXT,
    status TEXT CHECK (status IN ('pending', 'sent', 'completed')) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sent_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Weekly review items table
CREATE TABLE IF NOT EXISTS weekly_review_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    review_week DATE NOT NULL,
    status TEXT CHECK (status IN ('pending', 'keep_parked', 'activate')) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reviewed_at TIMESTAMP WITH TIME ZONE
);
