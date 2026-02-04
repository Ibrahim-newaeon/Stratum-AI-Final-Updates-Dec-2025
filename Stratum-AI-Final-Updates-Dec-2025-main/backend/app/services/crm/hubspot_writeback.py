# =============================================================================
# Stratum AI - HubSpot Writeback Service
# =============================================================================
"""
Service for writing attribution data back to HubSpot.

Features:
- Custom property creation for Stratum attribution data
- Contact attribution writeback (ad platform, campaign, ROAS)
- Deal attribution writeback (revenue attribution, profit ROAS)
- Batch sync operations
- Writeback history tracking
"""

import enum
from datetime import UTC, datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.crm import (
    CRMConnection,
    CRMConnectionStatus,
    CRMContact,
    CRMDeal,
    Touchpoint,
)
from app.services.crm.hubspot_client import HubSpotClient

logger = get_logger(__name__)


# =============================================================================
# Custom Property Definitions
# =============================================================================

# Stratum AI custom properties for contacts
CONTACT_PROPERTIES = [
    {
        "name": "stratum_ad_platform",
        "label": "Stratum - Ad Platform",
        "type": "string",
        "field_type": "text",
        "description": "Primary advertising platform that acquired this contact",
    },
    {
        "name": "stratum_campaign_id",
        "label": "Stratum - Campaign ID",
        "type": "string",
        "field_type": "text",
        "description": "Campaign ID from ad platform",
    },
    {
        "name": "stratum_campaign_name",
        "label": "Stratum - Campaign Name",
        "type": "string",
        "field_type": "text",
        "description": "Campaign name from ad platform",
    },
    {
        "name": "stratum_adset_id",
        "label": "Stratum - Ad Set ID",
        "type": "string",
        "field_type": "text",
        "description": "Ad set/ad group ID from ad platform",
    },
    {
        "name": "stratum_ad_id",
        "label": "Stratum - Ad ID",
        "type": "string",
        "field_type": "text",
        "description": "Individual ad ID from ad platform",
    },
    {
        "name": "stratum_first_touch_source",
        "label": "Stratum - First Touch Source",
        "type": "string",
        "field_type": "text",
        "description": "First touch attribution source",
    },
    {
        "name": "stratum_last_touch_source",
        "label": "Stratum - Last Touch Source",
        "type": "string",
        "field_type": "text",
        "description": "Last touch attribution source",
    },
    {
        "name": "stratum_attribution_confidence",
        "label": "Stratum - Attribution Confidence",
        "type": "number",
        "field_type": "number",
        "description": "Attribution confidence score (0-100)",
    },
    {
        "name": "stratum_total_ad_spend",
        "label": "Stratum - Total Ad Spend",
        "type": "number",
        "field_type": "number",
        "description": "Total attributed ad spend for this contact",
    },
    {
        "name": "stratum_touchpoints_count",
        "label": "Stratum - Touchpoints Count",
        "type": "number",
        "field_type": "number",
        "description": "Number of ad touchpoints before conversion",
    },
    {
        "name": "stratum_last_sync",
        "label": "Stratum - Last Sync",
        "type": "datetime",
        "field_type": "date",
        "description": "Last time Stratum synced attribution data",
    },
]

# Stratum AI custom properties for deals
DEAL_PROPERTIES = [
    {
        "name": "stratum_attributed_platform",
        "label": "Stratum - Attributed Platform",
        "type": "string",
        "field_type": "text",
        "description": "Primary platform attributed for this deal",
    },
    {
        "name": "stratum_attributed_campaign",
        "label": "Stratum - Attributed Campaign",
        "type": "string",
        "field_type": "text",
        "description": "Campaign name attributed for this deal",
    },
    {
        "name": "stratum_attributed_campaign_id",
        "label": "Stratum - Attributed Campaign ID",
        "type": "string",
        "field_type": "text",
        "description": "Campaign ID attributed for this deal",
    },
    {
        "name": "stratum_attribution_model",
        "label": "Stratum - Attribution Model",
        "type": "string",
        "field_type": "text",
        "description": "Attribution model used (last_touch, first_touch, linear, etc.)",
    },
    {
        "name": "stratum_attributed_spend",
        "label": "Stratum - Attributed Ad Spend",
        "type": "number",
        "field_type": "number",
        "description": "Ad spend attributed to this deal",
    },
    {
        "name": "stratum_revenue_roas",
        "label": "Stratum - Revenue ROAS",
        "type": "number",
        "field_type": "number",
        "description": "Revenue ROAS for this deal (deal amount / ad spend)",
    },
    {
        "name": "stratum_profit_roas",
        "label": "Stratum - Profit ROAS",
        "type": "number",
        "field_type": "number",
        "description": "Profit ROAS (after COGS) for this deal",
    },
    {
        "name": "stratum_cogs",
        "label": "Stratum - COGS",
        "type": "number",
        "field_type": "number",
        "description": "Cost of goods sold for this deal",
    },
    {
        "name": "stratum_gross_profit",
        "label": "Stratum - Gross Profit",
        "type": "number",
        "field_type": "number",
        "description": "Gross profit (revenue - COGS)",
    },
    {
        "name": "stratum_net_profit",
        "label": "Stratum - Net Profit",
        "type": "number",
        "field_type": "number",
        "description": "Net profit (gross profit - ad spend)",
    },
    {
        "name": "stratum_days_to_close",
        "label": "Stratum - Days to Close",
        "type": "number",
        "field_type": "number",
        "description": "Days from first touch to deal close",
    },
    {
        "name": "stratum_touchpoints_count",
        "label": "Stratum - Touchpoints Count",
        "type": "number",
        "field_type": "number",
        "description": "Number of ad touchpoints in the journey",
    },
    {
        "name": "stratum_last_sync",
        "label": "Stratum - Last Sync",
        "type": "datetime",
        "field_type": "date",
        "description": "Last time Stratum synced attribution data",
    },
]

PROPERTY_GROUP = {
    "name": "stratumroas",
    "label": "Stratum ROAS Attribution",
}


class WritebackStatus(str, enum.Enum):
    """Writeback operation status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class HubSpotWritebackService:
    """
    Service for writing Stratum attribution data back to HubSpot.

    Pushes:
    - Contact attribution (platform, campaign, ad)
    - Deal attribution (ROAS, profit metrics)
    - Touchpoint data
    """

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    async def setup_custom_properties(self) -> dict[str, Any]:
        """
        Create Stratum custom properties in HubSpot.

        Should be called once during initial setup or when properties are missing.

        Returns:
            Summary of created/existing properties
        """
        async with HubSpotClient(self.db, self.tenant_id) as client:
            results = {
                "property_group": None,
                "contact_properties": {"created": 0, "existing": 0, "failed": 0},
                "deal_properties": {"created": 0, "existing": 0, "failed": 0},
            }

            # Create property group for contacts
            group_response = await client.create_property_group(
                "contacts",
                PROPERTY_GROUP["name"],
                PROPERTY_GROUP["label"],
            )
            if group_response:
                results["property_group"] = "created"
                logger.info("Created contact property group: stratumroas")
            else:
                results["property_group"] = "existing_or_failed"

            # Create property group for deals
            await client.create_property_group(
                "deals",
                PROPERTY_GROUP["name"],
                PROPERTY_GROUP["label"],
            )

            # Create contact properties
            for prop in CONTACT_PROPERTIES:
                exists = await client.property_exists("contacts", prop["name"])
                if exists:
                    results["contact_properties"]["existing"] += 1
                else:
                    response = await client.create_contact_property(
                        name=prop["name"],
                        label=prop["label"],
                        property_type=prop["type"],
                        field_type=prop["field_type"],
                        group_name=PROPERTY_GROUP["name"],
                        description=prop["description"],
                    )
                    if response:
                        results["contact_properties"]["created"] += 1
                        logger.info(f"Created contact property: {prop['name']}")
                    else:
                        results["contact_properties"]["failed"] += 1
                        logger.error(f"Failed to create contact property: {prop['name']}")

            # Create deal properties
            for prop in DEAL_PROPERTIES:
                exists = await client.property_exists("deals", prop["name"])
                if exists:
                    results["deal_properties"]["existing"] += 1
                else:
                    response = await client.create_deal_property(
                        name=prop["name"],
                        label=prop["label"],
                        property_type=prop["type"],
                        field_type=prop["field_type"],
                        group_name=PROPERTY_GROUP["name"],
                        description=prop["description"],
                    )
                    if response:
                        results["deal_properties"]["created"] += 1
                        logger.info(f"Created deal property: {prop['name']}")
                    else:
                        results["deal_properties"]["failed"] += 1
                        logger.error(f"Failed to create deal property: {prop['name']}")

            return results

    async def sync_contact_attribution(
        self,
        contact_id: Optional[UUID] = None,
        modified_since: Optional[datetime] = None,
        batch_size: int = 100,
    ) -> dict[str, Any]:
        """
        Sync contact attribution data to HubSpot.

        Args:
            contact_id: Optional specific contact to sync
            modified_since: Sync contacts modified after this time
            batch_size: Number of contacts per batch

        Returns:
            Sync results
        """
        # Build query for contacts to sync
        conditions = [
            CRMContact.tenant_id == self.tenant_id,
            CRMContact.provider_contact_id.isnot(None),
        ]

        if contact_id:
            conditions.append(CRMContact.id == contact_id)

        if modified_since:
            conditions.append(CRMContact.updated_at >= modified_since)

        result = await self.db.execute(
            select(CRMContact).where(and_(*conditions)).limit(batch_size * 10)
        )
        contacts = result.scalars().all()

        if not contacts:
            return {
                "status": "success",
                "message": "No contacts to sync",
                "synced": 0,
                "failed": 0,
            }

        # Build update payloads
        updates = []
        for contact in contacts:
            # Get attribution data
            attribution = await self._get_contact_attribution(contact.id)

            if attribution:
                properties = {
                    "stratum_ad_platform": attribution.get("platform"),
                    "stratum_campaign_id": attribution.get("campaign_id"),
                    "stratum_campaign_name": attribution.get("campaign_name"),
                    "stratum_adset_id": attribution.get("adset_id"),
                    "stratum_ad_id": attribution.get("ad_id"),
                    "stratum_first_touch_source": attribution.get("first_touch_source"),
                    "stratum_last_touch_source": attribution.get("last_touch_source"),
                    "stratum_attribution_confidence": attribution.get("confidence"),
                    "stratum_total_ad_spend": attribution.get("total_spend"),
                    "stratum_touchpoints_count": attribution.get("touchpoints_count"),
                    "stratum_last_sync": datetime.now(UTC).strftime("%Y-%m-%d"),
                }

                # Remove None values
                properties = {k: v for k, v in properties.items() if v is not None}

                updates.append(
                    {
                        "id": contact.provider_contact_id,
                        "properties": properties,
                    }
                )

        if not updates:
            return {
                "status": "success",
                "message": "No attribution data to sync",
                "synced": 0,
                "failed": 0,
            }

        # Batch update in HubSpot
        async with HubSpotClient(self.db, self.tenant_id) as client:
            response = await client.batch_update_contacts(updates)

        synced = len(response.get("results", [])) if response else 0
        failed = len(response.get("errors", [])) if response else len(updates)

        # Update local sync timestamps
        for contact in contacts:
            contact.last_synced_at = datetime.now(UTC)
        await self.db.commit()

        logger.info(
            "hubspot_contact_writeback_complete",
            tenant_id=self.tenant_id,
            synced=synced,
            failed=failed,
        )

        return {
            "status": "completed" if failed == 0 else "partial",
            "synced": synced,
            "failed": failed,
            "errors": response.get("errors", []) if response else [],
        }

    async def sync_deal_attribution(
        self,
        deal_id: Optional[UUID] = None,
        modified_since: Optional[datetime] = None,
        batch_size: int = 100,
    ) -> dict[str, Any]:
        """
        Sync deal attribution data to HubSpot.

        Args:
            deal_id: Optional specific deal to sync
            modified_since: Sync deals modified after this time
            batch_size: Number of deals per batch

        Returns:
            Sync results
        """
        # Build query for deals to sync
        conditions = [
            CRMDeal.tenant_id == self.tenant_id,
            CRMDeal.provider_deal_id.isnot(None),
        ]

        if deal_id:
            conditions.append(CRMDeal.id == deal_id)

        if modified_since:
            conditions.append(CRMDeal.updated_at >= modified_since)

        result = await self.db.execute(
            select(CRMDeal).where(and_(*conditions)).limit(batch_size * 10)
        )
        deals = result.scalars().all()

        if not deals:
            return {
                "status": "success",
                "message": "No deals to sync",
                "synced": 0,
                "failed": 0,
            }

        # Build update payloads
        updates = []
        for deal in deals:
            # Get attribution data
            attribution = await self._get_deal_attribution(deal.id)

            properties = {
                "stratum_attributed_platform": attribution.get("platform"),
                "stratum_attributed_campaign": attribution.get("campaign_name"),
                "stratum_attributed_campaign_id": attribution.get("campaign_id"),
                "stratum_attribution_model": attribution.get("attribution_model"),
                "stratum_attributed_spend": attribution.get("attributed_spend"),
                "stratum_revenue_roas": attribution.get("revenue_roas"),
                "stratum_profit_roas": attribution.get("profit_roas"),
                "stratum_cogs": attribution.get("cogs"),
                "stratum_gross_profit": attribution.get("gross_profit"),
                "stratum_net_profit": attribution.get("net_profit"),
                "stratum_days_to_close": attribution.get("days_to_close"),
                "stratum_touchpoints_count": attribution.get("touchpoints_count"),
                "stratum_last_sync": datetime.now(UTC).strftime("%Y-%m-%d"),
            }

            # Remove None values
            properties = {k: v for k, v in properties.items() if v is not None}

            updates.append(
                {
                    "id": deal.provider_deal_id,
                    "properties": properties,
                }
            )

        if not updates:
            return {
                "status": "success",
                "message": "No attribution data to sync",
                "synced": 0,
                "failed": 0,
            }

        # Batch update in HubSpot
        async with HubSpotClient(self.db, self.tenant_id) as client:
            response = await client.batch_update_deals(updates)

        synced = len(response.get("results", [])) if response else 0
        failed = len(response.get("errors", [])) if response else len(updates)

        # Update local sync timestamps
        for deal in deals:
            deal.last_synced_at = datetime.now(UTC)
        await self.db.commit()

        logger.info(
            "hubspot_deal_writeback_complete",
            tenant_id=self.tenant_id,
            synced=synced,
            failed=failed,
        )

        return {
            "status": "completed" if failed == 0 else "partial",
            "synced": synced,
            "failed": failed,
            "errors": response.get("errors", []) if response else [],
        }

    async def full_sync(
        self,
        sync_contacts: bool = True,
        sync_deals: bool = True,
        modified_since: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """
        Run full writeback sync for all contacts and deals.

        Args:
            sync_contacts: Whether to sync contacts
            sync_deals: Whether to sync deals
            modified_since: Only sync records modified after this time

        Returns:
            Combined sync results
        """
        results = {
            "status": "completed",
            "started_at": datetime.now(UTC).isoformat(),
            "contacts": None,
            "deals": None,
        }

        if sync_contacts:
            results["contacts"] = await self.sync_contact_attribution(modified_since=modified_since)
            if results["contacts"]["status"] == "failed":
                results["status"] = "partial"

        if sync_deals:
            results["deals"] = await self.sync_deal_attribution(modified_since=modified_since)
            if results["deals"]["status"] == "failed":
                results["status"] = "partial"

        results["completed_at"] = datetime.now(UTC).isoformat()

        # Update connection last sync time
        conn_result = await self.db.execute(
            select(CRMConnection).where(
                and_(
                    CRMConnection.tenant_id == self.tenant_id,
                    CRMConnection.status == CRMConnectionStatus.CONNECTED,
                )
            )
        )
        connection = conn_result.scalar_one_or_none()
        if connection:
            connection.last_sync_at = datetime.now(UTC)
            connection.last_sync_status = results["status"]
            await self.db.commit()

        return results

    async def _get_contact_attribution(self, contact_id: UUID) -> dict[str, Any]:
        """Get attribution data for a contact from touchpoints."""
        # Get touchpoints for this contact
        result = await self.db.execute(
            select(Touchpoint)
            .where(Touchpoint.contact_id == contact_id)
            .order_by(Touchpoint.touchpoint_time)
        )
        touchpoints = result.scalars().all()

        if not touchpoints:
            return {}

        # Get first and last touch
        first_touch = touchpoints[0]
        last_touch = touchpoints[-1]

        # Calculate total spend
        total_spend = sum((tp.attributed_spend_cents or 0) / 100 for tp in touchpoints)

        return {
            "platform": last_touch.platform,
            "campaign_id": last_touch.campaign_id,
            "campaign_name": last_touch.campaign_name,
            "adset_id": last_touch.adset_id,
            "ad_id": last_touch.ad_id,
            "first_touch_source": f"{first_touch.platform}:{first_touch.campaign_name}"
            if first_touch.campaign_name
            else first_touch.platform,
            "last_touch_source": f"{last_touch.platform}:{last_touch.campaign_name}"
            if last_touch.campaign_name
            else last_touch.platform,
            "confidence": max((tp.match_confidence or 0) * 100 for tp in touchpoints),
            "total_spend": round(total_spend, 2) if total_spend > 0 else None,
            "touchpoints_count": len(touchpoints),
        }

    async def _get_deal_attribution(self, deal_id: UUID) -> dict[str, Any]:
        """Get attribution data for a deal."""
        # Get deal
        result = await self.db.execute(select(CRMDeal).where(CRMDeal.id == deal_id))
        deal = result.scalar_one_or_none()

        if not deal:
            return {}

        # Get associated contact touchpoints
        touchpoints = []
        if deal.primary_contact_id:
            tp_result = await self.db.execute(
                select(Touchpoint)
                .where(Touchpoint.contact_id == deal.primary_contact_id)
                .order_by(Touchpoint.touchpoint_time)
            )
            touchpoints = tp_result.scalars().all()

        # Calculate metrics
        total_spend = sum((tp.attributed_spend_cents or 0) / 100 for tp in touchpoints)

        deal_amount = (deal.amount_cents or 0) / 100

        # Revenue ROAS
        revenue_roas = deal_amount / total_spend if total_spend > 0 else None

        # Profit metrics (if available)
        gross_profit = None
        profit_roas = None
        net_profit = None
        cogs = None

        if deal.amount_cents and deal.probability and deal.probability >= 0.5:
            # Estimate COGS at 70% for now (would come from profit service)
            cogs = deal_amount * 0.7
            gross_profit = deal_amount - cogs
            net_profit = gross_profit - total_spend
            profit_roas = gross_profit / total_spend if total_spend > 0 else None

        # Days to close
        days_to_close = None
        if touchpoints and deal.closed_at:
            first_touch_date = touchpoints[0].touchpoint_time.date()
            days_to_close = (deal.closed_at.date() - first_touch_date).days

        # Get primary attribution (last touch by default)
        primary_tp = touchpoints[-1] if touchpoints else None

        return {
            "platform": primary_tp.platform if primary_tp else None,
            "campaign_id": primary_tp.campaign_id if primary_tp else None,
            "campaign_name": primary_tp.campaign_name if primary_tp else None,
            "attribution_model": deal.attribution_model.value
            if deal.attribution_model
            else "last_touch",
            "attributed_spend": round(total_spend, 2) if total_spend > 0 else None,
            "revenue_roas": round(revenue_roas, 2) if revenue_roas else None,
            "profit_roas": round(profit_roas, 2) if profit_roas else None,
            "cogs": round(cogs, 2) if cogs else None,
            "gross_profit": round(gross_profit, 2) if gross_profit else None,
            "net_profit": round(net_profit, 2) if net_profit else None,
            "days_to_close": days_to_close,
            "touchpoints_count": len(touchpoints),
        }

    async def get_writeback_status(self) -> dict[str, Any]:
        """Get current writeback configuration and status."""
        # Get connection
        result = await self.db.execute(
            select(CRMConnection).where(
                CRMConnection.tenant_id == self.tenant_id,
            )
        )
        connection = result.scalar_one_or_none()

        if not connection or connection.status != CRMConnectionStatus.CONNECTED:
            return {
                "enabled": False,
                "connected": False,
                "message": "HubSpot not connected",
            }

        # Count records to sync
        contacts_count = await self.db.execute(
            select(func.count())
            .select_from(CRMContact)
            .where(CRMContact.tenant_id == self.tenant_id)
        )
        deals_count = await self.db.execute(
            select(func.count()).select_from(CRMDeal).where(CRMDeal.tenant_id == self.tenant_id)
        )

        return {
            "enabled": True,
            "connected": True,
            "provider_account_id": connection.provider_account_id,
            "provider_account_name": connection.provider_account_name,
            "last_sync_at": connection.last_sync_at.isoformat()
            if connection.last_sync_at
            else None,
            "last_sync_status": connection.last_sync_status,
            "contacts_count": contacts_count.scalar(),
            "deals_count": deals_count.scalar(),
            "properties": {
                "contact_properties": len(CONTACT_PROPERTIES),
                "deal_properties": len(DEAL_PROPERTIES),
            },
        }
