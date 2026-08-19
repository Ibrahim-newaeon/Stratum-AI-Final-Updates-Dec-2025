# =============================================================================
# Stratum AI - Keeping the knowledge graph current after the backfill
# =============================================================================
"""The backfill is a snapshot; without this task it decays from the moment it ends.

``scripts/backfill_knowledge_graph.py`` loads the graph once, by hand.
``KnowledgeGraphSyncService.incremental_sync`` exists to keep it current and
had no caller — no Celery task, no beat entry — so every environment's graph
would drift further from the database the longer it stayed up, while every
route kept answering confidently from stale nodes.

Three things this pins, each of which has bitten this codebase before:

**The event loop.** Celery tasks are synchronous and this work is async against
the app's own database. ``asyncio.run`` closes its loop under still-pooled
asyncpg sockets, which never send a termination — that is the 2026-08-17
outage, where pgbouncer's pool bled a couple of slots an hour until login died
about a day after a deploy. ``app.workers.tasks.sync._run_async`` is the
sanctioned way through, and this task has to use it rather than reaching for
``asyncio.run`` directly.

**Overlap instead of a watermark.** The task re-syncs a window wider than its
own interval rather than persisting a last-run timestamp. Every write is a
MERGE on (tenant_id, external_id), so re-processing a row updates it in place;
a watermark would add state that can be lost, skipped past, or silently frozen
— and a frozen watermark looks exactly like a working sync.

**The gate.** The beat entry only registers when ``feature_knowledge_graph`` is
on. An environment where the backfill has not run has an empty graph, and
incrementally syncing the last ninety minutes into it would produce a graph
holding only the last ninety minutes — which reads as a complete graph of a
very quiet tenant.
"""

from __future__ import annotations

import ast
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.core.config import settings
from app.workers.celery_app import celery_app

pytestmark = pytest.mark.unit

BACKEND_DIR = Path(__file__).resolve().parents[2]
TASK_MODULE = BACKEND_DIR / "app" / "workers" / "tasks" / "knowledge_graph.py"
CELERY_APP = BACKEND_DIR / "app" / "workers" / "celery_app.py"


def _task_source() -> str:
    return TASK_MODULE.read_text(encoding="utf-8")


# =============================================================================
# The task exists and is registered
# =============================================================================
class TestTaskRegistration:
    def test_the_module_exists(self):
        assert TASK_MODULE.exists(), f"missing {TASK_MODULE}"

    def test_the_task_is_importable_under_its_beat_name(self):
        """The beat entry references a name, and a mismatch dispatches to nothing.

        This module was split out of app/workers/tasks.py, so an auto-generated
        task name gains the submodule segment and silently stops matching —
        the same trap refresh_all_competitors documents.
        """
        from app.workers.tasks import knowledge_graph as kg_tasks

        assert hasattr(kg_tasks, "sync_knowledge_graph_incremental")
        assert "app.workers.tasks.sync_knowledge_graph_incremental" in celery_app.tasks


# =============================================================================
# Event-loop hygiene
# =============================================================================
class TestEventLoopSafety:
    def test_uses_the_sanctioned_runner_not_bare_asyncio_run(self):
        """asyncio.run here is the 2026-08-17 outage.

        The async engine's pool is module-level and outlives the loop, so
        closing the loop underneath pooled asyncpg sockets leaks a Postgres
        session every time a transaction is open at teardown. _run_async
        disposes the pool on both sides of the loop.
        """
        source = _task_source()

        assert "_run_async" in source
        assert "asyncio.run(" not in source

    def test_holds_a_distributed_lock(self):
        """Beat fires on every worker; without a lock they duplicate the work."""
        assert "with_distributed_lock" in _task_source()


# =============================================================================
# Overlap, not a watermark
# =============================================================================
class TestWindow:
    def test_the_lookback_is_wider_than_the_schedule(self):
        """A window equal to the interval loses anything written during a run.

        MERGE makes the overlap free, so the window is deliberately generous.
        """
        from app.workers.tasks.knowledge_graph import (
            INCREMENTAL_INTERVAL_MINUTES,
            INCREMENTAL_LOOKBACK_MINUTES,
        )

        assert INCREMENTAL_LOOKBACK_MINUTES > INCREMENTAL_INTERVAL_MINUTES

    def test_the_window_is_derived_from_the_clock_not_from_stored_state(self):
        """State that can freeze is worse than a window that overlaps.

        A stuck last-run timestamp produces a sync that runs, succeeds and
        moves nothing — the failure shape this whole feature was gated for.

        Asserted behaviourally rather than by grepping the source for
        "watermark": that spelling of the test fails on the docstring
        *explaining* there is no watermark, and would pass for any persisted
        cursor that happened to be named something else.
        """
        from app.workers.tasks.knowledge_graph import (
            INCREMENTAL_LOOKBACK_MINUTES,
            incremental_window_start,
        )

        before = datetime.now(tz=UTC)
        first = incremental_window_start()
        second = incremental_window_start()
        after = datetime.now(tz=UTC)

        lookback = timedelta(minutes=INCREMENTAL_LOOKBACK_MINUTES)
        # Pinned to wall clock at call time, so it advances rather than
        # resuming from wherever a previous run stopped.
        assert before - lookback <= first <= after - lookback
        assert second >= first


# =============================================================================
# The gate
# =============================================================================
class TestBeatGating:
    def test_the_beat_entry_is_registered_behind_the_flag(self):
        """Reading the source, because the flag is off so the entry is absent.

        Asserting on celery_app.conf.beat_schedule would only prove the flag is
        currently False. What matters is that the registration is conditional
        on it at all.
        """
        source = CELERY_APP.read_text(encoding="utf-8")
        tree = ast.parse(source)

        guarded = False
        for node in ast.walk(tree):
            if not isinstance(node, ast.If):
                continue
            test_src = ast.get_source_segment(source, node.test) or ""
            body_src = "\n".join(
                ast.get_source_segment(source, stmt) or "" for stmt in node.body
            )
            if "feature_knowledge_graph" in test_src and "knowledge-graph" in body_src:
                guarded = True

        assert guarded, (
            "the knowledge-graph beat entry must register inside "
            "`if settings.feature_knowledge_graph:` — scheduling it into an "
            "environment that never ran the backfill builds a graph holding "
            "only the last lookback window."
        )

    def test_the_flag_is_still_off_by_default(self):
        """A writer existing is not the same as an environment being populated.

        The flag flips per environment, after the backfill has actually run
        there — not because this task shipped.
        """
        assert settings.feature_knowledge_graph is False
