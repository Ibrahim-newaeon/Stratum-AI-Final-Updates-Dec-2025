# =============================================================================
# Stratum AI - Real EMQ Measurement Service
# =============================================================================
"""
Service for measuring actual EMQ (Event Measurement Quality) using real CAPI
event delivery data instead of estimates.

Integrates with:
- CAPI event delivery logs (from platform_connectors.py)
- Pixel event tracking
- GA4 data for attribution accuracy
- Database for persistence
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import statistics

from app.core.logging import get_logger
from app.analytics.logic.emq_calculation import (
    PlatformMetrics,
    EmqCalculationResult,
    calculate_emq_score,
    calculate_aggregate_emq,
    determine_autopilot_mode,
)
from app.services.capi.platform_connectors import (
    get_event_delivery_logs,
    EventDeliveryLog,
)

logger = get_logger(__name__)


# =============================================================================
# Data Classes for Real EMQ Measurement
# =============================================================================

@dataclass
class PixelEvent:
    """Represents a pixel-fired event for EMQ matching."""
    event_id: str
    platform: str
    event_name: str
    timestamp: datetime
    user_hash: Optional[str] = None
    page_url: Optional[str] = None
    value: Optional[float] = None


@dataclass
class ConversionEvent:
    """Represents a conversion event for latency tracking."""
    event_id: str
    platform: str
    pixel_timestamp: Optional[datetime] = None  # When pixel fired
    capi_timestamp: Optional[datetime] = None   # When CAPI sent
    platform_timestamp: Optional[datetime] = None  # When platform received
    conversion_value: float = 0.0


@dataclass
class GA4ConversionData:
    """GA4 conversion data for attribution accuracy."""
    platform: str
    conversions: int
    revenue: float
    date: datetime


@dataclass
class RealEMQMetrics:
    """Real EMQ metrics calculated from actual event data."""
    platform: str
    period_start: datetime
    period_end: datetime

    # Event Matching (calculated from real data)
    pixel_events_count: int = 0
    capi_events_count: int = 0
    matched_events_count: int = 0
    match_rate: float = 0.0

    # Conversion Latency (calculated from real timestamps)
    latencies_ms: List[float] = field(default_factory=list)
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0

    # CAPI Delivery Stats
    capi_success_count: int = 0
    capi_failure_count: int = 0
    capi_delivery_rate: float = 0.0
    avg_capi_latency_ms: float = 0.0

    # Attribution
    platform_conversions: int = 0
    platform_revenue: float = 0.0
    ga4_conversions: int = 0
    ga4_revenue: float = 0.0

    # Data Freshness
    last_pixel_event: Optional[datetime] = None
    last_capi_event: Optional[datetime] = None


# =============================================================================
# In-Memory Storage for Pixel Events (In production, use Redis/Database)
# =============================================================================

_pixel_events: List[PixelEvent] = []
_conversion_events: Dict[str, ConversionEvent] = {}
_ga4_data: Dict[str, List[GA4ConversionData]] = {}


def record_pixel_event(event: PixelEvent):
    """Record a pixel event for EMQ matching."""
    global _pixel_events
    _pixel_events.append(event)
    # Keep only last 100000 events
    if len(_pixel_events) > 100000:
        _pixel_events = _pixel_events[-100000:]


def record_conversion(conversion: ConversionEvent):
    """Record a conversion event for latency tracking."""
    global _conversion_events
    _conversion_events[conversion.event_id] = conversion
    # Cleanup old conversions (keep last 7 days)
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    _conversion_events = {
        k: v for k, v in _conversion_events.items()
        if (v.pixel_timestamp or v.capi_timestamp or datetime.now(timezone.utc)) > cutoff
    }


def record_ga4_data(data: GA4ConversionData):
    """Record GA4 data for attribution comparison."""
    global _ga4_data
    if data.platform not in _ga4_data:
        _ga4_data[data.platform] = []
    _ga4_data[data.platform].append(data)
    # Keep only last 30 days
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    _ga4_data[data.platform] = [d for d in _ga4_data[data.platform] if d.date > cutoff]


# =============================================================================
# Real EMQ Measurement Functions
# =============================================================================

def calculate_real_emq_metrics(
    platform: str,
    period_hours: int = 24,
) -> RealEMQMetrics:
    """
    Calculate real EMQ metrics from actual event delivery data.

    Args:
        platform: Platform to calculate for
        period_hours: Time period to analyze

    Returns:
        RealEMQMetrics with actual measurements
    """
    now = datetime.now(timezone.utc)
    period_start = now - timedelta(hours=period_hours)

    metrics = RealEMQMetrics(
        platform=platform,
        period_start=period_start,
        period_end=now,
    )

    # =========================================================================
    # Get CAPI delivery data
    # =========================================================================
    capi_logs = get_event_delivery_logs(platform=platform, since=period_start)

    if capi_logs:
        metrics.capi_events_count = len(capi_logs)
        metrics.capi_success_count = sum(1 for log in capi_logs if log.success)
        metrics.capi_failure_count = metrics.capi_events_count - metrics.capi_success_count

        if metrics.capi_events_count > 0:
            metrics.capi_delivery_rate = (metrics.capi_success_count / metrics.capi_events_count) * 100

        # Calculate CAPI latencies
        capi_latencies = [log.latency_ms for log in capi_logs if log.success]
        if capi_latencies:
            metrics.avg_capi_latency_ms = statistics.mean(capi_latencies)

        # Find last CAPI event
        successful_logs = [log for log in capi_logs if log.success]
        if successful_logs:
            metrics.last_capi_event = max(log.timestamp for log in successful_logs)

    # =========================================================================
    # Get pixel events for this platform
    # =========================================================================
    pixel_events = [e for e in _pixel_events
                    if e.platform == platform and e.timestamp >= period_start]
    metrics.pixel_events_count = len(pixel_events)

    if pixel_events:
        metrics.last_pixel_event = max(e.timestamp for e in pixel_events)

    # =========================================================================
    # Calculate event match rate
    # =========================================================================
    # Match events by event_id
    pixel_event_ids = {e.event_id for e in pixel_events}
    capi_event_ids = {log.event_id for log in capi_logs if log.success}

    metrics.matched_events_count = len(pixel_event_ids & capi_event_ids)

    total_unique_events = len(pixel_event_ids | capi_event_ids)
    if total_unique_events > 0:
        metrics.match_rate = (metrics.matched_events_count / total_unique_events) * 100

    # =========================================================================
    # Calculate conversion latencies
    # =========================================================================
    # Get conversions that have both pixel and CAPI timestamps
    for conv in _conversion_events.values():
        if conv.platform != platform:
            continue
        if conv.pixel_timestamp and conv.capi_timestamp:
            latency_ms = (conv.capi_timestamp - conv.pixel_timestamp).total_seconds() * 1000
            if latency_ms > 0:  # Only positive latencies make sense
                metrics.latencies_ms.append(latency_ms)

    if metrics.latencies_ms:
        metrics.avg_latency_ms = statistics.mean(metrics.latencies_ms)
        sorted_latencies = sorted(metrics.latencies_ms)
        metrics.p50_latency_ms = sorted_latencies[len(sorted_latencies) // 2]
        p95_idx = int(len(sorted_latencies) * 0.95)
        metrics.p95_latency_ms = sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)]

    # =========================================================================
    # Get GA4 data for attribution accuracy
    # =========================================================================
    if platform in _ga4_data:
        recent_ga4 = [d for d in _ga4_data[platform] if d.date >= period_start]
        if recent_ga4:
            metrics.ga4_conversions = sum(d.conversions for d in recent_ga4)
            metrics.ga4_revenue = sum(d.revenue for d in recent_ga4)

    # Get platform conversion data from CAPI logs (conversion events)
    conversion_logs = [log for log in capi_logs
                       if log.event_name.lower() in ['purchase', 'conversion', 'complete_payment']]
    metrics.platform_conversions = len(conversion_logs)
    # Revenue would come from event parameters - simplified for now
    metrics.platform_revenue = metrics.platform_conversions * 50  # Estimate

    return metrics


def convert_real_to_platform_metrics(real_metrics: RealEMQMetrics) -> PlatformMetrics:
    """
    Convert real EMQ metrics to PlatformMetrics for EMQ calculation.

    This bridges the gap between actual measurements and the EMQ calculation logic.
    """
    # Convert latency from ms to hours
    avg_latency_hours = real_metrics.avg_latency_ms / (1000 * 3600) if real_metrics.avg_latency_ms > 0 else 0

    return PlatformMetrics(
        platform=real_metrics.platform,

        # Event matching - now from real data
        pixel_events=real_metrics.pixel_events_count,
        capi_events=real_metrics.capi_events_count,
        matched_events=real_metrics.matched_events_count,

        # Coverage - estimated based on CAPI delivery rate
        pages_with_pixel=100,  # Assume good coverage
        total_pages=100,
        events_configured=int(real_metrics.capi_delivery_rate) if real_metrics.capi_delivery_rate else 90,
        events_expected=100,

        # Latency - now from real data
        avg_conversion_latency_hours=avg_latency_hours,
        max_conversion_latency_hours=real_metrics.p95_latency_ms / (1000 * 3600) if real_metrics.p95_latency_ms > 0 else 0,

        # Attribution - now from real data
        platform_conversions=real_metrics.platform_conversions,
        ga4_conversions=real_metrics.ga4_conversions,
        platform_revenue=real_metrics.platform_revenue,
        ga4_revenue=real_metrics.ga4_revenue,

        # Freshness - now from real data
        last_event_at=real_metrics.last_capi_event or real_metrics.last_pixel_event,
        last_sync_at=real_metrics.last_capi_event,

        # API health - now from real data
        api_error_count=real_metrics.capi_failure_count,
        api_request_count=real_metrics.capi_events_count,
    )


class RealEMQService:
    """
    Service for calculating real EMQ scores from actual event data.

    This replaces estimated EMQ with real measurements from:
    - CAPI event delivery logs
    - Pixel event tracking
    - GA4 integration
    """

    def __init__(self):
        self._cache: Dict[str, Tuple[datetime, EmqCalculationResult]] = {}
        self._cache_ttl_seconds = 300  # 5 minute cache

    def get_platform_emq(
        self,
        platform: str,
        period_hours: int = 24,
        use_cache: bool = True,
    ) -> EmqCalculationResult:
        """
        Get real EMQ score for a platform.

        Args:
            platform: Platform name (meta, google, tiktok, etc.)
            period_hours: Analysis period
            use_cache: Whether to use cached results

        Returns:
            EmqCalculationResult with real measurements
        """
        cache_key = f"{platform}_{period_hours}"

        # Check cache
        if use_cache and cache_key in self._cache:
            cached_time, cached_result = self._cache[cache_key]
            if (datetime.now(timezone.utc) - cached_time).total_seconds() < self._cache_ttl_seconds:
                return cached_result

        # Calculate real metrics
        real_metrics = calculate_real_emq_metrics(platform, period_hours)

        # Convert to platform metrics
        platform_metrics = convert_real_to_platform_metrics(real_metrics)

        # Get previous period for trends
        prev_metrics = calculate_real_emq_metrics(platform, period_hours * 2)
        prev_platform_metrics = convert_real_to_platform_metrics(prev_metrics) if prev_metrics.capi_events_count > 0 else None

        # Calculate EMQ score
        result = calculate_emq_score(
            metrics=platform_metrics,
            previous_metrics=prev_platform_metrics,
        )

        # Add real metrics details
        result.drivers[0].details = f"Match rate: {real_metrics.match_rate:.1f}% ({real_metrics.matched_events_count}/{real_metrics.pixel_events_count + real_metrics.capi_events_count - real_metrics.matched_events_count} events)"
        result.drivers[2].details = f"Avg latency: {real_metrics.avg_capi_latency_ms:.0f}ms (P95: {real_metrics.p95_latency_ms:.0f}ms)"

        # Cache result
        self._cache[cache_key] = (datetime.now(timezone.utc), result)

        logger.info(f"Real EMQ calculated for {platform}: score={result.score}, band={result.confidence_band}")

        return result

    def get_aggregate_emq(
        self,
        platforms: Optional[List[str]] = None,
        period_hours: int = 24,
    ) -> EmqCalculationResult:
        """
        Get aggregate EMQ score across platforms.

        Args:
            platforms: List of platforms (default: all available)
            period_hours: Analysis period

        Returns:
            Aggregated EmqCalculationResult
        """
        if platforms is None:
            platforms = ["meta", "google", "tiktok", "snapchat", "linkedin"]

        platform_results = []
        for platform in platforms:
            try:
                result = self.get_platform_emq(platform, period_hours)
                if result.score > 0:  # Only include platforms with data
                    platform_results.append(result)
            except Exception as e:
                logger.warning(f"Failed to get EMQ for {platform}: {e}")

        if not platform_results:
            # Return default result if no data
            return EmqCalculationResult(
                score=0.0,
                previous_score=None,
                confidence_band="unsafe",
                drivers=[],
                calculated_at=datetime.now(timezone.utc),
            )

        return calculate_aggregate_emq(platform_results)

    def get_autopilot_recommendation(
        self,
        platform: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get autopilot mode recommendation based on real EMQ.

        Args:
            platform: Specific platform or None for aggregate

        Returns:
            Dict with mode recommendation and details
        """
        if platform:
            emq_result = self.get_platform_emq(platform)
        else:
            emq_result = self.get_aggregate_emq()

        mode, reason = determine_autopilot_mode(emq_result.score)

        return {
            "emq_score": emq_result.score,
            "confidence_band": emq_result.confidence_band,
            "autopilot_mode": mode,
            "reason": reason,
            "drivers": [
                {
                    "name": d.name,
                    "value": d.value,
                    "status": d.status.value,
                    "trend": d.trend.value,
                }
                for d in emq_result.drivers
            ],
            "calculated_at": emq_result.calculated_at.isoformat(),
        }

    def get_emq_diagnostics(
        self,
        platform: str,
        period_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Get detailed EMQ diagnostics for troubleshooting.

        Returns:
            Dict with detailed metrics and recommendations
        """
        real_metrics = calculate_real_emq_metrics(platform, period_hours)
        emq_result = self.get_platform_emq(platform, period_hours)

        # Generate recommendations based on metrics
        recommendations = []

        if real_metrics.match_rate < 70:
            recommendations.append({
                "priority": "critical",
                "issue": "Low event match rate",
                "action": "Verify pixel and CAPI event_id parameters match",
                "impact": "Causes duplicate conversion counting",
            })

        if real_metrics.capi_delivery_rate < 95:
            recommendations.append({
                "priority": "high",
                "issue": "CAPI delivery failures",
                "action": f"Check CAPI credentials and API health ({real_metrics.capi_failure_count} failures)",
                "impact": "Missing server-side events",
            })

        if real_metrics.avg_capi_latency_ms > 5000:
            recommendations.append({
                "priority": "medium",
                "issue": "High CAPI latency",
                "action": "Review network connectivity and batch sizes",
                "impact": "Delayed conversion reporting",
            })

        if real_metrics.ga4_conversions > 0 and real_metrics.platform_conversions > 0:
            variance = abs(real_metrics.platform_conversions - real_metrics.ga4_conversions) / real_metrics.ga4_conversions
            if variance > 0.2:
                recommendations.append({
                    "priority": "high",
                    "issue": f"Attribution variance: {variance*100:.1f}%",
                    "action": "Review attribution windows and conversion definitions",
                    "impact": "Unreliable ROAS calculations",
                })

        return {
            "platform": platform,
            "period": {
                "start": real_metrics.period_start.isoformat(),
                "end": real_metrics.period_end.isoformat(),
            },
            "emq_score": emq_result.score,
            "confidence_band": emq_result.confidence_band,
            "metrics": {
                "event_matching": {
                    "pixel_events": real_metrics.pixel_events_count,
                    "capi_events": real_metrics.capi_events_count,
                    "matched_events": real_metrics.matched_events_count,
                    "match_rate_percent": round(real_metrics.match_rate, 2),
                },
                "capi_delivery": {
                    "success_count": real_metrics.capi_success_count,
                    "failure_count": real_metrics.capi_failure_count,
                    "delivery_rate_percent": round(real_metrics.capi_delivery_rate, 2),
                    "avg_latency_ms": round(real_metrics.avg_capi_latency_ms, 2),
                },
                "conversion_latency": {
                    "avg_ms": round(real_metrics.avg_latency_ms, 2),
                    "p50_ms": round(real_metrics.p50_latency_ms, 2),
                    "p95_ms": round(real_metrics.p95_latency_ms, 2),
                },
                "attribution": {
                    "platform_conversions": real_metrics.platform_conversions,
                    "ga4_conversions": real_metrics.ga4_conversions,
                    "platform_revenue": real_metrics.platform_revenue,
                    "ga4_revenue": real_metrics.ga4_revenue,
                },
                "freshness": {
                    "last_pixel_event": real_metrics.last_pixel_event.isoformat() if real_metrics.last_pixel_event else None,
                    "last_capi_event": real_metrics.last_capi_event.isoformat() if real_metrics.last_capi_event else None,
                },
            },
            "recommendations": recommendations,
            "drivers": [
                {
                    "name": d.name,
                    "value": d.value,
                    "weight": d.weight,
                    "status": d.status.value,
                    "trend": d.trend.value,
                    "details": d.details,
                }
                for d in emq_result.drivers
            ],
        }


# Create singleton instance
real_emq_service = RealEMQService()
