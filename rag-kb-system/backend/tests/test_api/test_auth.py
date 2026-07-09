"""Auth API endpoint tests.

Tests for registration, login, token refresh, and profile endpoints.
"""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.core.security.jwt import create_access_token, create_refresh_token


@pytest.mark.asyncio
class TestRegisterEndpoint:
    """Tests for POST /api/v1/auth/register."""

    async def test_register_success(self, client: AsyncClient) -> None:
        """Test successful registration returns tokens."""
        payload = {
            "email": f"reg_{uuid.uuid4().hex[:8]}@example.com",
            "username": f"reg_{uuid.uuid4().hex[:8]}",
            "password": "ValidPass123",
            "full_name": "Test User",
        }

        resp = await client.post("/api/v1/auth/register", json=payload)

        assert resp.status_code == 201
        data = resp.json()
        assert data["code"] == 0
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"
        assert data["data"]["expires_in"] == 15 * 60

    async def test_register_weak_password(
        self, client: AsyncClient
    ) -> None:
        """Test registration with weak password returns 422."""
        payload = {
            "email": f"weak_{uuid.uuid4().hex[:8]}@example.com",
            "username": f"weak_{uuid.uuid4().hex[:8]}",
            "password": "weak",
        }

        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 422

    async def test_register_invalid_email(
        self, client: AsyncClient
    ) -> None:
        """Test registration with invalid email returns 422."""
        payload = {
            "email": "not-an-email",
            "username": f"inv_{uuid.uuid4().hex[:8]}",
            "password": "ValidPass123",
        }

        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 422

    async def test_register_duplicate_email(
        self, client: AsyncClient, test_user: "User"
    ) -> None:
        """Test registration with existing email returns 409."""
        payload = {
            "email": test_user.email,
            "username": f"dup_{uuid.uuid4().hex[:8]}",
            "password": "ValidPass123",
        }

        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 409


@pytest.mark.asyncio
class TestLoginEndpoint:
    """Tests for POST /api/v1/auth/login."""

    async def test_login_success(
        self, client: AsyncClient, test_user: "User"
    ) -> None:
        """Test successful login returns tokens."""
        payload = {
            "email": test_user.email,
            "password": "TestPass123!",
        }

        resp = await client.post("/api/v1/auth/login", json=payload)

        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]

    async def test_login_wrong_password(
        self, client: AsyncClient, test_user: "User"
    ) -> None:
        """Test login with wrong password returns 401."""
        payload = {
            "email": test_user.email,
            "password": "WrongPass123!",
        }

        resp = await client.post("/api/v1/auth/login", json=payload)
        assert resp.status_code == 401

    async def test_login_nonexistent_user(
        self, client: AsyncClient
    ) -> None:
        """Test login with nonexistent email returns 401."""
        payload = {
            "email": "nobody@example.com",
            "password": "AnyPass123!",
        }

        resp = await client.post("/api/v1/auth/login", json=payload)
        assert resp.status_code == 401


@pytest.mark.asyncio
class TestRefreshEndpoint:
    """Tests for POST /api/v1/auth/refresh."""

    async def test_refresh_success(
        self, client: AsyncClient, test_user: "User"
    ) -> None:
        """Test successful token refresh."""
        # Login first to get a refresh token
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "TestPass123!",
            },
        )
        refresh_token = login_resp.json()["data"]["refresh_token"]

        # Refresh
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert "access_token" in data["data"]

    async def test_refresh_invalid_token(
        self, client: AsyncClient
    ) -> None:
        """Test refresh with invalid token returns 401."""
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )
        assert resp.status_code == 401


@pytest.mark.asyncio
class TestProfileEndpoint:
    """Tests for GET/PUT /api/v1/auth/me."""

    async def test_get_profile_success(
        self, client: AsyncClient, test_user: "User"
    ) -> None:
        """Test getting current user profile."""
        # Login to get token
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "TestPass123!",
            },
        )
        token = login_resp.json()["data"]["access_token"]

        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["email"] == test_user.email
        assert data["username"] == test_user.username
        assert data["role"] == test_user.role

    async def test_get_profile_no_token(
        self, client: AsyncClient
    ) -> None:
        """Test getting profile without token returns 401."""
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    async def test_update_profile(
        self, client: AsyncClient, test_user: "User"
    ) -> None:
        """Test updating current user profile."""
        # Login to get token
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "TestPass123!",
            },
        )
        token = login_resp.json()["data"]["access_token"]

        resp = await client.put(
            "/api/v1/auth/me",
            json={
                "full_name": "Updated Name",
                "avatar_url": "https://example.com/new.png",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["full_name"] == "Updated Name"
        assert data["avatar_url"] == "https://example.com/new.png"

    async def test_change_password(
        self, client: AsyncClient, test_user: "User"
    ) -> None:
        """Test changing password."""
        # Login to get token
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "TestPass123!",
            },
        )
        token = login_resp.json()["data"]["access_token"]

        resp = await client.put(
            "/api/v1/auth/me/password",
            json={
                "current_password": "TestPass123!",
                "new_password": "NewSecure456!",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_change_password_wrong_current(
        self, client: AsyncClient, test_user: "User"
    ) -> None:
        """Test change password with wrong current password returns 401."""
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "TestPass123!",
            },
        )
        token = login_resp.json()["data"]["access_token"]

        resp = await client.put(
            "/api/v1/auth/me/password",
            json={
                "current_password": "WrongCurrent!",
                "new_password": "NewSecure456!",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 401
