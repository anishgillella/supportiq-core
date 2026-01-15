"""LLM service using OpenRouter"""
import httpx
from typing import List, Dict, Any, Optional
from app.core.config import settings


async def chat_completion(
    messages: List[Dict[str, str]],
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    json_mode: bool = False
) -> str:
    """
    Generate a chat completion using OpenRouter.

    Args:
        messages: List of message dicts with 'role' and 'content'
        system_prompt: Optional system prompt
        model: Model to use (defaults to settings.llm_model)
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature
        json_mode: If True, forces JSON output (model must support it)
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
        return data["choices"][0]["message"]["content"]


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
