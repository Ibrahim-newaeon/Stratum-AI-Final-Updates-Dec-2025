# Stratum Backend Guide

Follow the root project guide and `.claude/rules/backend.md`. For billing work, also follow `.claude/rules/paddle-billing.md`.

This directory owns FastAPI routes, domain services, SQLAlchemy models, Alembic migrations, Celery tasks, integrations, trust-gate enforcement, and backend tests. Preserve authenticated tenant scope, authorization, auditability, idempotency, asynchronous I/O, and transaction ownership.

Use the root Makefile or backend-declared commands. Run focused tests before the broader affected backend gate.
