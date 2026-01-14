# =============================================================================
# Stratum AI - HubSpot Sync Service
# =============================================================================
"""
Synchronizes contacts and deals from HubSpot to Stratum AI.
Supports scheduled syncs and real-time webhook updates.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.crm import (
    CRMConnection,
    CRMConnectionStatus,
    CRMContact,
    CRMDeal,
    CRMProvider,
    DealStage,
)
from app.services.crm.hubspot_client import HubSpotClient, hash_email, hash_phone
from app.services.crm.identity_matching import IdentityMatcher

logger = get_logger(__name__)


# Stage mapping from HubSpot to normalized stages
HUBSPOT_STAGE_MAPPING = {
    # Common HubSpot default stages
    "appointmentscheduled": DealStage.SQL,
    "qualifiedtobuy": DealStage.SQL,
    "presentationscheduled": DealStage.OPPORTUNITY,
    "decisionmakerboughtin": DealStage.PROPOSAL,
    "contractsent": DealStage.NEGOTIATION,
    "closedwon": DealStage.WON,
    "closedlost": DealStage.LOST,
    # Generic mappings
    "lead": DealStage.LEAD,
    "mql": DealStage.MQL,
    "sql": DealStage.SQL,
    "opportunity": DealStage.OPPORTUNITY,
    "proposal": DealStage.PROPOSAL,
    "negotiation": DealStage.NEGOTIATION,
    "won": DealStage.WON,
    "lost": DealStage.LOST,
}


class HubSpotSyncService:
    """
    Handles synchronization of HubSpot data to Stratum AI.

    Features:
    - Incremental sync (only updated records)
    - Full sync (all records)
    - Identity matching for attribution
    - Deal-contact association
    - Pipeline metrics aggregation
    """

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.client = HubSpotClient(db, tenant_id)
        self.identity_matcher = IdentityMatcher(db, tenant_id)

    async def sync_all(self, full_sync: bool = False) -> Dict[str, Any]:
        """
        Synchronize all HubSpot data.

        Args:
            full_sync: If True, sync all records. If False, sync only since last sync.

        Returns:
            Sync summary with counts and status
        """
        connection = await self._get_connection()
        if not connection or connection.status != CRMConnectionStatus.CONNECTED:
            return {
                "status": "error",
                "message": "HubSpot not connected",
            }

        # Determine sync start time
        updated_after = None
        if not full_sync and connection.last_sync_at:
            updated_after = connection.last_sync_at

        results = {
            "contacts_synced": 0,
            "contacts_created": 0,
            "contacts_updated": 0,
            "deals_synced": 0,
            "deals_created": 0,
            "deals_updated": 0,
            "errors": [],
        }

        try:
            # Sync contacts
            contact_results = await self._sync_contacts(connection, updated_after)
            results.update({
                "contacts_synced": contact_results["synced"],
                "contacts_created": contact_results["created"],
                "contacts_updated": contact_results["updated"],
            })
            if contact_results.get("errors"):
                results["errors"].extend(contact_results["errors"])

            # Sync deals
            deal_results = await self._sync_deals(connection, updated_after)
            results.update({
                "deals_synced": deal_results["synced"],
                "deals_created": deal_results["created"],
                "deals_updated": deal_results["updated"],
            })
            if deal_results.get("errors"):
                results["errors"].extend(deal_results["errors"])

            # Perform identity matching
            await self.identity_matcher.match_contacts_to_touchpoints()

            # Update connection status
            connection.last_sync_at = datetime.now(timezone.utc)
            connection.last_sync_status = "success" if not results["errors"] else "partial"
            connection.last_sync_contacts_count = results["contacts_synced"]
            connection.last_sync_deals_count = results["deals_synced"]

            await self.db.commit()

            results["status"] = "success" if not results["errors"] else "partial"
            logger.info(
                "hubspot_sync_complete",
                tenant_id=self.tenant_id,
                contacts=results["contacts_synced"],
                deals=results["deals_synced"],
            )

        except Exception as e:
            logger.error("hubspot_sync_failed", tenant_id=self.tenant_id, error=str(e))
            connection.last_sync_status = "failed"
            await self.db.commit()
            results["status"] = "error"
            results["errors"].append(str(e))

        return results

    async def _sync_contacts(
        self,
        connection: CRMConnection,
        updated_after: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Sync contacts from HubSpot."""
        results = {"synced": 0, "created": 0, "updated": 0, "errors": []}
        after = None

        properties = [
            "email", "phone", "mobilephone", "firstname", "lastname",
            "lifecyclestage", "hs_lead_status", "lead_source",
            "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
            "hs_analytics_source", "hs_analytics_first_url",
            "gclid", "hs_google_click_id",
            "createdate", "lastmodifieddate",
        ]

        async with self.client:
            while True:
                response = await self.client.get_contacts(
                    limit=100,
                    after=after,
                    properties=properties,
                    updated_after=updated_after,
                )

                if not response or "results" not in response:
                    break

                for contact_data in response["results"]:
                    try:
                        created, updated = await self._upsert_contact(
                            connection.id,
                            contact_data,
                        )
                        results["synced"] += 1
                        if created:
                            results["created"] += 1
                        elif updated:
                            results["updated"] += 1
                    except Exception as e:
                        results["errors"].append(f"Contact {contact_data.get('id')}: {str(e)}")

                # Check for more pages
                paging = response.get("paging", {})
                next_page = paging.get("next", {})
                after = next_page.get("after")

                if not after:
                    break

                # Commit batch
                await self.db.commit()

        await self.db.commit()
        return results

    async def _upsert_contact(
        self,
        connection_id: UUID,
        contact_data: Dict[str, Any],
    ) -> Tuple[bool, bool]:
        """
        Insert or update a contact.

        Returns:
            Tuple of (created, updated) booleans
        """
        crm_contact_id = str(contact_data["id"])
        properties = contact_data.get("properties", {})

        # Check if contact exists
        result = await self.db.execute(
            select(CRMContact).where(
                and_(
                    CRMContact.connection_id == connection_id,
                    CRMContact.crm_contact_id == crm_contact_id,
                )
            )
        )
        existing = result.scalar_one_or_none()

        # Extract and hash identity fields
        email = properties.get("email", "")
        phone = properties.get("phone") or properties.get("mobilephone") or ""

        email_hashed = hash_email(email) if email else None
        phone_hashed = hash_phone(phone) if phone else None

        # Parse dates
        crm_created = None
        crm_updated = None
        if properties.get("createdate"):
            try:
                crm_created = datetime.fromisoformat(
                    properties["createdate"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass
        if properties.get("lastmodifieddate"):
            try:
                crm_updated = datetime.fromisoformat(
                    properties["lastmodifieddate"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        contact_fields = {
            "crm_owner_id": properties.get("hubspot_owner_id"),
            "email_hash": email_hashed,
            "phone_hash": phone_hashed,
            "utm_source": properties.get("utm_source"),
            "utm_medium": properties.get("utm_medium"),
            "utm_campaign": properties.get("utm_campaign"),
            "utm_content": properties.get("utm_content"),
            "utm_term": properties.get("utm_term"),
            "gclid": properties.get("gclid") or properties.get("hs_google_click_id"),
            "lifecycle_stage": properties.get("lifecyclestage"),
            "lead_source": properties.get("lead_source") or properties.get("hs_analytics_source"),
            "raw_properties": properties,
            "crm_created_at": crm_created,
            "crm_updated_at": crm_updated,
        }

        if existing:
            # Update existing contact
            for key, value in contact_fields.items():
                if value is not None:
                    setattr(existing, key, value)
            existing.updated_at = datetime.now(timezone.utc)
            return False, True
        else:
            # Create new contact
            contact = CRMContact(
                tenant_id=self.tenant_id,
                connection_id=connection_id,
                crm_contact_id=crm_contact_id,
                **contact_fields,
            )
            self.db.add(contact)
            return True, False

    async def _sync_deals(
        self,
        connection: CRMConnection,
        updated_after: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Sync deals from HubSpot."""
        results = {"synced": 0, "created": 0, "updated": 0, "errors": []}
        after = None

        properties = [
            "dealname", "amount", "dealstage", "pipeline",
            "closedate", "hs_is_closed_won", "hs_is_closed",
            "hubspot_owner_id", "hs_analytics_source",
            "createdate", "hs_lastmodifieddate",
        ]

        async with self.client:
            while True:
                response = await self.client.get_deals(
                    limit=100,
                    after=after,
                    properties=properties,
                    updated_after=updated_after,
                )

                if not response or "results" not in response:
                    break

                for deal_data in response["results"]:
                    try:
                        created, updated = await self._upsert_deal(
                            connection.id,
                            deal_data,
                        )
                        results["synced"] += 1
                        if created:
                            results["created"] += 1
                        elif updated:
                            results["updated"] += 1
                    except Exception as e:
                        results["errors"].append(f"Deal {deal_data.get('id')}: {str(e)}")

                # Check for more pages
                paging = response.get("paging", {})
                next_page = paging.get("next", {})
                after = next_page.get("after")

                if not after:
                    break

                # Commit batch
                await self.db.commit()

        await self.db.commit()

        # Now associate deals with contacts
        await self._associate_deals_with_contacts(connection.id)

        return results

    async def _upsert_deal(
        self,
        connection_id: UUID,
        deal_data: Dict[str, Any],
    ) -> Tuple[bool, bool]:
        """
        Insert or update a deal.

        Returns:
            Tuple of (created, updated) booleans
        """
        crm_deal_id = str(deal_data["id"])
        properties = deal_data.get("properties", {})

        # Check if deal exists
        result = await self.db.execute(
            select(CRMDeal).where(
                and_(
                    CRMDeal.connection_id == connection_id,
                    CRMDeal.crm_deal_id == crm_deal_id,
                )
            )
        )
        existing = result.scalar_one_or_none()

        # Parse amount
        amount = None
        amount_cents = None
        if properties.get("amount"):
            try:
                amount = float(properties["amount"])
                amount_cents = int(amount * 100)
            except (ValueError, TypeError):
                pass

        # Parse stage
        stage = properties.get("dealstage", "")
        stage_normalized = HUBSPOT_STAGE_MAPPING.get(
            stage.lower().replace(" ", "").replace("_", ""),
            None,
        )

        # Parse close date
        close_date = None
        if properties.get("closedate"):
            try:
                close_date = datetime.fromisoformat(
                    properties["closedate"].replace("Z", "+00:00")
                ).date()
            except (ValueError, TypeError):
                pass

        # Parse won/closed flags
        is_won = str(properties.get("hs_is_closed_won", "")).lower() == "true"
        is_closed = str(properties.get("hs_is_closed", "")).lower() == "true"

        # Parse dates
        crm_created = None
        crm_updated = None
        if properties.get("createdate"):
            try:
                crm_created = datetime.fromisoformat(
                    properties["createdate"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass
        if properties.get("hs_lastmodifieddate"):
            try:
                crm_updated = datetime.fromisoformat(
                    properties["hs_lastmodifieddate"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        deal_fields = {
            "crm_pipeline_id": properties.get("pipeline"),
            "crm_owner_id": properties.get("hubspot_owner_id"),
            "deal_name": properties.get("dealname"),
            "stage": stage,
            "stage_normalized": stage_normalized,
            "amount": amount,
            "amount_cents": amount_cents,
            "close_date": close_date,
            "is_won": is_won,
            "is_closed": is_closed,
            "raw_properties": properties,
            "crm_created_at": crm_created,
            "crm_updated_at": crm_updated,
        }

        # Set won_at timestamp
        if is_won and close_date:
            deal_fields["won_at"] = datetime.combine(
                close_date,
                datetime.min.time(),
                tzinfo=timezone.utc,
            )

        if existing:
            # Update existing deal
            for key, value in deal_fields.items():
                if value is not None:
                    setattr(existing, key, value)
            existing.updated_at = datetime.now(timezone.utc)
            return False, True
        else:
            # Create new deal
            deal = CRMDeal(
                tenant_id=self.tenant_id,
                connection_id=connection_id,
                crm_deal_id=crm_deal_id,
                **deal_fields,
            )
            self.db.add(deal)
            return True, False

    async def _associate_deals_with_contacts(self, connection_id: UUID) -> None:
        """Associate deals with their contacts via HubSpot associations API."""
        # Get all deals without contacts
        result = await self.db.execute(
            select(CRMDeal).where(
                and_(
                    CRMDeal.connection_id == connection_id,
                    CRMDeal.contact_id.is_(None),
                )
            )
        )
        deals_without_contacts = result.scalars().all()

        async with self.client:
            for deal in deals_without_contacts:
                try:
                    # Get deal associations
                    associations = await self.client.get_deal_associations(
                        deal.crm_deal_id,
                        "contacts",
                    )

                    if associations and associations.get("results"):
                        # Get first associated contact
                        contact_id = str(associations["results"][0].get("id"))

                        # Find contact in our database
                        contact_result = await self.db.execute(
                            select(CRMContact).where(
                                and_(
                                    CRMContact.connection_id == connection_id,
                                    CRMContact.crm_contact_id == contact_id,
                                )
                            )
                        )
                        contact = contact_result.scalar_one_or_none()

                        if contact:
                            deal.contact_id = contact.id

                            # Copy attribution from contact if available
                            if contact.last_touch_campaign_id:
                                deal.attributed_campaign_id = contact.last_touch_campaign_id
                            if contact.utm_source:
                                # Map utm_source to platform
                                platform_map = {
                                    "facebook": "meta",
                                    "fb": "meta",
                                    "meta": "meta",
                                    "google": "google",
                                    "tiktok": "tiktok",
                                    "snapchat": "snapchat",
                                }
                                deal.attributed_platform = platform_map.get(
                                    contact.utm_source.lower(),
                                    contact.utm_source,
                                )

                except Exception as e:
                    logger.warning(
                        "deal_association_failed",
                        deal_id=deal.crm_deal_id,
                        error=str(e),
                    )

        await self.db.commit()

    async def process_webhook(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming webhook from HubSpot.

        Args:
            event_type: Type of event (e.g., "contact.creation", "deal.propertyChange")
            data: Webhook payload

        Returns:
            Processing result
        """
        logger.info("hubspot_webhook_received", event_type=event_type)

        connection = await self._get_connection()
        if not connection:
            return {"status": "error", "message": "No HubSpot connection"}

        result = {"status": "processed", "event_type": event_type}

        try:
            if event_type.startswith("contact."):
                # Fetch and upsert contact
                object_id = str(data.get("objectId"))
                async with self.client:
                    contact_data = await self.client.get_contact(object_id)
                    if contact_data:
                        await self._upsert_contact(connection.id, contact_data)
                        await self.db.commit()
                        result["contact_id"] = object_id

            elif event_type.startswith("deal."):
                # Fetch and upsert deal
                object_id = str(data.get("objectId"))
                async with self.client:
                    deal_data = await self.client.get_deal(object_id)
                    if deal_data:
                        await self._upsert_deal(connection.id, deal_data)
                        await self.db.commit()
                        result["deal_id"] = object_id

        except Exception as e:
            logger.error("hubspot_webhook_processing_failed", error=str(e))
            result["status"] = "error"
            result["error"] = str(e)

        return result

    async def _get_connection(self) -> Optional[CRMConnection]:
        """Get HubSpot connection for tenant."""
        result = await self.db.execute(
            select(CRMConnection).where(
                and_(
                    CRMConnection.tenant_id == self.tenant_id,
                    CRMConnection.provider == CRMProvider.HUBSPOT,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_pipeline_summary(self) -> Dict[str, Any]:
        """
        Get summary of CRM pipeline metrics.

        Returns:
            Pipeline summary with stage counts and values
        """
        connection = await self._get_connection()
        if not connection:
            return {"status": "not_connected"}

        # Get deal counts by stage
        stage_counts = {}
        stage_values = {}

        for stage in DealStage:
            result = await self.db.execute(
                select(CRMDeal).where(
                    and_(
                        CRMDeal.tenant_id == self.tenant_id,
                        CRMDeal.stage_normalized == stage,
                        CRMDeal.is_closed == False,
                    )
                )
            )
            deals = result.scalars().all()
            stage_counts[stage.value] = len(deals)
            stage_values[stage.value] = sum(d.amount or 0 for d in deals)

        # Get won deals
        result = await self.db.execute(
            select(CRMDeal).where(
                and_(
                    CRMDeal.tenant_id == self.tenant_id,
                    CRMDeal.is_won == True,
                )
            )
        )
        won_deals = result.scalars().all()

        return {
            "status": "connected",
            "stage_counts": stage_counts,
            "stage_values": stage_values,
            "total_pipeline_value": sum(stage_values.values()),
            "total_won_value": sum(d.amount or 0 for d in won_deals),
            "won_deal_count": len(won_deals),
            "last_sync_at": connection.last_sync_at.isoformat() if connection.last_sync_at else None,
        }
