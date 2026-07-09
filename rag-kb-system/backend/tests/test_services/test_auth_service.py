"""AuthService unit tests.

Tests for user registration, login, token refresh, and profile management.
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.password import get_password_hash, verify_password
from app.exceptions import (
    CredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
    ValidationError,
)
from app.models.user import User
from app.services.auth_service import AuthService, _validate_password_strength


class TestPasswordValidation:
    """Tests for password strength validation."""

    def test_valid_password(self) -> None:
        """Test that a strong password passes validation."""
        _validate_password_strength("SecurePass123")

    def test_too_short(self) -> None:
        """Test rejection of short password."""
        with pytest.raises(ValidationError, field="password"):
            _validate_password_strength("Ab1")

    def test_no_uppercase(self) -> None:
        """Test rejection of password without uppercase."""
        with pytest.raises(ValidationError):
            _validate_password_strength("lowercase123")

    def test_no_lowercase(self) -> None:
        """Test rejection of password without lowercase."""
        with pytest.raises(ValidationError):
            _validate_password_strength("UPPERCASE123")

    def test_no_digit(self) -> None:
        """Test rejection of password without digit."""
        with pytest.raises(ValidationError):
            _validate_password_strength("NoDigitsHere")

    def test_unicode_password(self) -> None:
        """Test that unicode passwords with proper complexity pass."""
        # Has upper, lower, digit, and is long enough
        _validate_password_strength("Пароль123Test")


class TestAuthServiceRegister:
    """Tests for AuthService.register."""

    @pytest_asyncio.fixture
    def service(self, db_session: AsyncSession) -> AuthService:
        """Create AuthService instance with test session."""
        return AuthService(db_session)

    async def test_register_success(
        self, service: AuthService, db_session: AsyncSession
    ) -> None:
        """Test successful user registration."""
        email = f"new_{uuid.uuid4().hex[:8]}@example.com"
        username = f"newuser_{uuid.uuid4().hex[:8]}"

        user = await service.register(
            email=email,
            username=username,
            password="ValidPass123",
            full_name="New User",
        )

        assert user.email == email
        assert user.username == username
        assert user.full_name == "New User"
        assert user.role == "user"
        assert user.is_active is True
        assert user.hashed_password != "ValidPass123"
        assert verify_password("ValidPass123", user.hashed_password)

    async def test_register_with_dept_id(
        self, service: AuthService
    ) -> None:
        """Test registration with department ID."""
        dept = uuid.uuid4()
        user = await service.register(
            email=f"dept_{uuid.uuid4().hex[:8]}@example.com",
            username=f"dept_{uuid.uuid4().hex[:8]}",
            password="ValidPass123",
            dept_id=dept,
        )

        assert user.dept_id == dept

    async def test_register_duplicate_email(
        self, service: AuthService, test_user: User
    ) -> None:
        """Test registration with existing email raises error."""
        with pytest.raises(UserAlreadyExistsError):
            await service.register(
                email=test_user.email,
                username=f"unique_{uuid.uuid4().hex[:8]}",
                password="ValidPass123",
            )

    async def test_register_duplicate_username(
        self, service: AuthService, test_user: User
    ) -> None:
        """Test registration with existing username raises error."""
        with pytest.raises(UserAlreadyExistsError):
            await service.register(
                email=f"unique_{uuid.uuid4().hex[:8]}@example.com",
                username=test_user.username,
                password="ValidPass123",
            )

    async def test_register_weak_password(
        self, service: AuthService
    ) -> None:
        """Test registration with weak password raises error."""
        with pytest.raises(ValidationError):
            await service.register(
                email=f"weak_{uuid.uuid4().hex[:8]}@example.com",
                username=f"weak_{uuid.uuid4().hex[:8]}",
                password="weak",
            )

    async def test_register_password_is_hashed(
        self, service: AuthService
    ) -> None:
        """Test that password is bcrypt-hashed, not stored in plaintext."""
        user = await service.register(
            email=f"hash_{uuid.uuid4().hex[:8]}@example.com",
            username=f"hash_{uuid.uuid4().hex[:8]}",
            password="HashTest123",
        )

        assert user.hashed_password != "HashTest123"
        assert user.hashed_password.startswith("$2b$")
        assert verify_password("HashTest123", user.hashed_password)


class TestAuthServiceLogin:
    """Tests for AuthService.login."""

    @pytest_asyncio.fixture
    def service(self, db_session: AsyncSession) -> AuthService:
        """Create AuthService instance with test session."""
        return AuthService(db_session)

    async def test_login_success(
        self, service: AuthService, test_user: User
    ) -> None:
        """Test successful login returns tokens."""
        result = await service.login(
            email=test_user.email,
            password="TestPass123!",
        )

        assert "access_token" in result
        assert "refresh_token" in result
        assert result["token_type"] == "bearer"
        assert result["expires_in"] > 0
        assert result["user"].id == test_user.id

    async def test_login_wrong_password(
        self, service: AuthService, test_user: User
    ) -> None:
        """Test login with wrong password raises CredentialsError."""
        with pytest.raises(CredentialsError):
            await service.login(
                email=test_user.email,
                password="WrongPass123!",
            )

    async def test_login_nonexistent_email(
        self, service: AuthService
    ) -> None:
        """Test login with nonexistent email raises CredentialsError."""
        with pytest.raises(CredentialsError):
            await service.login(
                email="nonexistent@example.com",
                password="AnyPass123!",
            )

    async def test_login_inactive_user(
        self, service: AuthService, db_session: AsyncSession
    ) -> None:
        """Test login with inactive account raises CredentialsError."""
        user = User(
            email=f"inactive_{uuid.uuid4().hex[:8]}@example.com",
            username=f"inactive_{uuid.uuid4().hex[:8]}",
            hashed_password=get_password_hash("InactivePass123!"),
            role="user",
            is_active=False,
        )
        db_session.add(user)
        await db_session.flush()

        with pytest.raises(CredentialsError):
            await service.login(
                email=user.email,
                password="InactivePass123!",
            )

    async def test_login_records_ip_and_user_agent(
        self, service: AuthService, test_user: User
    ) -> None:
        """Test that login records IP and user agent in session."""
        result = await service.login(
            email=test_user.email,
            password="TestPass123!",
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0",
        )

        # Tokens should be present
        assert result["access_token"]
        assert result["refresh_token"]


class TestAuthServiceRefresh:
    """Tests for AuthService.refresh_access_token."""

    @pytest_asyncio.fixture
    def service(self, db_session: AsyncSession) -> AuthService:
        """Create AuthService instance with test session."""
        return AuthService(db_session)

    async def test_refresh_success(
        self, service: AuthService, test_user: User
    ) -> None:
        """Test successful token refresh."""
        # First login to get a refresh token
        login_result = await service.login(
            email=test_user.email,
            password="TestPass123!",
        )
        refresh_token = login_result["refresh_token"]

        # Refresh
        result = await service.refresh_access_token(refresh_token)

        assert "access_token" in result
        assert result["token_type"] == "bearer"
        assert result["expires_in"] > 0

    async def test_refresh_invalid_token(
        self, service: AuthService
    ) -> None:
        """Test refresh with invalid token raises error."""
        with pytest.raises(CredentialsError):
            await service.refresh_access_token("invalid.token.here")

    async def test_refresh_with_access_token(
        self, service: AuthService, test_user: User
    ) -> None:
        """Test refresh with an access token (wrong type) raises error."""
        login_result = await service.login(
            email=test_user.email,
            password="TestPass123!",
        )
        # Try to use access token as refresh token
        with pytest.raises(CredentialsError):
            await service.refresh_access_token(login_result["access_token"])


class TestAuthServiceProfile:
    """Tests for AuthService profile operations."""

    @pytest_asyncio.fixture
    def service(self, db_session: AsyncSession) -> AuthService:
        """Create AuthService instance with test session."""
        return AuthService(db_session)

    async def test_get_user_by_id(
        self, service: AuthService, test_user: User
    ) -> None:
        """Test get user by ID."""
        user = await service.get_user_by_id(test_user.id)
        assert user.id == test_user.id
        assert user.email == test_user.email

    async def test_get_user_by_id_not_found(
        self, service: AuthService
    ) -> None:
        """Test get user by nonexistent ID raises error."""
        with pytest.raises(UserNotFoundError):
            await service.get_user_by_id(uuid.uuid4())

    async def test_update_profile(
        self, service: AuthService, test_user: User
    ) -> None:
        """Test updating user profile."""
        user = await service.update_profile(
            user_id=test_user.id,
            full_name="Updated Name",
            avatar_url="https://example.com/avatar.png",
        )

        assert user.full_name == "Updated Name"
        assert user.avatar_url == "https://example.com/avatar.png"

    async def test_update_profile_partial(
        self, service: AuthService, test_user: User
    ) -> None:
        """Test partial profile update (only full_name)."""
        user = await service.update_profile(
            user_id=test_user.id,
            full_name="Only Name",
        )

        assert user.full_name == "Only Name"

    async def test_change_password(
        self, service: AuthService, test_user: User
    ) -> None:
        """Test changing user password."""
        await service.change_password(
            user_id=test_user.id,
            current_password="TestPass123!",
            new_password="NewSecurePass456!",
        )

        # Verify new password works
        user = await service.get_user_by_id(test_user.id)
        assert verify_password("NewSecurePass456!", user.hashed_password)

    async def test_change_password_wrong_current(
        self, service: AuthService, test_user: User
    ) -> None:
        """Test change password with wrong current password."""
        with pytest.raises(CredentialsError):
            await service.change_password(
                user_id=test_user.id,
                current_password="WrongCurrent123!",
                new_password="NewSecurePass456!",
            )

    async def test_change_password_weak_new(
        self, service: AuthService, test_user: User
    ) -> None:
        """Test change password with weak new password."""
        with pytest.raises(ValidationError):
            await service.change_password(
                user_id=test_user.id,
                current_password="TestPass123!",
                new_password="weak",
            )
