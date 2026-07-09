"""Document API endpoint tests.

Tests for document upload, listing, retrieval, and deletion.
"""

import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.core.security.jwt import create_access_token


@pytest.mark.asyncio
class TestUploadEndpoint:
    """Tests for POST /api/v1/documents/upload."""

    async def test_upload_requires_auth(self, client: AsyncClient) -> None:
        """Upload without token returns 401."""
        resp = await client.post("/api/v1/documents/upload")
        assert resp.status_code in (401, 403)

    @patch("app.services.document_service.process_document")
    async def test_upload_success(
        self, mock_task: object, client: AsyncClient, test_user: "User"
    ) -> None:
        """Test successful file upload."""
        mock_task.apply_async.return_value.type = "task-id"

        token = create_access_token(subject=test_user.id, role="user")
        resp = await client.post(
            "/api/v1/documents/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.txt", b"Hello World", "text/plain")},
            data={"title": "Test Upload"},
        )

        assert resp.status_code == 201
        data = resp.json()["data"]
        assert "doc_id" in data
        assert data["status"] == "pending"
        assert data["filename"] == "test.txt"

    async def test_upload_unsupported_type(
        self, client: AsyncClient, test_user: "User"
    ) -> None:
        """Test upload with unsupported file type."""
        token = create_access_token(subject=test_user.id, role="user")
        resp = await client.post(
            "/api/v1/documents/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.xyz", b"content", "application/octet-stream")},
        )

        assert resp.status_code == 422

    async def test_upload_without_file(
        self, client: AsyncClient, test_user: "User"
    ) -> None:
        """Test upload without file returns 422."""
        token = create_access_token(subject=test_user.id, role="user")
        resp = await client.post(
            "/api/v1/documents/upload",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 422


@pytest.mark.asyncio
class TestListEndpoint:
    """Tests for GET /api/v1/documents."""

    async def test_list_requires_auth(self, client: AsyncClient) -> None:
        """List without token returns 401."""
        resp = await client.get("/api/v1/documents")
        assert resp.status_code == 401

    async def test_list_empty(
        self, client: AsyncClient, test_user: "User"
    ) -> None:
        """Test listing when no documents exist."""
        token = create_access_token(subject=test_user.id, role="user")
        resp = await client.get(
            "/api/v1/documents",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 0
        assert data["items"] == []


@pytest.mark.asyncio
class TestGetEndpoint:
    """Tests for GET /api/v1/documents/{id}."""

    async def test_get_nonexistent(
        self, client: AsyncClient, test_user: "User"
    ) -> None:
        """Test getting nonexistent document returns 404."""
        token = create_access_token(subject=test_user.id, role="user")
        resp = await client.get(
            f"/api/v1/documents/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 404


@pytest.mark.asyncio
class TestDeleteEndpoint:
    """Tests for DELETE /api/v1/documents/{id}."""

    async def test_delete_nonexistent(
        self, client: AsyncClient, test_user: "User"
    ) -> None:
        """Test deleting nonexistent document returns 404."""
        token = create_access_token(subject=test_user.id, role="user")
        resp = await client.delete(
            f"/api/v1/documents/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 404
