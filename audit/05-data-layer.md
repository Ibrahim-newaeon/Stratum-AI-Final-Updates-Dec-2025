# Phase 5 — Data Layer

## 1. Database

| Item | Value | Evidence |
|------|-------|----------|
| Engine | PostgreSQL 16 + pgvector | `docker-compose.yml:11`, migration 049 |
| Async driver | asyncpg via SQLAlchemy 2.0 | `requirements.txt:21-22` |
| Migrations | 64 Alembic revisions | `backend/migrations/versions/*.py` |
| Latest | 064 widen cdp identifier | `20260817_010000_064_widen_cdp_identifier_value.py` |

## 2. Connection Pooling

```64:69:backend/app/core/config.py
    db_pool_size: int = Field(default=10)
    db_max_overflow: int = Field(default=20)
    db_pool_recycle: int = Field(default=3600)
    db_pool_timeout: int = Field(default=30)
```

**ASSUMPTION:** Total connections = (pool_size + max_overflow) × (API workers + Celery workers + beat). Without production worker counts, cannot compute headroom — confidence LOW. Missing data: Railway/Hetzner Postgres plan limit.

## 3. Row-Level Security

Migrations:
- `032_add_row_level_security.py`
- `034_add_rls_coverage_gaps.py`

Tenant encryption keys: `061_add_tenant_encryption_keys.py` — per-tenant DEK for PII (`security.py:218-224`).

## 4. Model Layer

25 model modules under `backend/app/models/`. CDP model includes webhook `secret_key` column (`models/cdp.py:570` grep).

Tenant scoping pattern: queries filter by `tenant_id` in services; RLS as defense-in-depth.

## 5. Migrations — Safety Patterns

**Search:** `grep -l "op.drop_table\|DROP TABLE" backend/migrations/versions/*.py`

Notable:
- `046_drop_orphaned_autopilot_020_tables.py` — intentional drop with comment
- Merge heads: `25b2d4ee6525_merge_migration_heads.py`, `e21f74be91a2_merge_launch_readiness`

CI runs full `alembic upgrade head` against pgvector image (`ci.yml:145-148`, load-tests `840-842`).

Alembic version column widening handled in `fix_alembic_version.py` / `start.sh` (referenced `docker-compose.yml:200-203`, `ci.yml:835-838`).

## 6. Asset Storage

```391:398:backend/app/core/config.py
    asset_storage_backend: str = Field(
        default="local",
        description='Object storage backend for uploads: "local" or "s3"',
    )
    asset_upload_dir: str = Field(
        default="uploads/assets",
```

Production risk: local backend without mounted volume loses uploads on redeploy — documented in config comments (`config.py:387-390`).

## 7. Data Layer Findings

| ID | Sev | Title |
|----|-----|-------|
| F-012 | P2 | Default asset storage is local filesystem |
| — | — | No automated backup job in compose stack (see Phase 8) |

## 8. Positive Controls

- pgvector parity in CI and compose (`docker-compose.yml:6-10`)
- Per-tenant PII DEK with legacy dual-read migration path (`security.py:256-270`)
- PII decrypt never returns ciphertext on failure (`security.py:280-285`)
- CMS contact PII widening migration 063 (`20260817_000000_063_widen_cms_contact_pii_for_encryption.py`)

## 9. Searches Run

```
glob backend/migrations/versions/*.py  → 64 files
glob backend/app/models/*.py           → 25 files
grep "tenant_id" backend/app/models/cdp.py  → tenant-scoped tables
read config.py db_pool_*, asset_storage_*
```

## 10. Rollback Strategy

**UNKNOWN — not present in available evidence** for automated migration rollback in CI/CD. Manual `alembic downgrade` assumed. `needs_human_review: true`.
