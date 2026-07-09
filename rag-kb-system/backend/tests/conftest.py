"""Pytest configuration and shared fixtures.

Provides test database sessions, mock services, and
common test utilities.

Usage:
    pytest tests/ -v --tb=short
"""

import asyncio
import uuid
from collections.abc import AsyncGenerator, Generator
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings
from app.database import get_db
from app.main import app
from app.models.base import Base
from app.models.user import User
from app.core.security.password import get_password_hash


# ── Test Database ──────────────────────────────────────────────
TEST_DATABASE_URL = (
    f"postgresql+asyncpg://{settings.db.user}:{settings.db.password}"
    f"@{settings.db.host}:{settings.db.port}/rag_kb_test"
)

test_engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests.

    Yields:
        Event loop instance.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def setup_database() -> AsyncGenerator[None, None]:
    """Create and tear down test database tables.

    Yields:
        None after tables are created.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(setup_database: None) -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session with automatic rollback.

    Args:
        setup_database: Ensures tables exist.

    Yields:
        AsyncSession for test use.
    """
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client for API testing.

    Overrides the database dependency with the test session.

    Args:
        db_session: Test database session.

    Yields:
        AsyncClient for making API requests.
    """

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data() -> dict:
    """Provide test user registration data.

    Returns:
        Dictionary with user registration fields.
    """
    return {
        "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
        "username": f"testuser_{uuid.uuid4().hex[:8]}",
        "password": "TestPass123!",
        "full_name": "Test User",
    }


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user in the database.

    Args:
        db_session: Test database session.

    Returns:
        Created User instance.
    """
    user = User(
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        username=f"testuser_{uuid.uuid4().hex[:8]}",
        hashed_password=get_password_hash("TestPass123!"),
        full_name="Test User",
        role="viewer",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin test user.

    Args:
        db_session: Test database session.

    Returns:
        Created admin User instance.
    """
    user = User(
        email=f"admin_{uuid.uuid4().hex[:8]}@example.com",
        username=f"admin_{uuid.uuid4().hex[:8]}",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Admin User",
        role="admin",
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def mock_embedding_service() -> MagicMock:
    """Provide a mock embedding service.

    Returns:
        MagicMock configured for embedding operations.
    """
    mock = MagicMock()
    mock.encode.return_value = [[0.1] * 1024]
    return mock


@pytest.fixture
def mock_llm_service() -> AsyncMock:
    """Provide a mock LLM service.

    Returns:
        AsyncMock configured for LLM operations.
    """
    mock = AsyncMock()
    mock.generate.return_value = "This is a test answer."
    return mock
