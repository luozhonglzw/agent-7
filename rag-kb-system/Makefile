# ═══════════════════════════════════════════════════════════════
# RAG Knowledge Base System - Makefile
# ═══════════════════════════════════════════════════════════════

.PHONY: help dev dev-down prod prod-down logs test lint migrate migrate-up migrate-down seed

# ── Default ────────────────────────────────────────────────────
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Development ────────────────────────────────────────────────
dev: ## Start development environment
	docker compose up -d
	@echo "✅ Development environment started"
	@echo "   Backend:  http://localhost:8000"
	@echo "   Frontend: http://localhost:3000"
	@echo "   API Docs: http://localhost:8000/docs"

dev-down: ## Stop development environment
	docker compose down

dev-logs: ## View development logs
	docker compose logs -f

dev-rebuild: ## Rebuild and restart development environment
	docker compose up -d --build

# ── Production ─────────────────────────────────────────────────
prod: ## Start production environment
	docker compose -f docker-compose.prod.yml up -d --build
	@echo "✅ Production environment started"

prod-down: ## Stop production environment
	docker compose -f docker-compose.prod.yml down

prod-logs: ## View production logs
	docker compose -f docker-compose.prod.yml logs -f

# ── Database ───────────────────────────────────────────────────
migrate: ## Run Alembic migrations (generate new)
	cd backend && alembic revision --autogenerate -m "$(msg)"

migrate-up: ## Apply all migrations
	cd backend && alembic upgrade head

migrate-down: ## Rollback last migration
	cd backend && alembic downgrade -1

migrate-history: ## Show migration history
	cd backend && alembic history

db-shell: ## Connect to PostgreSQL shell
	docker compose exec postgres psql -U rag_user -d rag_kb

# ── Testing ────────────────────────────────────────────────────
test: ## Run all tests
	cd backend && python -m pytest tests/ -v --tb=short --cov=app --cov-report=term-missing

test-unit: ## Run unit tests only
	cd backend && python -m pytest tests/ -v -m "not integration" --tb=short

test-integration: ## Run integration tests only
	cd backend && python -m pytest tests/ -v -m "integration" --tb=short

test-html: ## Generate HTML coverage report
	cd backend && python -m pytest tests/ --cov=app --cov-report=html
	@echo "✅ Coverage report: backend/htmlcov/index.html"

# ── Code Quality ───────────────────────────────────────────────
lint: ## Run linting (ruff)
	cd backend && ruff check app/ tests/
	cd backend && ruff format --check app/ tests/

format: ## Format code (ruff)
	cd backend && ruff format app/ tests/
	cd backend && ruff check --fix app/ tests/

typecheck: ## Run type checking (mypy)
	cd backend && mypy app/ --ignore-missing-imports

# ── Utilities ──────────────────────────────────────────────────
seed: ## Seed admin user
	cd backend && python -m app.services.auth seed-admin

shell: ## Open Python shell in backend container
	docker compose exec backend python

redis-shell: ## Connect to Redis
	docker compose exec redis redis-cli

qdrant-shell: ## Check Qdrant health
	curl -s http://localhost:6333/healthz | python -m json.tool

clean: ## Clean up Docker resources
	docker compose down -v --remove-orphans
	docker system prune -f

# ── Frontend ───────────────────────────────────────────────────
frontend-install: ## Install frontend dependencies
	cd frontend && npm install

frontend-dev: ## Start frontend dev server
	cd frontend && npm run dev

frontend-build: ## Build frontend for production
	cd frontend && npm run build

# ── Documentation ──────────────────────────────────────────────
docs: ## Generate API documentation
	@echo "API docs available at http://localhost:8000/docs"
	@echo "ReDoc available at http://localhost:8000/redoc"
