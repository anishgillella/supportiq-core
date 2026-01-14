# SupportIQ Voice Agent - Overview

## Project Summary

SupportIQ Voice Agent is an AI-powered customer support system that:
1. Handles voice calls through a web-based interface (click-to-call)
2. Uses RAG (Retrieval Augmented Generation) to answer questions from your knowledge base
3. Captures and stores call transcripts
4. Analyzes calls for insights (sentiment, issue category, resolution status)
5. Provides analytics dashboards for managers, business owners, and QA analysts

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js)                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ /dashboard  │  │ /dashboard/ │  │ /chat       │  │ Voice       │    │
│  │ (Analytics) │  │ calls/[id]  │  │ (Text Chat) │  │ Widget      │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
         │                   │                              │
         │                   │                              │
         ▼                   ▼                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (FastAPI)                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ /api/v1/    │  │ /api/v1/    │  │ /api/v1/    │  │ /api/v1/    │    │
│  │ analytics   │  │ voice/calls │  │ vapi/webhook│  │ chat        │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
│         │                │                │                │            │
│         └────────────────┴────────────────┴────────────────┘            │
│                                   │                                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      SERVICES LAYER                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │   │
│  │  │ transcript  │  │ call        │  │ llm.py      │              │   │
│  │  │ _analysis.py│  │ _service.py │  │ (Gemini 2.5)│              │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
         │                                        │
         ▼                                        ▼
┌─────────────────────┐                ┌─────────────────────┐
│   SUPABASE          │                │   PINECONE          │
│   (PostgreSQL)      │                │   (Vector DB)       │
│                     │                │                     │
│ - voice_calls       │                │ - Knowledge base    │
│ - call_transcripts  │                │   embeddings        │
│ - call_analytics    │                │                     │
└─────────────────────┘                └─────────────────────┘
         ▲
         │
┌─────────────────────┐
│      VAPI.ai        │
│  (Voice Platform)   │
│                     │
│ - WebRTC calls      │
│ - Speech-to-text    │
│ - Text-to-speech    │
│ - Transcript export │
└─────────────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Next.js 16, React 18, Tailwind CSS |
| Backend | FastAPI (Python 3.11+) |
| Database | Supabase (PostgreSQL) |
| Vector DB | Pinecone |
| LLM | Gemini 2.5 Flash via OpenRouter |
| Voice | VAPI.ai |
| Embeddings | OpenAI text-embedding-3-small |

## Feature Set

### MVP Features (Phase 1)
- [ ] Click-to-call voice widget on frontend
- [ ] Single general-purpose voice agent
- [ ] RAG integration for answering questions
- [ ] Transcript capture and storage
- [ ] Post-call AI analysis
- [ ] Analytics dashboard

### Future Features (Phase 2)
- [ ] Multiple specialized agents (billing, technical, general)
- [ ] Smart routing based on intent
- [ ] Real-time sentiment alerts
- [ ] Customer journey tracking
- [ ] Knowledge gap detection

## Documentation Structure

| Document | Description |
|----------|-------------|
| 01-database-schema.md | Database tables for voice calls and analytics |
| 02-vapi-configuration.md | VAPI agent setup and configuration |
| 03-backend-api.md | FastAPI endpoints and webhook handlers |
| 04-ai-analysis.md | Transcript analysis service |
| 05-frontend-dashboard.md | Dashboard UI components |
| 06-deployment.md | Deployment and environment setup |

## Quick Start (After Implementation)

```bash
# 1. Add VAPI credentials to .env
VAPI_API_KEY=your_key
VAPI_ASSISTANT_ID=your_assistant_id

# 2. Run database migrations
psql -f backend/migrations/voice_calls.sql

# 3. Start backend
cd backend && uvicorn app.main:app --reload

# 4. Start frontend
cd frontend && npm run dev

# 5. Access dashboard
open http://localhost:3000/dashboard
```
