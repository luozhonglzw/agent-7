"""FastAPI middleware for request processing.

Provides middleware for:
- Request logging with timing
- CORS configuration
- Error handling with unified response format
- Request ID tracking
- Security headers

Usage:
    from app.core.middleware import setup_middleware

    app = FastAPI()
    setup_middleware(app)
"""

import logging
import time
import uuid
from collections.abc import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.exceptions import AppException

logger = logging.getLogger(__name__)


def setup_middleware(app: FastAPI) -> None:
    """Configure all middleware for the application.

    Args:
        app: FastAPI application instance.
    """
    # CORS (must be first)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time"],
    )

    # Custom middleware
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(RequestIDMiddleware)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request.

    Generates a UUID for each request and adds it to response headers.
    If the request already has an X-Request-ID header, it is preserved.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add request ID.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware/handler.

        Returns:
            HTTP response with X-Request-ID header.
        """
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log request details and timing.

    Logs method, path, status code, and processing time for each request.
    Skips health check endpoints to reduce noise.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with timing and logging.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware/handler.

        Returns:
            HTTP response with X-Process-Time header.
        """
        # Skip health check logging
        if request.url.path in ("/health", "/healthz"):
            return await call_next(request)

        start_time = time.perf_counter()
        request_id = getattr(request.state, "request_id", "unknown")

        logger.info(
            "Request started: %s %s [%s]",
            request.method,
            request.url.path,
            request_id,
        )

        response = await call_next(request)

        process_time = time.perf_counter() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.4f}"

        logger.info(
            "Request completed: %s %s [%s] status=%d time=%.4fs",
            request.method,
            request.url.path,
            request_id,
            response.status_code,
            process_time,
        )

        return response


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Global error handler middleware.

    Catches unhandled exceptions and returns unified JSON responses.
    Converts AppException instances to proper API responses.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with error handling.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware/handler.

        Returns:
            HTTP response (error or success).
        """
        try:
            return await call_next(request)

        except AppException as e:
            # Application exceptions with structured error info
            logger.warning(
                "App error: %s %s - [%d] %s",
                request.method,
                request.url.path,
                e.code,
                e.message,
            )
            return JSONResponse(
                status_code=e.status_code,
                content=e.to_dict(),
            )

        except Exception as e:
            # Unexpected exceptions
            request_id = getattr(request.state, "request_id", "unknown")
            logger.exception(
                "Unhandled error: %s %s [%s] - %s",
                request.method,
                request.url.path,
                request_id,
                str(e),
            )

            # Don't expose internal details in production
            detail = str(e) if settings.debug else "Internal server error"

            return JSONResponse(
                status_code=500,
                content={
                    "code": 5000,
                    "message": "Internal server error",
                    "data": {"detail": detail, "request_id": request_id},
                },
            )
