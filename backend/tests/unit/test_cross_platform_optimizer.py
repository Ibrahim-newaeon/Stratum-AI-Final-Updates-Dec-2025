# =============================================================================
# Stratum AI - Cross-Platform Optimizer unit tests
# =============================================================================
"""Unit tests for app.analytics.logic.cross_platform_optimizer.

Pure budget-reallocation logic, no I/O. Covers efficiency scoring, optimal
allocation across strategies, shift generation, what-if scenarios, and the
build_cross_platform_optimizer entry point (with guardrails).
"""

import pytest

from app.analytics.logic import cross_platform_optimizer as cpo
from app.analytics.logic.cross_platform_optimizer import (
    CrossPlatformOptimizerResponse,
    PlatformEfficiency,
    build_cross_platform_optimizer,
)

pytestmark = pytest.mark.unit


def _pe(
    platform,
    eff=50.0,
    conv=50,
    share=50.0,
    current_spend=500.0,
    roas=3.0,
    cpa=10.0,
):
    return PlatformEfficiency(
        platform=platform,
        campaigns=1,
        current_spend=current_spend,
        current_revenue=current_spend * roas,
        roas=roas,
        cpa=cpa,
        conversions=conv,
        spend_share_pct=share,
        efficiency_score=eff,
        efficiency_rank=0,
    )


def _campaign(cid, name, platform, spend, revenue, conversions):
    return {
        "id": cid,
        "name": name,
        "platform": platform,
        "spend": spend,
        "revenue": revenue,
        "conversions": conversions,
    }


# =============================================================================
# Efficiency score
# =============================================================================
class TestEfficiencyScore:
    def test_average_platform_scores_baseline_plus_volume(self):
        # at-average ROAS/CPA, 50 conversions -> 50 + 10 volume bonus
        s = cpo._compute_efficiency_score(
            roas=4.0, cpa=10.0, conversions=50, avg_roas=4.0, avg_cpa=10.0
        )
        assert s == pytest.approx(60.0, abs=0.1)

    def test_high_roas_boosts_score(self):
        s = cpo._compute_efficiency_score(
            roas=8.0, cpa=10.0, conversions=50, avg_roas=4.0, avg_cpa=10.0
        )
        # roas ratio 2.0 -> +25, +10 volume -> 85
        assert s == pytest.approx(85.0, abs=0.1)

    def test_low_volume_penalised(self):
        s = cpo._compute_efficiency_score(
            roas=4.0, cpa=10.0, conversions=2, avg_roas=4.0, avg_cpa=10.0
        )
        assert s == pytest.approx(40.0, abs=0.1)

    def test_score_clamped_0_100(self):
        low = cpo._compute_efficiency_score(0.0, 0.0, 0, 10.0, 0.0)
        assert 0 <= low <= 100


# =============================================================================
# Optimal allocation
# =============================================================================
class TestOptimalAllocation:
    def test_empty_platforms(self):
        assert cpo._compute_optimal_allocation([], 1000, "balanced") == {}

    def test_roas_max_favours_efficient_platform(self):
        platforms = [_pe("meta", eff=80), _pe("google", eff=40)]
        alloc = cpo._compute_optimal_allocation(platforms, 1000, "roas_max")
        assert sum(alloc.values()) == pytest.approx(1000, abs=1)
        assert alloc["meta"] > alloc["google"]

    def test_volume_max_strategy(self):
        platforms = [_pe("meta", eff=50, conv=200), _pe("google", eff=50, conv=10)]
        alloc = cpo._compute_optimal_allocation(platforms, 1000, "volume_max")
        assert alloc["meta"] > alloc["google"]

    def test_balanced_strategy_sums_to_budget(self):
        platforms = [_pe("meta", eff=70, share=60), _pe("google", eff=50, share=40)]
        alloc = cpo._compute_optimal_allocation(platforms, 2000, "balanced")
        assert sum(alloc.values()) == pytest.approx(2000, abs=1)


# =============================================================================
# Shift generation
# =============================================================================
class TestShifts:
    def test_shift_from_weak_to_strong(self):
        platforms = [
            _pe("meta", eff=80, current_spend=400, roas=5.0),
            _pe("google", eff=30, current_spend=600, roas=1.0),
        ]
        optimal = {"meta": 700, "google": 300}
        shifts = cpo._generate_shifts(platforms, optimal, 1000)
        assert shifts
        assert shifts[0].from_platform == "google"
        assert shifts[0].to_platform == "meta"
        assert shifts[0].shift_amount >= 50

    def test_no_shift_below_threshold(self):
        platforms = [_pe("meta", current_spend=500), _pe("google", current_spend=500)]
        optimal = {"meta": 520, "google": 480}  # diffs < 50
        assert cpo._generate_shifts(platforms, optimal, 1000) == []


# =============================================================================
# Scenarios
# =============================================================================
class TestScenarios:
    def test_three_named_scenarios(self):
        platforms = [
            _pe("meta", roas=5.0, cpa=10.0),
            _pe("google", roas=2.0, cpa=20.0),
        ]
        scenarios = cpo._build_scenarios(platforms, 1000, 3500, 3.5)
        names = {s.name for s in scenarios}
        assert names == {"ROAS Maximized", "Volume Maximized", "Equal Distribution"}
        for s in scenarios:
            assert s.projected_revenue >= 0
            assert sum(s.allocations.values()) == pytest.approx(1000, abs=2)


# =============================================================================
# build_cross_platform_optimizer
# =============================================================================
class TestBuild:
    def _campaigns(self):
        return [
            _campaign(1, "A", "meta", 600, 3000, 100),  # 5x ROAS
            _campaign(2, "B", "google", 400, 600, 20),  # 1.5x ROAS
        ]

    def test_empty(self):
        resp = build_cross_platform_optimizer([])
        assert isinstance(resp, CrossPlatformOptimizerResponse)
        assert resp.total_budget == 0
        assert "No campaigns" in resp.summary

    def test_full_structure_and_ranking(self):
        resp = build_cross_platform_optimizer(self._campaigns(), strategy="roas_max")
        assert resp.platforms_count == 2
        assert resp.total_budget == 1000
        assert resp.current_roas == pytest.approx(3.6, abs=0.01)
        # platforms ranked by efficiency (rank 1 = highest score)
        assert resp.platforms[0].efficiency_rank == 1
        assert resp.platforms[0].efficiency_score >= resp.platforms[1].efficiency_score
        assert len(resp.scenarios) == 3

    def test_guardrails_cap_changes(self):
        resp = build_cross_platform_optimizer(self._campaigns(), strategy="roas_max")
        # max +30% increase, -20% decrease enforced
        for r in resp.recommendations:
            assert -20.0 <= r.change_pct <= 30.0

    def test_strategy_passed_through(self):
        resp = build_cross_platform_optimizer(self._campaigns(), strategy="volume_max")
        assert resp.strategy == "volume_max"
        assert "volume maximization" in resp.summary
