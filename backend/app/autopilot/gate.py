# =============================================================================
# Stratum AI - Canonical execution gate
# =============================================================================
"""One place that decides whether automation may execute for a tenant.

Before this module there were four hand-rolled variants of the same decision,
and they disagreed:

* ``tasks.apply_actions_queue.check_signal_health`` — correct: reads the
  tenant's rollup, fails closed on missing data.
* ``stratum.workers.automation_runner.execute_action`` — blocked only below 40,
  executing through the 40-69 DEGRADED band that policy says to hold, and
  trusted a health score handed to it by its caller rather than measuring one.
* ``workers.tasks.rules._execute_action`` — no gate at all.
* ``stratum.mcp`` — returned APPROVED unconditionally (removed in #642).

Each new execution path re-derived the rules and got them slightly wrong. The
fix is not to patch each call site but to give them one function to call, so a
fifth path inherits the decision instead of reinventing it.

Thresholds come from CLAUDE.md's Trust Engine Rules and are the single source
of truth:

    HEALTHY  >= 70   autopilot enabled
    DEGRADED 40-69   alert + hold  (NOT executable)
    UNHEALTHY < 40   manual intervention required

Both flavours fail **closed**: absent, stale, or unreadable signal data blocks
execution rather than assuming health.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.trust_layer import FactSignalHealthDaily, SignalHealthStatus

logger = logging.getLogger(__name__)


# Trust Engine thresholds (CLAUDE.md). Do not fork these.
HEALTHY_THRESHOLD = 70
DEGRADED_THRESHOLD = 40

# Autopilot must not execute on stale or absent signal data. The daily rollup
# writes PRIOR-day rows, so today has none during the live day; read the most
# recent rollup inside this window and fail closed when there is none.
SIGNAL_HEALTH_FRESHNESS_DAYS = 2

# Statuses that block execution. DEGRADED is included deliberately: policy is
# "alert + hold", and holding means not executing.
BLOCKING_STATUSES = (SignalHealthStatus.DEGRADED, SignalHealthStatus.CRITICAL)


@dataclass(frozen=True)
class GateDecision:
    """Outcome of an execution gate evaluation."""

    allowed: bool
    reason: Optional[str] = None

    def __bool__(self) -> bool:  # pragma: no cover - convenience only
        return self.allowed


def _blocked(reason: str, tenant_id: int) -> GateDecision:
    logger.warning(
        "execution_gate_blocked", extra={"tenant_id": tenant_id, "reason": reason}
    )
    return GateDecision(allowed=False, reason=reason)


def _freshness_cutoff():
    return datetime.now(timezone.utc).date() - timedelta(
        days=SIGNAL_HEALTH_FRESHNESS_DAYS
    )


def _decide_from_records(records, tenant_id: int) -> GateDecision:
    """Shared verdict logic for both the async and sync flavours."""
    if not records:
        return _blocked(
            "No signal health rollup within the freshness window", tenant_id
        )

    # Per-platform rows share a date; evaluate only the most recent one.
    latest_date = max(record.date for record in records)
    for record in records:
        if record.date != latest_date:
            continue
        if record.status in BLOCKING_STATUSES:
            return _blocked(f"Signal health {record.status}", tenant_id)

    return GateDecision(allowed=True)


async def evaluate_signal_health(db: AsyncSession, tenant_id: int) -> GateDecision:
    """Signal-health verdict only — deliberately no freeze check.

    Kept separate because callers that already consult the freeze themselves
    need exactly this and nothing more. Folding the freeze in here silently
    widened what ``check_signal_health`` does: its unit tests mock a single
    ``db.execute``, so the extra query returned a truthy MagicMock and blocked
    healthy tenants. A function that says it checks signal health should issue
    one query and answer that question.
    """
    records = (
        (
            await db.execute(
                select(FactSignalHealthDaily).where(
                    and_(
                        FactSignalHealthDaily.tenant_id == tenant_id,
                        FactSignalHealthDaily.date >= _freshness_cutoff(),
                    )
                )
            )
        )
        .scalars()
        .all()
    )

    return _decide_from_records(records, tenant_id)


async def evaluate_execution_gate(db: AsyncSession, tenant_id: int) -> GateDecision:
    """Full gate: emergency freeze, then signal health. Fails closed on both.

    For callers that own the whole decision. Paths that already check the
    freeze separately should call :func:`evaluate_signal_health`.
    """
    from app.models.autopilot import TenantEnforcementSettings

    frozen = (
        await db.execute(
            select(TenantEnforcementSettings.autopilot_frozen).where(
                TenantEnforcementSettings.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()

    if bool(frozen):
        return _blocked("Autopilot is frozen for this tenant", tenant_id)

    return await evaluate_signal_health(db, tenant_id)


def evaluate_execution_gate_sync(db: Session, tenant_id: int) -> GateDecision:
    """Synchronous flavour, for Celery tasks that run on ``SyncSessionLocal``.

    Deliberately mirrors :func:`evaluate_execution_gate` rather than wrapping it
    — spinning an event loop inside a sync worker to reuse the async version
    causes more problems than the duplication saves. The verdict logic itself is
    shared through ``_decide_from_records``, so the two cannot drift on the part
    that matters.
    """
    from app.models.autopilot import TenantEnforcementSettings

    frozen = (
        db.execute(
            select(TenantEnforcementSettings.autopilot_frozen).where(
                TenantEnforcementSettings.tenant_id == tenant_id
            )
        )
        .scalars()
        .first()
    )

    if bool(frozen):
        return _blocked("Autopilot is frozen for this tenant", tenant_id)

    records = (
        db.execute(
            select(FactSignalHealthDaily).where(
                and_(
                    FactSignalHealthDaily.tenant_id == tenant_id,
                    FactSignalHealthDaily.date >= _freshness_cutoff(),
                )
            )
        )
        .scalars()
        .all()
    )

    return _decide_from_records(records, tenant_id)
