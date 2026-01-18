# =============================================================================
# Stratum AI - Salesforce Sync Service
# =============================================================================
"""
Salesforce data synchronization service.
Syncs contacts, leads, and opportunities from Salesforce to CDP profiles.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.cdp import (
    CDPProfile,
    CDPProfileIdentifier,
    CDPEvent,
    LifecycleStage,
    IdentifierType,
)
from app.models.crm import CRMConnection, CRMSyncLog, CRMProvider
from app.services.cdp.identity_service import IdentityService
from .salesforce_client import SalesforceClient, hash_email, hash_phone

logger = get_logger(__name__)


# Salesforce stage to lifecycle stage mapping
STAGE_MAPPING = {
    "prospecting": LifecycleStage.KNOWN,
    "qualification": LifecycleStage.KNOWN,
    "needs analysis": LifecycleStage.ENGAGED,
    "value proposition": LifecycleStage.ENGAGED,
    "id. decision makers": LifecycleStage.ENGAGED,
    "perception analysis": LifecycleStage.ENGAGED,
    "proposal/price quote": LifecycleStage.ENGAGED,
    "negotiation/review": LifecycleStage.ENGAGED,
    "closed won": LifecycleStage.CUSTOMER,
    "closed lost": LifecycleStage.CHURNED,
}


class SalesforceSyncService:
    """
    Synchronizes Salesforce data with CDP profiles.

    Features:
    - Incremental sync based on update timestamps
    - Identity resolution for contact/lead->profile mapping
    - Opportunity attribution tracking
    - Sync status logging
    """

    def __init__(self, db: AsyncSession, tenant_id: int, is_sandbox: bool = False):
        self.db = db
        self.tenant_id = tenant_id
        self.client = SalesforceClient(db, tenant_id, is_sandbox)
        self.identity_service = IdentityService(db, tenant_id)

    async def sync_all(self, full_sync: bool = False) -> Dict[str, Any]:
        """
        Run full synchronization.

        Args:
            full_sync: If True, sync all data. Otherwise, incremental.

        Returns:
            Sync results summary
        """
        start_time = datetime.now(timezone.utc)
        results = {
            "contacts_synced": 0,
            "contacts_created": 0,
            "contacts_updated": 0,
            "leads_synced": 0,
            "leads_created": 0,
            "leads_updated": 0,
            "opportunities_synced": 0,
            "opportunities_created": 0,
            "errors": [],
        }

        try:
            # Determine sync window
            since = None
            if not full_sync:
                connection = await self.client._get_connection()
                if connection and connection.last_sync_at:
                    since = connection.last_sync_at

            # Sync contacts first
            contact_results = await self._sync_contacts(since)
            results["contacts_synced"] = contact_results.get("contacts_synced", 0)
            results["contacts_created"] = contact_results.get("contacts_created", 0)
            results["contacts_updated"] = contact_results.get("contacts_updated", 0)

            # Sync leads
            lead_results = await self._sync_leads(since)
            results["leads_synced"] = lead_results.get("leads_synced", 0)
            results["leads_created"] = lead_results.get("leads_created", 0)
            results["leads_updated"] = lead_results.get("leads_updated", 0)

            # Sync opportunities
            opp_results = await self._sync_opportunities(since)
            results["opportunities_synced"] = opp_results.get("opportunities_synced", 0)
            results["opportunities_created"] = opp_results.get("opportunities_created", 0)

            # Update sync timestamp
            connection = await self.client._get_connection()
            if connection:
                connection.last_sync_at = start_time
                connection.last_sync_status = "success"
                await self.db.commit()

            # Log sync
            await self._log_sync(results, start_time, "success")

            logger.info(
                "salesforce_sync_complete",
                tenant_id=self.tenant_id,
                results=results,
            )

        except Exception as e:
            results["errors"].append(str(e))
            await self._log_sync(results, start_time, "failed", str(e))
            logger.error(
                "salesforce_sync_failed",
                tenant_id=self.tenant_id,
                error=str(e),
            )

        return results

    async def _sync_contacts(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        """Sync contacts from Salesforce."""
        results = {
            "contacts_synced": 0,
            "contacts_created": 0,
            "contacts_updated": 0,
        }

        offset = 0
        limit = 100
        has_more = True

        async with self.client:
            while has_more:
                response = await self.client.get_contacts(
                    limit=limit,
                    offset=offset,
                    modified_since=since,
                )

                if not response:
                    break

                records = response.get("records", [])
                if not records:
                    break

                for contact in records:
                    try:
                        created = await self._process_contact(contact)
                        results["contacts_synced"] += 1
                        if created:
                            results["contacts_created"] += 1
                        else:
                            results["contacts_updated"] += 1
                    except Exception as e:
                        logger.warning(
                            "salesforce_contact_sync_error",
                            contact_id=contact.get("Id"),
                            error=str(e),
                        )

                # Check pagination
                has_more = not response.get("done", True)
                offset += limit

                await self.db.flush()

        return results

    async def _process_contact(self, contact: Dict[str, Any]) -> bool:
        """
        Process a single Salesforce contact.

        Returns:
            True if created, False if updated
        """
        contact_id = contact.get("Id")
        email = contact.get("Email")
        phone = contact.get("Phone")

        # Build identifiers
        identifiers = []
        if email:
            identifiers.append({
                "type": IdentifierType.EMAIL.value,
                "value": email,
                "hash": hash_email(email),
            })
        if phone:
            identifiers.append({
                "type": IdentifierType.PHONE.value,
                "value": phone,
                "hash": hash_phone(phone),
            })

        # Add external ID
        identifiers.append({
            "type": IdentifierType.EXTERNAL_ID.value,
            "value": f"salesforce_contact:{contact_id}",
            "hash": f"salesforce_contact:{contact_id}",
        })

        if not identifiers:
            return False

        # Resolve or create profile
        profile = await self.identity_service.resolve_profile(identifiers)
        created = profile.created_at == profile.updated_at

        # Update profile data
        profile_data = profile.profile_data or {}
        profile_data.update({
            "salesforce_contact_id": contact_id,
            "first_name": contact.get("FirstName"),
            "last_name": contact.get("LastName"),
            "name": contact.get("Name"),
            "account_id": contact.get("AccountId"),
            "owner_id": contact.get("OwnerId"),
            "lead_source": contact.get("LeadSource"),
        })

        profile.profile_data = profile_data

        # Set lifecycle stage based on contact existence
        if email:
            profile.lifecycle_stage = LifecycleStage.KNOWN.value

        profile.last_seen_at = datetime.now(timezone.utc)

        return created

    async def _sync_leads(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        """Sync leads from Salesforce."""
        results = {
            "leads_synced": 0,
            "leads_created": 0,
            "leads_updated": 0,
        }

        offset = 0
        limit = 100
        has_more = True

        async with self.client:
            while has_more:
                response = await self.client.get_leads(
                    limit=limit,
                    offset=offset,
                    modified_since=since,
                )

                if not response:
                    break

                records = response.get("records", [])
                if not records:
                    break

                for lead in records:
                    try:
                        created = await self._process_lead(lead)
                        results["leads_synced"] += 1
                        if created:
                            results["leads_created"] += 1
                        else:
                            results["leads_updated"] += 1
                    except Exception as e:
                        logger.warning(
                            "salesforce_lead_sync_error",
                            lead_id=lead.get("Id"),
                            error=str(e),
                        )

                # Check pagination
                has_more = not response.get("done", True)
                offset += limit

                await self.db.flush()

        return results

    async def _process_lead(self, lead: Dict[str, Any]) -> bool:
        """
        Process a single Salesforce lead.

        Returns:
            True if created, False if updated
        """
        lead_id = lead.get("Id")
        email = lead.get("Email")
        phone = lead.get("Phone")

        # Build identifiers
        identifiers = []
        if email:
            identifiers.append({
                "type": IdentifierType.EMAIL.value,
                "value": email,
                "hash": hash_email(email),
            })
        if phone:
            identifiers.append({
                "type": IdentifierType.PHONE.value,
                "value": phone,
                "hash": hash_phone(phone),
            })

        # Add external ID
        identifiers.append({
            "type": IdentifierType.EXTERNAL_ID.value,
            "value": f"salesforce_lead:{lead_id}",
            "hash": f"salesforce_lead:{lead_id}",
        })

        if not identifiers:
            return False

        # Resolve or create profile
        profile = await self.identity_service.resolve_profile(identifiers)
        created = profile.created_at == profile.updated_at

        # Update profile data
        profile_data = profile.profile_data or {}
        profile_data.update({
            "salesforce_lead_id": lead_id,
            "first_name": lead.get("FirstName"),
            "last_name": lead.get("LastName"),
            "name": lead.get("Name"),
            "company": lead.get("Company"),
            "owner_id": lead.get("OwnerId"),
            "lead_source": lead.get("LeadSource"),
            "lead_status": lead.get("Status"),
        })

        profile.profile_data = profile_data

        # Set lifecycle stage based on lead status
        status = (lead.get("Status") or "").lower()
        if "converted" in status:
            profile.lifecycle_stage = LifecycleStage.CUSTOMER.value
        elif "qualified" in status:
            profile.lifecycle_stage = LifecycleStage.ENGAGED.value
        elif email:
            profile.lifecycle_stage = LifecycleStage.KNOWN.value

        profile.last_seen_at = datetime.now(timezone.utc)

        return created

    async def _sync_opportunities(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        """Sync opportunities from Salesforce."""
        results = {
            "opportunities_synced": 0,
            "opportunities_created": 0,
        }

        offset = 0
        limit = 100
        has_more = True

        async with self.client:
            while has_more:
                response = await self.client.get_opportunities(
                    limit=limit,
                    offset=offset,
                    modified_since=since,
                )

                if not response:
                    break

                records = response.get("records", [])
                if not records:
                    break

                for opp in records:
                    try:
                        await self._process_opportunity(opp)
                        results["opportunities_synced"] += 1
                        results["opportunities_created"] += 1
                    except Exception as e:
                        logger.warning(
                            "salesforce_opportunity_sync_error",
                            opp_id=opp.get("Id"),
                            error=str(e),
                        )

                # Check pagination
                has_more = not response.get("done", True)
                offset += limit

                await self.db.flush()

        return results

    async def _process_opportunity(self, opp: Dict[str, Any]) -> None:
        """Process a single Salesforce opportunity."""
        opp_id = opp.get("Id")
        account_id = opp.get("AccountId")

        if not account_id:
            return

        # Find profile by Salesforce account ID (through contact)
        profile = await self._find_profile_by_salesforce_account(account_id)
        if not profile:
            # Try to find via opportunity contact roles
            contact_roles = await self.client.get_opportunity_contact_roles(opp_id)
            if contact_roles and contact_roles.get("records"):
                for role in contact_roles.get("records", []):
                    contact_id = role.get("ContactId")
                    if contact_id:
                        profile = await self._find_profile_by_salesforce_id(
                            f"salesforce_contact:{contact_id}"
                        )
                        if profile:
                            break

        if not profile:
            return

        # Create opportunity event
        event = CDPEvent(
            tenant_id=self.tenant_id,
            profile_id=profile.id,
            event_name="SalesforceOpportunity",
            event_time=datetime.now(timezone.utc),
            received_at=datetime.now(timezone.utc),
            idempotency_key=f"salesforce_opp_{opp_id}",
            properties={
                "opportunity_id": opp_id,
                "opportunity_name": opp.get("Name"),
                "amount": opp.get("Amount"),
                "stage": opp.get("StageName"),
                "probability": opp.get("Probability"),
                "is_closed": opp.get("IsClosed"),
                "is_won": opp.get("IsWon"),
                "close_date": opp.get("CloseDate"),
                "lead_source": opp.get("LeadSource"),
            },
            context={
                "source": "salesforce",
                "sync_type": "crm_sync",
            },
            processed=True,
        )

        self.db.add(event)

        # Update profile revenue if opportunity is won
        if opp.get("IsWon") and opp.get("Amount"):
            profile.total_purchases = (profile.total_purchases or 0) + 1
            profile.total_revenue = (profile.total_revenue or 0) + float(opp.get("Amount", 0))
            profile.lifecycle_stage = LifecycleStage.CUSTOMER.value

        # Update lifecycle stage based on opportunity stage
        stage = (opp.get("StageName") or "").lower()
        mapped_stage = STAGE_MAPPING.get(stage)
        if mapped_stage:
            profile.lifecycle_stage = mapped_stage.value

    async def _find_profile_by_salesforce_id(self, external_id: str) -> Optional[CDPProfile]:
        """Find CDP profile by Salesforce external ID."""
        result = await self.db.execute(
            select(CDPProfileIdentifier).where(
                CDPProfileIdentifier.tenant_id == self.tenant_id,
                CDPProfileIdentifier.identifier_type == IdentifierType.EXTERNAL_ID.value,
                CDPProfileIdentifier.identifier_hash == external_id,
            )
        )
        identifier = result.scalar_one_or_none()

        if identifier:
            result = await self.db.execute(
                select(CDPProfile).where(CDPProfile.id == identifier.profile_id)
            )
            return result.scalar_one_or_none()

        return None

    async def _find_profile_by_salesforce_account(self, account_id: str) -> Optional[CDPProfile]:
        """Find CDP profile by Salesforce account ID."""
        # Search for any profile with this account_id in profile_data
        result = await self.db.execute(
            select(CDPProfile).where(
                CDPProfile.tenant_id == self.tenant_id,
                CDPProfile.profile_data["account_id"].astext == account_id,
            )
        )
        return result.scalar_one_or_none()

    async def _log_sync(
        self,
        results: Dict[str, Any],
        start_time: datetime,
        status: str,
        error: Optional[str] = None,
    ) -> None:
        """Log sync results."""
        duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

        log = CRMSyncLog(
            tenant_id=self.tenant_id,
            provider=CRMProvider.SALESFORCE,
            sync_type="full",
            status=status,
            started_at=start_time,
            completed_at=datetime.now(timezone.utc),
            duration_ms=duration_ms,
            records_processed=(
                results.get("contacts_synced", 0) +
                results.get("leads_synced", 0) +
                results.get("opportunities_synced", 0)
            ),
            records_created=(
                results.get("contacts_created", 0) +
                results.get("leads_created", 0) +
                results.get("opportunities_created", 0)
            ),
            records_updated=(
                results.get("contacts_updated", 0) +
                results.get("leads_updated", 0)
            ),
            records_failed=len(results.get("errors", [])),
            error_message=error,
            metadata=results,
        )

        self.db.add(log)
        await self.db.flush()

    async def get_pipeline_summary(self) -> Dict[str, Any]:
        """Get pipeline summary from Salesforce opportunities."""
        async with self.client:
            # Get open opportunities
            open_opps = await self.client.query(
                "SELECT StageName, COUNT(Id) cnt, SUM(Amount) total "
                "FROM Opportunity WHERE IsClosed = false "
                "GROUP BY StageName"
            )

            # Get won opportunities this year
            won_opps = await self.client.query(
                "SELECT COUNT(Id) cnt, SUM(Amount) total "
                "FROM Opportunity WHERE IsWon = true "
                "AND CloseDate = THIS_YEAR"
            )

        stage_counts = {}
        stage_values = {}
        total_pipeline_value = 0

        if open_opps and open_opps.get("records"):
            for record in open_opps["records"]:
                stage = record.get("StageName", "Unknown")
                stage_counts[stage] = record.get("cnt", 0)
                stage_values[stage] = record.get("total", 0) or 0
                total_pipeline_value += stage_values[stage]

        total_won_value = 0
        won_deal_count = 0

        if won_opps and won_opps.get("records"):
            record = won_opps["records"][0]
            won_deal_count = record.get("cnt", 0)
            total_won_value = record.get("total", 0) or 0

        connection = await self.client._get_connection()

        return {
            "status": "success",
            "stage_counts": stage_counts,
            "stage_values": stage_values,
            "total_pipeline_value": total_pipeline_value,
            "total_won_value": total_won_value,
            "won_deal_count": won_deal_count,
            "last_sync_at": connection.last_sync_at.isoformat() if connection and connection.last_sync_at else None,
        }
