# =============================================================================
# Stratum AI - Root Makefile
# =============================================================================
# Delegates to backend/Makefile so commands work from project root.

.DEFAULT_GOAL := help

.PHONY: help dev test test-all test-cov lint format migrate migration check clean

help: ## Show this help message
	@$(MAKE) -C backend help

dev: ## Start local dev server
	@$(MAKE) -C backend dev

test: ## Run unit tests
	@$(MAKE) -C backend test

test-all: ## Run all tests
	@$(MAKE) -C backend test-all

test-cov: ## Run tests with coverage
	@$(MAKE) -C backend test-cov

lint: ## Run linters
	@$(MAKE) -C backend lint

format: ## Auto-format code
	@$(MAKE) -C backend format

migrate: ## Run database migrations
	@$(MAKE) -C backend migrate

migration: ## Create a new migration
	@$(MAKE) -C backend migration msg="$(msg)"

check: ## Run all checks
	@$(MAKE) -C backend check

clean: ## Remove build artifacts
	@$(MAKE) -C backend clean
