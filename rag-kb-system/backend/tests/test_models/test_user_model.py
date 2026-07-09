"""User model unit tests.

Tests for User and UserSession model definitions and properties.
"""

import uuid

import pytest

from app.models.user import User, UserSession
from app.models.document import DocumentStatus


class TestUserModel:
    """Tests for User model."""

    def test_user_creation(self) -> None:
        """Test User model instantiation."""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_value",
            role="viewer",
        )

        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.role == "viewer"
        assert user.is_active is True
        assert user.is_superuser is False

    def test_user_is_admin_for_admin_role(self) -> None:
        """Test is_admin property for admin role."""
        user = User(
            email="admin@example.com",
            username="admin",
            hashed_password="hashed",
            role="admin",
        )

        assert user.is_admin is True

    def test_user_is_admin_for_superuser(self) -> None:
        """Test is_admin property for superuser."""
        user = User(
            email="super@example.com",
            username="super",
            hashed_password="hashed",
            role="viewer",
            is_superuser=True,
        )

        assert user.is_admin is True

    def test_user_is_not_admin_for_viewer(self) -> None:
        """Test is_admin property for viewer role."""
        user = User(
            email="viewer@example.com",
            username="viewer",
            hashed_password="hashed",
            role="viewer",
        )

        assert user.is_admin is False

    def test_user_repr(self) -> None:
        """Test User __repr__ method."""
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            email="test@example.com",
            username="testuser",
            hashed_password="hashed",
            role="editor",
        )

        repr_str = repr(user)
        assert str(user_id) in repr_str
        assert "test@example.com" in repr_str
        assert "editor" in repr_str


class TestDocumentStatus:
    """Tests for DocumentStatus enum."""

    def test_status_values(self) -> None:
        """Test all document status values exist."""
        assert DocumentStatus.PENDING.value == "pending"
        assert DocumentStatus.PARSING.value == "parsing"
        assert DocumentStatus.CHUNKING.value == "chunking"
        assert DocumentStatus.EMBEDDING.value == "embedding"
        assert DocumentStatus.INDEXING.value == "indexing"
        assert DocumentStatus.READY.value == "ready"
        assert DocumentStatus.FAILED.value == "failed"

    def test_status_string_comparison(self) -> None:
        """Test status string comparison."""
        assert DocumentStatus.PENDING == "pending"
        assert DocumentStatus.READY == "ready"
