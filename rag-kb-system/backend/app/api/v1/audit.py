"""Audit log API endpoints.

Provides read-only access to audit logs for compliance
and debugging purposes.

Endpoints:
    GET /audit/logs: List audit logs (admin only)
    GET /audit/logs/{id}: Get specific audit log entry (admin only)
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_role
from app.database import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.common import PaginatedResponse, SuccessResponse

router = APIRouter(prefix="/audit", tags=["Audit Logs"])


@router.get("/logs", response_model=SuccessResponse[PaginatedResponse])
async def list_audit_logs(
    current_user: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    user_id: str | None = Query(default=None, description="Filter by user UUID"),
    action: str | None = Query(default=None, description="Filter by action"),
    resource_type: str | None = Query(default=None, description="Filter by resource type"),
    status: str | None = Query(default=None, description="Filter by status"),
) -> SuccessResponse[PaginatedResponse]:
    """List audit log entries (admin only).

    Returns paginated audit log entries with optional filtering
    by user, action, resource type, and status.

    Args:
        current_user: Authenticated admin user.
        db: Database session.
        page: Page number (1-based).
        page_size: Items per page.
        user_id: Optional user UUID filter.
        action: Optional action filter.
        resource_type: Optional resource type filter.
        status: Optional status filter (success/failure).

    Returns:
        Paginated list of audit log entries.
    """
    # Build query with filters
    query = select(AuditLog)
    count_query = select(func.count(AuditLog.id))

    if user_id:
        query = query.where(AuditLog.user_id == uuid.UUID(user_id))
        count_query = count_query.where(AuditLog.user_id == uuid.UUID(user_id))
    if action:
        query = query.where(AuditLog.action == action)
        count_query = count_query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
        count_query = count_query.where(AuditLog.resource_type == resource_type)
    if status:
        query = query.where(AuditLog.status == status)
        count_query = count_query.where(AuditLog.status == status)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results (newest first)
    offset = (page - 1) * page_size
    query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()

    # Build response
    total_pages = (total + page_size - 1) // page_size
    items = [
        {
            "id": str(log.id),
            "user_id": str(log.user_id) if log.user_id else None,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "status": log.status,
            "error_message": log.error_message,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]

    paginated = PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )
    return SuccessResponse(data=paginated)


@router.get("/logs/{log_id}", response_model=SuccessResponse)
async def get_audit_log(
    log_id: str,
    current_user: Annotated[User, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse:
    """Get a specific audit log entry (admin only).

    Returns full audit log details including request context.

    Args:
        log_id: Audit log UUID.
        current_user: Authenticated admin user.
        db: Database session.

    Returns:
        Audit log entry details.
    """
    result = await db.execute(
        select(AuditLog).where(AuditLog.id == uuid.UUID(log_id))
    )
    log = result.scalar_one_or_none()

    if log is None:
        from app.exceptions import NotFoundError
        raise NotFoundError(resource="AuditLog", identifier=log_id)

    return SuccessResponse(
        data={
            "id": str(log.id),
            "user_id": str(log.user_id) if log.user_id else None,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "status": log.status,
            "error_message": log.error_message,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
    )
