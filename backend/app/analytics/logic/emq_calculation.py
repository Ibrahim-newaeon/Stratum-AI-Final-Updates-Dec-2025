# =============================================================================
# Stratum AI - EMQ (Event Measurement Quality) Calculation Logic
# =============================================================================
"""
Real EMQ calculation logic that computes scores from platform metrics.

EMQ Score is composed of 5 drivers:
1. Event Match Rate (30%) - How well events match between pixel and CAPI
2. Pixel Coverage (25%) - Percentage of pages/events with pixel installed
3. Conversion Latency (20%) - Time delay in conversion reporting
4. Attribution Accuracy (15%) - Platform vs GA4 attribution alignment
5. Data Freshness (10%) - How recent the data is

Each driver scores 0-100, weighted to produce final EMQ score.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from enum import Enum


class DriverStatus(str, Enum):
    """Status classification for EMQ drivers."""
    GOOD = "good"
    WARNING = "warning"
    CRITICAL = "critical"


class DriverTrend(str, Enum):
    """Trend direction for EMQ drivers."""
    UP = "up"
    DOWN = "down"
    FLAT = "flat"


@dataclass
class EmqDriverResult:
    """Result for a single EMQ driver calculation."""
    name: str
    value: float  # 0-100
    weight: float  # 0-1
    status: DriverStatus
    trend: DriverTrend
    details: Optional[str] = None


@dataclass
class EmqCalculationResult:
    """Complete EMQ calculation result."""
    score: float  # 0-100
    previous_score: Optional[float]
    confidence_band: str  # reliable, directional, unsafe
    drivers: List[EmqDriverResult]
    calculated_at: datetime


@dataclass
class PlatformMetrics:
    """Raw metrics from a platform for EMQ calculation."""
    platform: str

    # Event matching metrics
    pixel_events: int = 0
    capi_events: int = 0
    matched_events: int = 0

    # Coverage metrics
    pages_with_pixel: int = 0
    total_pages: int = 0
    events_configured: int = 0
    events_expected: int = 0

    # Latency metrics
    avg_conversion_latency_hours: float = 0.0
    max_conversion_latency_hours: float = 0.0

    # Attribution metrics
    platform_conversions: int = 0
    ga4_conversions: int = 0
    platform_revenue: float = 0.0
    ga4_revenue: float = 0.0

    # Freshness metrics
    last_event_at: Optional[datetime] = None
    last_sync_at: Optional[datetime] = None

    # API health
    api_error_count: int = 0
    api_request_count: int = 0


# =============================================================================
# Driver Calculation Functions
# =============================================================================

def calculate_event_match_rate(metrics: PlatformMetrics) -> EmqDriverResult:
    """
    Calculate Event Match Rate driver (30% weight).

    Measures how well pixel events match with CAPI events.
    Higher match rate = better data quality.
    """
    weight = 0.30
    name = "Event Match Rate"

    total_events = metrics.pixel_events + metrics.capi_events

    if total_events == 0:
        # No events = cannot calculate
        return EmqDriverResult(
            name=name,
            value=0.0,
            weight=weight,
            status=DriverStatus.CRITICAL,
            trend=DriverTrend.FLAT,
            details="No events received"
        )

    # Calculate match rate
    if metrics.matched_events > 0:
        # If we have explicit matched events data
        match_rate = (metrics.matched_events / max(metrics.pixel_events, metrics.capi_events)) * 100
    else:
        # Estimate from pixel/CAPI overlap
        min_events = min(metrics.pixel_events, metrics.capi_events)
        max_events = max(metrics.pixel_events, metrics.capi_events)
        if max_events > 0:
            match_rate = (min_events / max_events) * 100
        else:
            match_rate = 0.0

    # Clamp to 0-100
    value = min(100.0, max(0.0, match_rate))

    # Determine status
    if value >= 85:
        status = DriverStatus.GOOD
    elif value >= 70:
        status = DriverStatus.WARNING
    else:
        status = DriverStatus.CRITICAL

    return EmqDriverResult(
        name=name,
        value=round(value, 1),
        weight=weight,
        status=status,
        trend=DriverTrend.FLAT,  # Trend calculated separately
        details=f"{metrics.pixel_events} pixel, {metrics.capi_events} CAPI events"
    )


def calculate_pixel_coverage(metrics: PlatformMetrics) -> EmqDriverResult:
    """
    Calculate Pixel Coverage driver (25% weight).

    Measures installation completeness across pages and events.
    """
    weight = 0.25
    name = "Pixel Coverage"

    scores = []

    # Page coverage
    if metrics.total_pages > 0:
        page_coverage = (metrics.pages_with_pixel / metrics.total_pages) * 100
        scores.append(page_coverage)

    # Event coverage
    if metrics.events_expected > 0:
        event_coverage = (metrics.events_configured / metrics.events_expected) * 100
        scores.append(event_coverage)

    if not scores:
        # Default to good if no data (assume properly configured)
        value = 90.0
        details = "Coverage data not available"
    else:
        value = sum(scores) / len(scores)
        details = f"{metrics.pages_with_pixel}/{metrics.total_pages} pages, {metrics.events_configured}/{metrics.events_expected} events"

    value = min(100.0, max(0.0, value))

    if value >= 90:
        status = DriverStatus.GOOD
    elif value >= 75:
        status = DriverStatus.WARNING
    else:
        status = DriverStatus.CRITICAL

    return EmqDriverResult(
        name=name,
        value=round(value, 1),
        weight=weight,
        status=status,
        trend=DriverTrend.FLAT,
        details=details
    )


def calculate_conversion_latency(metrics: PlatformMetrics) -> EmqDriverResult:
    """
    Calculate Conversion Latency driver (20% weight).

    Lower latency = higher score.
    Target: < 1 hour = 100, > 24 hours = 0
    """
    weight = 0.20
    name = "Conversion Latency"

    latency_hours = metrics.avg_conversion_latency_hours

    if latency_hours <= 0:
        # No latency data or instant = perfect score
        value = 100.0
        details = "Real-time conversion tracking"
    elif latency_hours <= 1:
        # Under 1 hour = excellent (90-100)
        value = 100 - (latency_hours * 10)
        details = f"Avg latency: {latency_hours:.1f}h"
    elif latency_hours <= 4:
        # 1-4 hours = good (70-90)
        value = 90 - ((latency_hours - 1) * 6.67)
        details = f"Avg latency: {latency_hours:.1f}h"
    elif latency_hours <= 12:
        # 4-12 hours = warning (40-70)
        value = 70 - ((latency_hours - 4) * 3.75)
        details = f"Avg latency: {latency_hours:.1f}h (elevated)"
    elif latency_hours <= 24:
        # 12-24 hours = critical (0-40)
        value = 40 - ((latency_hours - 12) * 3.33)
        details = f"Avg latency: {latency_hours:.1f}h (high)"
    else:
        # Over 24 hours = 0
        value = 0.0
        details = f"Avg latency: {latency_hours:.1f}h (critical)"

    value = min(100.0, max(0.0, value))

    if value >= 70:
        status = DriverStatus.GOOD
    elif value >= 40:
        status = DriverStatus.WARNING
    else:
        status = DriverStatus.CRITICAL

    return EmqDriverResult(
        name=name,
        value=round(value, 1),
        weight=weight,
        status=status,
        trend=DriverTrend.FLAT,
        details=details
    )


def calculate_attribution_accuracy(metrics: PlatformMetrics) -> EmqDriverResult:
    """
    Calculate Attribution Accuracy driver (15% weight).

    Measures alignment between platform attribution and GA4.
    """
    weight = 0.15
    name = "Attribution Accuracy"

    # Calculate conversion variance
    if metrics.ga4_conversions > 0:
        conv_variance = abs(metrics.platform_conversions - metrics.ga4_conversions) / metrics.ga4_conversions
    elif metrics.platform_conversions > 0:
        conv_variance = 1.0  # 100% variance if GA4 has 0 but platform has data
    else:
        conv_variance = 0.0  # Both zero = no variance

    # Calculate revenue variance
    if metrics.ga4_revenue > 0:
        rev_variance = abs(metrics.platform_revenue - metrics.ga4_revenue) / metrics.ga4_revenue
    elif metrics.platform_revenue > 0:
        rev_variance = 1.0
    else:
        rev_variance = 0.0

    # Average variance (0 = perfect, 1 = 100% off)
    avg_variance = (conv_variance + rev_variance) / 2

    # Convert to score (0% variance = 100, 50%+ variance = 0)
    value = max(0.0, 100 - (avg_variance * 200))

    if value >= 80:
        status = DriverStatus.GOOD
        details = f"Platform-GA4 variance: {avg_variance*100:.1f}%"
    elif value >= 60:
        status = DriverStatus.WARNING
        details = f"Moderate variance: {avg_variance*100:.1f}%"
    else:
        status = DriverStatus.CRITICAL
        details = f"High variance: {avg_variance*100:.1f}%"

    return EmqDriverResult(
        name=name,
        value=round(value, 1),
        weight=weight,
        status=status,
        trend=DriverTrend.FLAT,
        details=details
    )


def calculate_data_freshness(metrics: PlatformMetrics, now: Optional[datetime] = None) -> EmqDriverResult:
    """
    Calculate Data Freshness driver (10% weight).

    Measures how recent the data is.
    """
    weight = 0.10
    name = "Data Freshness"

    if now is None:
        now = datetime.utcnow()

    # Use the most recent of last_event or last_sync
    last_update = metrics.last_event_at or metrics.last_sync_at

    if last_update is None:
        # No data = assume stale
        value = 50.0
        details = "Last update time unknown"
        status = DriverStatus.WARNING
    else:
        # Handle timezone-aware vs naive datetime comparison
        if last_update.tzinfo is not None and now.tzinfo is None:
            # last_update is timezone-aware, now is naive - make now naive by using last_update's timezone
            now = now.replace(tzinfo=last_update.tzinfo)
        elif last_update.tzinfo is None and now.tzinfo is not None:
            # last_update is naive, now is timezone-aware - strip timezone from now
            now = now.replace(tzinfo=None)

        hours_since_update = (now - last_update).total_seconds() / 3600

        if hours_since_update <= 1:
            value = 100.0
            details = "Data updated within last hour"
        elif hours_since_update <= 6:
            value = 100 - ((hours_since_update - 1) * 4)  # 96-80
            details = f"Data is {hours_since_update:.1f}h old"
        elif hours_since_update <= 24:
            value = 80 - ((hours_since_update - 6) * 2.22)  # 80-40
            details = f"Data is {hours_since_update:.1f}h old"
        else:
            value = max(0, 40 - ((hours_since_update - 24) * 1.67))
            details = f"Data is {hours_since_update:.1f}h old (stale)"

        value = min(100.0, max(0.0, value))

        if value >= 80:
            status = DriverStatus.GOOD
        elif value >= 50:
            status = DriverStatus.WARNING
        else:
            status = DriverStatus.CRITICAL

    return EmqDriverResult(
        name=name,
        value=round(value, 1),
        weight=weight,
        status=status,
        trend=DriverTrend.FLAT,
        details=details
    )


# =============================================================================
# Main Calculation Function
# =============================================================================

def calculate_emq_score(
    metrics: PlatformMetrics,
    previous_metrics: Optional[PlatformMetrics] = None,
    now: Optional[datetime] = None,
) -> EmqCalculationResult:
    """
    Calculate complete EMQ score from platform metrics.

    Args:
        metrics: Current platform metrics
        previous_metrics: Previous period metrics for trend calculation
        now: Current timestamp (for freshness calculation)

    Returns:
        EmqCalculationResult with score, drivers, and confidence band
    """
    if now is None:
        now = datetime.utcnow()

    # Calculate all drivers
    drivers = [
        calculate_event_match_rate(metrics),
        calculate_pixel_coverage(metrics),
        calculate_conversion_latency(metrics),
        calculate_attribution_accuracy(metrics),
        calculate_data_freshness(metrics, now),
    ]

    # Calculate weighted score
    score = sum(d.value * d.weight for d in drivers)
    score = round(score, 1)

    # Calculate previous score if we have previous metrics
    previous_score = None
    if previous_metrics:
        prev_drivers = [
            calculate_event_match_rate(previous_metrics),
            calculate_pixel_coverage(previous_metrics),
            calculate_conversion_latency(previous_metrics),
            calculate_attribution_accuracy(previous_metrics),
            calculate_data_freshness(previous_metrics, now - timedelta(days=1)),
        ]
        previous_score = round(sum(d.value * d.weight for d in prev_drivers), 1)

        # Calculate trends
        for i, driver in enumerate(drivers):
            delta = driver.value - prev_drivers[i].value
            if delta > 2:
                driver.trend = DriverTrend.UP
            elif delta < -2:
                driver.trend = DriverTrend.DOWN
            else:
                driver.trend = DriverTrend.FLAT

    # Determine confidence band
    if score >= 80:
        confidence_band = "reliable"
    elif score >= 60:
        confidence_band = "directional"
    else:
        confidence_band = "unsafe"

    return EmqCalculationResult(
        score=score,
        previous_score=previous_score,
        confidence_band=confidence_band,
        drivers=drivers,
        calculated_at=now,
    )


def calculate_aggregate_emq(
    platform_results: List[EmqCalculationResult],
) -> EmqCalculationResult:
    """
    Calculate aggregate EMQ across multiple platforms.

    Weighted average based on event volume per platform.
    """
    if not platform_results:
        return EmqCalculationResult(
            score=0.0,
            previous_score=None,
            confidence_band="unsafe",
            drivers=[],
            calculated_at=datetime.utcnow(),
        )

    # Simple average for now (could weight by spend or volume)
    avg_score = sum(r.score for r in platform_results) / len(platform_results)

    prev_scores = [r.previous_score for r in platform_results if r.previous_score is not None]
    avg_previous = sum(prev_scores) / len(prev_scores) if prev_scores else None

    # Aggregate drivers by name
    driver_totals: Dict[str, List[EmqDriverResult]] = {}
    for result in platform_results:
        for driver in result.drivers:
            if driver.name not in driver_totals:
                driver_totals[driver.name] = []
            driver_totals[driver.name].append(driver)

    aggregated_drivers = []
    for name, driver_list in driver_totals.items():
        avg_value = sum(d.value for d in driver_list) / len(driver_list)
        weight = driver_list[0].weight  # All same driver have same weight

        # Aggregate status (worst status wins)
        statuses = [d.status for d in driver_list]
        if DriverStatus.CRITICAL in statuses:
            status = DriverStatus.CRITICAL
        elif DriverStatus.WARNING in statuses:
            status = DriverStatus.WARNING
        else:
            status = DriverStatus.GOOD

        # Aggregate trend
        trends = [d.trend for d in driver_list]
        up_count = sum(1 for t in trends if t == DriverTrend.UP)
        down_count = sum(1 for t in trends if t == DriverTrend.DOWN)
        if up_count > down_count:
            trend = DriverTrend.UP
        elif down_count > up_count:
            trend = DriverTrend.DOWN
        else:
            trend = DriverTrend.FLAT

        aggregated_drivers.append(EmqDriverResult(
            name=name,
            value=round(avg_value, 1),
            weight=weight,
            status=status,
            trend=trend,
            details=f"Aggregated from {len(driver_list)} platforms"
        ))

    # Determine confidence band
    if avg_score >= 80:
        confidence_band = "reliable"
    elif avg_score >= 60:
        confidence_band = "directional"
    else:
        confidence_band = "unsafe"

    return EmqCalculationResult(
        score=round(avg_score, 1),
        previous_score=round(avg_previous, 1) if avg_previous else None,
        confidence_band=confidence_band,
        drivers=aggregated_drivers,
        calculated_at=datetime.utcnow(),
    )


# =============================================================================
# Autopilot Mode Determination
# =============================================================================

def determine_autopilot_mode(emq_score: float) -> Tuple[str, str]:
    """
    Determine autopilot mode based on EMQ score.

    Returns:
        Tuple of (mode, reason)
    """
    if emq_score >= 80:
        return ("normal", "EMQ score in reliable range")
    elif emq_score >= 60:
        return ("limited", f"EMQ score below reliable threshold ({emq_score:.1f} < 80)")
    elif emq_score >= 40:
        return ("cuts_only", f"EMQ score in unsafe range ({emq_score:.1f})")
    else:
        return ("frozen", f"EMQ score critically low ({emq_score:.1f} < 40)")


def calculate_event_loss_percentage(metrics: PlatformMetrics) -> float:
    """
    Calculate event loss percentage from metrics.

    Event loss = (expected - received) / expected * 100
    """
    if metrics.events_expected <= 0:
        return 0.0

    received = metrics.pixel_events + metrics.capi_events - metrics.matched_events
    if received < 0:
        received = max(metrics.pixel_events, metrics.capi_events)

    if received >= metrics.events_expected:
        return 0.0

    loss = (metrics.events_expected - received) / metrics.events_expected * 100
    return min(100.0, max(0.0, loss))
