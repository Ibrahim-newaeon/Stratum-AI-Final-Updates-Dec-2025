# =============================================================================
# Stratum AI - CAPI Dead Letter Queue Postgres persistence tests (CAPI-001)
# =============================================================================
"""
Failed CAPI events must land durably in Postgres (capi_dead_letter_queue), not
only in the Redis/in-memory working set, and the send path must actually feed
them there. Two halves are covered:

1. DeadLetterQueue.add_failed_event -> _persist_to_db writes a CAPIDeadLetterEntry.
2. CAPIService._dlq_failed_events enqueues only the platforms that failed.
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.capi.capi_service import CAPIService
from app.services.capi.dead_letter_queue import DeadLetterQueue
from app.services.capi.platform_connectors import CAPIResponse


def _fake_session_factory(db):
    @asynccontextmanager
    async def _factory():
        yield db

    return _factory


@pytest.mark.asyncio
async def test_add_failed_event_persists_to_postgres():
    db = MagicMock()
    db.merge = AsyncMock()
    db.commit = AsyncMock()

    dlq = DeadLetterQueue()  # not connected to Redis -> memory + Postgres
    with patch(
        "app.services.capi.dead_letter_queue.async_session_factory",
        new=_fake_session_factory(db),
    ):
        entry = await dlq.add_failed_event(
            tenant_id=42,
            platform="meta",
            event_name="Purchase",
            event_data={"event_id": "evt-1", "event_name": "Purchase"},
            error_message="connection reset",
        )

    db.merge.assert_awaited_once()
    db.commit.assert_awaited_once()
    persisted = db.merge.call_args.args[0]
    assert persisted.tenant_id == 42
    assert persisted.platform == "meta"
    assert persisted.event_id == "evt-1"
    assert persisted.status == "pending"
    # failure category is derived, not raw
    assert persisted.failure_category == "network_error"
    assert persisted.id == entry.id


@pytest.mark.asyncio
async def test_persist_failure_does_not_raise():
    db = MagicMock()
    db.merge = AsyncMock(side_effect=OSError("db down"))
    db.commit = AsyncMock()

    dlq = DeadLetterQueue()
    with patch(
        "app.services.capi.dead_letter_queue.async_session_factory",
        new=_fake_session_factory(db),
    ):
        # Must not raise even though Postgres write fails.
        entry = await dlq.add_failed_event(
            tenant_id=1,
            platform="google",
            event_name="Lead",
            event_data={},
            error_message="boom",
        )
    assert entry.tenant_id == 1


@pytest.mark.asyncio
async def test_dlq_failed_events_enqueues_only_failures():
    svc = CAPIService(tenant_id=7)
    events = [{"event_name": "Purchase", "event_id": "a"}]
    results = [
        ("meta", CAPIResponse(True, 1, 1, [], "meta"), 12.0),
        (
            "google",
            CAPIResponse(False, 1, 0, [{"message": "auth expired"}], "google"),
            9.0,
        ),
    ]

    fake_dlq = MagicMock()
    fake_dlq.add_failed_event = AsyncMock()
    with patch(
        "app.services.capi.dead_letter_queue.get_dlq",
        new=AsyncMock(return_value=fake_dlq),
    ):
        await svc._dlq_failed_events(events, results)

    # Only the failing platform (google) is enqueued; meta (success) is skipped.
    fake_dlq.add_failed_event.assert_awaited_once()
    kwargs = fake_dlq.add_failed_event.call_args.kwargs
    assert kwargs["platform"] == "google"
    assert kwargs["tenant_id"] == 7
    assert "auth expired" in kwargs["error_message"]


@pytest.mark.asyncio
async def test_dlq_capture_never_raises():
    svc = CAPIService(tenant_id=7)
    events = [{"event_name": "Purchase"}]
    results = [("meta", CAPIResponse(False, 1, 0, [], "meta"), 1.0)]

    with patch(
        "app.services.capi.dead_letter_queue.get_dlq",
        new=AsyncMock(side_effect=RuntimeError("redis gone")),
    ):
        # Swallowed — a DLQ failure must not fail the send.
        await svc._dlq_failed_events(events, results)
