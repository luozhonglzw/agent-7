"""User model unit tests.

Tests for User and UserSession model definitions and properties.
"""

import uuid

import pytest

from app.models.user import User, UserSession, USER_ROLES
from app.models.document import DocumentStatus


class TestUserModel:
    """Tests for User model."""

    def test_user_creation(self) -> None:
        """Test User model instantiation."""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_value",
            role="user",
        )

        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.role == "user"
        assert user.is_active is True
        assert user.is_superuser is False

    def test_user_roles_constant(self) -> None:
        """Test USER_ROLES constant contains expected values."""
        assert "admin" in USER_ROLES
        assert "manager" in USER_ROLES
        assert "user" in USER_ROLES
        assert len(USER_ROLES) == 3

    def test_user_dept_id_optional(self) -> None:
        """Test dept_id is optional and defaults to None."""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed",
            role="user",
        )
        assert user.dept_id is None

    def test_user_dept_id_set(self) -> None:
        """Test dept_id can be set."""
        dept = uuid.uuid4()
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed",
            role="user",
            dept_id=dept,
        )
        assert user.dept_id == dept

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
            role="user",
            is_superuser=True,
        )

        assert user.is_admin is True

    def test_user_is_not_admin_for_user_role(self) -> None:
        """Test is_admin property for user role."""
        user = User(
            email="user@example.com",
            username="user",
            hashed_password="hashed",
            role="user",
        )

        assert user.is_admin is False

    def test_is_manager_for_manager_role(self) -> None:
        """Test is_manager property for manager role."""
        user = User(
            email="mgr@example.com",
            username="manager",
            hashed_password="hashed",
            role="manager",
        )

        assert user.is_manager is True

    def test_is_manager_for_admin_role(self) -> None:
        """Test is_manager property returns True for admin (above manager)."""
        user = User(
            email="admin@example.com",
            username="admin",
            hashed_password="hashed",
            role="admin",
        )

        assert user.is_manager is True

    def test_is_manager_for_user_role(self) -> None:
        """Test is_manager property returns False for plain user."""
        user = User(
            email="user@example.com",
            username="user",
            hashed_password="hashed",
            role="user",
        )

        assert user.is_manager is False

    def test_is_manager_for_superuser(self) -> None:
        """Test is_manager property returns True for superuser."""
        user = User(
            email="super@example.com",
            username="super",
            hashed_password="hashed",
            role="user",
            is_superuser=True,
        )

        assert user.is_manager is True

    def test_user_repr(self) -> None:
        """Test User __repr__ method."""
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            email="test@example.com",
            username="testuser",
            hashed_password="hashed",
            role="manager",
        )

        repr_str = repr(user)
        assert str(user_id) in repr_str
        assert "test@example.com" in repr_str
        assert "manager" in repr_str


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
