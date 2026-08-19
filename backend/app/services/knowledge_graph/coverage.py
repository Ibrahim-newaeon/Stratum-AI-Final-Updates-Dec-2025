# =============================================================================
# Stratum AI - What the knowledge graph can and cannot answer
# =============================================================================
"""One place that says which graph relationships have no writer.

The backfill (``scripts/backfill_knowledge_graph.py`` driving
``KnowledgeGraphSyncService``) populates eight node labels and three edge
types. The read path traverses five more edge types and two more node labels.
That gap is not a missing loop in the backfill — the relationships are absent
from the relational schema, so there is nothing to copy:

``TrustGate -> Automation`` (BLOCKED / TRIGGERED)
    ``enforcement_audit_logs`` records ``(entity_type, entity_id, action_type,
    timestamp)`` — the *platform* entity, e.g. a campaign id — and has no FK to
    ``fact_actions_queue``. ``AutopilotEnforcer.check_action`` runs as a
    pre-flight check on a *proposed* action, so the queue row does not exist
    yet and its id is not in scope to record. Joining on ``(entity_id,
    action_type)`` within a time window would guess which automation a gate
    blocked whenever a tenant touched the same campaign twice in one day, and
    an edge asserting causation we have not established is worse than no edge.

``Signal -> TrustGate`` (EVALUATED_BY)
    ``fact_signal_health_daily`` is keyed ``(tenant, platform, date)``;
    ``enforcement_audit_logs`` has no platform column. Nothing identifies which
    signal informed a given gate.

``Revenue -> Channel`` (ATTRIBUTED_TO, DROVE) and Channel / Touchpoint nodes
    Unlike the two above, the sources exist — ``conversion_paths``,
    ``channel_interactions``, ``daily_attributed_revenue``. They are simply not
    loaded yet, so this gap closes with a backfill change rather than a schema
    change.

Why this file exists at all: after a *successful* backfill these surfaces
return ``[]``. "No automations were blocked" and "we never loaded the edge that
would show one" render identically, which is exactly the condition
``feature_knowledge_graph`` was held shut to avoid. Declaring the gap costs a
501. Hiding it costs trust in every number on the page.

When a gap closes, delete its entry — the tests in
``test_knowledge_graph_coverage.py`` name the keys, so a stale entry fails
loudly rather than quietly suppressing a surface that now works.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from fastapi import HTTPException, status

# Edge types the batch backfill actually creates. Anything a query traverses
# that is not in here returns nothing, however healthy the graph looks.
BACKFILLED_EDGES = frozenset({"PERFORMED", "GENERATED", "BELONGS_TO"})


@dataclass(frozen=True)
class CoverageGap:
    """A surface that cannot be answered, and precisely why."""

    key: str
    reason: str
    requires: tuple[str, ...]
    #: True when the data exists and only the loader is missing, False when the
    #: linkage is absent from the schema itself. Governs how expensive the fix
    #: is, so it is worth stating rather than leaving a reader to infer.
    blocked_on_schema: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "reason": self.reason,
            "requires": list(self.requires),
            "blocked_on_schema": self.blocked_on_schema,
        }


_TRUST_GATE_LINKAGE = (
    "Requires a trust-gate to action linkage that the schema does not carry: "
    "enforcement_audit_logs records the platform entity (entity_type, "
    "entity_id, action_type) with no foreign key to fact_actions_queue, and "
    "the enforcer runs before the queue row exists. Matching on entity and "
    "action within a time window would guess which automation a gate blocked."
)

_SIGNAL_LINKAGE = (
    "Requires a signal to trust-gate linkage that the schema does not carry: "
    "fact_signal_health_daily is keyed (tenant, platform, date) and "
    "enforcement_audit_logs has no platform column, so nothing identifies "
    "which signal informed a given gate decision."
)

_ATTRIBUTION_LOAD = (
    "Requires attribution touchpoints and channels to be loaded into the "
    "graph. The sources exist (conversion_paths, channel_interactions, "
    "daily_attributed_revenue) but the backfill does not yet write Channel or "
    "Touchpoint nodes or the ATTRIBUTED_TO / DROVE edges between them."
)


GAPS: dict[str, CoverageGap] = {
    "blocked_automations": CoverageGap(
        key="blocked_automations",
        reason=_TRUST_GATE_LINKAGE,
        requires=("TrustGate-[:BLOCKED]->Automation",),
        blocked_on_schema=True,
    ),
    "automation_trace": CoverageGap(
        key="automation_trace",
        reason=f"{_TRUST_GATE_LINKAGE} {_SIGNAL_LINKAGE}",
        requires=(
            "Signal-[:EVALUATED_BY]->TrustGate",
            "TrustGate-[:TRIGGERED|BLOCKED]->Automation",
            "Automation-[:PRODUCED]->Revenue",
        ),
        blocked_on_schema=True,
    ),
    "trust_gate_bottlenecks": CoverageGap(
        key="trust_gate_bottlenecks",
        reason=_TRUST_GATE_LINKAGE,
        requires=("TrustGate-[:BLOCKED]->Automation",),
        blocked_on_schema=True,
    ),
    "revenue_by_channel": CoverageGap(
        key="revenue_by_channel",
        reason=_ATTRIBUTION_LOAD,
        requires=("Revenue-[:ATTRIBUTED_TO]->Channel", "Touchpoint nodes"),
        blocked_on_schema=False,
    ),
    "channel_inefficiency": CoverageGap(
        key="channel_inefficiency",
        reason=_ATTRIBUTION_LOAD,
        requires=("Revenue-[:ATTRIBUTED_TO]->Channel", "Channel nodes"),
        blocked_on_schema=False,
    ),
    # Partial, and the distinction matters: _detect_revenue_decline itself
    # works — it compares revenue across two windows over Event/Revenue nodes
    # the backfill does write. Only its root-cause enrichment
    # (_trace_revenue_decline_cause) traverses Campaign-[:DROVE]->Revenue, so a
    # decline is still reported, without the campaign attribution behind it.
    "revenue_decline_root_cause": CoverageGap(
        key="revenue_decline_root_cause",
        reason=(
            f"{_ATTRIBUTION_LOAD} Revenue decline is still detected; only the "
            "per-campaign attribution behind it is unavailable."
        ),
        requires=("Campaign-[:DROVE]->Revenue",),
        blocked_on_schema=False,
    ),
    # Not reachable from any route today — these service methods have no
    # endpoint. Declared anyway so wiring one up surfaces the gap immediately
    # rather than shipping a surface that returns [].
    "channel_transitions": CoverageGap(
        key="channel_transitions",
        reason=_ATTRIBUTION_LOAD,
        requires=("Profile-[:RECEIVED]->Touchpoint", "Touchpoint nodes"),
        blocked_on_schema=False,
    ),
    "multi_touch_paths": CoverageGap(
        key="multi_touch_paths",
        reason=_ATTRIBUTION_LOAD,
        requires=("Profile-[:RECEIVED]->Touchpoint", "Touchpoint nodes"),
        blocked_on_schema=False,
    ),
}

#: Insight detectors that cannot produce findings. Reported alongside the
#: problems that *can* be detected, so an empty category is never mistaken for
#: a clean bill of health.
_DETECTOR_KEYS = (
    "blocked_automations",
    "trust_gate_bottlenecks",
    "channel_inefficiency",
)


def require_supported(key: str, strict: bool = False) -> None:
    """Raise 501 if ``key`` names a surface the graph cannot answer.

    501 rather than 404 (the tenant and the automation exist), 503 (nothing is
    temporarily unavailable) or 200 with an empty body (the lie this module
    exists to prevent).

    Args:
        key: Surface identifier, matching a key in ``GAPS``.
        strict: Raise KeyError for an unrecognised key instead of treating it
            as supported. Used by tests to catch typos, which would otherwise
            silently wave a broken surface through.
    """
    gap = GAPS.get(key)
    if gap is None:
        if strict and key not in _SUPPORTED_KEYS:
            raise KeyError(f"unknown knowledge-graph surface: {key!r}")
        return None

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=gap.reason,
    )


#: Surfaces known to work, so `strict` can tell "supported" from "misspelled".
_SUPPORTED_KEYS = frozenset(
    {
        "health_summary",
        "problems",
        "problem_detail",
        "revenue_by_segment",
        "customer_journey",
        "graph_stats",
        "health_check",
    }
)


def unavailable_detectors() -> tuple[str, ...]:
    """Detector keys that cannot produce findings."""
    return _DETECTOR_KEYS


def unavailable_report() -> list[dict[str, Any]]:
    """The detector gaps, shaped for an API response."""
    return [GAPS[key].as_dict() for key in _DETECTOR_KEYS]


def gap_for(key: str) -> Optional[CoverageGap]:
    return GAPS.get(key)
