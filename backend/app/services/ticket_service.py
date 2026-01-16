"""
Ticket Service - CRUD operations for support tickets

Tickets are automatically created after each call based on the call analysis,
or manually created via chat.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import json
from app.core.database import get_supabase_admin


def determine_priority(analysis: Dict[str, Any]) -> str:
    """
    Determine ticket priority based on call analysis.

    Priority levels:
    - critical: Very negative sentiment, unresolved, low CSAT
    - high: Negative sentiment or unresolved with action items
    - medium: Neutral sentiment, partially resolved
    - low: Positive sentiment, resolved
    """
    sentiment_score = analysis.get("sentiment_score", 0)
    resolution = analysis.get("resolution_status", "unknown")
    csat = analysis.get("customer_satisfaction_predicted", 3)
    action_items = analysis.get("action_items", [])

    # Critical: Very negative + unresolved
    if sentiment_score < -0.5 and resolution == "unresolved":
        return "critical"

    # Critical: Very low CSAT
    if csat < 2:
        return "critical"

    # High: Negative or unresolved with action items
    if sentiment_score < -0.3 or (resolution == "unresolved" and len(action_items) > 0):
        return "high"

    # Low: Positive and resolved
    if sentiment_score > 0.3 and resolution == "resolved":
        return "low"

    # Default: Medium
    return "medium"


def generate_ticket_title(analysis: Dict[str, Any]) -> str:
    """
    Generate a concise ticket title from the analysis.
    """
    category = analysis.get("primary_category", "general_inquiry")
    category_display = category.replace("_", " ").title()

    intent = analysis.get("customer_intent", "")
    if intent and len(intent) < 60:
        return f"{category_display}: {intent}"

    # Fallback to category + first key topic
    topics = analysis.get("key_topics", [])
    if topics:
        return f"{category_display}: {topics[0]}"

    return f"{category_display} Support Request"


async def create_ticket_from_call(
    call_id: str,
    user_id: Optional[str],
    analysis: Dict[str, Any],
    customer_email: Optional[str] = None,
    customer_name: Optional[str] = None,
    customer_phone: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Create a ticket from call analysis data.

    Called automatically after each call's analysis is complete.
    """
    try:
        supabase = get_supabase_admin()

        # Generate ticket data from analysis
        title = generate_ticket_title(analysis)
        priority = determine_priority(analysis)

        # Determine initial status based on resolution
        resolution_status = analysis.get("resolution_status", "unknown")
        if resolution_status == "resolved":
            status = "resolved"
        elif resolution_status == "escalated":
            status = "in_progress"
        else:
            status = "open"

        record = {
            "call_id": call_id,
            "user_id": user_id,
            "title": title,
            "description": analysis.get("call_summary", ""),
            "category": analysis.get("primary_category", "general_inquiry"),
            "priority": priority,
            "status": status,
            "customer_email": customer_email,
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "sentiment_score": analysis.get("sentiment_score"),
            "resolution_status": resolution_status,
            "customer_satisfaction_predicted": int(analysis.get("customer_satisfaction_predicted", 3)) if analysis.get("customer_satisfaction_predicted") is not None else None,
            "action_items": analysis.get("action_items", []),
            "key_topics": analysis.get("key_topics", []),
        }

        # Set resolved_at if already resolved
        if status == "resolved":
            record["resolved_at"] = datetime.utcnow().isoformat()

        result = supabase.table("supportiq_tickets").insert(record).execute()

        if result.data:
            print(f"[TICKET] Created ticket {result.data[0]['id']} for call {call_id}: {title} (Priority: {priority})")
            return result.data[0]

        return None

    except Exception as e:
        print(f"Error creating ticket: {e}")
        return None


async def get_ticket_by_id(ticket_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a ticket by its ID with associated call data.
    """
    try:
        supabase = get_supabase_admin()

        result = supabase.table("supportiq_tickets").select(
            "*, supportiq_voice_calls(id, vapi_call_id, started_at, duration_seconds, status)"
        ).eq("id", ticket_id).execute()

        return result.data[0] if result.data else None

    except Exception as e:
        print(f"Error getting ticket: {e}")
        return None


async def list_tickets(
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    """
    List tickets with optional filtering and pagination.
    """
    try:
        supabase = get_supabase_admin()

        query = supabase.table("supportiq_tickets").select("*", count="exact")

        # Apply filters
        if user_id:
            query = query.eq("user_id", user_id)
        if status:
            query = query.eq("status", status)
        if priority:
            query = query.eq("priority", priority)
        if category:
            query = query.eq("category", category)

        # Pagination
        offset = (page - 1) * page_size
        query = query.order("created_at", desc=True).range(offset, offset + page_size - 1)

        result = query.execute()

        return {
            "tickets": result.data or [],
            "total": result.count or 0,
            "page": page,
            "page_size": page_size,
        }

    except Exception as e:
        print(f"Error listing tickets: {e}")
        return {"tickets": [], "total": 0, "page": page, "page_size": page_size}


async def update_ticket(
    ticket_id: str,
    updates: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Update a ticket's status, priority, or other fields.
    """
    try:
        supabase = get_supabase_admin()

        # Add updated_at timestamp
        updates["updated_at"] = datetime.utcnow().isoformat()

        # If status changed to resolved, set resolved_at
        if updates.get("status") == "resolved":
            updates["resolved_at"] = datetime.utcnow().isoformat()

        result = supabase.table("supportiq_tickets").update(updates).eq(
            "id", ticket_id
        ).execute()

        return result.data[0] if result.data else None

    except Exception as e:
        print(f"Error updating ticket: {e}")
        return None


async def get_ticket_stats(user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get ticket statistics for the dashboard.
    """
    try:
        supabase = get_supabase_admin()

        query = supabase.table("supportiq_tickets").select("*")
        if user_id:
            query = query.eq("user_id", user_id)

        result = query.execute()
        tickets = result.data or []

        # Calculate stats
        total = len(tickets)
        open_count = sum(1 for t in tickets if t["status"] == "open")
        in_progress_count = sum(1 for t in tickets if t["status"] == "in_progress")
        resolved_count = sum(1 for t in tickets if t["status"] == "resolved")
        closed_count = sum(1 for t in tickets if t["status"] == "closed")

        # Priority breakdown
        critical = sum(1 for t in tickets if t["priority"] == "critical")
        high = sum(1 for t in tickets if t["priority"] == "high")
        medium = sum(1 for t in tickets if t["priority"] == "medium")
        low = sum(1 for t in tickets if t["priority"] == "low")

        # Category breakdown
        categories = {}
        for t in tickets:
            cat = t.get("category", "other")
            categories[cat] = categories.get(cat, 0) + 1

        # Calculate additional stats
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())

        tickets_today = sum(1 for t in tickets if datetime.fromisoformat(t["created_at"].replace("Z", "+00:00")).replace(tzinfo=None) >= today_start)
        tickets_this_week = sum(1 for t in tickets if datetime.fromisoformat(t["created_at"].replace("Z", "+00:00")).replace(tzinfo=None) >= week_start)

        # Calculate average resolution time
        resolved_tickets = [t for t in tickets if t.get("resolved_at") and t.get("created_at")]
        avg_resolution_time_hours = None
        if resolved_tickets:
            total_hours = 0
            for t in resolved_tickets:
                created = datetime.fromisoformat(t["created_at"].replace("Z", "+00:00"))
                resolved = datetime.fromisoformat(t["resolved_at"].replace("Z", "+00:00"))
                total_hours += (resolved - created).total_seconds() / 3600
            avg_resolution_time_hours = round(total_hours / len(resolved_tickets), 1)

        return {
            "total": total,
            # Top-level status counts for frontend compatibility
            "open": open_count,
            "in_progress": in_progress_count,
            "resolved": resolved_count,
            "closed": closed_count,
            # Keep by_status for backwards compatibility
            "by_status": {
                "open": open_count,
                "in_progress": in_progress_count,
                "resolved": resolved_count,
            },
            "by_priority": {
                "critical": critical,
                "high": high,
                "medium": medium,
                "low": low,
            },
            "by_category": categories,
            "avg_resolution_time_hours": avg_resolution_time_hours,
            "tickets_today": tickets_today,
            "tickets_this_week": tickets_this_week,
        }

    except Exception as e:
        print(f"Error getting ticket stats: {e}")
        return {
            "total": 0,
            "open": 0,
            "in_progress": 0,
            "resolved": 0,
            "closed": 0,
            "by_status": {"open": 0, "in_progress": 0, "resolved": 0},
            "by_priority": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "by_category": {},
            "avg_resolution_time_hours": None,
            "tickets_today": 0,
            "tickets_this_week": 0,
        }


# ============================================
# CHAT-BASED TICKET OPERATIONS
# ============================================

async def create_ticket_from_chat(
    user_id: str,
    title: str,
    description: str,
    priority: str = "medium",
    category: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Create a ticket from chat.

    Returns the created ticket with ticket_number.
    """
    try:
        supabase = get_supabase_admin()

        record = {
            "user_id": user_id,
            "title": title[:200],  # Limit title length
            "description": description,
            "category": category or "general_inquiry",
            "priority": priority if priority in ["low", "medium", "high", "critical"] else "medium",
            "status": "open",
            "source": "chat",
        }

        result = supabase.table("supportiq_tickets").insert(record).execute()

        if result.data:
            ticket = result.data[0]
            print(f"[TICKET] Created chat ticket #{ticket.get('ticket_number')} for user {user_id}: {title}")
            return ticket

        return None

    except Exception as e:
        print(f"Error creating chat ticket: {e}")
        return None


async def get_ticket_by_number(ticket_number: int) -> Optional[Dict[str, Any]]:
    """
    Get a ticket by its sequential ticket number.
    """
    try:
        supabase = get_supabase_admin()

        result = supabase.table("supportiq_tickets").select(
            "*, supportiq_voice_calls(id, vapi_call_id, started_at, duration_seconds, status)"
        ).eq("ticket_number", ticket_number).execute()

        return result.data[0] if result.data else None

    except Exception as e:
        print(f"Error getting ticket by number: {e}")
        return None


async def add_note_to_ticket(
    ticket_id: str,
    note_content: str,
    added_by: str = "chat",
) -> Optional[Dict[str, Any]]:
    """
    Add a note to an existing ticket.
    """
    try:
        supabase = get_supabase_admin()

        # Get current ticket
        ticket_result = supabase.table("supportiq_tickets").select("notes").eq("id", ticket_id).execute()

        if not ticket_result.data:
            return None

        current_notes = ticket_result.data[0].get("notes") or []

        # Add new note
        new_note = {
            "content": note_content,
            "added_by": added_by,
            "added_at": datetime.utcnow().isoformat(),
        }
        current_notes.append(new_note)

        # Update ticket
        result = supabase.table("supportiq_tickets").update({
            "notes": current_notes,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", ticket_id).execute()

        return result.data[0] if result.data else None

    except Exception as e:
        print(f"Error adding note to ticket: {e}")
        return None


async def search_tickets(
    query: str,
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Search tickets by title/description.

    If user_id is provided, user's tickets are returned first,
    followed by other matching tickets.
    """
    try:
        supabase = get_supabase_admin()
        limit = min(limit, 20)  # Cap at 20

        # Build the query - search in title and description
        # Note: Using ilike for simple text search. For production,
        # consider using Postgres full-text search.
        search_pattern = f"%{query}%"

        base_query = supabase.table("supportiq_tickets").select(
            "id, ticket_number, title, description, status, priority, category, created_at, updated_at, user_id, source"
        )

        # Apply status filter
        if status and status != "all":
            base_query = base_query.eq("status", status)

        # Search in title or description
        base_query = base_query.or_(f"title.ilike.{search_pattern},description.ilike.{search_pattern}")

        # Order by created_at desc
        base_query = base_query.order("created_at", desc=True).limit(limit * 2)  # Get extra for reordering

        result = base_query.execute()
        tickets = result.data or []

        # If user_id provided, reorder to put user's tickets first
        if user_id and tickets:
            user_tickets = [t for t in tickets if t.get("user_id") == user_id]
            other_tickets = [t for t in tickets if t.get("user_id") != user_id]
            tickets = (user_tickets + other_tickets)[:limit]
        else:
            tickets = tickets[:limit]

        return tickets

    except Exception as e:
        print(f"Error searching tickets: {e}")
        return []


async def get_tickets_by_ids(ticket_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Get multiple tickets by their IDs.
    Used for loading attached tickets in chat.
    """
    try:
        if not ticket_ids:
            return []

        supabase = get_supabase_admin()

        result = supabase.table("supportiq_tickets").select(
            "id, ticket_number, title, description, status, priority, category, created_at, updated_at"
        ).in_("id", ticket_ids).execute()

        return result.data or []

    except Exception as e:
        print(f"Error getting tickets by IDs: {e}")
        return []
