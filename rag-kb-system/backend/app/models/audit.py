"""AuditLog SQLAlchemy model.

Records all significant user actions for compliance and debugging.
Audit logs are append-only and should never be deleted.

Table:
    audit_logs: Immutable record of user actions.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditLog(Base):
    """Audit log entry.

    Records user actions with context for compliance tracking.
    This table uses a separate base (not BaseModel) because audit
    logs should NOT have soft delete or updated_at fields.

    Attributes:
        id: UUID primary key.
        user_id: User who performed the action (nullable for system actions).
        action: Action identifier (e.g., "document.upload", "user.login").
        resource_type: Type of resource acted upon.
        resource_id: ID of the resource acted upon.
        details: Additional action details (JSON).
        ip_address: Client IP address.
        user_agent: Client user agent string.
        status: Action outcome (success/failure).
        error_message: Error details if action failed.
        created_at: Timestamp of the action.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_user_action", "user_id", "action"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_created", "created_at"),
        {"comment": "Append-only audit trail"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="User who performed the action",
    )
    action: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Action identifier",
    )
    resource_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Resource type",
    )
    resource_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Resource ID",
    )
    details: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Action details",
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        comment="Client IP address",
    )
    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Client user agent",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="success",
        nullable=False,
        comment="Action status: success, failure",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if failed",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="Action timestamp",
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, action='{self.action}', "
            f"user_id={self.user_id}, status='{self.status}')>"
        )
