"""Embedding service using OpenAI"""
import openai
from typing import List
from app.core.config import settings


def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for a list of texts using OpenAI"""
    if not settings.openai_api_key:
        raise ValueError("OpenAI API key not configured")

    client = openai.OpenAI(api_key=settings.openai_api_key)

    response = client.embeddings.create(
        model=settings.embedding_model,
        input=texts,
        dimensions=settings.embedding_dimensions  # Request 1024 dimensions
    )

    return [item.embedding for item in response.data]


def get_embedding(text: str) -> List[float]:
    """Generate embedding for a single text"""
    embeddings = get_embeddings([text])
    return embeddings[0]
