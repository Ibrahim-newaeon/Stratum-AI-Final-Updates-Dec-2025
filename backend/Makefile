# =============================================================================
# Stratum AI - Backend Makefile
# =============================================================================

.DEFAULT_GOAL := help

.PHONY: help dev test test-all test-cov lint format migrate migration check clean

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

dev: ## Start local dev server with hot reload
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test: ## Run unit tests
	pytest tests/unit -v --tb=short -m "unit or not integration"

test-all: ## Run all tests (unit + integration)
	pytest tests/ -v --tb=short

test-cov: ## Run tests with coverage report
	pytest tests/unit --cov=app --cov-config=.coveragerc --cov-report=term-missing --cov-report=html -m "unit or not integration"

lint: ## Run ruff linter and mypy type checker
	ruff check app/
	mypy app/ --ignore-missing-imports

format: ## Auto-format code with ruff and black
	ruff check app/ --fix
	black app/ tests/
	isort app/ tests/

migrate: ## Run database migrations
	alembic upgrade head

migration: ## Create a new migration (usage: make migration msg="description")
	alembic revision --autogenerate -m "$(msg)"

check: ## Run all checks (lint + test)
	$(MAKE) lint
	$(MAKE) test

clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov .coverage coverage.xml
