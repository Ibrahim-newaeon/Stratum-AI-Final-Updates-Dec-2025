# =============================================================================
# Anomaly Detection (Spend/ROAS/CPA)
# =============================================================================
"""
Anomaly Detection using Z-scores.
From AI_Logic_Formulas_Pseudocode.md Section 4.

Goal: Catch "something broke" early.
"""

import statistics
from typing import Optional

from app.analytics.logic.types import (
    AlertSeverity,
    AnomalyParams,
    AnomalyResult,
)


def anomaly_zscore(
    metric_series: list[float],
    current_value: float,
    window: int = 14,
) -> float:
    """
    Calculate Z-score for anomaly detection.

    Args:
        metric_series: Historical values (last N days, excluding today)
        current_value: Today's value
        window: Number of days to use for baseline (default 14)

    Returns:
        Z-score (positive = above average, negative = below)
    """
    if len(metric_series) < 3:
        return 0.0

    # Use last `window` days
    series = metric_series[-window:] if len(metric_series) > window else metric_series

    try:
        mu = statistics.mean(series)
        sd = statistics.stdev(series) if len(series) > 1 else 0.0

        if sd <= 1e-9:
            return 0.0

        return (current_value - mu) / sd
    except (statistics.StatisticsError, ZeroDivisionError):
        return 0.0


def get_severity(zscore: float) -> AlertSeverity:
    """Map Z-score to severity level."""
    abs_z = abs(zscore)
    if abs_z >= 4.0:
        return AlertSeverity.CRITICAL
    elif abs_z >= 3.0:
        return AlertSeverity.HIGH
    elif abs_z >= 2.5:
        return AlertSeverity.MEDIUM
    else:
        return AlertSeverity.LOW


def detect_anomalies(
    metrics_series: dict[str, list[float]],
    current_values: dict[str, float],
    params: Optional[AnomalyParams] = None,
) -> list[AnomalyResult]:
    """
    Detect anomalies across multiple metrics.

    Args:
        metrics_series: Dict mapping metric name to historical values
        current_values: Dict mapping metric name to today's value
        params: Anomaly detection parameters

    Returns:
        List of AnomalyResult for detected anomalies
    """
    if params is None:
        params = AnomalyParams()

    anomalies = []

    for metric in params.metrics_to_check:
        if metric not in metrics_series or metric not in current_values:
            continue

        series = metrics_series[metric]
        current = current_values[metric]

        z = anomaly_zscore(series, current, params.window_days)

        # Check if it's an anomaly
        is_anomaly = abs(z) >= params.zscore_threshold

        if is_anomaly or abs(z) >= 2.0:  # Include near-anomalies for visibility
            # Calculate baseline stats
            window_series = (
                series[-params.window_days :] if len(series) > params.window_days else series
            )
            try:
                baseline_mean = statistics.mean(window_series)
                baseline_std = statistics.stdev(window_series) if len(window_series) > 1 else 0.0
            except statistics.StatisticsError:
                baseline_mean = 0.0
                baseline_std = 0.0

            anomalies.append(
                AnomalyResult(
                    metric=metric,
                    zscore=round(z, 2),
                    severity=get_severity(z) if is_anomaly else AlertSeverity.LOW,
                    current_value=current,
                    baseline_mean=round(baseline_mean, 2),
                    baseline_std=round(baseline_std, 2),
                    is_anomaly=is_anomaly,
                    direction="high" if z > 0 else "low",
                )
            )

    # Sort by absolute Z-score (most significant first)
    anomalies.sort(key=lambda x: abs(x.zscore), reverse=True)

    return anomalies


def detect_entity_anomalies(
    entity_id: str,
    metrics_history: dict[str, list[float]],
    current_metrics: dict[str, float],
    params: Optional[AnomalyParams] = None,
) -> dict:
    """
    Detect anomalies for a specific entity (campaign, account, etc.).

    Args:
        entity_id: Entity identifier
        metrics_history: Historical metrics for this entity
        current_metrics: Today's metrics
        params: Detection parameters

    Returns:
        Dict with entity_id and list of anomalies
    """
    anomalies = detect_anomalies(metrics_history, current_metrics, params)

    # Filter to only actual anomalies
    significant_anomalies = [a for a in anomalies if a.is_anomaly]

    return {
        "entity_id": entity_id,
        "anomalies": significant_anomalies,
        "anomaly_count": len(significant_anomalies),
        "has_critical": any(a.severity == AlertSeverity.CRITICAL for a in significant_anomalies),
        "has_high": any(a.severity == AlertSeverity.HIGH for a in significant_anomalies),
    }


def generate_anomaly_message(anomaly: AnomalyResult) -> str:
    """Generate human-readable message for an anomaly."""
    direction = "increased" if anomaly.direction == "high" else "decreased"
    pct_change = (
        abs(anomaly.current_value - anomaly.baseline_mean) / max(anomaly.baseline_mean, 1) * 100
    )

    return (
        f"{anomaly.metric} {direction} significantly "
        f"(z-score: {anomaly.zscore:.1f}, "
        f"current: {anomaly.current_value:.2f}, "
        f"baseline avg: {anomaly.baseline_mean:.2f}, "
        f"change: {pct_change:.1f}%)"
    )
