"""RBAC API integration tests.

Tests for permission-protected endpoints with different user roles.
"""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.core.security.jwt import create_access_token


@pytest.mark.asyncio
class TestDocumentUploadRBAC:
    """Test RBAC enforcement on document upload endpoint."""

    async def test_upload_requires_auth(self, client: AsyncClient) -> None:
        """Upload without token returns 401."""
        resp = await client.post("/api/v1/documents/upload")
        assert resp.status_code == 401

    async def test_upload_with_admin_token(
        self, client: AsyncClient, admin_user: "User"
    ) -> None:
        """Admin can access upload endpoint."""
        token = create_access_token(subject=admin_user.id, role="admin")
        resp = await client.post(
            "/api/v1/documents/upload",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Should not be 403 (may be 200 stub or 501 not implemented)
        assert resp.status_code != 403

    async def test_upload_with_user_token(
        self, client: AsyncClient, test_user: "User"
    ) -> None:
        """User with document:upload permission can access upload."""
        token = create_access_token(subject=test_user.id, role="user")
        resp = await client.post(
            "/api/v1/documents/upload",
            headers={"Authorization": f"Bearer {token}"},
        )
        # User role has document:upload permission, should not be 403
        assert resp.status_code != 403


@pytest.mark.asyncio
class TestAuditLogsRBAC:
    """Test RBAC enforcement on audit log endpoints."""

    async def test_audit_logs_requires_admin(
        self, client: AsyncClient, test_user: "User"
    ) -> None:
        """Non-admin user cannot access audit logs."""
        token = create_access_token(subject=test_user.id, role="user")
        resp = await client.get(
            "/api/v1/audit/logs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_audit_logs_requires_manager_denied(
        self, client: AsyncClient
    ) -> None:
        """Manager cannot access audit logs (admin only)."""
        user_id = uuid.uuid4()
        token = create_access_token(subject=user_id, role="manager")
        resp = await client.get(
            "/api/v1/audit/logs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_audit_logs_allows_admin(
        self, client: AsyncClient, admin_user: "User"
    ) -> None:
        """Admin can access audit logs."""
        token = create_access_token(subject=admin_user.id, role="admin")
        resp = await client.get(
            "/api/v1/audit/logs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
class TestRequirePermissionDependency:
    """Test the require_permission FastAPI dependency."""

    async def test_superuser_bypasses_permission_check(
        self, client: AsyncClient, admin_user: "User"
    ) -> None:
        """Superuser bypasses all permission checks."""
        token = create_access_token(subject=admin_user.id, role="admin")
        resp = await client.post(
            "/api/v1/documents/upload",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code != 403

    async def test_invalid_token_returns_401(self, client: AsyncClient) -> None:
        """Invalid token returns 401."""
        resp = await client.post(
            "/api/v1/documents/upload",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401

    async def test_expired_token_returns_401(self, client: AsyncClient) -> None:
        """Expired token returns 401."""
        from datetime import datetime, timedelta, timezone
        from jose import jwt

        payload = {
            "sub": str(uuid.uuid4()),
            "role": "admin",
            "type": "access",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        expired_token = jwt.encode(payload, "test_secret", algorithm="HS256")

        resp = await client.post(
            "/api/v1/documents/upload",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401
