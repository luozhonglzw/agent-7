"""Pydantic schemas for API request/response validation.

This package contains all Pydantic models for API input/output:
- common: Shared response models and pagination
- auth: Authentication request/response schemas
- document: Document management schemas
- search: Search and Q&A schemas
- admin: Admin operation schemas
- audit: Audit log schemas
"""

from app.schemas.common import (
    PaginatedResponse,
    PaginationParams,
    SuccessResponse,
    ErrorResponse,
)
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserProfile,
)
from app.schemas.document import (
    DocumentCreate,
    DocumentResponse,
    DocumentListResponse,
)
from app.schemas.search import (
    SearchRequest,
    SearchResponse,
    QARequest,
    QAResponse,
)

__all__ = [
    "PaginatedResponse",
    "PaginationParams",
    "SuccessResponse",
    "ErrorResponse",
    "LoginRequest",
    "RegisterRequest",
    "TokenResponse",
    "UserProfile",
    "DocumentCreate",
    "DocumentResponse",
    "DocumentListResponse",
    "SearchRequest",
    "SearchResponse",
    "QARequest",
    "QAResponse",
]
