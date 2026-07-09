"""Document management API endpoints.

Handles document upload, listing, deletion, and status tracking.

Endpoints:
    POST   /documents/upload: Upload a new document
    GET    /documents: List user's documents
    GET    /documents/{id}: Get document details
    DELETE /documents/{id}: Delete a document
    PUT    /documents/{id}: Update document metadata or replace file
    POST   /documents/{id}/reprocess: Reprocess a document
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_permission
from app.core.security.audit import audit_log
from app.database import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.schemas.document import DocumentResponse, DocumentUpdateRequest
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=SuccessResponse, status_code=201)
@require_permission("document", "upload")
@audit_log(action="upload", resource_type="document")
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(..., description="File to upload"),
    title: str | None = Form(default=None, description="Document title"),
    is_public: bool = Form(default=False, description="Public access flag"),
) -> SuccessResponse:
    """Upload a new document for processing.

    Accepts multipart/form-data with a file and optional metadata.
    Saves the file, creates a DB record, and triggers async processing.

    Requires ``document:upload`` permission.

    Args:
        request: FastAPI request (for audit context).
        background_tasks: Background tasks (for async audit write).
        current_user: Authenticated user.
        db: Database session.
        file: Uploaded file.
        title: Optional document title.
        is_public: Public access flag.

    Returns:
        SuccessResponse with document ID, task ID, and status.
    """
    content = await file.read()
    service = DocumentService(db)
    document, task_id = await service.upload_document(
        user_id=current_user.id,
        filename=file.filename or "unnamed",
        file_content=content,
        title=title,
        is_public=is_public,
    )

    return SuccessResponse(
        data={
            "doc_id": str(document.id),
            "task_id": task_id,
            "status": document.status.value,
            "filename": document.filename,
            "file_size": document.file_size,
        }
    )


@router.get("", response_model=SuccessResponse[PaginatedResponse])
async def list_documents(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
) -> SuccessResponse[PaginatedResponse]:
    """List documents accessible to the current user.

    Returns paginated document list with status and metadata.

    Args:
        current_user: Authenticated user.
        db: Database session.
        page: Page number (1-based).
        page_size: Items per page.
        status: Optional status filter.

    Returns:
        Paginated list of documents.
    """
    service = DocumentService(db)
    documents, total = await service.list_documents(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        status=status,
    )

    items = [
        DocumentResponse.model_validate(doc).model_dump()
        for doc in documents
    ]

    total_pages = (total + page_size - 1) // page_size
    paginated = PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )
    return SuccessResponse(data=paginated)


@router.get("/{document_id}", response_model=SuccessResponse[DocumentResponse])
async def get_document(
    document_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse[DocumentResponse]:
    """Get document details by ID.

    Returns full document metadata including processing status,
    chunk count, and token count.

    Args:
        document_id: Document UUID.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Document details.
    """
    service = DocumentService(db)
    document = await service.get_document(
        document_id=uuid.UUID(document_id),
        user_id=current_user.id,
    )
    return SuccessResponse(data=DocumentResponse.model_validate(document))


@router.delete("/{document_id}", response_model=SuccessResponse)
@audit_log(action="delete", resource_type="document")
async def delete_document(
    document_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse:
    """Delete a document and all associated data.

    Soft-deletes the document record. Only the owner or admin
    can delete documents.

    Args:
        document_id: Document UUID.
        request: FastAPI request (for audit context).
        background_tasks: Background tasks (for async audit write).
        current_user: Authenticated user.
        db: Database session.

    Returns:
        SuccessResponse confirming deletion.
    """
    service = DocumentService(db)
    await service.delete_document(
        document_id=uuid.UUID(document_id),
        user_id=current_user.id,
    )
    return SuccessResponse(message="Document deleted")


@router.put("/{document_id}", response_model=SuccessResponse[DocumentResponse])
async def update_document(
    document_id: str,
    body: DocumentUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse[DocumentResponse]:
    """Update document metadata.

    Allows updating title and public access flag.

    Args:
        document_id: Document UUID.
        body: Update data.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Updated document details.
    """
    service = DocumentService(db)
    document = await service.update_document(
        document_id=uuid.UUID(document_id),
        user_id=current_user.id,
        title=body.title,
        is_public=body.is_public,
    )
    return SuccessResponse(data=DocumentResponse.model_validate(document))


@router.post("/{document_id}/replace", response_model=SuccessResponse)
@audit_log(action="replace", resource_type="document")
async def replace_document(
    document_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(..., description="Replacement file"),
) -> SuccessResponse:
    """Replace a document's file and re-trigger processing.

    The old file is replaced with the new upload, and a new
    processing task is enqueued.

    Args:
        document_id: Document UUID.
        request: FastAPI request (for audit context).
        background_tasks: Background tasks (for async audit write).
        current_user: Authenticated user.
        db: Database session.
        file: Replacement file.

    Returns:
        SuccessResponse with new task ID.
    """
    content = await file.read()
    service = DocumentService(db)
    document, task_id = await service.replace_document(
        document_id=uuid.UUID(document_id),
        user_id=current_user.id,
        filename=file.filename or "unnamed",
        file_content=content,
    )
    return SuccessResponse(
        data={
            "doc_id": str(document.id),
            "task_id": task_id,
            "status": document.status.value,
        }
    )


@router.post("/{document_id}/reprocess", response_model=SuccessResponse)
@audit_log(action="reprocess", resource_type="document")
async def reprocess_document(
    document_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse:
    """Reprocess a document.

    Re-runs the full processing pipeline on the existing file.

    Args:
        document_id: Document UUID.
        request: FastAPI request (for audit context).
        background_tasks: Background tasks (for async audit write).
        current_user: Authenticated user.
        db: Database session.

    Returns:
        SuccessResponse with task ID.
    """
    service = DocumentService(db)
    document = await service.get_document(
        document_id=uuid.UUID(document_id),
        user_id=current_user.id,
    )

    from app.tasks.document import process_document

    result = process_document.apply_async(
        args=[str(document.id), document.file_path, document.file_type],
        task_id=str(document.id),
    )

    return SuccessResponse(
        data={
            "doc_id": str(document.id),
            "task_id": result.id,
            "status": "pending",
        }
    )
