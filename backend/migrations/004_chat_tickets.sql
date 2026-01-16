-- Migration: 004_chat_tickets.sql
-- Description: Add chat-based ticket management support
-- Run this in Supabase SQL Editor

-- 1. Add ticket_number to tickets (sequential, user-friendly ID)
ALTER TABLE supportiq_tickets
ADD COLUMN IF NOT EXISTS ticket_number SERIAL UNIQUE;

-- Backfill existing tickets with ticket numbers based on created_at order
WITH numbered AS (
  SELECT id, ROW_NUMBER() OVER (ORDER BY created_at) as rn
  FROM supportiq_tickets
  WHERE ticket_number IS NULL
)
UPDATE supportiq_tickets t
SET ticket_number = n.rn
FROM numbered n
WHERE t.id = n.id;

-- 2. Add source column to track ticket origin (call or chat)
ALTER TABLE supportiq_tickets
ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'call';

-- 3. Add notes array for tracking updates/comments
ALTER TABLE supportiq_tickets
ADD COLUMN IF NOT EXISTS notes JSONB DEFAULT '[]';

-- 4. Add attached_ticket_ids to conversations for ticket context
ALTER TABLE supportiq_conversations
ADD COLUMN IF NOT EXISTS attached_ticket_ids UUID[] DEFAULT '{}';

-- 5. Create full-text search index on ticket title for search
CREATE INDEX IF NOT EXISTS idx_tickets_title_search
ON supportiq_tickets USING gin(to_tsvector('english', coalesce(title, '')));

-- 6. Create GIN index for attached tickets array lookup
CREATE INDEX IF NOT EXISTS idx_conversations_tickets
ON supportiq_conversations USING GIN (attached_ticket_ids);

-- 7. Create index on ticket_number for fast lookups
CREATE INDEX IF NOT EXISTS idx_tickets_ticket_number
ON supportiq_tickets(ticket_number);

-- 8. Create index on source for filtering
CREATE INDEX IF NOT EXISTS idx_tickets_source
ON supportiq_tickets(source);

-- Add comments for documentation
COMMENT ON COLUMN supportiq_tickets.ticket_number IS 'User-friendly sequential ticket number (e.g., #47)';
COMMENT ON COLUMN supportiq_tickets.source IS 'Origin of ticket: call (auto-generated) or chat (user-created)';
COMMENT ON COLUMN supportiq_tickets.notes IS 'Array of notes/comments added to ticket [{content, added_by, added_at}]';
COMMENT ON COLUMN supportiq_conversations.attached_ticket_ids IS 'Tickets attached to this conversation for context';

-- 9. Grant permissions on the ticket_number sequence (required for inserts)
GRANT USAGE, SELECT, UPDATE ON SEQUENCE supportiq_tickets_ticket_number_seq TO anon;
GRANT USAGE, SELECT, UPDATE ON SEQUENCE supportiq_tickets_ticket_number_seq TO authenticated;
GRANT USAGE, SELECT, UPDATE ON SEQUENCE supportiq_tickets_ticket_number_seq TO service_role;
