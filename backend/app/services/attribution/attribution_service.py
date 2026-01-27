# =============================================================================
# Stratum AI - Multi-Touch Attribution Service
# =============================================================================
"""
Multi-Touch Attribution (MTA) calculations and reporting.

Supported models:
- First Touch: 100% credit to first interaction
- Last Touch: 100% credit to last interaction
- Linear: Equal credit to all touchpoints
- Position-Based (U-shaped): 40% first, 40% last, 20% middle
- Time Decay: Exponential decay toward conversion
- W-shaped: 30% first, 30% lead creation, 30% last, 10% middle
- Custom: User-defined weights
"""

import math
from datetime import UTC, datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.crm import (
    AttributionModel,
    CRMDeal,
    Touchpoint,
)

logger = get_logger(__name__)

# =============================================================================
# Platform-Specific Attribution Windows
# =============================================================================
# Default attribution windows (in days) per platform based on industry standards
# and typical customer journey lengths for each advertising platform.
PLATFORM_ATTRIBUTION_WINDOWS = {
    "meta": {
        "click_window": 7,  # Meta default: 7-day click
        "view_window": 1,  # Meta default: 1-day view
        "half_life_days": 3.5,  # Half-life for time decay
        "max_lookback": 28,  # Maximum lookback period
    },
    "google": {
        "click_window": 30,  # Google default: 30-day click
        "view_window": 0,  # Google doesn't use view-through by default
        "half_life_days": 7.0,  # Longer half-life for search intent
        "max_lookback": 90,  # Google supports up to 90 days
    },
    "tiktok": {
        "click_window": 7,  # TikTok default: 7-day click
        "view_window": 1,  # TikTok default: 1-day view
        "half_life_days": 2.0,  # Shorter - impulse purchases
        "max_lookback": 28,
    },
    "snapchat": {
        "click_window": 28,  # Snapchat default: 28-day click
        "view_window": 1,  # Snapchat default: 1-day view
        "half_life_days": 3.0,
        "max_lookback": 28,
    },
    "pinterest": {
        "click_window": 30,  # Pinterest supports longer consideration
        "view_window": 1,
        "half_life_days": 7.0,
        "max_lookback": 60,
    },
    "default": {
        "click_window": 7,
        "view_window": 1,
        "half_life_days": 7.0,
        "max_lookback": 30,
    },
}


def get_platform_attribution_config(platform: str) -> dict[str, Any]:
    """
    Get attribution window configuration for a specific platform.

    Args:
        platform: Platform name (meta, google, tiktok, etc.)

    Returns:
        Dict with click_window, view_window, half_life_days, max_lookback
    """
    platform_lower = (platform or "default").lower()
    return PLATFORM_ATTRIBUTION_WINDOWS.get(platform_lower, PLATFORM_ATTRIBUTION_WINDOWS["default"])


# =============================================================================
# Attribution Weight Calculators
# =============================================================================


class AttributionCalculator:
    """
    Calculates attribution weights for different models.

    All methods return a list of weights that sum to 1.0.
    """

    @staticmethod
    def first_touch(touchpoint_count: int) -> list[float]:
        """100% credit to first touchpoint."""
        if touchpoint_count == 0:
            return []
        weights = [0.0] * touchpoint_count
        weights[0] = 1.0
        return weights

    @staticmethod
    def last_touch(touchpoint_count: int) -> list[float]:
        """100% credit to last touchpoint."""
        if touchpoint_count == 0:
            return []
        weights = [0.0] * touchpoint_count
        weights[-1] = 1.0
        return weights

    @staticmethod
    def linear(touchpoint_count: int) -> list[float]:
        """Equal credit to all touchpoints."""
        if touchpoint_count == 0:
            return []
        weight = 1.0 / touchpoint_count
        return [weight] * touchpoint_count

    @staticmethod
    def position_based(touchpoint_count: int) -> list[float]:
        """
        U-shaped: 40% first, 40% last, 20% distributed to middle.

        Single touch: 100%
        Two touches: 50% each
        Three+ touches: 40% first, 40% last, remaining 20% split among middle
        """
        if touchpoint_count == 0:
            return []
        if touchpoint_count == 1:
            return [1.0]
        if touchpoint_count == 2:
            return [0.5, 0.5]

        weights = [0.0] * touchpoint_count
        weights[0] = 0.4
        weights[-1] = 0.4

        # Distribute remaining 20% among middle touchpoints
        middle_count = touchpoint_count - 2
        middle_weight = 0.2 / middle_count
        for i in range(1, touchpoint_count - 1):
            weights[i] = middle_weight

        return weights

    @staticmethod
    def time_decay(
        touchpoint_count: int,
        half_life_days: float = 7.0,
        touchpoint_times: Optional[list[datetime]] = None,
        conversion_time: Optional[datetime] = None,
    ) -> list[float]:
        """
        More recent touchpoints get more credit.

        Uses exponential decay with configurable half-life.
        Default half-life: 7 days (touchpoint loses half its value every 7 days).
        """
        if touchpoint_count == 0:
            return []
        if touchpoint_count == 1:
            return [1.0]

        # If no timestamps provided, use geometric decay
        if touchpoint_times is None or conversion_time is None:
            # Simple geometric decay: each touchpoint is 2x the previous
            raw_weights = [2**i for i in range(touchpoint_count)]
            total = sum(raw_weights)
            return [w / total for w in raw_weights]

        # Calculate decay based on actual timestamps
        decay_constant = math.log(2) / half_life_days
        raw_weights = []

        for tp_time in touchpoint_times:
            days_before = (conversion_time - tp_time).total_seconds() / 86400
            weight = math.exp(-decay_constant * days_before)
            raw_weights.append(weight)

        # Normalize to sum to 1.0
        total = sum(raw_weights)
        if total == 0:
            return AttributionCalculator.linear(touchpoint_count)

        return [w / total for w in raw_weights]

    @staticmethod
    def w_shaped(
        touchpoint_count: int,
        lead_creation_index: Optional[int] = None,
    ) -> list[float]:
        """
        W-shaped: 30% first, 30% lead creation, 30% last, 10% middle.

        If lead_creation_index is not provided, uses the middle touchpoint.
        For B2B funnels where lead creation is a key milestone.
        """
        if touchpoint_count == 0:
            return []
        if touchpoint_count == 1:
            return [1.0]
        if touchpoint_count == 2:
            return [0.5, 0.5]
        if touchpoint_count == 3:
            return [0.333, 0.334, 0.333]

        weights = [0.0] * touchpoint_count

        # First touch: 30%
        weights[0] = 0.3

        # Last touch: 30%
        weights[-1] = 0.3

        # Lead creation (middle by default): 30%
        if lead_creation_index is None:
            lead_creation_index = touchpoint_count // 2
        lead_creation_index = max(1, min(lead_creation_index, touchpoint_count - 2))
        weights[lead_creation_index] = 0.3

        # Distribute remaining 10% among other middle touchpoints
        middle_indices = [i for i in range(1, touchpoint_count - 1) if i != lead_creation_index]
        if middle_indices:
            middle_weight = 0.1 / len(middle_indices)
            for i in middle_indices:
                weights[i] = middle_weight
        else:
            # No other middle touchpoints, give extra to lead creation
            weights[lead_creation_index] += 0.1

        return weights

    @staticmethod
    def custom(weights: list[float]) -> list[float]:
        """Apply custom weights (normalized to sum to 1.0)."""
        if not weights:
            return []
        total = sum(weights)
        if total == 0:
            return AttributionCalculator.linear(len(weights))
        return [w / total for w in weights]

    @staticmethod
    def get_weights(
        model: AttributionModel,
        touchpoint_count: int,
        touchpoint_times: Optional[list[datetime]] = None,
        conversion_time: Optional[datetime] = None,
        half_life_days: float = 7.0,
        lead_creation_index: Optional[int] = None,
    ) -> list[float]:
        """Get attribution weights for a given model."""
        if model == AttributionModel.FIRST_TOUCH:
            return AttributionCalculator.first_touch(touchpoint_count)
        elif model == AttributionModel.LAST_TOUCH:
            return AttributionCalculator.last_touch(touchpoint_count)
        elif model == AttributionModel.LINEAR:
            return AttributionCalculator.linear(touchpoint_count)
        elif model == AttributionModel.POSITION_BASED:
            return AttributionCalculator.position_based(touchpoint_count)
        elif model == AttributionModel.TIME_DECAY:
            return AttributionCalculator.time_decay(
                touchpoint_count,
                half_life_days,
                touchpoint_times,
                conversion_time,
            )
        else:
            # Default to last touch
            return AttributionCalculator.last_touch(touchpoint_count)


# =============================================================================
# Attribution Service
# =============================================================================


class AttributionService:
    """
    Service for calculating and storing multi-touch attribution.
    """

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    async def attribute_deal(
        self,
        deal_id: UUID,
        model: AttributionModel = AttributionModel.LAST_TOUCH,
        half_life_days: float = 7.0,
    ) -> dict[str, Any]:
        """
        Calculate attribution for a single deal.

        Returns attribution breakdown by touchpoint.
        """
        # Get deal with contact
        deal_result = await self.db.execute(
            select(CRMDeal).where(and_(CRMDeal.id == deal_id, CRMDeal.tenant_id == self.tenant_id))
        )
        deal = deal_result.scalar_one_or_none()

        if not deal:
            return {"success": False, "error": "deal_not_found"}

        if not deal.contact_id:
            return {"success": False, "error": "no_contact_linked"}

        # Get touchpoints for the contact
        touchpoints = await self._get_contact_touchpoints(
            deal.contact_id,
            before_time=deal.won_at or deal.crm_updated_at or datetime.now(UTC),
        )

        if not touchpoints:
            return {"success": False, "error": "no_touchpoints"}

        # Calculate weights
        touchpoint_times = [tp.event_ts for tp in touchpoints]
        conversion_time = deal.won_at or datetime.now(UTC)

        weights = AttributionCalculator.get_weights(
            model=model,
            touchpoint_count=len(touchpoints),
            touchpoint_times=touchpoint_times,
            conversion_time=conversion_time,
            half_life_days=half_life_days,
        )

        # Apply weights to touchpoints
        attributed_revenue = deal.amount or 0
        attribution_breakdown = []

        for i, (tp, weight) in enumerate(zip(touchpoints, weights, strict=False)):
            tp.attribution_weight = weight
            tp.is_converting_touch = True

            attribution_breakdown.append(
                {
                    "touchpoint_id": str(tp.id),
                    "position": i + 1,
                    "event_ts": tp.event_ts.isoformat(),
                    "source": tp.source,
                    "campaign_id": tp.campaign_id,
                    "campaign_name": tp.campaign_name,
                    "weight": round(weight, 4),
                    "attributed_revenue": round(attributed_revenue * weight, 2),
                }
            )

        # Update deal with primary attribution (based on model)
        if model == AttributionModel.FIRST_TOUCH:
            primary_tp = touchpoints[0]
        else:
            # All other models use last touch as primary
            primary_tp = touchpoints[-1]

        deal.attributed_touchpoint_id = primary_tp.id
        deal.attributed_campaign_id = primary_tp.campaign_id
        deal.attributed_adset_id = primary_tp.adset_id
        deal.attributed_ad_id = primary_tp.ad_id
        deal.attributed_platform = primary_tp.source
        deal.attribution_model = model
        deal.attribution_confidence = self._calculate_confidence(touchpoints)

        await self.db.commit()

        return {
            "success": True,
            "deal_id": str(deal_id),
            "model": model.value,
            "touchpoint_count": len(touchpoints),
            "total_revenue": attributed_revenue,
            "confidence": deal.attribution_confidence,
            "breakdown": attribution_breakdown,
        }

    async def attribute_deal_with_platform_windows(
        self,
        deal_id: UUID,
        model: AttributionModel = AttributionModel.TIME_DECAY,
        platform: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Calculate attribution using platform-specific attribution windows.

        This method automatically uses the appropriate attribution window
        configuration based on the platform, providing more accurate attribution
        that aligns with how each platform measures conversions.

        Args:
            deal_id: The deal to attribute
            model: Attribution model to use (TIME_DECAY recommended)
            platform: Override platform detection (auto-detected from touchpoints if not provided)

        Returns:
            Attribution breakdown with platform-specific window applied
        """
        # Get deal
        deal_result = await self.db.execute(
            select(CRMDeal).where(and_(CRMDeal.id == deal_id, CRMDeal.tenant_id == self.tenant_id))
        )
        deal = deal_result.scalar_one_or_none()

        if not deal:
            return {"success": False, "error": "deal_not_found"}

        if not deal.contact_id:
            return {"success": False, "error": "no_contact_linked"}

        conversion_time = deal.won_at or deal.crm_updated_at or datetime.now(UTC)

        # Get all touchpoints first to determine primary platform
        all_touchpoints = await self._get_contact_touchpoints(
            deal.contact_id,
            before_time=conversion_time,
        )

        if not all_touchpoints:
            return {"success": False, "error": "no_touchpoints"}

        # Determine primary platform from touchpoints or use override
        if platform:
            primary_platform = platform.lower()
        else:
            # Count touchpoints per platform, use most common
            platform_counts = {}
            for tp in all_touchpoints:
                p = (tp.source or "unknown").lower()
                platform_counts[p] = platform_counts.get(p, 0) + 1
            primary_platform = max(platform_counts, key=platform_counts.get)

        # Get platform-specific config
        platform_config = get_platform_attribution_config(primary_platform)
        click_window = platform_config["click_window"]
        view_window = platform_config["view_window"]
        half_life_days = platform_config["half_life_days"]
        max_lookback = platform_config["max_lookback"]

        # Filter touchpoints by platform-specific windows
        filtered_touchpoints = []
        for tp in all_touchpoints:
            days_before = (conversion_time - tp.event_ts).total_seconds() / 86400

            # Skip if beyond max lookback
            if days_before > max_lookback:
                continue

            # Determine if this is a click or view touchpoint
            is_click = tp.gclid or tp.fbclid or tp.ttclid or tp.sclid or tp.click_id

            if is_click:
                # Apply click window
                if days_before <= click_window:
                    filtered_touchpoints.append(tp)
            else:
                # Apply view window (view-through attribution)
                if view_window > 0 and days_before <= view_window:
                    filtered_touchpoints.append(tp)

        if not filtered_touchpoints:
            # Fall back to all touchpoints if filtering removes everything
            filtered_touchpoints = all_touchpoints
            logger.warning(
                "platform_window_filter_fallback",
                deal_id=str(deal_id),
                platform=primary_platform,
                original_count=len(all_touchpoints),
            )

        # Calculate weights with platform-specific half-life
        touchpoint_times = [tp.event_ts for tp in filtered_touchpoints]

        weights = AttributionCalculator.get_weights(
            model=model,
            touchpoint_count=len(filtered_touchpoints),
            touchpoint_times=touchpoint_times,
            conversion_time=conversion_time,
            half_life_days=half_life_days,
        )

        # Apply weights
        attributed_revenue = deal.amount or 0
        attribution_breakdown = []

        for i, (tp, weight) in enumerate(zip(filtered_touchpoints, weights, strict=False)):
            tp.attribution_weight = weight
            tp.is_converting_touch = True

            days_before = (conversion_time - tp.event_ts).total_seconds() / 86400
            is_click = tp.gclid or tp.fbclid or tp.ttclid or tp.sclid or tp.click_id

            attribution_breakdown.append(
                {
                    "touchpoint_id": str(tp.id),
                    "position": i + 1,
                    "event_ts": tp.event_ts.isoformat(),
                    "source": tp.source,
                    "campaign_id": tp.campaign_id,
                    "campaign_name": tp.campaign_name,
                    "weight": round(weight, 4),
                    "attributed_revenue": round(attributed_revenue * weight, 2),
                    "days_before_conversion": round(days_before, 1),
                    "touchpoint_type": "click" if is_click else "view",
                }
            )

        # Update deal attribution
        if model == AttributionModel.FIRST_TOUCH:
            primary_tp = filtered_touchpoints[0]
        else:
            primary_tp = filtered_touchpoints[-1]

        deal.attributed_touchpoint_id = primary_tp.id
        deal.attributed_campaign_id = primary_tp.campaign_id
        deal.attributed_adset_id = primary_tp.adset_id
        deal.attributed_ad_id = primary_tp.ad_id
        deal.attributed_platform = primary_tp.source
        deal.attribution_model = model
        deal.attribution_confidence = self._calculate_confidence(filtered_touchpoints)

        await self.db.commit()

        return {
            "success": True,
            "deal_id": str(deal_id),
            "model": model.value,
            "platform": primary_platform,
            "platform_config": {
                "click_window_days": click_window,
                "view_window_days": view_window,
                "half_life_days": half_life_days,
                "max_lookback_days": max_lookback,
            },
            "touchpoint_count": len(filtered_touchpoints),
            "filtered_from": len(all_touchpoints),
            "total_revenue": attributed_revenue,
            "confidence": deal.attribution_confidence,
            "breakdown": attribution_breakdown,
        }

    async def batch_attribute_deals(
        self,
        model: AttributionModel = AttributionModel.LAST_TOUCH,
        deal_ids: Optional[list[UUID]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """
        Batch attribute multiple deals.

        If deal_ids not provided, attributes all unattributed won deals in date range.
        """
        # Build query
        query = select(CRMDeal).where(
            and_(
                CRMDeal.tenant_id == self.tenant_id,
                CRMDeal.is_won == True,
                CRMDeal.contact_id.isnot(None),
            )
        )

        if deal_ids:
            query = query.where(CRMDeal.id.in_(deal_ids))
        else:
            # Only unattributed deals
            query = query.where(CRMDeal.attributed_campaign_id.is_(None))

        if start_date:
            query = query.where(CRMDeal.won_at >= start_date)
        if end_date:
            query = query.where(CRMDeal.won_at <= end_date)

        result = await self.db.execute(query)
        deals = result.scalars().all()

        results = {
            "total": len(deals),
            "attributed": 0,
            "failed": 0,
            "errors": [],
        }

        for deal in deals:
            try:
                attr_result = await self.attribute_deal(deal.id, model)
                if attr_result.get("success"):
                    results["attributed"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(
                        {
                            "deal_id": str(deal.id),
                            "error": attr_result.get("error"),
                        }
                    )
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(
                    {
                        "deal_id": str(deal.id),
                        "error": str(e),
                    }
                )

        logger.info(
            "batch_attribution_complete",
            tenant_id=self.tenant_id,
            model=model.value,
            total=results["total"],
            attributed=results["attributed"],
        )

        return results

    async def compare_attribution_models(
        self,
        start_date: datetime,
        end_date: datetime,
        models: Optional[list[AttributionModel]] = None,
    ) -> dict[str, Any]:
        """
        Compare attribution results across different models.

        Calculates attributed revenue by campaign for each model.
        """
        if models is None:
            models = [
                AttributionModel.FIRST_TOUCH,
                AttributionModel.LAST_TOUCH,
                AttributionModel.LINEAR,
                AttributionModel.POSITION_BASED,
                AttributionModel.TIME_DECAY,
            ]

        # Get won deals with touchpoints in date range
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

        # Calculate attribution for each model
        model_results = {}

        for model in models:
            campaign_attribution: dict[str, dict[str, Any]] = {}
            platform_attribution: dict[str, dict[str, Any]] = {}

            for deal in deals:
                touchpoints = await self._get_contact_touchpoints(
                    deal.contact_id,
                    before_time=deal.won_at,
                )

                if not touchpoints:
                    continue

                revenue = deal.amount or 0
                touchpoint_times = [tp.event_ts for tp in touchpoints]

                weights = AttributionCalculator.get_weights(
                    model=model,
                    touchpoint_count=len(touchpoints),
                    touchpoint_times=touchpoint_times,
                    conversion_time=deal.won_at,
                )

                for tp, weight in zip(touchpoints, weights, strict=False):
                    # By campaign
                    campaign_key = tp.campaign_id or "direct"
                    if campaign_key not in campaign_attribution:
                        campaign_attribution[campaign_key] = {
                            "campaign_id": campaign_key,
                            "campaign_name": tp.campaign_name or campaign_key,
                            "attributed_revenue": 0,
                            "attributed_deals": 0,
                            "touchpoints": 0,
                        }
                    campaign_attribution[campaign_key]["attributed_revenue"] += revenue * weight
                    campaign_attribution[campaign_key]["attributed_deals"] += weight
                    campaign_attribution[campaign_key]["touchpoints"] += 1

                    # By platform
                    platform_key = tp.source or "unknown"
                    if platform_key not in platform_attribution:
                        platform_attribution[platform_key] = {
                            "platform": platform_key,
                            "attributed_revenue": 0,
                            "attributed_deals": 0,
                            "touchpoints": 0,
                        }
                    platform_attribution[platform_key]["attributed_revenue"] += revenue * weight
                    platform_attribution[platform_key]["attributed_deals"] += weight
                    platform_attribution[platform_key]["touchpoints"] += 1

            model_results[model.value] = {
                "model": model.value,
                "by_campaign": sorted(
                    campaign_attribution.values(),
                    key=lambda x: x["attributed_revenue"],
                    reverse=True,
                ),
                "by_platform": sorted(
                    platform_attribution.values(),
                    key=lambda x: x["attributed_revenue"],
                    reverse=True,
                ),
            }

        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "deals_analyzed": len(deals),
            "total_revenue": sum(d.amount or 0 for d in deals),
            "models": model_results,
        }

    async def get_campaign_attribution(
        self,
        campaign_id: str,
        start_date: datetime,
        end_date: datetime,
        model: AttributionModel = AttributionModel.LAST_TOUCH,
    ) -> dict[str, Any]:
        """
        Get attribution details for a specific campaign.
        """
        # Get touchpoints for this campaign
        touchpoint_result = await self.db.execute(
            select(Touchpoint).where(
                and_(
                    Touchpoint.tenant_id == self.tenant_id,
                    Touchpoint.campaign_id == campaign_id,
                    Touchpoint.event_ts >= start_date,
                    Touchpoint.event_ts <= end_date,
                )
            )
        )
        touchpoints = touchpoint_result.scalars().all()

        # Get contacts with these touchpoints
        contact_ids = list({tp.contact_id for tp in touchpoints if tp.contact_id})

        if not contact_ids:
            return {
                "campaign_id": campaign_id,
                "touchpoints": len(touchpoints),
                "contacts_reached": 0,
                "deals_attributed": 0,
                "attributed_revenue": 0,
                "by_model": {},
            }

        # Get deals for these contacts
        deal_result = await self.db.execute(
            select(CRMDeal).where(
                and_(
                    CRMDeal.tenant_id == self.tenant_id,
                    CRMDeal.contact_id.in_(contact_ids),
                    CRMDeal.is_won == True,
                )
            )
        )
        deals = deal_result.scalars().all()

        # Calculate attribution for each deal
        attributed_revenue = 0
        attributed_deals = 0

        for deal in deals:
            deal_touchpoints = await self._get_contact_touchpoints(
                deal.contact_id,
                before_time=deal.won_at,
            )

            if not deal_touchpoints:
                continue

            # Find campaign's position in journey
            campaign_indices = [
                i for i, tp in enumerate(deal_touchpoints) if tp.campaign_id == campaign_id
            ]

            if not campaign_indices:
                continue

            # Get weights for this journey
            touchpoint_times = [tp.event_ts for tp in deal_touchpoints]
            weights = AttributionCalculator.get_weights(
                model=model,
                touchpoint_count=len(deal_touchpoints),
                touchpoint_times=touchpoint_times,
                conversion_time=deal.won_at,
            )

            # Sum weights for this campaign's touchpoints
            campaign_weight = sum(weights[i] for i in campaign_indices)
            attributed_revenue += (deal.amount or 0) * campaign_weight
            attributed_deals += campaign_weight

        return {
            "campaign_id": campaign_id,
            "model": model.value,
            "touchpoints": len(touchpoints),
            "contacts_reached": len(contact_ids),
            "deals_attributed": round(attributed_deals, 2),
            "attributed_revenue": round(attributed_revenue, 2),
        }

    async def get_attribution_summary(
        self,
        start_date: datetime,
        end_date: datetime,
        model: AttributionModel = AttributionModel.LAST_TOUCH,
        group_by: str = "platform",  # platform, campaign, adset, day
    ) -> list[dict[str, Any]]:
        """
        Get attribution summary grouped by dimension.
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

        # Calculate attribution
        groups: dict[str, dict[str, Any]] = {}

        for deal in deals:
            touchpoints = await self._get_contact_touchpoints(
                deal.contact_id,
                before_time=deal.won_at,
            )

            if not touchpoints:
                continue

            revenue = deal.amount or 0
            touchpoint_times = [tp.event_ts for tp in touchpoints]

            weights = AttributionCalculator.get_weights(
                model=model,
                touchpoint_count=len(touchpoints),
                touchpoint_times=touchpoint_times,
                conversion_time=deal.won_at,
            )

            for tp, weight in zip(touchpoints, weights, strict=False):
                # Determine group key
                if group_by == "platform":
                    key = tp.source or "unknown"
                    display_name = key
                elif group_by == "campaign":
                    key = tp.campaign_id or "direct"
                    display_name = tp.campaign_name or key
                elif group_by == "adset":
                    key = tp.adset_id or "unknown"
                    display_name = tp.adset_name or key
                elif group_by == "day":
                    key = tp.event_ts.date().isoformat()
                    display_name = key
                else:
                    key = tp.source or "unknown"
                    display_name = key

                if key not in groups:
                    groups[key] = {
                        "key": key,
                        "name": display_name,
                        "attributed_revenue": 0,
                        "attributed_deals": 0,
                        "touchpoint_count": 0,
                        "unique_contacts": set(),
                    }

                groups[key]["attributed_revenue"] += revenue * weight
                groups[key]["attributed_deals"] += weight
                groups[key]["touchpoint_count"] += 1
                if deal.contact_id:
                    groups[key]["unique_contacts"].add(str(deal.contact_id))

        # Convert to list and clean up
        result = []
        for group in groups.values():
            result.append(
                {
                    "key": group["key"],
                    "name": group["name"],
                    "attributed_revenue": round(group["attributed_revenue"], 2),
                    "attributed_deals": round(group["attributed_deals"], 2),
                    "touchpoint_count": group["touchpoint_count"],
                    "unique_contacts": len(group["unique_contacts"]),
                }
            )

        return sorted(result, key=lambda x: x["attributed_revenue"], reverse=True)

    async def _get_contact_touchpoints(
        self,
        contact_id: UUID,
        before_time: Optional[datetime] = None,
    ) -> list[Touchpoint]:
        """Get touchpoints for a contact, ordered by time."""
        query = select(Touchpoint).where(
            and_(
                Touchpoint.contact_id == contact_id,
                Touchpoint.tenant_id == self.tenant_id,
            )
        )

        if before_time:
            query = query.where(Touchpoint.event_ts <= before_time)

        query = query.order_by(Touchpoint.event_ts)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    def _calculate_confidence(self, touchpoints: list[Touchpoint]) -> float:
        """Calculate attribution confidence score."""
        if not touchpoints:
            return 0.0

        base_confidence = 0.5

        # Touch count bonus (up to +0.2)
        touch_bonus = min(0.2, len(touchpoints) * 0.05)

        # Match quality bonus (up to +0.3)
        quality_bonus = 0.0
        for tp in touchpoints:
            if tp.gclid or tp.fbclid or tp.ttclid or tp.sclid:
                quality_bonus = max(quality_bonus, 0.3)
            elif tp.email_hash or tp.phone_hash:
                quality_bonus = max(quality_bonus, 0.2)
            elif tp.visitor_id or tp.ga_client_id:
                quality_bonus = max(quality_bonus, 0.1)

        return min(1.0, base_confidence + touch_bonus + quality_bonus)


# =============================================================================
# Data-Driven Attribution (Markov Chain Model)
# =============================================================================


class MarkovAttributionModel:
    """
    Data-Driven Attribution using Markov Chain modeling.

    This model learns the probability of conversion based on actual
    customer journey paths, providing more accurate attribution than
    rule-based models.
    """

    def __init__(self):
        self.transition_matrix: dict[str, dict[str, float]] = {}
        self.conversion_probs: dict[str, float] = {}
        self.removal_effects: dict[str, float] = {}
        self._is_fitted = False

    def fit(self, journeys: list[list[str]], converted: list[bool]) -> "MarkovAttributionModel":
        """
        Fit the Markov chain model on customer journey data.

        Args:
            journeys: List of journeys, each journey is a list of channel names
            converted: List of booleans indicating if journey converted
        """
        # Count transitions
        transitions: dict[str, dict[str, int]] = {}

        for journey, did_convert in zip(journeys, converted, strict=False):
            # Add start and end states
            path = ["(start)"] + journey + ["(conversion)" if did_convert else "(null)"]

            for i in range(len(path) - 1):
                from_state = path[i]
                to_state = path[i + 1]

                if from_state not in transitions:
                    transitions[from_state] = {}
                transitions[from_state][to_state] = transitions[from_state].get(to_state, 0) + 1

        # Convert to probabilities
        for from_state, to_states in transitions.items():
            total = sum(to_states.values())
            self.transition_matrix[from_state] = {
                to_state: count / total for to_state, count in to_states.items()
            }

        # Calculate baseline conversion probability
        self.conversion_probs["baseline"] = self._calculate_conversion_prob()

        # Calculate removal effect for each channel
        channels = set()
        for journey in journeys:
            channels.update(journey)

        for channel in channels:
            self.removal_effects[channel] = self._calculate_removal_effect(channel)

        self._is_fitted = True
        return self

    def _calculate_conversion_prob(self, removed_channel: Optional[str] = None) -> float:
        """Calculate overall conversion probability (optionally with channel removed)."""
        if not self.transition_matrix:
            return 0.0

        # Simulate random walks to estimate conversion probability
        num_simulations = 10000
        conversions = 0

        for _ in range(num_simulations):
            state = "(start)"
            visited = set()
            max_steps = 20

            for _ in range(max_steps):
                if state == "(conversion)":
                    conversions += 1
                    break
                elif state == "(null)" or state in visited:
                    break

                visited.add(state)

                if state not in self.transition_matrix:
                    break

                # Get next state probabilities
                next_states = self.transition_matrix[state].copy()

                # Remove channel if specified
                if removed_channel and removed_channel in next_states:
                    del next_states[removed_channel]
                    # Renormalize
                    total = sum(next_states.values())
                    if total > 0:
                        next_states = {k: v / total for k, v in next_states.items()}
                    else:
                        break

                if not next_states:
                    break

                # Sample next state
                states = list(next_states.keys())
                probs = list(next_states.values())
                state = states[
                    int(
                        sum(
                            p < sum(probs[: i + 1])
                            for i, p in enumerate([hash(str(_)) % 1000 / 1000])
                        )
                    )
                ]

        return conversions / num_simulations

    def _calculate_removal_effect(self, channel: str) -> float:
        """Calculate the removal effect for a channel."""
        if not self._is_fitted and "baseline" not in self.conversion_probs:
            return 0.0

        baseline = self.conversion_probs.get("baseline", 0)
        if baseline == 0:
            return 0.0

        prob_without = self._calculate_conversion_prob(removed_channel=channel)
        removal_effect = (baseline - prob_without) / baseline

        return max(0, removal_effect)

    def get_attribution_weights(self, channels: list[str]) -> dict[str, float]:
        """
        Get attribution weights for channels based on removal effects.

        Returns weights normalized to sum to 1.0
        """
        if not self._is_fitted:
            # Equal weights if not fitted
            weight = 1.0 / len(channels) if channels else 0
            return {ch: weight for ch in channels}

        # Get removal effects for channels in this journey
        effects = {ch: self.removal_effects.get(ch, 0) for ch in channels}

        total = sum(effects.values())
        if total == 0:
            weight = 1.0 / len(channels) if channels else 0
            return {ch: weight for ch in channels}

        return {ch: effect / total for ch, effect in effects.items()}


class ShapleyAttributionModel:
    """
    Shapley Value Attribution for fair multi-channel attribution.

    Computes the marginal contribution of each channel across all
    possible orderings, providing a game-theoretic fair attribution.
    """

    def __init__(self):
        self.channel_values: dict[str, float] = {}
        self._conversion_cache: dict[frozenset, float] = {}

    def compute_shapley_values(
        self,
        channels: list[str],
        conversion_function: callable,
    ) -> dict[str, float]:
        """
        Compute Shapley values for attribution.

        Args:
            channels: List of channels in the journey
            conversion_function: Function that takes a set of channels
                               and returns conversion probability

        Returns:
            Dict of channel -> Shapley value (sums to 1.0)
        """
        n = len(channels)
        if n == 0:
            return {}

        shapley_values = {ch: 0.0 for ch in channels}

        # For each channel, compute marginal contribution
        for channel in channels:
            other_channels = [c for c in channels if c != channel]

            # Iterate over all subsets of other channels
            for subset_size in range(len(other_channels) + 1):
                for subset in self._get_subsets(other_channels, subset_size):
                    subset_set = frozenset(subset)
                    with_channel = frozenset(subset + [channel])

                    # Get conversion probabilities
                    conv_without = self._get_cached_conversion(subset_set, conversion_function)
                    conv_with = self._get_cached_conversion(with_channel, conversion_function)

                    # Marginal contribution
                    marginal = conv_with - conv_without

                    # Shapley weight
                    weight = (
                        math.factorial(subset_size)
                        * math.factorial(n - subset_size - 1)
                        / math.factorial(n)
                    )

                    shapley_values[channel] += weight * marginal

        # Normalize to sum to 1
        total = sum(shapley_values.values())
        if total > 0:
            shapley_values = {k: v / total for k, v in shapley_values.items()}

        return shapley_values

    def _get_subsets(self, items: list[str], size: int) -> list[list[str]]:
        """Generate all subsets of given size."""
        if size == 0:
            return [[]]
        if size > len(items):
            return []

        result = []
        for i, item in enumerate(items):
            for subset in self._get_subsets(items[i + 1 :], size - 1):
                result.append([item] + subset)
        return result

    def _get_cached_conversion(
        self,
        channel_set: frozenset,
        conversion_function: callable,
    ) -> float:
        """Get cached conversion probability."""
        if channel_set not in self._conversion_cache:
            self._conversion_cache[channel_set] = conversion_function(set(channel_set))
        return self._conversion_cache[channel_set]


# =============================================================================
# Cross-Platform Attribution Aggregator
# =============================================================================


class CrossPlatformAttributor:
    """
    Aggregates and reconciles attribution across multiple ad platforms.

    Handles the challenge of platforms over-claiming conversions by
    using a neutral measurement approach.
    """

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    async def get_unified_attribution(
        self,
        start_date: datetime,
        end_date: datetime,
        normalization_method: str = "linear",  # linear, shapley, or proportional
    ) -> dict[str, Any]:
        """
        Get unified attribution across all platforms.

        Args:
            start_date: Start of attribution window
            end_date: End of attribution window
            normalization_method: How to handle overlapping claims

        Returns:
            Unified attribution report with platform breakdown
        """
        # Get all platform-reported conversions
        platform_claims = await self._get_platform_claims(start_date, end_date)

        # Get actual conversions from source of truth (GA4/CRM)
        actual_conversions = await self._get_actual_conversions(start_date, end_date)

        # Calculate overlap and reconcile
        reconciled = self._reconcile_claims(
            platform_claims,
            actual_conversions,
            normalization_method,
        )

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "actual_conversions": actual_conversions["count"],
            "actual_revenue": actual_conversions["revenue"],
            "platform_claims": platform_claims,
            "reconciled_attribution": reconciled,
            "over_claim_rate": self._calculate_over_claim_rate(platform_claims, actual_conversions),
            "methodology": normalization_method,
        }

    async def _get_platform_claims(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, dict[str, float]]:
        """Get conversion claims from each platform."""
        # This would query platform-specific metrics tables
        # Returning structure for now
        return {
            "meta": {"conversions": 0, "revenue": 0, "spend": 0},
            "google": {"conversions": 0, "revenue": 0, "spend": 0},
            "tiktok": {"conversions": 0, "revenue": 0, "spend": 0},
        }

    async def _get_actual_conversions(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, float]:
        """Get actual conversions from source of truth."""
        # Query CRM deals or GA4 conversions
        result = await self.db.execute(
            select(func.count(CRMDeal.id), func.sum(CRMDeal.amount)).where(
                and_(
                    CRMDeal.tenant_id == self.tenant_id,
                    CRMDeal.is_won == True,
                    CRMDeal.won_at >= start_date,
                    CRMDeal.won_at <= end_date,
                )
            )
        )
        row = result.first()
        return {
            "count": row[0] or 0,
            "revenue": float(row[1] or 0),
        }

    def _reconcile_claims(
        self,
        platform_claims: dict[str, dict[str, float]],
        actual: dict[str, float],
        method: str,
    ) -> dict[str, dict[str, float]]:
        """Reconcile platform claims against actual conversions."""
        total_claimed = sum(p["conversions"] for p in platform_claims.values())

        if total_claimed == 0:
            return {p: {"conversions": 0, "revenue": 0, "share": 0} for p in platform_claims}

        result = {}
        for platform, claims in platform_claims.items():
            if method == "proportional":
                # Distribute actual based on claimed share
                share = claims["conversions"] / total_claimed
            elif method == "spend_weighted":
                # Weight by spend
                total_spend = sum(p["spend"] for p in platform_claims.values())
                share = claims["spend"] / total_spend if total_spend > 0 else 0
            else:  # linear
                share = 1.0 / len(platform_claims)

            result[platform] = {
                "conversions": actual["count"] * share,
                "revenue": actual["revenue"] * share,
                "share": share,
                "original_claim": claims["conversions"],
            }

        return result

    def _calculate_over_claim_rate(
        self,
        claims: dict[str, dict[str, float]],
        actual: dict[str, float],
    ) -> float:
        """Calculate how much platforms over-claim."""
        total_claimed = sum(p["conversions"] for p in claims.values())
        actual_count = actual["count"]

        if actual_count == 0:
            return 0.0

        return max(0, (total_claimed - actual_count) / actual_count * 100)
