"""Authentication Pydantic schemas.

Defines request/response models for authentication endpoints.

Schemas:
    RegisterRequest: User registration input
    LoginRequest: User login input
    TokenResponse: JWT token pair response
    UserProfile: User profile response
    UpdateProfileRequest: Profile update input
    ChangePasswordRequest: Password change input
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    """User registration request.

    Attributes:
        email: Valid email address.
        username: Unique username (3-100 chars, alphanumeric).
        password: Password (min 8 chars, must include upper/lower/digit).
        full_name: Optional display name.
    """

    email: EmailStr = Field(..., description="Email address")
    username: str = Field(
        ..., min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$",
        description="Username (alphanumeric, 3-100 chars)",
    )
    password: str = Field(
        ..., min_length=8, max_length=128,
        description="Password (min 8 chars)",
    )
    full_name: str | None = Field(
        default=None, max_length=255, description="Full name"
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets complexity requirements.

        Args:
            v: Password string.

        Returns:
            Validated password.

        Raises:
            ValueError: If password is too weak.
        """
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseModel):
    """User login request.

    Attributes:
        email: Registered email address.
        password: Account password.
    """

    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=1, max_length=128, description="Password")


class TokenResponse(BaseModel):
    """JWT token pair response.

    Attributes:
        access_token: JWT access token.
        refresh_token: JWT refresh token.
        token_type: Token type (always "bearer").
        expires_in: Access token TTL in seconds.
    """

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token TTL in seconds")


class RefreshTokenRequest(BaseModel):
    """Refresh token request.

    Attributes:
        refresh_token: JWT refresh token.
    """

    refresh_token: str = Field(..., description="Refresh token")


class UserProfile(BaseModel):
    """User profile response.

    Attributes:
        id: User UUID.
        email: Email address.
        username: Username.
        full_name: Display name.
        role: User role.
        is_active: Account status.
        avatar_url: Avatar image URL.
        created_at: Account creation timestamp.
        last_login_at: Last login timestamp.
    """

    id: uuid.UUID = Field(..., description="User UUID")
    email: str = Field(..., description="Email address")
    username: str = Field(..., description="Username")
    full_name: str | None = Field(default=None, description="Full name")
    role: str = Field(..., description="User role")
    is_active: bool = Field(..., description="Account active status")
    avatar_url: str | None = Field(default=None, description="Avatar URL")
    created_at: datetime = Field(..., description="Account created at")
    last_login_at: datetime | None = Field(default=None, description="Last login")

    model_config = {"from_attributes": True}


class UpdateProfileRequest(BaseModel):
    """Profile update request.

    Attributes:
        full_name: New display name.
        avatar_url: New avatar URL.
    """

    full_name: str | None = Field(
        default=None, max_length=255, description="New full name"
    )
    avatar_url: str | None = Field(
        default=None, max_length=2048, description="New avatar URL"
    )


class ChangePasswordRequest(BaseModel):
    """Password change request.

    Attributes:
        current_password: Current password for verification.
        new_password: New password to set.
    """

    current_password: str = Field(
        ..., min_length=1, max_length=128, description="Current password"
    )
    new_password: str = Field(
        ..., min_length=8, max_length=128, description="New password"
    )

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate new password strength.

        Args:
            v: New password string.

        Returns:
            Validated password.

        Raises:
            ValueError: If password is too weak.
        """
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v
