"""Health check endpoint tests.

Tests for /health and /health/ready endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient) -> None:
    """Test basic health check endpoint.

    Args:
        client: Async HTTP test client.
    """
    response = await client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["code"] == 0
    assert data["message"] == "healthy"
    assert "app" in data["data"]
    assert "version" in data["data"]


@pytest.mark.asyncio
async def test_health_response_format(client: AsyncClient) -> None:
    """Test health check response format.

    Args:
        client: Async HTTP test client.
    """
    response = await client.get("/health")
    data = response.json()

    # Verify unified response format
    assert "code" in data
    assert "message" in data
    assert "data" in data
    assert isinstance(data["code"], int)
    assert isinstance(data["message"], str)
