# Chat-Based Ticket Management

This document outlines the implementation plan for chat-based ticket management in SupportIQ.

## Overview

Enable users to create, reference, and manage tickets through the AI chat interface, with full integration into the existing ticket system.

## Key Features

1. **Unified Ticket System** - All tickets (from calls OR chat) live in the same `tickets` table
2. **Chat Ticket Creation** - Users can create tickets via natural language or button
3. **Ticket Context Attachment** - Attach 1+ tickets to provide context for AI conversations
4. **Ticket Management** - View, update, and close tickets through chat

## Implementation Phases

- [Phase 1: Core Infrastructure](./phase-1-core.md)
- [Phase 2: Polish & Enhancements](./phase-2-polish.md)

## Design Decisions

### Ticket Picker UI
**Decision: Slide-out panel**

A modal interrupts flow. A slide-out panel from the right keeps the chat visible while browsing tickets. Show the user's tickets by default with a search bar to find others.

### Auto-attach from Calls
**Decision: Yes, auto-attach**

When user clicks "Chat about this call" from a call detail page, auto-attach that call's ticket. This is the expected behavior. Users can always remove it.

### Ticket Updates from Chat
**Decision: Full CRUD with confirmation**

AI can:
- Add notes (no confirmation needed)
- Change status (show confirmation: "Mark ticket #47 as resolved?")
- Close tickets (require confirmation)

### Chat History
**Decision: Persisted and resumable**

Chat sessions are saved for:
- Continuing conversations later
- Audit trail for ticket-related discussions
- Improved AI context over time
- Linking chat sessions to tickets

### Notifications
**Decision: None initially**

Keep it simple. Can add later if users request it.
