#!/usr/bin/env python3
"""Populate the Apache AGE knowledge graph from the relational tables.

Migration 065 provisioned AGE, created ``stratum_knowledge_graph`` and its 27
labels. ``feature_knowledge_graph`` stayed off anyway, because provisioned is
not populated: ``KnowledgeGraphSyncService`` had no caller, all 11 KG routes
are GETs, and enabling the flag would have traded a 503 for ``/stats``
reporting zero nodes and ``/insights/problems`` returning ``[]``. "No problems
found" and "no data has ever been loaded" render identically.

This is the writer. Run it once per environment before flipping the flag, and
again after any bulk import.

Usage::

    docker compose exec api python scripts/backfill_knowledge_graph.py --all-tenants
    docker compose exec api python scripts/backfill_knowledge_graph.py --tenant 3 --tenant 7
    docker compose exec api python scripts/backfill_knowledge_graph.py --all-tenants --dry-run

Exit codes: ``0`` everything backfilled, ``1`` at least one tenant failed or
the run wrote nothing at all, ``2`` the graph is not provisioned.

Safe to re-run. Every write goes through ``MERGE`` on
``(tenant_id, external_id)``, so a second pass updates in place rather than
duplicating, and each batch commits -- an interrupted run leaves the work it
had already done behind rather than rolling all of it back.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import func, select, text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.base_models import Tenant  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.session import AsyncSessionLocal  # noqa: E402
from app.services.knowledge_graph.sync import (  # noqa: E402
    SYNC_BATCH_SIZE,
    KnowledgeGraphSyncService,
)

logger = logging.getLogger("backfill_knowledge_graph")

GRAPH_NAME = "stratum_knowledge_graph"
AGE_REVISION = "065_add_age_knowledge_graph"

# Entity kinds in the order full_sync writes them, for a stable report.
ENTITY_ORDER = (
    "profiles",
    "campaigns",
    "segments",
    "events",
    "signals",
    "trust_gates",
    "automations",
    "channels",
    "touchpoints",
)


class GraphNotProvisioned(RuntimeError):
    """The AGE graph does not exist, so there is nothing to write into."""


# =============================================================================
# Preflight
# =============================================================================
async def ensure_graph_provisioned(session: AsyncSession) -> None:
    """Fail before touching a single tenant if the graph is missing.

    ``cypher()`` addresses a *named* graph, and AGE materializes that name as a
    schema. Without it every MERGE raises, so the choice is between one clear
    message here and a stack trace per entity kind per tenant later.

    Checked via ``to_regnamespace`` rather than by reading ``ag_catalog.ag_graph``:
    the catalog's own columns have moved between AGE versions, a schema has
    not.
    """
    result = await session.execute(
        text("SELECT to_regnamespace(:graph)::text"), {"graph": GRAPH_NAME}
    )
    if result.scalar() is None:
        raise GraphNotProvisioned(
            f"graph '{GRAPH_NAME}' does not exist. Run migration {AGE_REVISION} "
            "against a database built from backend/Dockerfile.postgres — the "
            "stock pgvector image does not carry Apache AGE."
        )


# =============================================================================
# Tenant selection
# =============================================================================
async def resolve_tenant_ids(
    session: AsyncSession, requested: Optional[list[int]] = None
) -> list[int]:
    """Return the tenant ids to backfill, verified to exist.

    A requested id that is absent or soft-deleted is dropped with a warning
    rather than silently backfilling nothing under it -- a typo'd id would
    otherwise produce a clean run of all zeros.
    """
    query = select(Tenant.id).where(Tenant.is_deleted.is_(False))
    if requested:
        query = query.where(Tenant.id.in_(requested))

    result = await session.execute(query.order_by(Tenant.id.asc()))
    found = list(result.scalars().all())

    if requested:
        missing = sorted(set(requested) - set(found))
        if missing:
            logger.warning(
                "skipping %d unknown or deleted tenant(s): %s",
                len(missing),
                ", ".join(str(t) for t in missing),
            )
    return found


# =============================================================================
# Counting (for --dry-run)
# =============================================================================
async def count_sources(session: AsyncSession, tenant_id: int) -> dict[str, int]:
    """Count the rows a real run would read, without writing anything."""
    from app.base_models import Campaign
    from app.models.attribution import DailyAttributedRevenue
    from app.models.autopilot import EnforcementAuditLog
    from app.models.cdp import CDPEvent, CDPProfile, CDPSegment
    from app.models.crm import Touchpoint
    from app.models.trust_layer import FactActionsQueue, FactSignalHealthDaily

    # Heterogeneous mapped classes: the shared surface is tenant_id, which
    # no common base declares.
    sources: dict[str, Any] = {
        "profiles": CDPProfile,
        "campaigns": Campaign,
        "segments": CDPSegment,
        "events": CDPEvent,
        "signals": FactSignalHealthDaily,
        "trust_gates": EnforcementAuditLog,
        "automations": FactActionsQueue,
        "channels": DailyAttributedRevenue,
        "touchpoints": Touchpoint,
    }

    counts: dict[str, int] = {}
    for name, model in sources.items():
        query = (
            select(func.count()).select_from(model).where(model.tenant_id == tenant_id)
        )
        if hasattr(model, "is_deleted"):
            query = query.where(model.is_deleted.is_(False))
        counts[name] = int((await session.execute(query)).scalar() or 0)
    return counts


# =============================================================================
# Backfill
# =============================================================================
async def backfill_tenant(
    session: AsyncSession, tenant_id: int, batch_size: int = SYNC_BATCH_SIZE
) -> dict[str, int]:
    """Run a full sync for one tenant and return its per-entity counts."""
    sync = KnowledgeGraphSyncService(session)
    return await sync.full_sync(tenant_id, batch_size=batch_size)


# =============================================================================
# Reporting
# =============================================================================
@dataclass
class Summary:
    """The verdict on a whole run.

    ``ok`` is deliberately false for a run that wrote nothing. Zero is the
    exact outcome the feature flag was held shut to avoid shipping, and a
    "backfill complete" line over a total of 0 reads as success to whoever runs
    it.
    """

    total: int
    ok: bool
    message: str
    failed: list[int] = field(default_factory=list)


def summarize(results: dict[int, Optional[dict[str, int]]]) -> Summary:
    """Reduce per-tenant results to a verdict. ``None`` means that tenant raised."""
    failed = sorted(t for t, counts in results.items() if counts is None)
    total = sum(
        sum(counts.values()) for counts in results.values() if counts is not None
    )
    succeeded = len(results) - len(failed)

    if failed:
        return Summary(
            total=total,
            ok=False,
            message=(
                f"{succeeded} tenant(s) backfilled, {total} entities written; "
                f"{len(failed)} failed: {', '.join(str(t) for t in failed)}"
            ),
            failed=failed,
        )

    if total == 0:
        return Summary(
            total=0,
            ok=False,
            message=(
                f"{succeeded} tenant(s) processed and the run wrote nothing. "
                "An empty graph answers every question with a confident zero, "
                "so this is a failure, not a clean run. Check that the tenants "
                "given actually have CDP/campaign data."
            ),
        )

    return Summary(
        total=total,
        ok=True,
        message=f"{succeeded} tenant(s) backfilled, {total} entities written",
    )


def render_table(results: dict[int, Optional[dict[str, int]]]) -> str:
    """Per-tenant, per-entity counts as a fixed-width table."""
    width = 12
    header = "tenant".rjust(8) + "".join(k.rjust(width) for k in ENTITY_ORDER)
    lines = [header, "-" * len(header)]

    for tenant_id in sorted(results):
        counts = results[tenant_id]
        if counts is None:
            lines.append(str(tenant_id).rjust(8) + "  FAILED".ljust(width))
            continue
        lines.append(
            str(tenant_id).rjust(8)
            + "".join(str(counts.get(k, 0)).rjust(width) for k in ENTITY_ORDER)
        )

    totals = {
        k: sum(c.get(k, 0) for c in results.values() if c is not None)
        for k in ENTITY_ORDER
    }
    lines.append("-" * len(header))
    lines.append(
        "total".rjust(8) + "".join(str(totals[k]).rjust(width) for k in ENTITY_ORDER)
    )
    return "\n".join(lines)


# =============================================================================
# Entry point
# =============================================================================
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Populate the AGE knowledge graph from the relational tables.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--tenant",
        type=int,
        action="append",
        dest="tenants",
        help="Tenant id to backfill. Repeatable.",
    )
    target.add_argument(
        "--all-tenants",
        action="store_true",
        help="Backfill every tenant that is not soft-deleted.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=SYNC_BATCH_SIZE,
        help=f"Rows per round trip and per commit (default {SYNC_BATCH_SIZE}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preflight and count source rows; write nothing.",
    )
    return parser


async def run(args: argparse.Namespace) -> int:
    async with AsyncSessionLocal() as session:
        try:
            await ensure_graph_provisioned(session)
        except GraphNotProvisioned as exc:
            logger.error("%s", exc)
            return 2

        tenant_ids = await resolve_tenant_ids(session, args.tenants)
        if not tenant_ids:
            logger.error("no tenants to backfill")
            return 1

        if not settings.feature_knowledge_graph:
            logger.warning(
                "feature_knowledge_graph is off — the graph will be populated "
                "but the routes stay 503 until the flag is flipped."
            )

        results: dict[int, Optional[dict[str, int]]] = {}
        for tenant_id in tenant_ids:
            started = time.monotonic()
            try:
                if args.dry_run:
                    counts = await count_sources(session, tenant_id)
                else:
                    counts = await backfill_tenant(
                        session, tenant_id, batch_size=args.batch_size
                    )
                results[tenant_id] = counts
                logger.info(
                    "tenant %s: %d entities in %.1fs",
                    tenant_id,
                    sum(counts.values()),
                    time.monotonic() - started,
                )
            except Exception:
                # One tenant's bad row must not abandon the rest. Batches that
                # already committed stay committed; this session is rolled back
                # to a usable state for the next tenant.
                logger.exception("tenant %s failed", tenant_id)
                await session.rollback()
                results[tenant_id] = None

    print(render_table(results))

    summary = summarize(results)
    if args.dry_run:
        print(f"\nDRY RUN — nothing written. {summary.total} source rows would sync.")
        return 0

    print(f"\n{summary.message}")
    return 0 if summary.ok else 1


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    args = build_parser().parse_args()
    return asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
