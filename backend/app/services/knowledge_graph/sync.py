"""
Knowledge Graph Sync Service

Synchronizes data from CDP and Trust Engine into the Knowledge Graph.
Provides real-time and batch sync capabilities.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    NodeLabel,
    EdgeLabel,
    ProfileNode,
    EventNode,
    SignalNode,
    TrustGateNode,
    AutomationNode,
    RevenueNode,
    CampaignNode,
    SegmentNode,
    ChannelNode,
    LifecycleStage,
    SignalStatus,
    GateDecision,
    AutomationStatus,
    Platform,
    BelongsToEdge,
    PerformedEdge,
    GeneratedEdge,
    EvaluatedByEdge,
    TriggeredEdge,
    BlockedEdge,
    AttributedToEdge,
)
from .service import KnowledgeGraphService

logger = logging.getLogger(__name__)

# Batch size for memory-efficient processing (per Feb 2026 audit)
SYNC_BATCH_SIZE = 100


class KnowledgeGraphSyncService:
    """
    Synchronizes Stratum data into the Knowledge Graph.

    Integrations:
    - CDP: Profiles, Events, Segments, Identity Links
    - Trust Engine: Signals, TrustGates, Automations
    - Campaigns: Campaign performance, Revenue attribution

    Usage:
        async with get_db_session() as session:
            sync = KnowledgeGraphSyncService(session)

            # Full sync for a tenant
            await sync.full_sync(tenant_id)

            # Incremental sync since last run
            await sync.incremental_sync(tenant_id, since=last_sync_at)

            # Real-time event sync
            await sync.sync_event(event)
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.kg = KnowledgeGraphService(session)

    # =========================================================================
    # CDP SYNC
    # =========================================================================

    async def sync_cdp_profiles(
        self,
        tenant_id: UUID,
        since: Optional[datetime] = None,
        batch_size: int = SYNC_BATCH_SIZE
    ) -> int:
        """
        Sync CDP profiles to the knowledge graph.

        Args:
            tenant_id: Tenant UUID
            since: Only sync profiles updated after this time
            batch_size: Batch size for memory efficiency

        Returns:
            Number of profiles synced
        """
        from app.models.cdp import CDPProfile

        query = select(CDPProfile).where(CDPProfile.tenant_id == tenant_id)
        if since:
            query = query.where(CDPProfile.updated_at > since)

        result = await self.session.execute(query)
        profiles = result.scalars().all()

        synced = 0
        for i in range(0, len(profiles), batch_size):
            batch = profiles[i:i + batch_size]

            for profile in batch:
                node = ProfileNode(
                    tenant_id=tenant_id,
                    external_id=str(profile.id),
                    lifecycle_stage=LifecycleStage(profile.lifecycle_stage.value),
                    first_seen_at=profile.first_seen_at,
                    last_seen_at=profile.last_seen_at,
                    total_events=profile.total_events or 0,
                    total_sessions=profile.total_sessions or 0,
                    total_purchases=profile.total_purchases or 0,
                    total_revenue_cents=int((profile.total_revenue or 0) * 100),
                    computed_traits=profile.computed_traits or {},
                    properties={
                        "profile_data": profile.profile_data or {},
                    }
                )

                # Extract RFM if present
                if profile.computed_traits:
                    node.rfm_segment = profile.computed_traits.get("rfm_segment")
                    node.rfm_score = profile.computed_traits.get("rfm_score")

                await self.kg.merge_node(node)
                synced += 1

            logger.info(f"Synced {synced}/{len(profiles)} profiles for tenant {tenant_id}")

        return synced

    async def sync_cdp_events(
        self,
        tenant_id: UUID,
        since: Optional[datetime] = None,
        batch_size: int = SYNC_BATCH_SIZE
    ) -> int:
        """
        Sync CDP events to the knowledge graph.

        Args:
            tenant_id: Tenant UUID
            since: Only sync events after this time
            batch_size: Batch size for memory efficiency

        Returns:
            Number of events synced
        """
        from app.models.cdp import CDPEvent

        query = select(CDPEvent).where(CDPEvent.tenant_id == tenant_id)
        if since:
            query = query.where(CDPEvent.created_at > since)
        query = query.order_by(CDPEvent.event_time.asc())

        result = await self.session.execute(query)
        events = result.scalars().all()

        synced = 0
        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]

            for event in batch:
                # Create event node
                node = EventNode(
                    tenant_id=tenant_id,
                    external_id=str(event.id),
                    event_type=event.event_name,
                    event_time=event.event_time,
                    source=event.source_id and str(event.source_id),
                    emq_score=event.emq_score,
                    event_properties=event.properties or {},
                )

                # Check for revenue
                if event.properties and "revenue" in event.properties:
                    node.revenue_cents = int(float(event.properties["revenue"]) * 100)

                await self.kg.merge_node(node)

                # Create PERFORMED edge from profile to event
                if event.profile_id:
                    edge = PerformedEdge(
                        start_node_id="",  # Will be matched by external_id
                        end_node_id="",
                        tenant_id=tenant_id,
                        session_id=event.context.get("session_id") if event.context else None,
                    )
                    await self.kg.create_edge(
                        edge,
                        start_label=NodeLabel.PROFILE,
                        start_external_id=str(event.profile_id),
                        end_label=NodeLabel.EVENT,
                        end_external_id=str(event.id)
                    )

                    # If revenue event, create Revenue node and GENERATED edge
                    if node.revenue_cents and node.revenue_cents > 0:
                        revenue_node = RevenueNode(
                            tenant_id=tenant_id,
                            external_id=f"rev_{event.id}",
                            amount_cents=node.revenue_cents,
                            revenue_type="purchase",
                            occurred_at=event.event_time,
                        )
                        await self.kg.merge_node(revenue_node)

                        gen_edge = GeneratedEdge(
                            start_node_id="",
                            end_node_id="",
                            tenant_id=tenant_id,
                        )
                        await self.kg.create_edge(
                            gen_edge,
                            start_label=NodeLabel.EVENT,
                            start_external_id=str(event.id),
                            end_label=NodeLabel.REVENUE,
                            end_external_id=f"rev_{event.id}"
                        )

                synced += 1

            logger.info(f"Synced {synced}/{len(events)} events for tenant {tenant_id}")

        return synced

    async def sync_cdp_segments(
        self,
        tenant_id: UUID,
        since: Optional[datetime] = None
    ) -> int:
        """
        Sync CDP segments and memberships to the knowledge graph.

        Args:
            tenant_id: Tenant UUID
            since: Only sync segments updated after this time

        Returns:
            Number of segments synced
        """
        from app.models.cdp import CDPSegment, CDPSegmentMembership

        query = select(CDPSegment).where(CDPSegment.tenant_id == tenant_id)
        if since:
            query = query.where(CDPSegment.updated_at > since)

        result = await self.session.execute(query)
        segments = result.scalars().all()

        synced = 0
        for segment in segments:
            node = SegmentNode(
                tenant_id=tenant_id,
                external_id=str(segment.id),
                name=segment.name,
                segment_type=segment.segment_type.value if segment.segment_type else "dynamic",
                profile_count=segment.profile_count or 0,
                conditions=segment.rules or {},
                last_computed_at=segment.last_computed_at,
            )
            await self.kg.merge_node(node)

            # Sync memberships
            membership_query = select(CDPSegmentMembership).where(
                CDPSegmentMembership.segment_id == segment.id,
                CDPSegmentMembership.is_active == True
            )
            membership_result = await self.session.execute(membership_query)
            memberships = membership_result.scalars().all()

            for membership in memberships:
                edge = BelongsToEdge(
                    start_node_id="",
                    end_node_id="",
                    tenant_id=tenant_id,
                    added_at=membership.added_at,
                    match_score=membership.match_score,
                )
                await self.kg.create_edge(
                    edge,
                    start_label=NodeLabel.PROFILE,
                    start_external_id=str(membership.profile_id),
                    end_label=NodeLabel.SEGMENT,
                    end_external_id=str(segment.id)
                )

            synced += 1

        logger.info(f"Synced {synced} segments for tenant {tenant_id}")
        return synced

    # =========================================================================
    # TRUST ENGINE SYNC
    # =========================================================================

    async def sync_signal_health(
        self,
        tenant_id: UUID,
        since: Optional[datetime] = None
    ) -> int:
        """
        Sync signal health records to the knowledge graph.

        Args:
            tenant_id: Tenant UUID
            since: Only sync signals after this time

        Returns:
            Number of signals synced
        """
        from app.models.trust_layer import FactSignalHealthDaily

        query = select(FactSignalHealthDaily).where(
            FactSignalHealthDaily.tenant_id == tenant_id
        )
        if since:
            query = query.where(FactSignalHealthDaily.date >= since.date())

        result = await self.session.execute(query)
        signals = result.scalars().all()

        synced = 0
        for signal in signals:
            # Map status to enum
            status_map = {
                "OK": SignalStatus.HEALTHY,
                "RISK": SignalStatus.DEGRADED,
                "DEGRADED": SignalStatus.DEGRADED,
                "CRITICAL": SignalStatus.CRITICAL,
            }

            node = SignalNode(
                tenant_id=tenant_id,
                external_id=f"signal_{signal.platform}_{signal.date}",
                signal_type="composite",
                source=signal.platform,
                platform=Platform(signal.platform.lower()) if signal.platform.lower() in [p.value for p in Platform] else None,
                score=signal.emq_score or 0,
                status=status_map.get(signal.status, SignalStatus.DEGRADED),
                issues=signal.issues or [],
                measured_at=datetime.combine(signal.date, datetime.min.time()),
            )
            await self.kg.merge_node(node)
            synced += 1

        logger.info(f"Synced {synced} signal health records for tenant {tenant_id}")
        return synced

    async def sync_trust_gate_decisions(
        self,
        tenant_id: UUID,
        since: Optional[datetime] = None
    ) -> int:
        """
        Sync trust gate audit log to the knowledge graph.

        Args:
            tenant_id: Tenant UUID
            since: Only sync decisions after this time

        Returns:
            Number of decisions synced
        """
        from app.models.trust_layer import TrustGateAuditLog

        query = select(TrustGateAuditLog).where(
            TrustGateAuditLog.tenant_id == tenant_id
        )
        if since:
            query = query.where(TrustGateAuditLog.created_at > since)

        result = await self.session.execute(query)
        decisions = result.scalars().all()

        synced = 0
        for decision in decisions:
            # Map decision to enum
            decision_map = {
                "execute": GateDecision.PASS,
                "hold": GateDecision.HOLD,
                "block": GateDecision.BLOCK,
            }

            node = TrustGateNode(
                tenant_id=tenant_id,
                external_id=str(decision.id),
                decision=decision_map.get(decision.decision, GateDecision.HOLD),
                signal_health_score=decision.signal_health_score or 0,
                threshold_used=decision.healthy_threshold or 70.0,
                action_type=decision.entity_type or "unknown",
                reason=decision.gate_reason or "",
                recommendations=[],
                evaluated_at=decision.created_at,
                is_dry_run=decision.is_dry_run or False,
            )
            await self.kg.merge_node(node)
            synced += 1

        logger.info(f"Synced {synced} trust gate decisions for tenant {tenant_id}")
        return synced

    async def sync_automation_actions(
        self,
        tenant_id: UUID,
        since: Optional[datetime] = None
    ) -> int:
        """
        Sync automation actions to the knowledge graph.

        Args:
            tenant_id: Tenant UUID
            since: Only sync actions after this time

        Returns:
            Number of actions synced
        """
        from app.models.trust_layer import FactActionsQueue

        query = select(FactActionsQueue).where(
            FactActionsQueue.tenant_id == tenant_id
        )
        if since:
            query = query.where(FactActionsQueue.created_at > since)

        result = await self.session.execute(query)
        actions = result.scalars().all()

        synced = 0
        for action in actions:
            # Map status to enum
            status_map = {
                "queued": AutomationStatus.PENDING,
                "approved": AutomationStatus.PENDING,
                "applied": AutomationStatus.COMPLETED,
                "failed": AutomationStatus.FAILED,
                "dismissed": AutomationStatus.BLOCKED,
            }

            node = AutomationNode(
                tenant_id=tenant_id,
                external_id=str(action.id),
                action_type=action.action_type or "unknown",
                entity_type=action.entity_type or "campaign",
                entity_id=action.entity_id or "",
                platform=Platform(action.platform.lower()) if action.platform and action.platform.lower() in [p.value for p in Platform] else Platform.META,
                status=status_map.get(action.status, AutomationStatus.PENDING),
                parameters={
                    "before_value": action.before_value,
                    "after_value": action.after_value,
                },
                executed_at=action.applied_at,
                result=action.platform_response,
            )
            await self.kg.merge_node(node)
            synced += 1

        logger.info(f"Synced {synced} automation actions for tenant {tenant_id}")
        return synced

    # =========================================================================
    # CAMPAIGN SYNC
    # =========================================================================

    async def sync_campaigns(
        self,
        tenant_id: UUID,
        since: Optional[datetime] = None
    ) -> int:
        """
        Sync campaigns to the knowledge graph.

        Args:
            tenant_id: Tenant UUID
            since: Only sync campaigns updated after this time

        Returns:
            Number of campaigns synced
        """
        from app.base_models import Campaign

        query = select(Campaign).where(Campaign.tenant_id == tenant_id)
        if since:
            query = query.where(Campaign.updated_at > since)

        result = await self.session.execute(query)
        campaigns = result.scalars().all()

        synced = 0
        for campaign in campaigns:
            platform_map = {
                "META": Platform.META,
                "GOOGLE": Platform.GOOGLE,
                "TIKTOK": Platform.TIKTOK,
                "SNAPCHAT": Platform.SNAPCHAT,
            }

            node = CampaignNode(
                tenant_id=tenant_id,
                external_id=str(campaign.id),
                name=campaign.name,
                platform=platform_map.get(campaign.platform.value, Platform.META) if campaign.platform else Platform.META,
                platform_campaign_id=campaign.platform_campaign_id or str(campaign.id),
                status=campaign.status.value if campaign.status else "active",
                objective=campaign.objective,
                budget_cents=campaign.budget_cents,
                spend_cents=campaign.spend_cents or 0,
                impressions=campaign.impressions or 0,
                clicks=campaign.clicks or 0,
                conversions=campaign.conversions or 0,
                revenue_cents=campaign.revenue_cents or 0,
                roas=campaign.roas,
            )
            await self.kg.merge_node(node)
            synced += 1

        logger.info(f"Synced {synced} campaigns for tenant {tenant_id}")
        return synced

    # =========================================================================
    # FULL & INCREMENTAL SYNC
    # =========================================================================

    async def full_sync(self, tenant_id: UUID) -> dict[str, int]:
        """
        Perform a full sync of all data for a tenant.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Dict of entity type -> count synced
        """
        logger.info(f"Starting full knowledge graph sync for tenant {tenant_id}")

        results = {
            "profiles": await self.sync_cdp_profiles(tenant_id),
            "events": await self.sync_cdp_events(tenant_id),
            "segments": await self.sync_cdp_segments(tenant_id),
            "signals": await self.sync_signal_health(tenant_id),
            "trust_gates": await self.sync_trust_gate_decisions(tenant_id),
            "automations": await self.sync_automation_actions(tenant_id),
            "campaigns": await self.sync_campaigns(tenant_id),
        }

        total = sum(results.values())
        logger.info(f"Full sync completed for tenant {tenant_id}: {total} total entities")

        return results

    async def incremental_sync(
        self,
        tenant_id: UUID,
        since: datetime
    ) -> dict[str, int]:
        """
        Perform incremental sync of data changed since last sync.

        Args:
            tenant_id: Tenant UUID
            since: Sync data updated after this time

        Returns:
            Dict of entity type -> count synced
        """
        logger.info(f"Starting incremental sync for tenant {tenant_id} since {since}")

        results = {
            "profiles": await self.sync_cdp_profiles(tenant_id, since=since),
            "events": await self.sync_cdp_events(tenant_id, since=since),
            "segments": await self.sync_cdp_segments(tenant_id, since=since),
            "signals": await self.sync_signal_health(tenant_id, since=since),
            "trust_gates": await self.sync_trust_gate_decisions(tenant_id, since=since),
            "automations": await self.sync_automation_actions(tenant_id, since=since),
            "campaigns": await self.sync_campaigns(tenant_id, since=since),
        }

        total = sum(results.values())
        logger.info(f"Incremental sync completed for tenant {tenant_id}: {total} entities updated")

        return results

    # =========================================================================
    # REAL-TIME SYNC HOOKS
    # =========================================================================

    async def on_event_ingested(
        self,
        tenant_id: UUID,
        event_id: UUID,
        event_name: str,
        profile_id: Optional[UUID],
        properties: dict[str, Any],
        event_time: datetime
    ) -> None:
        """
        Real-time hook called when a CDP event is ingested.

        Args:
            tenant_id: Tenant UUID
            event_id: Event UUID
            event_name: Event type/name
            profile_id: Associated profile UUID (if known)
            properties: Event properties
            event_time: When the event occurred
        """
        node = EventNode(
            tenant_id=tenant_id,
            external_id=str(event_id),
            event_type=event_name,
            event_time=event_time,
            event_properties=properties,
        )

        if "revenue" in properties:
            node.revenue_cents = int(float(properties["revenue"]) * 100)

        await self.kg.merge_node(node)

        if profile_id:
            edge = PerformedEdge(
                start_node_id="",
                end_node_id="",
                tenant_id=tenant_id,
            )
            await self.kg.create_edge(
                edge,
                start_label=NodeLabel.PROFILE,
                start_external_id=str(profile_id),
                end_label=NodeLabel.EVENT,
                end_external_id=str(event_id)
            )

    async def on_trust_gate_evaluated(
        self,
        tenant_id: UUID,
        gate_id: UUID,
        decision: str,
        signal_health: float,
        action_type: str,
        reason: str,
        automation_id: Optional[UUID] = None
    ) -> None:
        """
        Real-time hook called when a trust gate is evaluated.

        Args:
            tenant_id: Tenant UUID
            gate_id: Gate evaluation UUID
            decision: pass/hold/block
            signal_health: Signal health score at evaluation
            action_type: Type of action being evaluated
            reason: Decision reason
            automation_id: Related automation UUID
        """
        decision_enum = GateDecision(decision.lower())

        node = TrustGateNode(
            tenant_id=tenant_id,
            external_id=str(gate_id),
            decision=decision_enum,
            signal_health_score=signal_health,
            threshold_used=70.0,  # Default threshold
            action_type=action_type,
            reason=reason,
            evaluated_at=datetime.utcnow(),
        )
        await self.kg.merge_node(node)

        # Link to automation if provided
        if automation_id:
            if decision_enum == GateDecision.PASS:
                edge = TriggeredEdge(
                    start_node_id="",
                    end_node_id="",
                    tenant_id=tenant_id,
                    properties={"trigger_type": "trust_gate"},
                )
            else:
                edge = BlockedEdge(
                    start_node_id="",
                    end_node_id="",
                    tenant_id=tenant_id,
                    reason=reason,
                    signal_health_at_block=signal_health,
                )

            await self.kg.create_edge(
                edge,
                start_label=NodeLabel.TRUST_GATE,
                start_external_id=str(gate_id),
                end_label=NodeLabel.AUTOMATION,
                end_external_id=str(automation_id)
            )

    async def on_profile_merged(
        self,
        tenant_id: UUID,
        surviving_profile_id: UUID,
        merged_profile_id: UUID
    ) -> None:
        """
        Real-time hook called when profiles are merged.

        Creates MERGED_INTO edge in the graph.
        """
        from .models import GraphEdge

        edge = GraphEdge(
            start_node_id="",
            end_node_id="",
            label=EdgeLabel.MERGED_INTO,
            tenant_id=tenant_id,
            properties={"merged_at": datetime.utcnow().isoformat()},
        )
        await self.kg.create_edge(
            edge,
            start_label=NodeLabel.PROFILE,
            start_external_id=str(merged_profile_id),
            end_label=NodeLabel.PROFILE,
            end_external_id=str(surviving_profile_id)
        )
