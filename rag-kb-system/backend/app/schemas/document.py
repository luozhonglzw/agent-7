"""Document management Pydantic schemas.

Defines request/response models for document endpoints.

Schemas:
    DocumentCreate: Document upload metadata
    DocumentResponse: Document details response
    DocumentListResponse: Paginated document list
    DocumentStatusResponse: Processing status
    DocumentUpdateRequest: Document metadata update
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    """Document creation request (metadata alongside file upload).

    Attributes:
        title: Optional document title (defaults to filename).
        is_public: Whether document is publicly accessible.
        metadata_extra: Additional metadata.
    """

    title: str | None = Field(
        default=None, max_length=500, description="Document title"
    )
    is_public: bool = Field(default=False, description="Public access flag")
    metadata_extra: dict | None = Field(default=None, description="Extra metadata")


class DocumentResponse(BaseModel):
    """Document details response.

    Attributes:
        id: Document UUID.
        title: Document title.
        filename: Original filename.
        file_size: File size in bytes.
        file_type: File extension.
        status: Processing status.
        error_message: Error details if failed.
        page_count: Number of pages.
        chunk_count: Number of text chunks.
        token_count: Total token count.
        is_public: Public access flag.
        created_at: Upload timestamp.
        processed_at: Processing completion timestamp.
    """

    id: uuid.UUID = Field(..., description="Document UUID")
    title: str = Field(..., description="Document title")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    file_type: str = Field(..., description="File extension")
    status: str = Field(..., description="Processing status")
    error_message: str | None = Field(default=None, description="Error message")
    page_count: int | None = Field(default=None, description="Page count")
    chunk_count: int | None = Field(default=None, description="Chunk count")
    token_count: int | None = Field(default=None, description="Token count")
    is_public: bool = Field(default=False, description="Public access")
    created_at: datetime = Field(..., description="Upload timestamp")
    processed_at: datetime | None = Field(default=None, description="Processed at")

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """Paginated document list response.

    Attributes:
        items: List of documents.
        total: Total document count.
        page: Current page.
        page_size: Items per page.
    """

    items: list[DocumentResponse] = Field(
        default_factory=list, description="Document list"
    )
    total: int = Field(..., ge=0, description="Total count")
    page: int = Field(..., ge=1, description="Current page")
    page_size: int = Field(..., ge=1, description="Items per page")


class DocumentStatusResponse(BaseModel):
    """Document processing status response.

    Attributes:
        document_id: Document UUID.
        status: Current processing status.
        progress: Processing progress (0-100).
        error_message: Error details if failed.
    """

    document_id: uuid.UUID = Field(..., description="Document UUID")
    status: str = Field(..., description="Processing status")
    progress: int = Field(default=0, ge=0, le=100, description="Progress %")
    error_message: str | None = Field(default=None, description="Error message")


class DocumentUpdateRequest(BaseModel):
    """Document metadata update request.

    Attributes:
        title: New document title.
        is_public: New public access flag.
    """

    title: str | None = Field(
        default=None, max_length=500, description="New title"
    )
    is_public: bool | None = Field(
        default=None, description="New public access flag"
    )
