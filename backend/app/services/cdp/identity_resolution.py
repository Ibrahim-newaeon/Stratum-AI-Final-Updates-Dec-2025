# =============================================================================
# Stratum AI - CDP Identity Resolution Service
# =============================================================================
"""
Identity resolution and profile merging for CDP.

This service handles:
- Identity graph management (linking identifiers)
- Priority-based identity resolution
- Profile merging when same person is detected
- Cross-session anonymous ID linking
- Canonical identity management
"""

import hashlib
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Tuple, Set
from uuid import UUID

import structlog
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cdp import (
    CDPProfile,
    CDPProfileIdentifier,
    CDPEvent,
    CDPConsent,
    CDPIdentityLink,
    CDPProfileMerge,
    CDPCanonicalIdentity,
    IdentityLinkType,
    MergeReason,
    LifecycleStage,
    IDENTITY_PRIORITY,
)

logger = structlog.get_logger()


class IdentityResolutionService:
    """
    Service for identity resolution and profile merging.

    Identity Resolution Flow:
    1. Event arrives with identifiers
    2. Check if any identifier matches existing profile
    3. If multiple profiles match, merge them
    4. Link all identifiers in the event
    5. Update canonical identity based on priority
    """

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    # =========================================================================
    # Identity Priority Resolution
    # =========================================================================

    def get_identifier_priority(self, identifier_type: str) -> int:
        """Get priority score for an identifier type."""
        return IDENTITY_PRIORITY.get(identifier_type.lower(), 0)

    def get_strongest_identifier(
        self,
        identifiers: List[CDPProfileIdentifier]
    ) -> Optional[CDPProfileIdentifier]:
        """Get the strongest (highest priority) identifier from a list."""
        if not identifiers:
            return None

        return max(
            identifiers,
            key=lambda i: (
                self.get_identifier_priority(i.identifier_type),
                i.is_primary,
                i.confidence_score,
            )
        )

    async def determine_surviving_profile(
        self,
        profile_a: CDPProfile,
        profile_b: CDPProfile,
    ) -> Tuple[CDPProfile, CDPProfile]:
        """
        Determine which profile should survive in a merge.

        Rules (in order):
        1. Profile with higher priority canonical identity wins
        2. Profile with more events wins
        3. Profile created first wins

        Returns: (surviving_profile, merged_profile)
        """
        # Get canonical identities
        canonical_a = await self._get_canonical_identity(profile_a.id)
        canonical_b = await self._get_canonical_identity(profile_b.id)

        priority_a = canonical_a.priority_score if canonical_a else 0
        priority_b = canonical_b.priority_score if canonical_b else 0

        # Compare by priority first
        if priority_a != priority_b:
            if priority_a > priority_b:
                return profile_a, profile_b
            return profile_b, profile_a

        # Then by event count
        if profile_a.total_events != profile_b.total_events:
            if profile_a.total_events > profile_b.total_events:
                return profile_a, profile_b
            return profile_b, profile_a

        # Finally by creation time (older wins)
        if profile_a.created_at <= profile_b.created_at:
            return profile_a, profile_b
        return profile_b, profile_a

    async def _get_canonical_identity(
        self,
        profile_id: UUID
    ) -> Optional[CDPCanonicalIdentity]:
        """Get canonical identity for a profile."""
        result = await self.db.execute(
            select(CDPCanonicalIdentity)
            .where(
                CDPCanonicalIdentity.tenant_id == self.tenant_id,
                CDPCanonicalIdentity.profile_id == profile_id,
            )
        )
        return result.scalar_one_or_none()

    # =========================================================================
    # Identity Linking
    # =========================================================================

    async def link_identifiers(
        self,
        identifiers: List[CDPProfileIdentifier],
        link_type: IdentityLinkType = IdentityLinkType.SAME_EVENT,
        evidence: Optional[Dict] = None,
    ) -> List[CDPIdentityLink]:
        """
        Create links between all identifiers (they appeared together).

        Creates bidirectional links between all pairs of identifiers.
        """
        if len(identifiers) < 2:
            return []

        evidence = evidence or {}
        created_links = []

        # Create links between all pairs
        for i, source in enumerate(identifiers):
            for target in identifiers[i + 1:]:
                # Check if link already exists
                existing = await self.db.execute(
                    select(CDPIdentityLink)
                    .where(
                        CDPIdentityLink.tenant_id == self.tenant_id,
                        or_(
                            and_(
                                CDPIdentityLink.source_identifier_id == source.id,
                                CDPIdentityLink.target_identifier_id == target.id,
                            ),
                            and_(
                                CDPIdentityLink.source_identifier_id == target.id,
                                CDPIdentityLink.target_identifier_id == source.id,
                            ),
                        ),
                    )
                )

                if existing.scalar_one_or_none():
                    continue

                # Calculate confidence based on identifier types
                source_priority = self.get_identifier_priority(source.identifier_type)
                target_priority = self.get_identifier_priority(target.identifier_type)
                confidence = min(source_priority, target_priority) / 100.0
                confidence = max(0.5, min(1.0, confidence))  # Clamp between 0.5 and 1.0

                # Create bidirectional link (source -> target)
                link = CDPIdentityLink(
                    tenant_id=self.tenant_id,
                    source_identifier_id=source.id,
                    target_identifier_id=target.id,
                    link_type=link_type.value,
                    confidence_score=Decimal(str(round(confidence, 2))),
                    evidence=evidence,
                )
                self.db.add(link)
                created_links.append(link)

        if created_links:
            await self.db.flush()
            logger.info(
                "cdp_identity_links_created",
                tenant_id=self.tenant_id,
                link_count=len(created_links),
                link_type=link_type.value,
            )

        return created_links

    async def link_anonymous_to_known(
        self,
        anonymous_identifier: CDPProfileIdentifier,
        known_identifier: CDPProfileIdentifier,
        link_type: IdentityLinkType = IdentityLinkType.LOGIN,
        evidence: Optional[Dict] = None,
    ) -> Optional[CDPIdentityLink]:
        """
        Link an anonymous identifier to a known identifier (login event).

        This is typically called when a user logs in, linking their
        anonymous_id to their email/customer_id.
        """
        if anonymous_identifier.identifier_type != "anonymous_id":
            logger.warning(
                "cdp_link_anonymous_wrong_type",
                actual_type=anonymous_identifier.identifier_type,
            )
            return None

        evidence = evidence or {}
        evidence["link_reason"] = "anonymous_to_known"

        links = await self.link_identifiers(
            [anonymous_identifier, known_identifier],
            link_type=link_type,
            evidence=evidence,
        )

        return links[0] if links else None

    # =========================================================================
    # Profile Merging
    # =========================================================================

    async def find_profiles_to_merge(
        self,
        identifier_type: str,
        identifier_hash: str,
    ) -> List[CDPProfile]:
        """
        Find all profiles that have a specific identifier.

        If multiple profiles share an identifier, they should be merged.
        """
        result = await self.db.execute(
            select(CDPProfile)
            .join(CDPProfileIdentifier)
            .where(
                CDPProfileIdentifier.tenant_id == self.tenant_id,
                CDPProfileIdentifier.identifier_type == identifier_type,
                CDPProfileIdentifier.identifier_hash == identifier_hash,
            )
            .options(selectinload(CDPProfile.identifiers))
        )
        return list(result.scalars().unique().all())

    async def merge_profiles(
        self,
        surviving_profile: CDPProfile,
        merged_profile: CDPProfile,
        merge_reason: MergeReason = MergeReason.IDENTITY_MATCH,
        triggering_identifier: Optional[CDPProfileIdentifier] = None,
        merged_by_user_id: Optional[int] = None,
    ) -> CDPProfileMerge:
        """
        Merge two profiles into one.

        Steps:
        1. Create snapshot of merged profile
        2. Move all identifiers to surviving profile
        3. Move all events to surviving profile
        4. Move all consents to surviving profile
        5. Update surviving profile counters
        6. Delete merged profile
        7. Record merge in history
        """
        logger.info(
            "cdp_profile_merge_started",
            tenant_id=self.tenant_id,
            surviving_profile_id=str(surviving_profile.id),
            merged_profile_id=str(merged_profile.id),
            merge_reason=merge_reason.value,
        )

        # 1. Create snapshot of merged profile
        snapshot = {
            "id": str(merged_profile.id),
            "external_id": merged_profile.external_id,
            "lifecycle_stage": merged_profile.lifecycle_stage,
            "total_events": merged_profile.total_events,
            "total_sessions": merged_profile.total_sessions,
            "total_purchases": merged_profile.total_purchases,
            "total_revenue": float(merged_profile.total_revenue),
            "profile_data": merged_profile.profile_data,
            "computed_traits": merged_profile.computed_traits,
            "first_seen_at": merged_profile.first_seen_at.isoformat() if merged_profile.first_seen_at else None,
            "last_seen_at": merged_profile.last_seen_at.isoformat() if merged_profile.last_seen_at else None,
            "identifier_count": len(merged_profile.identifiers) if merged_profile.identifiers else 0,
        }

        # 2. Move identifiers to surviving profile
        await self.db.execute(
            update(CDPProfileIdentifier)
            .where(CDPProfileIdentifier.profile_id == merged_profile.id)
            .values(profile_id=surviving_profile.id)
        )

        # 3. Move events to surviving profile
        await self.db.execute(
            update(CDPEvent)
            .where(CDPEvent.profile_id == merged_profile.id)
            .values(profile_id=surviving_profile.id)
        )

        # 4. Move consents (or merge them)
        # Get consents from merged profile
        merged_consents_result = await self.db.execute(
            select(CDPConsent)
            .where(CDPConsent.profile_id == merged_profile.id)
        )
        merged_consents = merged_consents_result.scalars().all()

        for consent in merged_consents:
            # Check if surviving profile has same consent type
            existing_result = await self.db.execute(
                select(CDPConsent)
                .where(
                    CDPConsent.profile_id == surviving_profile.id,
                    CDPConsent.consent_type == consent.consent_type,
                )
            )
            existing = existing_result.scalar_one_or_none()

            if existing:
                # Keep the most recent consent decision
                if consent.updated_at > existing.updated_at:
                    existing.granted = consent.granted
                    existing.granted_at = consent.granted_at
                    existing.revoked_at = consent.revoked_at
                # Delete the merged consent
                await self.db.delete(consent)
            else:
                # Move consent to surviving profile
                consent.profile_id = surviving_profile.id

        # 5. Update surviving profile counters
        surviving_profile.total_events += merged_profile.total_events
        surviving_profile.total_sessions += merged_profile.total_sessions
        surviving_profile.total_purchases += merged_profile.total_purchases
        surviving_profile.total_revenue += merged_profile.total_revenue

        # Update first_seen_at to earliest
        if merged_profile.first_seen_at and (
            not surviving_profile.first_seen_at or
            merged_profile.first_seen_at < surviving_profile.first_seen_at
        ):
            surviving_profile.first_seen_at = merged_profile.first_seen_at

        # Update last_seen_at to latest
        if merged_profile.last_seen_at and (
            not surviving_profile.last_seen_at or
            merged_profile.last_seen_at > surviving_profile.last_seen_at
        ):
            surviving_profile.last_seen_at = merged_profile.last_seen_at

        # Merge profile_data (surviving takes precedence)
        merged_data = {**merged_profile.profile_data, **surviving_profile.profile_data}
        surviving_profile.profile_data = merged_data

        # Update lifecycle stage to most advanced
        lifecycle_order = {
            LifecycleStage.ANONYMOUS.value: 0,
            LifecycleStage.KNOWN.value: 1,
            LifecycleStage.CUSTOMER.value: 2,
            LifecycleStage.CHURNED.value: 1,  # Churned is at known level
        }
        surviving_stage = lifecycle_order.get(surviving_profile.lifecycle_stage, 0)
        merged_stage = lifecycle_order.get(merged_profile.lifecycle_stage, 0)
        if merged_stage > surviving_stage:
            surviving_profile.lifecycle_stage = merged_profile.lifecycle_stage

        # 6. Record merge in history
        merge_record = CDPProfileMerge(
            tenant_id=self.tenant_id,
            surviving_profile_id=surviving_profile.id,
            merged_profile_id=merged_profile.id,
            merge_reason=merge_reason.value,
            merged_profile_snapshot=snapshot,
            triggering_identifier_type=triggering_identifier.identifier_type if triggering_identifier else None,
            triggering_identifier_hash=triggering_identifier.identifier_hash if triggering_identifier else None,
            merged_event_count=merged_profile.total_events,
            merged_identifier_count=snapshot.get("identifier_count", 0),
            merged_by_user_id=merged_by_user_id,
        )
        self.db.add(merge_record)

        # 7. Delete merged profile
        await self.db.delete(merged_profile)

        await self.db.flush()

        logger.info(
            "cdp_profile_merge_completed",
            tenant_id=self.tenant_id,
            surviving_profile_id=str(surviving_profile.id),
            merged_profile_id=str(merged_profile.id),
            events_merged=merged_profile.total_events,
        )

        # 8. Update canonical identity for surviving profile
        await self.update_canonical_identity(surviving_profile.id)

        return merge_record

    async def resolve_and_merge(
        self,
        identifier_type: str,
        identifier_hash: str,
    ) -> Optional[CDPProfileMerge]:
        """
        Find profiles with matching identifier and merge if needed.

        Returns the merge record if a merge occurred, None otherwise.
        """
        profiles = await self.find_profiles_to_merge(identifier_type, identifier_hash)

        if len(profiles) < 2:
            return None

        # Sort profiles and merge all into the first (surviving)
        # This handles cases where more than 2 profiles need merging
        surviving, *to_merge = sorted(
            profiles,
            key=lambda p: (
                -self.get_identifier_priority(
                    p.identifiers[0].identifier_type if p.identifiers else "anonymous_id"
                ),
                -p.total_events,
                p.created_at,
            )
        )

        merge_records = []
        for profile in to_merge:
            merge = await self.merge_profiles(
                surviving,
                profile,
                merge_reason=MergeReason.IDENTITY_MATCH,
            )
            merge_records.append(merge)

        return merge_records[0] if merge_records else None

    # =========================================================================
    # Canonical Identity Management
    # =========================================================================

    async def update_canonical_identity(self, profile_id: UUID) -> CDPCanonicalIdentity:
        """
        Update or create the canonical identity for a profile.

        Selects the strongest identifier as the canonical identity.
        """
        # Get all identifiers for the profile
        result = await self.db.execute(
            select(CDPProfileIdentifier)
            .where(
                CDPProfileIdentifier.tenant_id == self.tenant_id,
                CDPProfileIdentifier.profile_id == profile_id,
            )
        )
        identifiers = result.scalars().all()

        # Find the strongest identifier
        strongest = self.get_strongest_identifier(identifiers)

        if not strongest:
            return None

        priority_score = self.get_identifier_priority(strongest.identifier_type)

        # Get or create canonical identity
        existing = await self._get_canonical_identity(profile_id)

        if existing:
            existing.canonical_identifier_id = strongest.id
            existing.canonical_type = strongest.identifier_type
            existing.canonical_value_hash = strongest.identifier_hash
            existing.priority_score = priority_score
            existing.is_verified = strongest.verified_at is not None
            existing.verified_at = strongest.verified_at
            existing.updated_at = datetime.now(timezone.utc)
            canonical = existing
        else:
            canonical = CDPCanonicalIdentity(
                tenant_id=self.tenant_id,
                profile_id=profile_id,
                canonical_identifier_id=strongest.id,
                canonical_type=strongest.identifier_type,
                canonical_value_hash=strongest.identifier_hash,
                priority_score=priority_score,
                is_verified=strongest.verified_at is not None,
                verified_at=strongest.verified_at,
            )
            self.db.add(canonical)

        await self.db.flush()

        logger.debug(
            "cdp_canonical_identity_updated",
            tenant_id=self.tenant_id,
            profile_id=str(profile_id),
            canonical_type=strongest.identifier_type,
            priority_score=priority_score,
        )

        return canonical

    # =========================================================================
    # Identity Graph Traversal
    # =========================================================================

    async def get_linked_identifiers(
        self,
        identifier_id: UUID,
        max_depth: int = 3,
    ) -> List[CDPProfileIdentifier]:
        """
        Get all identifiers linked to a given identifier (graph traversal).

        Uses BFS to traverse the identity graph up to max_depth.
        """
        visited: Set[UUID] = {identifier_id}
        to_visit = [identifier_id]
        depth = 0

        while to_visit and depth < max_depth:
            current_batch = to_visit
            to_visit = []

            for current_id in current_batch:
                # Find all linked identifiers
                result = await self.db.execute(
                    select(CDPIdentityLink)
                    .where(
                        CDPIdentityLink.tenant_id == self.tenant_id,
                        CDPIdentityLink.is_active == True,
                        or_(
                            CDPIdentityLink.source_identifier_id == current_id,
                            CDPIdentityLink.target_identifier_id == current_id,
                        ),
                    )
                )
                links = result.scalars().all()

                for link in links:
                    # Get the "other" identifier in the link
                    other_id = (
                        link.target_identifier_id
                        if link.source_identifier_id == current_id
                        else link.source_identifier_id
                    )

                    if other_id not in visited:
                        visited.add(other_id)
                        to_visit.append(other_id)

            depth += 1

        # Fetch all visited identifiers
        if len(visited) <= 1:
            return []

        result = await self.db.execute(
            select(CDPProfileIdentifier)
            .where(CDPProfileIdentifier.id.in_(list(visited)))
        )
        return list(result.scalars().all())

    async def get_identity_graph(
        self,
        profile_id: UUID,
    ) -> Dict:
        """
        Get the full identity graph for a profile.

        Returns nodes (identifiers) and edges (links).
        """
        # Get all identifiers for the profile
        result = await self.db.execute(
            select(CDPProfileIdentifier)
            .where(
                CDPProfileIdentifier.tenant_id == self.tenant_id,
                CDPProfileIdentifier.profile_id == profile_id,
            )
        )
        identifiers = result.scalars().all()

        if not identifiers:
            return {"nodes": [], "edges": []}

        identifier_ids = [i.id for i in identifiers]

        # Get all links involving these identifiers
        result = await self.db.execute(
            select(CDPIdentityLink)
            .where(
                CDPIdentityLink.tenant_id == self.tenant_id,
                or_(
                    CDPIdentityLink.source_identifier_id.in_(identifier_ids),
                    CDPIdentityLink.target_identifier_id.in_(identifier_ids),
                ),
            )
        )
        links = result.scalars().all()

        # Build graph representation
        nodes = [
            {
                "id": str(i.id),
                "type": i.identifier_type,
                "hash": i.identifier_hash[:8] + "...",
                "is_primary": i.is_primary,
                "priority": self.get_identifier_priority(i.identifier_type),
            }
            for i in identifiers
        ]

        edges = [
            {
                "source": str(l.source_identifier_id),
                "target": str(l.target_identifier_id),
                "type": l.link_type,
                "confidence": float(l.confidence_score),
            }
            for l in links
        ]

        return {"nodes": nodes, "edges": edges}


# =============================================================================
# Utility Functions
# =============================================================================

async def resolve_identity_on_event(
    db: AsyncSession,
    tenant_id: int,
    profile: CDPProfile,
    identifiers: List[CDPProfileIdentifier],
    event_id: Optional[UUID] = None,
) -> Optional[CDPProfileMerge]:
    """
    Resolve identity after an event is ingested.

    Called after event ingestion to:
    1. Link identifiers that appeared together
    2. Check for profile merges needed
    3. Update canonical identity
    """
    service = IdentityResolutionService(db, tenant_id)

    # Link all identifiers from this event
    await service.link_identifiers(
        identifiers,
        link_type=IdentityLinkType.SAME_EVENT,
        evidence={"event_id": str(event_id)} if event_id else {},
    )

    # Check for potential merges
    merge_result = None
    for identifier in identifiers:
        merge = await service.resolve_and_merge(
            identifier.identifier_type,
            identifier.identifier_hash,
        )
        if merge:
            merge_result = merge

    # Update canonical identity
    await service.update_canonical_identity(profile.id)

    return merge_result
