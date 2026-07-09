"""Custom exception classes for the RAG Knowledge Base System.

Provides a structured exception hierarchy with error codes for
consistent API error responses. All custom exceptions inherit
from AppException which provides error code and HTTP status mapping.

Error Code Ranges:
    0:      Success (no error)
    1000-1999: Authentication errors
    2000-2999: Authorization errors
    3000-3999: Validation errors
    4000-4999: Client errors
    5000-5999: Server errors

Usage:
    raise DocumentNotFoundError(document_id="abc-123")
    raise ValidationError(detail="Invalid email format", field="email")
"""

from typing import Any


class AppException(Exception):
    """Base application exception.

    All custom exceptions should inherit from this class.
    Provides structured error information for API responses.

    Attributes:
        code: Numeric error code for programmatic handling.
        message: Human-readable error message.
        detail: Additional error details.
        status_code: HTTP status code.
    """

    def __init__(
        self,
        code: int = 5000,
        message: str = "Internal server error",
        detail: str | None = None,
        status_code: int = 500,
    ) -> None:
        """Initialize application exception.

        Args:
            code: Numeric error code.
            message: Human-readable error message.
            detail: Additional error details.
            status_code: HTTP status code.
        """
        self.code = code
        self.message = message
        self.detail = detail or message
        self.status_code = status_code
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to API response format.

        Returns:
            Dictionary with code, message, and data fields.
        """
        return {
            "code": self.code,
            "message": self.message,
            "data": {"detail": self.detail},
        }


# ═══════════════════════════════════════════════════════════════
# Authentication Exceptions (1000-1999)
# ═══════════════════════════════════════════════════════════════


class AuthenticationError(AppException):
    """Raised when authentication fails.

    Used for invalid credentials, expired tokens, or missing auth.
    """

    def __init__(
        self,
        message: str = "Authentication failed",
        detail: str | None = None,
    ) -> None:
        super().__init__(
            code=1000,
            message=message,
            detail=detail,
            status_code=401,
        )


class TokenExpiredError(AuthenticationError):
    """Raised when a JWT token has expired."""

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(
            message="Token has expired",
            detail=detail or "Please log in again to obtain a new token",
        )
        self.code = 1001


class InvalidTokenError(AuthenticationError):
    """Raised when a JWT token is invalid or malformed."""

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(
            message="Invalid token",
            detail=detail or "The provided token is invalid or malformed",
        )
        self.code = 1002


class CredentialsError(AuthenticationError):
    """Raised when login credentials are incorrect."""

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(
            message="Invalid credentials",
            detail=detail or "Email or password is incorrect",
        )
        self.code = 1003


class UserAlreadyExistsError(AuthenticationError):
    """Raised when attempting to register an existing user."""

    def __init__(self, email: str = "") -> None:
        super().__init__(
            message="User already exists",
            detail=f"A user with email '{email}' already exists" if email else None,
        )
        self.code = 1004
        self.status_code = 409


# ═══════════════════════════════════════════════════════════════
# Authorization Exceptions (2000-2999)
# ═══════════════════════════════════════════════════════════════


class AuthorizationError(AppException):
    """Raised when a user lacks permission for an action."""

    def __init__(
        self,
        message: str = "Permission denied",
        detail: str | None = None,
    ) -> None:
        super().__init__(
            code=2000,
            message=message,
            detail=detail,
            status_code=403,
        )


class RoleNotFoundError(AuthorizationError):
    """Raised when a required role is not found."""

    def __init__(self, role: str = "") -> None:
        super().__init__(
            message="Role not found",
            detail=f"Role '{role}' does not exist" if role else None,
        )
        self.code = 2001


# ═══════════════════════════════════════════════════════════════
# Validation Exceptions (3000-3999)
# ═══════════════════════════════════════════════════════════════


class ValidationError(AppException):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str = "Validation error",
        detail: str | None = None,
        field: str | None = None,
    ) -> None:
        """Initialize validation error.

        Args:
            message: Error message.
            detail: Detailed error description.
            field: The field that failed validation.
        """
        super().__init__(
            code=3000,
            message=message,
            detail=detail,
            status_code=422,
        )
        self.field = field

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict with field info.

        Returns:
            Error dictionary with field information.
        """
        result = super().to_dict()
        if self.field:
            result["data"]["field"] = self.field
        return result


class FileValidationError(ValidationError):
    """Raised when file validation fails."""

    def __init__(
        self,
        message: str = "File validation error",
        detail: str | None = None,
        field: str = "file",
    ) -> None:
        super().__init__(message=message, detail=detail, field=field)
        self.code = 3001


class FileSizeExceededError(FileValidationError):
    """Raised when uploaded file exceeds size limit."""

    def __init__(self, max_size_mb: int = 50, actual_size_mb: int = 0) -> None:
        super().__init__(
            message="File size exceeded",
            detail=f"File size ({actual_size_mb}MB) exceeds limit ({max_size_mb}MB)",
        )
        self.code = 3002


class UnsupportedFileTypeError(FileValidationError):
    """Raised when file type is not supported."""

    def __init__(self, file_type: str = "", allowed: list[str] | None = None) -> None:
        allowed_str = ", ".join(allowed) if allowed else "N/A"
        super().__init__(
            message="Unsupported file type",
            detail=f"File type '{file_type}' is not supported. Allowed: {allowed_str}",
        )
        self.code = 3003


# ═══════════════════════════════════════════════════════════════
# Client Errors (4000-4999)
# ═══════════════════════════════════════════════════════════════


class NotFoundError(AppException):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        resource: str = "Resource",
        identifier: str = "",
    ) -> None:
        detail = f"{resource} '{identifier}' not found" if identifier else None
        super().__init__(
            code=4000,
            message=f"{resource} not found",
            detail=detail,
            status_code=404,
        )


class DocumentNotFoundError(NotFoundError):
    """Raised when a document is not found."""

    def __init__(self, document_id: str = "") -> None:
        super().__init__(resource="Document", identifier=document_id)
        self.code = 4001


class UserNotFoundError(NotFoundError):
    """Raised when a user is not found."""

    def __init__(self, user_id: str = "") -> None:
        super().__init__(resource="User", identifier=user_id)
        self.code = 4002


class ConflictError(AppException):
    """Raised when an operation conflicts with current state."""

    def __init__(
        self,
        message: str = "Conflict",
        detail: str | None = None,
    ) -> None:
        super().__init__(
            code=4003,
            message=message,
            detail=detail,
            status_code=409,
        )


class RateLimitError(AppException):
    """Raised when rate limit is exceeded."""

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(
            code=4004,
            message="Rate limit exceeded",
            detail=detail or "Too many requests, please try again later",
            status_code=429,
        )


class DocumentProcessingError(AppException):
    """Raised when document processing fails."""

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(
            code=4005,
            message="Document processing failed",
            detail=detail,
            status_code=422,
        )


# ═══════════════════════════════════════════════════════════════
# Server Errors (5000-5999)
# ═══════════════════════════════════════════════════════════════


class DatabaseError(AppException):
    """Raised when a database operation fails."""

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(
            code=5000,
            message="Database error",
            detail=detail or "A database error occurred",
            status_code=500,
        )


class ExternalServiceError(AppException):
    """Raised when an external service call fails."""

    def __init__(self, service: str = "", detail: str | None = None) -> None:
        super().__init__(
            code=5001,
            message=f"External service error: {service}" if service else "External service error",
            detail=detail,
            status_code=502,
        )


class LLMServiceError(ExternalServiceError):
    """Raised when LLM service call fails."""

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(service="LLM", detail=detail)
        self.code = 5002


class EmbeddingServiceError(ExternalServiceError):
    """Raised when embedding generation fails."""

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(service="Embedding", detail=detail)
        self.code = 5003


class VectorStoreError(ExternalServiceError):
    """Raised when vector store operation fails."""

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(service="Qdrant", detail=detail)
        self.code = 5004


class TaskQueueError(AppException):
    """Raised when a Celery task fails."""

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(
            code=5005,
            message="Task queue error",
            detail=detail or "Failed to enqueue or process task",
            status_code=500,
        )
