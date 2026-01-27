# =============================================================================
# Stratum AI - Pipedrive Writeback Service
# =============================================================================
"""
Service for writing attribution data back to Pipedrive.

Features:
- Custom field creation for Stratum attribution data
- Person attribution writeback (ad platform, campaign, ROAS)
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
    CRMProvider,
    Touchpoint,
)
from app.services.crm.pipedrive_client import PipedriveClient

logger = get_logger(__name__)


# =============================================================================
# Custom Field Definitions
# =============================================================================

# Stratum AI custom fields for persons
PERSON_CUSTOM_FIELDS = [
    {
        "name": "stratum_ad_platform",
        "field_type": "varchar",
        "description": "Primary advertising platform that acquired this person",
    },
    {
        "name": "stratum_campaign_id",
        "field_type": "varchar",
        "description": "Campaign ID from ad platform",
    },
    {
        "name": "stratum_campaign_name",
        "field_type": "varchar",
        "description": "Campaign name from ad platform",
    },
    {
        "name": "stratum_adset_id",
        "field_type": "varchar",
        "description": "Ad set/ad group ID from ad platform",
    },
    {
        "name": "stratum_ad_id",
        "field_type": "varchar",
        "description": "Individual ad ID from ad platform",
    },
    {
        "name": "stratum_first_touch_source",
        "field_type": "varchar",
        "description": "First touch attribution source",
    },
    {
        "name": "stratum_last_touch_source",
        "field_type": "varchar",
        "description": "Last touch attribution source",
    },
    {
        "name": "stratum_attribution_confidence",
        "field_type": "double",
        "description": "Attribution confidence score (0-100)",
    },
    {
        "name": "stratum_total_ad_spend",
        "field_type": "monetary",
        "description": "Total attributed ad spend for this person",
    },
    {
        "name": "stratum_touchpoints_count",
        "field_type": "int",
        "description": "Number of ad touchpoints before conversion",
    },
    {
        "name": "stratum_last_sync",
        "field_type": "date",
        "description": "Last time Stratum synced attribution data",
    },
]

# Stratum AI custom fields for deals
DEAL_CUSTOM_FIELDS = [
    {
        "name": "stratum_attributed_platform",
        "field_type": "varchar",
        "description": "Primary platform attributed for this deal",
    },
    {
        "name": "stratum_attributed_campaign",
        "field_type": "varchar",
        "description": "Campaign name attributed for this deal",
    },
    {
        "name": "stratum_attributed_campaign_id",
        "field_type": "varchar",
        "description": "Campaign ID attributed for this deal",
    },
    {
        "name": "stratum_attribution_model",
        "field_type": "varchar",
        "description": "Attribution model used (last_touch, first_touch, linear, etc.)",
    },
    {
        "name": "stratum_attributed_spend",
        "field_type": "monetary",
        "description": "Ad spend attributed to this deal",
    },
    {
        "name": "stratum_revenue_roas",
        "field_type": "double",
        "description": "Revenue ROAS for this deal (deal amount / ad spend)",
    },
    {
        "name": "stratum_profit_roas",
        "field_type": "double",
        "description": "Profit ROAS (after COGS) for this deal",
    },
    {
        "name": "stratum_cogs",
        "field_type": "monetary",
        "description": "Cost of goods sold for this deal",
    },
    {
        "name": "stratum_gross_profit",
        "field_type": "monetary",
        "description": "Gross profit (revenue - COGS)",
    },
    {
        "name": "stratum_net_profit",
        "field_type": "monetary",
        "description": "Net profit (gross profit - ad spend)",
    },
    {
        "name": "stratum_days_to_close",
        "field_type": "int",
        "description": "Days from first touch to deal close",
    },
    {
        "name": "stratum_touchpoints_count",
        "field_type": "int",
        "description": "Number of ad touchpoints in the journey",
    },
    {
        "name": "stratum_last_sync",
        "field_type": "date",
        "description": "Last time Stratum synced attribution data",
    },
]


class WritebackStatus(str, enum.Enum):
    """Writeback operation status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class PipedriveWritebackService:
    """
    Service for writing Stratum attribution data back to Pipedrive.

    Pushes:
    - Person attribution (platform, campaign, ad)
    - Deal attribution (ROAS, profit metrics)
    - Touchpoint data
    """

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.client = PipedriveClient(db, tenant_id)
        self._field_key_cache: dict[str, str] = {}

    async def setup_custom_fields(self) -> dict[str, Any]:
        """
        Create Stratum custom fields in Pipedrive.

        Should be called once during initial setup or when fields are missing.

        Returns:
            Summary of created/existing fields
        """
        results = {
            "person_fields": {"created": 0, "existing": 0, "failed": 0},
            "deal_fields": {"created": 0, "existing": 0, "failed": 0},
        }

        async with self.client:
            # Get existing fields
            existing_person_fields = await self.client.get_custom_fields("person")
            existing_deal_fields = await self.client.get_custom_fields("deal")

            # Build lookup by name
            person_field_names = {
                f.get("name", "").lower(): f for f in (existing_person_fields.get("data") or [])
            }
            deal_field_names = {
                f.get("name", "").lower(): f for f in (existing_deal_fields.get("data") or [])
            }

            # Create person custom fields
            for field_def in PERSON_CUSTOM_FIELDS:
                field_name = f"Stratum - {field_def['name'].replace('stratum_', '').replace('_', ' ').title()}"

                if field_name.lower() in person_field_names:
                    results["person_fields"]["existing"] += 1
                    # Cache the field key
                    self._field_key_cache[field_def["name"]] = person_field_names[
                        field_name.lower()
                    ].get("key")
                else:
                    response = await self.client.create_custom_field(
                        "person",
                        field_name,
                        field_def["field_type"],
                    )
                    if response and response.get("success"):
                        results["person_fields"]["created"] += 1
                        self._field_key_cache[field_def["name"]] = response.get("data", {}).get(
                            "key"
                        )
                        logger.info(f"Created person custom field: {field_name}")
                    else:
                        results["person_fields"]["failed"] += 1
                        logger.error(f"Failed to create person field: {field_name}")

            # Create deal custom fields
            for field_def in DEAL_CUSTOM_FIELDS:
                field_name = f"Stratum - {field_def['name'].replace('stratum_', '').replace('_', ' ').title()}"

                if field_name.lower() in deal_field_names:
                    results["deal_fields"]["existing"] += 1
                    # Cache the field key
                    self._field_key_cache[f"deal_{field_def['name']}"] = deal_field_names[
                        field_name.lower()
                    ].get("key")
                else:
                    response = await self.client.create_custom_field(
                        "deal",
                        field_name,
                        field_def["field_type"],
                    )
                    if response and response.get("success"):
                        results["deal_fields"]["created"] += 1
                        self._field_key_cache[f"deal_{field_def['name']}"] = response.get(
                            "data", {}
                        ).get("key")
                        logger.info(f"Created deal custom field: {field_name}")
                    else:
                        results["deal_fields"]["failed"] += 1
                        logger.error(f"Failed to create deal field: {field_name}")

        return results

    async def _ensure_field_cache(self) -> None:
        """Ensure custom field key cache is populated."""
        if self._field_key_cache:
            return

        async with self.client:
            # Get person fields
            person_fields = await self.client.get_custom_fields("person")
            for field in person_fields.get("data") or []:
                name = field.get("name", "").lower()
                if name.startswith("stratum"):
                    # Convert "Stratum - Ad Platform" to "stratum_ad_platform"
                    key_name = name.replace("stratum - ", "stratum_").replace(" ", "_")
                    self._field_key_cache[key_name] = field.get("key")

            # Get deal fields
            deal_fields = await self.client.get_custom_fields("deal")
            for field in deal_fields.get("data") or []:
                name = field.get("name", "").lower()
                if name.startswith("stratum"):
                    key_name = name.replace("stratum - ", "stratum_").replace(" ", "_")
                    self._field_key_cache[f"deal_{key_name}"] = field.get("key")

    async def sync_person_attribution(
        self,
        contact_id: Optional[UUID] = None,
        modified_since: Optional[datetime] = None,
        batch_size: int = 100,
    ) -> dict[str, Any]:
        """
        Sync person attribution data to Pipedrive.

        Args:
            contact_id: Optional specific contact to sync
            modified_since: Sync contacts modified after this time
            batch_size: Number of contacts per batch

        Returns:
            Sync results
        """
        await self._ensure_field_cache()

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
                "message": "No persons to sync",
                "synced": 0,
                "failed": 0,
            }

        synced = 0
        failed = 0
        errors = []

        async with self.client:
            for contact in contacts:
                try:
                    # Get attribution data
                    attribution = await self._get_contact_attribution(contact.id)

                    if not attribution:
                        continue

                    # Build properties dict with field keys
                    properties = {}
                    field_mappings = {
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

                    for field_name, value in field_mappings.items():
                        if value is not None and field_name in self._field_key_cache:
                            properties[self._field_key_cache[field_name]] = value

                    if not properties:
                        continue

                    # Update person in Pipedrive
                    response = await self.client.update_person(
                        contact.provider_contact_id,
                        properties,
                    )

                    if response and response.get("success"):
                        synced += 1
                        contact.last_synced_at = datetime.now(UTC)
                    else:
                        failed += 1
                        errors.append(
                            {
                                "contact_id": str(contact.id),
                                "error": response.get("error") if response else "Unknown error",
                            }
                        )

                except Exception as e:
                    failed += 1
                    errors.append(
                        {
                            "contact_id": str(contact.id),
                            "error": str(e),
                        }
                    )
                    logger.warning(
                        "pipedrive_person_writeback_error",
                        contact_id=str(contact.id),
                        error=str(e),
                    )

        await self.db.commit()

        logger.info(
            "pipedrive_person_writeback_complete",
            tenant_id=self.tenant_id,
            synced=synced,
            failed=failed,
        )

        return {
            "status": "completed" if failed == 0 else "partial",
            "synced": synced,
            "failed": failed,
            "errors": errors[:10],  # Limit errors returned
        }

    async def sync_deal_attribution(
        self,
        deal_id: Optional[UUID] = None,
        modified_since: Optional[datetime] = None,
        batch_size: int = 100,
    ) -> dict[str, Any]:
        """
        Sync deal attribution data to Pipedrive.

        Args:
            deal_id: Optional specific deal to sync
            modified_since: Sync deals modified after this time
            batch_size: Number of deals per batch

        Returns:
            Sync results
        """
        await self._ensure_field_cache()

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

        synced = 0
        failed = 0
        errors = []

        async with self.client:
            for deal in deals:
                try:
                    # Get attribution data
                    attribution = await self._get_deal_attribution(deal.id)

                    # Build properties dict with field keys
                    properties = {}
                    field_mappings = {
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

                    for field_name, value in field_mappings.items():
                        cache_key = f"deal_{field_name}"
                        if value is not None and cache_key in self._field_key_cache:
                            properties[self._field_key_cache[cache_key]] = value

                    if not properties:
                        continue

                    # Update deal in Pipedrive
                    response = await self.client.update_deal(
                        deal.provider_deal_id,
                        properties,
                    )

                    if response and response.get("success"):
                        synced += 1
                        deal.last_synced_at = datetime.now(UTC)
                    else:
                        failed += 1
                        errors.append(
                            {
                                "deal_id": str(deal.id),
                                "error": response.get("error") if response else "Unknown error",
                            }
                        )

                except Exception as e:
                    failed += 1
                    errors.append(
                        {
                            "deal_id": str(deal.id),
                            "error": str(e),
                        }
                    )
                    logger.warning(
                        "pipedrive_deal_writeback_error",
                        deal_id=str(deal.id),
                        error=str(e),
                    )

        await self.db.commit()

        logger.info(
            "pipedrive_deal_writeback_complete",
            tenant_id=self.tenant_id,
            synced=synced,
            failed=failed,
        )

        return {
            "status": "completed" if failed == 0 else "partial",
            "synced": synced,
            "failed": failed,
            "errors": errors[:10],
        }

    async def full_sync(
        self,
        sync_persons: bool = True,
        sync_deals: bool = True,
        modified_since: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """
        Run full writeback sync for all persons and deals.

        Args:
            sync_persons: Whether to sync persons
            sync_deals: Whether to sync deals
            modified_since: Only sync records modified after this time

        Returns:
            Combined sync results
        """
        results = {
            "status": "completed",
            "started_at": datetime.now(UTC).isoformat(),
            "persons": None,
            "deals": None,
        }

        if sync_persons:
            results["persons"] = await self.sync_person_attribution(modified_since=modified_since)
            if results["persons"]["status"] == "failed":
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
                    CRMConnection.provider == CRMProvider.PIPEDRIVE,
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
                CRMConnection.provider == CRMProvider.PIPEDRIVE,
            )
        )
        connection = result.scalar_one_or_none()

        if not connection or connection.status != CRMConnectionStatus.CONNECTED:
            return {
                "enabled": False,
                "connected": False,
                "message": "Pipedrive not connected",
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
            "provider": "pipedrive",
            "provider_account_id": connection.provider_account_id,
            "provider_account_name": connection.provider_account_name,
            "last_sync_at": connection.last_sync_at.isoformat()
            if connection.last_sync_at
            else None,
            "last_sync_status": connection.last_sync_status,
            "persons_count": contacts_count.scalar(),
            "deals_count": deals_count.scalar(),
            "custom_fields": {
                "person_fields": len(PERSON_CUSTOM_FIELDS),
                "deal_fields": len(DEAL_CUSTOM_FIELDS),
            },
        }
