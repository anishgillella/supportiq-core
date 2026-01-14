"""
Call Service - CRUD operations for voice calls and transcripts
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
    caller_id: Optional[str] = None,
    vapi_assistant_id: Optional[str] = None
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
            "caller_id": caller_id,
            "vapi_assistant_id": vapi_assistant_id
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
        ).execute()

        return result.data[0] if result.data else None

    except Exception as e:
        print(f"Error getting call by VAPI ID: {e}")
        return None


async def get_call_by_id(call_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a call by its internal ID with transcript and analytics.
    """
    try:
        supabase = get_supabase()

        result = supabase.table("supportiq_voice_calls").select(
            "*, supportiq_call_transcripts(*), supportiq_call_analytics(*)"
        ).eq("id", call_id).execute()

        return result.data[0] if result.data else None

    except Exception as e:
        print(f"Error getting call by ID: {e}")
        return None


async def list_calls(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    sentiment: Optional[str] = None,
    category: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    List calls with optional filtering.
    """
    try:
        supabase = get_supabase()

        # Build query
        query = supabase.table("supportiq_voice_calls").select(
            "*, supportiq_call_analytics(overall_sentiment, primary_category, resolution_status)",
            count="exact"
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

        # Format response
        calls = []
        for call in (result.data or []):
            analytics = None
            if call.get("supportiq_call_analytics"):
                analytics_list = call["supportiq_call_analytics"]
                if isinstance(analytics_list, list) and analytics_list:
                    analytics = analytics_list[0]
                elif isinstance(analytics_list, dict):
                    analytics = analytics_list

            calls.append({
                "id": call["id"],
                "vapi_call_id": call["vapi_call_id"],
                "started_at": call["started_at"],
                "ended_at": call.get("ended_at"),
                "duration_seconds": call.get("duration_seconds"),
                "status": call["status"],
                "agent_type": call.get("agent_type", "general"),
                "sentiment": analytics.get("overall_sentiment") if analytics else None,
                "category": analytics.get("primary_category") if analytics else None,
                "resolution": analytics.get("resolution_status") if analytics else None,
            })

        return {
            "calls": calls,
            "total": result.count or 0,
            "page": page,
            "page_size": page_size
        }

    except Exception as e:
        print(f"Error listing calls: {e}")
        return {"calls": [], "total": 0, "page": page, "page_size": page_size}


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


async def store_analytics(call_id: str, analytics: Dict[str, Any]) -> bool:
    """
    Store AI-generated analytics for a call.
    """
    try:
        supabase = get_supabase()

        record = {
            "call_id": call_id,
            "overall_sentiment": analytics.get("overall_sentiment", "neutral"),
            "sentiment_score": analytics.get("sentiment_score", 0.0),
            "sentiment_progression": analytics.get("sentiment_progression", []),
            "primary_category": analytics.get("primary_category", "general_inquiry"),
            "secondary_categories": analytics.get("secondary_categories", []),
            "resolution_status": analytics.get("resolution_status", "unresolved"),
            "customer_satisfaction_predicted": analytics.get("customer_satisfaction_predicted", 3.0),
            "agent_performance_score": analytics.get("agent_performance_score", 50.0),
            "customer_intent": analytics.get("customer_intent", ""),
            "key_topics": analytics.get("key_topics", []),
            "action_items": analytics.get("action_items", []),
            "improvement_suggestions": analytics.get("improvement_suggestions", []),
            "call_summary": analytics.get("call_summary", ""),
            "analysis_model": analytics.get("analysis_model", "google/gemini-2.5-flash-preview"),
            "analysis_version": "1.0"
        }

        supabase.table("supportiq_call_analytics").insert(record).execute()

        return True

    except Exception as e:
        print(f"Error storing analytics: {e}")
        return False
