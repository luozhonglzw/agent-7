"""Document management API endpoints.

Handles document upload, listing, deletion, and status tracking.

Endpoints:
    POST /documents/upload: Upload a new document
    GET  /documents: List user's documents
    GET  /documents/{id}: Get document details
    DELETE /documents/{id}: Delete a document
    POST /documents/{id}/reprocess: Reprocess a document
"""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_permission
from app.core.security.audit import audit_log
from app.database import get_db
from app.models.user import User

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload")
@require_permission("document", "upload")
@audit_log(action="upload", resource_type="document")
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Upload a new document for processing.

    Accepts PDF, DOCX, MD, TXT, and PPTX files.
    Initiates async processing pipeline (parse → chunk → embed → index).

    Requires ``document:upload`` permission.

    Args:
        request: FastAPI request (for audit context).
        background_tasks: Background tasks (for async audit write).
        current_user: Authenticated user.
        db: Database session.
    """
    # TODO: Implement in Phase 3
    return {"code": 0, "message": "Not implemented", "data": None}


@router.get("")
async def list_documents(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """List documents accessible to the current user.

    Returns paginated document list with status and metadata.
    Supports filtering by status, file type, and search query.

    Args:
        current_user: Authenticated user.
    """
    # TODO: Implement in Phase 3
    return {"code": 0, "message": "Not implemented", "data": None}


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get document details by ID.

    Returns full document metadata including processing status,
    chunk count, and token count.

    Args:
        document_id: Document UUID.
        current_user: Authenticated user.
    """
    # TODO: Implement in Phase 3
    return {"code": 0, "message": "Not implemented", "data": None}


@router.delete("/{document_id}")
@audit_log(action="delete", resource_type="document")
async def delete_document(
    document_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a document and all associated data.

    Removes document file, chunks, embeddings, and metadata.
    Only the owner or admin can delete documents.

    Args:
        document_id: Document UUID.
        request: FastAPI request (for audit context).
        background_tasks: Background tasks (for async audit write).
        current_user: Authenticated user.
        db: Database session.
    """
    # TODO: Implement in Phase 3
    return {"code": 0, "message": "Not implemented", "data": None}


@router.post("/{document_id}/reprocess")
@audit_log(action="reprocess", resource_type="document")
async def reprocess_document(
    document_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Reprocess a document.

    Deletes existing chunks and vectors, then re-runs the
    full processing pipeline.

    Args:
        document_id: Document UUID.
        request: FastAPI request (for audit context).
        background_tasks: Background tasks (for async audit write).
        current_user: Authenticated user.
        db: Database session.
    """
    # TODO: Implement in Phase 3
    return {"code": 0, "message": "Not implemented", "data": None}
