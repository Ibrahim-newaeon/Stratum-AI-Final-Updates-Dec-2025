# =============================================================================
# Stratum AI - Pacing Service Deep Integration Tests
# =============================================================================
"""DB-backed integration tests for ``app.services.pacing.pacing_service``.

Covers the paths the endpoint suite (test_pacing_api / test_pacing_targets_api)
never reaches with real data:

- ``PacingService.get_target_pacing`` full computation body: MTD actuals from
  seeded ``daily_kpis``, pro-rated expectations, forecast-backed projections
  (both the forecast-success and linear-fallback branches), gap analysis, and
  the on_track / at_risk / will_miss flag matrix.
- ``get_all_targets_pacing`` filtering + summary bucket counting.
- ``create_pacing_snapshot`` insert and update paths, ``create_all_snapshots``,
  and ``get_pacing_history`` (explicit range and default range).
- ``TargetService`` CRUD incl. cents conversion, filters, and current targets.
- ``_get_metric_value`` for every TargetMetric branch.

Dates are pinned to June 2026 so the math is deterministic: seeded spend is a
constant 100/day, which makes the EWMA forecast exactly 100/day (flat DoW
factors, zero residual std) and projections exact.
"""

from datetime import date, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio

from app.models.pacing import (
    DailyKPI,
    PacingSummary,
    TargetMetric,
    TargetPeriod,
)
from app.services.pacing.pacing_service import PacingService, TargetService

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

# Fixed anchor: mid-month so days_elapsed == days_remaining == 15.
AS_OF = date(2026, 6, 15)
PERIOD_START = date(2026, 6, 1)
PERIOD_END = date(2026, 6, 30)


def _kpi(
    tenant_id: int,
    d: date,
    *,
    spend: float = 100.0,
    revenue: float = 200.0,
    platform: str | None = "meta",
    campaign_id: str | None = None,
    account_id: str | None = None,
    conversions: int = 2,
    leads: int = 1,
    crm_leads: int = 1,
    roas: float | None = None,
) -> DailyKPI:
    return DailyKPI(
        tenant_id=tenant_id,
        date=d,
        platform=platform,
        campaign_id=campaign_id,
        account_id=account_id,
        spend_cents=int(spend * 100),
        revenue_cents=int(revenue * 100),
        conversions=conversions,
        leads=leads,
        crm_leads=crm_leads,
        roas=roas,
        day_of_week=d.weekday(),
        is_weekend=d.weekday() >= 5,
    )


@pytest_asyncio.fixture
async def pacing_service(db_session, test_tenant) -> PacingService:
    return PacingService(db_session, test_tenant["id"])


@pytest_asyncio.fixture
async def target_service(db_session, test_tenant) -> TargetService:
    return TargetService(db_session, test_tenant["id"])


@pytest_asyncio.fixture
async def seeded_kpis(db_session, test_tenant) -> None:
    """56 days of constant meta history ending at AS_OF.

    spend=100/day, revenue=200/day, conversions=2/day, leads=2/day (1+1 crm).
    MTD (June 1-15): spend 1500, revenue 3000, conversions 30.
    """
    start = AS_OF - timedelta(days=55)
    rows = [_kpi(test_tenant["id"], start + timedelta(days=i)) for i in range(56)]
    db_session.add_all(rows)
    await db_session.flush()


async def _make_target(
    target_service: TargetService,
    *,
    name: str = "june-spend",
    metric_type: TargetMetric = TargetMetric.SPEND,
    target_value: float = 3000.0,
    platform: str | None = "meta",
    **kwargs,
):
    return await target_service.create_target(
        name=name,
        metric_type=metric_type,
        target_value=target_value,
        period_start=kwargs.pop("period_start", PERIOD_START),
        period_end=kwargs.pop("period_end", PERIOD_END),
        platform=platform,
        **kwargs,
    )


# =============================================================================
# get_target_pacing
# =============================================================================


class TestGetTargetPacing:
    async def test_target_not_found(self, pacing_service):
        result = await pacing_service.get_target_pacing(uuid4(), AS_OF)
        assert result == {"status": "error", "message": "Target not found"}

    async def test_inactive_target(self, pacing_service, target_service):
        target = await _make_target(target_service)
        assert await target_service.delete_target(target.id) is True

        result = await pacing_service.get_target_pacing(target.id, AS_OF)
        assert result["status"] == "error"
        assert result["message"] == "Target is inactive"

    async def test_not_started(self, pacing_service, target_service):
        target = await _make_target(target_service)
        result = await pacing_service.get_target_pacing(target.id, date(2026, 5, 20))
        assert result["status"] == "not_started"
        assert result["period_start"] == PERIOD_START.isoformat()
        assert result["target_id"] == str(target.id)

    async def test_ended(self, pacing_service, target_service):
        target = await _make_target(target_service)
        result = await pacing_service.get_target_pacing(target.id, date(2026, 7, 5))
        assert result["status"] == "ended"
        assert result["period_end"] == PERIOD_END.isoformat()

    async def test_on_track_with_forecast(
        self, pacing_service, target_service, seeded_kpis
    ):
        # target 3000, MTD 1500 at day 15/30 => pacing exactly 100%.
        target = await _make_target(target_service, target_value=3000.0)
        result = await pacing_service.get_target_pacing(target.id, AS_OF)

        assert result["status"] == "success"
        assert result["target_name"] == "june-spend"
        assert result["metric_type"] == "spend"
        assert result["period"] == {
            "type": "monthly",
            "start": PERIOD_START.isoformat(),
            "end": PERIOD_END.isoformat(),
            "days_elapsed": 15,
            "days_remaining": 15,
            "days_total": 30,
            "progress_pct": 50.0,
        }
        assert result["scope"]["platform"] == "meta"
        assert result["mtd"]["actual"] == pytest.approx(1500.0)
        assert result["mtd"]["expected"] == pytest.approx(1500.0)
        assert result["mtd"]["gap"] == pytest.approx(0.0)
        assert result["pacing"]["pct"] == pytest.approx(100.0)
        assert result["pacing"]["completion_pct"] == pytest.approx(50.0)
        # Constant series -> EWMA forecast is exactly 100/day for 15 days.
        assert result["projection"]["eom"] == pytest.approx(3000.0, rel=0.01)
        assert result["projection"]["lower"] <= result["projection"]["eom"]
        assert result["projection"]["upper"] >= result["projection"]["eom"]
        assert result["gap_analysis"]["gap_to_target"] == pytest.approx(0.0, abs=50)
        assert result["daily"]["average"] == pytest.approx(100.0)
        assert result["daily"]["needed"] == pytest.approx(100.0)
        assert result["status_flags"] == {
            "on_track": True,
            "at_risk": False,
            "will_miss": False,
        }
        assert result["thresholds"] == {"warning_pct": 10.0, "critical_pct": 20.0}

    async def test_underpacing_will_miss(
        self, pacing_service, target_service, seeded_kpis
    ):
        # target 10000 => expected 5000, actual 1500 => ratio 0.3 < 0.75.
        target = await _make_target(target_service, target_value=10000.0)
        result = await pacing_service.get_target_pacing(target.id, AS_OF)

        assert result["status"] == "success"
        assert result["pacing"]["pct"] == pytest.approx(30.0)
        assert result["status_flags"]["will_miss"] is True
        assert result["status_flags"]["on_track"] is False
        assert result["status_flags"]["at_risk"] is False
        assert result["gap_analysis"]["gap_to_target"] > 0
        # daily needed = (10000 - 1500) / 15
        assert result["daily"]["needed"] == pytest.approx(566.67, abs=0.01)

    async def test_at_risk_band(self, pacing_service, target_service, seeded_kpis):
        # target 3600 => expected 1800, ratio 0.833 (at-risk band); projected
        # 3000 => gap 16.7% sits between warning (10) and critical (20).
        target = await _make_target(target_service, target_value=3600.0)
        result = await pacing_service.get_target_pacing(target.id, AS_OF)

        assert result["status"] == "success"
        assert result["pacing"]["pct"] == pytest.approx(83.3, abs=0.1)
        assert result["status_flags"]["at_risk"] is True
        assert result["status_flags"]["will_miss"] is False
        assert result["status_flags"]["on_track"] is False

    async def test_overpacing_will_miss(
        self, pacing_service, target_service, seeded_kpis
    ):
        # target 1500 => expected 750, ratio 2.0 > 1.25 => will_miss.
        target = await _make_target(target_service, target_value=1500.0)
        result = await pacing_service.get_target_pacing(target.id, AS_OF)

        assert result["status"] == "success"
        assert result["pacing"]["pct"] == pytest.approx(200.0)
        assert result["status_flags"]["will_miss"] is True
        # Negative gap: projected to overshoot the target.
        assert result["gap_analysis"]["gap_to_target"] < 0

    async def test_no_days_remaining_skips_forecast(
        self, pacing_service, target_service, seeded_kpis
    ):
        # as_of == period_end: no forecast, projection == MTD actual.
        target = await _make_target(target_service, target_value=3000.0)
        result = await pacing_service.get_target_pacing(target.id, PERIOD_END)

        assert result["status"] == "success"
        assert result["period"]["days_remaining"] == 0
        # Seeds stop at June 15, so MTD stays 1500.
        assert result["mtd"]["actual"] == pytest.approx(1500.0)
        assert result["projection"]["eom"] == pytest.approx(1500.0)
        assert result["projection"]["lower"] == pytest.approx(1500.0)
        assert result["projection"]["upper"] == pytest.approx(1500.0)
        assert result["daily"]["needed"] == 0

    async def test_forecast_fallback_linear(
        self, db_session, test_tenant, pacing_service, target_service
    ):
        # Campaign scope with only 3 days of data: the forecasting service
        # returns insufficient_data and pacing falls back to a linear
        # projection with fixed +-20% bounds.
        for i in range(3):
            db_session.add(
                _kpi(
                    test_tenant["id"],
                    AS_OF - timedelta(days=i),
                    spend=50.0,
                    campaign_id="camp-low",
                )
            )
        await db_session.flush()

        target = await _make_target(
            target_service,
            name="camp-low-spend",
            target_value=1000.0,
            campaign_id="camp-low",
        )
        result = await pacing_service.get_target_pacing(target.id, AS_OF)

        assert result["status"] == "success"
        # MTD 150, daily_avg 10 over 15 elapsed days, 15 remaining => 300.
        assert result["mtd"]["actual"] == pytest.approx(150.0)
        assert result["projection"]["eom"] == pytest.approx(300.0)
        assert result["projection"]["lower"] == pytest.approx(240.0)
        assert result["projection"]["upper"] == pytest.approx(360.0)

    async def test_roas_metric_with_null_values(
        self, pacing_service, target_service, seeded_kpis
    ):
        # Seeded rows have roas=None, so the null-value skip branch runs and
        # MTD stays 0.
        target = await _make_target(
            target_service,
            name="june-roas",
            metric_type=TargetMetric.ROAS,
            target_value=4.0,
        )
        result = await pacing_service.get_target_pacing(target.id, AS_OF)

        assert result["status"] == "success"
        assert result["mtd"]["actual"] == 0.0
        assert result["pacing"]["pct"] == 0.0

    async def test_default_as_of_date_is_today(self, pacing_service, target_service):
        # No as_of_date: defaults to today. Use a period straddling today.
        today = date.today()
        target = await _make_target(
            target_service,
            name="today-default",
            period_type=TargetPeriod.CUSTOM,
            period_start=today - timedelta(days=5),
            period_end=today + timedelta(days=5),
            target_value=100.0,
        )
        result = await pacing_service.get_target_pacing(target.id)
        assert result["status"] == "success"
        assert result["as_of_date"] == today.isoformat()

    async def test_tenant_level_scope_platform_none(
        self, db_session, test_tenant, pacing_service, target_service
    ):
        # platform=None target reads only tenant-level KPI rows.
        db_session.add(_kpi(test_tenant["id"], AS_OF, spend=42.0, platform=None))
        await db_session.flush()

        target = await _make_target(
            target_service, name="tenant-wide", platform=None, target_value=100.0
        )
        result = await pacing_service.get_target_pacing(target.id, AS_OF)
        assert result["status"] == "success"
        assert result["mtd"]["actual"] == pytest.approx(42.0)

    async def test_zero_target_value_guards(
        self, pacing_service, target_service, seeded_kpis
    ):
        # target_value 0 exercises the division guards (completion/gap pct 0).
        target = await _make_target(
            target_service, name="zero-target", target_value=0.0
        )
        result = await pacing_service.get_target_pacing(target.id, AS_OF)

        assert result["status"] == "success"
        assert result["pacing"]["completion_pct"] == 0
        assert result["gap_analysis"]["gap_pct"] == 0


# =============================================================================
# get_all_targets_pacing
# =============================================================================


@pytest_asyncio.fixture
async def three_targets(target_service, seeded_kpis) -> dict:
    """One target per summary bucket, distinct metric types to satisfy the
    unique-scope constraint.

    - SPEND 3000: pacing 100% -> on_track
    - REVENUE 7200: pacing 83.3%, gap 16.7% -> at_risk
    - CONVERSIONS 200: pacing 30% -> will_miss
    """
    on_track = await _make_target(
        target_service, name="spend-on-track", target_value=3000.0
    )
    at_risk = await _make_target(
        target_service,
        name="revenue-at-risk",
        metric_type=TargetMetric.REVENUE,
        target_value=7200.0,
    )
    will_miss = await _make_target(
        target_service,
        name="conv-will-miss",
        metric_type=TargetMetric.CONVERSIONS,
        target_value=200.0,
    )
    return {"on_track": on_track, "at_risk": at_risk, "will_miss": will_miss}


class TestGetAllTargetsPacing:
    async def test_summary_buckets(self, pacing_service, three_targets):
        result = await pacing_service.get_all_targets_pacing(as_of_date=AS_OF)

        assert result["status"] == "success"
        assert result["as_of_date"] == AS_OF.isoformat()
        assert result["summary"] == {
            "on_track": 1,
            "at_risk": 1,
            "will_miss": 1,
            "total": 3,
        }
        assert len(result["targets"]) == 3
        assert all(t["status"] == "success" for t in result["targets"])

    async def test_metric_type_filter(self, pacing_service, three_targets):
        result = await pacing_service.get_all_targets_pacing(
            as_of_date=AS_OF, metric_type=TargetMetric.SPEND
        )
        assert result["summary"]["total"] == 1
        assert result["targets"][0]["metric_type"] == "spend"

    async def test_platform_filter_no_data(
        self, pacing_service, target_service, three_targets
    ):
        await _make_target(
            target_service,
            name="google-spend",
            platform="google",
            target_value=500.0,
        )
        result = await pacing_service.get_all_targets_pacing(
            as_of_date=AS_OF, platform="google"
        )
        assert result["summary"]["total"] == 1
        # No google KPI data seeded: pacing 0 -> will_miss.
        assert result["summary"]["will_miss"] == 1

    async def test_account_id_filter(self, pacing_service, target_service):
        await _make_target(
            target_service,
            name="acct-spend",
            account_id="act_123",
            target_value=500.0,
        )
        result = await pacing_service.get_all_targets_pacing(
            as_of_date=AS_OF, account_id="act_123"
        )
        assert result["summary"]["total"] == 1
        assert result["targets"][0]["scope"]["account_id"] == "act_123"

    async def test_inactive_excluded_by_default(
        self, pacing_service, target_service, seeded_kpis
    ):
        target = await _make_target(target_service, name="soon-inactive")
        await target_service.delete_target(target.id)

        active = await pacing_service.get_all_targets_pacing(as_of_date=AS_OF)
        assert active["summary"]["total"] == 0

        # active_only=False includes it; pacing errors (inactive) so no bucket
        # is incremented.
        everything = await pacing_service.get_all_targets_pacing(
            as_of_date=AS_OF, active_only=False
        )
        assert everything["summary"]["total"] == 1
        assert everything["summary"]["on_track"] == 0
        assert everything["targets"][0]["status"] == "error"

    async def test_defaults_to_today_empty(self, pacing_service):
        result = await pacing_service.get_all_targets_pacing()
        assert result["status"] == "success"
        assert result["as_of_date"] == date.today().isoformat()
        assert result["summary"]["total"] == 0


# =============================================================================
# Snapshots
# =============================================================================


class TestSnapshots:
    async def test_create_snapshot_persists(
        self, db_session, pacing_service, target_service, seeded_kpis, test_tenant
    ):
        target = await _make_target(target_service, target_value=3000.0)
        snapshot = await pacing_service.create_pacing_snapshot(target.id, AS_OF)

        assert snapshot is not None
        assert snapshot.tenant_id == test_tenant["id"]
        assert snapshot.target_id == target.id
        assert snapshot.snapshot_date == AS_OF
        assert snapshot.period_start == PERIOD_START
        assert snapshot.period_end == PERIOD_END
        assert snapshot.days_elapsed == 15
        assert snapshot.days_remaining == 15
        assert snapshot.days_total == 30
        assert snapshot.mtd_actual == pytest.approx(1500.0)
        assert snapshot.mtd_expected == pytest.approx(1500.0)
        assert snapshot.pacing_pct == pytest.approx(100.0)
        assert snapshot.completion_pct == pytest.approx(50.0)
        assert snapshot.projected_eom == pytest.approx(3000.0, rel=0.01)
        assert snapshot.on_track is True
        assert snapshot.at_risk is False
        assert snapshot.will_miss is False

        # Row actually persisted.
        from sqlalchemy import select

        rows = (
            (
                await db_session.execute(
                    select(PacingSummary).where(PacingSummary.target_id == target.id)
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1

    async def test_snapshot_update_existing(
        self, db_session, pacing_service, target_service, seeded_kpis
    ):
        target = await _make_target(target_service, target_value=3000.0)
        first = await pacing_service.create_pacing_snapshot(target.id, AS_OF)
        second = await pacing_service.create_pacing_snapshot(target.id, AS_OF)

        assert second is not None
        assert second.id == first.id  # updated in place, not duplicated

        from sqlalchemy import select

        rows = (
            (
                await db_session.execute(
                    select(PacingSummary).where(PacingSummary.target_id == target.id)
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].mtd_actual == pytest.approx(1500.0)

    async def test_snapshot_fails_for_ended_period(
        self, pacing_service, target_service
    ):
        target = await _make_target(target_service)
        snapshot = await pacing_service.create_pacing_snapshot(
            target.id, date(2026, 7, 10)
        )
        assert snapshot is None

    async def test_snapshot_default_date(self, pacing_service):
        # Default as_of_date (today) with an unknown target: error path, None.
        assert await pacing_service.create_pacing_snapshot(uuid4()) is None

    async def test_create_all_snapshots_default_date_empty(self, pacing_service):
        result = await pacing_service.create_all_snapshots()
        assert result["as_of_date"] == date.today().isoformat()
        assert result["targets_processed"] == 0

    async def test_create_all_snapshots(self, pacing_service, three_targets):
        result = await pacing_service.create_all_snapshots(AS_OF)

        assert result["status"] == "success"
        assert result["as_of_date"] == AS_OF.isoformat()
        assert result["targets_processed"] == 3
        assert result["snapshots_created"] == 3
        assert result["snapshots_failed"] == 0

    async def test_create_all_snapshots_counts_failures(
        self, pacing_service, three_targets
    ):
        with patch.object(
            PacingService,
            "create_pacing_snapshot",
            new=AsyncMock(return_value=None),
        ):
            result = await pacing_service.create_all_snapshots(AS_OF)

        assert result["targets_processed"] == 3
        assert result["snapshots_created"] == 0
        assert result["snapshots_failed"] == 3

    async def test_pacing_history_explicit_range(
        self, pacing_service, target_service, seeded_kpis
    ):
        target = await _make_target(target_service, target_value=3000.0)
        await pacing_service.create_pacing_snapshot(target.id, date(2026, 6, 14))
        await pacing_service.create_pacing_snapshot(target.id, AS_OF)

        history = await pacing_service.get_pacing_history(
            target.id, start_date=PERIOD_START, end_date=PERIOD_END
        )
        assert [h["date"] for h in history] == ["2026-06-14", "2026-06-15"]
        entry = history[-1]
        assert entry["mtd_actual"] == pytest.approx(1500.0)
        assert entry["pacing_pct"] == pytest.approx(100.0)
        assert entry["on_track"] is True
        assert {"projected_eom", "gap_to_target", "completion_pct"} <= entry.keys()

        # Range excluding the snapshots is empty.
        empty = await pacing_service.get_pacing_history(
            target.id, start_date=date(2026, 5, 1), end_date=date(2026, 5, 31)
        )
        assert empty == []

    async def test_pacing_history_default_range(self, pacing_service, target_service):
        # Default range is (today-30, today): snapshot a target whose custom
        # period straddles today.
        today = date.today()
        target = await _make_target(
            target_service,
            name="current-window",
            period_type=TargetPeriod.CUSTOM,
            period_start=today - timedelta(days=10),
            period_end=today + timedelta(days=10),
            target_value=100.0,
        )
        snapshot = await pacing_service.create_pacing_snapshot(target.id, today)
        assert snapshot is not None

        history = await pacing_service.get_pacing_history(target.id)
        assert [h["date"] for h in history] == [today.isoformat()]


# =============================================================================
# TargetService CRUD
# =============================================================================


class TestTargetService:
    async def test_create_monetary_sets_cents(self, target_service, test_tenant):
        target = await _make_target(target_service, target_value=1234.56)
        assert target.tenant_id == test_tenant["id"]
        assert target.target_value_cents == 123456
        assert target.period_type == TargetPeriod.MONTHLY
        assert target.is_active is True

    async def test_create_non_monetary_no_cents(self, target_service):
        target = await _make_target(
            target_service,
            name="roas-target",
            metric_type=TargetMetric.ROAS,
            target_value=4.5,
        )
        assert target.target_value_cents is None

    async def test_get_target(self, target_service):
        target = await _make_target(target_service)
        found = await target_service.get_target(target.id)
        assert found is not None
        assert found.id == target.id

        assert await target_service.get_target(uuid4()) is None

    async def test_list_targets_filters(self, target_service):
        spend = await _make_target(target_service, name="list-spend")
        roas = await _make_target(
            target_service,
            name="list-roas",
            metric_type=TargetMetric.ROAS,
            target_value=3.0,
            platform="google",
            account_id="act_9",
        )
        inactive = await _make_target(
            target_service,
            name="list-inactive",
            metric_type=TargetMetric.LEADS,
            target_value=10.0,
        )
        await target_service.delete_target(inactive.id)

        all_active = await target_service.list_targets()
        ids = {t.id for t in all_active}
        assert spend.id in ids and roas.id in ids and inactive.id not in ids

        with_inactive = await target_service.list_targets(active_only=False)
        assert inactive.id in {t.id for t in with_inactive}

        by_metric = await target_service.list_targets(metric_type=TargetMetric.ROAS)
        assert [t.id for t in by_metric] == [roas.id]

        by_platform = await target_service.list_targets(platform="google")
        assert [t.id for t in by_platform] == [roas.id]

        by_account = await target_service.list_targets(account_id="act_9")
        assert [t.id for t in by_account] == [roas.id]

        by_period = await target_service.list_targets(period_type=TargetPeriod.MONTHLY)
        assert spend.id in {t.id for t in by_period}

    async def test_update_target_monetary_recomputes_cents(self, target_service):
        target = await _make_target(target_service, target_value=1000.0)
        updated = await target_service.update_target(
            target.id,
            name="renamed",
            target_value=2500.5,
            warning_threshold_pct=15.0,
        )
        assert updated is not None
        assert updated.name == "renamed"
        assert updated.target_value == 2500.5
        assert updated.target_value_cents == 250050
        assert updated.warning_threshold_pct == 15.0

    async def test_update_non_monetary_keeps_cents_none(self, target_service):
        target = await _make_target(
            target_service,
            name="upd-roas",
            metric_type=TargetMetric.ROAS,
            target_value=3.0,
        )
        updated = await target_service.update_target(target.id, target_value=5.0)
        assert updated.target_value == 5.0
        assert updated.target_value_cents is None

    async def test_update_ignores_disallowed_and_none(self, target_service):
        target = await _make_target(target_service, name="immutable-scope")
        updated = await target_service.update_target(
            target.id, platform="tiktok", name=None
        )
        # platform is not in the allowed list; None values are skipped.
        assert updated.platform == "meta"
        assert updated.name == "immutable-scope"

    async def test_update_unknown_returns_none(self, target_service):
        assert await target_service.update_target(uuid4(), name="x") is None

    async def test_delete_target_soft(self, target_service):
        target = await _make_target(target_service)
        assert await target_service.delete_target(target.id) is True
        refreshed = await target_service.get_target(target.id)
        assert refreshed.is_active is False

        assert await target_service.delete_target(uuid4()) is False

    async def test_get_current_targets(self, target_service):
        today = date.today()
        current = await _make_target(
            target_service,
            name="current",
            period_type=TargetPeriod.CUSTOM,
            period_start=today - timedelta(days=5),
            period_end=today + timedelta(days=5),
        )
        past = await _make_target(
            target_service,
            name="past",
            period_start=today - timedelta(days=60),
            period_end=today - timedelta(days=31),
        )

        result = await target_service.get_current_targets()
        ids = {t.id for t in result}
        assert current.id in ids and past.id not in ids

        by_metric = await target_service.get_current_targets(
            metric_type=TargetMetric.SPEND, platform="meta"
        )
        assert current.id in {t.id for t in by_metric}

        none_match = await target_service.get_current_targets(platform="google")
        assert none_match == []


# =============================================================================
# _get_metric_value
# =============================================================================


class TestGetMetricValue:
    @pytest.fixture
    def record(self, test_tenant) -> DailyKPI:
        d = AS_OF
        return DailyKPI(
            tenant_id=test_tenant["id"],
            date=d,
            spend_cents=12345,
            revenue_cents=67890,
            roas=3.2,
            conversions=7,
            leads=2,
            crm_leads=3,
            crm_pipeline_cents=100000,
            crm_won_revenue_cents=50000,
            cpa_cents=250,
            cpl_cents=125,
            day_of_week=d.weekday(),
            is_weekend=False,
        )

    @pytest.mark.parametrize(
        "metric,expected",
        [
            (TargetMetric.SPEND, 123.45),
            (TargetMetric.REVENUE, 678.90),
            (TargetMetric.ROAS, 3.2),
            (TargetMetric.CONVERSIONS, 7),
            (TargetMetric.LEADS, 5),
            (TargetMetric.PIPELINE_VALUE, 1000.0),
            (TargetMetric.WON_REVENUE, 500.0),
            (TargetMetric.CPA, 2.50),
            (TargetMetric.CPL, 1.25),
        ],
    )
    async def test_all_metric_branches(self, pacing_service, record, metric, expected):
        assert pacing_service._get_metric_value(record, metric) == pytest.approx(
            expected
        )

    async def test_none_cents_treated_as_zero(self, pacing_service, record):
        record.cpa_cents = None
        record.spend_cents = None
        assert pacing_service._get_metric_value(record, TargetMetric.CPA) == 0.0
        assert pacing_service._get_metric_value(record, TargetMetric.SPEND) == 0.0

    async def test_unknown_metric_returns_none(self, pacing_service, record):
        assert pacing_service._get_metric_value(record, "not-a-metric") is None
