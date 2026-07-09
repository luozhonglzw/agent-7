"""JWT token creation, validation, and decoding.

Provides secure JWT token management with access and refresh tokens.
Tokens are signed with HS256 and include standard claims.

Usage:
    from app.core.security.jwt import create_access_token, decode_token

    token = create_access_token(subject="user-uuid", role="admin")
    payload = decode_token(token)
"""

import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config import settings
from app.exceptions import InvalidTokenError, TokenExpiredError


def create_access_token(
    subject: str | uuid.UUID,
    role: str = "viewer",
    extra_claims: dict | None = None,
) -> str:
    """Create a JWT access token.

    Args:
        subject: Token subject (typically user UUID).
        role: User role for quick RBAC checks.
        extra_claims: Additional claims to include.

    Returns:
        Encoded JWT string.

    Example:
        >>> token = create_access_token(subject="user-123", role="admin")
        >>> len(token) > 0
        True
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.jwt.access_token_expire_minutes)

    payload = {
        "sub": str(subject),
        "role": role,
        "type": "access",
        "iat": now,
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.jwt.secret_key,
        algorithm=settings.jwt.algorithm,
    )


def create_refresh_token(
    subject: str | uuid.UUID,
    session_id: str | uuid.UUID | None = None,
) -> str:
    """Create a JWT refresh token.

    Args:
        subject: Token subject (typically user UUID).
        session_id: Associated session UUID.

    Returns:
        Encoded JWT refresh token string.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.jwt.refresh_token_expire_days)

    payload = {
        "sub": str(subject),
        "type": "refresh",
        "iat": now,
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }

    if session_id:
        payload["session_id"] = str(session_id)

    return jwt.encode(
        payload,
        settings.jwt.secret_key,
        algorithm=settings.jwt.algorithm,
    )


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token.

    Args:
        token: JWT token string.

    Returns:
        Decoded token payload dictionary.

    Raises:
        TokenExpiredError: If token has expired.
        InvalidTokenError: If token is invalid or malformed.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt.secret_key,
            algorithms=[settings.jwt.algorithm],
        )
        return payload

    except JWTError as e:
        error_msg = str(e).lower()
        if "expired" in error_msg:
            raise TokenExpiredError()
        raise InvalidTokenError(detail=str(e))


def verify_token(token: str, expected_type: str = "access") -> dict:
    """Verify token and check its type.

    Args:
        token: JWT token string.
        expected_type: Expected token type (access/refresh).

    Returns:
        Verified token payload.

    Raises:
        TokenExpiredError: If token has expired.
        InvalidTokenError: If token is invalid or wrong type.
    """
    payload = decode_token(token)

    token_type = payload.get("type")
    if token_type != expected_type:
        raise InvalidTokenError(
            detail=f"Expected {expected_type} token, got {token_type}"
        )

    return payload
