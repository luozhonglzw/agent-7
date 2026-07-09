"""Base SQLAlchemy model with common fields and utilities.

Provides a declarative base and abstract base model with
UUID primary key, timestamps, and soft delete support.

Usage:
    from app.models.base import BaseModel

    class MyModel(BaseModel):
        __tablename__ = "my_models"
        name: Mapped[str] = mapped_column(String(100))
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models.

    Provides common configuration for all ORM models.
    """

    pass


class BaseModel(Base):
    """Abstract base model with common fields.

    All domain models should inherit from this class to get:
    - UUID primary key
    - created_at timestamp (auto-set on insert)
    - updated_at timestamp (auto-set on insert/update)
    - Soft delete support via is_deleted flag

    Attributes:
        id: UUID primary key.
        created_at: Timestamp when record was created.
        updated_at: Timestamp when record was last updated.
        is_deleted: Soft delete flag.
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="UUID primary key",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Record creation timestamp",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Last update timestamp",
    )
    is_deleted: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        index=True,
        comment="Soft delete flag",
    )

    def soft_delete(self) -> None:
        """Mark record as deleted without removing from database."""
        self.is_deleted = True

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            Human-readable model representation.
        """
        return f"<{self.__class__.__name__}(id={self.id})>"
