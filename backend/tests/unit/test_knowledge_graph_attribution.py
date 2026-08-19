# =============================================================================
# Stratum AI - Loading channels and touchpoints into the knowledge graph
# =============================================================================
"""Closes four of the declared coverage gaps, at the grain the data has.

#709 declared five surfaces unanswerable and recorded the attribution ones as
``blocked_on_schema=False`` — "the sources exist, they are simply not loaded".
Checking the grain shows that was half wrong, and this file encodes both halves.

**Wrong about revenue attribution.** ``daily_attributed_revenue``,
``conversion_paths`` and ``channel_interactions`` are all *period aggregates*:
keyed by (tenant, date, dimension) or (path_hash, period), with no conversion
id. The graph's Revenue nodes are per event (``rev_{event_id}``), so nothing
joins a daily total to an individual revenue event. ``Revenue-[:ATTRIBUTED_TO]->
Channel`` and ``Campaign-[:DROVE]->Revenue`` are not loadable as the queries
were written — that is a grain mismatch in the schema, not a missing loop, and
those gaps are corrected to ``blocked_on_schema=True``.

So the two channel surfaces are served at the grain that does exist: a Channel
node carrying the rollup, read directly, instead of a traversal to per-event
Revenue that can never be populated. The window it summarises is stamped on the
node, because a rollup that does not say what period it covers is the same
class of problem in a smaller costume.

**Right about touchpoints, in a table I had missed.** ``crm.touchpoints`` is
per-touchpoint — contact, timestamp, source, campaign, UTMs — and carries its
own ``email_hash``. CDP hashes email identifiers with
``sha256(value.lower().strip())`` (``hash_identifier`` in endpoints/cdp.py,
unsalted), which is the same convention ``crm_contacts.email_hash`` documents.
So ``Profile-[:RECEIVED]->Touchpoint`` joins on a real key rather than a time
window, and both touchpoint gaps close.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

import pytest

from app.services.knowledge_graph import coverage
from app.services.knowledge_graph.models import ChannelNode, NodeLabel
from app.services.knowledge_graph.sync import KnowledgeGraphSyncService

pytestmark = pytest.mark.unit

TENANT_ID = 42


class _Result:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalars(self) -> "_Result":
        return self

    def all(self) -> list[Any]:
        return self._rows

    def fetchone(self):
        return (self._rows[0],) if self._rows else None

    def __iter__(self):
        return iter(
            self._rows
            if self._rows and isinstance(self._rows[0], tuple)
            else [(r,) for r in self._rows]
        )


class FakeSession:
    """Serves canned pages; records the Cypher the writer emits."""

    def __init__(self, pages: list[list[Any]] | None = None) -> None:
        self._pages = list(pages or [])
        self.commits = 0
        self.cypher: list[str] = []

    async def execute(self, statement: Any, params: Any = None) -> _Result:
        text = str(statement).strip()
        if text.startswith("LOAD") or "search_path" in text or "cypher(" in text:
            self.cypher.append(text)
            return _Result([])
        return _Result(self._pages.pop(0) if self._pages else [])

    async def commit(self) -> None:
        self.commits += 1

    def for_label(self, label: NodeLabel) -> list[str]:
        return [c for c in self.cypher if f":{label.value}" in c]


def _daily_row(dimension_id="meta", revenue=500_000, deals=25, spend=100_000, day=None):
    from app.models.attribution import AttributionModel, DailyAttributedRevenue

    return DailyAttributedRevenue(
        id=uuid4(),
        tenant_id=TENANT_ID,
        date=day or date(2026, 8, 1),
        attribution_model=AttributionModel.LAST_TOUCH,
        dimension_type="platform",
        dimension_id=dimension_id,
        dimension_name=dimension_id.title(),
        attributed_revenue_cents=revenue,
        attributed_deals=deals,
        spend_cents=spend,
    )


def _touchpoint(email_hash="abc123", source="meta", ts=None):
    from app.models.crm import Touchpoint

    return Touchpoint(
        id=uuid4(),
        tenant_id=TENANT_ID,
        contact_id=uuid4(),
        event_ts=ts or datetime.now(UTC),
        event_type="click",
        source=source,
        campaign_id="c-1",
        email_hash=email_hash,
    )


# =============================================================================
# Channels
# =============================================================================
class TestChannelLoad:
    async def test_rolls_daily_rows_up_into_one_node_per_channel(self):
        """Two days of meta becomes one Channel, not two."""
        session = FakeSession(
            [[_daily_row(day=date(2026, 8, 1)), _daily_row(day=date(2026, 8, 2))]]
        )
        sync = KnowledgeGraphSyncService(session)

        synced = await sync.sync_channels(TENANT_ID)

        assert synced == 1
        cypher = session.for_label(NodeLabel.CHANNEL)[0]
        # 500_000 x 2 revenue, 25 x 2 deals, 100_000 x 2 spend
        assert "1000000" in cypher
        assert "50" in cypher

    async def test_separate_channels_stay_separate(self):
        session = FakeSession([[_daily_row("meta"), _daily_row("google")]])
        sync = KnowledgeGraphSyncService(session)

        assert await sync.sync_channels(TENANT_ID) == 2

    async def test_the_node_states_the_window_it_covers(self):
        """A rollup that does not say what period it covers is a wrong number.

        The read route takes a ``days`` parameter; the node is a snapshot. If
        the two disagree and nothing says so, the caller reads a 90-day total
        as a 7-day one.
        """
        session = FakeSession([[_daily_row()]])
        sync = KnowledgeGraphSyncService(session)

        await sync.sync_channels(TENANT_ID, window_days=30)

        cypher = session.for_label(NodeLabel.CHANNEL)[0]
        assert "window_days" in cypher
        assert "30" in cypher

    async def test_roas_is_computed_not_invented(self):
        session = FakeSession([[_daily_row(revenue=400_000, spend=100_000)]])
        sync = KnowledgeGraphSyncService(session)

        await sync.sync_channels(TENANT_ID)

        assert "4.0" in session.for_label(NodeLabel.CHANNEL)[0]

    async def test_zero_spend_does_not_divide(self):
        session = FakeSession([[_daily_row(revenue=1_000, spend=0)]])
        sync = KnowledgeGraphSyncService(session)

        assert await sync.sync_channels(TENANT_ID) == 1

    def test_channel_node_carries_the_rollup_fields(self):
        node = ChannelNode(
            tenant_id=TENANT_ID,
            external_id="meta",
            name="Meta",
            channel_type="paid",
            total_revenue_cents=1_000,
            total_conversions=10,
            spend_cents=500,
            roas=2.0,
            window_days=30,
        )

        props = node.to_cypher_properties()
        assert props["total_conversions"] == 10
        assert props["spend_cents"] == 500
        assert props["window_days"] == 30


# =============================================================================
# Touchpoints
# =============================================================================
class TestTouchpointLoad:
    async def test_creates_a_node_per_touchpoint(self):
        session = FakeSession([[_touchpoint(), _touchpoint()], []])
        sync = KnowledgeGraphSyncService(session)

        synced = await sync.sync_touchpoints(TENANT_ID)

        assert synced == 2
        assert len(session.for_label(NodeLabel.TOUCHPOINT)) >= 2

    async def test_links_to_the_profile_sharing_its_email_hash(self):
        """A key join, not a time-window guess.

        CDP stores sha256(email.lower().strip()) unsalted via hash_identifier;
        crm touchpoints carry the same. That equality is the whole basis for
        this edge — without it there is no honest Profile -> Touchpoint link.
        """
        tp = _touchpoint(email_hash="deadbeef")
        profile_id = uuid4()
        # page 1: touchpoints, page 2: (email_hash, profile_id) resolution
        session = FakeSession([[tp], [("deadbeef", profile_id)], []])
        sync = KnowledgeGraphSyncService(session)

        await sync.sync_touchpoints(TENANT_ID)

        edges = [c for c in session.cypher if "RECEIVED" in c]
        assert edges, "no RECEIVED edge emitted"
        assert str(profile_id) in edges[0]

    async def test_a_touchpoint_with_no_matching_profile_is_still_loaded(self):
        """The node is real even when we cannot attach it to anyone.

        Dropping it would understate touchpoint volume; inventing a profile to
        hang it on would be worse.
        """
        session = FakeSession([[_touchpoint(email_hash="nomatch")], [], []])
        sync = KnowledgeGraphSyncService(session)

        synced = await sync.sync_touchpoints(TENANT_ID)

        assert synced == 1
        assert not [c for c in session.cypher if "RECEIVED" in c]


# =============================================================================
# The declared gaps move accordingly
# =============================================================================
class TestCoverageUpdated:
    def test_the_channel_and_touchpoint_gaps_are_closed(self):
        for closed in (
            "revenue_by_channel",
            "channel_inefficiency",
            "channel_transitions",
            "multi_touch_paths",
        ):
            assert closed not in coverage.GAPS

    def test_the_trust_engine_gaps_remain(self):
        for still_open in (
            "blocked_automations",
            "automation_trace",
            "trust_gate_bottlenecks",
        ):
            assert still_open in coverage.GAPS

    def test_revenue_attribution_is_recorded_as_a_schema_problem(self):
        """Corrects #709, which called this a loading gap.

        daily_attributed_revenue is a period aggregate and Revenue nodes are
        per event, so no amount of loading produces the edge.
        """
        gap = coverage.GAPS["revenue_decline_root_cause"]

        assert gap.blocked_on_schema is True
        assert "aggregate" in gap.reason.lower() or "grain" in gap.reason.lower()

    def test_channel_is_now_a_written_label(self):
        assert "Channel" in coverage.BACKFILLED_NODES
        assert "Touchpoint" in coverage.BACKFILLED_NODES

    def test_received_is_now_a_written_edge(self):
        assert "RECEIVED" in coverage.BACKFILLED_EDGES
