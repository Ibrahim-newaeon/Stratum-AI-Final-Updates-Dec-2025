"""
Knowledge Graph Sync Service

Synchronizes data from CDP and Trust Engine into the Knowledge Graph.
Provides real-time and batch sync capabilities.

Two properties this module has to hold, because both of its failure modes look
like success from the outside:

* **Completeness.** Every read was previously a single ``SELECT ... LIMIT
  1000`` with no ordering and no continuation, so a tenant with more than a
  thousand of anything was backfilled to 1000 rows and reported as done. Reads
  are keyset-paginated on the primary key now -- stable under concurrent
  writes, index-backed, and it runs to exhaustion.
* **Durability.** Nothing here ever committed. That never mattered while the
  only callers were GET routes; for a writer it means the whole backfill is
  rolled back at session close, having logged its counts on the way out. Each
  batch commits.

``tenant_id`` is an ``int`` throughout: ``tenants.id`` is ``Integer`` in this
schema. Both the read and write paths render it as a Cypher string literal, so
the two agree on ``'42'`` regardless.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator, Sequence
from datetime import UTC, datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from .models import (
    AutomationNode,
    AutomationStatus,
    BelongsToEdge,
    BlockedEdge,
    CampaignNode,
    EdgeLabel,
    EventNode,
    GateDecision,
    GeneratedEdge,
    LifecycleStage,
    NodeLabel,
    PerformedEdge,
    Platform,
    ProfileNode,
    RevenueNode,
    SegmentNode,
    SignalNode,
    SignalStatus,
    TriggeredEdge,
    TrustGateNode,
)
from .service import KnowledgeGraphService

logger = logging.getLogger(__name__)

# Rows fetched (and committed) per round trip. Small enough that a failure
# mid-backfill loses little, large enough that the per-batch commit is not the
# dominant cost.
SYNC_BATCH_SIZE = 500


def _json_list(raw: Any) -> list[str]:
    """Coerce a JSON-in-Text column into the ``list[str]`` a node field wants.

    ``FactSignalHealthDaily.issues`` is ``Text`` holding a JSON array. Handing
    the raw string to a ``list[str]`` field is the kind of mismatch Pydantic
    rejects loudly on a good day and iterates into single characters on a bad
    one, so the parse is explicit and total.
    """
    if raw in (None, ""):
        return []
    if isinstance(raw, list):
        return [str(item) for item in raw]
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return [str(raw)]
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return [str(parsed)]


def _json_dict(raw: Any) -> Optional[dict[str, Any]]:
    """Same, for the Text columns that hold a JSON object."""
    if raw in (None, ""):
        return None
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return {"raw": str(raw)}
    return parsed if isinstance(parsed, dict) else {"value": parsed}


def _bounded_score(raw: Any, default: float = 0.0) -> float:
    """Clamp a health score into the 0-100 the node field declares.

    ``signal_health_score`` is read out of a free-form JSONB ``details`` blob,
    so nothing upstream guarantees its range. Pydantic would reject an
    out-of-range value and take the whole batch down with it.
    """
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(100.0, value))


def _unit_score(raw: Any) -> Optional[float]:
    """Normalize a match score onto the 0-1 ``BelongsToEdge.match_score`` wants.

    ``CDPSegmentMembership.match_score`` is ``Numeric(5, 2)`` and is written as
    a percentage. The edge field is bounded ``ge=0, le=1``, so anything above 1
    is read as a percentage and scaled.
    """
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value > 1.0:
        value = value / 100.0
    return max(0.0, min(1.0, value))


def _enum_value(raw: Any) -> str:
    """Read a value off a column that may be an Enum instance or a plain str.

    ``StrEnumType`` columns hand back the enum; ``String`` columns hand back
    the string. Several of these tables are one and several are the other, and
    which is which is not visible from the sync code.
    """
    return str(getattr(raw, "value", raw) or "").lower()


def _as_platform(raw: Any) -> Optional[Platform]:
    """Map a platform string onto the graph's vocabulary, or None."""
    value = _enum_value(raw)
    try:
        return Platform(value)
    except ValueError:
        return None


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
    # BATCHING
    # =========================================================================

    async def _iter_batches(
        self,
        query: Select,
        pk: InstrumentedAttribute,
        batch_size: int,
    ) -> AsyncIterator[Sequence[Any]]:
        """Yield every row matching ``query``, keyset-paginated on ``pk``.

        Keyset rather than OFFSET for two reasons. None of these queries had an
        ORDER BY, so OFFSET paging over an unspecified order silently skips and
        duplicates rows; and OFFSET degrades quadratically over the row counts
        a backfill is for.

        Commits after each batch is consumed. The caller has written that
        batch's nodes and edges by then, so the transaction is closed at a
        point the work can be resumed from -- and the graph is left populated
        rather than rolled back if a later batch fails.
        """
        cursor: Any = None
        while True:
            page = query.order_by(pk.asc())
            if cursor is not None:
                page = page.where(pk > cursor)

            result = await self.session.execute(page.limit(batch_size))
            rows = list(result.scalars().all())
            if not rows:
                return

            yield rows
            await self.session.commit()

            if len(rows) < batch_size:
                return
            cursor = getattr(rows[-1], pk.key)

    # =========================================================================
    # CDP SYNC
    # =========================================================================

    async def sync_cdp_profiles(
        self,
        tenant_id: int,
        since: Optional[datetime] = None,
        batch_size: int = SYNC_BATCH_SIZE,
    ) -> int:
        """
        Sync CDP profiles to the knowledge graph.

        Args:
            tenant_id: Tenant ID
            since: Only sync profiles updated after this time
            batch_size: Rows per round trip

        Returns:
            Number of profiles synced
        """
        from app.models.cdp import CDPProfile

        query = select(CDPProfile).where(CDPProfile.tenant_id == tenant_id)
        if since:
            query = query.where(CDPProfile.updated_at > since)

        synced = 0
        async for batch in self._iter_batches(query, CDPProfile.id, batch_size):
            for profile in batch:
                traits = profile.computed_traits or {}
                node = ProfileNode(
                    tenant_id=tenant_id,
                    external_id=str(profile.id),
                    lifecycle_stage=LifecycleStage(
                        _enum_value(profile.lifecycle_stage)
                    ),
                    first_seen_at=profile.first_seen_at,
                    last_seen_at=profile.last_seen_at,
                    total_events=profile.total_events or 0,
                    total_sessions=profile.total_sessions or 0,
                    total_purchases=profile.total_purchases or 0,
                    total_revenue_cents=int((profile.total_revenue or 0) * 100),
                    rfm_segment=traits.get("rfm_segment"),
                    rfm_score=traits.get("rfm_score"),
                    computed_traits=traits,
                    properties={"profile_data": profile.profile_data or {}},
                )
                await self.kg.merge_node(node)
                synced += 1

            logger.info(f"Synced {synced} profiles for tenant {tenant_id}")

        return synced

    async def sync_cdp_events(
        self,
        tenant_id: int,
        since: Optional[datetime] = None,
        batch_size: int = SYNC_BATCH_SIZE,
    ) -> int:
        """
        Sync CDP events to the knowledge graph.

        Profiles are synced first by ``full_sync`` on purpose: the PERFORMED
        edge is created with a MATCH on both endpoints, so an event whose
        profile vertex does not exist yet produces no edge and no error.

        Args:
            tenant_id: Tenant ID
            since: Only sync events after this time
            batch_size: Rows per round trip

        Returns:
            Number of events synced
        """
        from app.models.cdp import CDPEvent

        query = select(CDPEvent).where(CDPEvent.tenant_id == tenant_id)
        if since:
            query = query.where(CDPEvent.created_at > since)

        synced = 0
        async for batch in self._iter_batches(query, CDPEvent.id, batch_size):
            for event in batch:
                node = EventNode(
                    tenant_id=tenant_id,
                    external_id=str(event.id),
                    event_type=event.event_name,
                    event_time=event.event_time,
                    source=event.source_id and str(event.source_id),
                    emq_score=(
                        float(event.emq_score) if event.emq_score is not None else None
                    ),
                    event_properties=event.properties or {},
                )

                # Check for revenue
                if event.properties and "revenue" in event.properties:
                    try:
                        node.revenue_cents = int(
                            float(event.properties["revenue"]) * 100
                        )
                    except (TypeError, ValueError):
                        node.revenue_cents = None

                await self.kg.merge_node(node)

                # Create PERFORMED edge from profile to event
                if event.profile_id:
                    edge = PerformedEdge(
                        start_node_id="",  # Will be matched by external_id
                        end_node_id="",
                        tenant_id=tenant_id,
                        session_id=(
                            event.context.get("session_id") if event.context else None
                        ),
                    )
                    await self.kg.create_edge(
                        edge,
                        start_label=NodeLabel.PROFILE,
                        start_external_id=str(event.profile_id),
                        end_label=NodeLabel.EVENT,
                        end_external_id=str(event.id),
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
                            end_external_id=f"rev_{event.id}",
                        )

                synced += 1

            logger.info(f"Synced {synced} events for tenant {tenant_id}")

        return synced

    async def sync_cdp_segments(
        self,
        tenant_id: int,
        since: Optional[datetime] = None,
        batch_size: int = SYNC_BATCH_SIZE,
    ) -> int:
        """
        Sync CDP segments and memberships to the knowledge graph.

        Args:
            tenant_id: Tenant ID
            since: Only sync segments updated after this time
            batch_size: Rows per round trip

        Returns:
            Number of segments synced
        """
        from app.models.cdp import CDPSegment, CDPSegmentMembership

        query = select(CDPSegment).where(CDPSegment.tenant_id == tenant_id)
        if since:
            query = query.where(CDPSegment.updated_at > since)

        synced = 0
        async for batch in self._iter_batches(query, CDPSegment.id, batch_size):
            for segment in batch:
                node = SegmentNode(
                    tenant_id=tenant_id,
                    external_id=str(segment.id),
                    name=segment.name,
                    # segment_type is String(50), not an Enum column.
                    segment_type=_enum_value(segment.segment_type) or "dynamic",
                    profile_count=segment.profile_count or 0,
                    conditions=segment.rules or {},
                    last_computed_at=segment.last_computed_at,
                )
                await self.kg.merge_node(node)
                synced += 1

            logger.info(f"Synced {synced} segments for tenant {tenant_id}")

        # Memberships walk their own paginated pass. A segment with a million
        # members is the normal case, not the exceptional one, so it cannot
        # ride inside the segment loop on a single capped query.
        membership_query = select(CDPSegmentMembership).where(
            CDPSegmentMembership.tenant_id == tenant_id,
            CDPSegmentMembership.is_active.is_(True),
        )
        memberships = 0
        async for batch in self._iter_batches(
            membership_query, CDPSegmentMembership.id, batch_size
        ):
            for membership in batch:
                edge = BelongsToEdge(
                    start_node_id="",
                    end_node_id="",
                    tenant_id=tenant_id,
                    added_at=membership.added_at,
                    match_score=_unit_score(membership.match_score),
                )
                await self.kg.create_edge(
                    edge,
                    start_label=NodeLabel.PROFILE,
                    start_external_id=str(membership.profile_id),
                    end_label=NodeLabel.SEGMENT,
                    end_external_id=str(membership.segment_id),
                )
                memberships += 1

        logger.info(f"Synced {memberships} segment memberships for tenant {tenant_id}")
        return synced

    # =========================================================================
    # TRUST ENGINE SYNC
    # =========================================================================

    async def sync_signal_health(
        self,
        tenant_id: int,
        since: Optional[datetime] = None,
        batch_size: int = SYNC_BATCH_SIZE,
    ) -> int:
        """
        Sync signal health records to the knowledge graph.

        Args:
            tenant_id: Tenant ID
            since: Only sync signals after this time
            batch_size: Rows per round trip

        Returns:
            Number of signals synced
        """
        from app.models.trust_layer import FactSignalHealthDaily

        query = select(FactSignalHealthDaily).where(
            FactSignalHealthDaily.tenant_id == tenant_id
        )
        if since:
            query = query.where(FactSignalHealthDaily.date >= since.date())

        # SignalHealthStatus values are lowercase. Keying this map on "OK" /
        # "RISK" / "CRITICAL" meant every row fell through to the default and
        # the entire platform read as DEGRADED.
        status_map = {
            "ok": SignalStatus.HEALTHY,
            "risk": SignalStatus.DEGRADED,
            "degraded": SignalStatus.DEGRADED,
            "critical": SignalStatus.CRITICAL,
        }

        synced = 0
        async for batch in self._iter_batches(
            query, FactSignalHealthDaily.id, batch_size
        ):
            for signal in batch:
                node = SignalNode(
                    tenant_id=tenant_id,
                    external_id=f"signal_{signal.platform}_{signal.date}",
                    signal_type="composite",
                    source=signal.platform,
                    platform=_as_platform(signal.platform),
                    score=signal.emq_score or 0,
                    status=status_map.get(
                        _enum_value(signal.status), SignalStatus.DEGRADED
                    ),
                    issues=_json_list(signal.issues),
                    measured_at=datetime.combine(signal.date, datetime.min.time()),
                )
                await self.kg.merge_node(node)
                synced += 1

            logger.info(f"Synced {synced} signal health records for tenant {tenant_id}")

        return synced

    async def sync_trust_gate_decisions(
        self,
        tenant_id: int,
        since: Optional[datetime] = None,
        batch_size: int = SYNC_BATCH_SIZE,
    ) -> int:
        """
        Sync enforcement interventions to the knowledge graph as trust gates.

        Reads ``EnforcementAuditLog`` -- the table the enforcer actually writes
        a decision to. This method previously imported ``TrustGateAuditLog``
        from ``app.models.trust_layer``, a class that exists nowhere in the
        repo; because the import sat inside the method body, the module still
        imported cleanly and the failure waited for the first call that never
        came.

        Args:
            tenant_id: Tenant ID
            since: Only sync decisions after this time
            batch_size: Rows per round trip

        Returns:
            Number of decisions synced
        """
        from app.models.autopilot import EnforcementAuditLog, EnforcementMode

        query = select(EnforcementAuditLog).where(
            EnforcementAuditLog.tenant_id == tenant_id
        )
        if since:
            query = query.where(EnforcementAuditLog.timestamp > since)

        # The audit log records the intervention, not the gate verdict, so the
        # verdict is read back off it: anything that stopped the action is a
        # BLOCK, anything that only warned is a HOLD, and a logged override is
        # an action that proceeded.
        decision_map = {
            "blocked": GateDecision.BLOCK,
            "auto_paused": GateDecision.BLOCK,
            "warned": GateDecision.HOLD,
            "notification_sent": GateDecision.HOLD,
            "kill_switch_changed": GateDecision.HOLD,
            "override_logged": GateDecision.PASS,
        }

        synced = 0
        async for batch in self._iter_batches(
            query, EnforcementAuditLog.id, batch_size
        ):
            for decision in batch:
                details = decision.details or {}
                node = TrustGateNode(
                    tenant_id=tenant_id,
                    external_id=str(decision.id),
                    decision=decision_map.get(
                        _enum_value(decision.intervention_action), GateDecision.HOLD
                    ),
                    signal_health_score=_bounded_score(
                        details.get("signal_health_score")
                    ),
                    threshold_used=float(details.get("threshold") or 70.0),
                    action_type=decision.action_type or "unknown",
                    reason=(
                        decision.override_reason
                        or _enum_value(decision.violation_type)
                        or ""
                    ),
                    recommendations=[],
                    evaluated_at=decision.timestamp,
                    # Advisory mode logs what it would have done without
                    # stopping anything, which is what is_dry_run means here.
                    is_dry_run=(
                        _enum_value(decision.enforcement_mode)
                        == EnforcementMode.ADVISORY.value
                    ),
                    properties={
                        "entity_type": decision.entity_type,
                        "entity_id": decision.entity_id,
                        "enforcement_mode": _enum_value(decision.enforcement_mode),
                    },
                )
                await self.kg.merge_node(node)
                synced += 1

            logger.info(f"Synced {synced} trust gate decisions for tenant {tenant_id}")

        return synced

    async def sync_automation_actions(
        self,
        tenant_id: int,
        since: Optional[datetime] = None,
        batch_size: int = SYNC_BATCH_SIZE,
    ) -> int:
        """
        Sync automation actions to the knowledge graph.

        Args:
            tenant_id: Tenant ID
            since: Only sync actions after this time
            batch_size: Rows per round trip

        Returns:
            Number of actions synced
        """
        from app.models.trust_layer import FactActionsQueue

        query = select(FactActionsQueue).where(FactActionsQueue.tenant_id == tenant_id)
        if since:
            query = query.where(FactActionsQueue.created_at > since)

        status_map = {
            "queued": AutomationStatus.PENDING,
            "approved": AutomationStatus.PENDING,
            "applied": AutomationStatus.COMPLETED,
            "failed": AutomationStatus.FAILED,
            "dismissed": AutomationStatus.BLOCKED,
        }

        synced = 0
        async for batch in self._iter_batches(query, FactActionsQueue.id, batch_size):
            for action in batch:
                node = AutomationNode(
                    tenant_id=tenant_id,
                    external_id=str(action.id),
                    action_type=action.action_type or "unknown",
                    entity_type=action.entity_type or "campaign",
                    entity_id=action.entity_id or "",
                    platform=_as_platform(action.platform) or Platform.META,
                    status=status_map.get(
                        _enum_value(action.status), AutomationStatus.PENDING
                    ),
                    # before_value / after_value / platform_response are all
                    # Text columns holding JSON, not JSONB.
                    parameters={
                        "before_value": _json_dict(action.before_value),
                        "after_value": _json_dict(action.after_value),
                    },
                    executed_at=action.applied_at,
                    result=_json_dict(action.platform_response),
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
        tenant_id: int,
        since: Optional[datetime] = None,
        batch_size: int = SYNC_BATCH_SIZE,
    ) -> int:
        """
        Sync campaigns to the knowledge graph.

        The column names here were invented: ``Campaign`` has no
        ``platform_campaign_id``, ``budget_cents`` or ``spend_cents``. The real
        ones are ``external_id``, ``daily_budget_cents`` /
        ``lifetime_budget_cents``, and ``total_spend_cents``.

        Args:
            tenant_id: Tenant ID
            since: Only sync campaigns updated after this time
            batch_size: Rows per round trip

        Returns:
            Number of campaigns synced
        """
        from app.base_models import Campaign

        query = select(Campaign).where(
            Campaign.tenant_id == tenant_id,
            Campaign.is_deleted.is_(False),
        )
        if since:
            query = query.where(Campaign.updated_at > since)

        synced = 0
        async for batch in self._iter_batches(query, Campaign.id, batch_size):
            for campaign in batch:
                node = CampaignNode(
                    tenant_id=tenant_id,
                    external_id=str(campaign.id),
                    name=campaign.name,
                    platform=_as_platform(campaign.platform) or Platform.META,
                    platform_campaign_id=campaign.external_id or str(campaign.id),
                    status=_enum_value(campaign.status) or "active",
                    objective=campaign.objective,
                    budget_cents=(
                        campaign.daily_budget_cents or campaign.lifetime_budget_cents
                    ),
                    spend_cents=campaign.total_spend_cents or 0,
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

    async def full_sync(
        self, tenant_id: int, batch_size: int = SYNC_BATCH_SIZE
    ) -> dict[str, int]:
        """
        Perform a full sync of all data for a tenant.

        Order matters: profiles and campaigns are the endpoints other rows
        attach edges to, and an edge whose endpoints are not in the graph is
        created silently as nothing at all.

        Args:
            tenant_id: Tenant ID
            batch_size: Rows per round trip

        Returns:
            Dict of entity type -> count synced
        """
        logger.info(f"Starting full knowledge graph sync for tenant {tenant_id}")

        results = {
            "profiles": await self.sync_cdp_profiles(tenant_id, batch_size=batch_size),
            "campaigns": await self.sync_campaigns(tenant_id, batch_size=batch_size),
            "segments": await self.sync_cdp_segments(tenant_id, batch_size=batch_size),
            "events": await self.sync_cdp_events(tenant_id, batch_size=batch_size),
            "signals": await self.sync_signal_health(tenant_id, batch_size=batch_size),
            "trust_gates": await self.sync_trust_gate_decisions(
                tenant_id, batch_size=batch_size
            ),
            "automations": await self.sync_automation_actions(
                tenant_id, batch_size=batch_size
            ),
        }

        total = sum(results.values())
        logger.info(
            f"Full sync completed for tenant {tenant_id}: {total} total entities"
        )

        return results

    async def incremental_sync(
        self, tenant_id: int, since: datetime, batch_size: int = SYNC_BATCH_SIZE
    ) -> dict[str, int]:
        """
        Perform incremental sync of data changed since last run.

        Args:
            tenant_id: Tenant ID
            since: Sync data updated after this time
            batch_size: Rows per round trip

        Returns:
            Dict of entity type -> count synced
        """
        logger.info(f"Starting incremental sync for tenant {tenant_id} since {since}")

        results = {
            "profiles": await self.sync_cdp_profiles(
                tenant_id, since=since, batch_size=batch_size
            ),
            "campaigns": await self.sync_campaigns(
                tenant_id, since=since, batch_size=batch_size
            ),
            "segments": await self.sync_cdp_segments(
                tenant_id, since=since, batch_size=batch_size
            ),
            "events": await self.sync_cdp_events(
                tenant_id, since=since, batch_size=batch_size
            ),
            "signals": await self.sync_signal_health(
                tenant_id, since=since, batch_size=batch_size
            ),
            "trust_gates": await self.sync_trust_gate_decisions(
                tenant_id, since=since, batch_size=batch_size
            ),
            "automations": await self.sync_automation_actions(
                tenant_id, since=since, batch_size=batch_size
            ),
        }

        total = sum(results.values())
        logger.info(
            f"Incremental sync completed for tenant {tenant_id}: {total} entities updated"
        )

        return results

    # =========================================================================
    # REAL-TIME SYNC HOOKS
    # =========================================================================

    async def on_event_ingested(
        self,
        tenant_id: int,
        event_id: UUID,
        event_name: str,
        profile_id: Optional[UUID],
        properties: dict[str, Any],
        event_time: datetime,
    ) -> None:
        """
        Real-time hook called when a CDP event is ingested.

        Args:
            tenant_id: Tenant ID
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
                end_external_id=str(event_id),
            )

    async def on_trust_gate_evaluated(
        self,
        tenant_id: int,
        gate_id: UUID,
        decision: str,
        signal_health: float,
        action_type: str,
        reason: str,
        automation_id: Optional[UUID] = None,
    ) -> None:
        """
        Real-time hook called when a trust gate is evaluated.

        Args:
            tenant_id: Tenant ID
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
            evaluated_at=datetime.now(tz=UTC),
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
                end_external_id=str(automation_id),
            )

    async def on_profile_merged(
        self, tenant_id: int, surviving_profile_id: UUID, merged_profile_id: UUID
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
            properties={"merged_at": datetime.now(tz=UTC).isoformat()},
        )
        await self.kg.create_edge(
            edge,
            start_label=NodeLabel.PROFILE,
            start_external_id=str(merged_profile_id),
            end_label=NodeLabel.PROFILE,
            end_external_id=str(surviving_profile_id),
        )
