-- SupportIQ Voice Agent Database Schema
-- Run this in your Supabase SQL Editor
-- Migration: 001_voice_calls.sql

-- ===========================================
-- VOICE CALLS TABLE
-- ===========================================

CREATE TABLE IF NOT EXISTS public.supportiq_voice_calls (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- VAPI identifiers
  vapi_call_id VARCHAR(255) UNIQUE NOT NULL,
  vapi_assistant_id VARCHAR(255),

  -- Call metadata
  caller_phone VARCHAR(50),
  caller_id UUID REFERENCES public.supportiq_users(id),

  -- Call timing
  started_at TIMESTAMPTZ NOT NULL,
  ended_at TIMESTAMPTZ,
  duration_seconds INTEGER,

  -- Call status: 'in_progress', 'completed', 'abandoned', 'failed', 'transferred'
  status VARCHAR(50) NOT NULL DEFAULT 'in_progress',

  -- Agent info (for multi-agent future)
  agent_type VARCHAR(50) DEFAULT 'general',

  -- Recording
  recording_url TEXT,

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ===========================================
-- CALL TRANSCRIPTS TABLE
-- ===========================================

CREATE TABLE IF NOT EXISTS public.supportiq_call_transcripts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  call_id UUID REFERENCES public.supportiq_voice_calls(id) ON DELETE CASCADE UNIQUE,

  -- Transcript content as JSON array
  -- Format: [{"role": "agent", "content": "...", "timestamp": 0.0}, ...]
  transcript JSONB NOT NULL DEFAULT '[]',

  -- Raw VAPI response for debugging
  raw_vapi_response JSONB,

  -- Stats
  word_count INTEGER,
  turn_count INTEGER,

  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ===========================================
-- CALL ANALYTICS TABLE
-- ===========================================

CREATE TABLE IF NOT EXISTS public.supportiq_call_analytics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  call_id UUID REFERENCES public.supportiq_voice_calls(id) ON DELETE CASCADE UNIQUE,

  -- Sentiment Analysis
  overall_sentiment VARCHAR(20) NOT NULL,
  sentiment_score FLOAT,
  sentiment_progression JSONB,

  -- Issue Classification
  primary_category VARCHAR(100),
  secondary_categories TEXT[],

  -- Resolution Status: 'resolved', 'partially_resolved', 'unresolved', 'escalated', 'follow_up_needed'
  resolution_status VARCHAR(50) NOT NULL,

  -- Quality Metrics
  customer_satisfaction_predicted FLOAT,
  agent_performance_score FLOAT,

  -- Extracted Information
  customer_intent TEXT,
  key_topics TEXT[],
  action_items TEXT[],

  -- AI Suggestions
  improvement_suggestions TEXT[],

  -- Summary
  call_summary TEXT,

  -- Analysis metadata
  analyzed_at TIMESTAMPTZ DEFAULT NOW(),
  analysis_model VARCHAR(100),
  analysis_version VARCHAR(20) DEFAULT '1.0'
);

-- ===========================================
-- DAILY ANALYTICS TABLE (Aggregated Stats)
-- ===========================================

CREATE TABLE IF NOT EXISTS public.supportiq_analytics_daily (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Date partition
  date DATE NOT NULL,
  user_id UUID REFERENCES public.supportiq_users(id),

  -- Call volume
  total_calls INTEGER DEFAULT 0,
  completed_calls INTEGER DEFAULT 0,
  abandoned_calls INTEGER DEFAULT 0,

  -- Duration
  total_duration_seconds INTEGER DEFAULT 0,
  avg_duration_seconds FLOAT DEFAULT 0,

  -- Resolution
  resolved_calls INTEGER DEFAULT 0,
  escalated_calls INTEGER DEFAULT 0,
  resolution_rate FLOAT DEFAULT 0,

  -- Sentiment
  positive_calls INTEGER DEFAULT 0,
  neutral_calls INTEGER DEFAULT 0,
  negative_calls INTEGER DEFAULT 0,
  avg_sentiment_score FLOAT DEFAULT 0,

  -- Categories breakdown
  category_breakdown JSONB DEFAULT '{}',

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),

  UNIQUE(date, user_id)
);

-- ===========================================
-- INDEXES
-- ===========================================

CREATE INDEX IF NOT EXISTS idx_voice_calls_vapi_id ON public.supportiq_voice_calls(vapi_call_id);
CREATE INDEX IF NOT EXISTS idx_voice_calls_status ON public.supportiq_voice_calls(status);
CREATE INDEX IF NOT EXISTS idx_voice_calls_started_at ON public.supportiq_voice_calls(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_voice_calls_caller ON public.supportiq_voice_calls(caller_id);
CREATE INDEX IF NOT EXISTS idx_voice_calls_agent_type ON public.supportiq_voice_calls(agent_type);

CREATE INDEX IF NOT EXISTS idx_transcripts_call_id ON public.supportiq_call_transcripts(call_id);

CREATE INDEX IF NOT EXISTS idx_analytics_call_id ON public.supportiq_call_analytics(call_id);
CREATE INDEX IF NOT EXISTS idx_analytics_category ON public.supportiq_call_analytics(primary_category);
CREATE INDEX IF NOT EXISTS idx_analytics_sentiment ON public.supportiq_call_analytics(overall_sentiment);
CREATE INDEX IF NOT EXISTS idx_analytics_resolution ON public.supportiq_call_analytics(resolution_status);

CREATE INDEX IF NOT EXISTS idx_daily_date ON public.supportiq_analytics_daily(date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_user ON public.supportiq_analytics_daily(user_id, date DESC);

-- ===========================================
-- TRIGGERS
-- ===========================================

-- Reuse existing function if it exists
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Voice calls trigger
DROP TRIGGER IF EXISTS update_voice_calls_updated_at ON public.supportiq_voice_calls;
CREATE TRIGGER update_voice_calls_updated_at
    BEFORE UPDATE ON public.supportiq_voice_calls
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Daily analytics trigger
DROP TRIGGER IF EXISTS update_analytics_daily_updated_at ON public.supportiq_analytics_daily;
CREATE TRIGGER update_analytics_daily_updated_at
    BEFORE UPDATE ON public.supportiq_analytics_daily
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ===========================================
-- PERMISSIONS
-- ===========================================

GRANT ALL ON TABLE public.supportiq_voice_calls TO service_role, anon, authenticated;
GRANT ALL ON TABLE public.supportiq_call_transcripts TO service_role, anon, authenticated;
GRANT ALL ON TABLE public.supportiq_call_analytics TO service_role, anon, authenticated;
GRANT ALL ON TABLE public.supportiq_analytics_daily TO service_role, anon, authenticated;

-- Disable RLS for demo (enable in production with proper policies)
ALTER TABLE public.supportiq_voice_calls DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.supportiq_call_transcripts DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.supportiq_call_analytics DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.supportiq_analytics_daily DISABLE ROW LEVEL SECURITY;

-- ===========================================
-- VERIFICATION
-- ===========================================

-- Check tables were created
DO $$
BEGIN
  RAISE NOTICE 'Voice tables created successfully!';
  RAISE NOTICE 'Tables: supportiq_voice_calls, supportiq_call_transcripts, supportiq_call_analytics, supportiq_analytics_daily';
END $$;
