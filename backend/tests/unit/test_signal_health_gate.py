# =============================================================================
# Stratum AI - Autopilot Signal-Health Gate Tests (TRUST-001)
# =============================================================================
"""
Tests for the execution-time signal-health gate failing CLOSED on no-data.

`check_signal_health` used to `return True` when no signal-health rows existed
for today — but the daily rollup writes PRIOR-day rows, so "today has no rows"
is the normal live-day state, making the gate a no-op that let approved budget
actions execute unverified. It now reads the most recent rollup within a
freshness window and fails closed when none exists.

Pure unit tests — the DB session is mocked (no database).
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.analytics.logic.types import SignalHealthStatus
from app.tasks.apply_actions_queue import check_signal_health


def _db_returning(records):
    """An AsyncSession stub whose execute().scalars().all() yields `records`."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = records
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    return db


def _rec(days_ago: int, status: SignalHealthStatus):
    return SimpleNamespace(
        date=datetime.now(timezone.utc).date() - timedelta(days=days_ago),
        status=status,
    )


async def test_no_recent_data_fails_closed():
    # The core fix: no signal data -> block, do NOT proceed.
    assert await check_signal_health(_db_returning([]), tenant_id=1) is False


async def test_recent_healthy_allows_execution():
    rec = _rec(1, SignalHealthStatus.HEALTHY)
    assert await check_signal_health(_db_returning([rec]), tenant_id=1) is True


async def test_recent_risk_allows_execution():
    rec = _rec(1, SignalHealthStatus.RISK)
    assert await check_signal_health(_db_returning([rec]), tenant_id=1) is True


async def test_recent_degraded_blocks():
    rec = _rec(1, SignalHealthStatus.DEGRADED)
    assert await check_signal_health(_db_returning([rec]), tenant_id=1) is False


async def test_recent_critical_blocks():
    rec = _rec(0, SignalHealthStatus.CRITICAL)
    assert await check_signal_health(_db_returning([rec]), tenant_id=1) is False


async def test_evaluates_latest_date_only():
    # An old degraded reading must not block if the latest rollup is healthy.
    records = [
        _rec(2, SignalHealthStatus.DEGRADED),  # older
        _rec(1, SignalHealthStatus.HEALTHY),  # latest
    ]
    assert await check_signal_health(_db_returning(records), tenant_id=1) is True
