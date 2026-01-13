"""Chat endpoint with RAG"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import List, Optional
import json
from datetime import datetime

from app.core.security import get_current_user, TokenData
from app.core.database import get_supabase_admin
from app.services.embeddings import get_embedding
from app.services.pinecone_service import query_vectors
from app.services.llm import chat_completion, build_rag_prompt

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class SourceInfo(BaseModel):
    title: str
    chunk: str


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    sources: List[SourceInfo]


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """Send a message and get an AI response with RAG"""
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

        if conversation_id:
            conv_result = supabase.table("supportiq_conversations") \
                .select("messages") \
                .eq("id", conversation_id) \
                .eq("user_id", current_user.user_id) \
                .execute()

            if conv_result.data:
                conversation_messages = conv_result.data[0].get("messages", [])
        else:
            # Create new conversation
            conv_result = supabase.table("supportiq_conversations").insert({
                "user_id": current_user.user_id,
                "title": request.message[:50] + "..." if len(request.message) > 50 else request.message,
                "messages": []
            }).execute()

            if conv_result.data:
                conversation_id = conv_result.data[0]["id"]
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create conversation"
                )

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

        # Debug: Log search results
        print(f"[RAG Debug] Query: {request.message}")
        print(f"[RAG Debug] Namespace: {current_user.user_id}")
        print(f"[RAG Debug] Search results count: {len(search_results)}")
        for i, result in enumerate(search_results):
            content_preview = result.get('metadata', {}).get('content', '')[:200]
            print(f"[RAG Debug] Result {i}: score={result.get('score', 0):.3f}")
            print(f"[RAG Debug] Content preview: {content_preview}...")

        for result in search_results:
            if result["score"] > 0.2:  # Lowered threshold to include results (was 0.7)
                metadata = result["metadata"]
                context_chunks.append({
                    "title": metadata.get("title", "Unknown"),
                    "content": metadata.get("content", "")
                })
                sources.append(SourceInfo(
                    title=metadata.get("title", "Unknown"),
                    chunk=metadata.get("content", "")[:200] + "..."
                ))

        # Build messages for LLM
        system_prompt = build_rag_prompt(
            user_query=request.message,
            context_chunks=context_chunks,
            company_name=company_name
        )

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

        # Get AI response
        ai_response = await chat_completion(
            messages=llm_messages,
            system_prompt=system_prompt
        )

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
            "sources": [{"title": s.title, "chunk": s.chunk} for s in sources]
        })

        supabase.table("supportiq_conversations").update({
            "messages": conversation_messages
        }).eq("id", conversation_id).execute()

        return ChatResponse(
            response=ai_response,
            conversation_id=conversation_id,
            sources=sources
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {str(e)}"
        )


@router.get("/supportiq_conversations")
async def list_supportiq_conversations(current_user: TokenData = Depends(get_current_user)):
    """List all supportiq_conversations"""
    supabase = get_supabase_admin()

    result = supabase.table("supportiq_conversations") \
        .select("id, title, created_at, updated_at") \
        .eq("user_id", current_user.user_id) \
        .order("updated_at", desc=True) \
        .execute()

    return {"supportiq_conversations": result.data or []}


@router.get("/supportiq_conversations/{conversation_id}")
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


@router.delete("/supportiq_conversations/{conversation_id}")
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
