# =============================================================================
# Stratum AI - Trust Layer Service
# =============================================================================
"""
Service for Trust Layer operations:
- Signal health monitoring and rollup
- Attribution variance tracking
- Trust banners and alerts
"""

import json
import threading
import time
from datetime import UTC, date, datetime
from typing import Any, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trust_layer import (
    AttributionVarianceStatus,
    FactAttributionVarianceDaily,
    FactSignalHealthDaily,
    SignalHealthStatus,
)


# =============================================================================
# Signal Health Cache (Memory Audit Feb 2026)
# =============================================================================


class SignalHealthCache:
    """
    LRU-bounded cache for signal health data with TTL.

    Reduces database load for repeated signal health queries.
    Cache is bounded to prevent unbounded memory growth (per memory audit Feb 2026).
    """

    DEFAULT_TTL = 300  # 5 minutes - signal health doesn't change frequently
    MAX_SIZE = 1024  # Maximum cache entries (matches audit recommendation)

    def __init__(self, ttl_seconds: int = DEFAULT_TTL, max_size: int = MAX_SIZE):
        self.ttl = ttl_seconds
        self.max_size = max_size
        self.cache: dict[str, tuple[float, Any]] = {}  # key -> (expiry_time, value)
        self._lock = threading.Lock()

    def _make_key(self, tenant_id: int, target_date: date) -> str:
        """Create cache key from tenant_id and date."""
        return f"signal_health:{tenant_id}:{target_date.isoformat()}"

    def get(self, tenant_id: int, target_date: date) -> Optional[Any]:
        """Get cached signal health if not expired."""
        key = self._make_key(tenant_id, target_date)
        with self._lock:
            if key in self.cache:
                expiry, value = self.cache[key]
                if time.time() < expiry:
                    return value
                # Expired, remove it
                del self.cache[key]
        return None

    def set(self, tenant_id: int, target_date: date, value: Any) -> None:
        """Cache signal health response with LRU eviction."""
        key = self._make_key(tenant_id, target_date)
        with self._lock:
            # Evict oldest entries if at capacity (LRU-style)
            if len(self.cache) >= self.max_size:
                self._evict_oldest()
            self.cache[key] = (time.time() + self.ttl, value)

    def invalidate(self, tenant_id: int, target_date: Optional[date] = None) -> None:
        """Invalidate cache for a tenant (optionally specific date)."""
        with self._lock:
            if target_date:
                key = self._make_key(tenant_id, target_date)
                self.cache.pop(key, None)
            else:
                # Invalidate all dates for tenant
                prefix = f"signal_health:{tenant_id}:"
                keys_to_delete = [k for k in self.cache if k.startswith(prefix)]
                for k in keys_to_delete:
                    del self.cache[k]

    def _evict_oldest(self) -> None:
        """Remove oldest entries when cache is full. Must be called with lock held."""
        if not self.cache:
            return
        # Find entries by expiry time (oldest first)
        sorted_entries = sorted(self.cache.items(), key=lambda x: x[1][0])
        # Remove oldest 10%
        to_remove = max(1, len(sorted_entries) // 10)
        for key, _ in sorted_entries[:to_remove]:
            del self.cache[key]


# Global cache instance (bounded per memory audit recommendation)
_signal_health_cache = SignalHealthCache(ttl_seconds=300, max_size=1024)

# =============================================================================
# Signal Health Service
# =============================================================================


class SignalHealthService:
    """Service for signal health monitoring."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_signal_health(
        self,
        tenant_id: int,
        target_date: Optional[date] = None,
    ) -> dict[str, Any]:
        """
        Get signal health summary for a tenant.

        Args:
            tenant_id: Tenant ID
            target_date: Date to query (defaults to today)

        Returns:
            Signal health summary with status, cards, and banners
        """
        if target_date is None:
            target_date = datetime.now(UTC).date()

        # Check cache first (memory optimization per audit Feb 2026)
        cached = _signal_health_cache.get(tenant_id, target_date)
        if cached is not None:
            return cached

        # Get records for the date
        result = await self.db.execute(
            select(FactSignalHealthDaily).where(
                and_(
                    FactSignalHealthDaily.tenant_id == tenant_id,
                    FactSignalHealthDaily.date == target_date,
                )
            )
        )
        records = result.scalars().all()

        if not records:
            return self._empty_response(target_date)

        # Aggregate by platform
        platform_rows = []
        overall_status = SignalHealthStatus.OK
        issues_list = []
        actions_list = []

        for record in records:
            row = {
                "platform": record.platform,
                "account_id": record.account_id,
                "emq_score": record.emq_score,
                "event_loss_pct": record.event_loss_pct,
                "freshness_minutes": record.freshness_minutes,
                "api_error_rate": record.api_error_rate,
                "status": record.status.value,
            }
            platform_rows.append(row)

            # Track worst status
            if self._status_priority(record.status) > self._status_priority(overall_status):
                overall_status = record.status

            # Collect issues and actions
            if record.issues:
                try:
                    issues_list.extend(json.loads(record.issues))
                except (json.JSONDecodeError, TypeError, ValueError):
                    issues_list.append(record.issues)

            if record.actions:
                try:
                    actions_list.extend(json.loads(record.actions))
                except (json.JSONDecodeError, TypeError, ValueError):
                    actions_list.append(record.actions)

        # Generate cards
        cards = self._generate_cards(records)

        # Generate banners
        banners = self._generate_banners(overall_status, issues_list, actions_list)

        result = {
            "date": target_date.isoformat(),
            "status": overall_status.value,
            "automation_blocked": overall_status
            in [SignalHealthStatus.DEGRADED, SignalHealthStatus.CRITICAL],
            "cards": cards,
            "platform_rows": platform_rows,
            "banners": banners,
            "issues": list(set(issues_list)),
            "actions": list(set(actions_list)),
        }

        # Cache result (memory optimization per audit Feb 2026)
        _signal_health_cache.set(tenant_id, target_date, result)

        return result

    def _status_priority(self, status: SignalHealthStatus) -> int:
        """Get priority for status comparison."""
        priorities = {
            SignalHealthStatus.OK: 0,
            SignalHealthStatus.RISK: 1,
            SignalHealthStatus.DEGRADED: 2,
            SignalHealthStatus.CRITICAL: 3,
        }
        return priorities.get(status, 0)

    def _generate_cards(self, records: list[FactSignalHealthDaily]) -> list[dict[str, Any]]:
        """Generate metric cards from records."""
        cards = []

        # Average EMQ
        emq_values = [r.emq_score for r in records if r.emq_score is not None]
        if emq_values:
            avg_emq = sum(emq_values) / len(emq_values)
            cards.append(
                {
                    "title": "Event Match Quality",
                    "value": f"{avg_emq:.0f}%",
                    "status": "ok" if avg_emq >= 90 else "risk" if avg_emq >= 80 else "degraded",
                    "description": "Average EMQ across platforms",
                }
            )

        # Average Event Loss
        loss_values = [r.event_loss_pct for r in records if r.event_loss_pct is not None]
        if loss_values:
            avg_loss = sum(loss_values) / len(loss_values)
            cards.append(
                {
                    "title": "Event Loss",
                    "value": f"{avg_loss:.1f}%",
                    "status": "ok" if avg_loss <= 5 else "risk" if avg_loss <= 10 else "degraded",
                    "description": "Average event loss rate",
                }
            )

        # Worst Freshness
        fresh_values = [r.freshness_minutes for r in records if r.freshness_minutes is not None]
        if fresh_values:
            max_fresh = max(fresh_values)
            cards.append(
                {
                    "title": "Data Freshness",
                    "value": f"{max_fresh} min",
                    "status": "ok"
                    if max_fresh <= 60
                    else "risk"
                    if max_fresh <= 180
                    else "degraded",
                    "description": "Maximum data delay",
                }
            )

        # API Health
        error_values = [r.api_error_rate for r in records if r.api_error_rate is not None]
        if error_values:
            max_error = max(error_values)
            cards.append(
                {
                    "title": "API Health",
                    "value": f"{100 - max_error:.1f}%",
                    "status": "ok" if max_error <= 2 else "risk" if max_error <= 5 else "degraded",
                    "description": "API success rate",
                }
            )

        return cards

    def _generate_banners(
        self,
        status: SignalHealthStatus,
        issues: list[str],
        actions: list[str],
    ) -> list[dict[str, Any]]:
        """Generate trust banners based on status."""
        banners = []

        if status == SignalHealthStatus.CRITICAL:
            banners.append(
                {
                    "type": "error",
                    "title": "Critical Data Quality Issue",
                    "message": "Data quality is critically impaired. Automation is blocked.",
                    "actions": actions[:3]
                    if actions
                    else ["Check API connections", "Review pixel implementation"],
                }
            )
        elif status == SignalHealthStatus.DEGRADED:
            banners.append(
                {
                    "type": "warning",
                    "title": "Data Quality Degraded",
                    "message": "Data quality is below acceptable thresholds. Proceed with caution.",
                    "actions": actions[:3]
                    if actions
                    else ["Review tracking setup", "Check event delivery"],
                }
            )
        elif status == SignalHealthStatus.RISK:
            banners.append(
                {
                    "type": "info",
                    "title": "Data Quality at Risk",
                    "message": "Some data quality metrics need attention.",
                    "actions": actions[:2] if actions else ["Monitor closely"],
                }
            )

        return banners

    def _empty_response(self, target_date: date) -> dict[str, Any]:
        """Return empty response when no data."""
        return {
            "date": target_date.isoformat(),
            "status": "no_data",
            "automation_blocked": False,
            "cards": [],
            "platform_rows": [],
            "banners": [
                {
                    "type": "info",
                    "title": "No Data Available",
                    "message": "Signal health data is not yet available for this date.",
                    "actions": ["Wait for data sync", "Check platform connections"],
                }
            ],
            "issues": [],
            "actions": [],
        }


# =============================================================================
# Attribution Variance Service
# =============================================================================


class AttributionVarianceService:
    """Service for attribution variance tracking."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_attribution_variance(
        self,
        tenant_id: int,
        target_date: Optional[date] = None,
    ) -> dict[str, Any]:
        """
        Get attribution variance summary for a tenant.

        Args:
            tenant_id: Tenant ID
            target_date: Date to query (defaults to today)

        Returns:
            Attribution variance summary with status, cards, and banners
        """
        if target_date is None:
            target_date = datetime.now(UTC).date()

        # Get records for the date
        result = await self.db.execute(
            select(FactAttributionVarianceDaily).where(
                and_(
                    FactAttributionVarianceDaily.tenant_id == tenant_id,
                    FactAttributionVarianceDaily.date == target_date,
                )
            )
        )
        records = result.scalars().all()

        if not records:
            return self._empty_response(target_date)

        # Aggregate data
        platform_rows = []
        total_ga4_revenue = 0
        total_platform_revenue = 0
        total_ga4_conversions = 0
        total_platform_conversions = 0
        worst_status = AttributionVarianceStatus.HEALTHY

        for record in records:
            row = {
                "platform": record.platform,
                "ga4_revenue": record.ga4_revenue,
                "platform_revenue": record.platform_revenue,
                "revenue_delta_pct": record.revenue_delta_pct,
                "ga4_conversions": record.ga4_conversions,
                "platform_conversions": record.platform_conversions,
                "conversion_delta_pct": record.conversion_delta_pct,
                "confidence": record.confidence,
                "status": record.status.value,
            }
            platform_rows.append(row)

            total_ga4_revenue += record.ga4_revenue
            total_platform_revenue += record.platform_revenue
            total_ga4_conversions += record.ga4_conversions
            total_platform_conversions += record.platform_conversions

            if self._status_priority(record.status) > self._status_priority(worst_status):
                worst_status = record.status

        # Calculate overall variance
        overall_rev_delta = 0
        if total_ga4_revenue > 0:
            overall_rev_delta = (
                (total_platform_revenue - total_ga4_revenue) / total_ga4_revenue
            ) * 100

        overall_conv_delta = 0
        if total_ga4_conversions > 0:
            overall_conv_delta = (
                (total_platform_conversions - total_ga4_conversions) / total_ga4_conversions
            ) * 100

        # Generate cards
        cards = [
            {
                "title": "Total GA4 Revenue",
                "value": f"${total_ga4_revenue:,.2f}",
                "status": "neutral",
            },
            {
                "title": "Total Platform Revenue",
                "value": f"${total_platform_revenue:,.2f}",
                "status": "neutral",
            },
            {
                "title": "Revenue Variance",
                "value": f"{overall_rev_delta:+.1f}%",
                "status": "ok"
                if abs(overall_rev_delta) < 15
                else "risk"
                if abs(overall_rev_delta) < 30
                else "degraded",
            },
            {
                "title": "Conversion Variance",
                "value": f"{overall_conv_delta:+.1f}%",
                "status": "ok"
                if abs(overall_conv_delta) < 15
                else "risk"
                if abs(overall_conv_delta) < 30
                else "degraded",
            },
        ]

        # Generate banners
        banners = self._generate_banners(worst_status, overall_rev_delta)

        return {
            "date": target_date.isoformat(),
            "status": worst_status.value,
            "overall_revenue_variance_pct": round(overall_rev_delta, 2),
            "overall_conversion_variance_pct": round(overall_conv_delta, 2),
            "cards": cards,
            "platform_rows": platform_rows,
            "banners": banners,
        }

    def _status_priority(self, status: AttributionVarianceStatus) -> int:
        """Get priority for status comparison."""
        priorities = {
            AttributionVarianceStatus.HEALTHY: 0,
            AttributionVarianceStatus.MINOR_VARIANCE: 1,
            AttributionVarianceStatus.MODERATE_VARIANCE: 2,
            AttributionVarianceStatus.HIGH_VARIANCE: 3,
        }
        return priorities.get(status, 0)

    def _generate_banners(
        self,
        status: AttributionVarianceStatus,
        revenue_variance: float,
    ) -> list[dict[str, Any]]:
        """Generate attribution banners."""
        banners = []

        if status == AttributionVarianceStatus.HIGH_VARIANCE:
            if revenue_variance > 0:
                banners.append(
                    {
                        "type": "warning",
                        "title": "High Attribution Variance",
                        "message": f"Platform reports {revenue_variance:.0f}% more revenue than GA4. This may affect ROAS accuracy.",
                        "actions": ["Review attribution windows", "Check cross-device tracking"],
                    }
                )
            else:
                banners.append(
                    {
                        "type": "warning",
                        "title": "High Attribution Variance",
                        "message": f"GA4 reports {abs(revenue_variance):.0f}% more revenue than platform. Check organic attribution.",
                        "actions": ["Review UTM parameters", "Check direct traffic attribution"],
                    }
                )
        elif status == AttributionVarianceStatus.MODERATE_VARIANCE:
            banners.append(
                {
                    "type": "info",
                    "title": "Attribution Variance Detected",
                    "message": "Moderate difference between platform and GA4 attribution.",
                    "actions": ["Monitor trends", "Review tracking setup"],
                }
            )

        return banners

    def _empty_response(self, target_date: date) -> dict[str, Any]:
        """Return empty response when no data."""
        return {
            "date": target_date.isoformat(),
            "status": "no_data",
            "overall_revenue_variance_pct": 0,
            "overall_conversion_variance_pct": 0,
            "cards": [],
            "platform_rows": [],
            "banners": [
                {
                    "type": "info",
                    "title": "No Attribution Data",
                    "message": "Attribution variance data is not yet available.",
                    "actions": ["Ensure GA4 is connected", "Wait for data sync"],
                }
            ],
        }
