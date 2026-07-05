# =============================================================================
# Stratum AI - Audience Auto-Sync Task Tests
# =============================================================================
"""
Tests for the scheduled audience-sync sweep (tasks.audience_auto_sync).

The sweep queries due PlatformAudience rows (auto_sync, active,
next_sync_at <= now) and runs each through AudienceSyncService with
triggered_by="schedule". Failures must not abort the sweep and must push
next_sync_at forward so broken audiences are not retried every 15 minutes.
"""

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.tasks.audience_auto_sync import FAILURE_BACKOFF_HOURS, audience_auto_sync


def make_audience(tenant_id: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        tenant_id=tenant_id,
        next_sync_at=datetime.now(UTC) - timedelta(minutes=5),
    )


def run_sweep_with(due_audiences, service_mock):
    """Execute the task eagerly with the session factory and service mocked."""
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = due_audiences
    session.execute = AsyncMock(return_value=result)

    @asynccontextmanager
    async def fake_factory():
        yield session

    with (
        patch("app.tasks.audience_auto_sync.async_session_factory", fake_factory),
        patch("app.db.session.dispose_stale_async_pool", AsyncMock()),
        patch(
            "app.services.cdp.audience_sync.service.AudienceSyncService",
            service_mock,
        ),
    ):
        outcome = audience_auto_sync.apply().get()

    return outcome, session


class TestAudienceAutoSyncSweep:
    def test_no_due_audiences_is_a_noop(self):
        service_cls = MagicMock()

        outcome, _ = run_sweep_with([], service_cls)

        assert outcome == {"status": "success", "synced": 0, "failed": 0}
        service_cls.assert_not_called()

    def test_due_audiences_sync_with_schedule_trigger(self):
        audiences = [make_audience(tenant_id=1), make_audience(tenant_id=2)]
        service = MagicMock()
        service.sync_platform_audience = AsyncMock()
        service_cls = MagicMock(return_value=service)

        outcome, session = run_sweep_with(audiences, service_cls)

        assert outcome == {"status": "success", "synced": 2, "failed": 0}
        assert service.sync_platform_audience.await_count == 2
        for call in service.sync_platform_audience.await_args_list:
            assert call.kwargs["triggered_by"] == "schedule"
        # Service is constructed per audience with that audience's tenant
        assert [c.args[1] for c in service_cls.call_args_list] == [1, 2]
        session.commit.assert_awaited()

    def test_failure_backs_off_and_does_not_abort_sweep(self):
        failing = make_audience(tenant_id=1)
        healthy = make_audience(tenant_id=2)
        before = failing.next_sync_at

        service = MagicMock()
        service.sync_platform_audience = AsyncMock(
            side_effect=[RuntimeError("platform 500"), None]
        )
        service_cls = MagicMock(return_value=service)

        outcome, _ = run_sweep_with([failing, healthy], service_cls)

        assert outcome == {"status": "success", "synced": 1, "failed": 1}
        # Failed audience pushed forward by the backoff, not left due
        assert failing.next_sync_at > before
        assert failing.next_sync_at >= datetime.now(UTC) + timedelta(
            hours=FAILURE_BACKOFF_HOURS, minutes=-1
        )
        # Healthy audience still synced after the failure
        assert service.sync_platform_audience.await_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
