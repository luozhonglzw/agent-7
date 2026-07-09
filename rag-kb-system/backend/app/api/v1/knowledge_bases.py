"""Knowledge Base management API endpoints.

Handles KB CRUD operations and document association.

Endpoints:
    POST   /knowledge-bases: Create a knowledge base
    GET    /knowledge-bases: List accessible knowledge bases
    GET    /knowledge-bases/{id}: Get KB details
    PUT    /knowledge-bases/{id}: Update KB metadata
    DELETE /knowledge-bases/{id}: Delete a KB
    POST   /knowledge-bases/{id}/documents: Add documents to KB
    DELETE /knowledge-bases/{id}/documents: Remove documents from KB
    GET    /knowledge-bases/{id}/documents: List documents in KB
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.security.audit import audit_log
from app.database import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.schemas.document import DocumentResponse
from app.schemas.knowledge_base import (
    KBCreate,
    KBDocumentAdd,
    KBDocumentRemove,
    KBResponse,
    KBUpdate,
)
from app.services.kb_service import KBService

router = APIRouter(prefix="/knowledge-bases", tags=["Knowledge Bases"])


@router.post("", response_model=SuccessResponse[KBResponse], status_code=201)
@audit_log(action="create_kb", resource_type="knowledge_base")
async def create_knowledge_base(
    request: Request,
    background_tasks: BackgroundTasks,
    body: KBCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse[KBResponse]:
    """Create a new knowledge base.

    Args:
        request: FastAPI request (for audit context).
        background_tasks: Background tasks (for async audit write).
        body: KB creation data.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        SuccessResponse with created KB.
    """
    service = KBService(db)
    kb = await service.create_kb(
        owner_id=current_user.id,
        name=body.name,
        description=body.description,
        visibility=body.visibility,
    )
    return SuccessResponse(data=KBResponse.model_validate(kb))


@router.get("", response_model=SuccessResponse[PaginatedResponse])
async def list_knowledge_bases(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> SuccessResponse[PaginatedResponse]:
    """List knowledge bases accessible to the current user.

    Returns KBs based on visibility rules:
    - PUBLIC: everyone can see
    - DEPT: same department users can see
    - PRIVATE: only owner can see

    Args:
        current_user: Authenticated user.
        db: Database session.
        page: Page number (1-based).
        page_size: Items per page.

    Returns:
        Paginated list of knowledge bases.
    """
    service = KBService(db)
    kbs, total = await service.list_kbs(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )

    items = [KBResponse.model_validate(kb).model_dump() for kb in kbs]
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


@router.get("/{kb_id}", response_model=SuccessResponse[KBResponse])
async def get_knowledge_base(
    kb_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse[KBResponse]:
    """Get knowledge base details by ID.

    Args:
        kb_id: Knowledge base UUID.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        KB details.
    """
    service = KBService(db)
    kb = await service.get_kb(
        kb_id=uuid.UUID(kb_id),
        user_id=current_user.id,
    )
    return SuccessResponse(data=KBResponse.model_validate(kb))


@router.put("/{kb_id}", response_model=SuccessResponse[KBResponse])
async def update_knowledge_base(
    kb_id: str,
    body: KBUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse[KBResponse]:
    """Update knowledge base metadata.

    Only the owner or admin can update.

    Args:
        kb_id: Knowledge base UUID.
        body: Update data.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Updated KB details.
    """
    service = KBService(db)
    kb = await service.update_kb(
        kb_id=uuid.UUID(kb_id),
        user_id=current_user.id,
        name=body.name,
        description=body.description,
        visibility=body.visibility,
    )
    return SuccessResponse(data=KBResponse.model_validate(kb))


@router.delete("/{kb_id}", response_model=SuccessResponse)
@audit_log(action="delete_kb", resource_type="knowledge_base")
async def delete_knowledge_base(
    kb_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse:
    """Delete a knowledge base.

    Soft-deletes the KB and removes all document associations.
    Does NOT delete the documents themselves.

    Args:
        kb_id: Knowledge base UUID.
        request: FastAPI request (for audit context).
        background_tasks: Background tasks (for async audit write).
        current_user: Authenticated user.
        db: Database session.

    Returns:
        SuccessResponse confirming deletion.
    """
    service = KBService(db)
    await service.delete_kb(
        kb_id=uuid.UUID(kb_id),
        user_id=current_user.id,
    )
    return SuccessResponse(message="Knowledge base deleted")


@router.post("/{kb_id}/documents", response_model=SuccessResponse)
@audit_log(action="add_kb_docs", resource_type="knowledge_base")
async def add_documents_to_kb(
    kb_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    body: KBDocumentAdd,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse:
    """Add documents to a knowledge base.

    Silently skips documents that are already associated or don't exist.

    Args:
        kb_id: Knowledge base UUID.
        request: FastAPI request (for audit context).
        background_tasks: Background tasks (for async audit write).
        body: Document IDs to add.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        SuccessResponse with count of added documents.
    """
    service = KBService(db)
    added = await service.add_documents(
        kb_id=uuid.UUID(kb_id),
        user_id=current_user.id,
        document_ids=body.document_ids,
    )
    return SuccessResponse(
        message=f"Added {added} documents",
        data={"added": added},
    )


@router.delete("/{kb_id}/documents", response_model=SuccessResponse)
@audit_log(action="remove_kb_docs", resource_type="knowledge_base")
async def remove_documents_from_kb(
    kb_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    body: KBDocumentRemove,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse:
    """Remove documents from a knowledge base.

    Args:
        kb_id: Knowledge base UUID.
        request: FastAPI request (for audit context).
        background_tasks: Background tasks (for async audit write).
        body: Document IDs to remove.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        SuccessResponse with count of removed documents.
    """
    service = KBService(db)
    removed = await service.remove_documents(
        kb_id=uuid.UUID(kb_id),
        user_id=current_user.id,
        document_ids=body.document_ids,
    )
    return SuccessResponse(
        message=f"Removed {removed} documents",
        data={"removed": removed},
    )


@router.get("/{kb_id}/documents", response_model=SuccessResponse[PaginatedResponse])
async def list_kb_documents(
    kb_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> SuccessResponse[PaginatedResponse]:
    """List documents in a knowledge base.

    Args:
        kb_id: Knowledge base UUID.
        current_user: Authenticated user.
        db: Database session.
        page: Page number (1-based).
        page_size: Items per page.

    Returns:
        Paginated list of documents in the KB.
    """
    service = KBService(db)
    documents, total = await service.list_kb_documents(
        kb_id=uuid.UUID(kb_id),
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )

    items = [DocumentResponse.model_validate(doc).model_dump() for doc in documents]
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
