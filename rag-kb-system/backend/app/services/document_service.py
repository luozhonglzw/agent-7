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
from app.models.user import User

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
    ) -> tuple[Document, str]:
        """Upload and register a new document.

        Validates file size and type, writes the file to disk,
        creates a database record, and enqueues async processing.

        Args:
            user_id: Uploading user UUID.
            filename: Original filename.
            file_content: File binary content.
            title: Optional document title.
            is_public: Public access flag.

        Returns:
            Tuple of (Document instance, Celery task_id).

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

        # Guess MIME type
        mime_type = self._guess_mime(file_ext)

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
            mime_type=mime_type,
            status=DocumentStatus.PENDING,
            is_public=is_public,
        )
        self.db.add(document)
        await self.db.flush()

        # Enqueue async processing (lazy import to avoid circular dependency)
        from app.tasks.document import process_document

        result = process_document.apply_async(
            args=[str(doc_id), str(storage_path), file_ext],
            task_id=str(doc_id),
        )

        logger.info(
            "Document uploaded: %s (%s, %d bytes) by user %s, task=%s",
            doc_id, filename, file_size, user_id, result.id,
        )
        return document, result.id

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
            # Check if user is admin/manager via role
            user_result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            if user is None or not user.is_manager:
                raise AuthorizationError(
                    detail="You don't have access to this document"
                )

        return document

    async def list_documents(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        kb_id: uuid.UUID | None = None,
    ) -> tuple[list[Document], int]:
        """List documents for a user.

        Args:
            user_id: User UUID.
            page: Page number (1-based).
            page_size: Items per page.
            status: Optional status filter.
            kb_id: Optional knowledge base filter (reserved for Phase 3+).

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

    async def list_all_documents(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
    ) -> tuple[list[Document], int]:
        """List all documents (admin/manager view).

        Args:
            page: Page number (1-based).
            page_size: Items per page.
            status: Optional status filter.

        Returns:
            Tuple of (documents list, total count).
        """
        query = select(Document).where(
            Document.is_deleted == False,  # noqa: E712
        )

        if status:
            query = query.where(Document.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

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

        # Check ownership or admin role
        if document.user_id != user_id:
            user_result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            if user is None or not user.is_admin:
                raise AuthorizationError(
                    detail="Only the owner or admin can delete this document"
                )

        document.soft_delete()
        await self.db.flush()

        logger.info("Document deleted: %s by user %s", document_id, user_id)

    async def update_document(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str | None = None,
        is_public: bool | None = None,
    ) -> Document:
        """Update document metadata.

        Args:
            document_id: Document UUID.
            user_id: Requesting user UUID.
            title: New title (None to skip).
            is_public: New public flag (None to skip).

        Returns:
            Updated Document instance.

        Raises:
            DocumentNotFoundError: If document not found.
            AuthorizationError: If user is not the owner.
        """
        document = await self.get_document(document_id, user_id)

        if title is not None:
            document.title = title
        if is_public is not None:
            document.is_public = is_public

        await self.db.flush()
        await self.db.refresh(document)

        logger.info("Document updated: %s by user %s", document_id, user_id)
        return document

    async def replace_document(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        filename: str,
        file_content: bytes,
    ) -> tuple[Document, str]:
        """Replace a document's file and re-trigger processing.

        The old file is kept on disk (no cleanup).  The document
        status is reset to PENDING and a new Celery task is enqueued.

        Args:
            document_id: Document UUID.
            user_id: Requesting user UUID.
            filename: New filename.
            file_content: New file content.

        Returns:
            Tuple of (Document, task_id).

        Raises:
            DocumentNotFoundError: If document not found.
            AuthorizationError: If user is not the owner.
            FileSizeExceededError: If file is too large.
            UnsupportedFileTypeError: If file type not supported.
        """
        document = await self.get_document(document_id, user_id)

        # Validate
        file_size = len(file_content)
        if file_size > settings.storage.max_file_size_bytes:
            raise FileSizeExceededError(
                max_size_mb=settings.storage.max_file_size_mb,
                actual_size_mb=file_size // (1024 * 1024),
            )

        file_ext = Path(filename).suffix.lower()
        if file_ext not in settings.storage.allowed_extension_list:
            raise UnsupportedFileTypeError(
                file_type=file_ext,
                allowed=settings.storage.allowed_extension_list,
            )

        # Write new file
        storage_path = settings.storage.upload_path / str(document_id) / filename
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        storage_path.write_bytes(file_content)

        # Update document record
        document.filename = filename
        document.file_path = str(storage_path)
        document.file_size = file_size
        document.file_type = file_ext
        document.mime_type = self._guess_mime(file_ext)
        document.status = DocumentStatus.PENDING
        document.error_message = None
        document.chunk_count = None
        document.token_count = None
        document.processed_at = None
        await self.db.flush()

        # Enqueue processing
        from app.tasks.document import process_document

        result = process_document.apply_async(
            args=[str(document_id), str(storage_path), file_ext],
            task_id=str(document_id),
        )

        logger.info(
            "Document replaced: %s by user %s, task=%s",
            document_id, user_id, result.id,
        )
        return document, result.id

    @staticmethod
    def _guess_mime(ext: str) -> str | None:
        """Guess MIME type from file extension.

        Args:
            ext: File extension (with leading dot).

        Returns:
            MIME type string or None.
        """
        mime_map = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".ppt": "application/vnd.ms-powerpoint",
            ".md": "text/markdown",
            ".txt": "text/plain",
            ".csv": "text/csv",
            ".py": "text/x-python",
            ".js": "text/javascript",
            ".ts": "text/typescript",
            ".java": "text/x-java",
            ".cpp": "text/x-c++src",
            ".c": "text/x-csrc",
            ".go": "text/x-go",
            ".rs": "text/x-rust",
            ".html": "text/html",
            ".css": "text/css",
            ".json": "application/json",
            ".yaml": "text/yaml",
            ".yml": "text/yaml",
            ".toml": "text/toml",
            ".sql": "text/x-sql",
            ".sh": "text/x-shellscript",
        }
        return mime_map.get(ext)
