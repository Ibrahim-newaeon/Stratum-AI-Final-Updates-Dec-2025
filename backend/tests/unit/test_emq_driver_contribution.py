# =============================================================================
# Stratum AI - EMQ driver contribution tests (TRUST-005)
# =============================================================================
"""
Each EMQ driver exposes its contribution (value * weight) — the points it adds
to the overall EMQ score — so callers can see what drives the number. The
drivers' contributions sum to the overall score.
"""

import pytest

from app.analytics.logic.emq_calculation import EmqDriverResult

pytestmark = pytest.mark.unit


def _driver(value, weight):
    return EmqDriverResult(
        name="d", value=value, weight=weight, status="good", trend="flat"
    )


def test_contribution_is_value_times_weight():
    assert _driver(90.0, 0.30).contribution == 27.0
    assert _driver(80.0, 0.25).contribution == 20.0


def test_contribution_rounds_to_two_places():
    assert _driver(83.3, 0.15).contribution == round(83.3 * 0.15, 2)


def test_contributions_sum_to_weighted_score():
    drivers = [_driver(90, 0.3), _driver(80, 0.25), _driver(70, 0.2)]
    weighted = round(sum(d.value * d.weight for d in drivers), 2)
    assert round(sum(d.contribution for d in drivers), 2) == weighted
