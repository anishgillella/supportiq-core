"""
Voice Calls API Router

Endpoints for managing and retrieving voice call data.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
import httpx

from app.services.call_service import list_calls, get_call_by_id
from app.models.voice import CallListResponse, CallDetailResponse, CallResponse
from app.core.security import get_current_user, TokenData
from app.core.config import settings

router = APIRouter(prefix="/voice/calls", tags=["Voice Calls"])


class InitiateCallRequest(BaseModel):
    """Request to initiate a voice call"""
    phone_number: Optional[str] = None  # For outbound calls
    assistant_id: Optional[str] = None  # Override default assistant


class InitiateCallResponse(BaseModel):
    """Response from call initiation"""
    success: bool
    call_id: Optional[str] = None
    web_call_url: Optional[str] = None
    message: str


@router.post("/initiate", response_model=InitiateCallResponse)
async def initiate_call(
    request: InitiateCallRequest = None,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Initiate a voice call via VAPI.

    The user_id is automatically passed as metadata so the voice agent
    can access the correct knowledge base namespace.

    For web calls (browser-based), returns a web_call_url.
    For phone calls, provide a phone_number.
    """
    try:
        assistant_id = request.assistant_id if request else None
        assistant_id = assistant_id or settings.vapi_assistant_id

        if not assistant_id:
            raise HTTPException(
                status_code=400,
                detail="No VAPI assistant configured. Set VAPI_ASSISTANT_ID in environment."
            )

        if not settings.vapi_api_key:
            raise HTTPException(
                status_code=400,
                detail="VAPI API key not configured."
            )

        # Debug: Print first/last 4 chars of API key to verify correct key is loaded
        api_key = settings.vapi_api_key
        print(f"Using VAPI API key: {api_key[:4]}...{api_key[-4:]}")

        # Build call payload with user_id in metadata
        # This metadata will be available in all webhook events
        call_payload = {
            "assistantId": assistant_id,
            "metadata": {
                "user_id": current_user.user_id,
                "initiated_from": "dashboard"
            }
        }

        # Add phone number for outbound calls
        if request and request.phone_number:
            call_payload["customer"] = {
                "number": request.phone_number
            }

        # Create call via VAPI API
        async with httpx.AsyncClient() as client:
            # For web calls, use the web-call endpoint
            if not (request and request.phone_number):
                response = await client.post(
                    "https://api.vapi.ai/call/web",
                    headers={
                        "Authorization": f"Bearer {settings.vapi_api_key}",
                        "Content-Type": "application/json"
                    },
                    json=call_payload,
                    timeout=30.0
                )
            else:
                # For phone calls
                response = await client.post(
                    "https://api.vapi.ai/call",
                    headers={
                        "Authorization": f"Bearer {settings.vapi_api_key}",
                        "Content-Type": "application/json"
                    },
                    json=call_payload,
                    timeout=30.0
                )

        if response.status_code not in [200, 201]:
            error_detail = response.text
            print(f"VAPI call initiation failed: {response.status_code} - {error_detail}")
            return InitiateCallResponse(
                success=False,
                message=f"Failed to initiate call: {error_detail}"
            )

        result = response.json()

        return InitiateCallResponse(
            success=True,
            call_id=result.get("id"),
            web_call_url=result.get("webCallUrl"),
            message="Call initiated successfully"
        )

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="VAPI request timed out")
    except Exception as e:
        print(f"Error initiating call: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=CallListResponse)
async def get_calls(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    sentiment: Optional[str] = Query(None, description="Filter by sentiment"),
    category: Optional[str] = Query(None, description="Filter by category"),
    date_from: Optional[datetime] = Query(None, description="Start date filter"),
    date_to: Optional[datetime] = Query(None, description="End date filter"),
    current_user: TokenData = Depends(get_current_user),
):
    """
    List voice calls for the current user with optional filtering and pagination.

    Each user only sees their own calls (data isolation).
    """
    result = await list_calls(
        page=page,
        page_size=page_size,
        status=status,
        sentiment=sentiment,
        category=category,
        date_from=date_from,
        date_to=date_to,
        user_id=current_user.user_id  # Filter by current user
    )

    return CallListResponse(**result)


@router.get("/{call_id}")
async def get_call(
    call_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get detailed information about a specific call.
    Includes transcript and full analytics.

    Users can only access their own calls (data isolation).
    """
    call = await get_call_by_id(call_id)

    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    # Verify the call belongs to the current user
    if call.get("caller_id") and call.get("caller_id") != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

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
async def get_call_transcript(
    call_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get just the transcript for a specific call.
    Users can only access their own call transcripts.
    """
    call = await get_call_by_id(call_id)

    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    # Verify ownership
    if call.get("caller_id") and call.get("caller_id") != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

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
async def get_call_analytics(
    call_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get just the analytics for a specific call.
    Users can only access their own call analytics.
    """
    call = await get_call_by_id(call_id)

    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    # Verify ownership
    if call.get("caller_id") and call.get("caller_id") != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

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
