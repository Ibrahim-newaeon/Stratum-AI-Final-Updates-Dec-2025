# =============================================================================
# Stratum AI - Signal Health Calculator
# =============================================================================
"""
Signal Health Calculator for Trust-Gated Autopilot.

Computes a composite signal health score from four components:
1. EMQ Score (40%): Event Match Quality from platform data
2. Freshness Score (25%): How recent and complete the data is
3. Variance Score (20%): Consistency between reported and actual metrics
4. Anomaly Score (15%): Detection of unusual patterns

The composite score determines whether automation can proceed:
- 70-100: HEALTHY - Full autopilot enabled
- 40-69: DEGRADED - Limited actions, alert only
- 0-39: UNHEALTHY - Manual intervention required
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Optional

from app.stratum.models import SignalHealth

logger = logging.getLogger("stratum.signal_health")


class HealthStatus(str, Enum):
    """Signal health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"


@dataclass
class SignalHealthConfig:
    """Configuration for signal health thresholds."""

    healthy_threshold: float = 70.0
    degraded_threshold: float = 40.0

    # Component weights (must sum to 1.0)
    # When CDP data is available, weights are redistributed
    emq_weight: float = 0.40
    freshness_weight: float = 0.25
    variance_weight: float = 0.20
    anomaly_weight: float = 0.15

    # CDP weight (when available, other weights are proportionally reduced)
    cdp_weight: float = 0.10
    cdp_enabled: bool = True

    # Freshness thresholds
    max_data_age_hours: int = 24
    stale_data_age_hours: int = 48

    # Variance thresholds
    max_acceptable_variance: float = 0.15  # 15%
    warning_variance: float = 0.10  # 10%

    # Anomaly thresholds
    anomaly_zscore_threshold: float = 3.0

    def get_weights(self, include_cdp: bool = False) -> dict[str, float]:
        """
        Get component weights, optionally including CDP.

        When CDP is included, other weights are proportionally reduced
        to maintain a total weight of 1.0.
        """
        if not include_cdp or not self.cdp_enabled:
            return {
                "emq": self.emq_weight,
                "freshness": self.freshness_weight,
                "variance": self.variance_weight,
                "anomaly": self.anomaly_weight,
                "cdp": 0.0,
            }

        # Reduce base weights proportionally to make room for CDP
        scale_factor = 1.0 - self.cdp_weight
        return {
            "emq": self.emq_weight * scale_factor,
            "freshness": self.freshness_weight * scale_factor,
            "variance": self.variance_weight * scale_factor,
            "anomaly": self.anomaly_weight * scale_factor,
            "cdp": self.cdp_weight,
        }


class SignalHealthCalculator:
    """
    Calculates composite signal health from multiple data quality signals.

    This calculator integrates with the existing EMQ calculation system
    and adds freshness, variance, and anomaly detection components.

    Usage:
        calculator = SignalHealthCalculator()

        health = calculator.calculate(
            emq_scores=[8.5, 7.2],  # Platform EMQ scores (0-10)
            last_data_received=datetime.now(UTC) - timedelta(hours=2),
            platform_revenue=10000.0,
            ga4_revenue=9500.0,
            historical_variance=[0.05, 0.08, 0.12],
        )

        if health.is_autopilot_safe():
            # Proceed with automation
            ...
    """

    def __init__(self, config: Optional[SignalHealthConfig] = None):
        """Initialize with optional custom configuration."""
        self.config = config or SignalHealthConfig()

    def calculate(
        self,
        emq_scores: Optional[list[float]] = None,
        last_data_received: Optional[datetime] = None,
        platform_revenue: Optional[float] = None,
        ga4_revenue: Optional[float] = None,
        historical_variance: Optional[list[float]] = None,
        current_metrics: Optional[dict[str, float]] = None,
        historical_metrics: Optional[list[dict[str, float]]] = None,
        cdp_emq_score: Optional[float] = None,
    ) -> SignalHealth:
        """
        Calculate composite signal health score.

        Args:
            emq_scores: List of EMQ scores (0-10 scale) from platforms
            last_data_received: Timestamp of most recent data sync
            platform_revenue: Revenue reported by ad platforms
            ga4_revenue: Revenue reported by GA4/analytics
            historical_variance: List of historical variance percentages
            current_metrics: Current period metrics for anomaly detection
            historical_metrics: Historical metrics for anomaly comparison
            cdp_emq_score: CDP EMQ score from CDPEMQAggregator (0-100)

        Returns:
            SignalHealth object with composite score and component breakdown
        """
        issues = []

        # Calculate each component
        emq_score = self._calculate_emq_component(emq_scores, issues)
        freshness_score = self._calculate_freshness_component(last_data_received, issues)
        variance_score = self._calculate_variance_component(
            platform_revenue, ga4_revenue, historical_variance, issues
        )
        anomaly_score = self._calculate_anomaly_component(
            current_metrics, historical_metrics, issues
        )

        # Calculate CDP component if available
        cdp_score = self._calculate_cdp_component(cdp_emq_score, issues)
        include_cdp = cdp_score is not None

        # Get weights (with or without CDP)
        weights = self.config.get_weights(include_cdp=include_cdp)

        # Calculate weighted composite score
        overall_score = (
            emq_score * weights["emq"]
            + freshness_score * weights["freshness"]
            + variance_score * weights["variance"]
            + anomaly_score * weights["anomaly"]
        )

        # Add CDP component if available
        if include_cdp:
            overall_score += cdp_score * weights["cdp"]

        # Determine status
        if overall_score >= self.config.healthy_threshold:
            status = HealthStatus.HEALTHY.value
        elif overall_score >= self.config.degraded_threshold:
            status = HealthStatus.DEGRADED.value
        else:
            status = HealthStatus.CRITICAL.value

        health = SignalHealth(
            overall_score=round(overall_score, 1),
            emq_score=round(emq_score, 1),
            freshness_score=round(freshness_score, 1),
            variance_score=round(variance_score, 1),
            anomaly_score=round(anomaly_score, 1),
            cdp_emq_score=round(cdp_score, 1) if cdp_score is not None else None,
            status=status,
            issues=issues,
            last_updated=datetime.now(UTC),
        )

        cdp_info = f", CDP:{health.cdp_emq_score}" if health.cdp_emq_score is not None else ""
        logger.info(
            f"Signal health calculated: {health.overall_score} ({health.status}) "
            f"[EMQ:{health.emq_score}, Fresh:{health.freshness_score}, "
            f"Var:{health.variance_score}, Anom:{health.anomaly_score}{cdp_info}]"
        )

        return health

    def _calculate_cdp_component(
        self,
        cdp_emq_score: Optional[float],
        issues: list[str],
    ) -> Optional[float]:
        """
        Calculate CDP EMQ component score (0-100).

        Returns None if CDP data is not available.
        """
        if cdp_emq_score is None:
            return None

        # CDP score is already 0-100 from CDPEMQAggregator
        score = min(100, max(0, cdp_emq_score))

        if score < 70:
            issues.append(f"CDP EMQ below target: {score:.1f} (target: 70+)")

        return score

    def _calculate_emq_component(
        self,
        emq_scores: Optional[list[float]],
        issues: list[str],
    ) -> float:
        """
        Calculate EMQ component score (0-100).

        Converts platform EMQ scores (0-10) to a 0-100 score.
        """
        if not emq_scores:
            issues.append("No EMQ data available - using default score")
            return 75.0  # Default moderate score

        # Convert 0-10 scores to 0-100 and average
        converted_scores = [min(100, max(0, score * 10)) for score in emq_scores]
        avg_score = sum(converted_scores) / len(converted_scores)

        if avg_score < 70:
            issues.append(f"EMQ score below target: {avg_score:.1f} (target: 70+)")

        return avg_score

    def _calculate_freshness_component(
        self,
        last_data_received: Optional[datetime],
        issues: list[str],
    ) -> float:
        """
        Calculate data freshness score (0-100).

        Based on how recently data was received:
        - < max_data_age_hours: 100
        - max_data_age_hours to stale_data_age_hours: Linear decay
        - > stale_data_age_hours: 0
        """
        if not last_data_received:
            issues.append("No data timestamp available - assuming stale")
            return 50.0  # Moderate penalty

        now = datetime.now(UTC)
        age_hours = (now - last_data_received).total_seconds() / 3600

        if age_hours <= self.config.max_data_age_hours:
            return 100.0
        elif age_hours >= self.config.stale_data_age_hours:
            issues.append(f"Data is stale ({age_hours:.1f}h old)")
            return 0.0
        else:
            # Linear decay between thresholds
            range_hours = self.config.stale_data_age_hours - self.config.max_data_age_hours
            decay = (age_hours - self.config.max_data_age_hours) / range_hours
            score = 100.0 * (1.0 - decay)
            issues.append(f"Data freshness degraded ({age_hours:.1f}h old)")
            return score

    def _calculate_variance_component(
        self,
        platform_revenue: Optional[float],
        ga4_revenue: Optional[float],
        historical_variance: Optional[list[float]],
        issues: list[str],
    ) -> float:
        """
        Calculate variance score (0-100).

        Based on:
        1. Current variance between platform and GA4 revenue
        2. Historical variance trend
        """
        if platform_revenue is None or ga4_revenue is None:
            if historical_variance:
                # Use historical average if current data unavailable
                avg_variance = sum(historical_variance) / len(historical_variance)
                return self._variance_to_score(avg_variance, issues)
            return 80.0  # Default moderate-good score

        # Calculate current variance
        if ga4_revenue > 0:
            current_variance = abs(platform_revenue - ga4_revenue) / ga4_revenue
        elif platform_revenue > 0:
            current_variance = 1.0  # 100% variance if GA4 shows 0
        else:
            current_variance = 0.0  # Both zero = no variance

        return self._variance_to_score(current_variance, issues)

    def _variance_to_score(
        self,
        variance: float,
        issues: list[str],
    ) -> float:
        """Convert variance percentage to 0-100 score."""
        if variance <= self.config.warning_variance:
            return 100.0
        elif variance >= self.config.max_acceptable_variance:
            issues.append(f"High attribution variance: {variance*100:.1f}%")
            # Linear decay from warning to max
            excess = variance - self.config.warning_variance
            max_excess = self.config.max_acceptable_variance - self.config.warning_variance
            if excess >= max_excess * 2:
                return 0.0
            decay = excess / (max_excess * 2)
            return 100.0 * (1.0 - decay)
        else:
            # Linear decay from warning to max_acceptable
            excess = variance - self.config.warning_variance
            max_excess = self.config.max_acceptable_variance - self.config.warning_variance
            decay = excess / max_excess * 0.3  # Max 30% reduction
            return 100.0 * (1.0 - decay)

    def _calculate_anomaly_component(
        self,
        current_metrics: Optional[dict[str, float]],
        historical_metrics: Optional[list[dict[str, float]]],
        issues: list[str],
    ) -> float:
        """
        Calculate anomaly detection score (0-100).

        Detects unusual patterns in key metrics using z-score analysis.
        """
        if not current_metrics or not historical_metrics or len(historical_metrics) < 7:
            return 90.0  # Default good score with insufficient data

        anomaly_count = 0
        metrics_checked = 0

        for metric_name in ["spend", "conversions", "cpa", "roas"]:
            if metric_name not in current_metrics:
                continue

            # Get historical values
            historical_values = [
                m.get(metric_name) for m in historical_metrics if m.get(metric_name) is not None
            ]

            if len(historical_values) < 7:
                continue

            metrics_checked += 1
            current_value = current_metrics[metric_name]

            # Calculate z-score
            mean = sum(historical_values) / len(historical_values)
            variance = sum((x - mean) ** 2 for x in historical_values) / len(historical_values)
            std_dev = variance**0.5

            if std_dev > 0:
                z_score = abs(current_value - mean) / std_dev
                if z_score > self.config.anomaly_zscore_threshold:
                    anomaly_count += 1
                    issues.append(f"Anomaly detected in {metric_name}: z-score={z_score:.2f}")

        if metrics_checked == 0:
            return 90.0

        # Score based on anomaly ratio
        anomaly_ratio = anomaly_count / metrics_checked
        if anomaly_ratio == 0:
            return 100.0
        elif anomaly_ratio <= 0.25:
            return 80.0
        elif anomaly_ratio <= 0.5:
            return 50.0
        else:
            return 20.0

    def calculate_from_emq_drivers(
        self,
        event_match_rate: float = 75.0,
        pixel_coverage: float = 80.0,
        conversion_latency: float = 65.0,
        attribution_accuracy: float = 70.0,
        data_freshness: float = 85.0,
    ) -> SignalHealth:
        """
        Calculate signal health from the 5 EMQ driver scores.

        This provides compatibility with the existing EMQ calculation system
        that uses the 5-driver model.

        Args:
            event_match_rate: EMQ driver (0-100)
            pixel_coverage: EMQ driver (0-100)
            conversion_latency: EMQ driver (0-100)
            attribution_accuracy: EMQ driver (0-100)
            data_freshness: EMQ driver (0-100)

        Returns:
            SignalHealth with scores mapped from EMQ drivers
        """
        issues = []

        # Map drivers to our 4-component model
        # EMQ Score = weighted average of match rate, pixel coverage, latency
        emq_weights = {"event_match_rate": 0.4, "pixel_coverage": 0.35, "conversion_latency": 0.25}
        emq_component = (
            event_match_rate * emq_weights["event_match_rate"]
            + pixel_coverage * emq_weights["pixel_coverage"]
            + conversion_latency * emq_weights["conversion_latency"]
        )

        # Freshness component from data freshness driver
        freshness_component = data_freshness

        # Variance component from attribution accuracy
        variance_component = attribution_accuracy

        # Anomaly component (no direct driver, estimate from consistency)
        anomaly_component = (emq_component + variance_component) / 2

        # Check for issues
        if event_match_rate < 70:
            issues.append(f"Event match rate low: {event_match_rate:.1f}%")
        if pixel_coverage < 75:
            issues.append(f"Pixel coverage needs improvement: {pixel_coverage:.1f}%")
        if conversion_latency < 60:
            issues.append(f"Conversion latency high: {conversion_latency:.1f}%")
        if attribution_accuracy < 70:
            issues.append(f"Attribution accuracy degraded: {attribution_accuracy:.1f}%")
        if data_freshness < 80:
            issues.append(f"Data freshness issue: {data_freshness:.1f}%")

        # Calculate overall
        overall_score = (
            emq_component * self.config.emq_weight
            + freshness_component * self.config.freshness_weight
            + variance_component * self.config.variance_weight
            + anomaly_component * self.config.anomaly_weight
        )

        # Determine status
        if overall_score >= self.config.healthy_threshold:
            status = HealthStatus.HEALTHY.value
        elif overall_score >= self.config.degraded_threshold:
            status = HealthStatus.DEGRADED.value
        else:
            status = HealthStatus.CRITICAL.value

        return SignalHealth(
            overall_score=round(overall_score, 1),
            emq_score=round(emq_component, 1),
            freshness_score=round(freshness_component, 1),
            variance_score=round(variance_component, 1),
            anomaly_score=round(anomaly_component, 1),
            status=status,
            issues=issues,
            last_updated=datetime.now(UTC),
        )
