"""LLM service using OpenRouter"""
import httpx
import json
from typing import List, Dict, Any, Optional, Tuple, Union
from app.core.config import settings


# Tool definitions for chat with ticket management
TICKET_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "Create a new support ticket. Use this when the user wants to log an issue, create a ticket, or report a problem.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Short descriptive title for the ticket (max 100 chars)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed description of the issue or request"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                        "description": "Priority level. Use 'critical' for urgent issues, 'high' for important, 'medium' for normal, 'low' for minor issues."
                    },
                    "category": {
                        "type": "string",
                        "description": "Category of the ticket (e.g., billing, technical_support, feature_request, account_issue)"
                    }
                },
                "required": ["title", "description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_ticket",
            "description": "Get details of a specific ticket by its ticket number. Use this when the user asks about a specific ticket.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_number": {
                        "type": "integer",
                        "description": "The ticket number (e.g., 47 for ticket #47)"
                    }
                },
                "required": ["ticket_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_ticket",
            "description": "Update a ticket's status or add notes. Use this when the user wants to change a ticket's status, add information, or close a ticket.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_number": {
                        "type": "integer",
                        "description": "The ticket number to update"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["open", "in_progress", "resolved", "closed"],
                        "description": "New status for the ticket"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Notes to add to the ticket"
                    }
                },
                "required": ["ticket_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_tickets",
            "description": "Search for tickets by keyword or filter by status. Use this when the user wants to find tickets or see a list of tickets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to find tickets by title or description"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["open", "in_progress", "resolved", "closed", "all"],
                        "description": "Filter by ticket status. Use 'all' to include all statuses."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default 10, max 20)"
                    }
                },
                "required": ["query"]
            }
        }
    }
]


async def chat_completion(
    messages: List[Dict[str, str]],
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    json_mode: bool = False,
    tools: Optional[List[Dict]] = None,
) -> Union[str, Tuple[str, List[Dict[str, Any]]]]:
    """
    Generate a chat completion using OpenRouter.

    Args:
        messages: List of message dicts with 'role' and 'content'
        system_prompt: Optional system prompt
        model: Model to use (defaults to settings.llm_model)
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature
        json_mode: If True, forces JSON output (model must support it)
        tools: Optional list of tool definitions for function calling

    Returns:
        If no tools or no tool calls: str (response content)
        If tools and tool calls: Tuple[str, List[Dict]] (content, tool_calls)
    """
    if not settings.openrouter_api_key:
        raise ValueError("OpenRouter API key not configured")

    model = model or settings.llm_model

    # Build messages list
    all_messages = []
    if system_prompt:
        all_messages.append({"role": "system", "content": system_prompt})
    all_messages.extend(messages)

    # Build request payload
    payload = {
        "model": model,
        "messages": all_messages,
        "max_tokens": max_tokens,
        "temperature": temperature
    }

    # Add JSON mode if requested (forces structured JSON output)
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    # Add tools if provided
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": settings.frontend_url,
                "X-Title": "SupportIQ"
            },
            json=payload
        )

        if response.status_code != 200:
            raise Exception(f"OpenRouter request failed: {response.text}")

        data = response.json()
        message = data["choices"][0]["message"]

        # Check if there are tool calls
        if tools and message.get("tool_calls"):
            tool_calls = []
            for tc in message["tool_calls"]:
                tool_calls.append({
                    "id": tc.get("id"),
                    "name": tc["function"]["name"],
                    "arguments": json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"]
                })
            return message.get("content", ""), tool_calls

        return message.get("content", "")


def build_rag_prompt(
    user_query: str,
    context_chunks: List[Dict[str, Any]],
    company_name: Optional[str] = None
) -> str:
    """
    Build a RAG prompt with retrieved context.
    """
    context_text = "\n\n---\n\n".join([
        f"Source: {chunk.get('title', 'Unknown')}\n{chunk.get('content', '')}"
        for chunk in context_chunks
    ])

    company_context = f" for {company_name}" if company_name else ""

    system_prompt = f"""You are a helpful customer support AI assistant{company_context}.
Your job is to answer questions based on the provided context from the company's knowledge base.

Guidelines:
- Answer questions accurately based on the provided context
- If the context doesn't contain relevant information, say so politely
- Be friendly, professional, and concise
- If asked about something not in the context, acknowledge the limitation
- Provide specific details when available
- Format responses clearly with bullet points or paragraphs as appropriate

CONTEXT FROM KNOWLEDGE BASE:
{context_text}

Remember: Only use information from the provided context. If you're unsure, ask clarifying questions."""

    return system_prompt
