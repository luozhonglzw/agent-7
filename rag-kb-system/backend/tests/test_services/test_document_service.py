"""DocumentService unit tests.

Tests for document upload, listing, deletion, and update.
"""

import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import (
    DocumentNotFoundError,
    FileSizeExceededError,
    UnsupportedFileTypeError,
)
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.services.document_service import DocumentService


@pytest_asyncio.fixture
def service(db_session: AsyncSession) -> DocumentService:
    """Create DocumentService with test session."""
    return DocumentService(db_session)


@pytest_asyncio.fixture
async def sample_document(db_session: AsyncSession, test_user: User) -> Document:
    """Create a sample document in the database."""
    doc = Document(
        user_id=test_user.id,
        owner_id=test_user.id,
        title="Test Document",
        filename="test.txt",
        file_path="/tmp/test.txt",
        file_size=1024,
        file_type=".txt",
        status=DocumentStatus.PENDING,
        is_public=False,
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


class TestUploadDocument:
    """Tests for DocumentService.upload_document."""

    @patch("app.services.document_service.process_document")
    async def test_upload_success(
        self, mock_task: object, service: DocumentService, test_user: User, tmp_path: Path
    ) -> None:
        """Test successful document upload."""
        with patch("app.config.settings.storage.upload_path", tmp_path):
            doc, task_id = await service.upload_document(
                user_id=test_user.id,
                filename="test.txt",
                file_content=b"Hello World",
                title="Test",
            )

        assert doc.title == "Test"
        assert doc.filename == "test.txt"
        assert doc.file_size == 11
        assert doc.file_type == ".txt"
        assert doc.status == DocumentStatus.PENDING
        assert doc.user_id == test_user.id

    @patch("app.services.document_service.process_document")
    async def test_upload_default_title(
        self, mock_task: object, service: DocumentService, test_user: User, tmp_path: Path
    ) -> None:
        """Test upload uses filename stem as default title."""
        with patch("app.config.settings.storage.upload_path", tmp_path):
            doc, _ = await service.upload_document(
                user_id=test_user.id,
                filename="my_report.pdf",
                file_content=b"PDF content",
            )

        assert doc.title == "my_report"

    async def test_upload_unsupported_type(
        self, service: DocumentService, test_user: User
    ) -> None:
        """Test upload with unsupported file type."""
        with pytest.raises(UnsupportedFileTypeError):
            await service.upload_document(
                user_id=test_user.id,
                filename="test.xyz",
                file_content=b"content",
            )

    async def test_upload_file_too_large(
        self, service: DocumentService, test_user: User
    ) -> None:
        """Test upload with file exceeding size limit."""
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB
        with pytest.raises(FileSizeExceededError):
            await service.upload_document(
                user_id=test_user.id,
                filename="large.txt",
                file_content=large_content,
            )

    @patch("app.services.document_service.process_document")
    async def test_upload_public_flag(
        self, mock_task: object, service: DocumentService, test_user: User, tmp_path: Path
    ) -> None:
        """Test upload with is_public flag."""
        with patch("app.config.settings.storage.upload_path", tmp_path):
            doc, _ = await service.upload_document(
                user_id=test_user.id,
                filename="public.txt",
                file_content=b"content",
                is_public=True,
            )

        assert doc.is_public is True


class TestGetDocument:
    """Tests for DocumentService.get_document."""

    async def test_get_existing_document(
        self, service: DocumentService, sample_document: Document, test_user: User
    ) -> None:
        """Test getting an existing document."""
        doc = await service.get_document(sample_document.id, test_user.id)
        assert doc.id == sample_document.id

    async def test_get_nonexistent_document(
        self, service: DocumentService
    ) -> None:
        """Test getting a nonexistent document raises error."""
        with pytest.raises(DocumentNotFoundError):
            await service.get_document(uuid.uuid4())


class TestListDocuments:
    """Tests for DocumentService.list_documents."""

    async def test_list_empty(
        self, service: DocumentService, test_user: User
    ) -> None:
        """Test listing documents when none exist."""
        docs, total = await service.list_documents(test_user.id)
        assert docs == []
        assert total == 0

    async def test_list_with_documents(
        self, service: DocumentService, sample_document: Document, test_user: User
    ) -> None:
        """Test listing documents returns results."""
        docs, total = await service.list_documents(test_user.id)
        assert total >= 1
        assert any(d.id == sample_document.id for d in docs)

    async def test_list_pagination(
        self, service: DocumentService, test_user: User
    ) -> None:
        """Test pagination parameters."""
        docs, total = await service.list_documents(
            test_user.id, page=1, page_size=1
        )
        assert len(docs) <= 1


class TestDeleteDocument:
    """Tests for DocumentService.delete_document."""

    async def test_delete_own_document(
        self, service: DocumentService, sample_document: Document, test_user: User
    ) -> None:
        """Test deleting own document."""
        await service.delete_document(sample_document.id, test_user.id)

        # Verify soft deleted
        with pytest.raises(DocumentNotFoundError):
            await service.get_document(sample_document.id)


class TestUpdateDocument:
    """Tests for DocumentService.update_document."""

    async def test_update_title(
        self, service: DocumentService, sample_document: Document, test_user: User
    ) -> None:
        """Test updating document title."""
        doc = await service.update_document(
            sample_document.id, test_user.id, title="New Title"
        )
        assert doc.title == "New Title"

    async def test_update_public_flag(
        self, service: DocumentService, sample_document: Document, test_user: User
    ) -> None:
        """Test updating public flag."""
        doc = await service.update_document(
            sample_document.id, test_user.id, is_public=True
        )
        assert doc.is_public is True
