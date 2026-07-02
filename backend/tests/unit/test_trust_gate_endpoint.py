# =============================================================================
# Stratum AI - Trust Gate Endpoint Adapter Tests
# =============================================================================
"""Unit tests for the FactSignalHealthDaily → stratum SignalHealth adapter
behind GET /trust/tenant/{id}/trust-gate and POST .../trust-gate/evaluate.

The adapter is the seam between the rolled-up daily table and the real
trust-gate engine; these lock in the safety default (no data blocks
automation) and the row mapping (EMQ rescale, worst-platform freshness).
"""

import pytest

from app.api.v1.endpoints.trust_layer import _signal_health_from_rows
from app.stratum.core.trust_gate import GateDecision, TrustGate, get_autopilot_mode
from app.stratum.models import AutomationAction, Platform

pytestmark = pytest.mark.unit


class _Row:
    """Minimal stand-in for a FactSignalHealthDaily row."""

    def __init__(self, emq_score=None, freshness_minutes=None):
        self.emq_score = emq_score
        self.freshness_minutes = freshness_minutes


def test_no_rows_is_critical_and_frozen():
    """Unknown data quality must never wave automation through."""
    health = _signal_health_from_rows([])

    assert health.overall_score == 0.0
    assert health.status == "critical"
    assert health.issues

    mode, _reason = get_autopilot_mode(health)
    assert mode == "frozen"

    result = TrustGate().evaluate(
        health,
        AutomationAction(
            platform=Platform.META,
            account_id="",
            entity_type="campaign",
            entity_id="camp-1",
            action_type="increase_budget",
        ),
    )
    assert result.decision == GateDecision.BLOCK


def test_healthy_rows_produce_healthy_composite():
    rows = [
        _Row(emq_score=90.0, freshness_minutes=15),
        _Row(emq_score=85.0, freshness_minutes=30),
    ]
    health = _signal_health_from_rows(rows)

    assert health.status == "healthy"
    assert health.overall_score >= 70
    # EMQ is rescaled from the 0-100 daily rows to the calculator's 0-10
    # input and back — a healthy input must stay healthy, not collapse.
    assert health.emq_score >= 80


def test_stale_data_degrades_freshness_component():
    fresh = _signal_health_from_rows([_Row(emq_score=90.0, freshness_minutes=10)])
    stale = _signal_health_from_rows([_Row(emq_score=90.0, freshness_minutes=2000)])

    assert stale.freshness_score < fresh.freshness_score
    assert stale.overall_score < fresh.overall_score


def test_worst_platform_freshness_wins():
    """One stale platform should drag the composite, not be averaged away."""
    mixed = _signal_health_from_rows(
        [
            _Row(emq_score=90.0, freshness_minutes=10),
            _Row(emq_score=90.0, freshness_minutes=2000),
        ]
    )
    all_fresh = _signal_health_from_rows(
        [
            _Row(emq_score=90.0, freshness_minutes=10),
            _Row(emq_score=90.0, freshness_minutes=30),
        ]
    )
    assert mixed.freshness_score < all_fresh.freshness_score
