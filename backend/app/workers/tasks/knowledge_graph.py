# =============================================================================
# Stratum AI - Keeping the knowledge graph current
# =============================================================================
"""Incremental sync for the AGE knowledge graph.

``scripts/backfill_knowledge_graph.py`` loads the graph once, by hand. This is
what stops it decaying afterwards: without it the graph drifts further from the
database the longer an environment stays up, while every route keeps answering
confidently from stale nodes — a slower version of the empty-graph problem the
feature was gated for.

**Window, not watermark.** Each run re-syncs a window wider than its own
interval instead of persisting a last-run timestamp. Every write is a MERGE on
``(tenant_id, external_id)``, so reprocessing a row updates it in place and the
overlap costs nothing. A watermark would add state that can be lost, skipped
past, or silently frozen — and a frozen watermark produces a task that runs,
succeeds, and moves nothing, which is precisely the failure shape this codebase
keeps producing.

**Gated on the flag.** The beat entry registers only when
``feature_knowledge_graph`` is on. An environment that has never run the
backfill has an empty graph, and incrementally syncing the last ninety minutes
into it would leave a graph containing only the last ninety minutes — which
reads as a complete graph of a very quiet tenant.
"""

from datetime import UTC, datetime, timedelta

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import select

from app.db.session import SyncSessionLocal, async_session_context
from app.models import Tenant
from app.services.knowledge_graph.sync import KnowledgeGraphSyncService
from app.workers.locks import with_distributed_lock
from app.workers.tasks.sync import _run_async

logger = get_task_logger(__name__)

#: Beat interval. Mirrored in celery_app.py's crontab — keep the two together.
INCREMENTAL_INTERVAL_MINUTES = 30

#: How far back each run re-reads. Deliberately wider than the interval: a
#: window equal to it loses anything written while the previous run was in
#: flight, and MERGE makes the overlap free.
INCREMENTAL_LOOKBACK_MINUTES = 90

#: Per-tenant ceiling. A tenant whose sync cannot finish inside this is a
#: tenant whose incremental window is too small a tool — it needs a backfill,
#: and failing loudly says so rather than silently running long.
PER_TENANT_TIMEOUT_SECONDS = 600


def incremental_window_start() -> datetime:
    """Start of the window this run re-reads, from the wall clock.

    Separate function so the "no stored cursor" property can be asserted
    directly: the value has to move with the clock rather than resume from
    wherever a previous run stopped.
    """
    return datetime.now(tz=UTC) - timedelta(minutes=INCREMENTAL_LOOKBACK_MINUTES)


async def _sync_one(tenant_id: int, since: datetime) -> dict[str, int]:
    async with async_session_context() as session:
        sync = KnowledgeGraphSyncService(session)
        return await sync.incremental_sync(tenant_id, since=since)


@shared_task(name="app.workers.tasks.sync_knowledge_graph_incremental")
@with_distributed_lock(timeout=1800)
def sync_knowledge_graph_incremental() -> dict[str, int]:
    """Re-sync recent changes into the knowledge graph for every active tenant.

    Scheduled by beat behind ``feature_knowledge_graph``. Holds a distributed
    lock because beat fires on every worker and duplicate runs would do the
    same work concurrently against the same graph.

    Returns:
        Counts of tenants processed and failed, plus total entities written.
    """
    since = incremental_window_start()

    with SyncSessionLocal() as db:
        tenant_ids = list(
            db.execute(select(Tenant.id).where(Tenant.is_deleted.is_(False)))
            .scalars()
            .all()
        )

    processed = 0
    failed = 0
    total_entities = 0

    for tenant_id in tenant_ids:
        try:
            # _run_async, never asyncio.run: the async engine's pool is
            # module-level and outlives the loop, so closing the loop under
            # pooled asyncpg sockets leaks a Postgres session every time a
            # transaction is open at teardown. That is the 2026-08-17 outage.
            counts = _run_async(
                _sync_one(tenant_id, since),
                timeout_seconds=PER_TENANT_TIMEOUT_SECONDS,
            )
            processed += 1
            total_entities += sum(counts.values())
        except Exception:
            # One tenant's bad row must not abandon the rest; the batches that
            # already committed stay committed.
            logger.exception(
                "knowledge_graph_incremental_failed tenant_id=%s", tenant_id
            )
            failed += 1

    logger.info(
        "knowledge_graph_incremental_complete tenants=%s failed=%s entities=%s",
        processed,
        failed,
        total_entities,
    )
    return {
        "tenants_processed": processed,
        "tenants_failed": failed,
        "entities_written": total_entities,
    }
