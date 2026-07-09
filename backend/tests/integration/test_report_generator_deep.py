# =============================================================================
# Stratum AI - Report Generator Deep Integration Tests (#342 Batch 4)
# =============================================================================
"""Deep integration coverage for ``app.services.reporting.report_generator``.

Strategy
--------
* Collectors are exercised against the real scratch database with seeded
  rows, and their aggregation/serialization logic is additionally covered
  by mocking at the DB-session boundary (``AsyncMock`` execute) so every
  line runs deterministically.
* ``ReportGenerator.generate_report`` is run end-to-end against the real DB
  for JSON / CSV / PDF / fallback formats, the failure path, and the
  template-not-found path.

Regression coverage for the #537 fixes (previously pinned as bugs, now
asserting the corrected behavior):

* BUG-1 ``collect_campaign_performance`` reads the real
  ``app.base_models.Campaign`` columns (``is_deleted``,
  ``total_spend_cents``, ``revenue_cents``, ``conversions``) and converts
  cents to dollars — campaign_performance and executive_summary no longer
  crash.
* BUG-2 ``collect_pacing_status`` reads ``Target.metric_type`` and reports
  only the columns that exist (no phantom ``current_value``).
* BUG-3 ``collect_profit_roas`` reads ``gross_revenue_cents`` /
  ``total_cogs_cents`` / ``ad_spend_cents`` / ``gross_profit_roas``.
* BUG-4 ``generate_report`` catches ``Exception`` so ANY collector failure
  moves the ReportExecution to a committed FAILED state.

NOTE: ``ReportGenerator.parse_date_range`` already has a dedicated unit
suite (tests/unit/test_report_date_range.py); only a compact smoke test is
kept here so this module's isolated coverage run still executes the branch
lines.
"""

import json
import types
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.orm import DeclarativeBase

from app.models.crm import (
    CRMConnection,
    CRMConnectionStatus,
    CRMDeal,
    CRMProvider,
    DailyPipelineMetrics,
)
from app.models.pacing import (
    AlertSeverity,
    AlertType,
    PacingAlert,
    Target,
    TargetMetric,
    TargetPeriod,
)
from app.models.profit import DailyProfitMetrics
from app.models.reporting import (
    ExecutionStatus,
    ReportExecution,
    ReportFormat,
    ReportTemplate,
    ReportType,
)
from app.services.reporting.report_generator import (
    ReportDataCollector,
    ReportGenerator,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

TODAY = date(2026, 7, 1)
START = TODAY - timedelta(days=6)
END = TODAY


# =============================================================================
# Helpers
# =============================================================================


def _mock_result(items):
    """Build a mock SQLAlchemy result whose .scalars().all() returns items."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = list(items)
    return result


def _mock_db(*result_batches):
    """AsyncSession stand-in whose execute() yields the given result sets."""
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[_mock_result(b) for b in result_batches])
    return db


async def _make_template(db_session, tenant_id, report_type, name, config=None):
    template = ReportTemplate(
        tenant_id=tenant_id,
        name=name,
        description=f"{name} description",
        report_type=report_type,
        config=config or {},
    )
    db_session.add(template)
    await db_session.flush()
    return template


async def _seed_crm_connection(db_session, tenant_id) -> CRMConnection:
    conn = CRMConnection(
        tenant_id=tenant_id,
        provider=CRMProvider.HUBSPOT,
        status=CRMConnectionStatus.CONNECTED,
    )
    db_session.add(conn)
    await db_session.flush()
    return conn


def _won_at(day: date) -> datetime:
    return datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc) + timedelta(
        hours=12
    )


async def _seed_deals(db_session, tenant_id) -> None:
    """4 in-period won deals, 1 lost deal, 1 out-of-period won deal."""
    conn = await _seed_crm_connection(db_session, tenant_id)
    deals = [
        # counted
        CRMDeal(
            tenant_id=tenant_id,
            connection_id=conn.id,
            crm_deal_id="deal-1",
            amount=1000.0,
            is_won=True,
            won_at=_won_at(START + timedelta(days=1)),
            attributed_platform="meta",
            attributed_campaign_id="c1",
        ),
        CRMDeal(
            tenant_id=tenant_id,
            connection_id=conn.id,
            crm_deal_id="deal-2",
            amount=500.0,
            is_won=True,
            won_at=_won_at(START + timedelta(days=2)),
            attributed_platform="meta",
            attributed_campaign_id=None,  # -> "unattributed" campaign bucket
        ),
        CRMDeal(
            tenant_id=tenant_id,
            connection_id=conn.id,
            crm_deal_id="deal-3",
            amount=2000.0,
            is_won=True,
            won_at=_won_at(END),
            attributed_platform=None,  # -> "unattributed" platform bucket
            attributed_campaign_id="c2",
        ),
        CRMDeal(  # repeats campaign c1 -> exercises the existing-bucket branch
            tenant_id=tenant_id,
            connection_id=conn.id,
            crm_deal_id="deal-6",
            amount=300.0,
            is_won=True,
            won_at=_won_at(START + timedelta(days=3)),
            attributed_platform="google",
            attributed_campaign_id="c1",
        ),
        # excluded: not won
        CRMDeal(
            tenant_id=tenant_id,
            connection_id=conn.id,
            crm_deal_id="deal-4",
            amount=9999.0,
            is_won=False,
        ),
        # excluded: won before period
        CRMDeal(
            tenant_id=tenant_id,
            connection_id=conn.id,
            crm_deal_id="deal-5",
            amount=8888.0,
            is_won=True,
            won_at=_won_at(START - timedelta(days=3)),
        ),
    ]
    db_session.add_all(deals)
    await db_session.flush()


async def _seed_pipeline_metrics(db_session, tenant_id) -> None:
    rows = [
        DailyPipelineMetrics(
            tenant_id=tenant_id,
            date=START + timedelta(days=1),
            leads_created=10,
            mqls_created=5,
            sqls_created=2,
            deals_won=1,
            pipeline_value_cents=250_000,
            won_revenue_cents=100_000,
        ),
        DailyPipelineMetrics(
            tenant_id=tenant_id,
            date=START + timedelta(days=2),
            leads_created=10,
            mqls_created=3,
            sqls_created=2,
            deals_won=1,
            pipeline_value_cents=150_000,
            won_revenue_cents=50_000,
        ),
        # excluded: outside the range
        DailyPipelineMetrics(
            tenant_id=tenant_id,
            date=START - timedelta(days=10),
            leads_created=77,
            mqls_created=77,
            sqls_created=77,
            deals_won=77,
            pipeline_value_cents=1,
            won_revenue_cents=1,
        ),
    ]
    db_session.add_all(rows)
    await db_session.flush()


# =============================================================================
# Fake Campaign entity used to cover collect_campaign_performance's logic at
# the DB-session boundary. Mirrors the real Campaign schema the collector now
# queries (``is_deleted`` + cents columns) so select() builds cleanly.
# =============================================================================


class _FakeBase(DeclarativeBase):
    pass


class _FakeCampaign(_FakeBase):
    __tablename__ = "_fake_campaigns_reportgen_deep"

    id = sa.Column(sa.Integer, primary_key=True)
    tenant_id = sa.Column(sa.Integer)
    is_deleted = sa.Column(sa.Boolean)
    platform = sa.Column(sa.String(50))
    total_spend_cents = sa.Column(sa.Integer)
    revenue_cents = sa.Column(sa.Integer)
    conversions = sa.Column(sa.Integer)


def _fake_campaign_row(
    name,
    platform_value,
    status_value,
    spend,
    revenue,
    conversions,
):
    """Build a campaign row. ``spend``/``revenue`` are given in dollars and
    stored as cents to mirror the real model."""
    return types.SimpleNamespace(
        id=uuid4(),
        name=name,
        platform=(
            types.SimpleNamespace(value=platform_value) if platform_value else None
        ),
        status=types.SimpleNamespace(value=status_value) if status_value else None,
        total_spend_cents=round(spend * 100),
        revenue_cents=round(revenue * 100),
        conversions=conversions,
    )


# =============================================================================
# Collector: attribution summary (real DB)
# =============================================================================


class TestCollectAttributionSummary:
    async def test_empty_period_returns_zero_summary(self, db_session, test_tenant):
        collector = ReportDataCollector(db_session, test_tenant["id"])
        data = await collector.collect_attribution_summary(START, END, {})

        assert data["summary"] == {
            "total_deals": 0,
            "total_revenue": 0,
            "avg_deal_size": 0,
        }
        assert data["by_platform"] == {}
        assert data["by_campaign"] == {}
        assert data["period"] == {
            "start_date": START.isoformat(),
            "end_date": END.isoformat(),
        }

    async def test_groups_won_deals_by_platform_and_campaign(
        self, db_session, test_tenant
    ):
        await _seed_deals(db_session, test_tenant["id"])
        collector = ReportDataCollector(db_session, test_tenant["id"])

        data = await collector.collect_attribution_summary(START, END, {})

        assert data["summary"]["total_deals"] == 4
        assert data["summary"]["total_revenue"] == pytest.approx(3800.0)
        assert data["summary"]["avg_deal_size"] == pytest.approx(3800.0 / 4)

        assert data["by_platform"]["meta"] == {"deals": 2, "revenue": 1500.0}
        assert data["by_platform"]["google"] == {"deals": 1, "revenue": 300.0}
        assert data["by_platform"]["unattributed"] == {"deals": 1, "revenue": 2000.0}

        assert data["by_campaign"]["c1"] == {"deals": 2, "revenue": 1300.0}
        assert data["by_campaign"]["c2"] == {"deals": 1, "revenue": 2000.0}
        assert data["by_campaign"]["unattributed"] == {"deals": 1, "revenue": 500.0}


# =============================================================================
# Collector: pipeline metrics (real DB)
# =============================================================================


class TestCollectPipelineMetrics:
    async def test_empty_period_skips_funnel_rates(self, db_session, test_tenant):
        collector = ReportDataCollector(db_session, test_tenant["id"])
        data = await collector.collect_pipeline_metrics(START, END, {})

        assert data["summary"]["total_leads"] == 0
        assert data["daily"] == []
        assert data["funnel"] == {"lead_to_mql": 0, "mql_to_sql": 0, "sql_to_won": 0}

    async def test_totals_daily_rows_and_funnel(self, db_session, test_tenant):
        await _seed_pipeline_metrics(db_session, test_tenant["id"])
        collector = ReportDataCollector(db_session, test_tenant["id"])

        data = await collector.collect_pipeline_metrics(START, END, {})

        assert len(data["daily"]) == 2  # out-of-range row excluded
        assert data["daily"][0]["date"] == (START + timedelta(days=1)).isoformat()
        assert data["daily"][0]["pipeline_value"] == 2500.0
        assert data["daily"][0]["won_revenue"] == 1000.0

        s = data["summary"]
        assert s["total_leads"] == 20
        assert s["total_mqls"] == 8
        assert s["total_sqls"] == 4
        assert s["total_won"] == 2
        assert s["total_pipeline_value"] == 4000.0
        assert s["total_won_revenue"] == 1500.0

        assert data["funnel"]["lead_to_mql"] == 40.0
        assert data["funnel"]["mql_to_sql"] == 50.0
        assert data["funnel"]["sql_to_won"] == 50.0


# =============================================================================
# Collector: pacing status
# =============================================================================


class TestCollectPacingStatus:
    async def test_alerts_without_targets(self, db_session, test_tenant):
        """With zero targets the collector works; alerts are serialized."""
        tenant_id = test_tenant["id"]
        db_session.add_all(
            [
                PacingAlert(
                    tenant_id=tenant_id,
                    alert_type=AlertType.OVERPACING_SPEND,
                    severity=AlertSeverity.CRITICAL,
                    title="Overpacing",
                    message="Spend is 30% over plan",
                    pacing_date=TODAY,
                ),
                # excluded by the created_at >= start filter
                PacingAlert(
                    tenant_id=tenant_id,
                    alert_type=AlertType.UNDERPACING_SPEND,
                    severity=AlertSeverity.INFO,
                    title="Old alert",
                    message="ancient history",
                    pacing_date=START - timedelta(days=30),
                    created_at=datetime.now(timezone.utc) - timedelta(days=365),
                ),
            ]
        )
        await db_session.flush()

        collector = ReportDataCollector(db_session, tenant_id)
        data = await collector.collect_pacing_status(START, END, {})

        assert data["summary"]["total_targets"] == 0
        assert data["targets"] == []
        assert len(data["recent_alerts"]) == 1
        alert = data["recent_alerts"][0]
        assert alert["type"] == "overpacing_spend"
        assert alert["severity"] == "critical"
        assert alert["message"] == "Spend is 30% over plan"
        assert alert["created_at"]  # iso string

    async def test_active_target_serialized_from_real_columns(
        self, db_session, test_tenant
    ):
        """An active Target is reported via its real ``metric_type`` column;
        the phantom ``current_value`` field is not emitted."""
        db_session.add(
            Target(
                tenant_id=test_tenant["id"],
                name="July spend",
                period_type=TargetPeriod.MONTHLY,
                period_start=START,
                period_end=END,
                metric_type=TargetMetric.SPEND,
                target_value=10_000.0,
                is_active=True,
            )
        )
        await db_session.flush()

        collector = ReportDataCollector(db_session, test_tenant["id"])
        data = await collector.collect_pacing_status(START, END, {})

        assert data["summary"]["total_targets"] == 1
        (target,) = data["targets"]
        assert target["name"] == "July spend"
        assert target["metric"] == "spend"
        assert target["target_value"] == pytest.approx(10_000.0)
        assert "current_value" not in target
        assert "progress_pct" not in target

    async def test_target_loop_logic_with_service_boundary_mock(self, test_tenant):
        """Covers the target/alert serialization loop against mocked rows."""
        targets = [
            types.SimpleNamespace(
                id=uuid4(),
                name="Spend target",
                metric_type=TargetMetric.SPEND,
                target_value=1000.0,
            ),
            types.SimpleNamespace(
                id=uuid4(),
                name="No metric target",
                metric_type=None,  # -> "unknown" branch
                target_value=None,
            ),
        ]
        alerts = [
            types.SimpleNamespace(
                alert_type=AlertType.ROAS_BELOW_TARGET,
                severity=AlertSeverity.WARNING,
                message="ROAS slipping",
                created_at=datetime(2026, 7, 1, 8, 0, tzinfo=timezone.utc),
            ),
            types.SimpleNamespace(
                alert_type=None,  # -> "unknown" branches
                severity=None,
                message="mystery",
                created_at=datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc),
            ),
        ]
        collector = ReportDataCollector(_mock_db(targets, alerts), test_tenant["id"])

        data = await collector.collect_pacing_status(START, END, {})

        assert data["summary"]["total_targets"] == 2
        t0, t1 = data["targets"]
        assert t0["metric"] == "spend"
        assert t0["target_value"] == 1000.0
        assert t1["metric"] == "unknown"
        assert "current_value" not in t0
        assert "progress_pct" not in t0

        a0, a1 = data["recent_alerts"]
        assert a0["type"] == "roas_below_target"
        assert a0["severity"] == "warning"
        assert a1["type"] == "unknown"
        assert a1["severity"] == "unknown"


# =============================================================================
# Collector: profit ROAS
# =============================================================================


class TestCollectProfitRoas:
    async def test_empty_period_returns_zero_summary(self, db_session, test_tenant):
        collector = ReportDataCollector(db_session, test_tenant["id"])
        data = await collector.collect_profit_roas(START, END, {})

        assert data["summary"] == {
            "total_revenue": 0.0,
            "total_cogs": 0.0,
            "total_gross_profit": 0.0,
            "total_spend": 0.0,
            "profit_roas": 0,
            "gross_margin_pct": 0,
        }
        assert data["daily"] == []

    async def test_seeded_row_aggregates_from_real_columns(
        self, db_session, test_tenant
    ):
        """A seeded DailyProfitMetrics row is aggregated via its real
        ``gross_revenue_cents`` / ``total_cogs_cents`` / ``ad_spend_cents`` /
        ``gross_profit_roas`` columns."""
        db_session.add(
            DailyProfitMetrics(
                tenant_id=test_tenant["id"],
                date=START + timedelta(days=1),
                gross_revenue_cents=100_000,
                total_cogs_cents=40_000,
                ad_spend_cents=50_000,
                gross_profit_cents=60_000,
            )
        )
        await db_session.flush()

        collector = ReportDataCollector(db_session, test_tenant["id"])
        data = await collector.collect_profit_roas(START, END, {})

        s = data["summary"]
        assert s["total_revenue"] == 1000.0
        assert s["total_cogs"] == 400.0
        assert s["total_gross_profit"] == 600.0
        assert s["total_spend"] == 500.0
        assert s["profit_roas"] == 1.2  # 60000 / 50000
        assert s["gross_margin_pct"] == 60.0

        assert len(data["daily"]) == 1
        day = data["daily"][0]
        assert day["revenue"] == 1000.0
        assert day["gross_profit"] == 600.0
        assert day["profit_roas"] is None  # gross_profit_roas not set on the row

    async def test_aggregation_logic_with_service_boundary_mock(self, test_tenant):
        """Covers the cents accumulation/rounding over mocked rows."""
        rows = [
            types.SimpleNamespace(
                date=START,
                gross_revenue_cents=100_000,
                total_cogs_cents=40_000,
                ad_spend_cents=50_000,
                gross_profit_cents=60_000,
                gross_profit_roas=1.2,
            ),
            types.SimpleNamespace(  # all-None row -> `or 0` branches
                date=START + timedelta(days=1),
                gross_revenue_cents=None,
                total_cogs_cents=None,
                ad_spend_cents=None,
                gross_profit_cents=None,
                gross_profit_roas=None,
            ),
        ]
        collector = ReportDataCollector(_mock_db(rows), test_tenant["id"])

        data = await collector.collect_profit_roas(START, END, {})

        assert data["summary"]["total_revenue"] == 1000.0
        assert data["summary"]["total_cogs"] == 400.0
        assert data["summary"]["total_gross_profit"] == 600.0
        assert data["summary"]["total_spend"] == 500.0
        assert data["summary"]["profit_roas"] == 1.2
        assert data["summary"]["gross_margin_pct"] == 60.0

        assert data["daily"][0] == {
            "date": START.isoformat(),
            "revenue": 1000.0,
            "cogs": 400.0,
            "gross_profit": 600.0,
            "spend": 500.0,
            "profit_roas": 1.2,
        }
        assert data["daily"][1]["revenue"] == 0.0
        assert data["daily"][1]["profit_roas"] is None


# =============================================================================
# Collector: campaign performance
# =============================================================================


class TestCollectCampaignPerformance:
    async def test_empty_period_returns_zero_summary(self, db_session, test_tenant):
        """With no campaigns the collector returns an empty, zeroed report."""
        collector = ReportDataCollector(db_session, test_tenant["id"])
        data = await collector.collect_campaign_performance(START, END, {})

        assert data["summary"]["total_campaigns"] == 0
        assert data["summary"]["total_spend"] == 0
        assert data["summary"]["overall_roas"] == 0
        assert data["campaigns"] == []
        assert data["by_platform"] == {}

    async def test_executive_summary_runs_with_empty_data(
        self, db_session, test_tenant
    ):
        collector = ReportDataCollector(db_session, test_tenant["id"])
        data = await collector.collect_executive_summary(START, END, {})

        assert data["highlights"]["total_spend"] == 0
        assert data["highlights"]["overall_roas"] == 0
        assert data["highlights"]["deals_won"] == 0

    async def test_aggregation_logic_with_service_boundary_mock(
        self, test_tenant, monkeypatch
    ):
        """Covers rollups/ROAS math using a schema-compatible fake entity."""
        import app.models as models_pkg

        monkeypatch.setattr(models_pkg, "Campaign", _FakeCampaign)

        campaigns = [
            _fake_campaign_row("Alpha", "meta", "active", 100.0, 300.0, 5),
            _fake_campaign_row("Beta", None, None, 0.0, 50.0, 2),  # unknown + roas 0
            _fake_campaign_row("Gamma", "meta", "paused", 100.0, 100.0, 3),
        ]
        collector = ReportDataCollector(_mock_db(campaigns), test_tenant["id"])

        config = {"filters": {"platforms": ["meta", "google"]}}
        data = await collector.collect_campaign_performance(START, END, config)

        assert data["summary"]["total_campaigns"] == 3
        assert data["summary"]["total_spend"] == 200.0
        assert data["summary"]["total_revenue"] == 450.0
        assert data["summary"]["total_conversions"] == 10
        assert data["summary"]["overall_roas"] == 2.25

        by_name = {c["name"]: c for c in data["campaigns"]}
        assert by_name["Alpha"]["roas"] == 3.0
        assert by_name["Alpha"]["platform"] == "meta"
        assert by_name["Alpha"]["status"] == "active"
        assert by_name["Beta"]["roas"] == 0  # zero-spend branch
        assert by_name["Beta"]["platform"] == "unknown"
        assert by_name["Beta"]["status"] == "unknown"

        assert data["by_platform"]["meta"] == {
            "spend": 200.0,
            "revenue": 400.0,
            "conversions": 8,
        }
        assert data["by_platform"]["unknown"]["revenue"] == 50.0

    async def test_no_platform_filter_and_zero_spend_overall(
        self, test_tenant, monkeypatch
    ):
        """No filters config + zero total spend -> overall_roas stays 0."""
        import app.models as models_pkg

        monkeypatch.setattr(models_pkg, "Campaign", _FakeCampaign)

        campaigns = [_fake_campaign_row("ZeroSpend", "meta", "active", 0.0, 10.0, 1)]
        collector = ReportDataCollector(_mock_db(campaigns), test_tenant["id"])

        data = await collector.collect_campaign_performance(START, END, {})

        assert data["summary"]["total_spend"] == 0.0
        assert data["summary"]["overall_roas"] == 0
        assert data["campaigns"][0]["roas"] == 0


# =============================================================================
# Collector: executive summary composition (collector-boundary mock)
# =============================================================================


class TestCollectExecutiveSummary:
    async def test_composes_highlights_from_sub_collectors(self, test_tenant):
        collector = ReportDataCollector(MagicMock(), test_tenant["id"])
        campaign_data = {
            "summary": {
                "total_spend": 100.0,
                "total_revenue": 250.0,
                "overall_roas": 2.5,
            }
        }
        attribution_data = {"summary": {"total_deals": 4}}
        pipeline_data = {"summary": {"total_pipeline_value": 9000.0}}
        collector.collect_campaign_performance = AsyncMock(return_value=campaign_data)
        collector.collect_attribution_summary = AsyncMock(return_value=attribution_data)
        collector.collect_pipeline_metrics = AsyncMock(return_value=pipeline_data)

        data = await collector.collect_executive_summary(START, END, {"x": 1})

        assert data["highlights"] == {
            "total_spend": 100.0,
            "total_revenue": 250.0,
            "overall_roas": 2.5,
            "deals_won": 4,
            "pipeline_value": 9000.0,
        }
        assert data["campaigns"] is campaign_data
        assert data["attribution"] is attribution_data
        assert data["pipeline"] is pipeline_data
        assert data["period"]["start_date"] == START.isoformat()
        collector.collect_campaign_performance.assert_awaited_once()


# =============================================================================
# ReportGenerator.generate_report — end-to-end against the real DB
# =============================================================================


class TestGenerateReport:
    async def test_template_not_found(self, db_session, test_tenant):
        generator = ReportGenerator(db_session, test_tenant["id"])
        result = await generator.generate_report(
            template_id=uuid4(), start_date=START, end_date=END
        )
        assert result == {"success": False, "error": "template_not_found"}

    async def test_template_of_other_tenant_not_found(self, db_session, test_tenant):
        """Tenant scoping: a template that belongs to another tenant is 404."""
        from app.base_models import Tenant

        other = Tenant(name="Other", slug="other-tenant-rg", plan="starter")
        db_session.add(other)
        await db_session.flush()
        template = await _make_template(
            db_session, other.id, ReportType.ATTRIBUTION_SUMMARY, "other-tmpl"
        )

        generator = ReportGenerator(db_session, test_tenant["id"])
        result = await generator.generate_report(
            template_id=template.id, start_date=START, end_date=END
        )
        assert result == {"success": False, "error": "template_not_found"}

    async def test_json_success_persists_execution(
        self, db_session, test_tenant, test_user
    ):
        tenant_id = test_tenant["id"]
        await _seed_deals(db_session, tenant_id)
        template = await _make_template(
            db_session,
            tenant_id,
            ReportType.ATTRIBUTION_SUMMARY,
            "attr-json",
            config={"sections": ["summary"]},
        )

        generator = ReportGenerator(db_session, tenant_id)
        result = await generator.generate_report(
            template_id=template.id,
            start_date=START,
            end_date=END,
            format=ReportFormat.JSON,
            config_override={"extra_flag": True},
            triggered_by_user_id=test_user["id"],
            execution_type="api",
        )

        assert result["success"] is True, result
        assert result["file_path"].endswith(".json")
        assert result["file_size_bytes"] > 0
        assert result["duration_seconds"] >= 0

        with open(result["file_path"]) as f:
            payload = json.load(f)
        assert payload["summary"]["total_deals"] == 4
        assert payload["summary"]["total_revenue"] == 3800.0

        execution = (
            await db_session.execute(
                select(ReportExecution).where(
                    ReportExecution.id == UUID(result["execution_id"])
                )
            )
        ).scalar_one()
        assert execution.status == ExecutionStatus.COMPLETED
        assert execution.execution_type == "api"
        assert execution.triggered_by_user_id == test_user["id"]
        assert execution.report_type == ReportType.ATTRIBUTION_SUMMARY
        assert execution.format == ReportFormat.JSON
        assert execution.date_range_start == START
        assert execution.date_range_end == END
        # template config merged with the override snapshot
        assert execution.config_used["sections"] == ["summary"]
        assert execution.config_used["extra_flag"] is True
        assert execution.metrics_summary["total_deals"] == 4
        assert execution.file_size_bytes == result["file_size_bytes"]
        assert execution.completed_at is not None

    async def test_csv_success_daily_table(self, db_session, test_tenant):
        tenant_id = test_tenant["id"]
        await _seed_pipeline_metrics(db_session, tenant_id)
        template = await _make_template(
            db_session, tenant_id, ReportType.PIPELINE_METRICS, "pipe-csv"
        )

        generator = ReportGenerator(db_session, tenant_id)
        result = await generator.generate_report(
            template_id=template.id,
            start_date=START,
            end_date=END,
            format=ReportFormat.CSV,
        )

        assert result["success"] is True, result
        assert result["file_path"].endswith(".csv")
        with open(result["file_path"]) as f:
            lines = [line for line in f.read().splitlines() if line]
        assert lines[0].split(",")[0] == "date"
        assert len(lines) == 3  # header + 2 daily rows

    async def test_csv_without_tabular_data_writes_empty_file(
        self, db_session, test_tenant
    ):
        """Attribution data has neither 'campaigns' nor 'daily' keys."""
        tenant_id = test_tenant["id"]
        template = await _make_template(
            db_session, tenant_id, ReportType.ATTRIBUTION_SUMMARY, "attr-csv"
        )

        generator = ReportGenerator(db_session, tenant_id)
        result = await generator.generate_report(
            template_id=template.id,
            start_date=START,
            end_date=END,
            format=ReportFormat.CSV,
        )

        assert result["success"] is True, result
        assert result["file_size_bytes"] == 0

    async def test_csv_campaigns_table_direct(self, db_session, test_tenant):
        """Cover the campaigns CSV branch of _generate_csv directly with a
        campaign-shaped payload (no seeded campaigns needed)."""
        tenant_id = test_tenant["id"]
        template = await _make_template(
            db_session, tenant_id, ReportType.CAMPAIGN_PERFORMANCE, "camp-csv"
        )
        generator = ReportGenerator(db_session, tenant_id)

        data = {
            "campaigns": [
                {
                    "name": "Alpha",
                    "platform": "meta",
                    "spend": 100.0,
                    "revenue": 300.0,
                    "roas": 3.0,
                    "conversions": 5,
                }
            ]
        }
        file_path, size = await generator._generate_csv(template, data, uuid4())

        assert file_path.endswith(".csv")
        assert size > 0
        with open(file_path) as f:
            content = f.read()
        assert "Campaign,Platform,Spend,Revenue,ROAS,Conversions" in content
        assert "Alpha,meta,100.0,300.0,3.0,5" in content

    async def test_csv_empty_daily_list_writes_no_rows(self, db_session, test_tenant):
        """'daily' key present but empty -> header loop skipped."""
        tenant_id = test_tenant["id"]
        template = await _make_template(
            db_session, tenant_id, ReportType.PROFIT_ROAS, "profit-empty-csv"
        )
        generator = ReportGenerator(db_session, tenant_id)

        _file_path, size = await generator._generate_csv(
            template, {"daily": []}, uuid4()
        )
        assert size == 0

    async def test_pdf_success_with_stub_weasyprint(
        self, db_session, test_tenant, monkeypatch
    ):
        """PDF format path; weasyprint is stubbed because the container's
        native pango libs are missing (see BUG-5 in the pdf test module)."""
        import sys

        tenant_id = test_tenant["id"]
        template = await _make_template(
            db_session, tenant_id, ReportType.PROFIT_ROAS, "profit-pdf"
        )

        fake = types.ModuleType("weasyprint")

        class _HTML:
            def __init__(self, string):
                self._string = string

            def write_pdf(self, target):
                with open(target, "wb") as f:
                    f.write(b"%PDF-1.4 stub\n")

        fake.HTML = _HTML
        monkeypatch.setitem(sys.modules, "weasyprint", fake)

        generator = ReportGenerator(db_session, tenant_id)
        result = await generator.generate_report(
            template_id=template.id,
            start_date=START,
            end_date=END,
            format=ReportFormat.PDF,
        )

        assert result["success"] is True, result
        assert result["file_path"].endswith(".pdf")
        with open(result["file_path"], "rb") as f:
            assert f.read().startswith(b"%PDF")

    async def test_unhandled_format_falls_back_to_json(self, db_session, test_tenant):
        tenant_id = test_tenant["id"]
        template = await _make_template(
            db_session, tenant_id, ReportType.PIPELINE_METRICS, "pipe-excel"
        )

        generator = ReportGenerator(db_session, tenant_id)
        result = await generator.generate_report(
            template_id=template.id,
            start_date=START,
            end_date=END,
            format=ReportFormat.EXCEL,
        )

        assert result["success"] is True, result
        assert result["file_path"].endswith(".json")

    async def test_custom_report_type_is_unsupported_payload(
        self, db_session, test_tenant
    ):
        tenant_id = test_tenant["id"]
        template = await _make_template(
            db_session, tenant_id, ReportType.CUSTOM, "custom-json"
        )

        generator = ReportGenerator(db_session, tenant_id)
        result = await generator.generate_report(
            template_id=template.id,
            start_date=START,
            end_date=END,
            format=ReportFormat.JSON,
        )

        assert result["success"] is True, result
        with open(result["file_path"]) as f:
            assert json.load(f) == {"error": "unsupported_report_type"}

    async def test_collector_error_marks_execution_failed(
        self, db_session, test_tenant, monkeypatch
    ):
        """BUG-4 durability: an exception outside the old hard-coded tuple
        (here AttributeError) must still move the execution to a committed
        FAILED state rather than leaving it stuck in RUNNING."""
        tenant_id = test_tenant["id"]
        template = await _make_template(
            db_session, tenant_id, ReportType.PIPELINE_METRICS, "pipe-fail"
        )

        async def boom(*args, **kwargs):
            raise AttributeError("collector exploded")

        monkeypatch.setattr(
            ReportDataCollector, "collect_pipeline_metrics", boom, raising=True
        )

        generator = ReportGenerator(db_session, tenant_id)
        result = await generator.generate_report(
            template_id=template.id, start_date=START, end_date=END
        )

        assert result["success"] is False
        assert result["error"] == "collector exploded"

        execution = (
            await db_session.execute(
                select(ReportExecution).where(
                    ReportExecution.id == UUID(result["execution_id"])
                )
            )
        ).scalar_one()
        assert execution.status == ExecutionStatus.FAILED
        assert execution.error_message == "collector exploded"
        assert execution.completed_at is not None


# =============================================================================
# _collect_data dispatch
# =============================================================================


class TestCollectDataDispatch:
    async def test_routes_each_report_type_to_its_collector(self, test_tenant):
        generator = ReportGenerator(MagicMock(), test_tenant["id"])
        expected = {
            ReportType.CAMPAIGN_PERFORMANCE: "collect_campaign_performance",
            ReportType.ATTRIBUTION_SUMMARY: "collect_attribution_summary",
            ReportType.PACING_STATUS: "collect_pacing_status",
            ReportType.PROFIT_ROAS: "collect_profit_roas",
            ReportType.PIPELINE_METRICS: "collect_pipeline_metrics",
            ReportType.EXECUTIVE_SUMMARY: "collect_executive_summary",
        }
        for method in expected.values():
            setattr(
                generator.collector,
                method,
                AsyncMock(return_value={"via": method}),
            )

        for report_type, method in expected.items():
            data = await generator._collect_data(report_type, START, END, {"c": 1})
            assert data == {"via": method}
            getattr(generator.collector, method).assert_awaited_once_with(
                START, END, {"c": 1}
            )

    async def test_unknown_type_returns_error_dict(self, test_tenant):
        generator = ReportGenerator(MagicMock(), test_tenant["id"])
        data = await generator._collect_data(ReportType.CUSTOM, START, END, {})
        assert data == {"error": "unsupported_report_type"}


# =============================================================================
# parse_date_range smoke (full matrix lives in tests/unit/test_report_date_range.py)
# =============================================================================


class TestParseDateRangeSmoke:
    def test_all_range_kinds_resolve_ordered_pairs(self):
        ref = date(2026, 5, 20)
        kinds = [
            "today",
            "yesterday",
            "last_7_days",
            "last_30_days",
            "last_90_days",
            "last_month",
            "this_month",
            "month_to_date",
            "quarter_to_date",
            "year_to_date",
            "unknown_kind",
        ]
        for kind in kinds:
            start, end = ReportGenerator.parse_date_range(kind, reference_date=ref)
            assert start <= end, kind
        assert ReportGenerator.parse_date_range("today", reference_date=ref) == (
            ref,
            ref,
        )
        # No reference date -> uses today's UTC date
        start, end = ReportGenerator.parse_date_range("yesterday")
        assert (end - start).days == 0
