"""Audit logging decorator for FastAPI endpoints.

Provides the ``@audit_log`` decorator that transparently records
who did what, when, and whether it succeeded.  Log entries are
written asynchronously via ``BackgroundTasks`` so they never block
the HTTP response.

Usage::

    from fastapi import BackgroundTasks, Request
    from app.core.security.audit import audit_log

    @router.post("/documents/upload")
    @audit_log(action="upload", resource_type="document")
    async def upload_document(
        request: Request,
        background_tasks: BackgroundTasks,
        current_user: User = Depends(get_current_user),
    ):
        ...
"""

import logging
import time
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from functools import wraps
from typing import Any

from fastapi import BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.audit import AuditLog

logger = logging.getLogger(__name__)


def _extract_request_context(
    kwargs: dict[str, Any],
) -> tuple[str | None, uuid.UUID | None, str | None, str | None]:
    """Pull request metadata out of the endpoint kwargs.

    Looks for a ``Request`` object and an authenticated user (any
    object with an ``id`` attribute).

    Args:
        kwargs: Keyword arguments passed to the endpoint.

    Returns:
        Tuple of (request_id, user_id, ip_address, user_agent).
    """
    request_id: str | None = None
    user_id: uuid.UUID | None = None
    ip_address: str | None = None
    user_agent: str | None = None

    # ── Request context ──────────────────────────────────────
    request: Request | None = kwargs.get("request")
    if request is not None:
        request_id = getattr(request.state, "request_id", None)
        user_agent = request.headers.get("User-Agent")
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip_address = forwarded.split(",")[0].strip()
        elif request.client:
            ip_address = request.client.host

    # ── Authenticated user ───────────────────────────────────
    for value in kwargs.values():
        if hasattr(value, "id") and hasattr(value, "email"):
            user_id = value.id
            break

    return request_id, user_id, ip_address, user_agent


async def _write_audit_log(
    user_id: uuid.UUID | None,
    action: str,
    resource_type: str | None,
    resource_id: str | None,
    request_id: str | None,
    status: str,
    latency_ms: float,
    ip_address: str | None,
    user_agent: str | None,
    error_message: str | None = None,
) -> None:
    """Insert a single audit log row (runs inside BackgroundTasks).

    Opens its own database session so it is independent of the
    request lifecycle.  Errors are logged but **never** propagate
    to the caller.

    Args:
        user_id: User who triggered the action.
        action: Action name (e.g. ``"upload"``).
        resource_type: Resource type (e.g. ``"document"``).
        resource_id: Resource identifier.
        request_id: Correlation ID from the middleware.
        status: ``"success"`` or ``"failure"``.
        latency_ms: Wall-clock time in milliseconds.
        ip_address: Client IP.
        user_agent: Client User-Agent.
        error_message: Error detail when *status* is ``"failure"``.
    """
    try:
        async with AsyncSessionLocal() as session:
            log_entry = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details={"request_id": request_id} if request_id else None,
                ip_address=ip_address,
                user_agent=user_agent,
                status=status,
                error_message=error_message,
                created_at=datetime.now(timezone.utc),
            )
            session.add(log_entry)
            await session.commit()
            logger.debug(
                "Audit logged: action=%s user=%s status=%s latency=%.1fms",
                action, user_id, status, latency_ms,
            )
    except Exception:
        # Audit failure must never break the main request.
        logger.exception("Failed to write audit log (action=%s)", action)


def audit_log(
    action: str,
    resource_type: str | None = None,
) -> Callable:
    """Decorator that records an audit trail entry for an endpoint.

    The decorated function **must** accept ``request: Request`` and
    ``background_tasks: BackgroundTasks`` as parameters (injected by
    FastAPI).  If either is missing the audit step is silently skipped.

    Args:
        action: Short action identifier (e.g. ``"register"``, ``"upload"``).
        resource_type: Optional resource type (e.g. ``"document"``).

    Returns:
        Decorated endpoint function.

    Example::

        @router.post("/auth/login")
        @audit_log(action="login", resource_type="user")
        async def login(request: Request, background_tasks: BackgroundTasks, ...):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # FastAPI injects dependencies by name into kwargs.
            bg: BackgroundTasks | None = kwargs.get("background_tasks")
            req: Request | None = kwargs.get("request")

            # If the endpoint doesn't accept these params, just run
            # the function without audit logging.
            if bg is None or req is None:
                return await func(*args, **kwargs)

            request_id, user_id, ip_address, user_agent = (
                _extract_request_context(kwargs)
            )

            start = time.perf_counter()
            status_str = "success"
            error_message: str | None = None

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as exc:
                status_str = "failure"
                error_message = str(exc)[:500]
                raise
            finally:
                latency_ms = (time.perf_counter() - start) * 1000

                # Resolve resource_id from URL path parameters.
                path_params = req.path_params if req else {}
                resource_id: str | None = (
                    str(next(iter(path_params.values()), None))
                    if path_params
                    else None
                )

                bg.add_task(
                    _write_audit_log,
                    user_id=user_id,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    request_id=request_id,
                    status=status_str,
                    latency_ms=round(latency_ms, 2),
                    ip_address=ip_address,
                    user_agent=user_agent,
                    error_message=error_message,
                )

        return wrapper

    return decorator
