"""User and UserSession SQLAlchemy models.

Defines the user account and session management tables
with proper relationships and constraints.

Tables:
    users: User accounts with authentication and role information.
    user_sessions: Active user sessions for token management.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

# Valid role values for the User model.
USER_ROLES = ("admin", "manager", "user")


class User(BaseModel):
    """User account model.

    Stores user authentication data, profile information,
    and role assignments for RBAC.

    Attributes:
        email: Unique email address (used for login).
        username: Unique display name.
        hashed_password: Bcrypt-hashed password.
        full_name: Optional full display name.
        role: User role for RBAC (admin/manager/user).
        dept_id: Department UUID for department-scoped permissions.
        is_active: Whether the account is active.
        is_superuser: Whether the user has superuser privileges.
        avatar_url: Optional avatar image URL.
        last_login_at: Timestamp of last successful login.
        sessions: Related user sessions.
    """

    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
        Index("ix_users_dept", "dept_id"),
        {"comment": "User accounts"},
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique email address",
    )
    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique username",
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Bcrypt hashed password",
    )
    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Full display name",
    )
    role: Mapped[str] = mapped_column(
        String(50),
        default="user",
        nullable=False,
        comment="User role: admin, manager, user",
    )
    dept_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Department UUID for dept-scoped permissions",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether account is active",
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Superuser flag",
    )
    avatar_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Avatar image URL",
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last successful login timestamp",
    )

    # Relationships
    sessions: Mapped[list["UserSession"]] = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role.

        Returns:
            True if user is admin or superuser.
        """
        return self.role == "admin" or self.is_superuser

    @property
    def is_manager(self) -> bool:
        """Check if user has manager role or above.

        Returns:
            True if user is manager, admin, or superuser.
        """
        return self.role in ("admin", "manager") or self.is_superuser

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"


class UserSession(BaseModel):
    """User session model for token management.

    Tracks active sessions for token refresh and revocation.

    Attributes:
        user_id: Foreign key to users table.
        refresh_token: Unique refresh token identifier.
        user_agent: Client user agent string.
        ip_address: Client IP address.
        expires_at: Session expiration timestamp.
        is_revoked: Whether the session has been revoked.
        user: Related user.
    """

    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("ix_user_sessions_token", "refresh_token"),
        Index("ix_user_sessions_user_active", "user_id", "is_revoked"),
        {"comment": "User sessions for token management"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User ID foreign key",
    )
    refresh_token: Mapped[str] = mapped_column(
        String(512),
        unique=True,
        nullable=False,
        comment="Refresh token identifier",
    )
    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Client user agent",
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        comment="Client IP address (supports IPv6)",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Session expiration timestamp",
    )
    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether session is revoked",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="sessions",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<UserSession(id={self.id}, user_id={self.user_id}, revoked={self.is_revoked})>"
