"""Knowledge base management endpoints"""
from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
import uuid

from app.core.security import get_current_user, TokenData
from app.core.database import get_supabase_admin
from app.services.scraper import scrape_website_simple, chunk_text
from app.services.embeddings import get_embeddings
from app.services.pinecone_service import upsert_vectors, delete_vectors

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])


class ScrapeRequest(BaseModel):
    website_url: str


class DocumentResponse(BaseModel):
    id: str
    title: str
    source: str
    source_type: str
    chunks_count: int
    created_at: str


class DocumentsListResponse(BaseModel):
    documents: List[DocumentResponse]


@router.post("/scrape")
async def scrape_website(
    request: ScrapeRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """Scrape a website and add it to the knowledge base"""
    supabase = get_supabase_admin()

    try:
        # Scrape the website
        pages = await scrape_website_simple(request.website_url)

        if not pages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract content from the website"
            )

        documents_created = 0
        total_chunks = 0

        for page in pages:
            # Create document record
            doc_result = supabase.table("knowledge_documents").insert({
                "user_id": current_user.user_id,
                "title": page["title"],
                "source": page["url"],
                "source_type": "website",
                "content": page["content"],
                "metadata": {"scraped_from": request.website_url}
            }).execute()

            if not doc_result.data:
                continue

            document = doc_result.data[0]
            documents_created += 1

            # Chunk the content
            chunks = chunk_text(page["content"])

            if not chunks:
                continue

            # Generate embeddings
            try:
                embeddings = get_embeddings(chunks)
            except Exception as e:
                print(f"Embedding generation failed: {e}")
                continue

            # Prepare vectors for Pinecone
            vectors = []
            chunk_records = []

            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                vector_id = f"{document['id']}_{i}"
                vectors.append({
                    "id": vector_id,
                    "values": embedding,
                    "metadata": {
                        "document_id": document["id"],
                        "chunk_index": i,
                        "title": page["title"],
                        "content": chunk[:1000],  # Store truncated content in metadata
                        "source": page["url"]
                    }
                })

                chunk_records.append({
                    "document_id": document["id"],
                    "user_id": current_user.user_id,
                    "chunk_index": i,
                    "content": chunk,
                    "embedding_id": vector_id,
                    "metadata": {"source": page["url"]}
                })

            # Upsert to Pinecone
            try:
                upsert_vectors(vectors, namespace=current_user.user_id)
            except Exception as e:
                print(f"Pinecone upsert failed: {e}")

            # Save chunks to database
            if chunk_records:
                supabase.table("knowledge_chunks").insert(chunk_records).execute()

            # Update document with chunk count
            supabase.table("knowledge_documents").update({
                "chunks_count": len(chunks)
            }).eq("id", document["id"]).execute()

            total_chunks += len(chunks)

        return {
            "success": True,
            "documents_count": documents_created,
            "chunks_count": total_chunks
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scrape website: {str(e)}"
        )


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user)
):
    """Upload a document to the knowledge base"""
    supabase = get_supabase_admin()

    # Check file type
    allowed_types = ["text/plain", "application/pdf", "text/markdown"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not supported. Allowed: {allowed_types}"
        )

    try:
        content = await file.read()
        text_content = content.decode("utf-8")

        # Create document record
        doc_result = supabase.table("knowledge_documents").insert({
            "user_id": current_user.user_id,
            "title": file.filename,
            "source": file.filename,
            "source_type": "text",
            "content": text_content,
            "metadata": {"filename": file.filename, "content_type": file.content_type}
        }).execute()

        if not doc_result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create document"
            )

        document = doc_result.data[0]

        # Chunk the content
        chunks = chunk_text(text_content)

        if chunks:
            # Generate embeddings
            embeddings = get_embeddings(chunks)

            # Prepare vectors for Pinecone
            vectors = []
            chunk_records = []

            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                vector_id = f"{document['id']}_{i}"
                vectors.append({
                    "id": vector_id,
                    "values": embedding,
                    "metadata": {
                        "document_id": document["id"],
                        "chunk_index": i,
                        "title": file.filename,
                        "content": chunk[:1000],
                        "source": file.filename
                    }
                })

                chunk_records.append({
                    "document_id": document["id"],
                    "user_id": current_user.user_id,
                    "chunk_index": i,
                    "content": chunk,
                    "embedding_id": vector_id,
                    "metadata": {"filename": file.filename}
                })

            # Upsert to Pinecone
            try:
                upsert_vectors(vectors, namespace=current_user.user_id)
            except Exception as e:
                print(f"Pinecone upsert failed: {e}")

            # Save chunks to database
            supabase.table("knowledge_chunks").insert(chunk_records).execute()

            # Update document with chunk count
            supabase.table("knowledge_documents").update({
                "chunks_count": len(chunks)
            }).eq("id", document["id"]).execute()

        return {
            "success": True,
            "document_id": document["id"],
            "chunks_count": len(chunks) if chunks else 0
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {str(e)}"
        )


@router.get("/documents", response_model=DocumentsListResponse)
async def list_documents(current_user: TokenData = Depends(get_current_user)):
    """List all documents in the knowledge base"""
    supabase = get_supabase_admin()

    result = supabase.table("knowledge_documents") \
        .select("id, title, source, source_type, chunks_count, created_at") \
        .eq("user_id", current_user.user_id) \
        .order("created_at", desc=True) \
        .execute()

    return {"documents": result.data or []}


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Delete a document and its chunks"""
    supabase = get_supabase_admin()

    # Verify ownership
    doc = supabase.table("knowledge_documents") \
        .select("id") \
        .eq("id", document_id) \
        .eq("user_id", current_user.user_id) \
        .execute()

    if not doc.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Get chunk IDs for Pinecone deletion
    chunks = supabase.table("knowledge_chunks") \
        .select("embedding_id") \
        .eq("document_id", document_id) \
        .execute()

    if chunks.data:
        vector_ids = [c["embedding_id"] for c in chunks.data if c["embedding_id"]]
        if vector_ids:
            try:
                delete_vectors(vector_ids, namespace=current_user.user_id)
            except Exception as e:
                print(f"Pinecone deletion failed: {e}")

    # Delete from database (cascade will handle chunks)
    supabase.table("knowledge_documents").delete().eq("id", document_id).execute()

    return {"success": True}
