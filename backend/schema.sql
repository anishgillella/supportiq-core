-- SupportIQ Onboarding Database Schema
-- Run this in your Supabase SQL Editor

-- ===========================================
-- CLEAN UP: Drop existing tables if they exist
-- ===========================================
DROP TABLE IF EXISTS public.user_profiles CASCADE;
DROP TABLE IF EXISTS public.users CASCADE;
DROP TABLE IF EXISTS public.onboarding_config CASCADE;

-- ===========================================
-- CREATE TABLES
-- ===========================================

-- Users table
CREATE TABLE public.users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  current_step INTEGER DEFAULT 1,
  onboarding_completed BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User profile data (collected during onboarding)
CREATE TABLE public.user_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES public.users(id) ON DELETE CASCADE UNIQUE,
  about_me TEXT,
  street_address VARCHAR(255),
  city VARCHAR(100),
  state VARCHAR(100),
  zip_code VARCHAR(20),
  birthdate DATE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Admin configuration for wizard pages
CREATE TABLE public.onboarding_config (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  page_number INTEGER NOT NULL CHECK (page_number IN (2, 3)),
  component_type VARCHAR(50) NOT NULL CHECK (component_type IN ('aboutMe', 'address', 'birthdate')),
  display_order INTEGER DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(page_number, component_type)
);

-- ===========================================
-- DEFAULT DATA
-- ===========================================

-- Default configuration: Page 2 = aboutMe + address, Page 3 = birthdate
INSERT INTO public.onboarding_config (page_number, component_type, display_order) VALUES
  (2, 'aboutMe', 1),
  (2, 'address', 2),
  (3, 'birthdate', 1);

-- ===========================================
-- INDEXES
-- ===========================================

CREATE INDEX idx_users_email ON public.users(email);
CREATE INDEX idx_profiles_user_id ON public.user_profiles(user_id);
CREATE INDEX idx_config_page ON public.onboarding_config(page_number);

-- ===========================================
-- TRIGGERS FOR updated_at
-- ===========================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON public.user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ===========================================
-- PERMISSIONS
-- ===========================================

-- Grant permissions to Supabase roles
GRANT ALL ON TABLE public.users TO service_role;
GRANT ALL ON TABLE public.users TO anon;
GRANT ALL ON TABLE public.users TO authenticated;

GRANT ALL ON TABLE public.user_profiles TO service_role;
GRANT ALL ON TABLE public.user_profiles TO anon;
GRANT ALL ON TABLE public.user_profiles TO authenticated;

GRANT ALL ON TABLE public.onboarding_config TO service_role;
GRANT ALL ON TABLE public.onboarding_config TO anon;
GRANT ALL ON TABLE public.onboarding_config TO authenticated;

-- ===========================================
-- ROW LEVEL SECURITY
-- ===========================================

-- Disable RLS for this demo (enable in production with proper policies)
ALTER TABLE public.users DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_profiles DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.onboarding_config DISABLE ROW LEVEL SECURITY;
