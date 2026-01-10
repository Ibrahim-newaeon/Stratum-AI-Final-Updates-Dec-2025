# =============================================================================
# Stratum AI - Competitor Benchmarking Service
# =============================================================================
"""
Service for benchmarking performance against industry competitors and standards.

Provides:
- Industry benchmark comparisons (CPM, CPC, CTR, CVR, ROAS)
- Percentile rankings against similar advertisers
- Trend analysis vs market
- Recommendations based on competitive position
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import statistics
import random

from app.core.logging import get_logger

logger = get_logger(__name__)


class Industry(str, Enum):
    """Industry verticals for benchmarking."""
    ECOMMERCE = "ecommerce"
    SAAS = "saas"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    TRAVEL = "travel"
    REAL_ESTATE = "real_estate"
    GAMING = "gaming"
    FOOD_BEVERAGE = "food_beverage"
    FASHION = "fashion"
    AUTOMOTIVE = "automotive"
    B2B = "b2b"
    RETAIL = "retail"
    ENTERTAINMENT = "entertainment"
    OTHER = "other"


class Region(str, Enum):
    """Geographic regions for benchmarking."""
    NORTH_AMERICA = "north_america"
    EUROPE = "europe"
    ASIA_PACIFIC = "asia_pacific"
    MIDDLE_EAST = "middle_east"
    LATIN_AMERICA = "latin_america"
    AFRICA = "africa"
    GLOBAL = "global"


class PerformanceLevel(str, Enum):
    """Performance level relative to benchmark."""
    EXCELLENT = "excellent"  # Top 10%
    ABOVE_AVERAGE = "above_average"  # Top 25%
    AVERAGE = "average"  # 25-75%
    BELOW_AVERAGE = "below_average"  # Bottom 25%
    POOR = "poor"  # Bottom 10%


@dataclass
class BenchmarkMetric:
    """A single benchmark metric with percentile data."""
    metric_name: str
    your_value: float
    benchmark_p25: float  # 25th percentile
    benchmark_median: float  # 50th percentile (median)
    benchmark_p75: float  # 75th percentile
    benchmark_p90: float  # 90th percentile
    benchmark_mean: float
    your_percentile: float  # Where you stand (0-100)
    performance_level: PerformanceLevel
    is_higher_better: bool  # True for CTR/ROAS, False for CPC/CPA
    trend_vs_benchmark: str  # "improving", "declining", "stable"


@dataclass
class CompetitorBenchmark:
    """Complete benchmark comparison."""
    tenant_id: str
    industry: Industry
    region: Region
    platform: str
    period_start: datetime
    period_end: datetime

    # Core metrics
    metrics: Dict[str, BenchmarkMetric]

    # Summary
    overall_percentile: float
    performance_level: PerformanceLevel
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]

    # Metadata
    benchmark_sample_size: int
    last_updated: datetime


@dataclass
class IndustryBenchmarkData:
    """Industry benchmark data structure."""
    industry: Industry
    region: Region
    platform: str
    metric_name: str
    p10: float
    p25: float
    median: float
    p75: float
    p90: float
    mean: float
    sample_size: int
    last_updated: datetime


class CompetitorBenchmarkingService:
    """
    Service for comparing performance against industry benchmarks.

    Usage:
        service = CompetitorBenchmarkingService()

        # Get benchmark comparison
        benchmark = service.get_benchmark(
            tenant_id="tenant_123",
            industry=Industry.ECOMMERCE,
            region=Region.NORTH_AMERICA,
            platform="meta",
            metrics={
                "ctr": 2.5,
                "cvr": 3.0,
                "cpc": 1.20,
                "roas": 2.8,
            }
        )

        # Get recommendations
        recommendations = service.get_recommendations(benchmark)
    """

    def __init__(self):
        # In production, this would come from a database or external API
        self._benchmark_data = self._load_benchmark_data()

    def _load_benchmark_data(self) -> Dict[str, IndustryBenchmarkData]:
        """Load industry benchmark data."""
        # Sample benchmark data - in production, this would come from
        # aggregated anonymized data or industry reports
        benchmarks = {}

        # Define benchmark data for key industry/platform combinations
        benchmark_configs = [
            # E-commerce benchmarks
            (Industry.ECOMMERCE, Region.GLOBAL, "meta", {
                "ctr": (0.8, 1.2, 1.8, 2.5, 3.5, 1.9),
                "cvr": (1.0, 1.8, 2.5, 3.5, 5.0, 2.7),
                "cpc": (0.30, 0.50, 0.80, 1.20, 2.00, 0.90),
                "cpm": (5.0, 8.0, 12.0, 18.0, 30.0, 13.5),
                "cpa": (10.0, 18.0, 30.0, 50.0, 100.0, 35.0),
                "roas": (1.5, 2.0, 3.0, 4.5, 7.0, 3.2),
            }),
            (Industry.ECOMMERCE, Region.GLOBAL, "google", {
                "ctr": (1.5, 2.5, 3.5, 5.0, 7.0, 3.8),
                "cvr": (1.5, 2.5, 3.5, 5.0, 7.0, 3.7),
                "cpc": (0.50, 0.80, 1.20, 1.80, 3.00, 1.35),
                "cpm": (8.0, 12.0, 18.0, 28.0, 45.0, 20.0),
                "cpa": (8.0, 15.0, 25.0, 45.0, 80.0, 30.0),
                "roas": (2.0, 2.5, 3.5, 5.0, 8.0, 3.8),
            }),
            (Industry.ECOMMERCE, Region.GLOBAL, "tiktok", {
                "ctr": (0.5, 0.8, 1.2, 1.8, 2.5, 1.3),
                "cvr": (0.8, 1.2, 2.0, 3.0, 4.5, 2.1),
                "cpc": (0.20, 0.35, 0.55, 0.85, 1.50, 0.60),
                "cpm": (3.0, 5.0, 8.0, 12.0, 20.0, 8.5),
                "cpa": (12.0, 20.0, 35.0, 60.0, 120.0, 42.0),
                "roas": (1.2, 1.8, 2.5, 3.8, 6.0, 2.7),
            }),
            # SaaS benchmarks
            (Industry.SAAS, Region.GLOBAL, "meta", {
                "ctr": (0.5, 0.8, 1.2, 1.8, 2.5, 1.3),
                "cvr": (2.0, 3.5, 5.0, 7.5, 12.0, 5.5),
                "cpc": (1.00, 1.80, 3.00, 5.00, 10.00, 3.50),
                "cpm": (15.0, 25.0, 40.0, 65.0, 100.0, 45.0),
                "cpa": (50.0, 100.0, 180.0, 300.0, 600.0, 210.0),
                "roas": (1.0, 1.5, 2.5, 4.0, 7.0, 2.8),
            }),
            (Industry.SAAS, Region.GLOBAL, "google", {
                "ctr": (2.0, 3.0, 4.5, 6.5, 9.0, 4.8),
                "cvr": (2.5, 4.0, 6.0, 9.0, 14.0, 6.5),
                "cpc": (2.00, 3.50, 5.50, 9.00, 15.00, 6.20),
                "cpm": (25.0, 40.0, 60.0, 100.0, 160.0, 70.0),
                "cpa": (40.0, 80.0, 150.0, 280.0, 500.0, 180.0),
                "roas": (1.2, 1.8, 3.0, 5.0, 9.0, 3.5),
            }),
            # Finance benchmarks
            (Industry.FINANCE, Region.GLOBAL, "meta", {
                "ctr": (0.4, 0.6, 1.0, 1.5, 2.2, 1.1),
                "cvr": (1.5, 2.5, 4.0, 6.0, 10.0, 4.3),
                "cpc": (2.00, 3.50, 6.00, 10.00, 20.00, 7.00),
                "cpm": (20.0, 35.0, 55.0, 90.0, 150.0, 62.0),
                "cpa": (80.0, 150.0, 280.0, 500.0, 1000.0, 340.0),
                "roas": (0.8, 1.2, 2.0, 3.5, 6.0, 2.3),
            }),
            # Gaming benchmarks
            (Industry.GAMING, Region.GLOBAL, "meta", {
                "ctr": (1.0, 1.5, 2.2, 3.2, 4.5, 2.4),
                "cvr": (5.0, 8.0, 12.0, 18.0, 28.0, 13.0),
                "cpc": (0.15, 0.25, 0.40, 0.65, 1.20, 0.45),
                "cpm": (2.0, 4.0, 6.5, 10.0, 18.0, 7.2),
                "cpa": (1.50, 2.50, 4.50, 8.00, 15.00, 5.20),
                "roas": (0.5, 0.8, 1.2, 2.0, 3.5, 1.4),
            }),
        ]

        for industry, region, platform, metrics in benchmark_configs:
            for metric_name, (p10, p25, median, p75, p90, mean) in metrics.items():
                key = f"{industry.value}_{region.value}_{platform}_{metric_name}"
                benchmarks[key] = IndustryBenchmarkData(
                    industry=industry,
                    region=region,
                    platform=platform,
                    metric_name=metric_name,
                    p10=p10,
                    p25=p25,
                    median=median,
                    p75=p75,
                    p90=p90,
                    mean=mean,
                    sample_size=random.randint(500, 2000),
                    last_updated=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 7)),
                )

        return benchmarks

    def get_benchmark(
        self,
        tenant_id: str,
        industry: Industry,
        region: Region,
        platform: str,
        metrics: Dict[str, float],
        period_days: int = 30,
    ) -> CompetitorBenchmark:
        """
        Get benchmark comparison for a tenant.

        Args:
            tenant_id: Tenant identifier
            industry: Industry vertical
            region: Geographic region
            platform: Ad platform (meta, google, tiktok, etc.)
            metrics: Dict of metric name -> your value
            period_days: Analysis period

        Returns:
            CompetitorBenchmark with detailed comparison
        """
        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=period_days)

        benchmark_metrics = {}

        # Calculate benchmark for each metric
        metric_definitions = {
            "ctr": ("Click-Through Rate", True),
            "cvr": ("Conversion Rate", True),
            "cpc": ("Cost Per Click", False),
            "cpm": ("Cost Per Mille", False),
            "cpa": ("Cost Per Acquisition", False),
            "roas": ("Return on Ad Spend", True),
        }

        percentiles = []

        for metric_name, your_value in metrics.items():
            key = f"{industry.value}_{region.value}_{platform}_{metric_name}"

            # Try to find benchmark data
            benchmark_data = self._benchmark_data.get(key)

            if benchmark_data is None:
                # Fall back to global/other industry
                key = f"{Industry.ECOMMERCE.value}_{Region.GLOBAL.value}_{platform}_{metric_name}"
                benchmark_data = self._benchmark_data.get(key)

            if benchmark_data is None:
                continue

            # Calculate percentile
            is_higher_better = metric_definitions.get(metric_name, (metric_name, True))[1]
            your_percentile = self._calculate_percentile(
                your_value,
                benchmark_data,
                is_higher_better,
            )

            # Determine performance level
            performance_level = self._get_performance_level(your_percentile, is_higher_better)

            # Determine trend (simplified - would use historical data in production)
            trend = "stable"

            benchmark_metrics[metric_name] = BenchmarkMetric(
                metric_name=metric_name,
                your_value=your_value,
                benchmark_p25=benchmark_data.p25,
                benchmark_median=benchmark_data.median,
                benchmark_p75=benchmark_data.p75,
                benchmark_p90=benchmark_data.p90,
                benchmark_mean=benchmark_data.mean,
                your_percentile=your_percentile,
                performance_level=performance_level,
                is_higher_better=is_higher_better,
                trend_vs_benchmark=trend,
            )

            percentiles.append(your_percentile)

        # Calculate overall percentile
        overall_percentile = statistics.mean(percentiles) if percentiles else 50.0
        overall_level = self._get_performance_level(overall_percentile, True)

        # Identify strengths and weaknesses
        strengths, weaknesses = self._identify_strengths_weaknesses(benchmark_metrics)

        # Generate recommendations
        recommendations = self._generate_recommendations(benchmark_metrics, industry, platform)

        # Get sample size
        sample_size = min(
            bd.sample_size for bd in self._benchmark_data.values()
            if bd.industry == industry and bd.platform == platform
        ) if self._benchmark_data else 0

        return CompetitorBenchmark(
            tenant_id=tenant_id,
            industry=industry,
            region=region,
            platform=platform,
            period_start=period_start,
            period_end=now,
            metrics=benchmark_metrics,
            overall_percentile=round(overall_percentile, 1),
            performance_level=overall_level,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            benchmark_sample_size=sample_size,
            last_updated=now,
        )

    def _calculate_percentile(
        self,
        value: float,
        benchmark: IndustryBenchmarkData,
        is_higher_better: bool,
    ) -> float:
        """Calculate percentile ranking."""
        # Use linear interpolation between benchmark percentiles
        percentile_points = [
            (benchmark.p10, 10),
            (benchmark.p25, 25),
            (benchmark.median, 50),
            (benchmark.p75, 75),
            (benchmark.p90, 90),
        ]

        if not is_higher_better:
            # For metrics where lower is better, invert the comparison
            percentile_points = [(v, 100 - p) for v, p in percentile_points]
            percentile_points.sort(key=lambda x: x[0])

        # Find where value falls
        if value <= percentile_points[0][0]:
            return percentile_points[0][1] if is_higher_better else 100 - percentile_points[0][1]

        if value >= percentile_points[-1][0]:
            return percentile_points[-1][1] if is_higher_better else 100 - percentile_points[-1][1]

        # Linear interpolation
        for i in range(len(percentile_points) - 1):
            v1, p1 = percentile_points[i]
            v2, p2 = percentile_points[i + 1]

            if v1 <= value <= v2:
                ratio = (value - v1) / (v2 - v1) if v2 != v1 else 0
                return p1 + ratio * (p2 - p1)

        return 50.0

    def _get_performance_level(
        self,
        percentile: float,
        is_higher_better: bool = True,
    ) -> PerformanceLevel:
        """Determine performance level from percentile."""
        if is_higher_better:
            if percentile >= 90:
                return PerformanceLevel.EXCELLENT
            elif percentile >= 75:
                return PerformanceLevel.ABOVE_AVERAGE
            elif percentile >= 25:
                return PerformanceLevel.AVERAGE
            elif percentile >= 10:
                return PerformanceLevel.BELOW_AVERAGE
            else:
                return PerformanceLevel.POOR
        else:
            # Lower is better
            if percentile <= 10:
                return PerformanceLevel.EXCELLENT
            elif percentile <= 25:
                return PerformanceLevel.ABOVE_AVERAGE
            elif percentile <= 75:
                return PerformanceLevel.AVERAGE
            elif percentile <= 90:
                return PerformanceLevel.BELOW_AVERAGE
            else:
                return PerformanceLevel.POOR

    def _identify_strengths_weaknesses(
        self,
        metrics: Dict[str, BenchmarkMetric],
    ) -> Tuple[List[str], List[str]]:
        """Identify strengths and weaknesses from benchmark metrics."""
        strengths = []
        weaknesses = []

        for name, metric in metrics.items():
            friendly_name = self._friendly_metric_name(name)

            if metric.performance_level in [PerformanceLevel.EXCELLENT, PerformanceLevel.ABOVE_AVERAGE]:
                pct = round(metric.your_percentile)
                strengths.append(f"{friendly_name} (top {100-pct}% of industry)")
            elif metric.performance_level in [PerformanceLevel.BELOW_AVERAGE, PerformanceLevel.POOR]:
                pct = round(metric.your_percentile)
                weaknesses.append(f"{friendly_name} (bottom {pct}% of industry)")

        return strengths, weaknesses

    def _generate_recommendations(
        self,
        metrics: Dict[str, BenchmarkMetric],
        industry: Industry,
        platform: str,
    ) -> List[str]:
        """Generate actionable recommendations based on benchmark comparison."""
        recommendations = []

        for name, metric in metrics.items():
            if metric.performance_level in [PerformanceLevel.BELOW_AVERAGE, PerformanceLevel.POOR]:
                rec = self._get_metric_recommendation(name, metric, industry, platform)
                if rec:
                    recommendations.append(rec)

        # Add general recommendations
        if not recommendations:
            recommendations.append("Maintain current strategy - performance is at or above industry benchmarks")
        else:
            recommendations.append("Consider A/B testing to improve underperforming metrics")

        return recommendations[:5]  # Limit to top 5 recommendations

    def _get_metric_recommendation(
        self,
        metric_name: str,
        metric: BenchmarkMetric,
        industry: Industry,
        platform: str,
    ) -> Optional[str]:
        """Get specific recommendation for a metric."""
        recommendations = {
            "ctr": {
                "general": "Improve ad creative quality and relevance to increase CTR",
                "meta": "Test video creatives and carousel formats for better engagement",
                "google": "Optimize ad copy and extensions, improve Quality Score",
                "tiktok": "Use native-style vertical videos with strong hooks in first 3 seconds",
            },
            "cvr": {
                "general": "Optimize landing pages and checkout flow to improve conversion rate",
                "meta": "Ensure landing page matches ad messaging, test different CTAs",
                "google": "Improve landing page relevance, add trust signals",
                "tiktok": "Use mobile-optimized landing pages with clear value propositions",
            },
            "cpc": {
                "general": "Review bidding strategy and audience targeting to reduce CPC",
                "meta": "Expand audiences to reduce competition, test automatic bidding",
                "google": "Improve Quality Score, use negative keywords, adjust bid caps",
                "tiktok": "Test broader targeting and creative refresh to reduce costs",
            },
            "cpm": {
                "general": "Optimize targeting and ad relevance to reduce CPM",
                "meta": "Test different placements and audience expansion",
                "google": "Review targeting settings and campaign structure",
                "tiktok": "Refresh creatives regularly to combat ad fatigue",
            },
            "cpa": {
                "general": "Focus on conversion optimization to reduce acquisition costs",
                "meta": "Use value-based lookalike audiences and conversion optimization",
                "google": "Implement conversion tracking improvements and smart bidding",
                "tiktok": "Test product-focused creatives with clear CTAs",
            },
            "roas": {
                "general": "Optimize for higher-value conversions to improve ROAS",
                "meta": "Implement value-based optimization and exclude low-value segments",
                "google": "Use target ROAS bidding with appropriate targets",
                "tiktok": "Focus on bottom-funnel campaigns for better ROAS",
            },
        }

        if metric_name in recommendations:
            platform_rec = recommendations[metric_name].get(platform)
            return platform_rec or recommendations[metric_name]["general"]

        return None

    def _friendly_metric_name(self, metric_name: str) -> str:
        """Convert metric name to friendly name."""
        names = {
            "ctr": "Click-Through Rate",
            "cvr": "Conversion Rate",
            "cpc": "Cost Per Click",
            "cpm": "CPM",
            "cpa": "Cost Per Acquisition",
            "roas": "ROAS",
        }
        return names.get(metric_name, metric_name.upper())

    def get_industry_report(
        self,
        industry: Industry,
        platform: str,
        region: Region = Region.GLOBAL,
    ) -> Dict[str, Any]:
        """
        Get industry benchmark report.

        Returns:
            Dict with benchmark data for all metrics
        """
        report = {
            "industry": industry.value,
            "platform": platform,
            "region": region.value,
            "metrics": {},
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        for metric_name in ["ctr", "cvr", "cpc", "cpm", "cpa", "roas"]:
            key = f"{industry.value}_{region.value}_{platform}_{metric_name}"
            benchmark = self._benchmark_data.get(key)

            if benchmark:
                report["metrics"][metric_name] = {
                    "p10": benchmark.p10,
                    "p25": benchmark.p25,
                    "median": benchmark.median,
                    "p75": benchmark.p75,
                    "p90": benchmark.p90,
                    "mean": benchmark.mean,
                    "sample_size": benchmark.sample_size,
                }

        return report

    def compare_platforms(
        self,
        tenant_id: str,
        industry: Industry,
        platform_metrics: Dict[str, Dict[str, float]],
    ) -> Dict[str, Any]:
        """
        Compare performance across multiple platforms.

        Args:
            tenant_id: Tenant identifier
            industry: Industry vertical
            platform_metrics: Dict of platform -> metrics dict

        Returns:
            Cross-platform comparison
        """
        comparisons = {}

        for platform, metrics in platform_metrics.items():
            benchmark = self.get_benchmark(
                tenant_id=tenant_id,
                industry=industry,
                region=Region.GLOBAL,
                platform=platform,
                metrics=metrics,
            )

            comparisons[platform] = {
                "overall_percentile": benchmark.overall_percentile,
                "performance_level": benchmark.performance_level.value,
                "strengths": benchmark.strengths,
                "weaknesses": benchmark.weaknesses,
            }

        # Find best performing platform
        best_platform = max(
            comparisons.keys(),
            key=lambda p: comparisons[p]["overall_percentile"]
        )

        return {
            "tenant_id": tenant_id,
            "industry": industry.value,
            "platforms": comparisons,
            "best_performing_platform": best_platform,
            "recommendation": f"Consider reallocating more budget to {best_platform} based on relative performance",
        }


# Singleton instance
benchmarking_service = CompetitorBenchmarkingService()


# =============================================================================
# Convenience Functions
# =============================================================================

def get_benchmark_comparison(
    tenant_id: str,
    industry: str,
    platform: str,
    metrics: Dict[str, float],
) -> Dict[str, Any]:
    """
    Get benchmark comparison for a tenant.

    Returns:
        Dict with benchmark comparison results
    """
    try:
        industry_enum = Industry(industry.lower())
    except ValueError:
        industry_enum = Industry.OTHER

    benchmark = benchmarking_service.get_benchmark(
        tenant_id=tenant_id,
        industry=industry_enum,
        region=Region.GLOBAL,
        platform=platform,
        metrics=metrics,
    )

    return {
        "overall_percentile": benchmark.overall_percentile,
        "performance_level": benchmark.performance_level.value,
        "strengths": benchmark.strengths,
        "weaknesses": benchmark.weaknesses,
        "recommendations": benchmark.recommendations,
        "metrics": {
            name: {
                "your_value": m.your_value,
                "benchmark_median": m.benchmark_median,
                "your_percentile": m.your_percentile,
                "performance": m.performance_level.value,
            }
            for name, m in benchmark.metrics.items()
        },
    }


# =============================================================================
# Advanced Competitor Benchmarking Features (P2 Enhancement)
# =============================================================================

@dataclass
class SeasonalBenchmark:
    """Benchmark adjusted for seasonality."""
    metric: str
    base_benchmark: float
    seasonal_adjustment: float
    adjusted_benchmark: float
    season: str
    confidence: float


@dataclass
class BenchmarkTrend:
    """Trend in benchmark metrics over time."""
    metric: str
    direction: str  # improving, declining, stable
    change_rate: float  # % change per month
    forecast_3m: float
    forecast_6m: float
    industry_context: str


@dataclass
class CompetitivePositionForecast:
    """Forecast of competitive position."""
    current_percentile: float
    forecast_1m_percentile: float
    forecast_3m_percentile: float
    forecast_6m_percentile: float
    trajectory: str  # gaining, losing, maintaining
    key_drivers: List[str]


class SeasonalBenchmarkAdjuster:
    """
    Adjusts benchmarks for seasonal patterns.

    Different industries and metrics have seasonal variations:
    - E-commerce peaks in Q4
    - B2B SaaS peaks in Q1
    - CPG varies by product type
    """

    # Seasonal multipliers by industry and quarter
    SEASONAL_PATTERNS = {
        Industry.ECOMMERCE: {
            "Q1": 0.85, "Q2": 0.95, "Q3": 1.05, "Q4": 1.35,
        },
        Industry.SAAS: {
            "Q1": 1.15, "Q2": 1.05, "Q3": 0.90, "Q4": 0.95,
        },
        Industry.FINANCE: {
            "Q1": 1.10, "Q2": 0.95, "Q3": 0.90, "Q4": 1.05,
        },
        Industry.GAMING: {
            "Q1": 0.90, "Q2": 0.85, "Q3": 0.95, "Q4": 1.30,
        },
    }

    # Metric-specific seasonal variations
    METRIC_SEASONALITY = {
        "ctr": {"Q4": 0.95},  # More competition = lower CTR
        "cpc": {"Q4": 1.25, "Q1": 0.80},  # Higher costs in Q4
        "roas": {"Q4": 1.10},  # Better returns despite costs
        "conversion_rate": {"Q4": 1.15},  # Higher purchase intent
    }

    def get_current_quarter(self) -> str:
        """Get current quarter."""
        month = datetime.now().month
        if month <= 3:
            return "Q1"
        elif month <= 6:
            return "Q2"
        elif month <= 9:
            return "Q3"
        return "Q4"

    def adjust_benchmark(
        self,
        metric: str,
        base_value: float,
        industry: Industry,
        date: Optional[datetime] = None,
    ) -> SeasonalBenchmark:
        """Adjust benchmark for seasonality."""
        if date:
            month = date.month
            quarter = f"Q{(month - 1) // 3 + 1}"
        else:
            quarter = self.get_current_quarter()

        # Get industry seasonal factor
        industry_patterns = self.SEASONAL_PATTERNS.get(industry, {})
        industry_factor = industry_patterns.get(quarter, 1.0)

        # Get metric-specific factor
        metric_patterns = self.METRIC_SEASONALITY.get(metric, {})
        metric_factor = metric_patterns.get(quarter, 1.0)

        # Combined adjustment
        total_adjustment = industry_factor * metric_factor
        adjusted_value = base_value * total_adjustment

        return SeasonalBenchmark(
            metric=metric,
            base_benchmark=round(base_value, 3),
            seasonal_adjustment=round(total_adjustment, 3),
            adjusted_benchmark=round(adjusted_value, 3),
            season=quarter,
            confidence=0.85 if industry in self.SEASONAL_PATTERNS else 0.6,
        )

    def get_seasonal_context(self, industry: Industry) -> str:
        """Get seasonal context for current period."""
        quarter = self.get_current_quarter()
        patterns = self.SEASONAL_PATTERNS.get(industry, {})
        factor = patterns.get(quarter, 1.0)

        if factor > 1.2:
            return f"Peak season for {industry.value} - benchmarks elevated"
        elif factor < 0.9:
            return f"Off-peak season for {industry.value} - benchmarks reduced"
        return f"Normal season for {industry.value}"


class BenchmarkTrendAnalyzer:
    """
    Analyzes trends in benchmark metrics over time.

    Tracks:
    - Historical benchmark changes
    - Industry-wide trends
    - Metric correlations
    """

    def __init__(self):
        self._historical_benchmarks: Dict[str, List[Tuple[datetime, float]]] = {}

    def record_benchmark(
        self,
        metric: str,
        industry: str,
        platform: str,
        value: float,
    ):
        """Record historical benchmark."""
        key = f"{metric}:{industry}:{platform}"
        if key not in self._historical_benchmarks:
            self._historical_benchmarks[key] = []

        self._historical_benchmarks[key].append((
            datetime.now(timezone.utc),
            value,
        ))

        # Keep last 365 days
        cutoff = datetime.now(timezone.utc) - timedelta(days=365)
        self._historical_benchmarks[key] = [
            (t, v) for t, v in self._historical_benchmarks[key] if t > cutoff
        ]

    def analyze_trend(
        self,
        metric: str,
        industry: str,
        platform: str,
    ) -> BenchmarkTrend:
        """Analyze trend for a metric."""
        key = f"{metric}:{industry}:{platform}"
        history = self._historical_benchmarks.get(key, [])

        if len(history) < 3:
            return BenchmarkTrend(
                metric=metric,
                direction="stable",
                change_rate=0,
                forecast_3m=0,
                forecast_6m=0,
                industry_context="Insufficient historical data",
            )

        # Calculate monthly change rate
        values = [v for _, v in sorted(history)]
        months = len(values)

        if values[0] > 0:
            total_change = (values[-1] - values[0]) / values[0]
            monthly_rate = total_change / max(1, months / 30)
        else:
            monthly_rate = 0

        # Determine direction
        if monthly_rate > 0.02:
            direction = "improving"
        elif monthly_rate < -0.02:
            direction = "declining"
        else:
            direction = "stable"

        # Forecast
        current_value = values[-1]
        forecast_3m = current_value * (1 + monthly_rate * 3)
        forecast_6m = current_value * (1 + monthly_rate * 6)

        # Generate context
        context = self._generate_industry_context(metric, direction, industry)

        return BenchmarkTrend(
            metric=metric,
            direction=direction,
            change_rate=round(monthly_rate * 100, 2),
            forecast_3m=round(forecast_3m, 3),
            forecast_6m=round(forecast_6m, 3),
            industry_context=context,
        )

    def _generate_industry_context(
        self,
        metric: str,
        direction: str,
        industry: str,
    ) -> str:
        """Generate context for trend."""
        contexts = {
            ("ctr", "improving"): f"Click-through rates rising in {industry} - competition may be decreasing",
            ("ctr", "declining"): f"CTR declining in {industry} - ad fatigue or competition increasing",
            ("roas", "improving"): f"ROAS improving across {industry} - optimize for scale",
            ("roas", "declining"): f"ROAS pressure in {industry} - focus on efficiency",
            ("cpc", "improving"): f"CPCs falling in {industry} - opportunity to increase volume",
            ("cpc", "declining"): f"CPCs rising in {industry} - expect margin pressure",
        }

        return contexts.get((metric, direction), f"{metric} {direction} in {industry}")


class CompetitivePositionForecaster:
    """
    Forecasts future competitive position.

    Uses current trends and momentum to predict:
    - Future percentile ranking
    - Trajectory direction
    - Key improvement drivers
    """

    def __init__(self, service: CompetitorBenchmarkingService):
        self.service = service
        self._position_history: Dict[str, List[Tuple[datetime, float]]] = {}

    def record_position(self, tenant_id: str, percentile: float):
        """Record historical position."""
        if tenant_id not in self._position_history:
            self._position_history[tenant_id] = []

        self._position_history[tenant_id].append((
            datetime.now(timezone.utc),
            percentile,
        ))

        # Keep last 180 days
        cutoff = datetime.now(timezone.utc) - timedelta(days=180)
        self._position_history[tenant_id] = [
            (t, p) for t, p in self._position_history[tenant_id] if t > cutoff
        ]

    def forecast_position(
        self,
        tenant_id: str,
        current_percentile: float,
        metric_trends: Dict[str, float],  # metric -> monthly change rate
    ) -> CompetitivePositionForecast:
        """Forecast future competitive position."""
        history = self._position_history.get(tenant_id, [])

        # Calculate momentum
        if len(history) >= 2:
            recent = [p for _, p in history[-5:]]
            momentum = (recent[-1] - recent[0]) / max(1, len(recent))
        else:
            momentum = 0

        # Combine momentum with metric trends
        avg_improvement = statistics.mean(metric_trends.values()) if metric_trends else 0
        combined_rate = (momentum + avg_improvement * 2) / 3  # Weight recent trends more

        # Forecast future positions
        forecast_1m = min(99, max(1, current_percentile + combined_rate * 30))
        forecast_3m = min(99, max(1, current_percentile + combined_rate * 90))
        forecast_6m = min(99, max(1, current_percentile + combined_rate * 180))

        # Determine trajectory
        if combined_rate > 0.1:
            trajectory = "gaining"
        elif combined_rate < -0.1:
            trajectory = "losing"
        else:
            trajectory = "maintaining"

        # Identify key drivers
        key_drivers = []
        for metric, trend in sorted(metric_trends.items(), key=lambda x: abs(x[1]), reverse=True)[:3]:
            if trend > 0:
                key_drivers.append(f"Improving {metric}")
            elif trend < 0:
                key_drivers.append(f"Declining {metric} - needs attention")

        if not key_drivers:
            key_drivers.append("Performance is stable")

        return CompetitivePositionForecast(
            current_percentile=round(current_percentile, 1),
            forecast_1m_percentile=round(forecast_1m, 1),
            forecast_3m_percentile=round(forecast_3m, 1),
            forecast_6m_percentile=round(forecast_6m, 1),
            trajectory=trajectory,
            key_drivers=key_drivers,
        )

    def get_improvement_opportunities(
        self,
        tenant_id: str,
        current_metrics: Dict[str, float],
        benchmarks: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        """Identify biggest improvement opportunities."""
        opportunities = []

        for metric, your_value in current_metrics.items():
            benchmark = benchmarks.get(metric)
            if benchmark is None:
                continue

            gap = (benchmark - your_value) / benchmark * 100 if benchmark > 0 else 0

            if gap > 10:  # More than 10% below benchmark
                # Estimate impact of closing gap
                potential_gain = min(gap * 0.5, 30)  # Can close ~50% of gap

                opportunities.append({
                    "metric": metric,
                    "your_value": round(your_value, 3),
                    "benchmark": round(benchmark, 3),
                    "gap_percent": round(gap, 1),
                    "potential_percentile_gain": round(potential_gain, 1),
                    "priority": "high" if gap > 30 else "medium",
                    "recommendation": f"Focus on improving {metric} - {gap:.0f}% below benchmark",
                })

        # Sort by potential gain
        opportunities.sort(key=lambda x: x["potential_percentile_gain"], reverse=True)

        return opportunities[:5]


# Singleton instances for P2 enhancements
seasonal_adjuster = SeasonalBenchmarkAdjuster()
benchmark_trend_analyzer = BenchmarkTrendAnalyzer()
position_forecaster = CompetitivePositionForecaster(benchmarking_service)
