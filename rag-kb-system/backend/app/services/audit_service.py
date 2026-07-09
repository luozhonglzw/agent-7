"""Audit logging service.

Records user actions for compliance and debugging.

Usage:
    from app.services.audit_service import AuditService

    service = AuditService(db_session)
    await service.log_action(user_id, "document.upload", "document", doc_id)
"""

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """Audit logging service.

    Records significant user actions in the audit trail.

    Attributes:
        db: Async database session.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize audit service.

        Args:
            db: Async database session.
        """
        self.db = db

    async def log_action(
        self,
        user_id: uuid.UUID | None,
        action: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        status: str = "success",
        error_message: str | None = None,
    ) -> AuditLog:
        """Record an audit log entry.

        Args:
            user_id: User who performed the action.
            action: Action identifier (e.g., "user.login").
            resource_type: Type of resource acted upon.
            resource_id: ID of the resource.
            details: Additional action details.
            ip_address: Client IP address.
            user_agent: Client user agent.
            status: Action outcome (success/failure).
            error_message: Error details if failed.

        Returns:
            Created AuditLog instance.
        """
        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            error_message=error_message,
        )
        self.db.add(log_entry)
        await self.db.flush()

        logger.debug(
            "Audit log: %s by %s on %s/%s [%s]",
            action, user_id, resource_type, resource_id, status,
        )
        return log_entry

    async def log_login(
        self,
        user_id: uuid.UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
        success: bool = True,
        error: str | None = None,
    ) -> AuditLog:
        """Record a login attempt.

        Args:
            user_id: User UUID.
            ip_address: Client IP.
            user_agent: Client user agent.
            success: Whether login succeeded.
            error: Error message if failed.

        Returns:
            Created AuditLog instance.
        """
        return await self.log_action(
            user_id=user_id,
            action="user.login",
            resource_type="user",
            resource_id=str(user_id),
            ip_address=ip_address,
            user_agent=user_agent,
            status="success" if success else "failure",
            error_message=error,
        )

    async def log_document_action(
        self,
        user_id: uuid.UUID,
        action: str,
        document_id: uuid.UUID,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        """Record a document action.

        Args:
            user_id: User UUID.
            action: Action (document.upload, document.delete, etc.).
            document_id: Document UUID.
            details: Additional details.
            ip_address: Client IP.

        Returns:
            Created AuditLog instance.
        """
        return await self.log_action(
            user_id=user_id,
            action=action,
            resource_type="document",
            resource_id=str(document_id),
            details=details,
            ip_address=ip_address,
        )
