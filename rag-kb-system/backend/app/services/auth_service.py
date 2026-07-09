"""Authentication service.

Handles user registration, login, token management, and profile operations.

Usage:
    from app.services.auth_service import AuthService

    service = AuthService(db_session)
    user = await service.register(email, username, password)
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security.password import get_password_hash, verify_password
from app.core.security.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.exceptions import (
    AuthenticationError,
    CredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.models.user import User, UserSession

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service.

    Manages user accounts, authentication, and session lifecycle.

    Attributes:
        db: Async database session.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize auth service.

        Args:
            db: Async database session.
        """
        self.db = db

    async def register(
        self,
        email: str,
        username: str,
        password: str,
        full_name: str | None = None,
    ) -> User:
        """Register a new user.

        Args:
            email: User email address.
            username: Unique username.
            password: Plain text password (will be hashed).
            full_name: Optional display name.

        Returns:
            Created User instance.

        Raises:
            UserAlreadyExistsError: If email or username exists.
        """
        # Check for existing email
        existing = await self.db.execute(
            select(User).where(User.email == email)
        )
        if existing.scalar_one_or_none():
            raise UserAlreadyExistsError(email=email)

        # Check for existing username
        existing = await self.db.execute(
            select(User).where(User.username == username)
        )
        if existing.scalar_one_or_none():
            raise UserAlreadyExistsError(email=username)

        # Create user
        user = User(
            email=email,
            username=username,
            hashed_password=get_password_hash(password),
            full_name=full_name,
            role="viewer",
            is_active=True,
        )
        self.db.add(user)
        await self.db.flush()

        logger.info("User registered: %s (%s)", user.id, email)
        return user

    async def login(
        self,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """Authenticate user and return tokens.

        Args:
            email: User email.
            password: Plain text password.
            ip_address: Client IP address.
            user_agent: Client user agent.

        Returns:
            Dictionary with access_token, refresh_token, and user.

        Raises:
            CredentialsError: If credentials are invalid.
        """
        # Find user by email
        result = await self.db.execute(
            select(User).where(
                User.email == email,
                User.is_deleted == False,  # noqa: E712
                User.is_active == True,  # noqa: E712
            )
        )
        user = result.scalar_one_or_none()

        if user is None:
            raise CredentialsError()

        # Verify password
        if not verify_password(password, user.hashed_password):
            raise CredentialsError()

        # Create tokens
        access_token = create_access_token(
            subject=user.id, role=user.role
        )
        refresh_token = create_refresh_token(subject=user.id)

        # Create session
        session = UserSession(
            user_id=user.id,
            refresh_token=refresh_token,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=datetime.now(timezone.utc).replace(
                day=datetime.now(timezone.utc).day
                + settings.jwt.refresh_token_expire_days
            ),
        )
        self.db.add(session)

        # Update last login
        user.last_login_at = datetime.now(timezone.utc)
        await self.db.flush()

        logger.info("User logged in: %s (%s)", user.id, email)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.jwt.access_token_expire_minutes * 60,
            "user": user,
        }

    async def refresh_access_token(self, refresh_token: str) -> dict:
        """Refresh access token using refresh token.

        Args:
            refresh_token: JWT refresh token.

        Returns:
            Dictionary with new access_token.

        Raises:
            AuthenticationError: If token is invalid or session revoked.
        """
        try:
            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise CredentialsError()
        except Exception:
            raise CredentialsError()

        user_id = payload.get("sub")
        if not user_id:
            raise CredentialsError()

        # Verify session exists and is not revoked
        result = await self.db.execute(
            select(UserSession).where(
                UserSession.refresh_token == refresh_token,
                UserSession.is_revoked == False,  # noqa: E712
            )
        )
        session = result.scalar_one_or_none()
        if session is None:
            raise AuthenticationError(detail="Session revoked or not found")

        # Get user
        result = await self.db.execute(
            select(User).where(
                User.id == uuid.UUID(user_id),
                User.is_active == True,  # noqa: E712
            )
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise UserNotFoundError(user_id=user_id)

        # Create new access token
        access_token = create_access_token(
            subject=user.id, role=user.role
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.jwt.access_token_expire_minutes * 60,
        }

    async def get_user_by_id(self, user_id: uuid.UUID) -> User:
        """Get user by UUID.

        Args:
            user_id: User UUID.

        Returns:
            User instance.

        Raises:
            UserNotFoundError: If user not found.
        """
        result = await self.db.execute(
            select(User).where(
                User.id == user_id,
                User.is_deleted == False,  # noqa: E712
            )
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise UserNotFoundError(user_id=str(user_id))
        return user
