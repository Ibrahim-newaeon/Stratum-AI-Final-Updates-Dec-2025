# =============================================================================
# Stratum AI - Celery async event-loop hygiene for sync tasks [OPS-01]
# =============================================================================
"""``_run_async`` enters a fresh event loop per task via ``asyncio.run()``.

Two things must happen around that loop, or the worker leaks Postgres
sessions that are ``idle in transaction`` forever:

1. On the way IN, discard connections pooled under a previous task's
   now-closed loop (``dispose_stale_async_pool``).
2. On the way OUT, close the connections opened under THIS loop while the
   loop is still alive. ``asyncio.run()`` closes the loop underneath any
   still-pooled asyncpg sockets, so a transaction that was open at that
   moment is abandoned rather than rolled back: pgbouncer reports
   ``client unexpected eof`` and Postgres keeps the session forever with
   ``BEGIN`` as its last statement. Twenty-five of those exhaust
   pgbouncer's server pool and take the whole product down.

The disposal must happen even when the task fails or times out — the
timeout path is precisely the one that leaves a transaction open, because
``orchestrator.sync_platform`` holds its transaction across external
ad-platform HTTP calls.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.workers.tasks.sync import _run_async


class TestRunAsyncEventLoopHygiene:
    def test_disposes_stale_pool_before_running(self):
        """Connections pooled under a previous task's dead loop are dropped."""

        async def _work():
            return "done"

        with (
            patch("app.db.session.dispose_stale_async_pool", AsyncMock()) as stale,
            patch("app.db.session.async_engine") as engine,
        ):
            engine.dispose = AsyncMock()
            assert _run_async(_work()) == "done"

        stale.assert_awaited_once()

    def test_closes_this_loops_connections_on_success(self):
        """A clean run must not leave sockets bound to the closing loop."""

        async def _work():
            return "done"

        with (
            patch("app.db.session.dispose_stale_async_pool", AsyncMock()),
            patch("app.db.session.async_engine") as engine,
        ):
            engine.dispose = AsyncMock()
            _run_async(_work())

        engine.dispose.assert_awaited_once()

    def test_closes_connections_when_task_raises(self):
        """An erroring task still must not abandon an open transaction."""

        async def _boom():
            raise RuntimeError("ad platform returned 500")

        with (
            patch("app.db.session.dispose_stale_async_pool", AsyncMock()),
            patch("app.db.session.async_engine") as engine,
        ):
            engine.dispose = AsyncMock()
            with pytest.raises(RuntimeError, match="ad platform"):
                _run_async(_boom())

        engine.dispose.assert_awaited_once()

    def test_closes_connections_on_timeout(self):
        """The production trigger: cancelled mid-transaction by the timeout.

        ``sync_platform`` opens its transaction and then awaits external ad
        platform APIs. When one hangs, ``wait_for`` cancels the task with the
        transaction still open. If the engine is not disposed while the loop
        is alive, that transaction is never rolled back and its pgbouncer
        pool slot is consumed permanently.
        """

        async def _hang():
            await asyncio.sleep(30)

        with (
            patch("app.db.session.dispose_stale_async_pool", AsyncMock()),
            patch("app.db.session.async_engine") as engine,
        ):
            engine.dispose = AsyncMock()
            with pytest.raises(asyncio.TimeoutError):
                _run_async(_hang(), timeout_seconds=0.01)

        engine.dispose.assert_awaited_once()
