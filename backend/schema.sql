-- SupportIQ Onboarding Database Schema
-- Run this in your Supabase SQL Editor
-- All tables use "supportiq_" prefix to avoid conflicts with other applications

-- ===========================================
-- CLEAN UP: Drop existing tables if they exist
-- ===========================================
DROP TABLE IF EXISTS public.supportiq_knowledge_chunks CASCADE;
DROP TABLE IF EXISTS public.supportiq_knowledge_documents CASCADE;
DROP TABLE IF EXISTS public.supportiq_conversations CASCADE;
DROP TABLE IF EXISTS public.supportiq_user_profiles CASCADE;
DROP TABLE IF EXISTS public.supportiq_users CASCADE;
DROP TABLE IF EXISTS public.supportiq_onboarding_config CASCADE;

-- ===========================================
-- CREATE TABLES
-- ===========================================

-- Users table (updated with company info)
CREATE TABLE public.supportiq_users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  company_name VARCHAR(255),
  company_website VARCHAR(500),
  current_step INTEGER DEFAULT 1,
  onboarding_completed BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User profile data (collected during onboarding)
CREATE TABLE public.supportiq_user_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES public.supportiq_users(id) ON DELETE CASCADE UNIQUE,
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
CREATE TABLE public.supportiq_onboarding_config (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  page_number INTEGER NOT NULL CHECK (page_number IN (2, 3)),
  component_type VARCHAR(50) NOT NULL CHECK (component_type IN ('aboutMe', 'address', 'birthdate')),
  display_order INTEGER DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(page_number, component_type)
);

-- ===========================================
-- KNOWLEDGE BASE TABLES
-- ===========================================

-- Knowledge documents (PDFs, scraped pages, etc.)
CREATE TABLE public.supportiq_knowledge_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES public.supportiq_users(id) ON DELETE CASCADE,
  title VARCHAR(500) NOT NULL,
  source VARCHAR(1000) NOT NULL, -- URL or filename
  source_type VARCHAR(50) NOT NULL CHECK (source_type IN ('website', 'pdf', 'text', 'docx')),
  content TEXT, -- Original full content
  metadata JSONB DEFAULT '{}',
  chunks_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Knowledge chunks (for RAG retrieval)
CREATE TABLE public.supportiq_knowledge_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID REFERENCES public.supportiq_knowledge_documents(id) ON DELETE CASCADE,
  user_id UUID REFERENCES public.supportiq_users(id) ON DELETE CASCADE,
  chunk_index INTEGER NOT NULL,
  content TEXT NOT NULL,
  embedding_id VARCHAR(255), -- Pinecone vector ID
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ===========================================
-- CONVERSATION TABLES
-- ===========================================

-- Conversations for chat history
CREATE TABLE public.supportiq_conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES public.supportiq_users(id) ON DELETE CASCADE,
  title VARCHAR(255),
  messages JSONB DEFAULT '[]', -- Array of {role, content, timestamp, sources}
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ===========================================
-- DEFAULT DATA
-- ===========================================

-- Default configuration: Page 2 = aboutMe + address, Page 3 = birthdate
INSERT INTO public.supportiq_onboarding_config (page_number, component_type, display_order) VALUES
  (2, 'aboutMe', 1),
  (2, 'address', 2),
  (3, 'birthdate', 1);

-- ===========================================
-- INDEXES
-- ===========================================

CREATE INDEX idx_supportiq_users_email ON public.supportiq_users(email);
CREATE INDEX idx_supportiq_profiles_user_id ON public.supportiq_user_profiles(user_id);
CREATE INDEX idx_supportiq_config_page ON public.supportiq_onboarding_config(page_number);
CREATE INDEX idx_supportiq_documents_user_id ON public.supportiq_knowledge_documents(user_id);
CREATE INDEX idx_supportiq_chunks_document_id ON public.supportiq_knowledge_chunks(document_id);
CREATE INDEX idx_supportiq_chunks_user_id ON public.supportiq_knowledge_chunks(user_id);
CREATE INDEX idx_supportiq_chunks_embedding_id ON public.supportiq_knowledge_chunks(embedding_id);
CREATE INDEX idx_supportiq_conversations_user_id ON public.supportiq_conversations(user_id);

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

CREATE TRIGGER update_supportiq_users_updated_at
    BEFORE UPDATE ON public.supportiq_users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_supportiq_profiles_updated_at
    BEFORE UPDATE ON public.supportiq_user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_supportiq_documents_updated_at
    BEFORE UPDATE ON public.supportiq_knowledge_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_supportiq_conversations_updated_at
    BEFORE UPDATE ON public.supportiq_conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ===========================================
-- PERMISSIONS
-- ===========================================

-- Grant permissions to Supabase roles
GRANT ALL ON TABLE public.supportiq_users TO service_role, anon, authenticated;
GRANT ALL ON TABLE public.supportiq_user_profiles TO service_role, anon, authenticated;
GRANT ALL ON TABLE public.supportiq_onboarding_config TO service_role, anon, authenticated;
GRANT ALL ON TABLE public.supportiq_knowledge_documents TO service_role, anon, authenticated;
GRANT ALL ON TABLE public.supportiq_knowledge_chunks TO service_role, anon, authenticated;
GRANT ALL ON TABLE public.supportiq_conversations TO service_role, anon, authenticated;

-- ===========================================
-- ROW LEVEL SECURITY
-- ===========================================

-- Disable RLS for this demo (enable in production with proper policies)
ALTER TABLE public.supportiq_users DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.supportiq_user_profiles DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.supportiq_onboarding_config DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.supportiq_knowledge_documents DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.supportiq_knowledge_chunks DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.supportiq_conversations DISABLE ROW LEVEL SECURITY;
