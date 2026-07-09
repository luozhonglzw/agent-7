"""Document management API endpoints.

Handles document upload, listing, deletion, and status tracking.

Endpoints:
    POST /documents/upload: Upload a new document
    GET  /documents: List user's documents
    GET  /documents/{id}: Get document details
    DELETE /documents/{id}: Delete a document
    POST /documents/{id}/reprocess: Reprocess a document
"""

from fastapi import APIRouter

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload")
async def upload_document():
    """Upload a new document for processing.

    Accepts PDF, DOCX, MD, TXT, and PPTX files.
    Initiates async processing pipeline (parse → chunk → embed → index).
    """
    # TODO: Implement in Phase 3
    return {"code": 0, "message": "Not implemented", "data": None}


@router.get("")
async def list_documents():
    """List documents accessible to the current user.

    Returns paginated document list with status and metadata.
    Supports filtering by status, file type, and search query.
    """
    # TODO: Implement in Phase 3
    return {"code": 0, "message": "Not implemented", "data": None}


@router.get("/{document_id}")
async def get_document(document_id: str):
    """Get document details by ID.

    Returns full document metadata including processing status,
    chunk count, and token count.
    """
    # TODO: Implement in Phase 3
    return {"code": 0, "message": "Not implemented", "data": None}


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """Delete a document and all associated data.

    Removes document file, chunks, embeddings, and metadata.
    Only the owner or admin can delete documents.
    """
    # TODO: Implement in Phase 3
    return {"code": 0, "message": "Not implemented", "data": None}


@router.post("/{document_id}/reprocess")
async def reprocess_document(document_id: str):
    """Reprocess a document.

    Deletes existing chunks and vectors, then re-runs the
    full processing pipeline.
    """
    # TODO: Implement in Phase 3
    return {"code": 0, "message": "Not implemented", "data": None}
