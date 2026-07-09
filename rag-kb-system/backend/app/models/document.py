"""Document and DocumentChunk SQLAlchemy models.

Defines the document management tables for storing uploaded files,
their processing status, and text chunks extracted from documents.

Tables:
    documents: Uploaded document metadata and processing status.
    document_chunks: Text chunks extracted from documents.
"""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class DocumentStatus(str, Enum):
    """Document processing status.

    Tracks the lifecycle of a document from upload through
    processing to ready or failed state.
    """

    PENDING = "pending"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"


class Document(BaseModel):
    """Document model for uploaded files.

    Stores metadata about uploaded documents including file info,
    processing status, and extracted content summary.

    Attributes:
        user_id: Foreign key to the uploading user.
        title: Document title (from filename or user input).
        filename: Original uploaded filename.
        file_path: Storage path for the uploaded file.
        file_size: File size in bytes.
        file_type: File extension (pdf, docx, etc.).
        mime_type: MIME type of the file.
        status: Current processing status.
        error_message: Error details if processing failed.
        page_count: Number of pages (for PDFs).
        chunk_count: Number of extracted text chunks.
        token_count: Total token count across all chunks.
        metadata_extra: Additional metadata (JSON).
        processed_at: Timestamp when processing completed.
        owner_id: Owner user ID (may differ from uploader).
        is_public: Whether document is publicly accessible.
        owner: Related user who uploaded the document.
        chunks: Related text chunks.
    """

    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_user_status", "user_id", "status"),
        Index("ix_documents_owner_public", "owner_id", "is_public"),
        Index("ix_documents_type", "file_type"),
        {"comment": "Uploaded documents"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Uploading user ID",
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Document title",
    )
    filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Original filename",
    )
    file_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Storage file path",
    )
    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="File size in bytes",
    )
    file_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="File extension",
    )
    mime_type: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="MIME type",
    )
    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(DocumentStatus, name="document_status"),
        default=DocumentStatus.PENDING,
        nullable=False,
        index=True,
        comment="Processing status",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error details if processing failed",
    )
    page_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of pages",
    )
    chunk_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of text chunks",
    )
    token_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Total token count",
    )
    metadata_extra: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Additional metadata",
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Processing completion timestamp",
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Document owner (defaults to uploader)",
    )
    is_public: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Public access flag",
    )

    # Relationships
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="DocumentChunk.chunk_index",
    )

    @property
    def is_ready(self) -> bool:
        """Check if document processing is complete.

        Returns:
            True if document status is READY.
        """
        return self.status == DocumentStatus.READY

    @property
    def file_size_mb(self) -> float:
        """Get file size in megabytes.

        Returns:
            File size in MB.
        """
        return self.file_size / (1024 * 1024)

    def __repr__(self) -> str:
        return (
            f"<Document(id={self.id}, title='{self.title}', "
            f"status={self.status.value})>"
        )


class DocumentChunk(BaseModel):
    """Text chunk extracted from a document.

    Stores individual text segments with position information
    for retrieval and citation.

    Attributes:
        document_id: Foreign key to parent document.
        chunk_index: Sequential index within the document.
        content: Text content of the chunk.
        token_count: Number of tokens in this chunk.
        page_number: Source page number (if applicable).
        start_char: Character offset in original document.
        end_char: Character end offset in original document.
        heading: Section heading (if available).
        heading_level: Heading hierarchy level.
        metadata_extra: Additional chunk metadata (JSON).
        document: Related parent document.
    """

    __tablename__ = "document_chunks"
    __table_args__ = (
        Index("ix_document_chunks_doc_index", "document_id", "chunk_index"),
        Index("ix_document_chunks_doc_page", "document_id", "page_number"),
        {"comment": "Text chunks from documents"},
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent document ID",
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Sequential chunk index",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Chunk text content",
    )
    token_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Token count",
    )
    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Source page number",
    )
    start_char: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Start character offset",
    )
    end_char: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="End character offset",
    )
    heading: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Section heading",
    )
    heading_level: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Heading hierarchy level",
    )
    metadata_extra: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Additional metadata",
    )

    # Relationships
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="chunks",
        lazy="selectin",
    )

    @property
    def preview(self) -> str:
        """Get a preview of the chunk content.

        Returns:
            First 200 characters of content with ellipsis.
        """
        if len(self.content) <= 200:
            return self.content
        return self.content[:197] + "..."

    def __repr__(self) -> str:
        return (
            f"<DocumentChunk(id={self.id}, doc_id={self.document_id}, "
            f"index={self.chunk_index})>"
        )
