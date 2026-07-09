"""Audit log decorator unit tests.

Tests for the @audit_log decorator, including context extraction,
timing, error handling, and background task scheduling.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import BackgroundTasks, Request

from app.core.security.audit import (
    _extract_request_context,
    audit_log,
)


class TestExtractRequestContext:
    """Tests for _extract_request_context helper."""

    def test_extracts_from_request_object(self) -> None:
        """Test extraction from a mock Request."""
        request = MagicMock(spec=Request)
        request.state.request_id = "req-123"
        request.headers = {
            "User-Agent": "TestAgent/1.0",
            "X-Forwarded-For": "10.0.0.1, 10.0.0.2",
        }

        request_id, user_id, ip, ua = _extract_request_context({"request": request})

        assert request_id == "req-123"
        assert ip == "10.0.0.1"  # First in chain
        assert ua == "TestAgent/1.0"
        assert user_id is None

    def test_extracts_user_from_kwargs(self) -> None:
        """Test extraction of user from kwargs."""
        user = MagicMock()
        user.id = uuid.uuid4()
        user.email = "test@example.com"

        _, user_id, _, _ = _extract_request_context({"current_user": user})

        assert user_id == user.id

    def test_extracts_ip_from_client(self) -> None:
        """Test fallback to request.client.host."""
        request = MagicMock(spec=Request)
        request.state.request_id = "req-456"
        request.headers = {"User-Agent": "TestAgent/2.0"}
        request.client.host = "192.168.1.100"

        _, _, ip, _ = _extract_request_context({"request": request})

        assert ip == "192.168.1.100"

    def test_returns_none_when_no_request(self) -> None:
        """Test returns all None when no request in kwargs."""
        request_id, user_id, ip, ua = _extract_request_context({})

        assert request_id is None
        assert user_id is None
        assert ip is None
        assert ua is None


@pytest.mark.asyncio
class TestAuditLogDecorator:
    """Tests for @audit_log decorator."""

    async def test_decorator_passes_through_return_value(self) -> None:
        """Test that the decorator does not alter the return value."""

        @audit_log(action="test", resource_type="resource")
        async def endpoint(
            request: Request,
            background_tasks: BackgroundTasks,
        ) -> dict:
            return {"result": "ok"}

        request = MagicMock(spec=Request)
        request.state.request_id = "req-1"
        request.headers = {"User-Agent": "Test"}
        request.path_params = {}
        bg = BackgroundTasks()

        result = await endpoint(request=request, background_tasks=bg)
        assert result == {"result": "ok"}

    async def test_decorator_passes_through_exception(self) -> None:
        """Test that exceptions propagate through the decorator."""

        @audit_log(action="fail", resource_type="resource")
        async def endpoint(
            request: Request,
            background_tasks: BackgroundTasks,
        ) -> None:
            raise ValueError("something broke")

        request = MagicMock(spec=Request)
        request.state.request_id = "req-2"
        request.headers = {"User-Agent": "Test"}
        request.path_params = {}
        bg = BackgroundTasks()

        with pytest.raises(ValueError, match="something broke"):
            await endpoint(request=request, background_tasks=bg)

    async def test_decorator_skips_audit_without_request(self) -> None:
        """Test that the decorator is a no-op when request is missing."""

        @audit_log(action="skip", resource_type="resource")
        async def endpoint() -> dict:
            return {"skipped": True}

        result = await endpoint()
        assert result == {"skipped": True}

    async def test_decorator_schedules_background_task(self) -> None:
        """Test that the decorator adds a background task."""

        @audit_log(action="upload", resource_type="document")
        async def endpoint(
            request: Request,
            background_tasks: BackgroundTasks,
        ) -> dict:
            return {"uploaded": True}

        request = MagicMock(spec=Request)
        request.state.request_id = "req-3"
        request.headers = {"User-Agent": "TestAgent"}
        request.path_params = {"document_id": "doc-123"}
        bg = BackgroundTasks()

        # BackgroundTasks.add_task is sync; we just verify it was called.
        bg.add_task = MagicMock()

        result = await endpoint(request=request, background_tasks=bg)
        assert result == {"uploaded": True}

        bg.add_task.assert_called_once()
        call_kwargs = bg.add_task.call_args
        # First positional arg is the coroutine function
        assert call_kwargs[0][0].__name__ == "_write_audit_log"

    async def test_decorator_records_failure_status(self) -> None:
        """Test that the decorator records failure on exception."""

        @audit_log(action="boom", resource_type="resource")
        async def endpoint(
            request: Request,
            background_tasks: BackgroundTasks,
        ) -> None:
            raise RuntimeError("kaboom")

        request = MagicMock(spec=Request)
        request.state.request_id = "req-4"
        request.headers = {"User-Agent": "Test"}
        request.path_params = {}
        bg = BackgroundTasks()
        bg.add_task = MagicMock()

        with pytest.raises(RuntimeError):
            await endpoint(request=request, background_tasks=bg)

        bg.add_task.assert_called_once()
        call_kwargs = bg.add_task.call_args
        # The status kwarg should be "failure"
        assert call_kwargs[1]["status"] == "failure"
        assert "kaboom" in call_kwargs[1]["error_message"]


@pytest.mark.asyncio
class TestWriteAuditLog:
    """Tests for _write_audit_log database writer."""

    async def test_write_creates_audit_record(self) -> None:
        """Test that _write_audit_log inserts a record (mocked session)."""
        from app.core.security.audit import _write_audit_log

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        with patch(
            "app.core.security.audit.AsyncSessionLocal"
        ) as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            await _write_audit_log(
                user_id=uuid.uuid4(),
                action="test_action",
                resource_type="test",
                resource_id="res-1",
                request_id="req-1",
                status="success",
                latency_ms=42.5,
                ip_address="127.0.0.1",
                user_agent="TestAgent",
            )

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    async def test_write_does_not_raise_on_failure(self) -> None:
        """Test that _write_audit_log swallows exceptions."""
        from app.core.security.audit import _write_audit_log

        with patch(
            "app.core.security.audit.AsyncSessionLocal"
        ) as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(
                side_effect=Exception("db down")
            )

            # Should not raise
            await _write_audit_log(
                user_id=uuid.uuid4(),
                action="test",
                resource_type=None,
                resource_id=None,
                request_id=None,
                status="success",
                latency_ms=0.0,
                ip_address=None,
                user_agent=None,
            )
