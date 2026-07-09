"""Casbin RBAC unit tests.

Tests for the Casbin enforcer, policy checking, and default policies.
"""

import pytest

import casbin

from app.core.security.rbac import check_permission


@pytest.fixture
def enforcer() -> casbin.Enforcer:
    """Create a Casbin enforcer with the project model.conf.

    Uses the built-in file-backed adapter (no database required)
    so that the tests can run without a live PostgreSQL instance.

    Returns:
        Casbin Enforcer with default policies loaded.
    """
    from pathlib import Path

    model_path = Path(__file__).resolve().parents[2] / "app" / "core" / "security" / "model.conf"
    enforcer = casbin.Enforcer(str(model_path))

    # ── Role hierarchy ────────────────────────────────────────
    enforcer.add_role_for_user("manager", "user")
    enforcer.add_role_for_user("admin", "manager")

    # ── admin policies (wildcard) ─────────────────────────────
    enforcer.add_policy("admin", "*", ".*")

    # ── manager policies ──────────────────────────────────────
    enforcer.add_policy("manager", "document", "read")
    enforcer.add_policy("manager", "document", "create")
    enforcer.add_policy("manager", "document", "update")
    enforcer.add_policy("manager", "document", "delete")
    enforcer.add_policy("manager", "document", "upload")
    enforcer.add_policy("manager", "user", "read")

    # ── user policies ─────────────────────────────────────────
    enforcer.add_policy("user", "document", "read")
    enforcer.add_policy("user", "document", "upload")
    enforcer.add_policy("user", "search", "read")
    enforcer.add_policy("user", "search", "search")

    return enforcer


class TestAdminPermissions:
    """Test that admin role has full access."""

    def test_admin_can_read_document(self, enforcer: casbin.Enforcer) -> None:
        """Admin can read documents."""
        assert check_permission(enforcer, "admin", "document", "read") is True

    def test_admin_can_upload_document(self, enforcer: casbin.Enforcer) -> None:
        """Admin can upload documents."""
        assert check_permission(enforcer, "admin", "document", "upload") is True

    def test_admin_can_delete_document(self, enforcer: casbin.Enforcer) -> None:
        """Admin can delete documents."""
        assert check_permission(enforcer, "admin", "document", "delete") is True

    def test_admin_can_search(self, enforcer: casbin.Enforcer) -> None:
        """Admin can search."""
        assert check_permission(enforcer, "admin", "search", "search") is True

    def test_admin_can_manage_users(self, enforcer: casbin.Enforcer) -> None:
        """Admin can manage users."""
        assert check_permission(enforcer, "admin", "user", "create") is True
        assert check_permission(enforcer, "admin", "user", "delete") is True

    def test_admin_wildcard_matches_any_resource(
        self, enforcer: casbin.Enforcer,
    ) -> None:
        """Admin wildcard policy matches arbitrary resources."""
        assert check_permission(enforcer, "admin", "anything", "whatever") is True


class TestManagerPermissions:
    """Test that manager role has department-level access."""

    def test_manager_can_read_document(self, enforcer: casbin.Enforcer) -> None:
        """Manager can read documents."""
        assert check_permission(enforcer, "manager", "document", "read") is True

    def test_manager_can_upload_document(self, enforcer: casbin.Enforcer) -> None:
        """Manager can upload documents."""
        assert check_permission(enforcer, "manager", "document", "upload") is True

    def test_manager_can_update_document(self, enforcer: casbin.Enforcer) -> None:
        """Manager can update documents."""
        assert check_permission(enforcer, "manager", "document", "update") is True

    def test_manager_can_delete_document(self, enforcer: casbin.Enforcer) -> None:
        """Manager can delete documents."""
        assert check_permission(enforcer, "manager", "document", "delete") is True

    def test_manager_can_read_users(self, enforcer: casbin.Enforcer) -> None:
        """Manager can read user list."""
        assert check_permission(enforcer, "manager", "user", "read") is True

    def test_manager_cannot_create_user(self, enforcer: casbin.Enforcer) -> None:
        """Manager cannot create users."""
        assert check_permission(enforcer, "manager", "user", "create") is False

    def test_manager_cannot_delete_user(self, enforcer: casbin.Enforcer) -> None:
        """Manager cannot delete users."""
        assert check_permission(enforcer, "manager", "user", "delete") is False

    def test_manager_inherits_user_permissions(
        self, enforcer: casbin.Enforcer,
    ) -> None:
        """Manager inherits user-level permissions."""
        assert check_permission(enforcer, "manager", "search", "read") is True
        assert check_permission(enforcer, "manager", "search", "search") is True


class TestUserPermissions:
    """Test that user role has limited access."""

    def test_user_can_read_document(self, enforcer: casbin.Enforcer) -> None:
        """User can read documents."""
        assert check_permission(enforcer, "user", "document", "read") is True

    def test_user_can_upload_document(self, enforcer: casbin.Enforcer) -> None:
        """User can upload documents."""
        assert check_permission(enforcer, "user", "document", "upload") is True

    def test_user_can_search(self, enforcer: casbin.Enforcer) -> None:
        """User can perform searches."""
        assert check_permission(enforcer, "user", "search", "search") is True

    def test_user_can_read_search(self, enforcer: casbin.Enforcer) -> None:
        """User can read search results."""
        assert check_permission(enforcer, "user", "search", "read") is True

    def test_user_cannot_delete_document(self, enforcer: casbin.Enforcer) -> None:
        """User cannot delete documents."""
        assert check_permission(enforcer, "user", "document", "delete") is False

    def test_user_cannot_update_document(self, enforcer: casbin.Enforcer) -> None:
        """User cannot update documents."""
        assert check_permission(enforcer, "user", "document", "update") is False

    def test_user_cannot_manage_users(self, enforcer: casbin.Enforcer) -> None:
        """User cannot manage users."""
        assert check_permission(enforcer, "user", "user", "read") is False
        assert check_permission(enforcer, "user", "user", "create") is False

    def test_user_cannot_access_unknown_resource(
        self, enforcer: casbin.Enforcer,
    ) -> None:
        """User cannot access resources not in policy."""
        assert check_permission(enforcer, "user", "admin_panel", "read") is False


class TestPolicyHotReload:
    """Test that policies can be updated at runtime."""

    def test_add_policy_grants_access(self, enforcer: casbin.Enforcer) -> None:
        """Adding a policy immediately grants access."""
        # user cannot delete by default
        assert check_permission(enforcer, "user", "document", "delete") is False

        # Grant delete permission
        enforcer.add_policy("user", "document", "delete")
        assert check_permission(enforcer, "user", "document", "delete") is True

        # Revoke it
        enforcer.remove_policy("user", "document", "delete")
        assert check_permission(enforcer, "user", "document", "delete") is False

    def test_add_role_grants_inherited_permissions(
        self, enforcer: casbin.Enforcer,
    ) -> None:
        """Adding a role assignment grants inherited permissions."""
        # Create a new role "editor" with document permissions
        enforcer.add_policy("editor", "document", "read")
        enforcer.add_policy("editor", "document", "update")

        # "viewer" has no permissions by default
        assert check_permission(enforcer, "viewer", "document", "read") is False

        # Assign editor role to viewer
        enforcer.add_role_for_user("viewer", "editor")
        assert check_permission(enforcer, "viewer", "document", "read") is True
        assert check_permission(enforcer, "viewer", "document", "update") is True

        # Cleanup
        enforcer.delete_role_for_user("viewer", "editor")
        enforcer.remove_policy("editor", "document", "read")
        enforcer.remove_policy("editor", "document", "update")
