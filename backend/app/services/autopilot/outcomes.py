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


# Phase B knobs. Held as module-level constants so they're easy to tune
# from a runbook without redeploying.
CONSERVATIVE_FACTOR = 0.5
"""Multiplier applied to every estimate before it's stored.

We deliberately under-claim. Showing the user "AT LEAST $1,420" that
turns out to be $2,800 is fine — they're impressed. Showing "$2,800"
that turns out to be $1,420 destroys the nudge's credibility forever.
0.5 is the conservative floor; tighten upward only with ground-truth
backtest data.
"""

PREVENTED_HORIZON_HOURS = 24
"""How far forward to extrapolate prevented spend on a pause action.

24h matches the typical autopilot review cadence — anything paused
for longer than a day is more likely to have been intentionally
killed than to have stayed paused on autopilot's recommendation.
"""

SAVED_HORIZON_DAYS = 7
"""How far forward to extrapolate budget reductions on a decrease action."""

EARNED_HORIZON_DAYS = 7
"""How far forward to extrapolate incremental revenue on a scale-up."""

# Action-type → outcome-type routing. Action strings come from the
# autopilot enforcer (see app/autopilot/enforcer.py) and the campaign
# rules engine (see app/api/v1/endpoints/autopilot_enforcement.py).
_PAUSE_ACTIONS = {"pause", "pause_campaign", "auto_pause", "kill_switch", "disable"}
_DECREASE_ACTIONS = {"budget_decrease", "scale_down"}
_INCREASE_ACTIONS = {"budget_increase", "scale_up"}


def _extract_burn_rate_cents_per_hour(
    current_value: Optional[dict[str, Any]],
    metrics: Optional[dict[str, Any]],
) -> Optional[float]:
    """Best-effort hourly burn rate in cents.

    Looks at current_value first (the live snapshot at decision time),
    then falls back to metrics (the rolling-window aggregate). Returns
    None when neither has enough information.
    """
    for source in (current_value, metrics):
        if not source:
            continue
        # Direct hourly figure if it's already there.
        hourly = source.get("hourly_burn_rate_cents") or source.get("hourly_spend_cents")
        if isinstance(hourly, (int, float)) and hourly > 0:
            return float(hourly)
        # Otherwise convert daily.
        daily = source.get("daily_spend_cents") or source.get("daily_budget_cents")
        if isinstance(daily, (int, float)) and daily > 0:
            return float(daily) / 24.0
    return None


def _extract_roas(metrics: Optional[dict[str, Any]]) -> Optional[float]:
    """Pull ROAS from metrics if available, else None."""
    if not metrics:
        return None
    roas = metrics.get("roas") or metrics.get("avg_roas")
    if isinstance(roas, (int, float)) and roas > 0:
        return float(roas)
    return None


def estimate_outcome(
    action_type: str,
    proposed_value: dict[str, Any],
    current_value: Optional[dict[str, Any]] = None,
    metrics: Optional[dict[str, Any]] = None,
) -> OutcomeEstimate:
    """
    Estimate the dollar value an autopilot decision delivered.

    Conservative linear extrapolation × 0.5 — see CONSERVATIVE_FACTOR.
    The estimator is deterministic and fail-soft: missing inputs
    degrade confidence rather than raise. A return of
    OutcomeEstimate(0, "neutral", "low") means we have no usable
    signal; the nudge consumer should treat that as "no value yet".

    Routing:
        pause / auto_pause / kill_switch
            → prevented spend over PREVENTED_HORIZON_HOURS
        budget_decrease / scale_down
            → saved spend over SAVED_HORIZON_DAYS
        budget_increase / scale_up
            → earned revenue (delta_spend × incremental ROAS)
              over EARNED_HORIZON_DAYS, conservatively assuming
              incremental ROAS ≤ historical ROAS.
        anything else
            → neutral, 0

    Confidence:
        high   — all needed inputs present + a corroborating signal
                 (e.g. ROAS history for an "earned" estimate)
        medium — primary inputs present but limited corroboration
        low    — minimum inputs only or fallback path
    """
    action = (action_type or "").lower().strip()

    # ── Pause: prevented spend ────────────────────────────────────────
    if action in _PAUSE_ACTIONS:
        burn = _extract_burn_rate_cents_per_hour(current_value, metrics)
        if burn is None:
            return OutcomeEstimate(0, "prevented", "low")
        raw = burn * PREVENTED_HORIZON_HOURS * CONSERVATIVE_FACTOR
        confidence: Confidence = "medium" if current_value else "low"
        return OutcomeEstimate(int(raw), "prevented", confidence)

    # ── Budget decrease: saved spend ──────────────────────────────────
    if action in _DECREASE_ACTIONS:
        old_budget = (current_value or {}).get("daily_budget_cents")
        new_budget = (proposed_value or {}).get("daily_budget_cents")
        if (
            isinstance(old_budget, (int, float))
            and isinstance(new_budget, (int, float))
            and old_budget > new_budget >= 0
        ):
            daily_delta = float(old_budget) - float(new_budget)
            raw = daily_delta * SAVED_HORIZON_DAYS * CONSERVATIVE_FACTOR
            return OutcomeEstimate(int(raw), "saved", "medium")
        # Fall back to burn-rate extrapolation when we don't have a
        # clean before/after pair (e.g. partial details payload).
        burn = _extract_burn_rate_cents_per_hour(current_value, metrics)
        if burn is None:
            return OutcomeEstimate(0, "saved", "low")
        raw = burn * 24 * SAVED_HORIZON_DAYS * 0.25 * CONSERVATIVE_FACTOR
        return OutcomeEstimate(int(raw), "saved", "low")

    # ── Budget increase: earned revenue ───────────────────────────────
    if action in _INCREASE_ACTIONS:
        old_budget = (current_value or {}).get("daily_budget_cents")
        new_budget = (proposed_value or {}).get("daily_budget_cents")
        roas = _extract_roas(metrics)
        if (
            isinstance(old_budget, (int, float))
            and isinstance(new_budget, (int, float))
            and new_budget > old_budget
            and roas is not None
        ):
            daily_delta = float(new_budget) - float(old_budget)
            # "Earned" = incremental revenue minus the extra spend.
            # Incremental ROAS is rarely the same as historical ROAS
            # — discount the historical figure further for safety.
            incremental_roas = max(roas - 1.0, 0.0)
            raw = (
                daily_delta
                * incremental_roas
                * EARNED_HORIZON_DAYS
                * CONSERVATIVE_FACTOR
            )
            confidence_e: Confidence = "high" if roas >= 2.0 else "medium"
            return OutcomeEstimate(int(raw), "earned", confidence_e)
        return OutcomeEstimate(0, "earned", "low")

    # ── Anything else: neutral ────────────────────────────────────────
    return OutcomeEstimate(0, "neutral", "low")


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
