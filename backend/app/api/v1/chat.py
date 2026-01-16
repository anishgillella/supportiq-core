"""Chat endpoint with RAG and Ticket Management Tools"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
from datetime import datetime

from app.core.security import get_current_user, TokenData
from app.core.database import get_supabase_admin
from app.services.embeddings import get_embedding
from app.services.pinecone_service import query_vectors
from app.services.llm import chat_completion, build_rag_prompt, TICKET_TOOLS
from app.services.ticket_service import (
    create_ticket_from_chat,
    get_ticket_by_number,
    get_ticket_by_id,
    update_ticket,
    add_note_to_ticket,
    search_tickets,
    get_tickets_by_ids,
)

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    attached_ticket_ids: Optional[List[str]] = None


class SourceInfo(BaseModel):
    title: str
    chunk: str


class TicketInfo(BaseModel):
    id: str
    ticket_number: int
    title: str
    status: str
    priority: str


class ToolCallInfo(BaseModel):
    name: str
    result: Dict[str, Any]


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    sources: List[SourceInfo]
    tool_calls: Optional[List[ToolCallInfo]] = None
    created_tickets: Optional[List[TicketInfo]] = None
    referenced_tickets: Optional[List[TicketInfo]] = None


# ============================================
# TOOL EXECUTION
# ============================================

async def execute_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    user_id: str,
) -> Dict[str, Any]:
    """Execute a tool and return the result."""

    if tool_name == "create_ticket":
        ticket = await create_ticket_from_chat(
            user_id=user_id,
            title=arguments.get("title", "New Ticket"),
            description=arguments.get("description", ""),
            priority=arguments.get("priority", "medium"),
            category=arguments.get("category"),
        )
        if ticket:
            return {
                "success": True,
                "ticket": {
                    "id": ticket["id"],
                    "ticket_number": ticket.get("ticket_number"),
                    "title": ticket["title"],
                    "status": ticket["status"],
                    "priority": ticket["priority"],
                }
            }
        return {"success": False, "error": "Failed to create ticket"}

    elif tool_name == "get_ticket":
        ticket_number = arguments.get("ticket_number")
        if not ticket_number:
            return {"success": False, "error": "Ticket number required"}

        ticket = await get_ticket_by_number(ticket_number)
        if ticket:
            return {
                "success": True,
                "ticket": {
                    "id": ticket["id"],
                    "ticket_number": ticket.get("ticket_number"),
                    "title": ticket["title"],
                    "description": ticket.get("description"),
                    "status": ticket["status"],
                    "priority": ticket["priority"],
                    "category": ticket.get("category"),
                    "created_at": ticket.get("created_at"),
                    "updated_at": ticket.get("updated_at"),
                    "notes": ticket.get("notes", []),
                }
            }
        return {"success": False, "error": f"Ticket #{ticket_number} not found"}

    elif tool_name == "update_ticket":
        ticket_number = arguments.get("ticket_number")
        if not ticket_number:
            return {"success": False, "error": "Ticket number required"}

        ticket = await get_ticket_by_number(ticket_number)
        if not ticket:
            return {"success": False, "error": f"Ticket #{ticket_number} not found"}

        updates = {}
        if arguments.get("status"):
            updates["status"] = arguments["status"]

        # Handle notes separately
        if arguments.get("notes"):
            await add_note_to_ticket(
                ticket_id=ticket["id"],
                note_content=arguments["notes"],
                added_by="chat",
            )

        if updates:
            updated = await update_ticket(ticket["id"], updates)
            if updated:
                return {
                    "success": True,
                    "ticket": {
                        "id": updated["id"],
                        "ticket_number": updated.get("ticket_number"),
                        "title": updated["title"],
                        "status": updated["status"],
                        "priority": updated["priority"],
                    },
                    "message": f"Ticket #{ticket_number} updated successfully"
                }
        elif arguments.get("notes"):
            # Only notes were added
            return {
                "success": True,
                "message": f"Note added to ticket #{ticket_number}"
            }

        return {"success": False, "error": "No updates provided"}

    elif tool_name == "search_tickets":
        query = arguments.get("query", "")
        status_filter = arguments.get("status")
        limit = min(arguments.get("limit", 10), 20)

        tickets = await search_tickets(
            query=query,
            user_id=user_id,
            status=status_filter if status_filter != "all" else None,
            limit=limit,
        )

        return {
            "success": True,
            "tickets": [
                {
                    "ticket_number": t.get("ticket_number"),
                    "title": t["title"],
                    "status": t["status"],
                    "priority": t["priority"],
                    "category": t.get("category"),
                    "created_at": t.get("created_at"),
                }
                for t in tickets
            ],
            "count": len(tickets),
        }

    return {"success": False, "error": f"Unknown tool: {tool_name}"}


def build_ticket_context(tickets: List[Dict[str, Any]]) -> str:
    """Build context string from attached tickets."""
    if not tickets:
        return ""

    context_parts = ["\n\nATTACHED TICKETS FOR CONTEXT:"]
    for t in tickets:
        context_parts.append(f"""
---
Ticket #{t.get('ticket_number', 'N/A')}: {t.get('title', 'Untitled')}
Status: {t.get('status', 'unknown')} | Priority: {t.get('priority', 'unknown')} | Category: {t.get('category', 'N/A')}
Description: {t.get('description', 'No description')[:500]}
Created: {t.get('created_at', 'N/A')}
---""")

    return "\n".join(context_parts)


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """Send a message and get an AI response with RAG and ticket tools"""
    supabase = get_supabase_admin()

    try:
        # Get user info for company name
        user_result = supabase.table("supportiq_users") \
            .select("company_name") \
            .eq("id", current_user.user_id) \
            .execute()

        company_name = None
        if user_result.data:
            company_name = user_result.data[0].get("company_name")

        # Get or create conversation
        conversation_id = request.conversation_id
        conversation_messages = []
        attached_ticket_ids = request.attached_ticket_ids or []

        if conversation_id:
            conv_result = supabase.table("supportiq_conversations") \
                .select("messages, attached_ticket_ids") \
                .eq("id", conversation_id) \
                .eq("user_id", current_user.user_id) \
                .execute()

            if conv_result.data:
                conversation_messages = conv_result.data[0].get("messages", [])
                # Merge attached tickets from request with existing
                existing_tickets = conv_result.data[0].get("attached_ticket_ids", []) or []
                attached_ticket_ids = list(set(existing_tickets + attached_ticket_ids))
        else:
            # Create new conversation
            conv_result = supabase.table("supportiq_conversations").insert({
                "user_id": current_user.user_id,
                "title": request.message[:50] + "..." if len(request.message) > 50 else request.message,
                "messages": [],
                "attached_ticket_ids": attached_ticket_ids,
            }).execute()

            if conv_result.data:
                conversation_id = conv_result.data[0]["id"]
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create conversation"
                )

        # Load attached tickets for context
        attached_tickets = []
        if attached_ticket_ids:
            attached_tickets = await get_tickets_by_ids(attached_ticket_ids)

        # Generate embedding for the query
        query_embedding = get_embedding(request.message)

        # Search for relevant chunks
        search_results = query_vectors(
            query_embedding=query_embedding,
            namespace=current_user.user_id,
            top_k=5
        )

        # Extract context chunks
        context_chunks = []
        sources = []

        for result in search_results:
            if result["score"] > 0.2:
                metadata = result["metadata"]
                context_chunks.append({
                    "title": metadata.get("title", "Unknown"),
                    "content": metadata.get("content", "")
                })
                sources.append(SourceInfo(
                    title=metadata.get("title", "Unknown"),
                    chunk=metadata.get("content", "")[:200] + "..."
                ))

        # Build system prompt with RAG context + ticket context
        base_system_prompt = build_rag_prompt(
            user_query=request.message,
            context_chunks=context_chunks,
            company_name=company_name
        )

        # Add ticket context and tools info
        ticket_context = build_ticket_context(attached_tickets)
        tools_info = """

You have access to ticket management tools:
- create_ticket: Create a new support ticket when the user wants to log an issue
- get_ticket: Look up details of a specific ticket by number (e.g., #47)
- update_ticket: Update a ticket's status or add notes
- search_tickets: Search for tickets by keyword

When the user asks about tickets, references a ticket number, or wants to create/update tickets, use the appropriate tool.
When referring to tickets, always use the format "ticket #[number]" (e.g., "ticket #47").
"""

        system_prompt = base_system_prompt + ticket_context + tools_info

        # Include conversation history (last 10 messages)
        llm_messages = []
        for msg in conversation_messages[-10:]:
            llm_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        # Add current user message
        llm_messages.append({
            "role": "user",
            "content": request.message
        })

        # Get AI response with tools
        result = await chat_completion(
            messages=llm_messages,
            system_prompt=system_prompt,
            tools=TICKET_TOOLS,
        )

        # Handle tool calls if any
        tool_call_results = []
        created_tickets = []
        referenced_tickets = []

        if isinstance(result, tuple):
            ai_content, tool_calls = result

            # Execute each tool call
            for tc in tool_calls:
                tool_result = await execute_tool(
                    tool_name=tc["name"],
                    arguments=tc["arguments"],
                    user_id=current_user.user_id,
                )
                tool_call_results.append(ToolCallInfo(
                    name=tc["name"],
                    result=tool_result,
                ))

                # Track created/referenced tickets
                if tc["name"] == "create_ticket" and tool_result.get("success"):
                    ticket_data = tool_result.get("ticket", {})
                    created_tickets.append(TicketInfo(
                        id=ticket_data.get("id", ""),
                        ticket_number=ticket_data.get("ticket_number", 0),
                        title=ticket_data.get("title", ""),
                        status=ticket_data.get("status", "open"),
                        priority=ticket_data.get("priority", "medium"),
                    ))
                elif tc["name"] in ["get_ticket", "update_ticket"] and tool_result.get("success"):
                    ticket_data = tool_result.get("ticket", {})
                    if ticket_data:
                        referenced_tickets.append(TicketInfo(
                            id=ticket_data.get("id", ""),
                            ticket_number=ticket_data.get("ticket_number", 0),
                            title=ticket_data.get("title", ""),
                            status=ticket_data.get("status", "open"),
                            priority=ticket_data.get("priority", "medium"),
                        ))

            # If there were tool calls, get a follow-up response with the results
            if tool_calls:
                # Add tool results to messages
                tool_results_msg = "\n\nTool Results:\n" + json.dumps(
                    [{"tool": tc.name, "result": tc.result} for tc in tool_call_results],
                    indent=2
                )

                follow_up_messages = llm_messages + [
                    {"role": "assistant", "content": ai_content or ""},
                    {"role": "user", "content": f"Based on these tool results, please provide a natural response to the user:{tool_results_msg}"}
                ]

                ai_response = await chat_completion(
                    messages=follow_up_messages,
                    system_prompt="You are a helpful assistant. Summarize the tool results in a friendly, conversational way. When mentioning tickets, use format 'ticket #[number]'.",
                    max_tokens=512,
                )
            else:
                ai_response = ai_content
        else:
            ai_response = result

        # Update conversation with new messages
        now = datetime.utcnow().isoformat()
        conversation_messages.append({
            "role": "user",
            "content": request.message,
            "timestamp": now
        })
        conversation_messages.append({
            "role": "assistant",
            "content": ai_response,
            "timestamp": now,
            "sources": [{"title": s.title, "chunk": s.chunk} for s in sources],
            "tool_calls": [{"name": tc.name, "result": tc.result} for tc in tool_call_results] if tool_call_results else None,
        })

        # Update conversation in database
        update_data = {"messages": conversation_messages}
        if attached_ticket_ids:
            update_data["attached_ticket_ids"] = attached_ticket_ids

        supabase.table("supportiq_conversations").update(update_data).eq("id", conversation_id).execute()

        return ChatResponse(
            response=ai_response,
            conversation_id=conversation_id,
            sources=sources,
            tool_calls=tool_call_results if tool_call_results else None,
            created_tickets=created_tickets if created_tickets else None,
            referenced_tickets=referenced_tickets if referenced_tickets else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {str(e)}"
        )


# ============================================
# CONVERSATION MANAGEMENT
# ============================================

@router.get("/conversations")
async def list_conversations(current_user: TokenData = Depends(get_current_user)):
    """List all conversations for the current user"""
    supabase = get_supabase_admin()

    result = supabase.table("supportiq_conversations") \
        .select("id, title, created_at, updated_at, attached_ticket_ids") \
        .eq("user_id", current_user.user_id) \
        .order("updated_at", desc=True) \
        .execute()

    return {"conversations": result.data or []}


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Get a specific conversation with messages"""
    supabase = get_supabase_admin()

    result = supabase.table("supportiq_conversations") \
        .select("*") \
        .eq("id", conversation_id) \
        .eq("user_id", current_user.user_id) \
        .execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    return result.data[0]


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Delete a conversation"""
    supabase = get_supabase_admin()

    supabase.table("supportiq_conversations") \
        .delete() \
        .eq("id", conversation_id) \
        .eq("user_id", current_user.user_id) \
        .execute()

    return {"success": True}


@router.patch("/conversations/{conversation_id}/tickets")
async def update_conversation_tickets(
    conversation_id: str,
    ticket_ids: List[str],
    current_user: TokenData = Depends(get_current_user)
):
    """Update the attached tickets for a conversation"""
    supabase = get_supabase_admin()

    # Verify ownership
    check = supabase.table("supportiq_conversations") \
        .select("id") \
        .eq("id", conversation_id) \
        .eq("user_id", current_user.user_id) \
        .execute()

    if not check.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    result = supabase.table("supportiq_conversations") \
        .update({"attached_ticket_ids": ticket_ids}) \
        .eq("id", conversation_id) \
        .execute()

    return {"success": True, "attached_ticket_ids": ticket_ids}


@router.post("/conversations/{conversation_id}/generate-title")
async def generate_conversation_title(
    conversation_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Generate an AI title for a conversation based on its first messages"""
    supabase = get_supabase_admin()

    # Get conversation
    result = supabase.table("supportiq_conversations") \
        .select("id, messages, title, user_id") \
        .eq("id", conversation_id) \
        .execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conv = result.data[0]

    # Check ownership
    if conv.get("user_id") != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    messages = conv.get("messages", [])
    if not messages:
        return {"title": "New Chat", "generated": False}

    # Get first few messages for context
    context_messages = messages[:4]  # First 2 exchanges
    context_text = "\n".join([
        f"{m['role']}: {m['content'][:200]}"
        for m in context_messages
    ])

    # Generate title using LLM
    try:
        title_prompt = f"""Based on this conversation, generate a short descriptive title (3-6 words, no quotes).
The title should capture the main topic or request.

Conversation:
{context_text}

Title:"""

        title = await chat_completion(
            messages=[{"role": "user", "content": title_prompt}],
            max_tokens=20,
            temperature=0.3,
        )

        # Clean up the title
        title = title.strip().strip('"\'').strip()
        if len(title) > 60:
            title = title[:57] + "..."

        # Update conversation with new title
        supabase.table("supportiq_conversations") \
            .update({"title": title}) \
            .eq("id", conversation_id) \
            .execute()

        return {"title": title, "generated": True}

    except Exception as e:
        print(f"Error generating title: {e}")
        # Fallback to first user message
        for m in messages:
            if m.get("role") == "user":
                fallback = m["content"][:50]
                if len(m["content"]) > 50:
                    fallback += "..."
                return {"title": fallback, "generated": False}

        return {"title": "New Chat", "generated": False}


# ============================================
# TICKET SEARCH (for picker)
# ============================================

@router.get("/tickets/recent")
async def get_recent_tickets_endpoint(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(10, ge=1, le=20, description="Max results"),
    current_user: TokenData = Depends(get_current_user)
):
    """Get recent tickets for the ticket picker (no search query required)"""
    from app.core.database import get_supabase_admin

    try:
        supabase = get_supabase_admin()

        query = supabase.table("supportiq_tickets").select(
            "id, ticket_number, title, description, status, priority, category, created_at, updated_at, user_id, source"
        )

        # Apply status filter
        if status and status != "all":
            query = query.eq("status", status)

        # Order by updated_at desc to show most recently active tickets
        query = query.order("updated_at", desc=True).limit(limit)

        result = query.execute()
        tickets = result.data or []

        # Reorder to put current user's tickets first
        user_tickets = [t for t in tickets if t.get("user_id") == current_user.user_id]
        other_tickets = [t for t in tickets if t.get("user_id") != current_user.user_id]
        tickets = (user_tickets + other_tickets)[:limit]

        return {
            "tickets": tickets,
            "count": len(tickets),
        }
    except Exception as e:
        print(f"Error getting recent tickets: {e}")
        return {"tickets": [], "count": 0}


@router.get("/tickets/search")
async def search_tickets_endpoint(
    q: str = Query(..., min_length=1, description="Search query"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(10, ge=1, le=20, description="Max results"),
    current_user: TokenData = Depends(get_current_user)
):
    """Search tickets for the ticket picker"""
    tickets = await search_tickets(
        query=q,
        user_id=current_user.user_id,
        status=status if status != "all" else None,
        limit=limit,
    )

    return {
        "tickets": tickets,
        "count": len(tickets),
    }


# Legacy endpoints for backwards compatibility
@router.get("/supportiq_conversations")
async def list_supportiq_conversations(current_user: TokenData = Depends(get_current_user)):
    """List all supportiq_conversations (legacy)"""
    return await list_conversations(current_user)


@router.get("/supportiq_conversations/{conversation_id}")
async def get_supportiq_conversation(
    conversation_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Get a specific conversation with messages (legacy)"""
    return await get_conversation(conversation_id, current_user)


@router.delete("/supportiq_conversations/{conversation_id}")
async def delete_supportiq_conversation(
    conversation_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Delete a conversation (legacy)"""
    return await delete_conversation(conversation_id, current_user)
