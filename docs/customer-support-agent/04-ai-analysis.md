# Phase 4: AI Transcript Analysis Service

## Overview

This service analyzes call transcripts using Gemini 2.5 Flash via OpenRouter to extract:
- Sentiment (overall + progression)
- Issue categorization
- Resolution status
- Customer satisfaction prediction
- Agent performance scoring
- Improvement suggestions

## File: `backend/app/services/transcript_analysis.py`

```python
"""
Transcript Analysis Service

Uses Gemini 2.5 Flash via OpenRouter to analyze call transcripts
and extract structured insights.
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.services.llm import chat_completion
from app.core.database import get_supabase

# ========================================
# ANALYSIS PROMPT
# ========================================

ANALYSIS_SYSTEM_PROMPT = """You are an expert customer service analyst. Analyze the following call transcript and provide structured insights.

Your analysis must be returned as valid JSON with the following structure:

{
  "overall_sentiment": "positive" | "neutral" | "negative" | "mixed",
  "sentiment_score": <float from -1.0 to 1.0>,
  "sentiment_progression": [
    {"timestamp": <seconds>, "sentiment": "positive" | "neutral" | "negative"}
  ],
  "primary_category": "<main issue category>",
  "secondary_categories": ["<other relevant categories>"],
  "resolution_status": "resolved" | "partially_resolved" | "unresolved" | "escalated" | "follow_up_needed",
  "customer_satisfaction_predicted": <float from 1.0 to 5.0>,
  "agent_performance_score": <float from 0 to 100>,
  "customer_intent": "<what did the customer want?>",
  "key_topics": ["<topic1>", "<topic2>"],
  "action_items": ["<any follow-ups needed>"],
  "improvement_suggestions": ["<how could this call have gone better?>"],
  "call_summary": "<2-3 sentence summary of the call>"
}

CATEGORY OPTIONS (use these or create appropriate ones):
- account_access: Login issues, password reset, 2FA problems
- billing: Payments, invoices, refunds, subscriptions
- technical_support: Bugs, errors, how-to questions
- product_inquiry: Features, pricing, comparisons
- complaint: Dissatisfaction, service issues
- feedback: Suggestions, praise
- general_inquiry: Hours, contact info, other
- cancellation: Account closure, subscription cancellation

SCORING GUIDELINES:

Sentiment Score (-1.0 to 1.0):
- -1.0 = Very negative (angry, frustrated)
- 0.0 = Neutral
- 1.0 = Very positive (happy, satisfied)

Customer Satisfaction (1-5):
- 5 = Extremely satisfied, issue resolved quickly
- 4 = Satisfied, issue resolved
- 3 = Neutral, issue somewhat addressed
- 2 = Dissatisfied, issue not fully resolved
- 1 = Very dissatisfied, negative experience

Agent Performance (0-100):
- 90-100 = Excellent (empathetic, efficient, resolved quickly)
- 70-89 = Good (professional, helpful)
- 50-69 = Average (did the job, room for improvement)
- 30-49 = Below average (issues with handling)
- 0-29 = Poor (unprofessional, unhelpful)

Be objective and base your analysis only on the transcript content."""


# ========================================
# MAIN ANALYSIS FUNCTION
# ========================================

async def analyze_transcript(
    call_id: str,
    transcript_messages: List[Dict[str, Any]],
    full_transcript: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Analyze a call transcript and store the results.

    Args:
        call_id: The UUID of the call in the database
        transcript_messages: List of {role, content, timestamp} messages
        full_transcript: Optional full text transcript

    Returns:
        The analysis results, or None if analysis failed
    """
    try:
        # Format transcript for analysis
        formatted_transcript = format_transcript_for_analysis(transcript_messages, full_transcript)

        if not formatted_transcript or len(formatted_transcript.strip()) < 20:
            print(f"Transcript too short for analysis: {call_id}")
            return None

        # Call LLM for analysis
        analysis_result = await get_llm_analysis(formatted_transcript)

        if not analysis_result:
            print(f"Failed to get LLM analysis for call: {call_id}")
            return None

        # Store in database
        stored = await store_analysis(call_id, analysis_result)

        if stored:
            # Update daily analytics
            await update_daily_analytics(call_id, analysis_result)

        return analysis_result

    except Exception as e:
        print(f"Error analyzing transcript for call {call_id}: {e}")
        return None


# ========================================
# HELPER FUNCTIONS
# ========================================

def format_transcript_for_analysis(
    messages: List[Dict[str, Any]],
    full_transcript: Optional[str] = None
) -> str:
    """
    Format transcript messages into a readable format for analysis.
    """
    if not messages and full_transcript:
        return full_transcript

    if not messages:
        return ""

    lines = []
    for msg in messages:
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "")
        timestamp = msg.get("timestamp", "")

        # Map VAPI roles to readable names
        if role == "ASSISTANT" or role == "BOT":
            role = "AGENT"
        elif role == "USER":
            role = "CUSTOMER"

        time_str = f"[{timestamp}s]" if timestamp else ""
        lines.append(f"{role} {time_str}: {content}")

    return "\n".join(lines)


async def get_llm_analysis(formatted_transcript: str) -> Optional[Dict[str, Any]]:
    """
    Send transcript to Gemini 2.5 Flash for analysis.
    """
    try:
        messages = [
            {
                "role": "user",
                "content": f"Analyze this customer service call transcript:\n\n{formatted_transcript}\n\nProvide your analysis as JSON only, no other text."
            }
        ]

        response = await chat_completion(
            messages=messages,
            system_prompt=ANALYSIS_SYSTEM_PROMPT,
            model="google/gemini-2.5-flash-preview",  # Use Gemini 2.5 Flash
            max_tokens=2048,
            temperature=0.3  # Lower temperature for more consistent analysis
        )

        # Parse JSON from response
        # Handle potential markdown code blocks
        response_text = response.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        analysis = json.loads(response_text.strip())

        # Validate required fields
        required_fields = [
            "overall_sentiment",
            "resolution_status",
            "call_summary"
        ]

        for field in required_fields:
            if field not in analysis:
                print(f"Missing required field in analysis: {field}")
                return None

        return analysis

    except json.JSONDecodeError as e:
        print(f"Failed to parse LLM response as JSON: {e}")
        return None
    except Exception as e:
        print(f"Error in LLM analysis: {e}")
        return None


async def store_analysis(call_id: str, analysis: Dict[str, Any]) -> bool:
    """
    Store the analysis results in the database.
    """
    try:
        supabase = get_supabase()

        record = {
            "call_id": call_id,
            "overall_sentiment": analysis.get("overall_sentiment", "neutral"),
            "sentiment_score": analysis.get("sentiment_score", 0.0),
            "sentiment_progression": analysis.get("sentiment_progression", []),
            "primary_category": analysis.get("primary_category", "general_inquiry"),
            "secondary_categories": analysis.get("secondary_categories", []),
            "resolution_status": analysis.get("resolution_status", "unresolved"),
            "customer_satisfaction_predicted": analysis.get("customer_satisfaction_predicted", 3.0),
            "agent_performance_score": analysis.get("agent_performance_score", 50.0),
            "customer_intent": analysis.get("customer_intent", ""),
            "key_topics": analysis.get("key_topics", []),
            "action_items": analysis.get("action_items", []),
            "improvement_suggestions": analysis.get("improvement_suggestions", []),
            "call_summary": analysis.get("call_summary", ""),
            "analysis_model": "google/gemini-2.5-flash-preview",
            "analysis_version": "1.0"
        }

        result = supabase.table("supportiq_call_analytics").insert(record).execute()

        return bool(result.data)

    except Exception as e:
        print(f"Error storing analysis: {e}")
        return False


async def update_daily_analytics(call_id: str, analysis: Dict[str, Any]) -> bool:
    """
    Update the daily aggregated analytics.
    """
    try:
        supabase = get_supabase()

        # Get call date
        call_result = supabase.table("supportiq_voice_calls").select(
            "started_at, duration_seconds"
        ).eq("id", call_id).single().execute()

        if not call_result.data:
            return False

        call_date = datetime.fromisoformat(
            call_result.data["started_at"].replace("Z", "+00:00")
        ).date().isoformat()

        duration = call_result.data.get("duration_seconds", 0) or 0

        # Get or create daily record
        existing = supabase.table("supportiq_analytics_daily").select("*").eq(
            "date", call_date
        ).is_("user_id", "null").execute()

        sentiment = analysis.get("overall_sentiment", "neutral")
        resolution = analysis.get("resolution_status", "unresolved")
        category = analysis.get("primary_category", "general_inquiry")

        if existing.data:
            # Update existing record
            record = existing.data[0]

            new_total = record["total_calls"] + 1
            new_duration = record["total_duration_seconds"] + duration

            updates = {
                "total_calls": new_total,
                "completed_calls": record["completed_calls"] + 1,
                "total_duration_seconds": new_duration,
                "avg_duration_seconds": new_duration / new_total,
                "resolved_calls": record["resolved_calls"] + (1 if resolution == "resolved" else 0),
                "escalated_calls": record["escalated_calls"] + (1 if resolution == "escalated" else 0),
                "positive_calls": record["positive_calls"] + (1 if sentiment == "positive" else 0),
                "neutral_calls": record["neutral_calls"] + (1 if sentiment == "neutral" else 0),
                "negative_calls": record["negative_calls"] + (1 if sentiment == "negative" else 0),
            }

            # Update resolution rate
            total_analyzed = updates["resolved_calls"] + updates["escalated_calls"] + (
                record["total_calls"] - record["resolved_calls"] - record["escalated_calls"]
            )
            if total_analyzed > 0:
                updates["resolution_rate"] = updates["resolved_calls"] / new_total * 100

            # Update category breakdown
            categories = record.get("category_breakdown", {}) or {}
            categories[category] = categories.get(category, 0) + 1
            updates["category_breakdown"] = categories

            supabase.table("supportiq_analytics_daily").update(updates).eq(
                "id", record["id"]
            ).execute()

        else:
            # Create new record
            new_record = {
                "date": call_date,
                "user_id": None,
                "total_calls": 1,
                "completed_calls": 1,
                "abandoned_calls": 0,
                "total_duration_seconds": duration,
                "avg_duration_seconds": duration,
                "resolved_calls": 1 if resolution == "resolved" else 0,
                "escalated_calls": 1 if resolution == "escalated" else 0,
                "resolution_rate": 100 if resolution == "resolved" else 0,
                "positive_calls": 1 if sentiment == "positive" else 0,
                "neutral_calls": 1 if sentiment == "neutral" else 0,
                "negative_calls": 1 if sentiment == "negative" else 0,
                "avg_sentiment_score": analysis.get("sentiment_score", 0.0),
                "category_breakdown": {category: 1}
            }

            supabase.table("supportiq_analytics_daily").insert(new_record).execute()

        return True

    except Exception as e:
        print(f"Error updating daily analytics: {e}")
        return False


# ========================================
# BATCH RE-ANALYSIS
# ========================================

async def reanalyze_call(call_id: str) -> Optional[Dict[str, Any]]:
    """
    Re-analyze an existing call (useful for model updates).
    """
    supabase = get_supabase()

    # Get transcript
    transcript_result = supabase.table("supportiq_call_transcripts").select(
        "transcript"
    ).eq("call_id", call_id).single().execute()

    if not transcript_result.data:
        return None

    messages = transcript_result.data.get("transcript", [])

    # Delete existing analysis
    supabase.table("supportiq_call_analytics").delete().eq("call_id", call_id).execute()

    # Re-analyze
    return await analyze_transcript(call_id, messages)


async def batch_analyze_pending() -> int:
    """
    Analyze all calls that don't have analytics yet.
    Returns the number of calls analyzed.
    """
    supabase = get_supabase()

    # Find calls without analytics
    calls_result = supabase.table("supportiq_voice_calls").select(
        "id"
    ).eq("status", "completed").execute()

    if not calls_result.data:
        return 0

    call_ids = [c["id"] for c in calls_result.data]

    # Find which have analytics
    analytics_result = supabase.table("supportiq_call_analytics").select(
        "call_id"
    ).in_("call_id", call_ids).execute()

    analyzed_ids = {a["call_id"] for a in (analytics_result.data or [])}

    # Find pending
    pending_ids = [cid for cid in call_ids if cid not in analyzed_ids]

    # Analyze each
    analyzed_count = 0
    for call_id in pending_ids:
        result = await reanalyze_call(call_id)
        if result:
            analyzed_count += 1

    return analyzed_count
```

## Call Service Helper (`backend/app/services/call_service.py`)

```python
"""
Call Service

Handles CRUD operations for voice calls and transcripts.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from app.core.database import get_supabase


async def create_call(
    vapi_call_id: str,
    started_at: str,
    ended_at: Optional[str] = None,
    duration_seconds: Optional[int] = None,
    status: str = "completed",
    agent_type: str = "general",
    recording_url: Optional[str] = None,
    caller_phone: Optional[str] = None,
    caller_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Create a new voice call record.
    """
    try:
        supabase = get_supabase()

        record = {
            "vapi_call_id": vapi_call_id,
            "started_at": started_at,
            "ended_at": ended_at,
            "duration_seconds": duration_seconds,
            "status": status,
            "agent_type": agent_type,
            "recording_url": recording_url,
            "caller_phone": caller_phone,
            "caller_id": caller_id
        }

        # Remove None values
        record = {k: v for k, v in record.items() if v is not None}

        result = supabase.table("supportiq_voice_calls").insert(record).execute()

        return result.data[0] if result.data else None

    except Exception as e:
        print(f"Error creating call record: {e}")
        return None


async def create_transcript(
    call_id: str,
    transcript: List[Dict[str, Any]],
    word_count: int = 0,
    turn_count: int = 0,
    raw_vapi_response: Optional[Dict] = None
) -> Optional[Dict[str, Any]]:
    """
    Create a transcript record for a call.
    """
    try:
        supabase = get_supabase()

        record = {
            "call_id": call_id,
            "transcript": transcript,
            "word_count": word_count,
            "turn_count": turn_count,
            "raw_vapi_response": raw_vapi_response
        }

        result = supabase.table("supportiq_call_transcripts").insert(record).execute()

        return result.data[0] if result.data else None

    except Exception as e:
        print(f"Error creating transcript record: {e}")
        return None


async def get_call_by_vapi_id(vapi_call_id: str) -> Optional[Dict[str, Any]]:
    """
    Find a call by its VAPI call ID.
    """
    try:
        supabase = get_supabase()

        result = supabase.table("supportiq_voice_calls").select("*").eq(
            "vapi_call_id", vapi_call_id
        ).single().execute()

        return result.data

    except Exception as e:
        print(f"Error getting call by VAPI ID: {e}")
        return None


async def update_call_status(
    call_id: str,
    status: str,
    ended_at: Optional[str] = None,
    duration_seconds: Optional[int] = None
) -> bool:
    """
    Update a call's status.
    """
    try:
        supabase = get_supabase()

        updates = {"status": status}
        if ended_at:
            updates["ended_at"] = ended_at
        if duration_seconds is not None:
            updates["duration_seconds"] = duration_seconds

        supabase.table("supportiq_voice_calls").update(updates).eq("id", call_id).execute()

        return True

    except Exception as e:
        print(f"Error updating call status: {e}")
        return False
```

## Configuration Update

Add to `backend/app/core/config.py`:

```python
# Add to Settings class:
vapi_api_key: str = ""
vapi_public_key: str = ""
vapi_assistant_id: str = ""
vapi_webhook_secret: str = ""

# Update default LLM model for analysis
analysis_model: str = "google/gemini-2.5-flash-preview"
```

## Testing the Analysis

### Manual Test Script

```python
# test_analysis.py
import asyncio
from app.services.transcript_analysis import analyze_transcript

test_messages = [
    {"role": "assistant", "content": "Hello, thank you for calling SupportIQ. How can I help you today?", "timestamp": 0},
    {"role": "user", "content": "Hi, I'm having trouble logging into my account. It keeps saying my password is wrong.", "timestamp": 3},
    {"role": "assistant", "content": "I'm sorry to hear you're having trouble. I'd be happy to help you reset your password. Can you confirm the email address associated with your account?", "timestamp": 8},
    {"role": "user", "content": "Sure, it's john@example.com", "timestamp": 15},
    {"role": "assistant", "content": "Thank you. I've sent a password reset link to that email. You should receive it within a few minutes. Is there anything else I can help you with?", "timestamp": 20},
    {"role": "user", "content": "No, that's all. Thanks for your help!", "timestamp": 28},
    {"role": "assistant", "content": "You're welcome! Have a great day!", "timestamp": 31}
]

async def main():
    result = await analyze_transcript(
        call_id="test-call-123",
        transcript_messages=test_messages
    )
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
```

### Expected Output

```json
{
  "overall_sentiment": "positive",
  "sentiment_score": 0.7,
  "sentiment_progression": [
    {"timestamp": 0, "sentiment": "neutral"},
    {"timestamp": 3, "sentiment": "negative"},
    {"timestamp": 15, "sentiment": "neutral"},
    {"timestamp": 28, "sentiment": "positive"}
  ],
  "primary_category": "account_access",
  "secondary_categories": ["password_reset"],
  "resolution_status": "resolved",
  "customer_satisfaction_predicted": 4.5,
  "agent_performance_score": 92,
  "customer_intent": "Customer wanted to regain access to their account after forgetting password",
  "key_topics": ["password reset", "account access", "email verification"],
  "action_items": [],
  "improvement_suggestions": [
    "Could proactively offer 2FA setup after password reset",
    "Consider mentioning password requirements for the new password"
  ],
  "call_summary": "Customer called about login issues due to forgotten password. Agent efficiently helped reset the password by sending a reset link. Customer was satisfied with the quick resolution."
}
```

## Next Steps

After implementing the analysis service:
1. Build the frontend dashboard (Phase 5)
2. Test end-to-end with VAPI
