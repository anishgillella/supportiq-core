"""
VAPI Webhook Router

Handles incoming webhooks from VAPI for:
- assistant-request: RAG context injection
- end-of-call-report: Transcript storage and analysis
- function-call: Knowledge base search
- status-update: Real-time call status
"""

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from typing import Dict, Any
from datetime import datetime

from app.services.call_service import create_call, create_transcript
from app.services.transcript_analysis import analyze_transcript
from app.services.pinecone_service import query_vectors
from app.services.embeddings import get_embedding
from app.core.config import settings

router = APIRouter(prefix="/vapi", tags=["VAPI Webhooks"])


# ========================================
# MAIN WEBHOOK ENDPOINT
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
        message = body.get("message", {})
        message_type = message.get("type", "")

        print(f"VAPI webhook received: {message_type}")

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

        elif message_type == "transcript":
            # Live transcript updates - just acknowledge
            return {"status": "ok"}

        else:
            # Log unknown message types for debugging
            print(f"Unknown VAPI message type: {message_type}")
            print(f"Full body: {body}")
            return {"status": "ok"}

    except Exception as e:
        print(f"VAPI webhook error: {e}")
        # Still return 200 to prevent VAPI retries
        return {"status": "error", "message": str(e)}


# ========================================
# HANDLER: ASSISTANT REQUEST (RAG CONTEXT)
# ========================================

async def handle_assistant_request(body: dict) -> dict:
    """
    Inject RAG context into the assistant's system prompt.
    Called at the start of each call or turn.
    """
    try:
        call_data = body.get("message", {}).get("call", {})

        # Get customer ID if available (from metadata)
        customer_id = call_data.get("metadata", {}).get("customer_id")

        # Return modified assistant configuration
        # VAPI will merge this with the base assistant config
        return {
            "assistant": {
                "model": {
                    "provider": "openrouter",
                    "model": settings.analysis_model,
                    "temperature": 0.7,
                    "maxTokens": 1024
                }
            }
        }

    except Exception as e:
        print(f"Error in assistant request: {e}")
        return {}


# ========================================
# HANDLER: FUNCTION CALL (RAG SEARCH)
# ========================================

async def handle_function_call(body: dict) -> dict:
    """
    Handle function calls from the assistant.
    Primary use: search_knowledge_base for RAG.
    """
    try:
        message = body.get("message", {})
        function_call = message.get("functionCall", {})
        function_name = function_call.get("name")
        parameters = function_call.get("parameters", {})

        print(f"Function call: {function_name} with params: {parameters}")

        if function_name == "search_knowledge_base":
            query = parameters.get("query", "")

            if not query:
                return {
                    "result": "I need more information to search. Could you please clarify your question?"
                }

            try:
                # Generate embedding for query
                query_embedding = get_embedding(query)

                # Search Pinecone - use a default namespace or get from metadata
                # For now, we'll search across all namespaces
                results = query_vectors(
                    query_embedding=query_embedding,
                    namespace="default",  # Could be made dynamic
                    top_k=3
                )

                if not results:
                    return {
                        "result": "I couldn't find specific information about that in our knowledge base. Let me try to help you another way. Could you provide more details about your question?"
                    }

                # Format results for voice response
                context_parts = []
                for match in results:
                    content = match.get("metadata", {}).get("content", "")
                    if content:
                        # Truncate long content for voice
                        if len(content) > 500:
                            content = content[:500] + "..."
                        context_parts.append(content)

                context = " ".join(context_parts)

                return {
                    "result": f"Based on our knowledge base: {context}"
                }

            except Exception as e:
                print(f"Knowledge base search error: {e}")
                return {
                    "result": "I'm having trouble searching our knowledge base right now. Let me try to help you in another way. Could you describe your issue in more detail?"
                }

        return {"result": "I'm not sure how to handle that request. Could you please rephrase?"}

    except Exception as e:
        print(f"Error in function call handler: {e}")
        return {"result": "I encountered an error. Please try again."}


# ========================================
# HANDLER: END OF CALL REPORT
# ========================================

async def handle_end_of_call(body: dict):
    """
    Process the end-of-call report from VAPI.

    1. Store call metadata
    2. Store transcript
    3. Trigger AI analysis
    """
    try:
        message = body.get("message", {})
        call_data = message.get("call", {})

        # Extract call info
        vapi_call_id = call_data.get("id")
        if not vapi_call_id:
            print("No call ID in end-of-call report")
            return

        started_at = call_data.get("startedAt")
        ended_at = call_data.get("endedAt")

        # Calculate duration
        duration = None
        if started_at and ended_at:
            try:
                start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                end = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
                duration = int((end - start).total_seconds())
            except Exception as e:
                print(f"Error calculating duration: {e}")

        # Extract transcript
        transcript_text = message.get("transcript", "")
        messages = message.get("messages", [])

        # Determine call status
        status = "completed"
        if call_data.get("endedReason") == "customer-ended-call":
            status = "completed"
        elif call_data.get("endedReason") == "assistant-error":
            status = "failed"
        elif duration and duration < 10:
            status = "abandoned"

        print(f"Processing call {vapi_call_id}: status={status}, duration={duration}s, messages={len(messages)}")

        # Create call record
        call_record = await create_call(
            vapi_call_id=vapi_call_id,
            started_at=started_at,
            ended_at=ended_at,
            duration_seconds=duration,
            status=status,
            agent_type="general",
            recording_url=call_data.get("recordingUrl"),
            vapi_assistant_id=call_data.get("assistantId")
        )

        if not call_record:
            print(f"Failed to create call record for {vapi_call_id}")
            return

        # Create transcript record
        word_count = len(transcript_text.split()) if transcript_text else 0
        transcript_record = await create_transcript(
            call_id=call_record["id"],
            transcript=messages,
            word_count=word_count,
            turn_count=len(messages),
            raw_vapi_response=message
        )

        print(f"Stored transcript for call {vapi_call_id}: {len(messages)} messages, {word_count} words")

        # Trigger AI analysis
        if messages or transcript_text:
            print(f"Starting AI analysis for call {vapi_call_id}")
            analysis = await analyze_transcript(
                call_id=call_record["id"],
                transcript_messages=messages,
                full_transcript=transcript_text
            )
            if analysis:
                print(f"Analysis complete for call {vapi_call_id}: {analysis.get('overall_sentiment')}, {analysis.get('resolution_status')}")
            else:
                print(f"Analysis failed for call {vapi_call_id}")

        print(f"Successfully processed call {vapi_call_id}")

    except Exception as e:
        print(f"Error processing end of call: {e}")
        import traceback
        traceback.print_exc()


# ========================================
# HANDLER: STATUS UPDATE
# ========================================

async def handle_status_update(body: dict):
    """
    Handle real-time status updates during a call.
    Useful for live dashboards (future feature).
    """
    try:
        message = body.get("message", {})
        status = message.get("status")
        call_id = message.get("call", {}).get("id")

        print(f"Call {call_id} status update: {status}")

        # Future: broadcast to WebSocket for live dashboard

    except Exception as e:
        print(f"Error in status update handler: {e}")


# ========================================
# FUNCTION ENDPOINT (ALTERNATIVE)
# ========================================

@router.post("/function")
async def vapi_function(request: Request):
    """
    Separate endpoint for function calls if configured in VAPI.
    Some VAPI configurations use a separate URL for functions.
    """
    body = await request.json()
    return await handle_function_call(body)
