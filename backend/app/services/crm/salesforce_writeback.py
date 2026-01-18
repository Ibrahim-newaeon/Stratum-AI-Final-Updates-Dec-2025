# =============================================================================
# Stratum AI - Salesforce Writeback Service
# =============================================================================
"""
Service for writing attribution data back to Salesforce.

Features:
- Custom field creation for Stratum attribution data
- Contact/Lead attribution writeback (ad platform, campaign, ROAS)
- Opportunity attribution writeback (revenue attribution, profit ROAS)
- Batch sync operations
- Writeback history tracking
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
    Touchpoint,
    CRMConnectionStatus,
    CRMProvider,
)
from app.services.crm.salesforce_client import SalesforceClient

logger = get_logger(__name__)


# =============================================================================
# Custom Field Definitions
# =============================================================================

# Stratum AI custom fields for Contacts
CONTACT_CUSTOM_FIELDS = [
    {
        "api_name": "Stratum_Ad_Platform__c",
        "label": "Stratum - Ad Platform",
        "type": "Text",
        "length": 255,
        "description": "Primary advertising platform that acquired this contact",
    },
    {
        "api_name": "Stratum_Campaign_ID__c",
        "label": "Stratum - Campaign ID",
        "type": "Text",
        "length": 255,
        "description": "Campaign ID from ad platform",
    },
    {
        "api_name": "Stratum_Campaign_Name__c",
        "label": "Stratum - Campaign Name",
        "type": "Text",
        "length": 255,
        "description": "Campaign name from ad platform",
    },
    {
        "api_name": "Stratum_First_Touch_Source__c",
        "label": "Stratum - First Touch Source",
        "type": "Text",
        "length": 255,
        "description": "First touch attribution source",
    },
    {
        "api_name": "Stratum_Last_Touch_Source__c",
        "label": "Stratum - Last Touch Source",
        "type": "Text",
        "length": 255,
        "description": "Last touch attribution source",
    },
    {
        "api_name": "Stratum_Attribution_Confidence__c",
        "label": "Stratum - Attribution Confidence",
        "type": "Number",
        "precision": 5,
        "scale": 2,
        "description": "Attribution confidence score (0-100)",
    },
    {
        "api_name": "Stratum_Total_Ad_Spend__c",
        "label": "Stratum - Total Ad Spend",
        "type": "Currency",
        "precision": 16,
        "scale": 2,
        "description": "Total attributed ad spend for this contact",
    },
    {
        "api_name": "Stratum_Touchpoints_Count__c",
        "label": "Stratum - Touchpoints Count",
        "type": "Number",
        "precision": 8,
        "scale": 0,
        "description": "Number of ad touchpoints before conversion",
    },
    {
        "api_name": "Stratum_Last_Sync__c",
        "label": "Stratum - Last Sync",
        "type": "DateTime",
        "description": "Last time Stratum synced attribution data",
    },
]

# Stratum AI custom fields for Opportunities
OPPORTUNITY_CUSTOM_FIELDS = [
    {
        "api_name": "Stratum_Attributed_Platform__c",
        "label": "Stratum - Attributed Platform",
        "type": "Text",
        "length": 255,
        "description": "Primary platform attributed for this opportunity",
    },
    {
        "api_name": "Stratum_Attributed_Campaign__c",
        "label": "Stratum - Attributed Campaign",
        "type": "Text",
        "length": 255,
        "description": "Campaign name attributed for this opportunity",
    },
    {
        "api_name": "Stratum_Attribution_Model__c",
        "label": "Stratum - Attribution Model",
        "type": "Text",
        "length": 100,
        "description": "Attribution model used (last_touch, first_touch, etc.)",
    },
    {
        "api_name": "Stratum_Attributed_Spend__c",
        "label": "Stratum - Attributed Ad Spend",
        "type": "Currency",
        "precision": 16,
        "scale": 2,
        "description": "Ad spend attributed to this opportunity",
    },
    {
        "api_name": "Stratum_Revenue_ROAS__c",
        "label": "Stratum - Revenue ROAS",
        "type": "Number",
        "precision": 10,
        "scale": 2,
        "description": "Revenue ROAS (amount / ad spend)",
    },
    {
        "api_name": "Stratum_Profit_ROAS__c",
        "label": "Stratum - Profit ROAS",
        "type": "Number",
        "precision": 10,
        "scale": 2,
        "description": "Profit ROAS (after COGS)",
    },
    {
        "api_name": "Stratum_Gross_Profit__c",
        "label": "Stratum - Gross Profit",
        "type": "Currency",
        "precision": 16,
        "scale": 2,
        "description": "Gross profit (revenue - COGS)",
    },
    {
        "api_name": "Stratum_Net_Profit__c",
        "label": "Stratum - Net Profit",
        "type": "Currency",
        "precision": 16,
        "scale": 2,
        "description": "Net profit (gross profit - ad spend)",
    },
    {
        "api_name": "Stratum_Days_to_Close__c",
        "label": "Stratum - Days to Close",
        "type": "Number",
        "precision": 8,
        "scale": 0,
        "description": "Days from first touch to close",
    },
    {
        "api_name": "Stratum_Touchpoints_Count__c",
        "label": "Stratum - Touchpoints Count",
        "type": "Number",
        "precision": 8,
        "scale": 0,
        "description": "Number of ad touchpoints in the journey",
    },
    {
        "api_name": "Stratum_Last_Sync__c",
        "label": "Stratum - Last Sync",
        "type": "DateTime",
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


class SalesforceWritebackService:
    """
    Service for writing Stratum attribution data back to Salesforce.

    Pushes:
    - Contact attribution (platform, campaign, ad)
    - Opportunity attribution (ROAS, profit metrics)
    - Touchpoint data
    """

    def __init__(self, db: AsyncSession, tenant_id: int, is_sandbox: bool = False):
        self.db = db
        self.tenant_id = tenant_id
        self.client = SalesforceClient(db, tenant_id, is_sandbox)
        self._existing_fields: Dict[str, List[str]] = {}

    async def setup_custom_fields(self) -> Dict[str, Any]:
        """
        Create Stratum custom fields in Salesforce.

        Note: Creating custom fields via API requires Metadata API access.
        This method provides field specifications for manual creation
        or uses Metadata API if available.

        Returns:
            Summary of field setup status
        """
        results = {
            "contact_fields": {
                "required": len(CONTACT_CUSTOM_FIELDS),
                "existing": 0,
                "missing": [],
            },
            "opportunity_fields": {
                "required": len(OPPORTUNITY_CUSTOM_FIELDS),
                "existing": 0,
                "missing": [],
            },
            "instructions": [],
        }

        async with self.client:
            # Check existing Contact fields
            contact_fields = await self.client.get_custom_fields("Contact")
            contact_field_names = {f.get("name", "").lower() for f in contact_fields}

            for field in CONTACT_CUSTOM_FIELDS:
                if field["api_name"].lower() in contact_field_names:
                    results["contact_fields"]["existing"] += 1
                else:
                    results["contact_fields"]["missing"].append(field["api_name"])

            # Check existing Opportunity fields
            opp_fields = await self.client.get_custom_fields("Opportunity")
            opp_field_names = {f.get("name", "").lower() for f in opp_fields}

            for field in OPPORTUNITY_CUSTOM_FIELDS:
                if field["api_name"].lower() in opp_field_names:
                    results["opportunity_fields"]["existing"] += 1
                else:
                    results["opportunity_fields"]["missing"].append(field["api_name"])

        # Provide instructions for missing fields
        if results["contact_fields"]["missing"] or results["opportunity_fields"]["missing"]:
            results["instructions"] = [
                "Some custom fields need to be created in Salesforce Setup.",
                "Go to Setup > Object Manager > [Contact/Opportunity] > Fields & Relationships > New",
                "Create the following fields with the specified properties:",
            ]

            if results["contact_fields"]["missing"]:
                results["instructions"].append(f"Contact fields needed: {', '.join(results['contact_fields']['missing'])}")

            if results["opportunity_fields"]["missing"]:
                results["instructions"].append(f"Opportunity fields needed: {', '.join(results['opportunity_fields']['missing'])}")

        return results

    async def get_required_fields_info(self) -> Dict[str, Any]:
        """Get detailed information about required custom fields."""
        return {
            "contact_fields": CONTACT_CUSTOM_FIELDS,
            "opportunity_fields": OPPORTUNITY_CUSTOM_FIELDS,
            "instructions": [
                "Create these custom fields in Salesforce Setup:",
                "1. Go to Setup > Object Manager",
                "2. Select Contact or Opportunity",
                "3. Go to Fields & Relationships",
                "4. Click New to create each field",
                "5. Use the API Name exactly as specified (including __c suffix)",
            ],
        }

    async def sync_contact_attribution(
        self,
        contact_id: Optional[UUID] = None,
        modified_since: Optional[datetime] = None,
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Sync contact attribution data to Salesforce.

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

                    # Build properties dict
                    properties = {
                        "Stratum_Ad_Platform__c": attribution.get("platform"),
                        "Stratum_Campaign_ID__c": attribution.get("campaign_id"),
                        "Stratum_Campaign_Name__c": attribution.get("campaign_name"),
                        "Stratum_First_Touch_Source__c": attribution.get("first_touch_source"),
                        "Stratum_Last_Touch_Source__c": attribution.get("last_touch_source"),
                        "Stratum_Attribution_Confidence__c": attribution.get("confidence"),
                        "Stratum_Total_Ad_Spend__c": attribution.get("total_spend"),
                        "Stratum_Touchpoints_Count__c": attribution.get("touchpoints_count"),
                        "Stratum_Last_Sync__c": datetime.now(timezone.utc).isoformat(),
                    }

                    # Remove None values
                    properties = {k: v for k, v in properties.items() if v is not None}

                    if not properties:
                        continue

                    # Update contact in Salesforce
                    response = await self.client.update_contact(
                        contact.provider_contact_id,
                        properties,
                    )

                    if response and response.get("success"):
                        synced += 1
                        contact.last_synced_at = datetime.now(timezone.utc)
                    else:
                        failed += 1
                        errors.append({
                            "contact_id": str(contact.id),
                            "error": str(response) if response else "Unknown error",
                        })

                except Exception as e:
                    failed += 1
                    errors.append({
                        "contact_id": str(contact.id),
                        "error": str(e),
                    })
                    logger.warning(
                        "salesforce_contact_writeback_error",
                        contact_id=str(contact.id),
                        error=str(e),
                    )

        await self.db.commit()

        logger.info(
            "salesforce_contact_writeback_complete",
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

    async def sync_opportunity_attribution(
        self,
        deal_id: Optional[UUID] = None,
        modified_since: Optional[datetime] = None,
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Sync opportunity attribution data to Salesforce.

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
                "message": "No opportunities to sync",
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

                    # Build properties dict
                    properties = {
                        "Stratum_Attributed_Platform__c": attribution.get("platform"),
                        "Stratum_Attributed_Campaign__c": attribution.get("campaign_name"),
                        "Stratum_Attribution_Model__c": attribution.get("attribution_model"),
                        "Stratum_Attributed_Spend__c": attribution.get("attributed_spend"),
                        "Stratum_Revenue_ROAS__c": attribution.get("revenue_roas"),
                        "Stratum_Profit_ROAS__c": attribution.get("profit_roas"),
                        "Stratum_Gross_Profit__c": attribution.get("gross_profit"),
                        "Stratum_Net_Profit__c": attribution.get("net_profit"),
                        "Stratum_Days_to_Close__c": attribution.get("days_to_close"),
                        "Stratum_Touchpoints_Count__c": attribution.get("touchpoints_count"),
                        "Stratum_Last_Sync__c": datetime.now(timezone.utc).isoformat(),
                    }

                    # Remove None values
                    properties = {k: v for k, v in properties.items() if v is not None}

                    if not properties:
                        continue

                    # Update opportunity in Salesforce
                    response = await self.client.update_opportunity(
                        deal.provider_deal_id,
                        properties,
                    )

                    if response and response.get("success"):
                        synced += 1
                        deal.last_synced_at = datetime.now(timezone.utc)
                    else:
                        failed += 1
                        errors.append({
                            "deal_id": str(deal.id),
                            "error": str(response) if response else "Unknown error",
                        })

                except Exception as e:
                    failed += 1
                    errors.append({
                        "deal_id": str(deal.id),
                        "error": str(e),
                    })
                    logger.warning(
                        "salesforce_opportunity_writeback_error",
                        deal_id=str(deal.id),
                        error=str(e),
                    )

        await self.db.commit()

        logger.info(
            "salesforce_opportunity_writeback_complete",
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
        sync_contacts: bool = True,
        sync_opportunities: bool = True,
        modified_since: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Run full writeback sync for all contacts and opportunities.

        Args:
            sync_contacts: Whether to sync contacts
            sync_opportunities: Whether to sync opportunities
            modified_since: Only sync records modified after this time

        Returns:
            Combined sync results
        """
        results = {
            "status": "completed",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "contacts": None,
            "opportunities": None,
        }

        if sync_contacts:
            results["contacts"] = await self.sync_contact_attribution(
                modified_since=modified_since
            )
            if results["contacts"]["status"] == "failed":
                results["status"] = "partial"

        if sync_opportunities:
            results["opportunities"] = await self.sync_opportunity_attribution(
                modified_since=modified_since
            )
            if results["opportunities"]["status"] == "failed":
                results["status"] = "partial"

        results["completed_at"] = datetime.now(timezone.utc).isoformat()

        # Update connection last sync time
        conn_result = await self.db.execute(
            select(CRMConnection).where(
                and_(
                    CRMConnection.tenant_id == self.tenant_id,
                    CRMConnection.provider == CRMProvider.SALESFORCE,
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
        result = await self.db.execute(
            select(Touchpoint)
            .where(Touchpoint.contact_id == contact_id)
            .order_by(Touchpoint.touchpoint_time)
        )
        touchpoints = result.scalars().all()

        if not touchpoints:
            return {}

        first_touch = touchpoints[0]
        last_touch = touchpoints[-1]

        total_spend = sum(
            (tp.attributed_spend_cents or 0) / 100 for tp in touchpoints
        )

        return {
            "platform": last_touch.platform,
            "campaign_id": last_touch.campaign_id,
            "campaign_name": last_touch.campaign_name,
            "first_touch_source": f"{first_touch.platform}:{first_touch.campaign_name}" if first_touch.campaign_name else first_touch.platform,
            "last_touch_source": f"{last_touch.platform}:{last_touch.campaign_name}" if last_touch.campaign_name else last_touch.platform,
            "confidence": max((tp.match_confidence or 0) * 100 for tp in touchpoints),
            "total_spend": round(total_spend, 2) if total_spend > 0 else None,
            "touchpoints_count": len(touchpoints),
        }

    async def _get_deal_attribution(self, deal_id: UUID) -> Dict[str, Any]:
        """Get attribution data for a deal."""
        result = await self.db.execute(
            select(CRMDeal).where(CRMDeal.id == deal_id)
        )
        deal = result.scalar_one_or_none()

        if not deal:
            return {}

        touchpoints = []
        if deal.primary_contact_id:
            tp_result = await self.db.execute(
                select(Touchpoint)
                .where(Touchpoint.contact_id == deal.primary_contact_id)
                .order_by(Touchpoint.touchpoint_time)
            )
            touchpoints = tp_result.scalars().all()

        total_spend = sum(
            (tp.attributed_spend_cents or 0) / 100 for tp in touchpoints
        )

        deal_amount = (deal.amount_cents or 0) / 100
        revenue_roas = deal_amount / total_spend if total_spend > 0 else None

        gross_profit = None
        profit_roas = None
        net_profit = None

        if deal.amount_cents and deal.probability and deal.probability >= 0.5:
            cogs = deal_amount * 0.7
            gross_profit = deal_amount - cogs
            net_profit = gross_profit - total_spend
            profit_roas = gross_profit / total_spend if total_spend > 0 else None

        days_to_close = None
        if touchpoints and deal.closed_at:
            first_touch_date = touchpoints[0].touchpoint_time.date()
            days_to_close = (deal.closed_at.date() - first_touch_date).days

        primary_tp = touchpoints[-1] if touchpoints else None

        return {
            "platform": primary_tp.platform if primary_tp else None,
            "campaign_name": primary_tp.campaign_name if primary_tp else None,
            "attribution_model": deal.attribution_model.value if deal.attribution_model else "last_touch",
            "attributed_spend": round(total_spend, 2) if total_spend > 0 else None,
            "revenue_roas": round(revenue_roas, 2) if revenue_roas else None,
            "profit_roas": round(profit_roas, 2) if profit_roas else None,
            "gross_profit": round(gross_profit, 2) if gross_profit else None,
            "net_profit": round(net_profit, 2) if net_profit else None,
            "days_to_close": days_to_close,
            "touchpoints_count": len(touchpoints),
        }

    async def get_writeback_status(self) -> Dict[str, Any]:
        """Get current writeback configuration and status."""
        result = await self.db.execute(
            select(CRMConnection).where(
                CRMConnection.tenant_id == self.tenant_id,
                CRMConnection.provider == CRMProvider.SALESFORCE,
            )
        )
        connection = result.scalar_one_or_none()

        if not connection or connection.status != CRMConnectionStatus.CONNECTED:
            return {
                "enabled": False,
                "connected": False,
                "message": "Salesforce not connected",
            }

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
            "provider": "salesforce",
            "provider_account_id": connection.provider_account_id,
            "provider_account_name": connection.provider_account_name,
            "is_sandbox": (connection.raw_properties or {}).get("is_sandbox", False),
            "last_sync_at": connection.last_sync_at.isoformat() if connection.last_sync_at else None,
            "last_sync_status": connection.last_sync_status,
            "contacts_count": contacts_count.scalar(),
            "deals_count": deals_count.scalar(),
            "custom_fields": {
                "contact_fields": len(CONTACT_CUSTOM_FIELDS),
                "opportunity_fields": len(OPPORTUNITY_CUSTOM_FIELDS),
            },
        }
