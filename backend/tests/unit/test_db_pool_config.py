# =============================================================================
# Stratum AI - DB connection pool config test (DB-001)
# =============================================================================
"""
Both the async (API) and sync (Celery/migrations) engines must apply a bounded
pool_timeout so that pool exhaustion raises promptly instead of blocking the
request/task forever, and must honor the configured pool sizing.
"""

import pytest

from app.core.config import settings
from app.db.session import async_engine, sync_engine

pytestmark = pytest.mark.unit


def test_sync_engine_has_pool_timeout():
    assert sync_engine.pool._timeout == settings.db_pool_timeout


def test_async_engine_has_pool_timeout():
    assert async_engine.pool._timeout == settings.db_pool_timeout


def test_pool_timeout_is_bounded():
    # A finite, positive timeout — never block indefinitely on exhaustion.
    assert 0 < settings.db_pool_timeout <= 120


def test_engines_honor_configured_pool_size():
    assert sync_engine.pool.size() == settings.db_pool_size
