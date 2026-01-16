# Phase 1: Core Infrastructure

## Goals
- Enable ticket creation from chat
- Allow attaching existing tickets to chat context
- Implement basic ticket operations via LLM function calling
- Persist chat sessions

---

## 1. Database Schema Updates

### 1.1 Update `tickets` table

```sql
-- Add source column to track where ticket originated
ALTER TABLE tickets ADD COLUMN source TEXT DEFAULT 'call';
-- Values: 'call' | 'chat'

-- Add chat_session_id for tickets created from chat
ALTER TABLE tickets ADD COLUMN chat_session_id UUID REFERENCES chat_sessions(id);
```

### 1.2 Create `chat_sessions` table

```sql
CREATE TABLE chat_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title TEXT,  -- AI-generated from first message
  attached_ticket_ids UUID[] DEFAULT '{}',  -- Tickets attached to this session
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_chat_sessions_updated_at ON chat_sessions(updated_at DESC);
```

### 1.3 Create `chat_messages` table

```sql
CREATE TABLE chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL,  -- 'user' | 'assistant' | 'system'
  content TEXT NOT NULL,
  ticket_refs UUID[] DEFAULT '{}',  -- Tickets mentioned in this message
  tool_calls JSONB,  -- Store any function calls made
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX idx_chat_messages_created_at ON chat_messages(created_at);
```

---

## 2. Backend API Endpoints

### 2.1 Chat Session Endpoints

```
POST   /api/chat/sessions              Create new chat session
GET    /api/chat/sessions              List user's chat sessions
GET    /api/chat/sessions/:id          Get session with messages
DELETE /api/chat/sessions/:id          Delete a session
PATCH  /api/chat/sessions/:id/tickets  Attach/detach tickets
```

### 2.2 Chat Message Endpoints

```
POST   /api/chat/sessions/:id/messages  Send message & get AI response
```

### 2.3 Ticket Endpoints (for chat)

```
POST   /api/chat/tickets                Create ticket from chat
GET    /api/tickets/:id                 Get ticket details (existing)
PATCH  /api/tickets/:id                 Update ticket (existing)
GET    /api/tickets/search?q=...        Search tickets
```

---

## 3. LLM Function Calling Tools

The chat AI will have access to these tools:

### 3.1 `create_ticket`

```python
{
    "name": "create_ticket",
    "description": "Create a new support ticket",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Short descriptive title for the ticket"
            },
            "description": {
                "type": "string",
                "description": "Detailed description of the issue"
            },
            "priority": {
                "type": "string",
                "enum": ["low", "medium", "high", "urgent"],
                "description": "Ticket priority level"
            },
            "category": {
                "type": "string",
                "description": "Category/type of the ticket"
            }
        },
        "required": ["title", "description"]
    }
}
```

### 3.2 `get_ticket`

```python
{
    "name": "get_ticket",
    "description": "Get details of a ticket by ID or ticket number",
    "parameters": {
        "type": "object",
        "properties": {
            "ticket_id": {
                "type": "integer",
                "description": "The ticket number (e.g., 47)"
            }
        },
        "required": ["ticket_id"]
    }
}
```

### 3.3 `update_ticket`

```python
{
    "name": "update_ticket",
    "description": "Update a ticket's status or add notes",
    "parameters": {
        "type": "object",
        "properties": {
            "ticket_id": {
                "type": "integer",
                "description": "The ticket number to update"
            },
            "status": {
                "type": "string",
                "enum": ["open", "in_progress", "resolved", "closed"],
                "description": "New status for the ticket"
            },
            "notes": {
                "type": "string",
                "description": "Notes to add to the ticket"
            }
        },
        "required": ["ticket_id"]
    }
}
```

### 3.4 `search_tickets`

```python
{
    "name": "search_tickets",
    "description": "Search for tickets by keyword or filter",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            },
            "status": {
                "type": "string",
                "enum": ["open", "in_progress", "resolved", "closed", "all"],
                "description": "Filter by status"
            },
            "limit": {
                "type": "integer",
                "description": "Max results to return",
                "default": 10
            }
        },
        "required": ["query"]
    }
}
```

---

## 4. Backend Service Implementation

### 4.1 Chat Service (`backend/services/chat_service.py`)

```python
class ChatService:
    async def create_session(self, user_id: str) -> ChatSession
    async def get_session(self, session_id: str) -> ChatSession
    async def list_sessions(self, user_id: str) -> List[ChatSession]
    async def delete_session(self, session_id: str) -> bool
    async def attach_tickets(self, session_id: str, ticket_ids: List[str]) -> ChatSession
    async def detach_tickets(self, session_id: str, ticket_ids: List[str]) -> ChatSession
    async def send_message(self, session_id: str, content: str) -> ChatMessage
    async def generate_title(self, session_id: str) -> str
```

### 4.2 Chat LLM Service (`backend/services/chat_llm_service.py`)

```python
class ChatLLMService:
    async def process_message(
        self,
        session: ChatSession,
        user_message: str,
        attached_tickets: List[Ticket]
    ) -> Tuple[str, List[ToolCall]]

    async def execute_tool(self, tool_name: str, args: dict) -> dict
```

---

## 5. Frontend Components

### 5.1 Updated Chat Page Structure

```
/dashboard/chat
├── page.tsx                    # Main chat page
├── components/
│   ├── chat-container.tsx      # Main chat container
│   ├── chat-header.tsx         # Header with session title, ticket chips
│   ├── chat-messages.tsx       # Message list
│   ├── chat-input.tsx          # Input with send button
│   ├── ticket-chip.tsx         # Small ticket badge component
│   ├── ticket-picker.tsx       # Slide-out ticket selector
│   └── ticket-card-inline.tsx  # Inline ticket card in messages
```

### 5.2 Chat Header with Attached Tickets

```tsx
// Displays attached tickets as removable chips
<ChatHeader>
  <h2>Chat with AI</h2>
  <div className="attached-tickets">
    {attachedTickets.map(ticket => (
      <TicketChip
        key={ticket.id}
        ticket={ticket}
        onRemove={() => detachTicket(ticket.id)}
      />
    ))}
    <button onClick={openTicketPicker}>
      <Plus /> Add Ticket
    </button>
  </div>
</ChatHeader>
```

### 5.3 Ticket Picker Slide-out Panel

```tsx
// Slide-out from right side
<TicketPicker
  isOpen={isPickerOpen}
  onClose={() => setPickerOpen(false)}
  onSelect={(ticket) => attachTicket(ticket)}
  excludeIds={attachedTickets.map(t => t.id)}
/>
```

### 5.4 Inline Ticket Cards

When AI creates or references a ticket, show an inline card:

```tsx
<TicketCardInline
  ticket={ticket}
  actions={['view', 'detach']}
/>
```

---

## 6. Frontend API Client Updates

### 6.1 New API Methods (`frontend/lib/api.ts`)

```typescript
// Chat sessions
createChatSession(): Promise<ChatSession>
getChatSession(id: string): Promise<ChatSession>
listChatSessions(): Promise<ChatSession[]>
deleteChatSession(id: string): Promise<void>
attachTicketsToSession(sessionId: string, ticketIds: string[]): Promise<ChatSession>
detachTicketsFromSession(sessionId: string, ticketIds: string[]): Promise<ChatSession>

// Chat messages
sendChatMessage(sessionId: string, content: string): Promise<ChatMessage>

// Tickets
searchTickets(query: string, status?: string): Promise<Ticket[]>
```

---

## 7. Implementation Order

1. **Database migrations** - Create tables and update schema
2. **Backend models** - Pydantic models for chat entities
3. **Backend services** - Chat service and LLM service
4. **Backend routes** - API endpoints
5. **Frontend API client** - Add new methods
6. **Frontend components** - Build UI components
7. **Integration** - Connect frontend to backend
8. **Testing** - Manual testing and bug fixes

---

## 8. Acceptance Criteria

- [ ] User can create a new chat session
- [ ] User can send messages and receive AI responses
- [ ] User can attach existing tickets to a chat session
- [ ] User can create new tickets via chat ("create a ticket for...")
- [ ] AI can reference attached tickets in responses
- [ ] Inline ticket cards display when AI mentions tickets
- [ ] Chat sessions are persisted and resumable
- [ ] Ticket picker allows searching and filtering
