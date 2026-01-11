"""Pinecone vector database service"""
from pinecone import Pinecone
from typing import List, Dict, Any, Optional
from app.core.config import settings


_pinecone_client: Optional[Pinecone] = None
_index = None


def get_pinecone():
    """Get Pinecone index using the configured host"""
    global _pinecone_client, _index

    if not settings.pinecone_api_key:
        raise ValueError("Pinecone API key not configured")

    if _index is None:
        _pinecone_client = Pinecone(api_key=settings.pinecone_api_key)
        # Connect to existing index using host
        _index = _pinecone_client.Index(host=settings.pinecone_host)

    return _index


def upsert_vectors(
    vectors: List[Dict[str, Any]],
    namespace: str
) -> int:
    """
    Upsert vectors to Pinecone
    vectors: List of dicts with 'id', 'values' (embedding), and 'metadata'
    namespace: User-specific namespace (user_id)
    """
    index = get_pinecone()

    # Pinecone recommends batches of 100
    batch_size = 100
    upserted_count = 0

    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i + batch_size]
        index.upsert(vectors=batch, namespace=namespace)
        upserted_count += len(batch)

    return upserted_count


def query_vectors(
    query_embedding: List[float],
    namespace: str,
    top_k: int = 5,
    filter: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Query similar vectors from Pinecone
    Returns list of matches with 'id', 'score', and 'metadata'
    """
    index = get_pinecone()

    results = index.query(
        vector=query_embedding,
        namespace=namespace,
        top_k=top_k,
        include_metadata=True,
        filter=filter
    )

    return [
        {
            "id": match.id,
            "score": match.score,
            "metadata": match.metadata
        }
        for match in results.matches
    ]


def delete_vectors(
    ids: List[str],
    namespace: str
) -> None:
    """Delete vectors by ID"""
    index = get_pinecone()
    index.delete(ids=ids, namespace=namespace)


def delete_namespace(namespace: str) -> None:
    """Delete all vectors in a namespace"""
    index = get_pinecone()
    index.delete(delete_all=True, namespace=namespace)
