# Phase 2: Polish & Enhancements

## Goals
- Improve UX with auto-attach from call pages
- Add chat history sidebar
- Implement AI-generated session titles
- Link tickets bidirectionally to chat sessions
- Add keyboard shortcuts and accessibility

---

## 1. Auto-Attach from Call Pages

### 1.1 "Chat about this call" Button

Add button to call detail page that:
1. Creates new chat session
2. Auto-attaches the call's ticket
3. Navigates to chat with context pre-loaded

```tsx
// In call detail page
<Button onClick={() => startChatAboutCall(call.id, call.ticket_id)}>
  <MessageSquare className="w-4 h-4 mr-2" />
  Chat about this call
</Button>
```

### 1.2 URL Parameter Support

Support URL parameter to pre-attach tickets:

```
/dashboard/chat?attach=ticket_uuid_1,ticket_uuid_2
```

Frontend parses this on mount and auto-attaches.

---

## 2. Chat History Sidebar

### 2.1 Layout Update

Split chat page into sidebar + main area:

```
┌─────────────────────────────────────────────────────┐
│ Sidebar (260px)      │  Main Chat Area              │
│                      │                              │
│ [+ New Chat]         │  [Ticket chips]  [Settings]  │
│                      │  ─────────────────────────   │
│ Today                │                              │
│ ├─ Billing issue     │  Messages...                 │
│ └─ Password reset    │                              │
│                      │                              │
│ Yesterday            │                              │
│ └─ API question      │                              │
│                      │                              │
│ Last 7 Days          │  [Input field]    [Send]     │
│ └─ Feature request   │                              │
└─────────────────────────────────────────────────────┘
```

### 2.2 Session List Component

```tsx
<ChatHistorySidebar>
  <NewChatButton />

  <SessionGroup label="Today">
    {todaySessions.map(session => (
      <SessionItem
        key={session.id}
        session={session}
        isActive={session.id === activeSessionId}
        onClick={() => setActiveSession(session.id)}
        onDelete={() => deleteSession(session.id)}
      />
    ))}
  </SessionGroup>

  <SessionGroup label="Yesterday">
    {yesterdaySessions.map(session => ...)}
  </SessionGroup>

  <SessionGroup label="Last 7 Days">
    {weekSessions.map(session => ...)}
  </SessionGroup>
</ChatHistorySidebar>
```

### 2.3 Session Item

Shows:
- AI-generated title (or "New Chat" if untitled)
- First line of last message (truncated)
- Timestamp
- Delete button (on hover)
- Attached ticket count badge

---

## 3. AI-Generated Session Titles

### 3.1 Title Generation

After first user message + AI response, generate title:

```python
async def generate_title(self, messages: List[ChatMessage]) -> str:
    prompt = """Based on this conversation, generate a very short title (3-5 words max).
    Just return the title, nothing else.

    Conversation:
    {messages}
    """

    response = await self.llm.generate(prompt)
    return response.strip()[:50]  # Max 50 chars
```

### 3.2 Auto-Update

- Title is `null` for new sessions
- After first exchange, generate and save title
- User can manually edit title (optional)

---

## 4. Bidirectional Ticket-Chat Linking

### 4.1 Ticket Detail Shows Chat Sessions

On ticket detail page, show linked chat sessions:

```tsx
<TicketDetail>
  {/* ... existing ticket info ... */}

  <Section title="Related Conversations">
    {linkedSessions.map(session => (
      <ChatSessionLink
        session={session}
        onClick={() => navigateToChat(session.id)}
      />
    ))}
  </Section>
</TicketDetail>
```

### 4.2 Database Update

Add index for efficient lookup:

```sql
-- GIN index for array contains queries
CREATE INDEX idx_chat_sessions_ticket_ids ON chat_sessions USING GIN (attached_ticket_ids);
```

Query for linked sessions:

```sql
SELECT * FROM chat_sessions
WHERE $1 = ANY(attached_ticket_ids)
ORDER BY updated_at DESC;
```

---

## 5. Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd/Ctrl + K` | Focus search / new chat |
| `Cmd/Ctrl + Enter` | Send message |
| `Cmd/Ctrl + Shift + T` | Open ticket picker |
| `Escape` | Close ticket picker / Cancel |
| `Up Arrow` (in input) | Edit last message |

### 5.1 Implementation

```tsx
useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault()
      focusSearch()
    }
    if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 't') {
      e.preventDefault()
      openTicketPicker()
    }
    // ... more shortcuts
  }

  window.addEventListener('keydown', handleKeyDown)
  return () => window.removeEventListener('keydown', handleKeyDown)
}, [])
```

---

## 6. Enhanced Ticket Operations

### 6.1 Bulk Operations

Allow bulk actions on multiple tickets from chat:

```
User: "Close tickets 45, 46, and 47"
AI: "I'll close these 3 tickets. Confirm?"
    [Close All] [Cancel]
```

### 6.2 Ticket Notes from Chat

When AI adds context, save as ticket note:

```
User: "Add a note to ticket 45 that customer mentioned they're on the Pro plan"
AI: "Added note to ticket #45: Customer mentioned they're on the Pro plan"
```

Store in ticket's notes array with metadata:

```json
{
  "content": "Customer mentioned they're on the Pro plan",
  "added_by": "chat",
  "chat_session_id": "uuid",
  "added_at": "2024-01-15T10:30:00Z"
}
```

---

## 7. Message Enhancements

### 7.1 Message Actions

On hover over messages, show actions:

- Copy text
- Regenerate (for AI messages)
- Create ticket from this (for user messages)

### 7.2 Markdown Support

Render AI responses with markdown:

- Code blocks with syntax highlighting
- Lists and headers
- Links
- Tables

### 7.3 Typing Indicator

Show "AI is typing..." with animated dots while waiting for response.

---

## 8. Error Handling & Edge Cases

### 8.1 Graceful Degradation

- If ticket lookup fails, show error inline but continue chat
- If session save fails, show warning but allow continued typing
- Offline mode: queue messages and sync when back online

### 8.2 Rate Limiting

- Show "Please wait..." if user sends too quickly
- Queue messages if hitting API limits

### 8.3 Session Recovery

- Auto-save draft messages
- Recover unsent message after page refresh

---

## 9. Acceptance Criteria

- [ ] "Chat about this call" button works from call detail page
- [ ] Chat history sidebar shows sessions grouped by date
- [ ] Sessions have AI-generated titles
- [ ] Ticket detail page shows linked chat sessions
- [ ] Keyboard shortcuts work
- [ ] Bulk ticket operations work via chat
- [ ] Notes can be added to tickets via chat
- [ ] Markdown renders correctly in AI responses
- [ ] Typing indicator shows during AI generation
- [ ] Error states handled gracefully
