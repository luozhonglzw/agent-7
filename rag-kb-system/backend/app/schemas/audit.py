"""Audit log Pydantic schemas.

Defines response models for audit log endpoints.

Schemas:
    AuditLogResponse: Single audit log entry
    AuditLogListResponse: Paginated audit log list
    AuditLogFilter: Filter parameters for audit logs
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AuditLogResponse(BaseModel):
    """Audit log entry response.

    Attributes:
        id: Log entry UUID.
        user_id: User who performed the action.
        action: Action identifier.
        resource_type: Resource type acted upon.
        resource_id: Resource ID acted upon.
        details: Additional action details.
        ip_address: Client IP address.
        status: Action outcome.
        error_message: Error details if failed.
        created_at: Action timestamp.
    """

    id: uuid.UUID = Field(..., description="Log entry UUID")
    user_id: uuid.UUID | None = Field(default=None, description="User ID")
    action: str = Field(..., description="Action identifier")
    resource_type: str | None = Field(default=None, description="Resource type")
    resource_id: str | None = Field(default=None, description="Resource ID")
    details: dict | None = Field(default=None, description="Action details")
    ip_address: str | None = Field(default=None, description="Client IP")
    status: str = Field(..., description="Action status")
    error_message: str | None = Field(default=None, description="Error message")
    created_at: datetime = Field(..., description="Timestamp")

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    """Paginated audit log list.

    Attributes:
        items: List of audit log entries.
        total: Total entry count.
        page: Current page.
        page_size: Items per page.
    """

    items: list[AuditLogResponse] = Field(
        default_factory=list, description="Audit log entries"
    )
    total: int = Field(..., ge=0, description="Total count")
    page: int = Field(..., ge=1, description="Current page")
    page_size: int = Field(..., ge=1, description="Items per page")


class AuditLogFilter(BaseModel):
    """Audit log filter parameters.

    Attributes:
        user_id: Filter by user ID.
        action: Filter by action type.
        resource_type: Filter by resource type.
        status: Filter by status.
        start_date: Filter from date.
        end_date: Filter to date.
    """

    user_id: uuid.UUID | None = Field(default=None, description="Filter by user")
    action: str | None = Field(
        default=None, max_length=255, description="Filter by action"
    )
    resource_type: str | None = Field(
        default=None, max_length=100, description="Filter by resource type"
    )
    status: str | None = Field(
        default=None, pattern=r"^(success|failure)$", description="Filter by status"
    )
    start_date: datetime | None = Field(
        default=None, description="Start date filter"
    )
    end_date: datetime | None = Field(
        default=None, description="End date filter"
    )
