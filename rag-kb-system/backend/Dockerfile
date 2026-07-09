# ═══════════════════════════════════════════════════════════════
# RAG Knowledge Base System - Backend Dockerfile
# ═══════════════════════════════════════════════════════════════
# Multi-stage build for development and production

# ── Base Stage ─────────────────────────────────────────────────
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libmagic1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ── Development Stage ──────────────────────────────────────────
FROM base AS development

COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements-dev.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ── Production Stage ───────────────────────────────────────────
FROM base AS production

COPY requirements.txt ./
RUN pip install -r requirements.txt && \
    pip cache purge

COPY . .

# Create non-root user
RUN groupadd -r rag && useradd -r -g rag -d /app -s /sbin/nologin rag && \
    mkdir -p /app/uploads && \
    chown -R rag:rag /app

USER rag

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "4", "--loop", "uvloop", "--http", "httptools"]
