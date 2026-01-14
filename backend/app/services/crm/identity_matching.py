# =============================================================================
# Stratum AI - Identity Matching Service
# =============================================================================
"""
Identity matching for attribution across CRM contacts and ad touchpoints.
Links ad interactions to CRM leads/deals for closed-loop measurement.

Matching priority (best to worst accuracy):
1. email_hash - Most reliable
2. phone_hash - Reliable
3. click_ids (gclid, fbclid, ttclid, sclid) - Platform-specific, very accurate
4. visitor_id / ga_client_id - Session-based
5. utm_campaign + timestamp - Fallback, least accurate
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.crm import (
    CRMContact,
    CRMDeal,
    Touchpoint,
    AttributionModel,
)

logger = get_logger(__name__)


# Attribution lookback windows (days)
DEFAULT_LOOKBACK_DAYS = 30
MAX_LOOKBACK_DAYS = 90


class IdentityMatcher:
    """
    Matches CRM contacts to ad touchpoints for attribution.

    Supports multiple identity signals with priority-based matching:
    - Direct matches (email, phone, click IDs)
    - Probabilistic matches (UTM + timing)
    """

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: int,
        lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.lookback_days = min(lookback_days, MAX_LOOKBACK_DAYS)

    async def match_contacts_to_touchpoints(self) -> Dict[str, Any]:
        """
        Match all unmatched contacts to their ad touchpoints.

        Returns:
            Summary of matching results
        """
        results = {
            "contacts_processed": 0,
            "contacts_matched": 0,
            "matches_by_signal": {
                "email": 0,
                "phone": 0,
                "gclid": 0,
                "fbclid": 0,
                "ttclid": 0,
                "sclid": 0,
                "visitor_id": 0,
                "utm_fallback": 0,
            },
        }

        # Get contacts without attribution
        contacts = await self._get_unattributed_contacts()
        results["contacts_processed"] = len(contacts)

        for contact in contacts:
            match_result = await self._match_contact(contact)
            if match_result["matched"]:
                results["contacts_matched"] += 1
                results["matches_by_signal"][match_result["signal"]] += 1

        await self.db.commit()

        logger.info(
            "identity_matching_complete",
            tenant_id=self.tenant_id,
            processed=results["contacts_processed"],
            matched=results["contacts_matched"],
        )

        return results

    async def _get_unattributed_contacts(self) -> List[CRMContact]:
        """Get contacts that haven't been matched to touchpoints."""
        result = await self.db.execute(
            select(CRMContact).where(
                and_(
                    CRMContact.tenant_id == self.tenant_id,
                    CRMContact.first_touch_campaign_id.is_(None),
                )
            ).limit(1000)  # Process in batches
        )
        return result.scalars().all()

    async def _match_contact(self, contact: CRMContact) -> Dict[str, Any]:
        """
        Find and link touchpoints for a contact.

        Uses priority-based matching:
        1. Click IDs (most accurate)
        2. Email/Phone hash
        3. Visitor ID
        4. UTM fallback

        Returns:
            Match result with signal type
        """
        touchpoints = []
        match_signal = None

        # Priority 1: Click IDs
        if contact.gclid:
            touchpoints = await self._find_touchpoints_by_click_id("gclid", contact.gclid)
            if touchpoints:
                match_signal = "gclid"

        if not touchpoints and contact.fbclid:
            touchpoints = await self._find_touchpoints_by_click_id("fbclid", contact.fbclid)
            if touchpoints:
                match_signal = "fbclid"

        if not touchpoints and contact.ttclid:
            touchpoints = await self._find_touchpoints_by_click_id("ttclid", contact.ttclid)
            if touchpoints:
                match_signal = "ttclid"

        if not touchpoints and contact.sclid:
            touchpoints = await self._find_touchpoints_by_click_id("sclid", contact.sclid)
            if touchpoints:
                match_signal = "sclid"

        # Priority 2: Email hash
        if not touchpoints and contact.email_hash:
            touchpoints = await self._find_touchpoints_by_identity(
                "email_hash",
                contact.email_hash,
                contact.crm_created_at,
            )
            if touchpoints:
                match_signal = "email"

        # Priority 3: Phone hash
        if not touchpoints and contact.phone_hash:
            touchpoints = await self._find_touchpoints_by_identity(
                "phone_hash",
                contact.phone_hash,
                contact.crm_created_at,
            )
            if touchpoints:
                match_signal = "phone"

        # Priority 4: Visitor ID
        if not touchpoints and contact.ga_client_id:
            touchpoints = await self._find_touchpoints_by_identity(
                "ga_client_id",
                contact.ga_client_id,
                contact.crm_created_at,
            )
            if touchpoints:
                match_signal = "visitor_id"

        # Priority 5: UTM fallback (least accurate)
        if not touchpoints and contact.utm_campaign:
            touchpoints = await self._find_touchpoints_by_utm(
                contact.utm_source,
                contact.utm_medium,
                contact.utm_campaign,
                contact.crm_created_at,
            )
            if touchpoints:
                match_signal = "utm_fallback"

        if not touchpoints:
            return {"matched": False, "signal": None}

        # Sort touchpoints by time
        touchpoints.sort(key=lambda t: t.event_ts)

        # Update contact with attribution
        first_touch = touchpoints[0]
        last_touch = touchpoints[-1]

        contact.first_touch_campaign_id = first_touch.campaign_id
        contact.last_touch_campaign_id = last_touch.campaign_id
        contact.first_touch_ts = first_touch.event_ts
        contact.last_touch_ts = last_touch.event_ts
        contact.touch_count = len(touchpoints)

        # Link touchpoints to contact
        for i, tp in enumerate(touchpoints):
            tp.contact_id = contact.id
            tp.touch_position = i + 1
            tp.total_touches = len(touchpoints)
            tp.is_first_touch = (i == 0)
            tp.is_last_touch = (i == len(touchpoints) - 1)

        return {"matched": True, "signal": match_signal, "touch_count": len(touchpoints)}

    async def _find_touchpoints_by_click_id(
        self,
        click_id_field: str,
        click_id_value: str,
    ) -> List[Touchpoint]:
        """Find touchpoints by platform click ID."""
        column = getattr(Touchpoint, click_id_field)
        result = await self.db.execute(
            select(Touchpoint).where(
                and_(
                    Touchpoint.tenant_id == self.tenant_id,
                    column == click_id_value,
                )
            ).order_by(Touchpoint.event_ts)
        )
        return list(result.scalars().all())

    async def _find_touchpoints_by_identity(
        self,
        identity_field: str,
        identity_value: str,
        conversion_time: Optional[datetime] = None,
    ) -> List[Touchpoint]:
        """Find touchpoints by identity hash within lookback window."""
        column = getattr(Touchpoint, identity_field)

        # Calculate lookback window
        if conversion_time:
            lookback_start = conversion_time - timedelta(days=self.lookback_days)
        else:
            lookback_start = datetime.now(timezone.utc) - timedelta(days=self.lookback_days)

        result = await self.db.execute(
            select(Touchpoint).where(
                and_(
                    Touchpoint.tenant_id == self.tenant_id,
                    column == identity_value,
                    Touchpoint.event_ts >= lookback_start,
                    Touchpoint.event_ts <= (conversion_time or datetime.now(timezone.utc)),
                )
            ).order_by(Touchpoint.event_ts)
        )
        return list(result.scalars().all())

    async def _find_touchpoints_by_utm(
        self,
        utm_source: Optional[str],
        utm_medium: Optional[str],
        utm_campaign: Optional[str],
        conversion_time: Optional[datetime] = None,
    ) -> List[Touchpoint]:
        """
        Find touchpoints by UTM parameters (fallback method).
        This is the least accurate matching method.
        """
        if not utm_campaign:
            return []

        # Calculate lookback window (shorter for UTM matching)
        utm_lookback_days = min(self.lookback_days, 7)  # Max 7 days for UTM fallback
        if conversion_time:
            lookback_start = conversion_time - timedelta(days=utm_lookback_days)
            lookback_end = conversion_time
        else:
            lookback_end = datetime.now(timezone.utc)
            lookback_start = lookback_end - timedelta(days=utm_lookback_days)

        conditions = [
            Touchpoint.tenant_id == self.tenant_id,
            Touchpoint.utm_campaign == utm_campaign,
            Touchpoint.event_ts >= lookback_start,
            Touchpoint.event_ts <= lookback_end,
        ]

        if utm_source:
            conditions.append(Touchpoint.utm_source == utm_source)
        if utm_medium:
            conditions.append(Touchpoint.utm_medium == utm_medium)

        result = await self.db.execute(
            select(Touchpoint).where(and_(*conditions)).order_by(Touchpoint.event_ts)
        )
        return list(result.scalars().all())

    async def attribute_deal(
        self,
        deal: CRMDeal,
        model: AttributionModel = AttributionModel.LAST_TOUCH,
    ) -> Dict[str, Any]:
        """
        Attribute a deal to ad campaigns based on contact touchpoints.

        Args:
            deal: The deal to attribute
            model: Attribution model to use

        Returns:
            Attribution result with campaign assignments
        """
        if not deal.contact_id:
            return {"attributed": False, "reason": "no_contact"}

        # Get contact's touchpoints
        result = await self.db.execute(
            select(Touchpoint).where(
                and_(
                    Touchpoint.contact_id == deal.contact_id,
                    Touchpoint.event_ts <= (deal.won_at or datetime.now(timezone.utc)),
                )
            ).order_by(Touchpoint.event_ts)
        )
        touchpoints = list(result.scalars().all())

        if not touchpoints:
            return {"attributed": False, "reason": "no_touchpoints"}

        # Apply attribution model
        if model == AttributionModel.LAST_TOUCH:
            attributed_tp = touchpoints[-1]
            attributed_tp.is_converting_touch = True
            attributed_tp.attribution_weight = 1.0

        elif model == AttributionModel.FIRST_TOUCH:
            attributed_tp = touchpoints[0]
            attributed_tp.is_converting_touch = True
            attributed_tp.attribution_weight = 1.0

        elif model == AttributionModel.LINEAR:
            # Equal credit to all touchpoints
            weight = 1.0 / len(touchpoints)
            for tp in touchpoints:
                tp.is_converting_touch = True
                tp.attribution_weight = weight
            attributed_tp = touchpoints[-1]  # Use last touch for primary attribution

        elif model == AttributionModel.POSITION_BASED:
            # 40% first, 40% last, 20% middle
            for i, tp in enumerate(touchpoints):
                tp.is_converting_touch = True
                if i == 0:
                    tp.attribution_weight = 0.4
                elif i == len(touchpoints) - 1:
                    tp.attribution_weight = 0.4
                else:
                    tp.attribution_weight = 0.2 / max(1, len(touchpoints) - 2)
            attributed_tp = touchpoints[-1]  # Use last touch for primary attribution

        elif model == AttributionModel.TIME_DECAY:
            # More recent touchpoints get more credit
            total_weight = sum(2 ** i for i in range(len(touchpoints)))
            for i, tp in enumerate(touchpoints):
                tp.is_converting_touch = True
                tp.attribution_weight = (2 ** i) / total_weight
            attributed_tp = touchpoints[-1]

        else:
            # Default to last touch
            attributed_tp = touchpoints[-1]
            attributed_tp.is_converting_touch = True
            attributed_tp.attribution_weight = 1.0

        # Update deal with attribution
        deal.attributed_touchpoint_id = attributed_tp.id
        deal.attributed_campaign_id = attributed_tp.campaign_id
        deal.attributed_adset_id = attributed_tp.adset_id
        deal.attributed_ad_id = attributed_tp.ad_id
        deal.attributed_platform = attributed_tp.source
        deal.attribution_model = model
        deal.attribution_confidence = self._calculate_confidence(touchpoints, model)

        await self.db.commit()

        return {
            "attributed": True,
            "model": model.value,
            "campaign_id": deal.attributed_campaign_id,
            "platform": deal.attributed_platform,
            "touchpoint_count": len(touchpoints),
            "confidence": deal.attribution_confidence,
        }

    def _calculate_confidence(
        self,
        touchpoints: List[Touchpoint],
        model: AttributionModel,
    ) -> float:
        """
        Calculate attribution confidence score (0-1).

        Factors:
        - Number of touchpoints
        - Match quality (click_id > email > utm)
        - Time between touches and conversion
        """
        if not touchpoints:
            return 0.0

        base_confidence = 0.5

        # More touchpoints = higher confidence (up to +0.2)
        touch_bonus = min(0.2, len(touchpoints) * 0.05)

        # Match quality bonus (up to +0.3)
        quality_bonus = 0.0
        for tp in touchpoints:
            if tp.gclid or tp.fbclid or tp.ttclid or tp.sclid:
                quality_bonus = max(quality_bonus, 0.3)  # Click ID = highest
            elif tp.email_hash or tp.phone_hash:
                quality_bonus = max(quality_bonus, 0.2)  # Identity hash = medium
            elif tp.visitor_id or tp.ga_client_id:
                quality_bonus = max(quality_bonus, 0.1)  # Visitor ID = low

        return min(1.0, base_confidence + touch_bonus + quality_bonus)

    async def get_attribution_report(
        self,
        start_date: datetime,
        end_date: datetime,
        group_by: str = "campaign",  # campaign, platform, source
    ) -> List[Dict[str, Any]]:
        """
        Generate attribution report for won deals.

        Args:
            start_date: Report start date
            end_date: Report end date
            group_by: Grouping dimension

        Returns:
            List of attribution metrics by group
        """
        # Get attributed won deals in date range
        result = await self.db.execute(
            select(CRMDeal).where(
                and_(
                    CRMDeal.tenant_id == self.tenant_id,
                    CRMDeal.is_won == True,
                    CRMDeal.won_at >= start_date,
                    CRMDeal.won_at <= end_date,
                    CRMDeal.attributed_campaign_id.isnot(None),
                )
            )
        )
        deals = result.scalars().all()

        # Group metrics
        groups: Dict[str, Dict[str, Any]] = {}

        for deal in deals:
            if group_by == "campaign":
                key = deal.attributed_campaign_id or "unattributed"
            elif group_by == "platform":
                key = deal.attributed_platform or "unattributed"
            else:
                key = deal.attributed_platform or "unattributed"

            if key not in groups:
                groups[key] = {
                    "group": key,
                    "deals_won": 0,
                    "revenue": 0.0,
                    "avg_deal_size": 0.0,
                    "avg_confidence": 0.0,
                }

            groups[key]["deals_won"] += 1
            groups[key]["revenue"] += deal.amount or 0
            groups[key]["avg_confidence"] += deal.attribution_confidence or 0

        # Calculate averages
        for group in groups.values():
            if group["deals_won"] > 0:
                group["avg_deal_size"] = group["revenue"] / group["deals_won"]
                group["avg_confidence"] = group["avg_confidence"] / group["deals_won"]

        return list(groups.values())


# =============================================================================
# Utility Functions
# =============================================================================

async def create_touchpoint_from_click(
    db: AsyncSession,
    tenant_id: int,
    click_data: Dict[str, Any],
) -> Touchpoint:
    """
    Create a touchpoint from ad click data.

    Args:
        db: Database session
        tenant_id: Tenant ID
        click_data: Click event data with UTMs, click IDs, etc.

    Returns:
        Created touchpoint
    """
    touchpoint = Touchpoint(
        tenant_id=tenant_id,
        event_ts=click_data.get("timestamp", datetime.now(timezone.utc)),
        event_type=click_data.get("event_type", "click"),
        source=click_data.get("source", "unknown"),
        campaign_id=click_data.get("campaign_id"),
        campaign_name=click_data.get("campaign_name"),
        adset_id=click_data.get("adset_id"),
        adset_name=click_data.get("adset_name"),
        ad_id=click_data.get("ad_id"),
        ad_name=click_data.get("ad_name"),
        utm_source=click_data.get("utm_source"),
        utm_medium=click_data.get("utm_medium"),
        utm_campaign=click_data.get("utm_campaign"),
        utm_content=click_data.get("utm_content"),
        utm_term=click_data.get("utm_term"),
        gclid=click_data.get("gclid"),
        fbclid=click_data.get("fbclid"),
        ttclid=click_data.get("ttclid"),
        sclid=click_data.get("sclid"),
        click_id=click_data.get("click_id"),
        email_hash=click_data.get("email_hash"),
        phone_hash=click_data.get("phone_hash"),
        visitor_id=click_data.get("visitor_id"),
        ga_client_id=click_data.get("ga_client_id"),
        device_type=click_data.get("device_type"),
        country=click_data.get("country"),
        landing_page_url=click_data.get("landing_page_url"),
        referrer_url=click_data.get("referrer_url"),
    )

    db.add(touchpoint)
    await db.flush()
    return touchpoint
