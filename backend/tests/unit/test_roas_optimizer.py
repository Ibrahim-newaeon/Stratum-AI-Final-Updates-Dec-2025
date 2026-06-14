# =============================================================================
# Stratum AI - ROAS Optimizer Unit Tests
# =============================================================================
"""Unit tests for the pure scoring helpers of ``app.ml.roas_optimizer``.

Covers the deterministic, I/O-free logic: campaign health scoring,
score → status mapping, and the per-platform ROAS target configuration.
The model-backed prediction paths are exercised elsewhere.
"""

import pytest

from app.ml.roas_optimizer import ROASOptimizer

pytestmark = pytest.mark.unit


@pytest.fixture
def optimizer() -> ROASOptimizer:
    return ROASOptimizer()


@pytest.fixture
def meta_thresholds(optimizer: ROASOptimizer) -> dict:
    return optimizer.platform_targets["meta"]


# =============================================================================
# platform_targets configuration
# =============================================================================
class TestPlatformTargets:
    def test_all_platforms_present(self, optimizer: ROASOptimizer):
        assert set(optimizer.platform_targets) == {
            "meta",
            "google",
            "tiktok",
            "snapchat",
            "linkedin",
        }

    def test_thresholds_are_monotonic(self, optimizer: ROASOptimizer):
        # For every platform: min < good < excellent.
        for platform, t in optimizer.platform_targets.items():
            assert t["min"] < t["good"] < t["excellent"], platform


# =============================================================================
# _calculate_health_score
# =============================================================================
class TestHealthScore:
    def test_perfect_campaign_scores_100(
        self, optimizer: ROASOptimizer, meta_thresholds: dict
    ):
        campaign = {
            "roas": 5.0,  # >= excellent (4.0) → 50
            "ctr": 3.0,  # 2x benchmark → capped 25
            "conversions": 10,
            "spend": 200,  # cpa 20 < target 50 → capped 25
        }
        assert optimizer._calculate_health_score(campaign, meta_thresholds) == 100.0

    def test_empty_campaign_scores_zero(
        self, optimizer: ROASOptimizer, meta_thresholds: dict
    ):
        assert optimizer._calculate_health_score({}, meta_thresholds) == 0.0

    def test_roas_at_good_threshold(
        self, optimizer: ROASOptimizer, meta_thresholds: dict
    ):
        # roas == good → 35 ROAS points; ctr == benchmark → 25; no conversions → 0.
        campaign = {"roas": 2.5, "ctr": 1.5}
        assert optimizer._calculate_health_score(campaign, meta_thresholds) == 60.0

    def test_roas_at_min_threshold(
        self, optimizer: ROASOptimizer, meta_thresholds: dict
    ):
        # roas == min → 20 ROAS points; ctr half benchmark → 12.5.
        campaign = {"roas": 1.5, "ctr": 0.75}
        assert optimizer._calculate_health_score(campaign, meta_thresholds) == 32.5

    def test_ctr_score_is_capped(self, optimizer: ROASOptimizer, meta_thresholds: dict):
        # Very high CTR cannot push the CTR component above 25.
        low_ctr = optimizer._calculate_health_score(
            {"roas": 0, "ctr": 1.5}, meta_thresholds
        )
        huge_ctr = optimizer._calculate_health_score(
            {"roas": 0, "ctr": 100.0}, meta_thresholds
        )
        assert low_ctr == 25.0
        assert huge_ctr == 25.0

    def test_conversion_requires_spend_and_conversions(
        self, optimizer: ROASOptimizer, meta_thresholds: dict
    ):
        # Spend but zero conversions → no conversion points.
        campaign = {"roas": 0, "ctr": 0, "spend": 500, "conversions": 0}
        assert optimizer._calculate_health_score(campaign, meta_thresholds) == 0.0


# =============================================================================
# _get_status_from_score
# =============================================================================
class TestStatusFromScore:
    @pytest.mark.parametrize(
        "score,expected",
        [
            (100, "excellent"),
            (80, "excellent"),
            (79.9, "good"),
            (60, "good"),
            (59.9, "needs_attention"),
            (40, "needs_attention"),
            (39.9, "underperforming"),
            (20, "underperforming"),
            (19.9, "critical"),
            (0, "critical"),
        ],
    )
    def test_status_bands(self, optimizer: ROASOptimizer, score: float, expected: str):
        assert optimizer._get_status_from_score(score) == expected
