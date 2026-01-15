-- Migration: Create supportiq_tickets table
-- Description: Support tickets auto-generated from call analysis
-- Run this in Supabase SQL Editor

-- Create the tickets table
CREATE TABLE IF NOT EXISTS supportiq_tickets (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  call_id UUID REFERENCES supportiq_voice_calls(id) ON DELETE CASCADE,
  user_id UUID,
  title TEXT NOT NULL,
  description TEXT,
  category TEXT,
  priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
  status TEXT DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'resolved', 'closed')),
  customer_email TEXT,
  customer_name TEXT,
  customer_phone TEXT,
  sentiment_score FLOAT,
  resolution_status TEXT,
  customer_satisfaction_predicted INT CHECK (customer_satisfaction_predicted >= 1 AND customer_satisfaction_predicted <= 5),
  action_items TEXT[] DEFAULT '{}',
  key_topics TEXT[] DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  resolved_at TIMESTAMPTZ
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_tickets_user_id ON supportiq_tickets(user_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON supportiq_tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_priority ON supportiq_tickets(priority);
CREATE INDEX IF NOT EXISTS idx_tickets_call_id ON supportiq_tickets(call_id);
CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON supportiq_tickets(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tickets_category ON supportiq_tickets(category);

-- Grant permissions
GRANT ALL ON TABLE supportiq_tickets TO service_role, anon, authenticated;

-- Disable RLS for demo (enable in production with proper policies)
ALTER TABLE supportiq_tickets DISABLE ROW LEVEL SECURITY;

-- Add comment for documentation
COMMENT ON TABLE supportiq_tickets IS 'Support tickets automatically generated from voice call analysis';
