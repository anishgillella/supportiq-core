# Voice Call Analytics System

Technical documentation for the SupportIQ voice call analytics pipeline.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Data Flow](#data-flow)
- [VAPI Integration](#vapi-integration)
- [Transcript Analysis](#transcript-analysis)
- [Database Schema](#database-schema)
- [API Endpoints](#api-endpoints)
- [Data Models](#data-models)
- [Configuration](#configuration)

---

## Overview

The analytics system captures, processes, and analyzes voice calls made through VAPI. When a call ends, the system:

1. Receives a webhook from VAPI with the call transcript
2. Stores the call metadata and transcript in Supabase
3. Analyzes the transcript using Gemini 2.5 Flash via OpenRouter
4. Extracts structured insights (sentiment, resolution, customer profile, etc.)
5. Updates daily aggregated analytics
6. Makes data available via REST APIs and dashboard

**Key Features:**
- Real-time transcript analysis
- Sentiment tracking and progression
- Customer profile extraction
- Agent performance scoring
- Churn risk assessment
- Issue categorization
- Data isolation per user (multi-tenant)

---

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────────┐
│   Browser   │      │     VAPI     │      │  FastAPI Server │
│  (Web Call) │──────│  Voice Agent │──────│    /vapi/*      │
└─────────────┘      └──────────────┘      └────────┬────────┘
                                                    │
                     ┌──────────────────────────────┼──────────────────────────────┐
                     │                              │                              │
                     ▼                              ▼                              ▼
              ┌─────────────┐              ┌───────────────┐              ┌───────────────┐
              │  Supabase   │              │   OpenRouter  │              │   Pinecone    │
              │  (Storage)  │              │  (Gemini LLM) │              │ (RAG Vectors) │
              └─────────────┘              └───────────────┘              └───────────────┘
```

**Components:**

| Component | Purpose |
|-----------|---------|
| VAPI | Voice agent platform - handles calls, STT/TTS |
| FastAPI | Backend API server for webhooks and REST endpoints |
| Supabase | PostgreSQL database for call data, transcripts, analytics |
| OpenRouter | LLM gateway - routes to Gemini 2.5 Flash for analysis |
| Pinecone | Vector database for RAG knowledge base search |

---

## Data Flow

### 1. Call Initiation

```
User → Frontend → POST /api/v1/voice/calls/initiate → VAPI API
                                                         │
                                           Creates web call
                                           Includes user_id in metadata
```

When a user initiates a call from the dashboard:
- `POST /api/v1/voice/calls/initiate` is called
- The server calls VAPI's `/call/web` API
- `user_id` is passed in call metadata for data isolation

**Code Reference:** `backend/app/api/v1/voice_calls.py:36-131`

### 2. During Call (RAG Function Calls)

```
VAPI → POST /api/v1/vapi/webhook (type: "function-call")
                │
                ▼
        Query Pinecone (namespace = user_id)
                │
                ▼
        Return context to VAPI assistant
```

When the voice agent needs knowledge base context:
- VAPI sends a `function-call` webhook
- The handler extracts `user_id` from call metadata
- Searches Pinecone in the user's namespace
- Returns relevant context chunks

**Code Reference:** `backend/app/api/v1/vapi.py:148-223`

### 3. Call End - Transcript Processing

```
VAPI → POST /api/v1/vapi/webhook (type: "end-of-call-report")
                │
                ▼
    ┌───────────────────────────────────┐
    │  Background Task: handle_end_of_call  │
    └───────────────────────────────────┘
                │
    ┌───────────┼───────────┐
    │           │           │
    ▼           ▼           ▼
 Create      Create      Analyze
 Call        Transcript  Transcript
 Record      Record      (LLM)
    │           │           │
    ▼           ▼           ▼
supportiq_  supportiq_  supportiq_
voice_calls call_trans- call_
            cripts      analytics
```

**Detailed Flow:**

1. **Webhook Receipt** (`vapi.py:29-74`)
   - VAPI sends `end-of-call-report` when call ends
   - Handler responds immediately with `{"status": "processing"}`
   - Actual processing runs in background task

2. **Call Record Creation** (`call_service.py:9-49`)
   - Extracts: `vapi_call_id`, `started_at`, `ended_at`, `duration`
   - Determines status: `completed`, `failed`, `abandoned`
   - Associates with `user_id` (caller_id) for data isolation
   - Inserts into `supportiq_voice_calls`

3. **Transcript Storage** (`call_service.py:52-79`)
   - Stores transcript messages as JSONB array
   - Records word count and turn count
   - Saves raw VAPI response for debugging
   - Inserts into `supportiq_call_transcripts`

4. **AI Analysis** (`transcript_analysis.py:161-198`)
   - Formats transcript for LLM
   - Sends to Gemini 2.5 Flash via OpenRouter
   - Parses structured JSON response
   - Stores in `supportiq_call_analytics`
   - Updates `supportiq_analytics_daily`

**Code Reference:** `backend/app/api/v1/vapi.py:230-327`

---

## VAPI Integration

### Webhook Configuration

Configure your VAPI assistant to send webhooks to:
```
https://your-domain.com/api/v1/vapi/webhook
```

### Supported Webhook Types

| Type | Purpose | Handler |
|------|---------|---------|
| `assistant-request` | Inject RAG context at call start | `handle_assistant_request` |
| `end-of-call-report` | Process completed call | `handle_end_of_call` |
| `function-call` | Handle RAG search requests | `handle_function_call` |
| `status-update` | Real-time call status | `handle_status_update` |
| `transcript` | Live transcript updates | Acknowledged only |

### Webhook Payload Examples

**end-of-call-report:**
```json
{
  "message": {
    "type": "end-of-call-report",
    "call": {
      "id": "call_abc123",
      "startedAt": "2024-01-15T10:30:00Z",
      "endedAt": "2024-01-15T10:35:00Z",
      "endedReason": "customer-ended-call",
      "recordingUrl": "https://...",
      "assistantId": "asst_xyz",
      "metadata": {
        "user_id": "uuid-of-user"
      }
    },
    "transcript": "Full transcript text...",
    "messages": [
      {"role": "assistant", "content": "Hello, how can I help?", "timestamp": 0.5},
      {"role": "user", "content": "I have a question...", "timestamp": 2.1}
    ]
  }
}
```

**function-call:**
```json
{
  "message": {
    "type": "function-call",
    "call": {
      "id": "call_abc123",
      "metadata": {"user_id": "uuid-of-user"}
    },
    "functionCall": {
      "name": "search_knowledge_base",
      "parameters": {"query": "return policy"}
    }
  }
}
```

### User ID Metadata

For data isolation, the `user_id` is passed when initiating calls:

```python
call_payload = {
    "assistantId": assistant_id,
    "metadata": {
        "user_id": current_user.user_id,
        "initiated_from": "dashboard"
    }
}
```

This `user_id` is then available in all webhook events and used to:
- Associate calls with the correct user
- Search the user's knowledge base namespace
- Filter analytics by user

---

## Transcript Analysis

### LLM Configuration

| Setting | Value |
|---------|-------|
| Provider | OpenRouter |
| Model | `google/gemini-2.5-flash-preview` |
| Max Tokens | 4096 |
| Temperature | 0.2 (low for consistent structured output) |

### Analysis Prompt

The system uses a comprehensive prompt (`transcript_analysis.py:20-154`) that extracts:

**Call Analysis:**
- `overall_sentiment`: positive, neutral, negative, mixed
- `sentiment_score`: -1.0 to 1.0
- `sentiment_progression`: Array of sentiment changes with triggers
- `primary_category`: Main issue type
- `resolution_status`: resolved, partially_resolved, unresolved, escalated, follow_up_needed
- `customer_satisfaction_predicted`: 1.0 to 5.0
- `customer_intent`: What the customer wanted
- `key_topics`: Array of discussed topics
- `action_items`: Follow-ups needed
- `call_summary`: 2-3 sentence summary

**Customer Profile:**
- Contact info (name, email, phone, account_id)
- Customer type (new, returning, VIP, at_risk)
- Frustration level
- Pain points, feature requests, complaints
- Churn risk assessment with risk factors

**Agent Performance:**
- Overall score (0-100)
- Empathy, knowledge, communication, efficiency scores
- Strengths and areas for improvement
- Training recommendations

### Category Options

```
account_access    - Login, password, 2FA issues
billing           - Payments, invoices, refunds, subscriptions
technical_support - Bugs, errors, how-to questions
product_inquiry   - Features, pricing, comparisons
complaint         - Service issues, dissatisfaction
feedback          - Suggestions, praise
general_inquiry   - Hours, contact, other
cancellation      - Account/subscription cancellation
onboarding        - New user setup, getting started
upgrade           - Plan upgrades, add-ons
```

### Scoring Guidelines

**Sentiment Score (-1.0 to 1.0):**
- `-1.0` = Very negative (angry, frustrated throughout)
- `0.0` = Neutral (no strong emotions)
- `1.0` = Very positive (happy, satisfied)

**Customer Satisfaction (1-5):**
- `5` = Issue resolved quickly, exceeded expectations
- `4` = Satisfied, issue resolved
- `3` = Neutral, issue somewhat addressed
- `2` = Dissatisfied, issue not fully resolved
- `1` = Very dissatisfied, bad experience

**Agent Scores (0-100):**
- `90-100` = Excellent
- `70-89` = Good
- `50-69` = Average
- `30-49` = Below average
- `0-29` = Poor

---

## Database Schema

### Tables

#### `supportiq_voice_calls`
Primary call record table.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `vapi_call_id` | VARCHAR(255) | VAPI's call identifier (unique) |
| `vapi_assistant_id` | VARCHAR(255) | Which assistant handled the call |
| `caller_phone` | VARCHAR(50) | Phone number if applicable |
| `caller_id` | UUID | FK to supportiq_users (data isolation) |
| `started_at` | TIMESTAMPTZ | Call start time |
| `ended_at` | TIMESTAMPTZ | Call end time |
| `duration_seconds` | INTEGER | Call duration |
| `status` | VARCHAR(50) | in_progress, completed, abandoned, failed, transferred |
| `agent_type` | VARCHAR(50) | Agent type (default: "general") |
| `recording_url` | TEXT | URL to call recording |

#### `supportiq_call_transcripts`
Stores transcript for each call.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `call_id` | UUID | FK to voice_calls (unique - 1:1) |
| `transcript` | JSONB | Array of messages: `[{role, content, timestamp}]` |
| `raw_vapi_response` | JSONB | Complete webhook payload |
| `word_count` | INTEGER | Total words in transcript |
| `turn_count` | INTEGER | Number of conversation turns |

#### `supportiq_call_analytics`
AI-generated analysis for each call.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `call_id` | UUID | FK to voice_calls (unique - 1:1) |
| `overall_sentiment` | VARCHAR(20) | positive, neutral, negative, mixed |
| `sentiment_score` | FLOAT | -1.0 to 1.0 |
| `sentiment_progression` | JSONB | Array of sentiment changes |
| `primary_category` | VARCHAR(100) | Main issue category |
| `secondary_categories` | TEXT[] | Additional categories |
| `resolution_status` | VARCHAR(50) | resolved, unresolved, etc. |
| `customer_satisfaction_predicted` | FLOAT | 1.0 to 5.0 |
| `agent_performance_score` | FLOAT | 0 to 100 |
| `customer_intent` | TEXT | What customer wanted |
| `key_topics` | TEXT[] | Topics discussed |
| `action_items` | TEXT[] | Follow-ups needed |
| `improvement_suggestions` | TEXT[] | How to improve |
| `call_summary` | TEXT | Brief summary |
| `analysis_model` | VARCHAR(100) | Model used for analysis |
| `analysis_version` | VARCHAR(20) | Analysis prompt version |

#### `supportiq_analytics_daily`
Aggregated daily statistics.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `date` | DATE | The date |
| `user_id` | UUID | FK to users (NULL for global stats) |
| `total_calls` | INTEGER | Total calls that day |
| `completed_calls` | INTEGER | Successfully completed |
| `abandoned_calls` | INTEGER | Abandoned calls |
| `total_duration_seconds` | INTEGER | Sum of all durations |
| `avg_duration_seconds` | FLOAT | Average duration |
| `resolved_calls` | INTEGER | Resolved count |
| `escalated_calls` | INTEGER | Escalated count |
| `resolution_rate` | FLOAT | Percentage resolved |
| `positive_calls` | INTEGER | Positive sentiment count |
| `neutral_calls` | INTEGER | Neutral sentiment count |
| `negative_calls` | INTEGER | Negative sentiment count |
| `avg_sentiment_score` | FLOAT | Average sentiment |
| `category_breakdown` | JSONB | `{category: count}` |

### Entity Relationship

```
supportiq_users
     │
     │ 1:N
     ▼
supportiq_voice_calls ──────┬─── 1:1 ───► supportiq_call_transcripts
     │                      │
     │                      └─── 1:1 ───► supportiq_call_analytics
     │
     │ N:1
     ▼
supportiq_analytics_daily
```

### Indexes

```sql
-- Voice calls
idx_voice_calls_vapi_id      ON (vapi_call_id)
idx_voice_calls_status       ON (status)
idx_voice_calls_started_at   ON (started_at DESC)
idx_voice_calls_caller       ON (caller_id)
idx_voice_calls_agent_type   ON (agent_type)

-- Analytics
idx_analytics_call_id        ON (call_id)
idx_analytics_category       ON (primary_category)
idx_analytics_sentiment      ON (overall_sentiment)
idx_analytics_resolution     ON (resolution_status)

-- Daily
idx_daily_date               ON (date DESC)
idx_daily_user               ON (user_id, date DESC)
```

---

## API Endpoints

### Voice Calls

#### `POST /api/v1/voice/calls/initiate`
Initiate a new voice call via VAPI.

**Auth:** Required (JWT)

**Request:**
```json
{
  "phone_number": "+1234567890",  // Optional: for outbound calls
  "assistant_id": "asst_xyz"      // Optional: override default
}
```

**Response:**
```json
{
  "success": true,
  "call_id": "call_abc123",
  "web_call_url": "https://vapi.ai/call/...",
  "message": "Call initiated successfully"
}
```

#### `GET /api/v1/voice/calls`
List calls for the current user.

**Auth:** Required (JWT)

**Query Params:**
| Param | Type | Description |
|-------|------|-------------|
| `page` | int | Page number (default: 1) |
| `page_size` | int | Items per page (default: 20, max: 100) |
| `status` | string | Filter by status |
| `sentiment` | string | Filter by sentiment |
| `category` | string | Filter by category |
| `date_from` | datetime | Start date filter |
| `date_to` | datetime | End date filter |

**Response:**
```json
{
  "calls": [
    {
      "id": "uuid",
      "vapi_call_id": "call_abc",
      "started_at": "2024-01-15T10:30:00Z",
      "ended_at": "2024-01-15T10:35:00Z",
      "duration_seconds": 300,
      "status": "completed",
      "agent_type": "general",
      "sentiment": "positive",
      "category": "billing",
      "resolution": "resolved"
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

#### `GET /api/v1/voice/calls/{call_id}`
Get detailed call information.

**Auth:** Required (JWT)

**Response:**
```json
{
  "id": "uuid",
  "vapi_call_id": "call_abc",
  "started_at": "2024-01-15T10:30:00Z",
  "ended_at": "2024-01-15T10:35:00Z",
  "duration_seconds": 300,
  "status": "completed",
  "agent_type": "general",
  "sentiment": "positive",
  "category": "billing",
  "resolution": "resolved",
  "transcript": [
    {"role": "assistant", "content": "Hello!", "timestamp": 0.5},
    {"role": "user", "content": "Hi, I have a question", "timestamp": 2.0}
  ],
  "analytics": {
    "overall_sentiment": "positive",
    "sentiment_score": 0.8,
    "primary_category": "billing",
    "resolution_status": "resolved",
    "customer_satisfaction_predicted": 4.5,
    "agent_performance_score": 85.0,
    "call_summary": "Customer called about billing...",
    ...
  },
  "recording_url": "https://..."
}
```

#### `GET /api/v1/voice/calls/{call_id}/transcript`
Get just the transcript for a call.

#### `GET /api/v1/voice/calls/{call_id}/analytics`
Get just the analytics for a call.

### Analytics Dashboard

#### `GET /api/v1/analytics/dashboard`
Get comprehensive analytics dashboard.

**Auth:** Required (JWT) - Returns only current user's data

**Query Params:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `days` | int | 7 | Number of days to analyze (1-90) |

**Response:**
```json
{
  "overview": {
    "total_calls": 150,
    "avg_duration_seconds": 245.5,
    "resolution_rate": 78.5,
    "avg_sentiment_score": 0.65,
    "calls_today": 12,
    "calls_this_week": 150
  },
  "sentiment": {
    "positive": 85,
    "neutral": 45,
    "negative": 15,
    "mixed": 5
  },
  "categories": {
    "categories": {
      "billing": 45,
      "technical_support": 38,
      "product_inquiry": 32,
      ...
    }
  },
  "trends": [
    {"date": "2024-01-09", "calls": 20, "avg_sentiment": 0.6, "resolution_rate": 75.0},
    {"date": "2024-01-10", "calls": 22, "avg_sentiment": 0.7, "resolution_rate": 80.0},
    ...
  ],
  "top_issues": [
    {"category": "billing", "count": 45},
    {"category": "technical_support", "count": 38}
  ],
  "recent_calls": [
    {"id": "uuid", "started_at": "...", "duration": 300, "status": "completed", "sentiment": "positive"}
  ]
}
```

#### `GET /api/v1/analytics/cumulative`
Get all-time cumulative analytics (global, not user-specific).

**Response:**
```json
{
  "overview": {
    "total_calls": 5000,
    "total_duration_seconds": 1250000,
    "avg_duration_seconds": 250,
    "total_resolved": 3900,
    "total_escalated": 250,
    "resolution_rate": 78.0,
    "avg_sentiment_score": 0.65,
    "avg_csat": 4.1,
    "avg_agent_score": 82.5,
    "calls_today": 45,
    "calls_this_week": 320,
    "calls_this_month": 1200,
    "calls_vs_last_week": 5.5
  },
  "sentiment": {...},
  "categories": {...},
  "customer_insights": {
    "total_unique_customers": 3500,
    "repeat_caller_rate": 15.5,
    "high_risk_customers": 45,
    "top_pain_points": [...],
    "top_feature_requests": [...]
  },
  "agent_leaderboard": [
    {"agent_type": "general", "total_calls": 5000, "avg_score": 82.5, "avg_resolution_rate": 78.0}
  ],
  "weekly_trends": [...],
  "monthly_trends": [...],
  "top_issues_all_time": [...]
}
```

#### `GET /api/v1/analytics/overview`
Get just overview stats.

#### `GET /api/v1/analytics/sentiment`
Get just sentiment breakdown.

#### `GET /api/v1/analytics/categories`
Get just category breakdown.

#### `GET /api/v1/analytics/trends`
Get daily trends data.

### VAPI Webhooks

#### `POST /api/v1/vapi/webhook`
Main webhook endpoint for VAPI events.

**Auth:** None (webhook from VAPI)

#### `POST /api/v1/vapi/function`
Alternative function call endpoint.

---

## Data Models

### Enums

```python
class CallStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    FAILED = "failed"
    TRANSFERRED = "transferred"

class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"

class ResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    PARTIALLY_RESOLVED = "partially_resolved"
    UNRESOLVED = "unresolved"
    ESCALATED = "escalated"
    FOLLOW_UP_NEEDED = "follow_up_needed"

class UrgencyLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class CustomerType(str, Enum):
    NEW = "new"
    RETURNING = "returning"
    VIP = "vip"
    AT_RISK = "at_risk"
    UNKNOWN = "unknown"
```

### Key Models

See `backend/app/models/voice.py` for complete Pydantic models:

- `CallResponse` - Basic call info
- `CallDetailResponse` - Call with transcript and analytics
- `CallListResponse` - Paginated list of calls
- `AnalyticsDashboard` - User dashboard data
- `CumulativeDashboard` - Global cumulative data
- `CustomerProfile` - Extracted customer information
- `CallAnalytics` - Complete analysis results
- `AgentPerformance` - Agent scoring

---

## Configuration

### Environment Variables

```bash
# VAPI Configuration
VAPI_API_KEY=your-vapi-api-key
VAPI_PUBLIC_KEY=your-vapi-public-key
VAPI_ASSISTANT_ID=your-assistant-id

# OpenRouter (for LLM analysis)
OPENROUTER_API_KEY=your-openrouter-key

# Analysis Model
ANALYSIS_MODEL=google/gemini-2.5-flash-preview

# OpenAI (for embeddings)
OPENAI_API_KEY=your-openai-key

# Pinecone (for RAG)
PINECONE_API_KEY=your-pinecone-key
PINECONE_HOST=https://your-index.svc.pinecone.io

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key
```

### VAPI Assistant Setup

1. Create an assistant in VAPI dashboard
2. Set the webhook URL to `https://your-domain/api/v1/vapi/webhook`
3. Enable function calling with `search_knowledge_base` function
4. Configure the assistant ID in environment variables

### Function Definition for VAPI

Add this function to your VAPI assistant:

```json
{
  "name": "search_knowledge_base",
  "description": "Search the company knowledge base for relevant information to answer customer questions",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "The search query based on what the customer is asking about"
      }
    },
    "required": ["query"]
  }
}
```

---

## Troubleshooting

### Common Issues

**No analytics generated:**
- Check OpenRouter API key is valid
- Verify transcript has >20 characters
- Check logs for LLM parsing errors

**RAG not returning results:**
- Verify Pinecone API key and host
- Check knowledge base has documents in user's namespace
- Ensure embeddings are generated correctly

**Calls not associated with users:**
- Verify `user_id` is passed in call metadata
- Check webhook is receiving metadata correctly
- Look for "No user_id found" in logs

**Webhook not received:**
- Verify webhook URL is publicly accessible
- Check VAPI assistant webhook configuration
- Review VAPI dashboard for webhook delivery status

### Debug Logging

The system logs key events:
```
VAPI webhook received: end-of-call-report
[END OF CALL] Processing call for user_id: abc-123
Processing call call_xyz: status=completed, duration=300s, messages=15
Stored transcript for call call_xyz: 15 messages, 450 words
Starting AI analysis for call call_xyz
Analysis complete for call call_xyz: positive, resolved
```

---

## Future Enhancements

- [ ] Real-time WebSocket updates for live dashboard
- [ ] Multi-agent support with agent-specific analytics
- [ ] Customer profile database with historical tracking
- [ ] Automated follow-up task creation
- [ ] Custom category configuration per user
- [ ] Export analytics to CSV/Excel
- [ ] Slack/email notifications for negative sentiment
