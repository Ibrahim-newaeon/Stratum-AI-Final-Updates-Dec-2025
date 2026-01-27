# =============================================================================
# Stratum AI - Real-Time Conversion Latency Tracking Service
# =============================================================================
"""
Service for tracking conversion latency in real-time.

Measures the time between:
- Click event and conversion event
- Pixel fire and CAPI event delivery
- Event send and platform acknowledgment

Used for:
- EMQ accuracy improvements
- Identifying attribution window issues
- Diagnosing data freshness problems
"""

import statistics
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class LatencyMeasurement:
    """A single latency measurement."""

    measurement_id: str
    platform: str
    event_type: str  # click_to_conversion, pixel_to_capi, send_to_ack
    start_time: datetime
    end_time: datetime
    latency_ms: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LatencyStats:
    """Aggregated latency statistics."""

    count: int = 0
    min_ms: float = 0.0
    max_ms: float = 0.0
    avg_ms: float = 0.0
    median_ms: float = 0.0
    p75_ms: float = 0.0
    p90_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    std_dev_ms: float = 0.0


@dataclass
class PendingConversion:
    """Tracks a pending conversion awaiting completion."""

    event_id: str
    platform: str
    event_type: str
    start_time: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


class ConversionLatencyTracker:
    """
    Real-time conversion latency tracking.

    Tracks three types of latency:
    1. click_to_conversion: Time from click to conversion event
    2. pixel_to_capi: Time from pixel fire to CAPI send
    3. send_to_ack: Time from CAPI send to platform acknowledgment

    Usage:
        tracker = ConversionLatencyTracker()

        # Start tracking a click
        tracker.start_tracking("click_123", "meta", "click_to_conversion")

        # Later, when conversion happens
        tracker.end_tracking("click_123", "meta", "click_to_conversion")

        # Get latency stats
        stats = tracker.get_stats("meta", "click_to_conversion")
    """

    def __init__(self, max_pending_age_hours: int = 168):  # 7 days default
        self._pending: dict[str, PendingConversion] = {}
        self._measurements: list[LatencyMeasurement] = []
        self._lock = threading.RLock()
        self._max_pending_age = timedelta(hours=max_pending_age_hours)

        # In-memory aggregated stats by platform and event type
        self._stats_cache: dict[str, dict[str, list[float]]] = defaultdict(
            lambda: defaultdict(list)
        )

    def start_tracking(
        self,
        event_id: str,
        platform: str,
        event_type: str,
        start_time: Optional[datetime] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        """
        Start tracking latency for an event.

        Args:
            event_id: Unique identifier for the event
            platform: Platform name (meta, google, tiktok, etc.)
            event_type: Type of latency being tracked
            start_time: When the event started (defaults to now)
            metadata: Additional event metadata
        """
        with self._lock:
            key = f"{platform}:{event_type}:{event_id}"

            if key in self._pending:
                logger.debug(f"Overwriting pending tracking for {key}")

            self._pending[key] = PendingConversion(
                event_id=event_id,
                platform=platform,
                event_type=event_type,
                start_time=start_time or datetime.now(UTC),
                metadata=metadata or {},
            )

    def end_tracking(
        self,
        event_id: str,
        platform: str,
        event_type: str,
        end_time: Optional[datetime] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[float]:
        """
        End tracking and record the latency measurement.

        Args:
            event_id: The event identifier
            platform: Platform name
            event_type: Type of latency
            end_time: When the event completed (defaults to now)
            metadata: Additional metadata to merge

        Returns:
            The latency in milliseconds, or None if not found
        """
        with self._lock:
            key = f"{platform}:{event_type}:{event_id}"

            pending = self._pending.pop(key, None)
            if not pending:
                logger.debug(f"No pending tracking found for {key}")
                return None

            end = end_time or datetime.now(UTC)

            # Handle timezone comparison
            start = pending.start_time
            if start.tzinfo is None and end.tzinfo is not None:
                start = start.replace(tzinfo=UTC)
            elif start.tzinfo is not None and end.tzinfo is None:
                end = end.replace(tzinfo=UTC)

            latency_ms = (end - start).total_seconds() * 1000

            # Don't record negative latencies (clock issues)
            if latency_ms < 0:
                logger.warning(f"Negative latency recorded for {key}: {latency_ms}ms")
                return None

            # Merge metadata
            combined_metadata = {**pending.metadata}
            if metadata:
                combined_metadata.update(metadata)

            measurement = LatencyMeasurement(
                measurement_id=f"{key}_{end.timestamp()}",
                platform=platform,
                event_type=event_type,
                start_time=start,
                end_time=end,
                latency_ms=latency_ms,
                metadata=combined_metadata,
            )

            self._measurements.append(measurement)
            self._stats_cache[platform][event_type].append(latency_ms)

            # Keep only last 100k measurements in memory
            if len(self._measurements) > 100000:
                self._measurements = self._measurements[-100000:]

            # Keep only last 10k latencies per platform/type for stats
            if len(self._stats_cache[platform][event_type]) > 10000:
                self._stats_cache[platform][event_type] = self._stats_cache[platform][event_type][
                    -10000:
                ]

            return latency_ms

    def record_latency(
        self,
        platform: str,
        event_type: str,
        latency_ms: float,
        event_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        """
        Directly record a latency measurement (when start/end times are known).

        Args:
            platform: Platform name
            event_type: Type of latency
            latency_ms: The latency in milliseconds
            event_id: Optional event identifier
            metadata: Optional metadata
        """
        with self._lock:
            now = datetime.now(UTC)

            measurement = LatencyMeasurement(
                measurement_id=event_id or f"{platform}_{event_type}_{now.timestamp()}",
                platform=platform,
                event_type=event_type,
                start_time=now - timedelta(milliseconds=latency_ms),
                end_time=now,
                latency_ms=latency_ms,
                metadata=metadata or {},
            )

            self._measurements.append(measurement)
            self._stats_cache[platform][event_type].append(latency_ms)

    def get_stats(
        self,
        platform: Optional[str] = None,
        event_type: Optional[str] = None,
        period_hours: int = 24,
    ) -> LatencyStats:
        """
        Get latency statistics.

        Args:
            platform: Filter by platform (None for all)
            event_type: Filter by event type (None for all)
            period_hours: Time period to analyze

        Returns:
            Aggregated latency statistics
        """
        with self._lock:
            cutoff = datetime.now(UTC) - timedelta(hours=period_hours)

            # Filter measurements
            measurements = [
                m
                for m in self._measurements
                if m.end_time >= cutoff
                and (platform is None or m.platform == platform)
                and (event_type is None or m.event_type == event_type)
            ]

            if not measurements:
                return LatencyStats()

            latencies = [m.latency_ms for m in measurements]

            return self._calculate_stats(latencies)

    def get_stats_by_platform(
        self,
        period_hours: int = 24,
    ) -> dict[str, LatencyStats]:
        """Get latency statistics grouped by platform."""
        with self._lock:
            cutoff = datetime.now(UTC) - timedelta(hours=period_hours)

            # Group by platform
            by_platform: dict[str, list[float]] = defaultdict(list)

            for m in self._measurements:
                if m.end_time >= cutoff:
                    by_platform[m.platform].append(m.latency_ms)

            return {
                platform: self._calculate_stats(latencies)
                for platform, latencies in by_platform.items()
            }

    def get_stats_by_event_type(
        self,
        platform: Optional[str] = None,
        period_hours: int = 24,
    ) -> dict[str, LatencyStats]:
        """Get latency statistics grouped by event type."""
        with self._lock:
            cutoff = datetime.now(UTC) - timedelta(hours=period_hours)

            by_type: dict[str, list[float]] = defaultdict(list)

            for m in self._measurements:
                if m.end_time >= cutoff and (platform is None or m.platform == platform):
                    by_type[m.event_type].append(m.latency_ms)

            return {
                event_type: self._calculate_stats(latencies)
                for event_type, latencies in by_type.items()
            }

    def _calculate_stats(self, latencies: list[float]) -> LatencyStats:
        """Calculate statistics from a list of latencies."""
        if not latencies:
            return LatencyStats()

        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)

        return LatencyStats(
            count=n,
            min_ms=round(sorted_latencies[0], 2),
            max_ms=round(sorted_latencies[-1], 2),
            avg_ms=round(statistics.mean(latencies), 2),
            median_ms=round(statistics.median(latencies), 2),
            p75_ms=round(sorted_latencies[int(n * 0.75)], 2) if n > 1 else sorted_latencies[0],
            p90_ms=round(sorted_latencies[int(n * 0.90)], 2) if n > 1 else sorted_latencies[0],
            p95_ms=round(sorted_latencies[int(n * 0.95)], 2) if n > 1 else sorted_latencies[0],
            p99_ms=round(sorted_latencies[int(n * 0.99)], 2) if n > 1 else sorted_latencies[0],
            std_dev_ms=round(statistics.stdev(latencies), 2) if n > 1 else 0.0,
        )

    def get_latency_timeline(
        self,
        platform: str,
        event_type: str,
        period_hours: int = 24,
        bucket_minutes: int = 60,
    ) -> list[dict[str, Any]]:
        """
        Get latency over time for charting.

        Returns a list of time buckets with average latency.
        """
        with self._lock:
            cutoff = datetime.now(UTC) - timedelta(hours=period_hours)
            bucket_size = timedelta(minutes=bucket_minutes)

            # Filter measurements
            measurements = [
                m
                for m in self._measurements
                if m.end_time >= cutoff and m.platform == platform and m.event_type == event_type
            ]

            if not measurements:
                return []

            # Group by time bucket
            buckets: dict[datetime, list[float]] = defaultdict(list)

            for m in measurements:
                # Round to bucket
                bucket_time = m.end_time.replace(
                    minute=(m.end_time.minute // bucket_minutes) * bucket_minutes,
                    second=0,
                    microsecond=0,
                )
                buckets[bucket_time].append(m.latency_ms)

            # Create timeline
            timeline = []
            for bucket_time in sorted(buckets.keys()):
                latencies = buckets[bucket_time]
                timeline.append(
                    {
                        "timestamp": bucket_time.isoformat(),
                        "count": len(latencies),
                        "avg_ms": round(statistics.mean(latencies), 2),
                        "p95_ms": round(sorted(latencies)[int(len(latencies) * 0.95)], 2)
                        if len(latencies) > 1
                        else latencies[0],
                    }
                )

            return timeline

    def get_slow_conversions(
        self,
        platform: Optional[str] = None,
        threshold_hours: float = 24,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get conversions that exceeded a latency threshold.

        Useful for diagnosing attribution issues.
        """
        with self._lock:
            threshold_ms = threshold_hours * 3600 * 1000

            slow = [
                {
                    "measurement_id": m.measurement_id,
                    "platform": m.platform,
                    "event_type": m.event_type,
                    "latency_hours": round(m.latency_ms / 3600000, 2),
                    "start_time": m.start_time.isoformat(),
                    "end_time": m.end_time.isoformat(),
                    "metadata": m.metadata,
                }
                for m in self._measurements
                if m.latency_ms > threshold_ms and (platform is None or m.platform == platform)
            ]

            # Sort by latency descending
            slow.sort(key=lambda x: x["latency_hours"], reverse=True)

            return slow[:limit]

    def cleanup_stale_pending(self):
        """Remove stale pending conversions that never completed."""
        with self._lock:
            now = datetime.now(UTC)
            stale_keys = []

            for key, pending in self._pending.items():
                age = now - pending.start_time
                if age > self._max_pending_age:
                    stale_keys.append(key)

            for key in stale_keys:
                del self._pending[key]

            if stale_keys:
                logger.info(f"Cleaned up {len(stale_keys)} stale pending conversions")

    def get_pending_count(self) -> dict[str, int]:
        """Get count of pending conversions by platform."""
        with self._lock:
            counts: dict[str, int] = defaultdict(int)
            for pending in self._pending.values():
                counts[pending.platform] += 1
            return dict(counts)

    def get_diagnostics(self) -> dict[str, Any]:
        """Get diagnostics about the tracker state."""
        with self._lock:
            return {
                "total_measurements": len(self._measurements),
                "pending_conversions": len(self._pending),
                "pending_by_platform": self.get_pending_count(),
                "platforms_tracked": list({m.platform for m in self._measurements}),
                "event_types_tracked": list({m.event_type for m in self._measurements}),
                "oldest_measurement": self._measurements[0].end_time.isoformat()
                if self._measurements
                else None,
                "newest_measurement": self._measurements[-1].end_time.isoformat()
                if self._measurements
                else None,
            }


# Singleton instance
latency_tracker = ConversionLatencyTracker()


# =============================================================================
# Convenience Functions for Integration
# =============================================================================


def track_click(click_id: str, platform: str, metadata: Optional[dict] = None):
    """Track a click event for conversion latency."""
    latency_tracker.start_tracking(
        event_id=click_id,
        platform=platform,
        event_type="click_to_conversion",
        metadata=metadata,
    )


def track_conversion(
    click_id: str,
    platform: str,
    conversion_time: Optional[datetime] = None,
    metadata: Optional[dict] = None,
) -> Optional[float]:
    """
    Track a conversion event and return the latency from click.

    Returns:
        Latency in milliseconds, or None if click wasn't tracked
    """
    return latency_tracker.end_tracking(
        event_id=click_id,
        platform=platform,
        event_type="click_to_conversion",
        end_time=conversion_time,
        metadata=metadata,
    )


def track_pixel_fire(event_id: str, platform: str):
    """Track when a pixel fires."""
    latency_tracker.start_tracking(
        event_id=event_id,
        platform=platform,
        event_type="pixel_to_capi",
    )


def track_capi_send(event_id: str, platform: str) -> Optional[float]:
    """Track when CAPI sends the event."""
    return latency_tracker.end_tracking(
        event_id=event_id,
        platform=platform,
        event_type="pixel_to_capi",
    )


def track_capi_ack(
    event_id: str,
    platform: str,
    latency_ms: float,
):
    """Track CAPI send-to-acknowledgment latency."""
    latency_tracker.record_latency(
        platform=platform,
        event_type="send_to_ack",
        latency_ms=latency_ms,
        event_id=event_id,
    )


def get_conversion_latency_stats(
    platform: Optional[str] = None,
    period_hours: int = 24,
) -> dict[str, Any]:
    """
    Get conversion latency statistics for EMQ calculation.

    Returns:
        Dict with avg, p50, p95 latencies in hours for EMQ
    """
    stats = latency_tracker.get_stats(
        platform=platform,
        event_type="click_to_conversion",
        period_hours=period_hours,
    )

    return {
        "avg_latency_hours": stats.avg_ms / 3600000 if stats.count > 0 else 0,
        "median_latency_hours": stats.median_ms / 3600000 if stats.count > 0 else 0,
        "p95_latency_hours": stats.p95_ms / 3600000 if stats.count > 0 else 0,
        "sample_count": stats.count,
    }


# =============================================================================
# Advanced Conversion Latency Analytics (P0 Enhancement)
# =============================================================================


@dataclass
class LatencyAnomaly:
    """Detected anomaly in conversion latency."""

    anomaly_id: str
    platform: str
    event_type: str
    detected_at: datetime
    severity: str  # low, medium, high, critical
    current_latency_ms: float
    expected_latency_ms: float
    deviation_percent: float
    description: str
    impact: str
    recommended_action: str


@dataclass
class LatencyForecast:
    """Forecasted conversion latency."""

    platform: str
    event_type: str
    forecast_date: datetime
    predicted_p50_ms: float
    predicted_p95_ms: float
    confidence_interval_low: float
    confidence_interval_high: float
    trend: str  # increasing, stable, decreasing


@dataclass
class AttributionWindowRecommendation:
    """Recommendation for attribution window settings."""

    platform: str
    current_window_days: int
    recommended_window_days: int
    coverage_at_current: float  # % of conversions captured
    coverage_at_recommended: float
    rationale: str


class LatencyAnomalyDetector:
    """
    Detects anomalies in conversion latency patterns.

    Uses statistical methods to identify:
    - Sudden latency spikes
    - Gradual latency drift
    - Platform-specific issues
    """

    def __init__(self, sensitivity: float = 2.0):
        self.sensitivity = sensitivity
        self._baseline_stats: dict[str, dict[str, float]] = {}

    def update_baseline(
        self,
        platform: str,
        event_type: str,
        stats: LatencyStats,
    ):
        """Update baseline statistics for anomaly detection."""
        key = f"{platform}:{event_type}"
        self._baseline_stats[key] = {
            "avg_ms": stats.avg_ms,
            "p95_ms": stats.p95_ms,
            "std_dev_ms": stats.std_dev_ms,
            "count": stats.count,
            "updated_at": datetime.now(UTC).timestamp(),
        }

    def detect_anomalies(
        self,
        platform: str,
        event_type: str,
        current_stats: LatencyStats,
    ) -> list[LatencyAnomaly]:
        """Detect anomalies in current latency vs baseline."""
        key = f"{platform}:{event_type}"
        baseline = self._baseline_stats.get(key)

        if not baseline or baseline["count"] < 10:
            return []

        anomalies = []
        now = datetime.now(UTC)

        # Check P95 latency
        if baseline["std_dev_ms"] > 0:
            z_score_p95 = (current_stats.p95_ms - baseline["p95_ms"]) / baseline["std_dev_ms"]

            if z_score_p95 > self.sensitivity:
                severity = self._calculate_severity(z_score_p95)
                deviation = (
                    ((current_stats.p95_ms - baseline["p95_ms"]) / baseline["p95_ms"] * 100)
                    if baseline["p95_ms"] > 0
                    else 0
                )

                anomalies.append(
                    LatencyAnomaly(
                        anomaly_id=f"latency_{platform}_{event_type}_{now.timestamp()}",
                        platform=platform,
                        event_type=event_type,
                        detected_at=now,
                        severity=severity,
                        current_latency_ms=current_stats.p95_ms,
                        expected_latency_ms=baseline["p95_ms"],
                        deviation_percent=round(deviation, 1),
                        description=f"P95 latency increased by {deviation:.1f}% from baseline",
                        impact=self._estimate_impact(event_type, deviation),
                        recommended_action=self._get_recommendation(event_type, z_score_p95),
                    )
                )

        # Check average latency drift
        if baseline["avg_ms"] > 0:
            avg_drift = (current_stats.avg_ms - baseline["avg_ms"]) / baseline["avg_ms"] * 100

            if avg_drift > 50:  # 50% increase in average
                anomalies.append(
                    LatencyAnomaly(
                        anomaly_id=f"drift_{platform}_{event_type}_{now.timestamp()}",
                        platform=platform,
                        event_type=event_type,
                        detected_at=now,
                        severity="medium",
                        current_latency_ms=current_stats.avg_ms,
                        expected_latency_ms=baseline["avg_ms"],
                        deviation_percent=round(avg_drift, 1),
                        description=f"Average latency drifting upward (+{avg_drift:.1f}%)",
                        impact="May affect attribution accuracy over time",
                        recommended_action="Review event processing pipeline for bottlenecks",
                    )
                )

        return anomalies

    def _calculate_severity(self, z_score: float) -> str:
        """Calculate anomaly severity from z-score."""
        if z_score >= 4:
            return "critical"
        elif z_score >= 3:
            return "high"
        elif z_score >= 2.5:
            return "medium"
        return "low"

    def _estimate_impact(self, event_type: str, deviation_percent: float) -> str:
        """Estimate business impact of latency anomaly."""
        if event_type == "click_to_conversion":
            if deviation_percent > 100:
                return "High risk of attribution misses - conversions may exceed attribution window"
            elif deviation_percent > 50:
                return "Moderate risk - some late conversions may be missed"
            return "Low risk - within acceptable variance"

        if event_type == "send_to_ack":
            if deviation_percent > 200:
                return "API reliability concerns - check platform status"
            return "Normal API variability"

        return "Impact varies by use case"

    def _get_recommendation(self, event_type: str, z_score: float) -> str:
        """Get recommendation based on event type and severity."""
        if event_type == "click_to_conversion":
            if z_score >= 3:
                return "Consider extending attribution window temporarily; investigate campaign changes"
            return "Monitor closely; check for external factors (holidays, promotions)"

        if event_type == "send_to_ack":
            if z_score >= 3:
                return "Check platform API status; consider implementing request queuing"
            return "Normal variance; continue monitoring"

        return "Review related system components"


class LatencyForecaster:
    """
    Forecasts future conversion latency using historical patterns.

    Uses exponential smoothing and trend analysis.
    """

    def __init__(self):
        self._history: dict[str, list[tuple[datetime, LatencyStats]]] = {}

    def record_stats(self, platform: str, event_type: str, stats: LatencyStats):
        """Record stats for forecasting."""
        key = f"{platform}:{event_type}"
        if key not in self._history:
            self._history[key] = []

        self._history[key].append((datetime.now(UTC), stats))

        # Keep last 90 days
        cutoff = datetime.now(UTC) - timedelta(days=90)
        self._history[key] = [(t, s) for t, s in self._history[key] if t > cutoff]

    def forecast(
        self,
        platform: str,
        event_type: str,
        days_ahead: int = 7,
    ) -> list[LatencyForecast]:
        """Forecast latency for upcoming days."""
        key = f"{platform}:{event_type}"
        history = self._history.get(key, [])

        if len(history) < 7:
            return []

        # Extract time series
        p50_series = [s.median_ms for _, s in history]
        p95_series = [s.p95_ms for _, s in history]

        # Simple exponential smoothing
        alpha = 0.3
        smoothed_p50 = p50_series[0]
        smoothed_p95 = p95_series[0]

        for p50, p95 in zip(p50_series[1:], p95_series[1:], strict=False):
            smoothed_p50 = alpha * p50 + (1 - alpha) * smoothed_p50
            smoothed_p95 = alpha * p95 + (1 - alpha) * smoothed_p95

        # Calculate trend
        recent = p50_series[-7:]
        older = p50_series[-14:-7] if len(p50_series) >= 14 else p50_series[: len(p50_series) // 2]

        trend = "stable"
        if older:
            avg_recent = statistics.mean(recent)
            avg_older = statistics.mean(older)
            if avg_recent > avg_older * 1.1:
                trend = "increasing"
            elif avg_recent < avg_older * 0.9:
                trend = "decreasing"

        # Calculate confidence intervals
        std_p50 = statistics.stdev(p50_series) if len(p50_series) > 1 else smoothed_p50 * 0.1
        std_p95 = statistics.stdev(p95_series) if len(p95_series) > 1 else smoothed_p95 * 0.1

        forecasts = []
        for d in range(1, days_ahead + 1):
            # Widen confidence interval with time
            ci_multiplier = 1 + (d * 0.1)

            forecasts.append(
                LatencyForecast(
                    platform=platform,
                    event_type=event_type,
                    forecast_date=datetime.now(UTC) + timedelta(days=d),
                    predicted_p50_ms=round(smoothed_p50, 1),
                    predicted_p95_ms=round(smoothed_p95, 1),
                    confidence_interval_low=round(
                        max(0, smoothed_p50 - std_p50 * ci_multiplier), 1
                    ),
                    confidence_interval_high=round(smoothed_p95 + std_p95 * ci_multiplier, 1),
                    trend=trend,
                )
            )

        return forecasts


class AttributionWindowOptimizer:
    """
    Optimizes attribution window settings based on conversion latency data.

    Analyzes historical latency distributions to recommend optimal
    attribution windows that balance coverage with accuracy.
    """

    # Platform default attribution windows (days)
    DEFAULT_WINDOWS = {
        "meta": 7,
        "google": 30,
        "tiktok": 7,
        "snapchat": 7,
    }

    def __init__(self, tracker: ConversionLatencyTracker):
        self.tracker = tracker

    def analyze_coverage(
        self,
        platform: str,
        window_days: int,
        period_hours: int = 168,  # 7 days
    ) -> float:
        """
        Calculate what percentage of conversions would be captured
        with a given attribution window.
        """
        stats = self.tracker.get_stats(
            platform=platform,
            event_type="click_to_conversion",
            period_hours=period_hours,
        )

        if stats.count == 0:
            return 100.0  # No data, assume full coverage

        window_ms = window_days * 24 * 3600 * 1000

        # Estimate coverage based on percentiles
        # This is simplified - in production, we'd analyze raw data
        if window_ms >= stats.p99_ms:
            return 99.0
        elif window_ms >= stats.p95_ms:
            return 95.0
        elif window_ms >= stats.p90_ms:
            return 90.0
        elif window_ms >= stats.p75_ms:
            return 75.0
        elif window_ms >= stats.median_ms:
            return 50.0
        else:
            # Linear interpolation for small windows
            return min(50.0, (window_ms / stats.median_ms) * 50.0)

    def recommend_window(
        self,
        platform: str,
        target_coverage: float = 95.0,
    ) -> AttributionWindowRecommendation:
        """
        Recommend optimal attribution window for target coverage.
        """
        current_window = self.DEFAULT_WINDOWS.get(platform, 7)
        current_coverage = self.analyze_coverage(platform, current_window)

        # Try different window sizes
        test_windows = [1, 3, 7, 14, 28, 30, 60, 90]
        best_window = current_window
        best_coverage = current_coverage

        for window in test_windows:
            coverage = self.analyze_coverage(platform, window)
            if coverage >= target_coverage and window < best_window or coverage > best_coverage:
                best_window = window
                best_coverage = coverage

        # Generate rationale
        if best_window < current_window:
            rationale = f"Can reduce window from {current_window} to {best_window} days while maintaining {best_coverage:.1f}% coverage"
        elif best_window > current_window:
            rationale = f"Consider extending window to {best_window} days to capture {best_coverage:.1f}% of conversions"
        else:
            rationale = (
                f"Current {current_window}-day window is optimal for {best_coverage:.1f}% coverage"
            )

        return AttributionWindowRecommendation(
            platform=platform,
            current_window_days=current_window,
            recommended_window_days=best_window,
            coverage_at_current=round(current_coverage, 1),
            coverage_at_recommended=round(best_coverage, 1),
            rationale=rationale,
        )

    def get_all_recommendations(self) -> list[AttributionWindowRecommendation]:
        """Get attribution window recommendations for all platforms."""
        recommendations = []

        for platform in self.DEFAULT_WINDOWS:
            rec = self.recommend_window(platform)
            recommendations.append(rec)

        return recommendations


# Singleton instances for P0 enhancements
latency_anomaly_detector = LatencyAnomalyDetector()
latency_forecaster = LatencyForecaster()
attribution_optimizer = AttributionWindowOptimizer(latency_tracker)
