"""Admin operation Pydantic schemas.

Defines request/response models for admin endpoints.

Schemas:
    AdminUserResponse: User details for admin view
    AdminUserListResponse: Paginated user list
    UpdateUserRoleRequest: Role change request
    UpdateUserStatusRequest: Status change request
    SystemStatsResponse: System statistics
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AdminUserResponse(BaseModel):
    """User details for admin view.

    Attributes:
        id: User UUID.
        email: Email address.
        username: Username.
        full_name: Display name.
        role: User role.
        is_active: Account status.
        is_superuser: Superuser flag.
        created_at: Account creation timestamp.
        last_login_at: Last login timestamp.
        document_count: Number of documents owned.
    """

    id: uuid.UUID = Field(..., description="User UUID")
    email: str = Field(..., description="Email address")
    username: str = Field(..., description="Username")
    full_name: str | None = Field(default=None, description="Full name")
    role: str = Field(..., description="User role")
    is_active: bool = Field(..., description="Account active")
    is_superuser: bool = Field(default=False, description="Superuser")
    created_at: datetime = Field(..., description="Created at")
    last_login_at: datetime | None = Field(default=None, description="Last login")
    document_count: int = Field(default=0, description="Document count")

    model_config = {"from_attributes": True}


class AdminUserListResponse(BaseModel):
    """Paginated user list for admin.

    Attributes:
        items: List of users.
        total: Total user count.
        page: Current page.
        page_size: Items per page.
    """

    items: list[AdminUserResponse] = Field(
        default_factory=list, description="User list"
    )
    total: int = Field(..., ge=0, description="Total count")
    page: int = Field(..., ge=1, description="Current page")
    page_size: int = Field(..., ge=1, description="Items per page")


class UpdateUserRoleRequest(BaseModel):
    """Role change request.

    Attributes:
        role: New role to assign (admin/editor/viewer).
    """

    role: str = Field(
        ..., pattern=r"^(admin|editor|viewer)$",
        description="New role",
    )


class UpdateUserStatusRequest(BaseModel):
    """Status change request.

    Attributes:
        is_active: New account status.
    """

    is_active: bool = Field(..., description="Account active status")


class SystemStatsResponse(BaseModel):
    """System statistics.

    Attributes:
        total_users: Total user count.
        active_users: Active user count.
        total_documents: Total document count.
        ready_documents: Processed document count.
        total_chunks: Total text chunks.
        total_embeddings: Total embedding vectors.
        storage_used_mb: Total storage used in MB.
    """

    total_users: int = Field(default=0, description="Total users")
    active_users: int = Field(default=0, description="Active users")
    total_documents: int = Field(default=0, description="Total documents")
    ready_documents: int = Field(default=0, description="Ready documents")
    total_chunks: int = Field(default=0, description="Total chunks")
    total_embeddings: int = Field(default=0, description="Total embeddings")
    storage_used_mb: float = Field(default=0.0, description="Storage used (MB)")
