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

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
import statistics
import threading

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
    metadata: Dict[str, Any] = field(default_factory=dict)


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
    metadata: Dict[str, Any] = field(default_factory=dict)


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
        self._pending: Dict[str, PendingConversion] = {}
        self._measurements: List[LatencyMeasurement] = []
        self._lock = threading.RLock()
        self._max_pending_age = timedelta(hours=max_pending_age_hours)

        # In-memory aggregated stats by platform and event type
        self._stats_cache: Dict[str, Dict[str, List[float]]] = defaultdict(
            lambda: defaultdict(list)
        )

    def start_tracking(
        self,
        event_id: str,
        platform: str,
        event_type: str,
        start_time: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
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
                start_time=start_time or datetime.now(timezone.utc),
                metadata=metadata or {},
            )

    def end_tracking(
        self,
        event_id: str,
        platform: str,
        event_type: str,
        end_time: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
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

            end = end_time or datetime.now(timezone.utc)

            # Handle timezone comparison
            start = pending.start_time
            if start.tzinfo is None and end.tzinfo is not None:
                start = start.replace(tzinfo=timezone.utc)
            elif start.tzinfo is not None and end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)

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
                self._stats_cache[platform][event_type] = \
                    self._stats_cache[platform][event_type][-10000:]

            return latency_ms

    def record_latency(
        self,
        platform: str,
        event_type: str,
        latency_ms: float,
        event_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
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
            now = datetime.now(timezone.utc)

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
            cutoff = datetime.now(timezone.utc) - timedelta(hours=period_hours)

            # Filter measurements
            measurements = [
                m for m in self._measurements
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
    ) -> Dict[str, LatencyStats]:
        """Get latency statistics grouped by platform."""
        with self._lock:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=period_hours)

            # Group by platform
            by_platform: Dict[str, List[float]] = defaultdict(list)

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
    ) -> Dict[str, LatencyStats]:
        """Get latency statistics grouped by event type."""
        with self._lock:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=period_hours)

            by_type: Dict[str, List[float]] = defaultdict(list)

            for m in self._measurements:
                if m.end_time >= cutoff:
                    if platform is None or m.platform == platform:
                        by_type[m.event_type].append(m.latency_ms)

            return {
                event_type: self._calculate_stats(latencies)
                for event_type, latencies in by_type.items()
            }

    def _calculate_stats(self, latencies: List[float]) -> LatencyStats:
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
    ) -> List[Dict[str, Any]]:
        """
        Get latency over time for charting.

        Returns a list of time buckets with average latency.
        """
        with self._lock:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=period_hours)
            bucket_size = timedelta(minutes=bucket_minutes)

            # Filter measurements
            measurements = [
                m for m in self._measurements
                if m.end_time >= cutoff
                and m.platform == platform
                and m.event_type == event_type
            ]

            if not measurements:
                return []

            # Group by time bucket
            buckets: Dict[datetime, List[float]] = defaultdict(list)

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
                timeline.append({
                    "timestamp": bucket_time.isoformat(),
                    "count": len(latencies),
                    "avg_ms": round(statistics.mean(latencies), 2),
                    "p95_ms": round(sorted(latencies)[int(len(latencies) * 0.95)], 2)
                        if len(latencies) > 1 else latencies[0],
                })

            return timeline

    def get_slow_conversions(
        self,
        platform: Optional[str] = None,
        threshold_hours: float = 24,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
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
                if m.latency_ms > threshold_ms
                and (platform is None or m.platform == platform)
            ]

            # Sort by latency descending
            slow.sort(key=lambda x: x["latency_hours"], reverse=True)

            return slow[:limit]

    def cleanup_stale_pending(self):
        """Remove stale pending conversions that never completed."""
        with self._lock:
            now = datetime.now(timezone.utc)
            stale_keys = []

            for key, pending in self._pending.items():
                age = now - pending.start_time
                if age > self._max_pending_age:
                    stale_keys.append(key)

            for key in stale_keys:
                del self._pending[key]

            if stale_keys:
                logger.info(f"Cleaned up {len(stale_keys)} stale pending conversions")

    def get_pending_count(self) -> Dict[str, int]:
        """Get count of pending conversions by platform."""
        with self._lock:
            counts: Dict[str, int] = defaultdict(int)
            for pending in self._pending.values():
                counts[pending.platform] += 1
            return dict(counts)

    def get_diagnostics(self) -> Dict[str, Any]:
        """Get diagnostics about the tracker state."""
        with self._lock:
            return {
                "total_measurements": len(self._measurements),
                "pending_conversions": len(self._pending),
                "pending_by_platform": self.get_pending_count(),
                "platforms_tracked": list(set(m.platform for m in self._measurements)),
                "event_types_tracked": list(set(m.event_type for m in self._measurements)),
                "oldest_measurement": self._measurements[0].end_time.isoformat()
                    if self._measurements else None,
                "newest_measurement": self._measurements[-1].end_time.isoformat()
                    if self._measurements else None,
            }


# Singleton instance
latency_tracker = ConversionLatencyTracker()


# =============================================================================
# Convenience Functions for Integration
# =============================================================================

def track_click(click_id: str, platform: str, metadata: Optional[Dict] = None):
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
    metadata: Optional[Dict] = None,
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
) -> Dict[str, Any]:
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
