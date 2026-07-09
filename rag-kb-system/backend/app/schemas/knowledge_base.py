"""Knowledge Base Pydantic schemas.

Defines request/response models for knowledge base endpoints.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class KBCreate(BaseModel):
    """Knowledge base creation request.

    Attributes:
        name: Knowledge base name.
        description: Optional description.
        visibility: Access level (public/private/dept).
    """

    name: str = Field(
        ..., min_length=1, max_length=255, description="Knowledge base name"
    )
    description: str | None = Field(
        default=None, max_length=2000, description="Description"
    )
    visibility: str = Field(
        default="private",
        pattern="^(public|private|dept)$",
        description="Visibility: public, private, or dept",
    )


class KBUpdate(BaseModel):
    """Knowledge base update request.

    Attributes:
        name: New name (None to skip).
        description: New description (None to skip).
        visibility: New visibility (None to skip).
    """

    name: str | None = Field(
        default=None, min_length=1, max_length=255, description="New name"
    )
    description: str | None = Field(
        default=None, max_length=2000, description="New description"
    )
    visibility: str | None = Field(
        default=None,
        pattern="^(public|private|dept)$",
        description="New visibility",
    )


class KBResponse(BaseModel):
    """Knowledge base response.

    Attributes:
        id: KB UUID.
        name: KB name.
        description: KB description.
        visibility: Access level.
        owner_id: Owner user UUID.
        document_count: Number of documents in the KB.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: uuid.UUID = Field(..., description="KB UUID")
    name: str = Field(..., description="KB name")
    description: str | None = Field(default=None, description="Description")
    visibility: str = Field(..., description="Visibility level")
    owner_id: uuid.UUID = Field(..., description="Owner user UUID")
    document_count: int = Field(default=0, description="Document count")
    created_at: datetime = Field(..., description="Created at")
    updated_at: datetime = Field(..., description="Updated at")

    model_config = {"from_attributes": True}


class KBDocumentAdd(BaseModel):
    """Request to add documents to a knowledge base.

    Attributes:
        document_ids: List of document UUIDs to add.
    """

    document_ids: list[uuid.UUID] = Field(
        ..., min_length=1, max_length=100, description="Document UUIDs to add"
    )


class KBDocumentRemove(BaseModel):
    """Request to remove documents from a knowledge base.

    Attributes:
        document_ids: List of document UUIDs to remove.
    """

    document_ids: list[uuid.UUID] = Field(
        ..., min_length=1, max_length=100, description="Document UUIDs to remove"
    )
