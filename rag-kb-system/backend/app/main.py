"""FastAPI application entry point.

Configures the FastAPI application with middleware, routes,
lifecycle events, and health check endpoints.

Usage:
    # Development
    uvicorn app.main:app --reload

    # Production
    uvicorn app.main:app --workers 4 --loop uvloop --http httptools
"""

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.middleware import setup_middleware
from app.api.v1 import api_v1_router
from app.exceptions import AppException

# ── Logging Configuration ──────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan Events ────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.

    Handles startup and shutdown events:
    - Startup: Initialize database, verify connections, create upload dir
    - Shutdown: Close database connections, cleanup resources

    Args:
        app: FastAPI application instance.

    Yields:
        Control to the application.
    """
    logger.info("Starting %s (%s mode)", settings.app_name, settings.app_env)

    # ── Startup ──
    try:
        # Ensure upload directory exists
        settings.storage.upload_path.mkdir(parents=True, exist_ok=True)
        logger.info("Upload directory: %s", settings.storage.upload_path.absolute())

        # Verify database connection
        from app.database import engine
        async with engine.connect() as conn:
            logger.info("Database connection: OK")

        # Verify Redis connection
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis.url)
        await r.ping()
        await r.aclose()
        logger.info("Redis connection: OK")

        logger.info("Application startup complete")

    except Exception as e:
        logger.error("Startup failed: %s", e)
        raise

    yield

    # ── Shutdown ──
    logger.info("Shutting down application...")
    from app.database import close_db
    await close_db()
    logger.info("Application shutdown complete")


# ── FastAPI Application ────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    description=(
        "Enterprise-grade RAG Knowledge Base System. "
        "Provides document management, semantic search, and "
        "LLM-powered question answering with source citations."
    ),
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Health", "description": "Health check endpoints"},
        {"name": "Authentication", "description": "User auth endpoints"},
        {"name": "Documents", "description": "Document management"},
        {"name": "Search & Q&A", "description": "Search and Q&A"},
        {"name": "Admin", "description": "Administrative operations"},
        {"name": "Audit Logs", "description": "Audit trail"},
    ],
)

# ── Middleware ──────────────────────────────────────────────────
setup_middleware(app)

# ── Routes ─────────────────────────────────────────────────────
app.include_router(api_v1_router)


# ── Health Check ───────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check() -> JSONResponse:
    """Application health check.

    Returns basic application status without checking dependencies.
    Used by load balancers and container orchestrators.

    Returns:
        JSON response with application status.
    """
    return JSONResponse(
        content={
            "code": 0,
            "message": "healthy",
            "data": {
                "app": settings.app_name,
                "version": "1.0.0",
                "env": settings.app_env,
            },
        }
    )


@app.get("/health/ready", tags=["Health"])
async def readiness_check() -> JSONResponse:
    """Readiness health check.

    Verifies all dependencies (database, Redis, Qdrant) are accessible.
    Used by Kubernetes readiness probes.

    Returns:
        JSON response with dependency status.
    """
    checks = {}

    # Check database
    try:
        from app.database import engine
        async with engine.connect() as conn:
            checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    # Check Redis
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis.url)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    # Check Qdrant
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"http://{settings.qdrant.host}:{settings.qdrant.port}/healthz",
                timeout=5.0,
            )
            checks["qdrant"] = "ok" if resp.status_code == 200 else f"status: {resp.status_code}"
    except Exception as e:
        checks["qdrant"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "code": 0 if all_ok else 5001,
            "message": "ready" if all_ok else "not ready",
            "data": {"checks": checks},
        },
    )


# ── Global Exception Handlers ──────────────────────────────────
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle application exceptions with unified response format.

    Args:
        request: HTTP request.
        exc: Application exception.

    Returns:
        JSON error response.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )
