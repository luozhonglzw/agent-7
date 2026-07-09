"""Authentication API endpoints.

Handles user registration, login, token refresh, and profile management.

Endpoints:
    POST /auth/register: Register new user
    POST /auth/login: User login
    POST /auth/refresh: Refresh access token
    GET  /auth/me: Get current user profile
    PUT  /auth/me: Update current user profile
"""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_client_ip, get_current_user
from app.core.security.audit import audit_log
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserProfile,
)
from app.schemas.common import SuccessResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=SuccessResponse[TokenResponse], status_code=201)
@audit_log(action="register", resource_type="user")
async def register(
    request: Request,
    background_tasks: BackgroundTasks,
    body: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse[TokenResponse]:
    """Register a new user account.

    Validates password strength, checks email/username uniqueness,
    hashes the password with bcrypt, and creates the user.
    Returns access and refresh tokens upon successful registration.

    Args:
        request: FastAPI request (for audit context).
        background_tasks: FastAPI background tasks (for async audit write).
        body: Registration request data.
        db: Database session.

    Returns:
        SuccessResponse with JWT token pair.
    """
    service = AuthService(db)
    user = await service.register(
        email=body.email,
        username=body.username,
        password=body.password,
        full_name=body.full_name,
    )

    # Auto-login: generate tokens right after registration
    from app.core.security.jwt import create_access_token, create_refresh_token
    from app.config import settings
    from datetime import datetime, timedelta, timezone
    from app.models.user import UserSession

    access_token = create_access_token(subject=user.id, role=user.role)
    refresh_token = create_refresh_token(subject=user.id)

    session = UserSession(
        user_id=user.id,
        refresh_token=refresh_token,
        user_agent=request.headers.get("User-Agent"),
        ip_address=get_client_ip(request),
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.jwt.refresh_token_expire_days),
    )
    db.add(session)
    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()

    token_data = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.jwt.access_token_expire_minutes * 60,
    )
    return SuccessResponse(data=token_data)


@router.post("/login", response_model=SuccessResponse[TokenResponse])
@audit_log(action="login", resource_type="user")
async def login(
    request: Request,
    background_tasks: BackgroundTasks,
    body: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse[TokenResponse]:
    """Authenticate user and return tokens.

    Validates credentials and returns JWT access and refresh tokens.
    Records login attempt in audit log.

    Args:
        request: FastAPI request (for audit context).
        background_tasks: FastAPI background tasks (for async audit write).
        body: Login request data.
        db: Database session.

    Returns:
        SuccessResponse with JWT token pair.
    """
    service = AuthService(db)
    result = await service.login(
        email=body.email,
        password=body.password,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    token_data = TokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        token_type=result["token_type"],
        expires_in=result["expires_in"],
    )
    return SuccessResponse(data=token_data)


@router.post("/refresh", response_model=SuccessResponse[TokenResponse])
async def refresh_token(
    body: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse[TokenResponse]:
    """Refresh access token using refresh token.

    Accepts a valid refresh token and returns a new access token.
    The refresh token remains valid until its expiry.

    Args:
        body: Refresh token request data.
        db: Database session.

    Returns:
        SuccessResponse with new JWT token pair.
    """
    service = AuthService(db)
    result = await service.refresh_access_token(body.refresh_token)

    token_data = TokenResponse(
        access_token=result["access_token"],
        refresh_token=body.refresh_token,
        token_type=result["token_type"],
        expires_in=result["expires_in"],
    )
    return SuccessResponse(data=token_data)


@router.get("/me", response_model=SuccessResponse[UserProfile])
async def get_profile(
    current_user: Annotated[User, Depends(get_current_user)],
) -> SuccessResponse[UserProfile]:
    """Get current user profile.

    Returns the authenticated user's profile information.

    Args:
        current_user: Authenticated user from JWT token.

    Returns:
        SuccessResponse with user profile data.
    """
    profile = UserProfile.model_validate(current_user)
    return SuccessResponse(data=profile)


@router.put("/me", response_model=SuccessResponse[UserProfile])
async def update_profile(
    body: UpdateProfileRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse[UserProfile]:
    """Update current user profile.

    Allows updating display name and avatar URL.

    Args:
        body: Profile update data.
        current_user: Authenticated user from JWT token.
        db: Database session.

    Returns:
        SuccessResponse with updated user profile.
    """
    service = AuthService(db)
    user = await service.update_profile(
        user_id=current_user.id,
        full_name=body.full_name,
        avatar_url=body.avatar_url,
    )
    profile = UserProfile.model_validate(user)
    return SuccessResponse(data=profile)


@router.put("/me/password", response_model=SuccessResponse)
async def change_password(
    body: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse:
    """Change current user password.

    Verifies the current password, validates new password strength,
    and updates the password hash.

    Args:
        body: Password change data.
        current_user: Authenticated user from JWT token.
        db: Database session.

    Returns:
        SuccessResponse confirming password change.
    """
    service = AuthService(db)
    await service.change_password(
        user_id=current_user.id,
        current_password=body.current_password,
        new_password=body.new_password,
    )
    return SuccessResponse(message="Password changed successfully")
