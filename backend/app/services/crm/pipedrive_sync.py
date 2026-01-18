# =============================================================================
# Stratum AI - Pipedrive Sync Service
# =============================================================================
"""
Pipedrive data synchronization service.
Syncs persons and deals from Pipedrive to CDP profiles.
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
from .pipedrive_client import PipedriveClient, hash_email, hash_phone

logger = get_logger(__name__)


class PipedriveSyncService:
    """
    Synchronizes Pipedrive data with CDP profiles.

    Features:
    - Incremental sync based on update timestamps
    - Identity resolution for person->profile mapping
    - Deal attribution tracking
    - Sync status logging
    """

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.client = PipedriveClient(db, tenant_id)
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
            "persons_synced": 0,
            "persons_created": 0,
            "persons_updated": 0,
            "deals_synced": 0,
            "deals_created": 0,
            "errors": [],
        }

        try:
            # Determine sync window
            since = None
            if not full_sync:
                connection = await self.client._get_connection()
                if connection and connection.last_sync_at:
                    since = connection.last_sync_at

            # Sync persons first (contacts)
            person_results = await self._sync_persons(since)
            results.update(person_results)

            # Sync deals
            deal_results = await self._sync_deals(since)
            results.update(deal_results)

            # Update sync timestamp
            connection = await self.client._get_connection()
            if connection:
                connection.last_sync_at = start_time
                connection.last_sync_status = "success"
                await self.db.commit()

            # Log sync
            await self._log_sync(results, start_time, "success")

            logger.info(
                "pipedrive_sync_complete",
                tenant_id=self.tenant_id,
                results=results,
            )

        except Exception as e:
            results["errors"].append(str(e))
            await self._log_sync(results, start_time, "failed", str(e))
            logger.error(
                "pipedrive_sync_failed",
                tenant_id=self.tenant_id,
                error=str(e),
            )

        return results

    async def _sync_persons(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        """Sync persons from Pipedrive."""
        results = {
            "persons_synced": 0,
            "persons_created": 0,
            "persons_updated": 0,
        }

        start = 0
        limit = 100
        has_more = True

        async with self.client:
            while has_more:
                response = await self.client.get_persons(
                    limit=limit,
                    start=start,
                    updated_since=since,
                )

                if not response or not response.get("success"):
                    break

                data = response.get("data", [])
                if not data:
                    break

                for person in data:
                    try:
                        created = await self._process_person(person)
                        results["persons_synced"] += 1
                        if created:
                            results["persons_created"] += 1
                        else:
                            results["persons_updated"] += 1
                    except Exception as e:
                        logger.warning(
                            "pipedrive_person_sync_error",
                            person_id=person.get("id"),
                            error=str(e),
                        )

                # Check pagination
                additional_data = response.get("additional_data", {})
                pagination = additional_data.get("pagination", {})
                has_more = pagination.get("more_items_in_collection", False)
                start = pagination.get("next_start", start + limit)

                await self.db.flush()

        return results

    async def _process_person(self, person: Dict[str, Any]) -> bool:
        """
        Process a single Pipedrive person.

        Returns:
            True if created, False if updated
        """
        person_id = person.get("id")
        email = None
        phone = None

        # Extract email
        emails = person.get("email", [])
        if emails and isinstance(emails, list) and emails[0]:
            email_obj = emails[0]
            email = email_obj.get("value") if isinstance(email_obj, dict) else email_obj

        # Extract phone
        phones = person.get("phone", [])
        if phones and isinstance(phones, list) and phones[0]:
            phone_obj = phones[0]
            phone = phone_obj.get("value") if isinstance(phone_obj, dict) else phone_obj

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
            "value": f"pipedrive:{person_id}",
            "hash": f"pipedrive:{person_id}",
        })

        if not identifiers:
            return False

        # Resolve or create profile
        profile = await self.identity_service.resolve_profile(identifiers)
        created = profile.created_at == profile.updated_at

        # Update profile data
        profile_data = profile.profile_data or {}
        profile_data.update({
            "pipedrive_id": person_id,
            "first_name": person.get("first_name"),
            "last_name": person.get("last_name"),
            "name": person.get("name"),
            "org_id": person.get("org_id"),
            "org_name": person.get("org_name"),
            "owner_id": person.get("owner_id"),
        })

        # Add custom fields if present
        for key, value in person.items():
            if key.startswith("pipedrive_") or key in ["email", "phone"]:
                continue
            if isinstance(value, (str, int, float, bool)) and value is not None:
                profile_data[f"pipedrive_{key}"] = value

        profile.profile_data = profile_data

        # Update lifecycle stage based on person status
        if person.get("open_deals_count", 0) > 0:
            profile.lifecycle_stage = LifecycleStage.CUSTOMER.value
        elif email:
            profile.lifecycle_stage = LifecycleStage.KNOWN.value

        profile.last_seen_at = datetime.now(timezone.utc)

        return created

    async def _sync_deals(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        """Sync deals from Pipedrive."""
        results = {
            "deals_synced": 0,
            "deals_created": 0,
        }

        start = 0
        limit = 100
        has_more = True

        async with self.client:
            while has_more:
                response = await self.client.get_deals(
                    limit=limit,
                    start=start,
                    updated_since=since,
                )

                if not response or not response.get("success"):
                    break

                data = response.get("data", [])
                if not data:
                    break

                for deal in data:
                    try:
                        await self._process_deal(deal)
                        results["deals_synced"] += 1
                        results["deals_created"] += 1
                    except Exception as e:
                        logger.warning(
                            "pipedrive_deal_sync_error",
                            deal_id=deal.get("id"),
                            error=str(e),
                        )

                # Check pagination
                additional_data = response.get("additional_data", {})
                pagination = additional_data.get("pagination", {})
                has_more = pagination.get("more_items_in_collection", False)
                start = pagination.get("next_start", start + limit)

                await self.db.flush()

        return results

    async def _process_deal(self, deal: Dict[str, Any]) -> None:
        """Process a single Pipedrive deal."""
        deal_id = deal.get("id")
        person_id = deal.get("person_id")

        if not person_id:
            return

        # Find profile by Pipedrive person ID
        profile = await self._find_profile_by_pipedrive_id(person_id)
        if not profile:
            return

        # Create deal event
        event = CDPEvent(
            tenant_id=self.tenant_id,
            profile_id=profile.id,
            event_name="PipedriveDeal",
            event_time=datetime.now(timezone.utc),
            received_at=datetime.now(timezone.utc),
            idempotency_key=f"pipedrive_deal_{deal_id}",
            properties={
                "deal_id": deal_id,
                "deal_title": deal.get("title"),
                "deal_value": deal.get("value"),
                "deal_currency": deal.get("currency"),
                "deal_status": deal.get("status"),
                "deal_stage_id": deal.get("stage_id"),
                "deal_pipeline_id": deal.get("pipeline_id"),
                "won_time": deal.get("won_time"),
                "lost_time": deal.get("lost_time"),
                "close_time": deal.get("close_time"),
            },
            context={
                "source": "pipedrive",
                "sync_type": "crm_sync",
            },
            processed=True,
        )

        self.db.add(event)

        # Update profile revenue if deal is won
        if deal.get("status") == "won" and deal.get("value"):
            profile.total_purchases = (profile.total_purchases or 0) + 1
            profile.total_revenue = (profile.total_revenue or 0) + float(deal.get("value", 0))
            profile.lifecycle_stage = LifecycleStage.CUSTOMER.value

    async def _find_profile_by_pipedrive_id(self, person_id: int) -> Optional[CDPProfile]:
        """Find CDP profile by Pipedrive person ID."""
        # Look for external ID identifier
        result = await self.db.execute(
            select(CDPProfileIdentifier).where(
                CDPProfileIdentifier.tenant_id == self.tenant_id,
                CDPProfileIdentifier.identifier_type == IdentifierType.EXTERNAL_ID.value,
                CDPProfileIdentifier.identifier_hash == f"pipedrive:{person_id}",
            )
        )
        identifier = result.scalar_one_or_none()

        if identifier:
            result = await self.db.execute(
                select(CDPProfile).where(CDPProfile.id == identifier.profile_id)
            )
            return result.scalar_one_or_none()

        return None

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
            provider=CRMProvider.PIPEDRIVE,
            sync_type="full",
            status=status,
            started_at=start_time,
            completed_at=datetime.now(timezone.utc),
            duration_ms=duration_ms,
            records_processed=results.get("persons_synced", 0) + results.get("deals_synced", 0),
            records_created=results.get("persons_created", 0) + results.get("deals_created", 0),
            records_updated=results.get("persons_updated", 0),
            records_failed=len(results.get("errors", [])),
            error_message=error,
            metadata=results,
        )

        self.db.add(log)
        await self.db.flush()
