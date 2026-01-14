"""
Voice Calls API Router

Endpoints for managing and retrieving voice call data.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime

from app.services.call_service import list_calls, get_call_by_id
from app.models.voice import CallListResponse, CallDetailResponse, CallResponse

router = APIRouter(prefix="/voice/calls", tags=["Voice Calls"])


@router.get("", response_model=CallListResponse)
async def get_calls(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    sentiment: Optional[str] = Query(None, description="Filter by sentiment"),
    category: Optional[str] = Query(None, description="Filter by category"),
    date_from: Optional[datetime] = Query(None, description="Start date filter"),
    date_to: Optional[datetime] = Query(None, description="End date filter"),
):
    """
    List all voice calls with optional filtering and pagination.
    """
    result = await list_calls(
        page=page,
        page_size=page_size,
        status=status,
        sentiment=sentiment,
        category=category,
        date_from=date_from,
        date_to=date_to
    )

    return CallListResponse(**result)


@router.get("/{call_id}")
async def get_call(call_id: str):
    """
    Get detailed information about a specific call.
    Includes transcript and full analytics.
    """
    call = await get_call_by_id(call_id)

    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    # Extract nested data
    transcript_data = None
    analytics_data = None

    if call.get("supportiq_call_transcripts"):
        transcripts = call["supportiq_call_transcripts"]
        if isinstance(transcripts, list) and transcripts:
            transcript_data = transcripts[0].get("transcript", [])
        elif isinstance(transcripts, dict):
            transcript_data = transcripts.get("transcript", [])

    if call.get("supportiq_call_analytics"):
        analytics = call["supportiq_call_analytics"]
        if isinstance(analytics, list) and analytics:
            analytics_data = analytics[0]
        elif isinstance(analytics, dict):
            analytics_data = analytics

    return {
        "id": call["id"],
        "vapi_call_id": call["vapi_call_id"],
        "started_at": call["started_at"],
        "ended_at": call.get("ended_at"),
        "duration_seconds": call.get("duration_seconds"),
        "status": call["status"],
        "agent_type": call.get("agent_type", "general"),
        "sentiment": analytics_data.get("overall_sentiment") if analytics_data else None,
        "category": analytics_data.get("primary_category") if analytics_data else None,
        "resolution": analytics_data.get("resolution_status") if analytics_data else None,
        "transcript": transcript_data,
        "analytics": analytics_data,
        "recording_url": call.get("recording_url")
    }


@router.get("/{call_id}/transcript")
async def get_call_transcript(call_id: str):
    """
    Get just the transcript for a specific call.
    """
    call = await get_call_by_id(call_id)

    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    transcript_data = None
    if call.get("supportiq_call_transcripts"):
        transcripts = call["supportiq_call_transcripts"]
        if isinstance(transcripts, list) and transcripts:
            transcript_data = transcripts[0]
        elif isinstance(transcripts, dict):
            transcript_data = transcripts

    if not transcript_data:
        raise HTTPException(status_code=404, detail="Transcript not found")

    return {
        "call_id": call_id,
        "transcript": transcript_data.get("transcript", []),
        "word_count": transcript_data.get("word_count", 0),
        "turn_count": transcript_data.get("turn_count", 0)
    }


@router.get("/{call_id}/analytics")
async def get_call_analytics(call_id: str):
    """
    Get just the analytics for a specific call.
    """
    call = await get_call_by_id(call_id)

    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    analytics_data = None
    if call.get("supportiq_call_analytics"):
        analytics = call["supportiq_call_analytics"]
        if isinstance(analytics, list) and analytics:
            analytics_data = analytics[0]
        elif isinstance(analytics, dict):
            analytics_data = analytics

    if not analytics_data:
        raise HTTPException(status_code=404, detail="Analytics not found")

    return {
        "call_id": call_id,
        **analytics_data
    }
