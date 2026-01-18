# =============================================================================
# Stratum AI - Zoho CRM Writeback Service
# =============================================================================
"""
Service for writing attribution data back to Zoho CRM.

Features:
- Custom field creation for Stratum attribution data
- Contact attribution writeback (ad platform, campaign, ROAS)
- Deal attribution writeback (revenue attribution, profit ROAS)
- Batch sync operations
- Writeback history tracking

Note: Custom field creation via API requires Zoho CRM Enterprise edition.
For other editions, fields must be created manually in Zoho CRM settings.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
import enum

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.crm import (
    CRMConnection,
    CRMContact,
    CRMDeal,
    CRMProvider,
    Touchpoint,
    CRMConnectionStatus,
)
from app.services.crm.zoho_client import ZohoClient

logger = get_logger(__name__)


# =============================================================================
# Custom Field Definitions for Zoho
# =============================================================================

# Stratum AI custom fields for contacts
# Note: Zoho field names use underscores and are case-sensitive
CONTACT_FIELDS = [
    {
        "field_label": "Stratum Ad Platform",
        "api_name": "Stratum_Ad_Platform",
        "data_type": "text",
        "length": 100,
        "description": "Primary advertising platform that acquired this contact",
    },
    {
        "field_label": "Stratum Campaign ID",
        "api_name": "Stratum_Campaign_ID",
        "data_type": "text",
        "length": 255,
        "description": "Campaign ID from ad platform",
    },
    {
        "field_label": "Stratum Campaign Name",
        "api_name": "Stratum_Campaign_Name",
        "data_type": "text",
        "length": 255,
        "description": "Campaign name from ad platform",
    },
    {
        "field_label": "Stratum Ad Set ID",
        "api_name": "Stratum_Adset_ID",
        "data_type": "text",
        "length": 255,
        "description": "Ad set/ad group ID from ad platform",
    },
    {
        "field_label": "Stratum Ad ID",
        "api_name": "Stratum_Ad_ID",
        "data_type": "text",
        "length": 255,
        "description": "Individual ad ID from ad platform",
    },
    {
        "field_label": "Stratum First Touch Source",
        "api_name": "Stratum_First_Touch_Source",
        "data_type": "text",
        "length": 255,
        "description": "First touch attribution source",
    },
    {
        "field_label": "Stratum Last Touch Source",
        "api_name": "Stratum_Last_Touch_Source",
        "data_type": "text",
        "length": 255,
        "description": "Last touch attribution source",
    },
    {
        "field_label": "Stratum Attribution Confidence",
        "api_name": "Stratum_Attribution_Confidence",
        "data_type": "double",
        "description": "Attribution confidence score (0-100)",
    },
    {
        "field_label": "Stratum Total Ad Spend",
        "api_name": "Stratum_Total_Ad_Spend",
        "data_type": "currency",
        "description": "Total attributed ad spend for this contact",
    },
    {
        "field_label": "Stratum Touchpoints Count",
        "api_name": "Stratum_Touchpoints_Count",
        "data_type": "integer",
        "description": "Number of ad touchpoints before conversion",
    },
    {
        "field_label": "Stratum Last Sync",
        "api_name": "Stratum_Last_Sync",
        "data_type": "datetime",
        "description": "Last time Stratum synced attribution data",
    },
]

# Stratum AI custom fields for deals
DEAL_FIELDS = [
    {
        "field_label": "Stratum Attributed Platform",
        "api_name": "Stratum_Attributed_Platform",
        "data_type": "text",
        "length": 100,
        "description": "Primary platform attributed for this deal",
    },
    {
        "field_label": "Stratum Attributed Campaign",
        "api_name": "Stratum_Attributed_Campaign",
        "data_type": "text",
        "length": 255,
        "description": "Campaign name attributed for this deal",
    },
    {
        "field_label": "Stratum Attributed Campaign ID",
        "api_name": "Stratum_Attributed_Campaign_ID",
        "data_type": "text",
        "length": 255,
        "description": "Campaign ID attributed for this deal",
    },
    {
        "field_label": "Stratum Attribution Model",
        "api_name": "Stratum_Attribution_Model",
        "data_type": "text",
        "length": 50,
        "description": "Attribution model used (last_touch, first_touch, linear, etc.)",
    },
    {
        "field_label": "Stratum Attributed Spend",
        "api_name": "Stratum_Attributed_Spend",
        "data_type": "currency",
        "description": "Ad spend attributed to this deal",
    },
    {
        "field_label": "Stratum Revenue ROAS",
        "api_name": "Stratum_Revenue_ROAS",
        "data_type": "double",
        "description": "Revenue ROAS for this deal (deal amount / ad spend)",
    },
    {
        "field_label": "Stratum Profit ROAS",
        "api_name": "Stratum_Profit_ROAS",
        "data_type": "double",
        "description": "Profit ROAS (after COGS) for this deal",
    },
    {
        "field_label": "Stratum COGS",
        "api_name": "Stratum_COGS",
        "data_type": "currency",
        "description": "Cost of goods sold for this deal",
    },
    {
        "field_label": "Stratum Gross Profit",
        "api_name": "Stratum_Gross_Profit",
        "data_type": "currency",
        "description": "Gross profit (revenue - COGS)",
    },
    {
        "field_label": "Stratum Net Profit",
        "api_name": "Stratum_Net_Profit",
        "data_type": "currency",
        "description": "Net profit (gross profit - ad spend)",
    },
    {
        "field_label": "Stratum Days to Close",
        "api_name": "Stratum_Days_to_Close",
        "data_type": "integer",
        "description": "Days from first touch to deal close",
    },
    {
        "field_label": "Stratum Touchpoints Count",
        "api_name": "Stratum_Touchpoints_Count",
        "data_type": "integer",
        "description": "Number of ad touchpoints in the journey",
    },
    {
        "field_label": "Stratum Last Sync",
        "api_name": "Stratum_Last_Sync",
        "data_type": "datetime",
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


class ZohoWritebackService:
    """
    Service for writing Stratum attribution data back to Zoho CRM.

    Pushes:
    - Contact attribution (platform, campaign, ad)
    - Deal attribution (ROAS, profit metrics)
    - Touchpoint data
    """

    def __init__(self, db: AsyncSession, tenant_id: int, region: str = "com"):
        """
        Initialize Zoho writeback service.

        Args:
            db: Database session
            tenant_id: Tenant ID
            region: Zoho region (com, eu, in, com.au, jp, com.cn)
        """
        self.db = db
        self.tenant_id = tenant_id
        self.region = region

    async def get_required_fields_info(self) -> Dict[str, Any]:
        """
        Get information about required custom fields.

        Returns instructions for manual field creation if API creation is not available.
        """
        return {
            "message": "Custom fields must be created in Zoho CRM. Enterprise edition supports API creation.",
            "contact_fields": [
                {
                    "label": f["field_label"],
                    "api_name": f["api_name"],
                    "type": f["data_type"],
                }
                for f in CONTACT_FIELDS
            ],
            "deal_fields": [
                {
                    "label": f["field_label"],
                    "api_name": f["api_name"],
                    "type": f["data_type"],
                }
                for f in DEAL_FIELDS
            ],
            "setup_instructions": [
                "1. Go to Zoho CRM Settings > Customization > Modules and Fields",
                "2. Select Contacts module and add each contact field listed above",
                "3. Select Deals module and add each deal field listed above",
                "4. Use the exact API names provided to ensure proper data sync",
            ],
        }

    async def setup_custom_fields(self) -> Dict[str, Any]:
        """
        Attempt to create Stratum custom fields in Zoho CRM.

        Note: This requires Zoho CRM Enterprise edition.
        For other editions, fields must be created manually.

        Returns:
            Summary of created/existing fields
        """
        async with ZohoClient(self.db, self.tenant_id, self.region) as client:
            results = {
                "contact_fields": {"created": 0, "failed": 0, "errors": []},
                "deal_fields": {"created": 0, "failed": 0, "errors": []},
            }

            # Try to create contact fields
            for field in CONTACT_FIELDS:
                try:
                    response = await client.create_custom_field(
                        module="Contacts",
                        field_label=field["field_label"],
                        field_type=field["data_type"],
                        length=field.get("length", 255),
                    )
                    if response and "fields" in response:
                        results["contact_fields"]["created"] += 1
                        logger.info(f"Created Zoho contact field: {field['field_label']}")
                    else:
                        results["contact_fields"]["failed"] += 1
                        results["contact_fields"]["errors"].append(
                            f"Failed to create {field['field_label']}: API returned no data"
                        )
                except Exception as e:
                    results["contact_fields"]["failed"] += 1
                    results["contact_fields"]["errors"].append(
                        f"Failed to create {field['field_label']}: {str(e)}"
                    )

            # Try to create deal fields
            for field in DEAL_FIELDS:
                try:
                    response = await client.create_custom_field(
                        module="Deals",
                        field_label=field["field_label"],
                        field_type=field["data_type"],
                        length=field.get("length", 255),
                    )
                    if response and "fields" in response:
                        results["deal_fields"]["created"] += 1
                        logger.info(f"Created Zoho deal field: {field['field_label']}")
                    else:
                        results["deal_fields"]["failed"] += 1
                        results["deal_fields"]["errors"].append(
                            f"Failed to create {field['field_label']}: API returned no data"
                        )
                except Exception as e:
                    results["deal_fields"]["failed"] += 1
                    results["deal_fields"]["errors"].append(
                        f"Failed to create {field['field_label']}: {str(e)}"
                    )

            # If all failed, provide manual instructions
            if (results["contact_fields"]["created"] == 0 and
                results["deal_fields"]["created"] == 0):
                results["manual_setup_required"] = True
                results["instructions"] = await self.get_required_fields_info()

            return results

    async def sync_contact_attribution(
        self,
        contact_id: Optional[UUID] = None,
        modified_since: Optional[datetime] = None,
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Sync contact attribution data to Zoho CRM.

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
            CRMContact.crm_contact_id.isnot(None),
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
            # Skip lead-prefixed contacts (leads have different module)
            if contact.crm_contact_id.startswith("lead_"):
                continue

            # Get attribution data
            attribution = await self._get_contact_attribution(contact.id)

            if attribution:
                update_data = {
                    "id": contact.crm_contact_id,
                    "Stratum_Ad_Platform": attribution.get("platform"),
                    "Stratum_Campaign_ID": attribution.get("campaign_id"),
                    "Stratum_Campaign_Name": attribution.get("campaign_name"),
                    "Stratum_Adset_ID": attribution.get("adset_id"),
                    "Stratum_Ad_ID": attribution.get("ad_id"),
                    "Stratum_First_Touch_Source": attribution.get("first_touch_source"),
                    "Stratum_Last_Touch_Source": attribution.get("last_touch_source"),
                    "Stratum_Attribution_Confidence": attribution.get("confidence"),
                    "Stratum_Total_Ad_Spend": attribution.get("total_spend"),
                    "Stratum_Touchpoints_Count": attribution.get("touchpoints_count"),
                    "Stratum_Last_Sync": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                }

                # Remove None values
                update_data = {k: v for k, v in update_data.items() if v is not None}
                updates.append(update_data)

        if not updates:
            return {
                "status": "success",
                "message": "No attribution data to sync",
                "synced": 0,
                "failed": 0,
            }

        # Batch update in Zoho
        async with ZohoClient(self.db, self.tenant_id, self.region) as client:
            response = await client.batch_update_contacts(updates)

        synced = len(response.get("data", [])) if response else 0
        failed = len(response.get("errors", [])) if response else len(updates)

        logger.info(
            "zoho_contact_writeback_complete",
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
    ) -> Dict[str, Any]:
        """
        Sync deal attribution data to Zoho CRM.

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
            CRMDeal.crm_deal_id.isnot(None),
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

            update_data = {
                "id": deal.crm_deal_id,
                "Stratum_Attributed_Platform": attribution.get("platform"),
                "Stratum_Attributed_Campaign": attribution.get("campaign_name"),
                "Stratum_Attributed_Campaign_ID": attribution.get("campaign_id"),
                "Stratum_Attribution_Model": attribution.get("attribution_model"),
                "Stratum_Attributed_Spend": attribution.get("attributed_spend"),
                "Stratum_Revenue_ROAS": attribution.get("revenue_roas"),
                "Stratum_Profit_ROAS": attribution.get("profit_roas"),
                "Stratum_COGS": attribution.get("cogs"),
                "Stratum_Gross_Profit": attribution.get("gross_profit"),
                "Stratum_Net_Profit": attribution.get("net_profit"),
                "Stratum_Days_to_Close": attribution.get("days_to_close"),
                "Stratum_Touchpoints_Count": attribution.get("touchpoints_count"),
                "Stratum_Last_Sync": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            }

            # Remove None values
            update_data = {k: v for k, v in update_data.items() if v is not None}
            updates.append(update_data)

        if not updates:
            return {
                "status": "success",
                "message": "No attribution data to sync",
                "synced": 0,
                "failed": 0,
            }

        # Batch update in Zoho
        async with ZohoClient(self.db, self.tenant_id, self.region) as client:
            response = await client.batch_update_deals(updates)

        synced = len(response.get("data", [])) if response else 0
        failed = len(response.get("errors", [])) if response else len(updates)

        logger.info(
            "zoho_deal_writeback_complete",
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
    ) -> Dict[str, Any]:
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
            "provider": "zoho",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "contacts": None,
            "deals": None,
        }

        if sync_contacts:
            results["contacts"] = await self.sync_contact_attribution(
                modified_since=modified_since
            )
            if results["contacts"]["status"] == "failed":
                results["status"] = "partial"

        if sync_deals:
            results["deals"] = await self.sync_deal_attribution(
                modified_since=modified_since
            )
            if results["deals"]["status"] == "failed":
                results["status"] = "partial"

        results["completed_at"] = datetime.now(timezone.utc).isoformat()

        # Update connection last sync time
        conn_result = await self.db.execute(
            select(CRMConnection).where(
                and_(
                    CRMConnection.tenant_id == self.tenant_id,
                    CRMConnection.provider == CRMProvider.ZOHO,
                    CRMConnection.status == CRMConnectionStatus.CONNECTED,
                )
            )
        )
        connection = conn_result.scalar_one_or_none()
        if connection:
            connection.last_sync_at = datetime.now(timezone.utc)
            connection.last_sync_status = results["status"]
            await self.db.commit()

        return results

    async def _get_contact_attribution(self, contact_id: UUID) -> Dict[str, Any]:
        """Get attribution data for a contact from touchpoints."""
        # Get touchpoints for this contact
        result = await self.db.execute(
            select(Touchpoint)
            .where(Touchpoint.contact_id == contact_id)
            .order_by(Touchpoint.event_ts)
        )
        touchpoints = result.scalars().all()

        if not touchpoints:
            return {}

        # Get first and last touch
        first_touch = touchpoints[0]
        last_touch = touchpoints[-1]

        # Calculate total spend
        total_spend = sum(
            (tp.cost_cents or 0) / 100 for tp in touchpoints
        )

        return {
            "platform": last_touch.source,
            "campaign_id": last_touch.campaign_id,
            "campaign_name": last_touch.campaign_name,
            "adset_id": last_touch.adset_id,
            "ad_id": last_touch.ad_id,
            "first_touch_source": f"{first_touch.source}:{first_touch.campaign_name}" if first_touch.campaign_name else first_touch.source,
            "last_touch_source": f"{last_touch.source}:{last_touch.campaign_name}" if last_touch.campaign_name else last_touch.source,
            "confidence": 85,  # Default confidence
            "total_spend": round(total_spend, 2) if total_spend > 0 else None,
            "touchpoints_count": len(touchpoints),
        }

    async def _get_deal_attribution(self, deal_id: UUID) -> Dict[str, Any]:
        """Get attribution data for a deal."""
        # Get deal
        result = await self.db.execute(
            select(CRMDeal).where(CRMDeal.id == deal_id)
        )
        deal = result.scalar_one_or_none()

        if not deal:
            return {}

        # Get associated contact touchpoints
        touchpoints = []
        if deal.contact_id:
            tp_result = await self.db.execute(
                select(Touchpoint)
                .where(Touchpoint.contact_id == deal.contact_id)
                .order_by(Touchpoint.event_ts)
            )
            touchpoints = tp_result.scalars().all()

        # Calculate metrics
        total_spend = sum(
            (tp.cost_cents or 0) / 100 for tp in touchpoints
        )

        deal_amount = deal.amount or 0

        # Revenue ROAS
        revenue_roas = deal_amount / total_spend if total_spend > 0 else None

        # Profit metrics
        gross_profit = None
        profit_roas = None
        net_profit = None
        cogs = None

        if deal.amount and deal.is_won:
            # Estimate COGS at 70% (would come from profit service in production)
            cogs = deal_amount * 0.7
            gross_profit = deal_amount - cogs
            net_profit = gross_profit - total_spend
            profit_roas = gross_profit / total_spend if total_spend > 0 else None

        # Days to close
        days_to_close = None
        if touchpoints and deal.won_at:
            first_touch_date = touchpoints[0].event_ts.date()
            days_to_close = (deal.won_at.date() - first_touch_date).days

        # Get primary attribution (last touch by default)
        primary_tp = touchpoints[-1] if touchpoints else None

        return {
            "platform": primary_tp.source if primary_tp else deal.attributed_platform,
            "campaign_id": primary_tp.campaign_id if primary_tp else deal.attributed_campaign_id,
            "campaign_name": primary_tp.campaign_name if primary_tp else None,
            "attribution_model": deal.attribution_model.value if deal.attribution_model else "last_touch",
            "attributed_spend": round(total_spend, 2) if total_spend > 0 else None,
            "revenue_roas": round(revenue_roas, 2) if revenue_roas else None,
            "profit_roas": round(profit_roas, 2) if profit_roas else None,
            "cogs": round(cogs, 2) if cogs else None,
            "gross_profit": round(gross_profit, 2) if gross_profit else None,
            "net_profit": round(net_profit, 2) if net_profit else None,
            "days_to_close": days_to_close,
            "touchpoints_count": len(touchpoints),
        }

    async def get_writeback_status(self) -> Dict[str, Any]:
        """Get current writeback configuration and status."""
        # Get connection
        result = await self.db.execute(
            select(CRMConnection).where(
                and_(
                    CRMConnection.tenant_id == self.tenant_id,
                    CRMConnection.provider == CRMProvider.ZOHO,
                )
            )
        )
        connection = result.scalar_one_or_none()

        if not connection or connection.status != CRMConnectionStatus.CONNECTED:
            return {
                "enabled": False,
                "connected": False,
                "provider": "zoho",
                "message": "Zoho CRM not connected",
            }

        # Count records to sync
        contacts_count = await self.db.execute(
            select(func.count()).select_from(CRMContact).where(
                CRMContact.tenant_id == self.tenant_id
            )
        )
        deals_count = await self.db.execute(
            select(func.count()).select_from(CRMDeal).where(
                CRMDeal.tenant_id == self.tenant_id
            )
        )

        return {
            "enabled": True,
            "connected": True,
            "provider": "zoho",
            "provider_account_id": connection.provider_account_id,
            "provider_account_name": connection.provider_account_name,
            "last_sync_at": connection.last_sync_at.isoformat() if connection.last_sync_at else None,
            "last_sync_status": connection.last_sync_status,
            "contacts_count": contacts_count.scalar(),
            "deals_count": deals_count.scalar(),
            "fields": {
                "contact_fields": len(CONTACT_FIELDS),
                "deal_fields": len(DEAL_FIELDS),
            },
        }

    async def write_segment_membership(
        self,
        contact_id: str,
        segments: List[str],
    ) -> Dict[str, Any]:
        """
        Write segment membership to a contact.

        Args:
            contact_id: Zoho contact ID
            segments: List of segment names

        Returns:
            Update result
        """
        async with ZohoClient(self.db, self.tenant_id, self.region) as client:
            update_data = {
                "Stratum_Segments": ", ".join(segments[:10]),  # Limit to 10 segments
                "Stratum_Last_Sync": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            }

            response = await client.update_contact(contact_id, update_data)

            if response and "data" in response:
                return {"status": "success", "contact_id": contact_id}
            else:
                return {"status": "failed", "contact_id": contact_id, "error": "Update failed"}
