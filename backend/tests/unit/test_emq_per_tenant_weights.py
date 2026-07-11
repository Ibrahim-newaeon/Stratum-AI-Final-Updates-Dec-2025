# =============================================================================
# Stratum AI - Per-tenant EMQ weights (ML-06)
# =============================================================================
"""
EMQ driver weights were hardcoded per driver. calculate_emq_score now accepts an
optional per-tenant weights map; _apply_weight_overrides applies + renormalizes.
"""

import pytest

from app.analytics.logic.emq_calculation import (
    DEFAULT_EMQ_WEIGHTS,
    DriverStatus,
    DriverTrend,
    EmqDriverResult,
    PlatformMetrics,
    _apply_weight_overrides,
    calculate_emq_score,
)

pytestmark = pytest.mark.unit


def _drivers():
    return [
        EmqDriverResult(
            name=name,
            value=80.0,
            weight=weight,
            status=DriverStatus.GOOD,
            trend=DriverTrend.FLAT,
        )
        for name, weight in DEFAULT_EMQ_WEIGHTS.items()
    ]


def test_default_weights_sum_to_one():
    assert round(sum(DEFAULT_EMQ_WEIGHTS.values()), 5) == 1.0


def test_no_override_is_noop():
    ds = _drivers()
    _apply_weight_overrides(ds, None)
    assert [d.weight for d in ds] == list(DEFAULT_EMQ_WEIGHTS.values())


def test_override_renormalizes_to_one():
    ds = _drivers()
    _apply_weight_overrides(ds, {"Event Match Rate": 0.5})
    assert round(sum(d.weight for d in ds), 5) == 1.0
    emr = next(d for d in ds if d.name == "Event Match Rate")
    assert emr.weight == max(d.weight for d in ds)


def test_all_weight_on_one_driver():
    ds = _drivers()
    _apply_weight_overrides(
        ds,
        {
            "Data Freshness": 1.0,
            "Event Match Rate": 0,
            "Pixel Coverage": 0,
            "Conversion Latency": 0,
            "Attribution Accuracy": 0,
        },
    )
    fresh = next(d for d in ds if d.name == "Data Freshness")
    assert fresh.weight == 1.0
    assert round(sum(d.weight for d in ds), 5) == 1.0


def test_ignores_non_numeric_and_negative():
    ds = _drivers()
    _apply_weight_overrides(ds, {"Event Match Rate": "high", "Pixel Coverage": -5})
    emr = next(d for d in ds if d.name == "Event Match Rate")
    assert emr.weight == DEFAULT_EMQ_WEIGHTS["Event Match Rate"]


def test_calculate_emq_score_accepts_weights():
    metrics = PlatformMetrics(
        platform="meta",
        pixel_events=1000,
        capi_events=1000,
        matched_events=900,
        pages_with_pixel=90,
        total_pages=100,
        avg_conversion_latency_hours=0.5,
        platform_conversions=100,
        ga4_conversions=100,
    )
    base = calculate_emq_score(metrics)
    weighted = calculate_emq_score(metrics, weights={"Event Match Rate": 0.9})
    # Both are valid 0-100 scores; the heavy override changes the composite.
    assert 0 <= base.score <= 100
    assert 0 <= weighted.score <= 100
    assert round(sum(d.weight for d in weighted.drivers), 5) == 1.0
