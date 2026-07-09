"""Document management service.

Handles document CRUD, file upload, and processing orchestration.

Usage:
    from app.services.document_service import DocumentService

    service = DocumentService(db_session)
    doc = await service.upload_document(user_id, file, title)
"""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import (
    DocumentNotFoundError,
    FileSizeExceededError,
    UnsupportedFileTypeError,
    AuthorizationError,
)
from app.models.document import Document, DocumentStatus
from app.tasks.document import process_document

logger = logging.getLogger(__name__)


class DocumentService:
    """Document management service.

    Manages document lifecycle from upload through processing.

    Attributes:
        db: Async database session.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize document service.

        Args:
            db: Async database session.
        """
        self.db = db

    async def upload_document(
        self,
        user_id: uuid.UUID,
        filename: str,
        file_content: bytes,
        title: str | None = None,
        is_public: bool = False,
    ) -> Document:
        """Upload and register a new document.

        Args:
            user_id: Uploading user UUID.
            filename: Original filename.
            file_content: File binary content.
            title: Optional document title.
            is_public: Public access flag.

        Returns:
            Created Document instance.

        Raises:
            FileSizeExceededError: If file is too large.
            UnsupportedFileTypeError: If file type not supported.
        """
        # Validate file size
        file_size = len(file_content)
        if file_size > settings.storage.max_file_size_bytes:
            raise FileSizeExceededError(
                max_size_mb=settings.storage.max_file_size_mb,
                actual_size_mb=file_size // (1024 * 1024),
            )

        # Validate file type
        file_ext = Path(filename).suffix.lower()
        if file_ext not in settings.storage.allowed_extension_list:
            raise UnsupportedFileTypeError(
                file_type=file_ext,
                allowed=settings.storage.allowed_extension_list,
            )

        # Generate storage path
        doc_id = uuid.uuid4()
        storage_path = settings.storage.upload_path / str(doc_id) / filename
        storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file to disk
        storage_path.write_bytes(file_content)

        # Create database record
        document = Document(
            id=doc_id,
            user_id=user_id,
            owner_id=user_id,
            title=title or Path(filename).stem,
            filename=filename,
            file_path=str(storage_path),
            file_size=file_size,
            file_type=file_ext,
            status=DocumentStatus.PENDING,
            is_public=is_public,
        )
        self.db.add(document)
        await self.db.flush()

        # Enqueue async processing
        process_document.apply_async(
            args=[str(doc_id), str(storage_path), file_ext],
            task_id=str(doc_id),
        )

        logger.info(
            "Document uploaded: %s (%s, %d bytes) by user %s",
            doc_id, filename, file_size, user_id,
        )
        return document

    async def get_document(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> Document:
        """Get document by ID with permission check.

        Args:
            document_id: Document UUID.
            user_id: Requesting user UUID (for permission check).

        Returns:
            Document instance.

        Raises:
            DocumentNotFoundError: If document not found.
            AuthorizationError: If user lacks access.
        """
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.is_deleted == False,  # noqa: E712
            )
        )
        document = result.scalar_one_or_none()

        if document is None:
            raise DocumentNotFoundError(str(document_id))

        # Permission check
        if user_id and not document.is_public and document.user_id != user_id:
            raise AuthorizationError(detail="You don't have access to this document")

        return document

    async def list_documents(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
    ) -> tuple[list[Document], int]:
        """List documents for a user.

        Args:
            user_id: User UUID.
            page: Page number.
            page_size: Items per page.
            status: Optional status filter.

        Returns:
            Tuple of (documents list, total count).
        """
        query = select(Document).where(
            Document.user_id == user_id,
            Document.is_deleted == False,  # noqa: E712
        )

        if status:
            query = query.where(Document.status == status)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Get paginated results
        offset = (page - 1) * page_size
        query = query.order_by(Document.created_at.desc())
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(query)
        documents = list(result.scalars().all())

        return documents, total

    async def delete_document(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Soft delete a document.

        Args:
            document_id: Document UUID.
            user_id: Requesting user UUID.

        Raises:
            DocumentNotFoundError: If document not found.
            AuthorizationError: If user is not the owner.
        """
        document = await self.get_document(document_id)

        if document.user_id != user_id:
            raise AuthorizationError(detail="Only the owner can delete this document")

        document.soft_delete()
        await self.db.flush()

        logger.info("Document deleted: %s by user %s", document_id, user_id)
