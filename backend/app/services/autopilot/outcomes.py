# =============================================================================
# Stratum AI — Autopilot Outcomes Service
# =============================================================================
"""
Outcome estimation + rollup for autopilot decisions.

Phase A (this file):
    Stub estimator that always returns OutcomeEstimate(value_cents=0,
    type="neutral", confidence="low"). The schema, endpoint, and frontend
    nudge wire through end-to-end so the system is ready for Phase B.

Phase B (next):
    Counterfactual computation. For pause-type actions:
        value_cents = pre_pause_burn_rate_per_hour * hours_paused
                      * conservative_factor (0.5)
    For scale-type actions:
        value_cents = (post_scale_revenue - pre_scale_revenue) per hour
                      * hours_active * conservative_factor (0.5)
    Conservative factor exists because over-claiming destroys trust.
    Better to surface "AT LEAST $1,420" that's truly $2,800 than
    "$2,800" that turns out to be $1,420.

The rollup query is shape-stable across phases — Phase B only changes
how value_cents gets populated; the rollup math doesn't move.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.autopilot import EnforcementAuditLog

logger = get_logger(__name__)


# =============================================================================
# Types
# =============================================================================

OutcomeType = str  # "saved" | "earned" | "prevented" | "neutral"
Confidence = str  # "low" | "medium" | "high"


@dataclass
class OutcomeEstimate:
    """Estimated outcome for a single autopilot decision."""

    value_cents: int
    outcome_type: OutcomeType
    confidence: Confidence


@dataclass
class OutcomeSummary:
    """Aggregate outcome over a period for a tenant."""

    period_start: datetime
    period_end: datetime
    total_value_cents: int
    decisions_count: int
    saved_cents: int
    earned_cents: int
    prevented_cents: int
    confidence_breakdown: dict[Confidence, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_value_cents": self.total_value_cents,
            "decisions_count": self.decisions_count,
            "saved_cents": self.saved_cents,
            "earned_cents": self.earned_cents,
            "prevented_cents": self.prevented_cents,
            "confidence_breakdown": self.confidence_breakdown,
        }


# =============================================================================
# Estimator (Phase A: stub)
# =============================================================================


def estimate_outcome(
    action_type: str,
    proposed_value: dict[str, Any],
    current_value: Optional[dict[str, Any]] = None,
    metrics: Optional[dict[str, Any]] = None,
) -> OutcomeEstimate:
    """
    Estimate the dollar value an autopilot decision delivered.

    Phase A returns a sentinel OutcomeEstimate(0, "neutral", "low") —
    real-time estimation lands in Phase B once we have ground-truth
    counterfactual data from a few real customers.

    Returning a non-None estimate (rather than NULL) means the
    nudge eligibility check still rejects this row (`value_cents < min`)
    so users don't see misleading $0 nudges. The column gets populated
    with 0 instead of NULL so future Phase B reconciliation jobs can
    distinguish "computed but no value" from "never computed".
    """
    # Suppress unused-arg warnings while keeping the signature stable
    # for Phase B.
    del action_type, proposed_value, current_value, metrics

    return OutcomeEstimate(
        value_cents=0,
        outcome_type="neutral",
        confidence="low",
    )


# =============================================================================
# Rollup
# =============================================================================


async def get_outcome_summary(
    db: AsyncSession,
    tenant_id: int,
    period: str = "7d",
) -> OutcomeSummary:
    """
    Aggregate autopilot outcomes for a tenant over a period.

    Args:
        db: Async DB session
        tenant_id: Tenant to aggregate for
        period: '24h' | '7d' | '30d' (defaults to 7d — the granularity
                that matches the weekly nudge cadence)

    Returns:
        OutcomeSummary with totals + counts. When no rows match, every
        numeric field is 0 — the frontend reads `decisions_count == 0`
        as "no nudge yet, don't render".
    """
    period_end = datetime.now(timezone.utc)
    period_days = {"24h": 1, "7d": 7, "30d": 30}.get(period, 7)
    period_start = period_end - timedelta(days=period_days)

    # Single aggregate query — much cheaper than fetching rows + summing
    # in Python on a populated tenant.
    stmt = select(
        func.coalesce(func.sum(EnforcementAuditLog.value_delivered_cents), 0).label("total"),
        func.count(EnforcementAuditLog.id).label("count"),
        func.coalesce(
            func.sum(
                func.coalesce(EnforcementAuditLog.value_delivered_cents, 0)
            ).filter(EnforcementAuditLog.outcome_type == "saved"),
            0,
        ).label("saved"),
        func.coalesce(
            func.sum(
                func.coalesce(EnforcementAuditLog.value_delivered_cents, 0)
            ).filter(EnforcementAuditLog.outcome_type == "earned"),
            0,
        ).label("earned"),
        func.coalesce(
            func.sum(
                func.coalesce(EnforcementAuditLog.value_delivered_cents, 0)
            ).filter(EnforcementAuditLog.outcome_type == "prevented"),
            0,
        ).label("prevented"),
    ).where(
        EnforcementAuditLog.tenant_id == tenant_id,
        EnforcementAuditLog.timestamp >= period_start,
        EnforcementAuditLog.timestamp <= period_end,
    )

    result = await db.execute(stmt)
    row = result.one()

    # Confidence breakdown — separate query because filter+group is
    # awkward in a single SELECT and the result set is tiny (≤3 rows).
    breakdown_stmt = (
        select(
            EnforcementAuditLog.outcome_confidence,
            func.count(EnforcementAuditLog.id),
        )
        .where(
            EnforcementAuditLog.tenant_id == tenant_id,
            EnforcementAuditLog.timestamp >= period_start,
            EnforcementAuditLog.timestamp <= period_end,
            EnforcementAuditLog.outcome_confidence.is_not(None),
        )
        .group_by(EnforcementAuditLog.outcome_confidence)
    )
    breakdown_result = await db.execute(breakdown_stmt)
    confidence_breakdown: dict[str, int] = {
        conf: count for conf, count in breakdown_result.all() if conf
    }

    return OutcomeSummary(
        period_start=period_start,
        period_end=period_end,
        total_value_cents=int(row.total or 0),
        decisions_count=int(row.count or 0),
        saved_cents=int(row.saved or 0),
        earned_cents=int(row.earned or 0),
        prevented_cents=int(row.prevented or 0),
        confidence_breakdown=confidence_breakdown,
    )
