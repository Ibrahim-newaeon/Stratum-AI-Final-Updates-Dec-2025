# =============================================================================
# Stratum AI - A/B Power Analysis unit tests
# =============================================================================
"""Unit tests for app.ml.ab_power_analysis.

Pure statistics (numpy/scipy + dataclasses), no DB/HTTP. Monte-Carlo paths
(Bayesian, Thompson Sampling) are seeded for determinism with loose bounds.
"""

import math

import numpy as np
import pytest

from app.ml.ab_power_analysis import (
    ABPowerAnalyzer,
    BayesianABTester,
    CUPEDAnalyzer,
    MetricType,
    ThompsonSamplingBandit,
    TestType as TType,  # aliased: avoids pytest trying to collect the enum
    calculate_ab_sample_size,
    check_test_power,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def analyzer() -> ABPowerAnalyzer:
    return ABPowerAnalyzer()


@pytest.fixture(autouse=True)
def _seed():
    """Deterministic Monte-Carlo for every test."""
    np.random.seed(1234)


# =============================================================================
# Sample size
# =============================================================================
class TestSampleSize:
    def test_proportion_relative_effect(self, analyzer: ABPowerAnalyzer):
        result = analyzer.calculate_sample_size(
            baseline_rate=0.05,
            minimum_detectable_effect=0.1,  # 10% relative lift
            power=0.8,
            alpha=0.05,
        )
        assert result.sample_size_per_variant > 0
        assert result.total_sample_size == result.sample_size_per_variant * 2
        assert result.effect_type == "relative"
        assert result.days_to_significance is None  # no traffic given

    def test_absolute_effect_flag(self, analyzer: ABPowerAnalyzer):
        result = analyzer.calculate_sample_size(
            baseline_rate=0.10,
            minimum_detectable_effect=0.02,
            effect_is_relative=False,
        )
        assert result.effect_type == "absolute"
        assert result.sample_size_per_variant > 0

    def test_smaller_effect_needs_more_samples(self, analyzer: ABPowerAnalyzer):
        big = analyzer.calculate_sample_size(0.05, 0.2)
        small = analyzer.calculate_sample_size(0.05, 0.05)
        assert small.sample_size_per_variant > big.sample_size_per_variant

    def test_traffic_yields_days(self, analyzer: ABPowerAnalyzer):
        result = analyzer.calculate_sample_size(
            baseline_rate=0.05, minimum_detectable_effect=0.1, traffic_per_day=1000
        )
        assert result.days_to_significance is not None
        assert result.days_to_significance >= 1
        assert result.traffic_per_day == 1000

    def test_continuous_metric(self, analyzer: ABPowerAnalyzer):
        result = analyzer.calculate_sample_size(
            baseline_rate=100.0,
            minimum_detectable_effect=0.05,
            metric_type=MetricType.CONTINUOUS,
            baseline_std=20.0,
        )
        assert result.sample_size_per_variant > 0

    def test_continuous_without_std_uses_estimate(self, analyzer: ABPowerAnalyzer):
        # baseline_std None -> estimated as baseline_rate * 0.5 (no crash)
        result = analyzer.calculate_sample_size(
            baseline_rate=100.0,
            minimum_detectable_effect=0.05,
            metric_type=MetricType.CONTINUOUS,
        )
        assert result.sample_size_per_variant > 0

    def test_count_metric(self, analyzer: ABPowerAnalyzer):
        result = analyzer.calculate_sample_size(
            baseline_rate=10.0,
            minimum_detectable_effect=0.1,
            metric_type=MetricType.COUNT,
        )
        assert result.sample_size_per_variant > 0

    def test_zero_effect_proportion_is_infinite(self, analyzer: ABPowerAnalyzer):
        assert analyzer._sample_size_proportion(0.05, 0.05, 1.96, 0.84) == float("inf")

    def test_zero_diff_continuous_is_infinite(self, analyzer: ABPowerAnalyzer):
        assert analyzer._sample_size_continuous(0.0, 1.0, 1.96, 0.84) == float("inf")

    def test_zero_diff_count_is_infinite(self, analyzer: ABPowerAnalyzer):
        assert analyzer._sample_size_count(5.0, 5.0, 1.96, 0.84) == float("inf")


# =============================================================================
# z-scores
# =============================================================================
class TestZScore:
    def test_two_sided_larger_than_one_sided(self, analyzer: ABPowerAnalyzer):
        two = analyzer._get_z_score(0.05, TType.TWO_SIDED)
        one = analyzer._get_z_score(0.05, TType.ONE_SIDED_GREATER)
        assert two > one
        assert two == pytest.approx(1.959963, abs=1e-4)
        assert one == pytest.approx(1.644853, abs=1e-4)


# =============================================================================
# Power
# =============================================================================
class TestPower:
    def test_power_in_unit_interval(self, analyzer: ABPowerAnalyzer):
        p = analyzer.calculate_power(5000, 0.05, 0.1)
        assert 0.0 <= p <= 1.0

    def test_power_increases_with_sample_size(self, analyzer: ABPowerAnalyzer):
        low = analyzer.calculate_power(500, 0.05, 0.1)
        high = analyzer.calculate_power(50000, 0.05, 0.1)
        assert high > low

    def test_power_continuous_and_count(self, analyzer: ABPowerAnalyzer):
        pc = analyzer.calculate_power(
            5000, 100.0, 0.1, metric_type=MetricType.CONTINUOUS, baseline_std=20.0
        )
        pk = analyzer.calculate_power(
            5000, 10.0, 0.1, metric_type=MetricType.COUNT
        )
        assert 0.0 <= pc <= 1.0
        assert 0.0 <= pk <= 1.0

    def test_continuous_power_without_std(self, analyzer: ABPowerAnalyzer):
        p = analyzer.calculate_power(
            5000, 100.0, 0.1, metric_type=MetricType.CONTINUOUS
        )
        assert 0.0 <= p <= 1.0


# =============================================================================
# MDE
# =============================================================================
class TestMDE:
    def test_mde_keys_and_positive(self, analyzer: ABPowerAnalyzer):
        mde = analyzer.calculate_mde(5000, 0.05)
        assert set(mde) >= {
            "absolute_mde",
            "relative_mde_percent",
            "sample_size_per_variant",
        }
        assert mde["absolute_mde"] > 0
        assert mde["relative_mde_percent"] > 0

    def test_more_samples_shrink_mde(self, analyzer: ABPowerAnalyzer):
        small_n = analyzer.calculate_mde(1000, 0.05)
        large_n = analyzer.calculate_mde(100000, 0.05)
        assert large_n["absolute_mde"] < small_n["absolute_mde"]

    def test_mde_continuous_and_count(self, analyzer: ABPowerAnalyzer):
        c = analyzer.calculate_mde(
            5000, 100.0, metric_type=MetricType.CONTINUOUS, baseline_std=10.0
        )
        k = analyzer.calculate_mde(5000, 10.0, metric_type=MetricType.COUNT)
        assert c["absolute_mde"] > 0
        assert k["absolute_mde"] > 0


# =============================================================================
# Sequential testing
# =============================================================================
class TestSequential:
    def test_continue_when_inconclusive(self, analyzer: ABPowerAnalyzer):
        r = analyzer.sequential_test(
            successes_a=150, trials_a=3000,
            successes_b=180, trials_b=3000,
            planned_samples=10000,
        )
        assert r.conclusion == "continue"
        assert r.should_stop is False
        assert r.samples_used == 6000

    def test_variant_b_wins(self, analyzer: ABPowerAnalyzer):
        r = analyzer.sequential_test(
            successes_a=100, trials_a=2000,
            successes_b=250, trials_b=2000,
            planned_samples=4000,
        )
        assert r.should_stop is True
        assert r.conclusion == "variant_b_wins"

    def test_variant_a_wins(self, analyzer: ABPowerAnalyzer):
        r = analyzer.sequential_test(
            successes_a=250, trials_a=2000,
            successes_b=100, trials_b=2000,
            planned_samples=4000,
        )
        assert r.should_stop is True
        assert r.conclusion == "variant_a_wins"

    def test_no_difference_at_planned(self, analyzer: ABPowerAnalyzer):
        r = analyzer.sequential_test(
            successes_a=100, trials_a=2000,
            successes_b=103, trials_b=2000,
            planned_samples=4000,
        )
        assert r.should_stop is True
        assert r.conclusion == "no_difference"

    def test_explicit_current_look(self, analyzer: ABPowerAnalyzer):
        r = analyzer.sequential_test(
            successes_a=150, trials_a=3000,
            successes_b=180, trials_b=3000,
            planned_samples=10000,
            spending_function="uniform",
            current_look=3,
        )
        assert r.spending_function == "uniform"
        assert 0.0 < r.adjusted_alpha <= 0.05


class TestSpendingFunctions:
    @pytest.mark.parametrize("fn", ["obrien_fleming", "pocock", "uniform"])
    def test_spent_never_exceeds_alpha(self, analyzer: ABPowerAnalyzer, fn: str):
        spent = analyzer._calculate_spending(
            alpha=0.05, information_fraction=0.5,
            spending_function=fn, num_looks=5, current_look=3,
        )
        assert 0.0 < spent <= 0.05

    def test_obrien_fleming_full_information_equals_alpha(
        self, analyzer: ABPowerAnalyzer
    ):
        spent = analyzer._calculate_spending(
            alpha=0.05, information_fraction=1.0,
            spending_function="obrien_fleming", num_looks=5, current_look=5,
        )
        assert spent == pytest.approx(0.05, abs=1e-3)

    def test_pocock_full_information_equals_alpha(self, analyzer: ABPowerAnalyzer):
        spent = analyzer._calculate_spending(
            alpha=0.05, information_fraction=1.0,
            spending_function="pocock", num_looks=5, current_look=5,
        )
        # alpha * log(1 + (e-1)*1) = alpha * log(e) = alpha
        assert spent == pytest.approx(0.05, abs=1e-9)


# =============================================================================
# Multiple-testing corrections
# =============================================================================
class TestCorrections:
    def test_bonferroni(self, analyzer: ABPowerAnalyzer):
        assert analyzer.bonferroni_correction(0.05, 5) == pytest.approx(0.01)

    def test_holm_rejects_only_smallest_here(self, analyzer: ABPowerAnalyzer):
        res = analyzer.holm_bonferroni([0.001, 0.04, 0.03, 0.5], alpha=0.05)
        # Results come back in original order
        by_idx = {r["original_index"]: r for r in res}
        assert by_idx[0]["is_significant"] is True
        assert by_idx[1]["is_significant"] is False
        assert by_idx[3]["is_significant"] is False

    def test_benjamini_hochberg_more_powerful(self, analyzer: ABPowerAnalyzer):
        res = analyzer.benjamini_hochberg([0.001, 0.01, 0.02, 0.5], alpha=0.05)
        by_idx = {r["original_index"]: r for r in res}
        # BH keeps ranks 1..3 significant for this set
        assert by_idx[0]["is_significant"] is True
        assert by_idx[1]["is_significant"] is True
        assert by_idx[2]["is_significant"] is True
        assert by_idx[3]["is_significant"] is False

    def test_correction_preserves_original_order(self, analyzer: ABPowerAnalyzer):
        res = analyzer.holm_bonferroni([0.5, 0.001, 0.2], alpha=0.05)
        assert [r["original_index"] for r in res] == [0, 1, 2]


# =============================================================================
# Convenience module functions
# =============================================================================
class TestConvenience:
    def test_calculate_ab_sample_size_with_traffic(self):
        out = calculate_ab_sample_size(0.05, 10, daily_traffic=1000)
        assert out["sample_size_per_variant"] > 0
        assert out["days_to_significance"] is not None
        assert "days" in out["recommendation"]

    def test_calculate_ab_sample_size_without_traffic(self):
        out = calculate_ab_sample_size(0.05, 10)
        assert out["days_to_significance"] is None
        assert "samples" in out["recommendation"]

    def test_check_test_power(self):
        out = check_test_power(5000, 0.05, 10)
        assert 0.0 <= out["power_to_detect_target"] <= 1.0
        # source returns a numpy bool; assert it matches the power threshold
        assert bool(out["power_is_sufficient"]) == (
            out["power_to_detect_target"] >= 0.8
        )
        assert out["minimum_detectable_lift_percent"] > 0

    def test_check_test_power_large_sample_sufficient(self):
        out = check_test_power(200000, 0.05, 10)
        assert out["power_is_sufficient"]


# =============================================================================
# Bayesian A/B testing
# =============================================================================
class TestBayesian:
    def test_b_clearly_better(self):
        tester = BayesianABTester()
        res = tester.analyze(
            successes_a=100, trials_a=1000,
            successes_b=160, trials_b=1000,
            num_samples=20000,
        )
        assert res.probability_b_beats_a > 0.9
        assert res.probability_a_beats_b == pytest.approx(
            1 - res.probability_b_beats_a, abs=1e-4
        )
        assert res.posterior_mean_b > res.posterior_mean_a
        # expected loss of choosing the true winner (B) is small
        assert res.expected_loss_choosing_b < res.expected_loss_choosing_a

    def test_credible_intervals_ordered(self):
        tester = BayesianABTester()
        res = tester.analyze(120, 1000, 150, 1000, num_samples=20000)
        lo_a, hi_a = res.credible_interval_a
        lo_b, hi_b = res.credible_interval_b
        assert lo_a < hi_a
        assert lo_b < hi_b

    @pytest.mark.parametrize(
        "prob,expected_fragment",
        [
            (0.97, "Strong evidence B"),
            (0.91, "Good evidence B"),
            (0.80, "Moderate evidence B"),
            (0.03, "Strong evidence A"),
            (0.08, "Good evidence A"),
            (0.20, "Moderate evidence A"),
            (0.50, "No clear winner"),
        ],
    )
    def test_recommendation_thresholds(self, prob, expected_fragment):
        tester = BayesianABTester()
        rec = tester._generate_recommendation(prob, 0.0, 0.0, 1.0)
        assert expected_fragment in rec

    def test_stopping_threshold_keys(self):
        tester = BayesianABTester()
        out = tester.calculate_stopping_threshold(
            min_sample_per_variant=200, max_sample_per_variant=5000
        )
        assert out["minimum_samples"] == 200
        assert out["maximum_samples"] == 5000
        assert "recommendation" in out


# =============================================================================
# CUPED variance reduction
# =============================================================================
class TestCUPED:
    def test_correlated_covariate_reduces_variance(self):
        rng = np.random.default_rng(7)
        cov_a = rng.normal(50, 10, 2000)
        cov_b = rng.normal(50, 10, 2000)
        # metric strongly correlated with the pre-period covariate
        metric_a = cov_a * 2 + rng.normal(0, 2, 2000)
        metric_b = cov_b * 2 + rng.normal(0, 2, 2000) + 3  # B lifted by ~3

        result = CUPEDAnalyzer().apply_cuped(metric_a, metric_b, cov_a, cov_b)
        assert result.variance_reduction_percent > 0
        assert result.adjusted_variance <= result.original_variance
        assert result.effective_sample_increase >= 1.0
        # theta ~ slope (2.0) since metric = 2*covariate + noise
        assert result.theta == pytest.approx(2.0, abs=0.2)

    def test_power_boost_from_correlation(self):
        out = CUPEDAnalyzer().estimate_power_boost(0.7)
        assert out["expected_variance_reduction_percent"] == pytest.approx(49.0, abs=0.1)
        assert out["effective_sample_multiplier"] == pytest.approx(1.96, abs=0.05)

    def test_zero_correlation_no_boost(self):
        out = CUPEDAnalyzer().estimate_power_boost(0.0)
        assert out["expected_variance_reduction_percent"] == 0.0
        assert out["effective_sample_multiplier"] == 1.0


# =============================================================================
# Thompson Sampling bandit
# =============================================================================
class TestBandit:
    def test_select_arm_returns_known_arm(self):
        bandit = ThompsonSamplingBandit(["a", "b", "c"])
        assert bandit.select_arm() in {"a", "b", "c"}

    def test_update_success_and_failure(self):
        bandit = ThompsonSamplingBandit(["a", "b"])
        bandit.update("a", True)
        bandit.update("a", False)
        arm = bandit.arms["a"]
        assert arm.total_pulls == 2
        # priors were (1,1); +1 success, +1 failure
        assert arm.successes == 2
        assert arm.failures == 2
        assert arm.ucb_value > 0

    def test_update_unknown_arm_is_noop(self):
        bandit = ThompsonSamplingBandit(["a", "b"])
        bandit.update("does-not-exist", True)  # must not raise
        assert sum(a.total_pulls for a in bandit.arms.values()) == 0

    def test_allocation_weights_sum_to_one(self):
        bandit = ThompsonSamplingBandit(["a", "b", "c"])
        weights = bandit.get_allocation_weights()
        assert set(weights) == {"a", "b", "c"}
        assert sum(weights.values()) == pytest.approx(1.0, abs=1e-9)

    def test_winner_gets_most_traffic(self):
        bandit = ThompsonSamplingBandit(["a", "b"])
        # b converts far better than a
        for _ in range(200):
            bandit.update("a", False)
        for _ in range(150):
            bandit.update("b", True)
        for _ in range(50):
            bandit.update("b", False)
        results = bandit.get_results()
        assert results["best_arm"] == "b"
        assert results["best_conversion_rate"] > 0.5
        assert results["total_observations"] == 400
        weights = bandit.get_allocation_weights()
        assert weights["b"] > weights["a"]
