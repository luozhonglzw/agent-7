"""Security module unit tests.

Tests for password hashing and JWT token operations.
"""

import uuid

import pytest

from app.core.security.password import get_password_hash, verify_password
from app.core.security.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token,
)
from app.exceptions import InvalidTokenError, TokenExpiredError


class TestPasswordHashing:
    """Tests for password hashing utilities."""

    def test_hash_password(self) -> None:
        """Test password hashing produces valid bcrypt hash."""
        password = "SecurePass123!"
        hashed = get_password_hash(password)

        assert hashed != password
        assert hashed.startswith("$2b$")
        assert len(hashed) > 50

    def test_verify_correct_password(self) -> None:
        """Test password verification with correct password."""
        password = "SecurePass123!"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self) -> None:
        """Test password verification with wrong password."""
        hashed = get_password_hash("CorrectPass123!")

        assert verify_password("WrongPass123!", hashed) is False

    def test_different_hashes_for_same_password(self) -> None:
        """Test that same password produces different hashes."""
        password = "SecurePass123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2
        # Both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

    def test_empty_password(self) -> None:
        """Test hashing empty password."""
        hashed = get_password_hash("")
        assert verify_password("", hashed) is True

    def test_unicode_password(self) -> None:
        """Test hashing Unicode password."""
        password = "密码测试123!@#"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True


class TestJWTToken:
    """Tests for JWT token operations."""

    def test_create_access_token(self) -> None:
        """Test access token creation."""
        user_id = str(uuid.uuid4())
        token = create_access_token(subject=user_id, role="admin")

        assert isinstance(token, str)
        assert len(token) > 0
        assert token.count(".") == 2  # JWT has 3 parts

    def test_decode_access_token(self) -> None:
        """Test access token decoding."""
        user_id = str(uuid.uuid4())
        token = create_access_token(subject=user_id, role="editor")

        payload = decode_token(token)

        assert payload["sub"] == user_id
        assert payload["role"] == "editor"
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload

    def test_create_refresh_token(self) -> None:
        """Test refresh token creation."""
        user_id = str(uuid.uuid4())
        token = create_refresh_token(subject=user_id)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_refresh_token(self) -> None:
        """Test refresh token decoding."""
        user_id = str(uuid.uuid4())
        token = create_refresh_token(subject=user_id)

        payload = decode_token(token)

        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"

    def test_verify_token_correct_type(self) -> None:
        """Test token verification with correct type."""
        user_id = str(uuid.uuid4())
        token = create_access_token(subject=user_id)

        payload = verify_token(token, expected_type="access")
        assert payload["sub"] == user_id

    def test_verify_token_wrong_type(self) -> None:
        """Test token verification with wrong type raises error."""
        user_id = str(uuid.uuid4())
        token = create_access_token(subject=user_id)

        with pytest.raises(InvalidTokenError):
            verify_token(token, expected_type="refresh")

    def test_decode_invalid_token(self) -> None:
        """Test decoding invalid token raises error."""
        with pytest.raises(InvalidTokenError):
            decode_token("invalid.token.here")

    def test_decode_expired_token(self) -> None:
        """Test decoding expired token raises error."""
        # Create a token that expires immediately
        from datetime import datetime, timedelta, timezone
        from jose import jwt

        payload = {
            "sub": str(uuid.uuid4()),
            "type": "access",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        expired_token = jwt.encode(
            payload, "test_secret", algorithm="HS256"
        )

        # This should raise an error
        with pytest.raises((TokenExpiredError, InvalidTokenError)):
            decode_token(expired_token)

    def test_extra_claims(self) -> None:
        """Test access token with extra claims."""
        user_id = str(uuid.uuid4())
        extra = {"department": "engineering", "team": "backend"}
        token = create_access_token(
            subject=user_id, role="admin", extra_claims=extra
        )

        payload = decode_token(token)
        assert payload["department"] == "engineering"
        assert payload["team"] == "backend"

    def test_token_with_session_id(self) -> None:
        """Test refresh token with session ID."""
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        token = create_refresh_token(subject=user_id, session_id=session_id)

        payload = decode_token(token)
        assert payload["session_id"] == session_id
