# =============================================================================
# Stratum AI - Zoho CRM Sync Service
# =============================================================================
"""
Synchronizes contacts and deals from Zoho CRM to Stratum AI.
Supports scheduled syncs and incremental updates.
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
from app.services.crm.zoho_client import ZohoClient, hash_email, hash_phone
from app.services.crm.identity_matching import IdentityMatcher

logger = get_logger(__name__)


# Stage mapping from Zoho to normalized stages
# Zoho default stages: Qualification, Needs Analysis, Value Proposition,
# Identify Decision Makers, Proposal/Price Quote, Negotiation/Review, Closed Won, Closed Lost
ZOHO_STAGE_MAPPING = {
    # Zoho default stages
    "qualification": DealStage.LEAD,
    "needs analysis": DealStage.MQL,
    "value proposition": DealStage.SQL,
    "identify decision makers": DealStage.SQL,
    "proposal/price quote": DealStage.PROPOSAL,
    "proposal": DealStage.PROPOSAL,
    "negotiation/review": DealStage.NEGOTIATION,
    "negotiation": DealStage.NEGOTIATION,
    "closed won": DealStage.WON,
    "closed-won": DealStage.WON,
    "closed lost": DealStage.LOST,
    "closed-lost": DealStage.LOST,
    # Generic mappings
    "lead": DealStage.LEAD,
    "mql": DealStage.MQL,
    "sql": DealStage.SQL,
    "opportunity": DealStage.OPPORTUNITY,
    "won": DealStage.WON,
    "lost": DealStage.LOST,
}


class ZohoSyncService:
    """
    Handles synchronization of Zoho CRM data to Stratum AI.

    Features:
    - Incremental sync (only updated records)
    - Full sync (all records)
    - Identity matching for attribution
    - Deal-contact association
    - Pipeline metrics aggregation
    - Multi-region support
    """

    def __init__(self, db: AsyncSession, tenant_id: int, region: str = "com"):
        """
        Initialize Zoho sync service.

        Args:
            db: Database session
            tenant_id: Tenant ID
            region: Zoho region (com, eu, in, com.au, jp, com.cn)
        """
        self.db = db
        self.tenant_id = tenant_id
        self.region = region
        self.client = ZohoClient(db, tenant_id, region)
        self.identity_matcher = IdentityMatcher(db, tenant_id)

    async def sync_all(self, full_sync: bool = False) -> Dict[str, Any]:
        """
        Synchronize all Zoho CRM data.

        Args:
            full_sync: If True, sync all records. If False, sync only since last sync.

        Returns:
            Sync summary with counts and status
        """
        connection = await self._get_connection()
        if not connection or connection.status != CRMConnectionStatus.CONNECTED:
            return {
                "status": "error",
                "message": "Zoho CRM not connected",
            }

        # Determine sync start time
        modified_since = None
        if not full_sync and connection.last_sync_at:
            modified_since = connection.last_sync_at

        results = {
            "contacts_synced": 0,
            "contacts_created": 0,
            "contacts_updated": 0,
            "deals_synced": 0,
            "deals_created": 0,
            "deals_updated": 0,
            "leads_synced": 0,
            "errors": [],
        }

        try:
            # Sync contacts
            contact_results = await self._sync_contacts(connection, modified_since)
            results.update({
                "contacts_synced": contact_results["synced"],
                "contacts_created": contact_results["created"],
                "contacts_updated": contact_results["updated"],
            })
            if contact_results.get("errors"):
                results["errors"].extend(contact_results["errors"])

            # Sync leads (optional - can be converted to contacts)
            lead_results = await self._sync_leads(connection, modified_since)
            results["leads_synced"] = lead_results.get("synced", 0)
            if lead_results.get("errors"):
                results["errors"].extend(lead_results["errors"])

            # Sync deals
            deal_results = await self._sync_deals(connection, modified_since)
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
                "zoho_sync_complete",
                tenant_id=self.tenant_id,
                contacts=results["contacts_synced"],
                deals=results["deals_synced"],
            )

        except Exception as e:
            logger.error("zoho_sync_failed", tenant_id=self.tenant_id, error=str(e))
            connection.last_sync_status = "failed"
            await self.db.commit()
            results["status"] = "error"
            results["errors"].append(str(e))

        return results

    async def _sync_contacts(
        self,
        connection: CRMConnection,
        modified_since: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Sync contacts from Zoho CRM."""
        results = {"synced": 0, "created": 0, "updated": 0, "errors": []}
        page = 1

        fields = [
            "Email", "Phone", "Mobile", "First_Name", "Last_Name",
            "Account_Name", "Lead_Source", "Owner",
            "Created_Time", "Modified_Time",
            # Custom UTM fields (if configured in Zoho)
            "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
            "gclid", "fbclid", "ttclid",
        ]

        async with self.client:
            while True:
                response = await self.client.get_contacts(
                    page=page,
                    per_page=200,
                    fields=fields,
                    modified_since=modified_since,
                )

                if not response or "data" not in response:
                    break

                for contact_data in response["data"]:
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
                info = response.get("info", {})
                if not info.get("more_records", False):
                    break

                page += 1

                # Commit batch
                await self.db.commit()

        await self.db.commit()
        return results

    async def _sync_leads(
        self,
        connection: CRMConnection,
        modified_since: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Sync leads from Zoho CRM (stored as contacts with lead lifecycle stage)."""
        results = {"synced": 0, "created": 0, "updated": 0, "errors": []}
        page = 1

        fields = [
            "Email", "Phone", "Mobile", "First_Name", "Last_Name",
            "Company", "Lead_Source", "Lead_Status", "Owner",
            "Created_Time", "Modified_Time",
        ]

        async with self.client:
            while True:
                response = await self.client.get_leads(
                    page=page,
                    per_page=200,
                    fields=fields,
                    modified_since=modified_since,
                )

                if not response or "data" not in response:
                    break

                for lead_data in response["data"]:
                    try:
                        # Convert lead to contact format
                        contact_data = self._convert_lead_to_contact(lead_data)
                        created, updated = await self._upsert_contact(
                            connection.id,
                            contact_data,
                            is_lead=True,
                        )
                        results["synced"] += 1
                        if created:
                            results["created"] += 1
                        elif updated:
                            results["updated"] += 1
                    except Exception as e:
                        results["errors"].append(f"Lead {lead_data.get('id')}: {str(e)}")

                # Check for more pages
                info = response.get("info", {})
                if not info.get("more_records", False):
                    break

                page += 1
                await self.db.commit()

        await self.db.commit()
        return results

    def _convert_lead_to_contact(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Zoho lead data to contact format."""
        return {
            "id": f"lead_{lead_data.get('id')}",  # Prefix to distinguish from contacts
            "Email": lead_data.get("Email"),
            "Phone": lead_data.get("Phone"),
            "Mobile": lead_data.get("Mobile"),
            "First_Name": lead_data.get("First_Name"),
            "Last_Name": lead_data.get("Last_Name"),
            "Account_Name": {"name": lead_data.get("Company")},
            "Lead_Source": lead_data.get("Lead_Source"),
            "Owner": lead_data.get("Owner"),
            "Created_Time": lead_data.get("Created_Time"),
            "Modified_Time": lead_data.get("Modified_Time"),
            "_lifecycle_stage": "lead",  # Mark as lead
            "_lead_status": lead_data.get("Lead_Status"),
        }

    async def _upsert_contact(
        self,
        connection_id: UUID,
        contact_data: Dict[str, Any],
        is_lead: bool = False,
    ) -> Tuple[bool, bool]:
        """
        Insert or update a contact.

        Returns:
            Tuple of (created, updated) booleans
        """
        crm_contact_id = str(contact_data.get("id"))

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
        email = contact_data.get("Email", "") or ""
        phone = contact_data.get("Phone") or contact_data.get("Mobile") or ""

        email_hashed = hash_email(email) if email else None
        phone_hashed = hash_phone(phone) if phone else None

        # Parse dates
        crm_created = None
        crm_updated = None
        if contact_data.get("Created_Time"):
            try:
                crm_created = datetime.fromisoformat(
                    contact_data["Created_Time"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass
        if contact_data.get("Modified_Time"):
            try:
                crm_updated = datetime.fromisoformat(
                    contact_data["Modified_Time"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        # Extract owner ID
        owner = contact_data.get("Owner")
        owner_id = None
        if isinstance(owner, dict):
            owner_id = owner.get("id")
        elif owner:
            owner_id = str(owner)

        # Extract account/company name
        account = contact_data.get("Account_Name")
        company_name = None
        if isinstance(account, dict):
            company_name = account.get("name")
        elif account:
            company_name = str(account)

        # Determine lifecycle stage
        lifecycle_stage = contact_data.get("_lifecycle_stage", "contact")
        if is_lead:
            lifecycle_stage = "lead"

        # Extract lead source
        lead_source = contact_data.get("Lead_Source")
        if isinstance(lead_source, dict):
            lead_source = lead_source.get("name")

        contact_fields = {
            "crm_owner_id": owner_id,
            "email_hash": email_hashed,
            "phone_hash": phone_hashed,
            "utm_source": contact_data.get("utm_source"),
            "utm_medium": contact_data.get("utm_medium"),
            "utm_campaign": contact_data.get("utm_campaign"),
            "utm_content": contact_data.get("utm_content"),
            "utm_term": contact_data.get("utm_term"),
            "gclid": contact_data.get("gclid"),
            "fbclid": contact_data.get("fbclid"),
            "ttclid": contact_data.get("ttclid"),
            "lifecycle_stage": lifecycle_stage,
            "lead_source": lead_source,
            "raw_properties": {
                "first_name": contact_data.get("First_Name"),
                "last_name": contact_data.get("Last_Name"),
                "email": email,
                "phone": phone,
                "company": company_name,
                "owner_id": owner_id,
            },
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
        modified_since: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Sync deals from Zoho CRM."""
        results = {"synced": 0, "created": 0, "updated": 0, "errors": []}
        page = 1

        fields = [
            "Deal_Name", "Amount", "Stage", "Pipeline",
            "Closing_Date", "Account_Name", "Contact_Name",
            "Owner", "Created_Time", "Modified_Time",
        ]

        async with self.client:
            while True:
                response = await self.client.get_deals(
                    page=page,
                    per_page=200,
                    fields=fields,
                    modified_since=modified_since,
                )

                if not response or "data" not in response:
                    break

                for deal_data in response["data"]:
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
                info = response.get("info", {})
                if not info.get("more_records", False):
                    break

                page += 1
                await self.db.commit()

        await self.db.commit()

        # Associate deals with contacts
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
        crm_deal_id = str(deal_data.get("id"))

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
        if deal_data.get("Amount"):
            try:
                amount = float(deal_data["Amount"])
                amount_cents = int(amount * 100)
            except (ValueError, TypeError):
                pass

        # Parse stage
        stage = deal_data.get("Stage", "")
        if isinstance(stage, dict):
            stage = stage.get("name", "")

        stage_lower = stage.lower().strip()
        stage_normalized = ZOHO_STAGE_MAPPING.get(stage_lower)

        # Determine if won/closed
        is_won = "won" in stage_lower
        is_closed = "closed" in stage_lower

        # Parse close date
        close_date = None
        if deal_data.get("Closing_Date"):
            try:
                close_date = datetime.fromisoformat(
                    deal_data["Closing_Date"]
                ).date()
            except (ValueError, TypeError):
                try:
                    # Try parsing YYYY-MM-DD format
                    close_date = datetime.strptime(
                        deal_data["Closing_Date"], "%Y-%m-%d"
                    ).date()
                except (ValueError, TypeError):
                    pass

        # Parse dates
        crm_created = None
        crm_updated = None
        if deal_data.get("Created_Time"):
            try:
                crm_created = datetime.fromisoformat(
                    deal_data["Created_Time"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass
        if deal_data.get("Modified_Time"):
            try:
                crm_updated = datetime.fromisoformat(
                    deal_data["Modified_Time"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        # Extract owner ID
        owner = deal_data.get("Owner")
        owner_id = None
        if isinstance(owner, dict):
            owner_id = owner.get("id")
        elif owner:
            owner_id = str(owner)

        # Extract pipeline
        pipeline = deal_data.get("Pipeline")
        pipeline_id = None
        if isinstance(pipeline, dict):
            pipeline_id = pipeline.get("id")
        elif pipeline:
            pipeline_id = str(pipeline)

        deal_fields = {
            "crm_pipeline_id": pipeline_id,
            "crm_owner_id": owner_id,
            "deal_name": deal_data.get("Deal_Name"),
            "stage": stage,
            "stage_normalized": stage_normalized,
            "amount": amount,
            "amount_cents": amount_cents,
            "close_date": close_date,
            "is_won": is_won,
            "is_closed": is_closed,
            "raw_properties": deal_data,
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
        """Associate deals with their contacts via Zoho API."""
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
                    # Get deal contacts from Zoho
                    contacts_response = await self.client.get_deal_contacts(
                        deal.crm_deal_id,
                    )

                    if contacts_response and contacts_response.get("data"):
                        # Get first associated contact
                        contact_data = contacts_response["data"][0]
                        zoho_contact_id = str(contact_data.get("id"))

                        # Find contact in our database
                        contact_result = await self.db.execute(
                            select(CRMContact).where(
                                and_(
                                    CRMContact.connection_id == connection_id,
                                    CRMContact.crm_contact_id == zoho_contact_id,
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
                        "zoho_deal_association_failed",
                        deal_id=deal.crm_deal_id,
                        error=str(e),
                    )

        await self.db.commit()

    async def _get_connection(self) -> Optional[CRMConnection]:
        """Get Zoho connection for tenant."""
        result = await self.db.execute(
            select(CRMConnection).where(
                and_(
                    CRMConnection.tenant_id == self.tenant_id,
                    CRMConnection.provider == CRMProvider.ZOHO,
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
            return {"status": "not_connected", "provider": "zoho"}

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
            "provider": "zoho",
            "stage_counts": stage_counts,
            "stage_values": stage_values,
            "total_pipeline_value": sum(stage_values.values()),
            "total_won_value": sum(d.amount or 0 for d in won_deals),
            "won_deal_count": len(won_deals),
            "last_sync_at": connection.last_sync_at.isoformat() if connection.last_sync_at else None,
        }

    async def sync_single_contact(self, zoho_contact_id: str) -> Dict[str, Any]:
        """
        Sync a single contact by ID.

        Args:
            zoho_contact_id: Zoho contact ID

        Returns:
            Sync result
        """
        connection = await self._get_connection()
        if not connection:
            return {"status": "error", "message": "Zoho not connected"}

        async with self.client:
            contact_data = await self.client.get_contact(zoho_contact_id)
            if not contact_data or "data" not in contact_data:
                return {"status": "error", "message": "Contact not found"}

            contact = contact_data["data"][0]
            created, updated = await self._upsert_contact(connection.id, contact)
            await self.db.commit()

            return {
                "status": "success",
                "created": created,
                "updated": updated,
                "contact_id": zoho_contact_id,
            }

    async def sync_single_deal(self, zoho_deal_id: str) -> Dict[str, Any]:
        """
        Sync a single deal by ID.

        Args:
            zoho_deal_id: Zoho deal ID

        Returns:
            Sync result
        """
        connection = await self._get_connection()
        if not connection:
            return {"status": "error", "message": "Zoho not connected"}

        async with self.client:
            deal_data = await self.client.get_deal(zoho_deal_id)
            if not deal_data or "data" not in deal_data:
                return {"status": "error", "message": "Deal not found"}

            deal = deal_data["data"][0]
            created, updated = await self._upsert_deal(connection.id, deal)
            await self.db.commit()

            return {
                "status": "success",
                "created": created,
                "updated": updated,
                "deal_id": zoho_deal_id,
            }
