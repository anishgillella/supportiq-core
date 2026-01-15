-- SupportIQ Enhanced Analytics Schema
-- Migration: 002_enhanced_analytics.sql
-- Run this in your Supabase SQL Editor after 001_voice_calls.sql

-- ===========================================
-- CUSTOMER PROFILES TABLE
-- Tracks customers across multiple calls
-- ===========================================

CREATE TABLE IF NOT EXISTS public.supportiq_customer_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- User association (multi-tenant)
  user_id UUID REFERENCES public.supportiq_users(id),

  -- Contact Information
  name VARCHAR(255),
  email VARCHAR(255),
  phone VARCHAR(50),
  account_id VARCHAR(100),
  company VARCHAR(255),

  -- Customer Classification
  customer_type VARCHAR(50) DEFAULT 'unknown', -- new, returning, vip, at_risk
  communication_style VARCHAR(50) DEFAULT 'neutral', -- formal, casual, technical, emotional
  language_preference VARCHAR(10) DEFAULT 'en',

  -- Engagement Metrics
  total_calls INTEGER DEFAULT 0,
  total_call_duration_seconds INTEGER DEFAULT 0,
  first_call_at TIMESTAMPTZ,
  last_call_at TIMESTAMPTZ,

  -- Satisfaction Metrics
  avg_satisfaction_score FLOAT DEFAULT 0.0,
  avg_sentiment_score FLOAT DEFAULT 0.0,

  -- Churn Risk
  churn_risk_level VARCHAR(20) DEFAULT 'low', -- low, medium, high
  churn_risk_score FLOAT DEFAULT 0.0,
  churn_risk_factors TEXT[],

  -- Aggregated Feedback
  pain_points TEXT[],
  feature_requests TEXT[],
  complaints TEXT[],
  compliments TEXT[],

  -- Products & Context
  products_mentioned TEXT[],
  competitor_mentions TEXT[],

  -- Follow-up Tracking
  requires_follow_up BOOLEAN DEFAULT FALSE,
  follow_up_reason TEXT,
  follow_up_deadline TIMESTAMPTZ,

  -- Special Notes
  special_notes TEXT[],
  tags TEXT[],

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),

  -- Unique constraint for user + identifier combinations
  UNIQUE(user_id, email),
  UNIQUE(user_id, phone),
  UNIQUE(user_id, account_id)
);

-- ===========================================
-- ENHANCED CALL ANALYTICS TABLE
-- Add more fields to existing table
-- ===========================================

-- Add new columns to supportiq_call_analytics
ALTER TABLE public.supportiq_call_analytics
ADD COLUMN IF NOT EXISTS tags TEXT[],
ADD COLUMN IF NOT EXISTS resolution_notes TEXT,
ADD COLUMN IF NOT EXISTS nps_predicted INTEGER,
ADD COLUMN IF NOT EXISTS questions_asked TEXT[],
ADD COLUMN IF NOT EXISTS questions_unanswered TEXT[],
ADD COLUMN IF NOT EXISTS commitments_made TEXT[],
ADD COLUMN IF NOT EXISTS knowledge_gaps TEXT[],
ADD COLUMN IF NOT EXISTS one_line_summary TEXT,
ADD COLUMN IF NOT EXISTS customer_profile_id UUID REFERENCES public.supportiq_customer_profiles(id);

-- ===========================================
-- AGENT PERFORMANCE TABLE
-- Detailed agent metrics per call
-- ===========================================

CREATE TABLE IF NOT EXISTS public.supportiq_agent_performance (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  call_id UUID REFERENCES public.supportiq_voice_calls(id) ON DELETE CASCADE UNIQUE,

  -- Overall Score
  overall_score FLOAT DEFAULT 0.0,

  -- Detailed Scores (0-100)
  empathy_score FLOAT DEFAULT 0.0,
  knowledge_score FLOAT DEFAULT 0.0,
  communication_score FLOAT DEFAULT 0.0,
  efficiency_score FLOAT DEFAULT 0.0,

  -- Conversation Flow Metrics
  opening_quality FLOAT DEFAULT 0.0,
  closing_quality FLOAT DEFAULT 0.0,
  problem_identification_time_seconds FLOAT,
  resolution_time_seconds FLOAT,
  dead_air_seconds FLOAT DEFAULT 0.0,
  interruptions_count INTEGER DEFAULT 0,

  -- Qualitative Feedback
  strengths TEXT[],
  areas_for_improvement TEXT[],
  training_recommendations TEXT[],

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ===========================================
-- CUSTOMER FEEDBACK AGGREGATION TABLE
-- For cumulative insights
-- ===========================================

CREATE TABLE IF NOT EXISTS public.supportiq_feedback_aggregation (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES public.supportiq_users(id),

  -- Feedback Item
  feedback_type VARCHAR(50) NOT NULL, -- pain_point, feature_request, complaint, compliment
  feedback_text TEXT NOT NULL,

  -- Occurrence Tracking
  occurrence_count INTEGER DEFAULT 1,
  first_mentioned_at TIMESTAMPTZ DEFAULT NOW(),
  last_mentioned_at TIMESTAMPTZ DEFAULT NOW(),

  -- Associated Calls
  call_ids UUID[],

  -- Metadata
  category VARCHAR(100),
  tags TEXT[],

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),

  UNIQUE(user_id, feedback_type, feedback_text)
);

-- ===========================================
-- ANALYTICS SUMMARY TABLE
-- Pre-computed cumulative stats
-- ===========================================

CREATE TABLE IF NOT EXISTS public.supportiq_analytics_summary (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES public.supportiq_users(id),

  -- Time Period
  period_type VARCHAR(20) NOT NULL, -- daily, weekly, monthly, all_time
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,

  -- Call Volume
  total_calls INTEGER DEFAULT 0,
  completed_calls INTEGER DEFAULT 0,
  abandoned_calls INTEGER DEFAULT 0,
  escalated_calls INTEGER DEFAULT 0,

  -- Duration Metrics
  total_duration_seconds INTEGER DEFAULT 0,
  avg_duration_seconds FLOAT DEFAULT 0.0,
  min_duration_seconds INTEGER,
  max_duration_seconds INTEGER,

  -- Resolution Metrics
  resolved_calls INTEGER DEFAULT 0,
  first_call_resolution_count INTEGER DEFAULT 0,
  resolution_rate FLOAT DEFAULT 0.0,
  first_call_resolution_rate FLOAT DEFAULT 0.0,

  -- Sentiment Metrics
  positive_calls INTEGER DEFAULT 0,
  neutral_calls INTEGER DEFAULT 0,
  negative_calls INTEGER DEFAULT 0,
  mixed_calls INTEGER DEFAULT 0,
  avg_sentiment_score FLOAT DEFAULT 0.0,

  -- Customer Satisfaction
  avg_csat_score FLOAT DEFAULT 0.0,
  avg_nps_score FLOAT DEFAULT 0.0,

  -- Agent Performance
  avg_agent_score FLOAT DEFAULT 0.0,

  -- Customer Risk
  high_risk_customer_count INTEGER DEFAULT 0,
  avg_churn_risk_score FLOAT DEFAULT 0.0,

  -- Category Breakdown (JSONB)
  category_breakdown JSONB DEFAULT '{}',

  -- Top Items (JSONB arrays)
  top_pain_points JSONB DEFAULT '[]',
  top_feature_requests JSONB DEFAULT '[]',
  top_complaints JSONB DEFAULT '[]',
  top_knowledge_gaps JSONB DEFAULT '[]',

  -- Comparison Metrics
  calls_change_percent FLOAT DEFAULT 0.0,
  resolution_change_percent FLOAT DEFAULT 0.0,
  sentiment_change_percent FLOAT DEFAULT 0.0,

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),

  UNIQUE(user_id, period_type, period_start)
);

-- ===========================================
-- INDEXES
-- ===========================================

-- Customer Profiles
CREATE INDEX IF NOT EXISTS idx_customer_profiles_user ON public.supportiq_customer_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_customer_profiles_email ON public.supportiq_customer_profiles(user_id, email);
CREATE INDEX IF NOT EXISTS idx_customer_profiles_phone ON public.supportiq_customer_profiles(user_id, phone);
CREATE INDEX IF NOT EXISTS idx_customer_profiles_churn_risk ON public.supportiq_customer_profiles(churn_risk_level);
CREATE INDEX IF NOT EXISTS idx_customer_profiles_type ON public.supportiq_customer_profiles(customer_type);

-- Agent Performance
CREATE INDEX IF NOT EXISTS idx_agent_perf_call ON public.supportiq_agent_performance(call_id);
CREATE INDEX IF NOT EXISTS idx_agent_perf_score ON public.supportiq_agent_performance(overall_score DESC);

-- Feedback Aggregation
CREATE INDEX IF NOT EXISTS idx_feedback_user ON public.supportiq_feedback_aggregation(user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_type ON public.supportiq_feedback_aggregation(feedback_type);
CREATE INDEX IF NOT EXISTS idx_feedback_count ON public.supportiq_feedback_aggregation(occurrence_count DESC);

-- Analytics Summary
CREATE INDEX IF NOT EXISTS idx_summary_user_period ON public.supportiq_analytics_summary(user_id, period_type, period_start DESC);

-- ===========================================
-- TRIGGERS
-- ===========================================

-- Customer profiles update trigger
DROP TRIGGER IF EXISTS update_customer_profiles_updated_at ON public.supportiq_customer_profiles;
CREATE TRIGGER update_customer_profiles_updated_at
    BEFORE UPDATE ON public.supportiq_customer_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Feedback aggregation update trigger
DROP TRIGGER IF EXISTS update_feedback_aggregation_updated_at ON public.supportiq_feedback_aggregation;
CREATE TRIGGER update_feedback_aggregation_updated_at
    BEFORE UPDATE ON public.supportiq_feedback_aggregation
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Analytics summary update trigger
DROP TRIGGER IF EXISTS update_analytics_summary_updated_at ON public.supportiq_analytics_summary;
CREATE TRIGGER update_analytics_summary_updated_at
    BEFORE UPDATE ON public.supportiq_analytics_summary
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ===========================================
-- PERMISSIONS
-- ===========================================

GRANT ALL ON TABLE public.supportiq_customer_profiles TO service_role, anon, authenticated;
GRANT ALL ON TABLE public.supportiq_agent_performance TO service_role, anon, authenticated;
GRANT ALL ON TABLE public.supportiq_feedback_aggregation TO service_role, anon, authenticated;
GRANT ALL ON TABLE public.supportiq_analytics_summary TO service_role, anon, authenticated;

-- Disable RLS for demo (enable in production with proper policies)
ALTER TABLE public.supportiq_customer_profiles DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.supportiq_agent_performance DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.supportiq_feedback_aggregation DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.supportiq_analytics_summary DISABLE ROW LEVEL SECURITY;

-- ===========================================
-- VERIFICATION
-- ===========================================

DO $$
BEGIN
  RAISE NOTICE 'Enhanced analytics tables created successfully!';
  RAISE NOTICE 'New tables: supportiq_customer_profiles, supportiq_agent_performance, supportiq_feedback_aggregation, supportiq_analytics_summary';
  RAISE NOTICE 'Enhanced: supportiq_call_analytics with new columns';
END $$;
