"""
Tickets API Router

Endpoints for managing support tickets.
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
from pydantic import BaseModel

from app.services.ticket_service import (
    get_ticket_by_id,
    list_tickets,
    update_ticket,
    get_ticket_stats,
)
from app.core.security import get_current_user, TokenData


router = APIRouter(prefix="/tickets", tags=["Tickets"])


class TicketUpdateRequest(BaseModel):
    """Request to update a ticket"""
    status: Optional[str] = None
    priority: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None


@router.get("")
async def get_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    current_user: TokenData = Depends(get_current_user),
):
    """
    List tickets for the current user with optional filtering.
    """
    result = await list_tickets(
        user_id=current_user.user_id,
        status=status,
        priority=priority,
        category=category,
        page=page,
        page_size=page_size,
    )
    return result


@router.get("/stats")
async def get_tickets_stats(
    current_user: TokenData = Depends(get_current_user),
):
    """
    Get ticket statistics for the dashboard.
    """
    return await get_ticket_stats(user_id=current_user.user_id)


@router.get("/{ticket_id}")
async def get_ticket(
    ticket_id: str,
    current_user: TokenData = Depends(get_current_user),
):
    """
    Get a specific ticket by ID.
    """
    ticket = await get_ticket_by_id(ticket_id)

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Verify ownership
    if ticket.get("user_id") and ticket.get("user_id") != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return ticket


@router.patch("/{ticket_id}")
async def update_ticket_endpoint(
    ticket_id: str,
    request: TicketUpdateRequest,
    current_user: TokenData = Depends(get_current_user),
):
    """
    Update a ticket's status, priority, etc.
    """
    # First verify the ticket exists and user has access
    ticket = await get_ticket_by_id(ticket_id)

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if ticket.get("user_id") and ticket.get("user_id") != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Build updates dict
    updates = {}
    if request.status:
        if request.status not in ["open", "in_progress", "resolved", "closed"]:
            raise HTTPException(status_code=400, detail="Invalid status")
        updates["status"] = request.status
    if request.priority:
        if request.priority not in ["low", "medium", "high", "critical"]:
            raise HTTPException(status_code=400, detail="Invalid priority")
        updates["priority"] = request.priority
    if request.title:
        updates["title"] = request.title
    if request.description:
        updates["description"] = request.description

    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    result = await update_ticket(ticket_id, updates)

    if not result:
        raise HTTPException(status_code=500, detail="Failed to update ticket")

    return result
