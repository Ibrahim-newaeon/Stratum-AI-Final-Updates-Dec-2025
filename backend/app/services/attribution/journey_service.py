# =============================================================================
# Stratum AI - Customer Journey Service
# =============================================================================
"""
Customer journey tracking and visualization service.

Aggregates touchpoint data into journey paths for analysis:
- Journey path analysis (what paths lead to conversions)
- Touchpoint sequence patterns
- Channel transition analysis
- Time-to-conversion metrics
"""

from collections import defaultdict
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.crm import (
    CRMContact,
    CRMDeal,
    Touchpoint,
)

logger = get_logger(__name__)


# =============================================================================
# Journey Aggregator
# =============================================================================


class JourneyAggregator:
    """
    Aggregates journey patterns for analysis.

    Identifies common paths to conversion and channel combinations.
    """

    @staticmethod
    def path_to_string(touchpoints: list[Touchpoint], by: str = "platform") -> str:
        """Convert touchpoint sequence to a path string."""
        if by == "platform":
            elements = [tp.source or "unknown" for tp in touchpoints]
        elif by == "campaign":
            elements = [tp.campaign_name or tp.campaign_id or "direct" for tp in touchpoints]
        else:
            elements = [tp.source or "unknown" for tp in touchpoints]

        # Simplify consecutive same elements
        simplified = []
        for elem in elements:
            if not simplified or simplified[-1] != elem:
                simplified.append(elem)

        return " → ".join(simplified)

    @staticmethod
    def calculate_path_metrics(
        touchpoints: list[Touchpoint],
        conversion_time: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """Calculate metrics for a single journey path."""
        if not touchpoints:
            return {
                "touch_count": 0,
                "unique_channels": 0,
                "time_to_conversion_hours": None,
                "first_to_last_hours": None,
            }

        first_touch = touchpoints[0]
        last_touch = touchpoints[-1]
        unique_channels = len({tp.source for tp in touchpoints if tp.source})

        first_to_last_hours = None
        if len(touchpoints) > 1:
            delta = last_touch.event_ts - first_touch.event_ts
            first_to_last_hours = delta.total_seconds() / 3600

        time_to_conversion_hours = None
        if conversion_time and first_touch.event_ts:
            delta = conversion_time - first_touch.event_ts
            time_to_conversion_hours = delta.total_seconds() / 3600

        return {
            "touch_count": len(touchpoints),
            "unique_channels": unique_channels,
            "time_to_conversion_hours": round(time_to_conversion_hours, 2)
            if time_to_conversion_hours
            else None,
            "first_to_last_hours": round(first_to_last_hours, 2) if first_to_last_hours else None,
        }


# =============================================================================
# Journey Service
# =============================================================================


class JourneyService:
    """
    Service for analyzing customer journeys and conversion paths.
    """

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    async def get_contact_journey(
        self,
        contact_id: UUID,
        include_deals: bool = True,
    ) -> dict[str, Any]:
        """
        Get complete journey for a single contact.
        """
        # Get contact
        contact_result = await self.db.execute(
            select(CRMContact).where(
                and_(
                    CRMContact.id == contact_id,
                    CRMContact.tenant_id == self.tenant_id,
                )
            )
        )
        contact = contact_result.scalar_one_or_none()

        if not contact:
            return {"success": False, "error": "contact_not_found"}

        # Get touchpoints
        touchpoint_result = await self.db.execute(
            select(Touchpoint)
            .where(
                and_(
                    Touchpoint.contact_id == contact_id,
                    Touchpoint.tenant_id == self.tenant_id,
                )
            )
            .order_by(Touchpoint.event_ts)
        )
        touchpoints = touchpoint_result.scalars().all()

        # Build timeline
        timeline = []
        for tp in touchpoints:
            timeline.append(
                {
                    "type": "touchpoint",
                    "timestamp": tp.event_ts.isoformat(),
                    "event_type": tp.event_type,
                    "source": tp.source,
                    "campaign_id": tp.campaign_id,
                    "campaign_name": tp.campaign_name,
                    "adset_name": tp.adset_name,
                    "ad_name": tp.ad_name,
                    "utm_source": tp.utm_source,
                    "utm_medium": tp.utm_medium,
                    "utm_campaign": tp.utm_campaign,
                    "landing_page": tp.landing_page_url,
                    "is_first_touch": tp.is_first_touch,
                    "is_last_touch": tp.is_last_touch,
                    "is_converting_touch": tp.is_converting_touch,
                    "attribution_weight": tp.attribution_weight,
                }
            )

        # Get deals if requested
        deals = []
        if include_deals:
            deal_result = await self.db.execute(
                select(CRMDeal)
                .where(
                    and_(
                        CRMDeal.contact_id == contact_id,
                        CRMDeal.tenant_id == self.tenant_id,
                    )
                )
                .order_by(CRMDeal.crm_created_at)
            )
            deals_data = deal_result.scalars().all()

            for deal in deals_data:
                deals.append(
                    {
                        "id": str(deal.id),
                        "crm_deal_id": deal.crm_deal_id,
                        "name": deal.deal_name,
                        "stage": deal.stage,
                        "amount": deal.amount,
                        "is_won": deal.is_won,
                        "won_at": deal.won_at.isoformat() if deal.won_at else None,
                        "attributed_platform": deal.attributed_platform,
                        "attributed_campaign": deal.attributed_campaign_id,
                        "attribution_model": deal.attribution_model.value
                        if deal.attribution_model
                        else None,
                        "attribution_confidence": deal.attribution_confidence,
                    }
                )

                # Add deal events to timeline
                if deal.crm_created_at:
                    timeline.append(
                        {
                            "type": "deal_created",
                            "timestamp": deal.crm_created_at.isoformat(),
                            "deal_id": str(deal.id),
                            "deal_name": deal.deal_name,
                            "amount": deal.amount,
                        }
                    )
                if deal.won_at:
                    timeline.append(
                        {
                            "type": "deal_won",
                            "timestamp": deal.won_at.isoformat(),
                            "deal_id": str(deal.id),
                            "deal_name": deal.deal_name,
                            "amount": deal.amount,
                        }
                    )

        # Sort timeline by timestamp
        timeline.sort(key=lambda x: x["timestamp"])

        # Calculate journey metrics
        metrics = JourneyAggregator.calculate_path_metrics(
            touchpoints,
            contact.crm_created_at,
        )

        return {
            "success": True,
            "contact_id": str(contact_id),
            "crm_contact_id": contact.crm_contact_id,
            "lifecycle_stage": contact.lifecycle_stage,
            "first_touch_ts": contact.first_touch_ts.isoformat()
            if contact.first_touch_ts
            else None,
            "last_touch_ts": contact.last_touch_ts.isoformat() if contact.last_touch_ts else None,
            "touch_count": contact.touch_count,
            "path": JourneyAggregator.path_to_string(touchpoints, by="platform"),
            "metrics": metrics,
            "timeline": timeline,
            "deals": deals,
        }

    async def get_top_conversion_paths(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: int = 20,
        min_conversions: int = 2,
        path_by: str = "platform",  # platform or campaign
    ) -> list[dict[str, Any]]:
        """
        Get most common paths that lead to conversions.
        """
        # Get won deals in date range with contacts
        deal_result = await self.db.execute(
            select(CRMDeal).where(
                and_(
                    CRMDeal.tenant_id == self.tenant_id,
                    CRMDeal.is_won == True,
                    CRMDeal.won_at >= start_date,
                    CRMDeal.won_at <= end_date,
                    CRMDeal.contact_id.isnot(None),
                )
            )
        )
        deals = deal_result.scalars().all()

        # Aggregate paths
        path_stats: dict[str, dict[str, Any]] = {}

        for deal in deals:
            # Get touchpoints for this deal's contact
            touchpoint_result = await self.db.execute(
                select(Touchpoint)
                .where(
                    and_(
                        Touchpoint.contact_id == deal.contact_id,
                        Touchpoint.event_ts <= deal.won_at,
                    )
                )
                .order_by(Touchpoint.event_ts)
            )
            touchpoints = touchpoint_result.scalars().all()

            if not touchpoints:
                continue

            path = JourneyAggregator.path_to_string(touchpoints, by=path_by)
            metrics = JourneyAggregator.calculate_path_metrics(touchpoints, deal.won_at)

            if path not in path_stats:
                path_stats[path] = {
                    "path": path,
                    "conversions": 0,
                    "total_revenue": 0,
                    "total_touches": 0,
                    "total_time_hours": 0,
                    "unique_channels_sum": 0,
                }

            path_stats[path]["conversions"] += 1
            path_stats[path]["total_revenue"] += deal.amount or 0
            path_stats[path]["total_touches"] += metrics["touch_count"]
            if metrics["time_to_conversion_hours"]:
                path_stats[path]["total_time_hours"] += metrics["time_to_conversion_hours"]
            path_stats[path]["unique_channels_sum"] += metrics["unique_channels"]

        # Calculate averages and filter
        results = []
        for path, stats in path_stats.items():
            if stats["conversions"] < min_conversions:
                continue

            results.append(
                {
                    "path": path,
                    "conversions": stats["conversions"],
                    "total_revenue": round(stats["total_revenue"], 2),
                    "avg_revenue": round(stats["total_revenue"] / stats["conversions"], 2),
                    "avg_touches": round(stats["total_touches"] / stats["conversions"], 1),
                    "avg_time_to_conversion_hours": round(
                        stats["total_time_hours"] / stats["conversions"], 1
                    )
                    if stats["total_time_hours"] > 0
                    else None,
                    "avg_unique_channels": round(
                        stats["unique_channels_sum"] / stats["conversions"], 1
                    ),
                }
            )

        # Sort by conversions
        results.sort(key=lambda x: x["conversions"], reverse=True)

        return results[:limit]

    async def get_channel_transitions(
        self,
        start_date: datetime,
        end_date: datetime,
        min_transitions: int = 5,
    ) -> dict[str, Any]:
        """
        Analyze channel transitions (Sankey diagram data).

        Returns data for visualizing how users move between channels.
        """
        # Get contacts with multiple touchpoints in date range
        contact_result = await self.db.execute(
            select(CRMContact.id).where(
                and_(
                    CRMContact.tenant_id == self.tenant_id,
                    CRMContact.touch_count > 1,
                    CRMContact.first_touch_ts >= start_date,
                    CRMContact.last_touch_ts <= end_date,
                )
            )
        )
        contact_ids = [row[0] for row in contact_result.fetchall()]

        # Count transitions between channels
        transitions: dict[tuple[str, str], int] = defaultdict(int)
        channel_totals: dict[str, int] = defaultdict(int)

        for contact_id in contact_ids:
            touchpoint_result = await self.db.execute(
                select(Touchpoint)
                .where(
                    and_(
                        Touchpoint.contact_id == contact_id,
                        Touchpoint.tenant_id == self.tenant_id,
                    )
                )
                .order_by(Touchpoint.event_ts)
            )
            touchpoints = touchpoint_result.scalars().all()

            if len(touchpoints) < 2:
                continue

            for i in range(len(touchpoints) - 1):
                from_channel = touchpoints[i].source or "unknown"
                to_channel = touchpoints[i + 1].source or "unknown"

                transitions[(from_channel, to_channel)] += 1
                channel_totals[from_channel] += 1

        # Build Sankey-style data
        nodes = list(set([t[0] for t in transitions] + [t[1] for t in transitions]))
        node_index = {node: i for i, node in enumerate(nodes)}

        links = []
        for (from_channel, to_channel), count in transitions.items():
            if count >= min_transitions:
                links.append(
                    {
                        "source": node_index[from_channel],
                        "target": node_index[to_channel],
                        "source_name": from_channel,
                        "target_name": to_channel,
                        "value": count,
                        "percentage": round(count / channel_totals[from_channel] * 100, 1),
                    }
                )

        # Sort links by value
        links.sort(key=lambda x: x["value"], reverse=True)

        return {
            "nodes": [{"name": node, "index": i} for i, node in enumerate(nodes)],
            "links": links,
            "total_transitions": sum(transitions.values()),
            "unique_paths": len(transitions),
        }

    async def get_journey_metrics(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, Any]:
        """
        Get aggregate journey metrics for the tenant.
        """
        # Get won deals in date range
        deal_result = await self.db.execute(
            select(CRMDeal).where(
                and_(
                    CRMDeal.tenant_id == self.tenant_id,
                    CRMDeal.is_won == True,
                    CRMDeal.won_at >= start_date,
                    CRMDeal.won_at <= end_date,
                    CRMDeal.contact_id.isnot(None),
                )
            )
        )
        deals = deal_result.scalars().all()

        # Calculate metrics
        touch_counts = []
        time_to_conversions = []
        channel_counts = []
        platforms_seen = defaultdict(int)

        for deal in deals:
            touchpoint_result = await self.db.execute(
                select(Touchpoint)
                .where(
                    and_(
                        Touchpoint.contact_id == deal.contact_id,
                        Touchpoint.event_ts <= deal.won_at,
                    )
                )
                .order_by(Touchpoint.event_ts)
            )
            touchpoints = touchpoint_result.scalars().all()

            if not touchpoints:
                continue

            metrics = JourneyAggregator.calculate_path_metrics(touchpoints, deal.won_at)

            touch_counts.append(metrics["touch_count"])
            channel_counts.append(metrics["unique_channels"])
            if metrics["time_to_conversion_hours"]:
                time_to_conversions.append(metrics["time_to_conversion_hours"])

            for tp in touchpoints:
                if tp.source:
                    platforms_seen[tp.source] += 1

        # Calculate averages
        avg_touches = sum(touch_counts) / len(touch_counts) if touch_counts else 0
        avg_time = sum(time_to_conversions) / len(time_to_conversions) if time_to_conversions else 0
        avg_channels = sum(channel_counts) / len(channel_counts) if channel_counts else 0

        # Calculate distributions
        touch_distribution = {}
        for count in touch_counts:
            bucket = f"{count}" if count <= 5 else "6+"
            touch_distribution[bucket] = touch_distribution.get(bucket, 0) + 1

        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "summary": {
                "total_conversions": len(deals),
                "total_revenue": sum(d.amount or 0 for d in deals),
                "avg_touches_per_conversion": round(avg_touches, 1),
                "avg_time_to_conversion_hours": round(avg_time, 1),
                "avg_time_to_conversion_days": round(avg_time / 24, 1),
                "avg_channels_per_journey": round(avg_channels, 1),
            },
            "touch_distribution": touch_distribution,
            "platform_contribution": dict(
                sorted(
                    platforms_seen.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
            ),
        }

    async def get_assisted_conversions(
        self,
        start_date: datetime,
        end_date: datetime,
        group_by: str = "platform",  # platform, campaign
    ) -> list[dict[str, Any]]:
        """
        Get assisted conversion metrics (touchpoints that assisted but weren't last touch).
        """
        # Get won deals with multiple touchpoints
        deal_result = await self.db.execute(
            select(CRMDeal).where(
                and_(
                    CRMDeal.tenant_id == self.tenant_id,
                    CRMDeal.is_won == True,
                    CRMDeal.won_at >= start_date,
                    CRMDeal.won_at <= end_date,
                    CRMDeal.contact_id.isnot(None),
                )
            )
        )
        deals = deal_result.scalars().all()

        # Track assists and last-touches
        stats: dict[str, dict[str, Any]] = {}

        for deal in deals:
            touchpoint_result = await self.db.execute(
                select(Touchpoint)
                .where(
                    and_(
                        Touchpoint.contact_id == deal.contact_id,
                        Touchpoint.event_ts <= deal.won_at,
                    )
                )
                .order_by(Touchpoint.event_ts)
            )
            touchpoints = touchpoint_result.scalars().all()

            if not touchpoints:
                continue

            revenue = deal.amount or 0

            for i, tp in enumerate(touchpoints):
                if group_by == "platform":
                    key = tp.source or "unknown"
                else:
                    key = tp.campaign_id or "direct"

                if key not in stats:
                    stats[key] = {
                        "key": key,
                        "name": key if group_by == "platform" else (tp.campaign_name or key),
                        "last_touch_conversions": 0,
                        "last_touch_revenue": 0,
                        "assisted_conversions": 0,
                        "assisted_revenue": 0,
                        "total_touches": 0,
                    }

                stats[key]["total_touches"] += 1

                if i == len(touchpoints) - 1:
                    # Last touch
                    stats[key]["last_touch_conversions"] += 1
                    stats[key]["last_touch_revenue"] += revenue
                else:
                    # Assist
                    stats[key]["assisted_conversions"] += 1
                    stats[key]["assisted_revenue"] += revenue

        # Calculate ratios
        results = []
        for key, data in stats.items():
            total_conversions = data["last_touch_conversions"] + data["assisted_conversions"]
            assist_ratio = (
                data["assisted_conversions"] / total_conversions if total_conversions > 0 else 0
            )

            results.append(
                {
                    **data,
                    "total_conversions": total_conversions,
                    "total_revenue": data["last_touch_revenue"] + data["assisted_revenue"],
                    "assist_ratio": round(assist_ratio, 2),
                }
            )

        return sorted(results, key=lambda x: x["total_touches"], reverse=True)

    async def get_time_lag_report(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, Any]:
        """
        Analyze time lag between touchpoints and conversion.
        """
        # Get won deals
        deal_result = await self.db.execute(
            select(CRMDeal).where(
                and_(
                    CRMDeal.tenant_id == self.tenant_id,
                    CRMDeal.is_won == True,
                    CRMDeal.won_at >= start_date,
                    CRMDeal.won_at <= end_date,
                    CRMDeal.contact_id.isnot(None),
                )
            )
        )
        deals = deal_result.scalars().all()

        # Time lag buckets (in days)
        buckets = {
            "0": {"label": "Same day", "count": 0, "revenue": 0},
            "1": {"label": "1 day", "count": 0, "revenue": 0},
            "2-3": {"label": "2-3 days", "count": 0, "revenue": 0},
            "4-7": {"label": "4-7 days", "count": 0, "revenue": 0},
            "8-14": {"label": "8-14 days", "count": 0, "revenue": 0},
            "15-30": {"label": "15-30 days", "count": 0, "revenue": 0},
            "31-60": {"label": "31-60 days", "count": 0, "revenue": 0},
            "60+": {"label": "60+ days", "count": 0, "revenue": 0},
        }

        for deal in deals:
            # Get first touchpoint
            touchpoint_result = await self.db.execute(
                select(Touchpoint)
                .where(
                    and_(
                        Touchpoint.contact_id == deal.contact_id,
                        Touchpoint.event_ts <= deal.won_at,
                    )
                )
                .order_by(Touchpoint.event_ts)
                .limit(1)
            )
            first_touch = touchpoint_result.scalar_one_or_none()

            if not first_touch:
                continue

            days_to_convert = (deal.won_at - first_touch.event_ts).days
            revenue = deal.amount or 0

            # Assign to bucket
            if days_to_convert == 0:
                bucket_key = "0"
            elif days_to_convert == 1:
                bucket_key = "1"
            elif days_to_convert <= 3:
                bucket_key = "2-3"
            elif days_to_convert <= 7:
                bucket_key = "4-7"
            elif days_to_convert <= 14:
                bucket_key = "8-14"
            elif days_to_convert <= 30:
                bucket_key = "15-30"
            elif days_to_convert <= 60:
                bucket_key = "31-60"
            else:
                bucket_key = "60+"

            buckets[bucket_key]["count"] += 1
            buckets[bucket_key]["revenue"] += revenue

        total_conversions = sum(b["count"] for b in buckets.values())

        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "total_conversions": total_conversions,
            "buckets": [
                {
                    "key": key,
                    "label": data["label"],
                    "conversions": data["count"],
                    "revenue": round(data["revenue"], 2),
                    "percentage": round(data["count"] / total_conversions * 100, 1)
                    if total_conversions > 0
                    else 0,
                }
                for key, data in buckets.items()
            ],
        }
