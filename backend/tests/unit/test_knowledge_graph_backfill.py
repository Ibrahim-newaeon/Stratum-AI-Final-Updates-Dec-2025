# =============================================================================
# Stratum AI - Knowledge Graph backfill
# =============================================================================
"""The writer that populates the knowledge graph.

Migration 065 provisioned AGE and created the graph, but ``19ad2c1`` kept
``feature_knowledge_graph`` off for a second reason: nothing ever wrote to it.
``KnowledgeGraphSyncService`` had seven populate methods and a ``full_sync``
orchestrator, and no caller anywhere in the codebase -- so it had never once
been executed against the real schema.

Every assertion in this file pins something that was broken the first time it
was. They are not hypothetical:

* ``GraphNode.tenant_id`` was typed ``UUID``. Tenants are ``Integer`` in this
  database, and the read path already interpolated whatever it was given as a
  string, so reads worked and every write would have raised ValidationError.
* ``sync_trust_gate_decisions`` imported ``TrustGateAuditLog`` from
  ``app.models.trust_layer``. No such class exists anywhere in the repo.
* ``sync_campaigns`` read ``platform_campaign_id``, ``budget_cents`` and
  ``spend_cents`` off ``Campaign``, which has none of the three.
* ``sync_cdp_segments`` called ``.value`` on ``segment_type``, a plain String.
* ``sync_signal_health`` passed ``issues`` -- a Text column holding JSON --
  straight into a ``list[str]`` field.
* Every query was capped at ``.limit(1000)`` with no pagination, so a backfill
  of a tenant with more than a thousand of anything would silently stop there
  and report success.
* Nothing in the module ever committed. The API routes are all GETs, so it had
  never mattered; a backfill that does not commit writes nothing at all.

The last two are the dangerous ones, and they are the reason this file exists
rather than a script that just calls ``full_sync``: both fail by *reporting
success while doing nothing*, which is exactly the shape the flag was held
shut to avoid.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from app.services.knowledge_graph.models import NodeLabel, ProfileNode
from app.services.knowledge_graph.queries import CypherQueryBuilder
from app.services.knowledge_graph.sync import KnowledgeGraphSyncService

pytestmark = pytest.mark.unit

BACKEND_DIR = Path(__file__).resolve().parents[2]
SCRIPT_PATH = BACKEND_DIR / "scripts" / "backfill_knowledge_graph.py"

TENANT_ID = 42


def load_script():
    """Import the backfill script by path -- ``scripts/`` is not a package.

    Registered in ``sys.modules`` before execution because ``@dataclass``
    resolves annotations through ``sys.modules[cls.__module__]``, which is None
    for a module that has not been installed there yet.
    """
    if "backfill_knowledge_graph" in sys.modules:
        return sys.modules["backfill_knowledge_graph"]
    spec = importlib.util.spec_from_file_location(
        "backfill_knowledge_graph", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# =============================================================================
# Test doubles
# =============================================================================
class _ScalarResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalars(self) -> _ScalarResult:
        return self

    def all(self) -> list[Any]:
        return self._rows

    def fetchone(self):
        return (self._rows[0],) if self._rows else None

    def scalar(self):
        return self._rows[0] if self._rows else None

    def __iter__(self):
        return iter((row,) for row in self._rows)


class FakeSession:
    """Serves canned pages of ORM rows and records commits.

    Statements are routed by content: anything AGE-related is swallowed and
    answered empty, anything else pops the next page. That lets a sync method
    run end to end -- real query construction, real Pydantic nodes, real Cypher
    strings -- with no database.
    """

    def __init__(self, pages: list[list[Any]] | None = None) -> None:
        self._pages = list(pages or [])
        self.commits = 0
        self.graph_statements: list[str] = []
        self.data_statements: list[str] = []

    async def execute(self, statement: Any, params: Any = None) -> _ScalarResult:
        rendered = str(statement).strip()
        if (
            rendered.startswith("LOAD")
            or "search_path" in rendered
            or "cypher(" in rendered
        ):
            self.graph_statements.append(rendered)
            return _ScalarResult([])
        self.data_statements.append(rendered)
        return _ScalarResult(self._pages.pop(0) if self._pages else [])

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:  # pragma: no cover - safety net only
        pass

    def cypher_for(self, label: NodeLabel) -> list[str]:
        needle = f":{label.value}"
        return [s for s in self.graph_statements if needle in s]


# =============================================================================
# Tenant identity: the graph and the database must agree
# =============================================================================
class TestTenantIdentity:
    def test_graph_node_accepts_the_integer_tenant_id_the_database_uses(self):
        """``tenants.id`` is ``Integer``. A UUID-typed field rejects every write.

        Nothing in this schema has a UUID tenant. The annotation described a
        database that does not exist, and because only the *write* path runs
        it through Pydantic, the mismatch was invisible from the read routes.
        """
        node = ProfileNode(tenant_id=TENANT_ID, external_id="p1")

        assert node.tenant_id == TENANT_ID

    def test_written_and_queried_tenant_literals_match(self):
        """Both sides land on the same Cypher literal or the graph partitions.

        The read path interpolates ``tenant_id`` into the Cypher text; the
        write path stringifies it into node properties. If those two ever
        disagree on representation, every query returns nothing and the graph
        looks empty rather than broken.
        """
        written = ProfileNode(
            tenant_id=TENANT_ID, external_id="p1"
        ).to_cypher_properties()["tenant_id"]

        queried, _params = (
            CypherQueryBuilder(TENANT_ID)
            .match_node("n", NodeLabel.PROFILE)
            .return_fields(["n"])
            .build()
        )

        assert written == str(TENANT_ID)
        assert f"n.tenant_id = '{written}'" in queried


# =============================================================================
# Completeness: a capped backfill is a silent partial backfill
# =============================================================================
class TestPagination:
    async def test_sync_walks_past_the_first_page(self):
        """The old code issued one SELECT capped at 1000 rows and stopped.

        A tenant with 50k profiles would have been reported as a complete
        backfill of 1000. The graph then answers questions about 2% of the
        customer base with no indication that is what it is doing.
        """
        profiles = [_profile() for _ in range(5)]
        session = FakeSession([profiles[0:2], profiles[2:4], profiles[4:5]])
        sync = KnowledgeGraphSyncService(session)

        synced = await sync.sync_cdp_profiles(TENANT_ID, batch_size=2)

        assert synced == 5

    async def test_sync_stops_on_a_short_page(self):
        """A page shorter than the batch size is the last one -- no extra query."""
        session = FakeSession([[_profile()]])
        sync = KnowledgeGraphSyncService(session)

        synced = await sync.sync_cdp_profiles(TENANT_ID, batch_size=10)

        assert synced == 1
        assert len(session.data_statements) == 1

    async def test_pagination_is_keyset_not_offset(self):
        """OFFSET over an unordered query skips and duplicates rows.

        None of these tables had an ORDER BY, so paging by offset would have
        been silently lossy. Keyset paging on the primary key is both stable
        and index-backed.
        """
        profiles = [_profile() for _ in range(4)]
        session = FakeSession([profiles[0:2], profiles[2:4], []])
        sync = KnowledgeGraphSyncService(session)

        await sync.sync_cdp_profiles(TENANT_ID, batch_size=2)

        assert "ORDER BY" in session.data_statements[0].upper()
        assert "OFFSET" not in session.data_statements[1].upper()
        assert "cdp_profiles.id >" in session.data_statements[1]


# =============================================================================
# Durability: an uncommitted backfill writes nothing
# =============================================================================
class TestDurability:
    async def test_sync_commits_each_batch(self):
        """Nothing in the knowledge_graph package had ever called commit().

        It had never mattered, because every route that reached this code was
        a GET. A backfill that does not commit logs its counts, rolls back at
        session close, and leaves an empty graph behind.
        """
        session = FakeSession([[_profile(), _profile()], [_profile()]])
        sync = KnowledgeGraphSyncService(session)

        await sync.sync_cdp_profiles(TENANT_ID, batch_size=2)

        assert session.commits == 2


# =============================================================================
# Schema alignment: every one of these referenced a column that is not there
# =============================================================================
class TestSchemaAlignment:
    async def test_trust_gate_sync_reads_the_enforcement_audit_log(self):
        """``TrustGateAuditLog`` does not exist. ``EnforcementAuditLog`` does.

        The import was inside the method body, so the module still imported
        cleanly and the failure waited until the first call.
        """
        from app.models.autopilot import (
            EnforcementAuditLog,
            EnforcementMode,
            InterventionAction,
            ViolationType,
        )

        row = EnforcementAuditLog(
            id=uuid4(),
            tenant_id=TENANT_ID,
            timestamp=datetime.now(UTC),
            action_type="budget_increase",
            entity_type="campaign",
            entity_id="c-1",
            violation_type=ViolationType.ROAS_BELOW_THRESHOLD,
            intervention_action=InterventionAction.BLOCKED,
            enforcement_mode=EnforcementMode.HARD_BLOCK,
            details={"signal_health_score": 41.0, "threshold": 70.0},
        )
        session = FakeSession([[row]])
        sync = KnowledgeGraphSyncService(session)

        synced = await sync.sync_trust_gate_decisions(TENANT_ID)

        assert synced == 1
        assert session.cypher_for(NodeLabel.TRUST_GATE)

    async def test_campaign_sync_uses_columns_the_table_actually_has(self):
        """``platform_campaign_id``/``budget_cents``/``spend_cents`` are invented.

        The real columns are ``external_id``, ``daily_budget_cents`` /
        ``lifetime_budget_cents``, and ``total_spend_cents``.
        """
        from app.base_models import AdPlatform, Campaign, CampaignStatus

        row = Campaign(
            id=7,
            tenant_id=TENANT_ID,
            platform=AdPlatform.META,
            external_id="23847",
            account_id="act_1",
            name="Prospecting",
            status=CampaignStatus.ACTIVE,
            objective="conversions",
            daily_budget_cents=50_000,
            total_spend_cents=31_255,
            impressions=120_000,
            clicks=3_400,
            conversions=210,
            revenue_cents=98_000,
            roas=3.13,
        )
        session = FakeSession([[row]])
        sync = KnowledgeGraphSyncService(session)

        synced = await sync.sync_campaigns(TENANT_ID)

        assert synced == 1
        cypher = session.cypher_for(NodeLabel.CAMPAIGN)[0]
        assert "'23847'" in cypher
        assert "31255" in cypher

    async def test_segment_sync_handles_a_plain_string_segment_type(self):
        """``CDPSegment.segment_type`` is ``String(50)``, not an Enum column.

        ``segment.segment_type.value`` raises AttributeError on every row that
        has one -- which is every row, since the column is NOT NULL.
        """
        from app.models.cdp import CDPSegment

        row = CDPSegment(
            id=uuid4(),
            tenant_id=TENANT_ID,
            name="High LTV",
            segment_type="dynamic",
            rules={"op": "gt", "field": "ltv", "value": 500},
            profile_count=12,
        )
        session = FakeSession([[row], []])
        sync = KnowledgeGraphSyncService(session)

        synced = await sync.sync_cdp_segments(TENANT_ID)

        assert synced == 1
        assert "'dynamic'" in session.cypher_for(NodeLabel.SEGMENT)[0]

    async def test_signal_sync_parses_the_json_issues_text(self):
        """``issues`` is a Text column holding a JSON array, not a list.

        ``SignalNode.issues`` is ``list[str]``; handing it the raw string makes
        Pydantic either reject it or, worse, iterate it into characters.
        """
        from app.models.trust_layer import FactSignalHealthDaily, SignalHealthStatus

        row = FactSignalHealthDaily(
            id=uuid4(),
            tenant_id=TENANT_ID,
            date=date(2026, 8, 1),
            platform="meta",
            emq_score=64.0,
            status=SignalHealthStatus.RISK,
            issues=json.dumps(["capi_gap", "stale_feed"]),
        )
        session = FakeSession([[row]])
        sync = KnowledgeGraphSyncService(session)

        synced = await sync.sync_signal_health(TENANT_ID)

        assert synced == 1
        cypher = session.cypher_for(NodeLabel.SIGNAL)[0]
        assert "capi_gap" in cypher
        assert "stale_feed" in cypher

    async def test_signal_sync_survives_a_null_issues_column(self):
        """``issues`` is nullable, and most rows leave it null."""
        from app.models.trust_layer import FactSignalHealthDaily, SignalHealthStatus

        row = FactSignalHealthDaily(
            id=uuid4(),
            tenant_id=TENANT_ID,
            date=date(2026, 8, 1),
            platform="meta",
            emq_score=88.0,
            status=SignalHealthStatus.OK,
            issues=None,
        )
        session = FakeSession([[row]])
        sync = KnowledgeGraphSyncService(session)

        assert await sync.sync_signal_health(TENANT_ID) == 1

    async def test_signal_status_maps_the_lowercase_enum_values(self):
        """``SignalHealthStatus`` values are lowercase: ok/risk/degraded/critical.

        The old map keyed on "OK"/"RISK"/"CRITICAL", so every row fell through
        to the default and the whole platform read as DEGRADED.
        """
        from app.models.trust_layer import FactSignalHealthDaily, SignalHealthStatus

        row = FactSignalHealthDaily(
            id=uuid4(),
            tenant_id=TENANT_ID,
            date=date(2026, 8, 1),
            platform="meta",
            emq_score=92.0,
            status=SignalHealthStatus.OK,
        )
        session = FakeSession([[row]])
        sync = KnowledgeGraphSyncService(session)

        await sync.sync_signal_health(TENANT_ID)

        assert "'healthy'" in session.cypher_for(NodeLabel.SIGNAL)[0]


# =============================================================================
# The script
# =============================================================================
class TestBackfillScript:
    def test_script_exists(self):
        assert SCRIPT_PATH.exists(), f"missing backfill script at {SCRIPT_PATH}"

    async def test_refuses_to_run_when_the_graph_is_not_provisioned(self):
        """Without migration 065 the graph schema is absent and every MERGE errors.

        Failing here, before any tenant is touched, is the difference between
        one clear message and a stack trace per entity type per tenant.
        """
        script = load_script()
        session = FakeSession([[None]])  # to_regnamespace(...) -> NULL

        with pytest.raises(script.GraphNotProvisioned) as exc:
            await script.ensure_graph_provisioned(session)

        assert "065" in str(exc.value)

    async def test_accepts_a_provisioned_graph(self):
        script = load_script()
        session = FakeSession([["stratum_knowledge_graph"]])

        await script.ensure_graph_provisioned(session)

    async def test_reports_an_empty_backfill_as_a_problem(self):
        """Zero written is the failure this whole exercise exists to avoid.

        "Backfill complete" over a total of 0 reads as success and is the exact
        shape of the empty-graph problem the feature flag was held shut for.
        """
        script = load_script()

        result = script.summarize({1: {"profiles": 0, "events": 0}})

        assert result.total == 0
        assert not result.ok
        assert "nothing" in result.message.lower()

    async def test_reports_a_populated_backfill_as_success(self):
        script = load_script()

        result = script.summarize({1: {"profiles": 12, "events": 300}})

        assert result.total == 312
        assert result.ok

    async def test_a_failing_tenant_does_not_hide_behind_a_zero(self):
        """A tenant that raised is not a tenant that had no data."""
        script = load_script()

        result = script.summarize({1: {"profiles": 5}, 2: None})

        assert not result.ok
        assert "2" in result.message


# =============================================================================
# Helpers
# =============================================================================
def _profile():
    from app.models.cdp import CDPProfile, LifecycleStage

    return CDPProfile(
        id=uuid4(),
        tenant_id=TENANT_ID,
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
        lifecycle_stage=LifecycleStage.CUSTOMER,
        total_events=3,
        total_sessions=2,
        total_purchases=1,
        total_revenue=120,
        profile_data={},
        computed_traits={},
    )
