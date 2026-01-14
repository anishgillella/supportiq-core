# Phase 3: Backend API & Webhook Implementation

## Overview

This document details the FastAPI endpoints needed for:
1. VAPI webhook handlers
2. Voice call CRUD operations
3. Analytics data retrieval

## File Structure

```
backend/app/
├── api/v1/
│   ├── vapi.py          # VAPI webhook handlers
│   ├── voice_calls.py   # Call management endpoints
│   └── analytics.py     # Analytics endpoints
├── models/
│   └── voice.py         # Pydantic models
└── services/
    ├── call_service.py  # Call business logic
    └── transcript_analysis.py  # AI analysis
```

## 1. VAPI Webhook Router (`api/v1/vapi.py`)

### 1.1 Webhook Endpoint

```python
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

router = APIRouter(prefix="/vapi", tags=["VAPI"])

# ========================================
# MODELS
# ========================================

class VAPIMessage(BaseModel):
    type: str
    call: Optional[Dict[str, Any]] = None
    transcript: Optional[str] = None
    messages: Optional[List[Dict[str, Any]]] = None
    functionCall: Optional[Dict[str, Any]] = None

class FunctionCallRequest(BaseModel):
    name: str
    parameters: Dict[str, Any]

# ========================================
# WEBHOOK ENDPOINT
# ========================================

@router.post("/webhook")
async def vapi_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Main webhook endpoint for VAPI events.

    Handles:
    - assistant-request: Called when VAPI needs context (RAG)
    - end-of-call-report: Called when call ends with transcript
    - function-call: Called when assistant invokes a function
    - status-update: Real-time call status updates
    """
    try:
        body = await request.json()
        message_type = body.get("message", {}).get("type", "")

        if message_type == "assistant-request":
            return await handle_assistant_request(body)

        elif message_type == "end-of-call-report":
            # Process in background to respond quickly to VAPI
            background_tasks.add_task(handle_end_of_call, body)
            return {"status": "processing"}

        elif message_type == "function-call":
            return await handle_function_call(body)

        elif message_type == "status-update":
            await handle_status_update(body)
            return {"status": "ok"}

        else:
            # Log unknown message types for debugging
            print(f"Unknown VAPI message type: {message_type}")
            return {"status": "ok"}

    except Exception as e:
        print(f"VAPI webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# HANDLER: ASSISTANT REQUEST (RAG CONTEXT)
# ========================================

async def handle_assistant_request(body: dict) -> dict:
    """
    Inject RAG context into the assistant's system prompt.
    Called at the start of each call or turn.
    """
    call_data = body.get("message", {}).get("call", {})

    # Get customer ID if available (from metadata)
    customer_id = call_data.get("metadata", {}).get("customer_id")

    # Get company name for context
    company_name = "SupportIQ"  # Default, could be dynamic

    # Return modified assistant configuration
    return {
        "assistant": {
            "model": {
                "provider": "openrouter",
                "model": "google/gemini-2.5-flash-preview",
                "temperature": 0.7,
                "maxTokens": 1024
            }
        }
    }


# ========================================
# HANDLER: FUNCTION CALL (RAG SEARCH)
# ========================================

async def handle_function_call(body: dict) -> dict:
    """
    Handle function calls from the assistant.
    Primary use: search_knowledge_base for RAG.
    """
    from app.services.pinecone_service import query_vectors
    from app.services.embeddings import generate_embedding
    from app.core.database import get_supabase

    function_call = body.get("message", {}).get("functionCall", {})
    function_name = function_call.get("name")
    parameters = function_call.get("parameters", {})

    if function_name == "search_knowledge_base":
        query = parameters.get("query", "")

        if not query:
            return {
                "result": "I need more information to search. Could you please clarify your question?"
            }

        try:
            # Generate embedding for query
            query_embedding = await generate_embedding(query)

            # Search Pinecone
            results = await query_vectors(query_embedding, top_k=3)

            if not results:
                return {
                    "result": "I couldn't find specific information about that in our knowledge base. Let me try to help you another way."
                }

            # Format results for voice response
            context_parts = []
            for match in results:
                content = match.get("metadata", {}).get("content", "")
                if content:
                    context_parts.append(content)

            context = "\n\n".join(context_parts)

            return {
                "result": f"Based on our knowledge base: {context}"
            }

        except Exception as e:
            print(f"Knowledge base search error: {e}")
            return {
                "result": "I'm having trouble searching our knowledge base right now. Let me help you in another way."
            }

    return {"result": "I'm not sure how to handle that request."}


# ========================================
# HANDLER: END OF CALL REPORT
# ========================================

async def handle_end_of_call(body: dict):
    """
    Process the end-of-call report from VAPI.

    1. Store call metadata
    2. Store transcript
    3. Trigger AI analysis (async)
    """
    from app.services.call_service import create_call, create_transcript
    from app.services.transcript_analysis import analyze_transcript
    from app.core.database import get_supabase

    try:
        message = body.get("message", {})
        call_data = message.get("call", {})

        # Extract call info
        vapi_call_id = call_data.get("id")
        started_at = call_data.get("startedAt")
        ended_at = call_data.get("endedAt")

        # Calculate duration
        duration = None
        if started_at and ended_at:
            start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            end = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
            duration = int((end - start).total_seconds())

        # Extract transcript
        transcript = message.get("transcript", "")
        messages = message.get("messages", [])

        # Create call record
        call_record = await create_call(
            vapi_call_id=vapi_call_id,
            started_at=started_at,
            ended_at=ended_at,
            duration_seconds=duration,
            status="completed",
            agent_type="general",
            recording_url=call_data.get("recordingUrl")
        )

        if not call_record:
            print(f"Failed to create call record for {vapi_call_id}")
            return

        # Create transcript record
        transcript_record = await create_transcript(
            call_id=call_record["id"],
            transcript=messages,
            word_count=len(transcript.split()) if transcript else 0,
            turn_count=len(messages)
        )

        # Trigger AI analysis in background
        if transcript or messages:
            await analyze_transcript(
                call_id=call_record["id"],
                transcript_messages=messages,
                full_transcript=transcript
            )

        print(f"Successfully processed call {vapi_call_id}")

    except Exception as e:
        print(f"Error processing end of call: {e}")


# ========================================
# HANDLER: STATUS UPDATE
# ========================================

async def handle_status_update(body: dict):
    """
    Handle real-time status updates during a call.
    Useful for live dashboards (future feature).
    """
    message = body.get("message", {})
    status = message.get("status")
    call_id = message.get("call", {}).get("id")

    # For now, just log
    print(f"Call {call_id} status: {status}")

    # Future: broadcast to WebSocket for live dashboard
```

### 1.2 Function Endpoint (Alternative)

Some VAPI configurations use a separate endpoint for functions:

```python
@router.post("/function")
async def vapi_function(request: Request):
    """
    Separate endpoint for function calls if configured in VAPI.
    """
    body = await request.json()
    return await handle_function_call(body)
```

## 2. Voice Calls Router (`api/v1/voice_calls.py`)

```python
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel

router = APIRouter(prefix="/voice/calls", tags=["Voice Calls"])

# ========================================
# MODELS
# ========================================

class CallResponse(BaseModel):
    id: str
    vapi_call_id: str
    started_at: datetime
    ended_at: Optional[datetime]
    duration_seconds: Optional[int]
    status: str
    agent_type: str
    # Joined data
    sentiment: Optional[str] = None
    category: Optional[str] = None
    resolution: Optional[str] = None

class CallDetailResponse(CallResponse):
    transcript: Optional[List[dict]] = None
    analytics: Optional[dict] = None
    recording_url: Optional[str] = None

class CallListResponse(BaseModel):
    calls: List[CallResponse]
    total: int
    page: int
    page_size: int

# ========================================
# ENDPOINTS
# ========================================

@router.get("", response_model=CallListResponse)
async def list_calls(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    sentiment: Optional[str] = None,
    category: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
):
    """
    List all voice calls with optional filtering.
    """
    from app.core.database import get_supabase

    supabase = get_supabase()

    # Build query
    query = supabase.table("supportiq_voice_calls").select(
        "*, supportiq_call_analytics(overall_sentiment, primary_category, resolution_status)"
    )

    # Apply filters
    if status:
        query = query.eq("status", status)
    if date_from:
        query = query.gte("started_at", date_from.isoformat())
    if date_to:
        query = query.lte("started_at", date_to.isoformat())

    # Pagination
    offset = (page - 1) * page_size
    query = query.order("started_at", desc=True).range(offset, offset + page_size - 1)

    result = query.execute()

    # Get total count
    count_result = supabase.table("supportiq_voice_calls").select("id", count="exact").execute()
    total = count_result.count or 0

    # Format response
    calls = []
    for call in result.data:
        analytics = call.get("supportiq_call_analytics", [{}])[0] if call.get("supportiq_call_analytics") else {}
        calls.append(CallResponse(
            id=call["id"],
            vapi_call_id=call["vapi_call_id"],
            started_at=call["started_at"],
            ended_at=call.get("ended_at"),
            duration_seconds=call.get("duration_seconds"),
            status=call["status"],
            agent_type=call.get("agent_type", "general"),
            sentiment=analytics.get("overall_sentiment"),
            category=analytics.get("primary_category"),
            resolution=analytics.get("resolution_status")
        ))

    return CallListResponse(
        calls=calls,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{call_id}", response_model=CallDetailResponse)
async def get_call(call_id: str):
    """
    Get detailed information about a specific call.
    Includes transcript and full analytics.
    """
    from app.core.database import get_supabase

    supabase = get_supabase()

    # Get call with related data
    result = supabase.table("supportiq_voice_calls").select(
        "*, supportiq_call_transcripts(*), supportiq_call_analytics(*)"
    ).eq("id", call_id).single().execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Call not found")

    call = result.data
    transcript_data = call.get("supportiq_call_transcripts", [{}])[0] if call.get("supportiq_call_transcripts") else {}
    analytics_data = call.get("supportiq_call_analytics", [{}])[0] if call.get("supportiq_call_analytics") else {}

    return CallDetailResponse(
        id=call["id"],
        vapi_call_id=call["vapi_call_id"],
        started_at=call["started_at"],
        ended_at=call.get("ended_at"),
        duration_seconds=call.get("duration_seconds"),
        status=call["status"],
        agent_type=call.get("agent_type", "general"),
        sentiment=analytics_data.get("overall_sentiment"),
        category=analytics_data.get("primary_category"),
        resolution=analytics_data.get("resolution_status"),
        transcript=transcript_data.get("transcript"),
        analytics=analytics_data,
        recording_url=call.get("recording_url")
    )
```

## 3. Analytics Router (`api/v1/analytics.py`)

```python
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from typing import Dict, List

router = APIRouter(prefix="/analytics", tags=["Analytics"])

# ========================================
# MODELS
# ========================================

class OverviewStats(BaseModel):
    total_calls: int
    avg_duration_seconds: float
    resolution_rate: float
    avg_sentiment_score: float
    calls_today: int
    calls_this_week: int

class SentimentBreakdown(BaseModel):
    positive: int
    neutral: int
    negative: int
    mixed: int

class CategoryBreakdown(BaseModel):
    categories: Dict[str, int]

class TrendDataPoint(BaseModel):
    date: str
    calls: int
    avg_sentiment: float
    resolution_rate: float

class AnalyticsDashboard(BaseModel):
    overview: OverviewStats
    sentiment: SentimentBreakdown
    categories: CategoryBreakdown
    trends: List[TrendDataPoint]
    top_issues: List[Dict]
    recent_calls: List[Dict]

# ========================================
# ENDPOINTS
# ========================================

@router.get("/dashboard", response_model=AnalyticsDashboard)
async def get_dashboard(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze")
):
    """
    Get comprehensive analytics dashboard data.
    """
    from app.core.database import get_supabase

    supabase = get_supabase()
    start_date = datetime.utcnow() - timedelta(days=days)

    # Get calls with analytics
    result = supabase.table("supportiq_voice_calls").select(
        "*, supportiq_call_analytics(*)"
    ).gte("started_at", start_date.isoformat()).execute()

    calls = result.data or []

    # Calculate overview stats
    total_calls = len(calls)
    total_duration = sum(c.get("duration_seconds", 0) or 0 for c in calls)
    avg_duration = total_duration / total_calls if total_calls > 0 else 0

    # Get analytics data
    analytics_list = []
    for call in calls:
        analytics = call.get("supportiq_call_analytics", [])
        if analytics:
            analytics_list.append(analytics[0])

    # Resolution rate
    resolved = sum(1 for a in analytics_list if a.get("resolution_status") == "resolved")
    resolution_rate = (resolved / len(analytics_list) * 100) if analytics_list else 0

    # Sentiment
    sentiment_scores = [a.get("sentiment_score", 0) for a in analytics_list if a.get("sentiment_score") is not None]
    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0

    # Sentiment breakdown
    sentiment_breakdown = {"positive": 0, "neutral": 0, "negative": 0, "mixed": 0}
    for a in analytics_list:
        s = a.get("overall_sentiment", "neutral")
        if s in sentiment_breakdown:
            sentiment_breakdown[s] += 1

    # Category breakdown
    category_counts = {}
    for a in analytics_list:
        cat = a.get("primary_category", "unknown")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    # Calls today and this week
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    calls_today = sum(1 for c in calls if datetime.fromisoformat(c["started_at"].replace("Z", "+00:00")).date() == today)
    calls_this_week = total_calls  # Already filtered by days param

    # Trends (daily)
    trends = []
    for i in range(days):
        day = (datetime.utcnow() - timedelta(days=days-i-1)).date()
        day_calls = [c for c in calls if datetime.fromisoformat(c["started_at"].replace("Z", "+00:00")).date() == day]
        day_analytics = []
        for c in day_calls:
            if c.get("supportiq_call_analytics"):
                day_analytics.extend(c["supportiq_call_analytics"])

        day_resolved = sum(1 for a in day_analytics if a.get("resolution_status") == "resolved")
        day_sentiments = [a.get("sentiment_score", 0) for a in day_analytics if a.get("sentiment_score")]

        trends.append(TrendDataPoint(
            date=day.isoformat(),
            calls=len(day_calls),
            avg_sentiment=sum(day_sentiments) / len(day_sentiments) if day_sentiments else 0,
            resolution_rate=(day_resolved / len(day_analytics) * 100) if day_analytics else 0
        ))

    # Top issues (by category)
    top_issues = sorted(
        [{"category": k, "count": v} for k, v in category_counts.items()],
        key=lambda x: x["count"],
        reverse=True
    )[:5]

    # Recent calls
    recent = sorted(calls, key=lambda x: x["started_at"], reverse=True)[:5]
    recent_calls = [
        {
            "id": c["id"],
            "started_at": c["started_at"],
            "duration": c.get("duration_seconds"),
            "status": c["status"],
            "sentiment": c.get("supportiq_call_analytics", [{}])[0].get("overall_sentiment") if c.get("supportiq_call_analytics") else None
        }
        for c in recent
    ]

    return AnalyticsDashboard(
        overview=OverviewStats(
            total_calls=total_calls,
            avg_duration_seconds=avg_duration,
            resolution_rate=resolution_rate,
            avg_sentiment_score=avg_sentiment,
            calls_today=calls_today,
            calls_this_week=calls_this_week
        ),
        sentiment=SentimentBreakdown(**sentiment_breakdown),
        categories=CategoryBreakdown(categories=category_counts),
        trends=trends,
        top_issues=top_issues,
        recent_calls=recent_calls
    )


@router.get("/overview")
async def get_overview_stats(days: int = Query(7, ge=1, le=90)):
    """
    Get quick overview statistics only.
    """
    dashboard = await get_dashboard(days=days)
    return dashboard.overview
```

## 4. Register Routers in `main.py`

Add to `backend/app/main.py`:

```python
from app.api.v1 import vapi, voice_calls, analytics

# ... existing code ...

# Register new routers
app.include_router(vapi.router, prefix="/api/v1")
app.include_router(voice_calls.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
```

## 5. API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/vapi/webhook` | VAPI webhook handler |
| POST | `/api/v1/vapi/function` | VAPI function calls (optional) |
| GET | `/api/v1/voice/calls` | List all calls with filtering |
| GET | `/api/v1/voice/calls/{id}` | Get call details with transcript |
| GET | `/api/v1/analytics/dashboard` | Full dashboard data |
| GET | `/api/v1/analytics/overview` | Quick stats only |

## Next Steps

After implementing the API:
1. Create the transcript analysis service (Phase 4)
2. Build the frontend dashboard (Phase 5)
