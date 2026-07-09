# RAG Knowledge Base System

Enterprise-grade Retrieval-Augmented Generation (RAG) system for knowledge management. Integrates document management, semantic search, and AI-powered Q&A with source citations.

## Features

- **Document Management**: Upload PDF, DOCX, PPT, Markdown, TXT files with automatic parsing and indexing
- **Hybrid Search**: Dense vector search (BGE-M3) + sparse BM25 with Reciprocal Rank Fusion (RRF)
- **Reranking**: Cross-encoder reranking with BGE-Reranker-v2-M3 for improved relevance
- **AI Q&A**: RAG-based question answering with streaming responses and source citations
- **RBAC**: Role-based access control (admin/editor/viewer) with Casbin
- **Audit Trail**: Complete operation logging for compliance
- **Async Processing**: Celery-based background task queue for document processing

## Tech Stack

### Backend
- **Framework**: FastAPI + SQLAlchemy 2.0 + Alembic
- **Task Queue**: Celery + Redis
- **Vector DB**: Qdrant
- **Database**: PostgreSQL 16
- **Embedding**: BAAI/bge-m3
- **Reranker**: BAAI/bge-reranker-v2-m3
- **LLM**: Anthropic-compatible API (mimo-v2-pro)

### Frontend
- **Framework**: Next.js 15 + TypeScript
- **Styling**: Tailwind CSS + shadcn/ui
- **State**: Zustand
- **Markdown**: react-markdown + remark-gfm

## Project Structure

```
rag-kb-system/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API endpoints
│   │   ├── core/            # Core modules (parsers, chunking, retrieval, LLM, security)
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Business logic layer
│   │   └── tasks/           # Celery async tasks
│   ├── alembic/             # Database migrations
│   ├── tests/               # Test suite
│   └── Dockerfile
├── frontend/
│   ├── app/                 # Next.js App Router
│   ├── components/          # React components
│   ├── lib/                 # Utilities and API client
│   ├── hooks/               # Custom React hooks
│   └── types/               # TypeScript type definitions
├── docker-compose.yml       # Development environment
├── docker-compose.prod.yml  # Production environment
├── nginx/nginx.conf         # Reverse proxy config
└── Makefile                 # Development commands
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+ (for local development)
- Node.js 20+ (for frontend development)

### 1. Clone and Configure

```bash
cd rag-kb-system
cp .env.example .env
# Edit .env with your configuration
```

### 2. Start with Docker

```bash
# Start all services
make dev

# Or manually
docker compose up -d
```

Services:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 3. Database Migration

```bash
# Run migrations
make migrate-up
```

### 4. Create Admin User

```bash
make seed
```

## Development

### Backend (Local)

```bash
cd backend

# Install dependencies
pip install -r requirements-dev.txt

# Set environment variables
export $(cat ../.env | xargs)

# Run development server
uvicorn app.main:app --reload

# Run tests
make test

# Run linting
make lint
```

### Frontend (Local)

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run integration tests
make test-integration

# Generate coverage report
make test-html
```

## Deployment

### Production

```bash
# Configure production environment
cp .env.example .env
# Edit .env with production values

# Start production environment
make prod

# View logs
make prod-logs
```

### Environment Variables

See `.env.example` for all configuration options. Key variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_PASSWORD` | Database password | Required |
| `JWT_SECRET_KEY` | JWT signing key | Required |
| `LLM_API_KEY` | LLM API key | Required |
| `QDRANT_API_KEY` | Qdrant API key | Optional |

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend   │────▶│   Nginx     │────▶│   Backend   │
│  (Next.js)   │     │  (Proxy)    │     │  (FastAPI)  │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌──────────────────────────┼──────────────────────┐
                    │                          │                      │
              ┌─────▼─────┐           ┌───────▼───────┐      ┌──────▼──────┐
              │ PostgreSQL │           │    Redis      │      │   Qdrant    │
              │    16      │           │  (Celery)     │      │  (Vectors)  │
              └───────────┘           └───────────────┘      └─────────────┘
```

## License

Proprietary - All rights reserved.
