"""Common Pydantic schemas for API responses and pagination.

Provides unified response format and pagination parameters
used across all API endpoints.

Response Format:
    {
        "code": 0,       # 0=success, 4000-4999=client error, 5000-5999=server error
        "message": "",   # Human-readable message
        "data": {}       # Response payload
    }
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response wrapper.

    Wraps all successful API responses in a consistent format.

    Attributes:
        code: Always 0 for success.
        message: Success message.
        data: Response payload.
    """

    code: int = Field(default=0, description="Response code (0=success)")
    message: str = Field(default="success", description="Response message")
    data: T | None = Field(default=None, description="Response data")


class ErrorResponse(BaseModel):
    """Standard error response.

    Wraps all error API responses in a consistent format.

    Attributes:
        code: Error code (4000-5999).
        message: Human-readable error message.
        data: Error details.
    """

    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    data: dict[str, Any] | None = Field(default=None, description="Error details")


class PaginationParams(BaseModel):
    """Pagination query parameters.

    Used for list endpoints that support pagination.

    Attributes:
        page: Page number (1-based).
        page_size: Number of items per page.
        sort_by: Field to sort by.
        sort_order: Sort direction (asc/desc).
    """

    page: int = Field(
        default=1,
        ge=1,
        le=10000,
        description="Page number (1-based)",
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Items per page",
    )
    sort_by: str | None = Field(
        default=None,
        max_length=50,
        description="Sort field name",
    )
    sort_order: str = Field(
        default="desc",
        pattern="^(asc|desc)$",
        description="Sort direction",
    )

    @property
    def offset(self) -> int:
        """Calculate SQL offset from page and page_size.

        Returns:
            Number of records to skip.
        """
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response.

    Wraps paginated data with metadata.

    Attributes:
        items: List of items for current page.
        total: Total number of items.
        page: Current page number.
        page_size: Items per page.
        total_pages: Total number of pages.
        has_next: Whether there is a next page.
        has_prev: Whether there is a previous page.
    """

    items: list[T] = Field(default_factory=list, description="Page items")
    total: int = Field(..., ge=0, description="Total item count")
    page: int = Field(..., ge=1, description="Current page")
    page_size: int = Field(..., ge=1, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total pages")
    has_next: bool = Field(default=False, description="Has next page")
    has_prev: bool = Field(default=False, description="Has previous page")


class MessageResponse(BaseModel):
    """Simple message response.

    For endpoints that only return a status message.

    Attributes:
        code: Response code.
        message: Status message.
    """

    code: int = Field(default=0, description="Response code")
    message: str = Field(..., description="Response message")


class IDResponse(BaseModel):
    """ID response for created resources.

    Returned after creating a new resource.

    Attributes:
        code: Response code.
        message: Success message.
        id: UUID of the created resource.
    """

    code: int = Field(default=0, description="Response code")
    message: str = Field(default="created", description="Response message")
    id: str = Field(..., description="Created resource UUID")
