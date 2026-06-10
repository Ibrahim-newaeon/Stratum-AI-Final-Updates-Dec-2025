# =============================================================================
# Stratum AI - Competitor Benchmarking Service unit tests
# =============================================================================
"""Unit tests for app.services.competitor_benchmarking_service.

Pure in-memory industry benchmarking, no I/O. Covers percentile
interpolation (both metric directions), performance levels, benchmark
assembly with industry fallback, strengths/weaknesses, recommendations,
industry reports, cross-platform comparison, and the P2 enhancements
(seasonal adjuster, trend analyzer, position forecaster).
"""

from datetime import datetime, timezone

import pytest

from app.services.competitor_benchmarking_service import (
    BenchmarkTrendAnalyzer,
    CompetitivePositionForecaster,
    CompetitorBenchmarkingService,
    Industry,
    PerformanceLevel,
    Region,
    SeasonalBenchmarkAdjuster,
    get_benchmark_comparison,
)

pytestmark = pytest.mark.unit


@pytest.fixture()
def svc():
    return CompetitorBenchmarkingService()


def _ctr_benchmark(svc):
    # ecommerce/global/meta ctr: p10=0.8 p25=1.2 median=1.8 p75=2.5 p90=3.5
    return svc._benchmark_data["ecommerce_global_meta_ctr"]


def _cpc_benchmark(svc):
    # ecommerce/global/meta cpc: p10=0.30 p25=0.50 median=0.80 p75=1.20 p90=2.00
    return svc._benchmark_data["ecommerce_global_meta_cpc"]


# =============================================================================
# Percentile calculation
# =============================================================================
class TestPercentile:
    def test_median_value_is_50th(self, svc):
        assert svc._calculate_percentile(1.8, _ctr_benchmark(svc), True) == 50.0

    def test_below_p10_clamps(self, svc):
        assert svc._calculate_percentile(0.5, _ctr_benchmark(svc), True) == 10.0

    def test_above_p90_clamps(self, svc):
        assert svc._calculate_percentile(5.0, _ctr_benchmark(svc), True) == 90.0

    def test_linear_interpolation(self, svc):
        # 1.5 is halfway between p25 (1.2) and median (1.8) -> 37.5
        assert svc._calculate_percentile(1.5, _ctr_benchmark(svc), True) == 37.5

    def test_lower_is_better_cheap_is_top(self, svc):
        # very cheap CPC -> 10th percentile -> EXCELLENT for lower-better
        assert svc._calculate_percentile(0.20, _cpc_benchmark(svc), False) == 10.0

    def test_lower_is_better_expensive_is_bottom(self, svc):
        assert svc._calculate_percentile(3.0, _cpc_benchmark(svc), False) == 90.0

    def test_lower_is_better_median(self, svc):
        assert svc._calculate_percentile(0.80, _cpc_benchmark(svc), False) == 50.0


# =============================================================================
# Performance levels
# =============================================================================
class TestPerformanceLevel:
    @pytest.mark.parametrize(
        "percentile,expected",
        [
            (95, PerformanceLevel.EXCELLENT),
            (80, PerformanceLevel.ABOVE_AVERAGE),
            (50, PerformanceLevel.AVERAGE),
            (15, PerformanceLevel.BELOW_AVERAGE),
            (5, PerformanceLevel.POOR),
        ],
    )
    def test_higher_better(self, svc, percentile, expected):
        assert svc._get_performance_level(percentile, True) == expected

    @pytest.mark.parametrize(
        "percentile,expected",
        [
            (5, PerformanceLevel.EXCELLENT),
            (20, PerformanceLevel.ABOVE_AVERAGE),
            (50, PerformanceLevel.AVERAGE),
            (85, PerformanceLevel.BELOW_AVERAGE),
            (95, PerformanceLevel.POOR),
        ],
    )
    def test_lower_better(self, svc, percentile, expected):
        assert svc._get_performance_level(percentile, False) == expected


# =============================================================================
# get_benchmark
# =============================================================================
class TestGetBenchmark:
    def test_median_metrics_average_overall(self, svc):
        benchmark = svc.get_benchmark(
            "t1",
            Industry.ECOMMERCE,
            Region.GLOBAL,
            "meta",
            {"ctr": 1.8, "roas": 3.0},  # both at median
        )
        assert benchmark.overall_percentile == 50.0
        assert benchmark.performance_level == PerformanceLevel.AVERAGE
        assert set(benchmark.metrics) == {"ctr", "roas"}
        assert benchmark.metrics["ctr"].benchmark_median == 1.8

    def test_strengths_and_weaknesses_split(self, svc):
        benchmark = svc.get_benchmark(
            "t1",
            Industry.ECOMMERCE,
            Region.GLOBAL,
            "meta",
            {"ctr": 5.0, "roas": 1.0},  # ctr top, roas bottom
        )
        assert any("Click-Through Rate" in s for s in benchmark.strengths)
        assert any("ROAS" in w for w in benchmark.weaknesses)

    def test_unknown_industry_falls_back_to_ecommerce(self, svc):
        benchmark = svc.get_benchmark(
            "t1",
            Industry.TRAVEL,  # no travel benchmarks defined
            Region.GLOBAL,
            "meta",
            {"ctr": 1.8},
        )
        # fallback to ecommerce/global/meta median
        assert benchmark.metrics["ctr"].your_percentile == 50.0
        # Regression: empty industry/platform combo used to raise
        # ValueError from min() on an empty sequence
        assert benchmark.benchmark_sample_size == 0

    def test_unknown_metric_skipped(self, svc):
        benchmark = svc.get_benchmark(
            "t1",
            Industry.ECOMMERCE,
            Region.GLOBAL,
            "meta",
            {"bounce_rate": 42.0},
        )
        assert benchmark.metrics == {}
        assert benchmark.overall_percentile == 50.0  # default

    def test_unknown_platform_yields_empty_metrics(self, svc):
        benchmark = svc.get_benchmark(
            "t1",
            Industry.ECOMMERCE,
            Region.GLOBAL,
            "linkedin",
            {"ctr": 2.0},
        )
        assert benchmark.metrics == {}

    def test_recommendations_for_weak_metrics(self, svc):
        benchmark = svc.get_benchmark(
            "t1",
            Industry.ECOMMERCE,
            Region.GLOBAL,
            "meta",
            {"ctr": 0.5},  # poor
        )
        joined = " ".join(benchmark.recommendations)
        assert "video creatives" in joined  # meta-specific CTR advice
        assert "A/B testing" in joined

    def test_recommendations_when_all_strong(self, svc):
        benchmark = svc.get_benchmark(
            "t1",
            Industry.ECOMMERCE,
            Region.GLOBAL,
            "meta",
            {"ctr": 3.0, "roas": 5.0},
        )
        assert benchmark.recommendations == [
            "Maintain current strategy - performance is at or above industry benchmarks"
        ]

    def test_general_recommendation_for_unlisted_platform(self, svc):
        rec = svc._get_metric_recommendation(
            "ctr",
            None,
            Industry.ECOMMERCE,
            "snapchat",
        )
        assert rec == "Improve ad creative quality and relevance to increase CTR"

    def test_unknown_metric_recommendation_is_none(self, svc):
        assert (
            svc._get_metric_recommendation("bounce", None, Industry.ECOMMERCE, "meta")
            is None
        )


# =============================================================================
# Industry report + platform comparison
# =============================================================================
class TestReports:
    def test_industry_report_full(self, svc):
        report = svc.get_industry_report(Industry.ECOMMERCE, "meta")
        assert set(report["metrics"]) == {"ctr", "cvr", "cpc", "cpm", "cpa", "roas"}
        assert report["metrics"]["ctr"]["median"] == 1.8
        assert report["industry"] == "ecommerce"

    def test_industry_report_missing_combo_empty(self, svc):
        report = svc.get_industry_report(Industry.SAAS, "tiktok")
        assert report["metrics"] == {}

    def test_compare_platforms_picks_best(self, svc):
        result = svc.compare_platforms(
            "t1",
            Industry.ECOMMERCE,
            {
                "meta": {"ctr": 3.0, "roas": 5.0},  # strong
                "tiktok": {"ctr": 0.5, "roas": 1.0},  # weak
            },
        )
        assert result["best_performing_platform"] == "meta"
        assert "meta" in result["recommendation"]
        assert (
            result["platforms"]["meta"]["overall_percentile"]
            > result["platforms"]["tiktok"]["overall_percentile"]
        )


# =============================================================================
# Convenience wrapper (module singleton)
# =============================================================================
class TestConvenience:
    def test_invalid_industry_falls_back_to_other(self):
        result = get_benchmark_comparison(
            "ut_bench_t1",
            "not_an_industry",
            "meta",
            {"ctr": 1.8},
        )
        # OTHER has no data -> ecommerce fallback -> median
        assert result["metrics"]["ctr"]["your_percentile"] == 50.0
        assert set(result) >= {
            "overall_percentile",
            "performance_level",
            "strengths",
            "weaknesses",
            "recommendations",
        }


# =============================================================================
# SeasonalBenchmarkAdjuster
# =============================================================================
class TestSeasonalAdjuster:
    def test_q4_ecommerce_cpc_compound_adjustment(self):
        adjuster = SeasonalBenchmarkAdjuster()
        result = adjuster.adjust_benchmark(
            "cpc",
            base_value=1.0,
            industry=Industry.ECOMMERCE,
            date=datetime(2026, 12, 15, tzinfo=timezone.utc),
        )
        assert result.season == "Q4"
        # 1.35 * 1.25 = 1.6875, rounded to 3 places
        assert result.seasonal_adjustment == pytest.approx(1.688, abs=0.001)
        assert result.adjusted_benchmark == pytest.approx(1.688, abs=0.001)
        assert result.confidence == 0.85

    def test_unknown_industry_neutral(self):
        adjuster = SeasonalBenchmarkAdjuster()
        result = adjuster.adjust_benchmark(
            "ctr",
            base_value=2.0,
            industry=Industry.TRAVEL,
            date=datetime(2026, 7, 1, tzinfo=timezone.utc),
        )
        assert result.seasonal_adjustment == 1.0
        assert result.adjusted_benchmark == 2.0
        assert result.confidence == 0.6

    def test_quarter_derivation_from_date(self):
        adjuster = SeasonalBenchmarkAdjuster()
        for month, quarter in [(1, "Q1"), (4, "Q2"), (9, "Q3"), (10, "Q4")]:
            result = adjuster.adjust_benchmark(
                "ctr",
                1.0,
                Industry.SAAS,
                date=datetime(2026, month, 1, tzinfo=timezone.utc),
            )
            assert result.season == quarter

    def test_current_quarter_valid(self):
        assert SeasonalBenchmarkAdjuster().get_current_quarter() in {
            "Q1",
            "Q2",
            "Q3",
            "Q4",
        }

    def test_seasonal_context_mentions_industry(self):
        context = SeasonalBenchmarkAdjuster().get_seasonal_context(Industry.ECOMMERCE)
        assert "ecommerce" in context


# =============================================================================
# BenchmarkTrendAnalyzer
# =============================================================================
class TestTrendAnalyzer:
    def _record(self, analyzer, values):
        for v in values:
            analyzer.record_benchmark("ctr", "ecommerce", "meta", v)

    def test_insufficient_history(self):
        trend = BenchmarkTrendAnalyzer().analyze_trend("ctr", "ecommerce", "meta")
        assert trend.direction == "stable"
        assert trend.industry_context == "Insufficient historical data"

    def test_improving_trend_and_forecast(self):
        analyzer = BenchmarkTrendAnalyzer()
        self._record(analyzer, [1.0, 1.5, 2.0])
        trend = analyzer.analyze_trend("ctr", "ecommerce", "meta")
        assert trend.direction == "improving"
        assert trend.change_rate == 100.0  # +100% over ~1 "month" unit
        assert trend.forecast_3m == 8.0  # 2.0 * (1 + 1.0*3)
        assert trend.forecast_6m == 14.0
        assert "competition may be decreasing" in trend.industry_context

    def test_declining_trend(self):
        analyzer = BenchmarkTrendAnalyzer()
        self._record(analyzer, [2.0, 1.5, 1.0])
        trend = analyzer.analyze_trend("ctr", "ecommerce", "meta")
        assert trend.direction == "declining"
        assert trend.change_rate == -50.0
        assert "ad fatigue" in trend.industry_context

    def test_stable_trend(self):
        analyzer = BenchmarkTrendAnalyzer()
        self._record(analyzer, [1.0, 1.0, 1.005])
        trend = analyzer.analyze_trend("ctr", "ecommerce", "meta")
        assert trend.direction == "stable"

    def test_unknown_context_pair_fallback(self):
        analyzer = BenchmarkTrendAnalyzer()
        context = analyzer._generate_industry_context("cvr", "improving", "gaming")
        assert context == "cvr improving in gaming"


# =============================================================================
# CompetitivePositionForecaster
# =============================================================================
class TestPositionForecaster:
    def _forecaster(self):
        return CompetitivePositionForecaster(CompetitorBenchmarkingService())

    def test_stable_without_signals(self):
        forecast = self._forecaster().forecast_position("t1", 50.0, {})
        assert forecast.trajectory == "maintaining"
        assert forecast.forecast_1m_percentile == 50.0
        assert forecast.key_drivers == ["Performance is stable"]

    def test_gaining_with_improving_metrics(self):
        forecast = self._forecaster().forecast_position("t1", 50.0, {"ctr": 0.5})
        assert forecast.trajectory == "gaining"
        assert forecast.forecast_1m_percentile == 60.0  # 50 + (1/3)*30
        assert forecast.forecast_6m_percentile == 99.0  # capped
        assert "Improving ctr" in forecast.key_drivers

    def test_losing_with_declining_metrics(self):
        forecast = self._forecaster().forecast_position("t1", 50.0, {"roas": -0.5})
        assert forecast.trajectory == "losing"
        assert "Declining roas - needs attention" in forecast.key_drivers

    def test_momentum_from_position_history(self):
        forecaster = self._forecaster()
        for p in [40.0, 45.0, 50.0, 55.0, 60.0]:
            forecaster.record_position("t1", p)
        forecast = forecaster.forecast_position("t1", 60.0, {})
        # momentum (60-40)/5 = 4 -> combined 1.33 -> gaining
        assert forecast.trajectory == "gaining"

    def test_improvement_opportunities(self):
        forecaster = self._forecaster()
        opportunities = forecaster.get_improvement_opportunities(
            "t1",
            current_metrics={"ctr": 1.0, "roas": 3.0, "mystery": 5.0},
            benchmarks={"ctr": 2.0, "roas": 3.0},
        )
        assert len(opportunities) == 1  # roas at benchmark, mystery unknown
        opp = opportunities[0]
        assert opp["metric"] == "ctr"
        assert opp["gap_percent"] == 50.0
        assert opp["potential_percentile_gain"] == 25.0
        assert opp["priority"] == "high"

    def test_opportunities_sorted_by_gain(self):
        forecaster = self._forecaster()
        opportunities = forecaster.get_improvement_opportunities(
            "t1",
            current_metrics={"ctr": 1.6, "cvr": 1.0},
            benchmarks={"ctr": 2.0, "cvr": 4.0},  # 20% vs 75% gaps
        )
        assert [o["metric"] for o in opportunities] == ["cvr", "ctr"]
