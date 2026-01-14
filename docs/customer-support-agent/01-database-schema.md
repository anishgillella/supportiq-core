# Phase 1: Database Schema

## Overview

This document defines the database tables needed for the voice agent feature. All tables use the `supportiq_` prefix to avoid conflicts with other applications.

## New Tables

### 1. `supportiq_voice_calls`

Stores metadata for each voice call.

```sql
CREATE TABLE public.supportiq_voice_calls (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- VAPI identifiers
  vapi_call_id VARCHAR(255) UNIQUE NOT NULL,
  vapi_assistant_id VARCHAR(255),

  -- Call metadata
  caller_phone VARCHAR(50),           -- Phone number if available
  caller_id UUID REFERENCES public.supportiq_users(id), -- Linked user if authenticated

  -- Call timing
  started_at TIMESTAMPTZ NOT NULL,
  ended_at TIMESTAMPTZ,
  duration_seconds INTEGER,           -- Call duration in seconds

  -- Call status
  status VARCHAR(50) NOT NULL DEFAULT 'in_progress',
  -- Possible values: 'in_progress', 'completed', 'abandoned', 'failed', 'transferred'

  -- Agent info (for multi-agent future)
  agent_type VARCHAR(50) DEFAULT 'general',
  -- Possible values: 'general', 'billing', 'technical', 'sales'

  -- Recording (if enabled)
  recording_url TEXT,

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 2. `supportiq_call_transcripts`

Stores the full transcript of each call.

```sql
CREATE TABLE public.supportiq_call_transcripts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  call_id UUID REFERENCES public.supportiq_voice_calls(id) ON DELETE CASCADE UNIQUE,

  -- Transcript content
  transcript JSONB NOT NULL DEFAULT '[]',
  -- Format: [
  --   {"role": "agent", "content": "Hello, how can I help?", "timestamp": 0.0},
  --   {"role": "customer", "content": "I have a billing question", "timestamp": 2.5},
  --   ...
  -- ]

  -- Raw VAPI response (for debugging)
  raw_vapi_response JSONB,

  -- Word count and summary stats
  word_count INTEGER,
  turn_count INTEGER,

  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3. `supportiq_call_analytics`

Stores AI-generated analysis of each call.

```sql
CREATE TABLE public.supportiq_call_analytics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  call_id UUID REFERENCES public.supportiq_voice_calls(id) ON DELETE CASCADE UNIQUE,

  -- Sentiment Analysis
  overall_sentiment VARCHAR(20) NOT NULL,
  -- Possible values: 'positive', 'neutral', 'negative', 'mixed'
  sentiment_score FLOAT,              -- -1.0 to 1.0
  sentiment_progression JSONB,        -- [{"timestamp": 0, "sentiment": "neutral"}, ...]

  -- Issue Classification
  primary_category VARCHAR(100),
  -- Examples: 'billing', 'technical_support', 'account_access', 'product_inquiry', 'complaint', 'feedback'
  secondary_categories TEXT[],

  -- Resolution Status
  resolution_status VARCHAR(50) NOT NULL,
  -- Possible values: 'resolved', 'partially_resolved', 'unresolved', 'escalated', 'follow_up_needed'

  -- Call Quality Metrics
  customer_satisfaction_predicted FLOAT,  -- 1-5 scale prediction
  agent_performance_score FLOAT,          -- 1-100 scale

  -- Key Information Extracted
  customer_intent TEXT,               -- What did the customer want?
  key_topics TEXT[],                  -- Main topics discussed
  action_items TEXT[],                -- Any follow-ups needed

  -- AI Improvement Suggestions
  improvement_suggestions TEXT[],

  -- Summary
  call_summary TEXT,                  -- 2-3 sentence summary

  -- Analysis metadata
  analyzed_at TIMESTAMPTZ DEFAULT NOW(),
  analysis_model VARCHAR(100),        -- Which LLM was used
  analysis_version VARCHAR(20) DEFAULT '1.0'
);
```

### 4. `supportiq_analytics_daily` (Aggregated Stats)

Pre-computed daily statistics for dashboard performance.

```sql
CREATE TABLE public.supportiq_analytics_daily (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Date partition
  date DATE NOT NULL,
  user_id UUID REFERENCES public.supportiq_users(id), -- NULL for system-wide stats

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

  -- Categories breakdown (JSON for flexibility)
  category_breakdown JSONB DEFAULT '{}',
  -- Format: {"billing": 10, "technical": 5, "general": 15}

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),

  UNIQUE(date, user_id)
);
```

## Indexes

```sql
-- Voice calls indexes
CREATE INDEX idx_voice_calls_vapi_id ON public.supportiq_voice_calls(vapi_call_id);
CREATE INDEX idx_voice_calls_status ON public.supportiq_voice_calls(status);
CREATE INDEX idx_voice_calls_started_at ON public.supportiq_voice_calls(started_at DESC);
CREATE INDEX idx_voice_calls_caller ON public.supportiq_voice_calls(caller_id);
CREATE INDEX idx_voice_calls_agent_type ON public.supportiq_voice_calls(agent_type);

-- Transcripts indexes
CREATE INDEX idx_transcripts_call_id ON public.supportiq_call_transcripts(call_id);

-- Analytics indexes
CREATE INDEX idx_analytics_call_id ON public.supportiq_call_analytics(call_id);
CREATE INDEX idx_analytics_category ON public.supportiq_call_analytics(primary_category);
CREATE INDEX idx_analytics_sentiment ON public.supportiq_call_analytics(overall_sentiment);
CREATE INDEX idx_analytics_resolution ON public.supportiq_call_analytics(resolution_status);

-- Daily analytics indexes
CREATE INDEX idx_daily_date ON public.supportiq_analytics_daily(date DESC);
CREATE INDEX idx_daily_user ON public.supportiq_analytics_daily(user_id, date DESC);
```

## Triggers

```sql
-- Update updated_at for voice_calls
CREATE TRIGGER update_voice_calls_updated_at
    BEFORE UPDATE ON public.supportiq_voice_calls
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Update updated_at for daily analytics
CREATE TRIGGER update_analytics_daily_updated_at
    BEFORE UPDATE ON public.supportiq_analytics_daily
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

## Permissions

```sql
-- Grant permissions
GRANT ALL ON TABLE public.supportiq_voice_calls TO service_role, anon, authenticated;
GRANT ALL ON TABLE public.supportiq_call_transcripts TO service_role, anon, authenticated;
GRANT ALL ON TABLE public.supportiq_call_analytics TO service_role, anon, authenticated;
GRANT ALL ON TABLE public.supportiq_analytics_daily TO service_role, anon, authenticated;

-- Disable RLS for demo (enable in production)
ALTER TABLE public.supportiq_voice_calls DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.supportiq_call_transcripts DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.supportiq_call_analytics DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.supportiq_analytics_daily DISABLE ROW LEVEL SECURITY;
```

## Sample Data for Testing

```sql
-- Sample call
INSERT INTO public.supportiq_voice_calls (
  vapi_call_id, started_at, ended_at, duration_seconds, status, agent_type
) VALUES (
  'call_test_001',
  NOW() - INTERVAL '1 hour',
  NOW() - INTERVAL '55 minutes',
  300,
  'completed',
  'general'
);

-- Sample transcript
INSERT INTO public.supportiq_call_transcripts (
  call_id,
  transcript,
  word_count,
  turn_count
) VALUES (
  (SELECT id FROM public.supportiq_voice_calls WHERE vapi_call_id = 'call_test_001'),
  '[
    {"role": "agent", "content": "Hello, thank you for calling SupportIQ. How can I help you today?", "timestamp": 0.0},
    {"role": "customer", "content": "Hi, I am having trouble logging into my account.", "timestamp": 3.5},
    {"role": "agent", "content": "I would be happy to help you with that. Can you tell me the email address associated with your account?", "timestamp": 8.0}
  ]'::jsonb,
  45,
  3
);

-- Sample analytics
INSERT INTO public.supportiq_call_analytics (
  call_id,
  overall_sentiment,
  sentiment_score,
  primary_category,
  resolution_status,
  customer_satisfaction_predicted,
  agent_performance_score,
  customer_intent,
  key_topics,
  improvement_suggestions,
  call_summary,
  analysis_model
) VALUES (
  (SELECT id FROM public.supportiq_voice_calls WHERE vapi_call_id = 'call_test_001'),
  'neutral',
  0.2,
  'account_access',
  'resolved',
  4.2,
  85.0,
  'Customer wanted to reset their password',
  ARRAY['password reset', 'account access', 'login issues'],
  ARRAY['Consider offering 2FA setup after password reset', 'Could have proactively sent password reset link'],
  'Customer called about login issues. Agent helped reset password successfully. Customer was satisfied with resolution.',
  'google/gemini-2.5-flash-preview'
);
```

## Migration Script

Full migration script will be created at: `backend/migrations/001_voice_calls.sql`

This should be run in Supabase SQL Editor after the schema is finalized.
