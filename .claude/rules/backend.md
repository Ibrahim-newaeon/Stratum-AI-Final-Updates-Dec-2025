---
paths:
  - "backend/**"
---

# Backend rules

- Keep HTTP transport in endpoint modules and reusable behavior in services or domain modules.
- Preserve authenticated tenant scope, authorization, audit records, idempotency, rate limits, and transaction ownership.
- Use existing asynchronous SQLAlchemy and I/O patterns; never block the event loop.
- Append Alembic migrations and review generated SQL. Never rewrite applied history.
- Run focused backend tests first, then the applicable lint, type, security, and integration checks.
