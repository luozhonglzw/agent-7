"""FastAPI dependency injection functions.

Provides reusable dependencies for authentication, database sessions,
and permission checking (both role-based and Casbin policy-based).

Usage:
    from app.api.dependencies import get_current_user, require_role, require_permission

    @router.get("/admin/users")
    async def list_users(
        current_user: User = Depends(require_role("admin")),
        db: AsyncSession = Depends(get_db),
    ):
        ...

    @router.post("/documents/upload")
    async def upload(
        current_user: User = Depends(require_permission("document", "upload")),
    ):
        ...
"""

import logging
import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security.jwt import verify_token
from app.exceptions import (
    AuthenticationError,
    AuthorizationError,
    InvalidTokenError,
    UserNotFoundError,
)
from app.models.user import User

logger = logging.getLogger(__name__)

# ── Security Schemes ───────────────────────────────────────────
bearer_scheme = HTTPBearer(
    auto_error=False,
    description="JWT Bearer token",
)


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate current user from JWT token.

    Args:
        credentials: HTTP Bearer credentials from request header.
        db: Database session.

    Returns:
        Authenticated User object.

    Raises:
        HTTPException: If token is missing, invalid, or user not found.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 1000, "message": "Authentication required"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = verify_token(credentials.credentials, expected_type="access")
        user_id = payload.get("sub")
        if not user_id:
            raise InvalidTokenError(detail="Token missing subject claim")

    except (InvalidTokenError, Exception) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 1002, "message": str(e)},
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user from database
    try:
        result = await db.execute(
            select(User).where(
                User.id == uuid.UUID(user_id),
                User.is_deleted == False,  # noqa: E712
                User.is_active == True,  # noqa: E712
            )
        )
        user = result.scalar_one_or_none()

        if user is None:
            raise UserNotFoundError(user_id=user_id)

        return user

    except Exception as e:
        if isinstance(e, UserNotFoundError):
            raise
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 1000, "message": "Authentication failed"},
        )


def require_role(*roles: str):
    """Dependency factory for role-based access control.

    Args:
        *roles: Allowed roles (e.g., "admin", "manager").

    Returns:
        Dependency function that checks user role.

    Example:
        @router.get("/admin")
        async def admin_only(user = Depends(require_role("admin"))):
            ...
    """

    async def role_checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        """Check if current user has required role.

        Args:
            current_user: Authenticated user from token.

        Returns:
            User if authorized.

        Raises:
            HTTPException: If user lacks required role.
        """
        if current_user.is_superuser:
            return current_user

        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": 2000,
                    "message": "Permission denied",
                    "data": {
                        "detail": f"Requires one of roles: {', '.join(roles)}",
                        "required_roles": list(roles),
                        "user_role": current_user.role,
                    },
                },
            )
        return current_user

    return role_checker


def require_permission(resource: str, action: str):
    """Dependency factory for Casbin policy-based access control.

    Checks the current user's role against the Casbin policy to
    determine whether the requested action on the given resource
    is allowed.  Superusers always pass.

    Policies are evaluated using the model defined in
    ``app/core/security/model.conf`` and stored in the
    ``casbin_rules`` PostgreSQL table.

    Args:
        resource: Resource identifier (e.g. ``"document"``, ``"search"``).
        action: Action identifier (e.g. ``"read"``, ``"upload"``).

    Returns:
        Dependency function that enforces the permission.

    Example:
        @router.post("/documents/upload")
        async def upload(
            user = Depends(require_permission("document", "upload")),
        ):
            ...
    """

    async def permission_checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        """Check if current user has the required permission.

        Args:
            current_user: Authenticated user from token.

        Returns:
            User if authorized.

        Raises:
            HTTPException 403: If policy denies the action.
        """
        # Superuser bypasses all permission checks.
        if current_user.is_superuser:
            return current_user

        from app.core.security.rbac import get_enforcer, check_permission

        enforcer = await get_enforcer()
        allowed = check_permission(enforcer, current_user.role, resource, action)

        if not allowed:
            logger.warning(
                "RBAC denied: user=%s role=%s resource=%s action=%s",
                current_user.id, current_user.role, resource, action,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": 2000,
                    "message": "Permission denied",
                    "data": {
                        "detail": (
                            f"Role '{current_user.role}' is not allowed to "
                            f"perform '{action}' on '{resource}'"
                        ),
                        "resource": resource,
                        "action": action,
                        "user_role": current_user.role,
                    },
                },
            )

        return current_user

    return permission_checker


async def get_optional_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Get current user if authenticated, None otherwise.

    Unlike get_current_user, this does not raise on missing token.

    Args:
        credentials: Optional HTTP Bearer credentials.
        db: Database session.

    Returns:
        User if authenticated, None if no token provided.
    """
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials, db)
    except Exception:
        return None


def get_client_ip(request: Request) -> str | None:
    """Extract client IP from request.

    Checks X-Forwarded-For header first (for proxied requests),
    then falls back to request.client.host.

    Args:
        request: FastAPI request object.

    Returns:
        Client IP address string or None.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None
