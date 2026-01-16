-- Migration: 003_granular_analytics.sql
-- Description: Add granular analytics columns for CES, escalation, handle time, etc.
-- Date: 2026-01-15

-- ========================================
-- ADD NEW COLUMNS TO supportiq_call_analytics
-- ========================================

-- Customer Effort Score
ALTER TABLE supportiq_call_analytics ADD COLUMN IF NOT EXISTS customer_effort_score INTEGER DEFAULT 3;
ALTER TABLE supportiq_call_analytics ADD COLUMN IF NOT EXISTS customer_had_to_repeat BOOLEAN DEFAULT FALSE;
ALTER TABLE supportiq_call_analytics ADD COLUMN IF NOT EXISTS transfer_count INTEGER DEFAULT 0;

-- Escalation tracking
ALTER TABLE supportiq_call_analytics ADD COLUMN IF NOT EXISTS was_escalated BOOLEAN DEFAULT FALSE;
ALTER TABLE supportiq_call_analytics ADD COLUMN IF NOT EXISTS escalation_reason TEXT;
ALTER TABLE supportiq_call_analytics ADD COLUMN IF NOT EXISTS escalation_level VARCHAR(50);
ALTER TABLE supportiq_call_analytics ADD COLUMN IF NOT EXISTS escalation_resolved BOOLEAN;
ALTER TABLE supportiq_call_analytics ADD COLUMN IF NOT EXISTS escalated_to_department VARCHAR(100);

-- Handle time breakdown (stored as JSONB for flexibility)
ALTER TABLE supportiq_call_analytics ADD COLUMN IF NOT EXISTS handle_time_breakdown JSONB DEFAULT '{}';

-- Conversation quality metrics (stored as JSONB)
ALTER TABLE supportiq_call_analytics ADD COLUMN IF NOT EXISTS conversation_quality JSONB DEFAULT '{}';

-- Competitive intelligence (stored as JSONB)
ALTER TABLE supportiq_call_analytics ADD COLUMN IF NOT EXISTS competitive_intelligence JSONB DEFAULT '{}';

-- Product analytics (stored as JSONB)
ALTER TABLE supportiq_call_analytics ADD COLUMN IF NOT EXISTS product_analytics JSONB DEFAULT '{}';

-- Time-based metadata
ALTER TABLE supportiq_call_analytics ADD COLUMN IF NOT EXISTS call_hour INTEGER;
ALTER TABLE supportiq_call_analytics ADD COLUMN IF NOT EXISTS call_day_of_week VARCHAR(10);
ALTER TABLE supportiq_call_analytics ADD COLUMN IF NOT EXISTS is_peak_hour BOOLEAN DEFAULT FALSE;

-- ========================================
-- ADD NEW COLUMNS TO supportiq_agent_performance
-- ========================================

ALTER TABLE supportiq_agent_performance ADD COLUMN IF NOT EXISTS talk_time_seconds INTEGER DEFAULT 0;
ALTER TABLE supportiq_agent_performance ADD COLUMN IF NOT EXISTS hold_time_seconds INTEGER DEFAULT 0;
ALTER TABLE supportiq_agent_performance ADD COLUMN IF NOT EXISTS escalations_initiated INTEGER DEFAULT 0;

-- ========================================
-- ADD NEW COLUMNS TO supportiq_customer_profiles
-- ========================================

ALTER TABLE supportiq_customer_profiles ADD COLUMN IF NOT EXISTS avg_customer_effort_score FLOAT;
ALTER TABLE supportiq_customer_profiles ADD COLUMN IF NOT EXISTS total_escalations INTEGER DEFAULT 0;
ALTER TABLE supportiq_customer_profiles ADD COLUMN IF NOT EXISTS first_contact_resolution_rate FLOAT;

-- ========================================
-- CREATE FCR TRACKING TABLE
-- ========================================

CREATE TABLE IF NOT EXISTS supportiq_fcr_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id UUID REFERENCES supportiq_voice_calls(id) ON DELETE CASCADE,
    customer_identifier VARCHAR(255),
    issue_category VARCHAR(100),
    resolved_on_first_contact BOOLEAN DEFAULT FALSE,
    follow_up_call_id UUID REFERENCES supportiq_voice_calls(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- CREATE HOURLY ANALYTICS TABLE
-- ========================================

CREATE TABLE IF NOT EXISTS supportiq_hourly_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    date DATE NOT NULL,
    hour INTEGER NOT NULL CHECK (hour >= 0 AND hour <= 23),
    call_count INTEGER DEFAULT 0,
    avg_duration_seconds FLOAT,
    avg_sentiment_score FLOAT,
    avg_effort_score FLOAT,
    escalation_count INTEGER DEFAULT 0,
    resolution_rate FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, date, hour)
);

-- ========================================
-- CREATE INDEXES FOR PERFORMANCE
-- ========================================

-- Customer effort score queries
CREATE INDEX IF NOT EXISTS idx_call_analytics_effort ON supportiq_call_analytics(customer_effort_score);

-- Escalation queries
CREATE INDEX IF NOT EXISTS idx_call_analytics_escalated ON supportiq_call_analytics(was_escalated);

-- Time-based analytics queries
CREATE INDEX IF NOT EXISTS idx_call_analytics_hour ON supportiq_call_analytics(call_hour);
CREATE INDEX IF NOT EXISTS idx_call_analytics_dow ON supportiq_call_analytics(call_day_of_week);

-- Hourly analytics lookups
CREATE INDEX IF NOT EXISTS idx_hourly_analytics_date ON supportiq_hourly_analytics(date, hour);
CREATE INDEX IF NOT EXISTS idx_hourly_analytics_user_date ON supportiq_hourly_analytics(user_id, date);

-- FCR tracking lookups
CREATE INDEX IF NOT EXISTS idx_fcr_customer ON supportiq_fcr_tracking(customer_identifier);
CREATE INDEX IF NOT EXISTS idx_fcr_call ON supportiq_fcr_tracking(call_id);

-- ========================================
-- COMMENT ON NEW COLUMNS
-- ========================================

COMMENT ON COLUMN supportiq_call_analytics.customer_effort_score IS 'Customer effort score 1-5 (1=effortless, 5=very high effort)';
COMMENT ON COLUMN supportiq_call_analytics.handle_time_breakdown IS 'JSONB containing talk_time, hold_time, silence_time, percentages';
COMMENT ON COLUMN supportiq_call_analytics.conversation_quality IS 'JSONB containing clarity_score, empathy_count, jargon_count, etc.';
COMMENT ON COLUMN supportiq_call_analytics.competitive_intelligence IS 'JSONB containing competitor mentions, switching intent, price sensitivity';
COMMENT ON COLUMN supportiq_call_analytics.product_analytics IS 'JSONB containing products discussed, features requested/problematic, upsell opportunities';
COMMENT ON TABLE supportiq_fcr_tracking IS 'Tracks first contact resolution by linking follow-up calls to original issues';
COMMENT ON TABLE supportiq_hourly_analytics IS 'Pre-aggregated hourly analytics for time-based reporting';
