# =============================================================================
# Stratum AI - Pacing Alert Service Deep Integration Tests
# =============================================================================
"""Service-layer integration tests for
``app.services.pacing.alert_service`` (#342 Batch 4).

Drives ``PacingAlertService`` and ``AlertNotificationService`` against the
real Postgres test database:

- Alert generation branches (critical/warning under/over-pacing, projected
  miss, dedupe, severity escalation, auto-resolution).
- ``check_all_targets`` sweep over seeded ``Target`` rows with real pacing
  math (no ``daily_kpis`` -> critical underpacing; uniform spend -> on
  track + auto-resolve).
- Pacing-cliff detection over seeded ``DailyKPI`` series.
- Alert lifecycle (acknowledge / resolve / dismiss) incl. tenant isolation.
- Alert summary aggregation (status/severity/type counts, resolution time).
- Notification building/dispatch, with true externals (Slack HTTP, SMTP,
  WhatsApp API) mocked at the service boundary per Batch-3 rules.

NOTE: run with the session-scoped event loop CI uses
(``-o asyncio_default_test_loop_scope=session``) or the default per-test
loop — these tests only use the db_session fixture, not the ASGI app.
"""

import smtplib
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.pacing import (
    AlertSeverity,
    AlertStatus,
    AlertType,
    DailyKPI,
    PacingAlert,
    Target,
    TargetMetric,
    TargetPeriod,
)
from app.services.pacing.alert_service import (
    AlertNotificationService,
    PacingAlertService,
)

pytestmark = pytest.mark.integration

# Fixed clock: mid-month so days_elapsed and days_remaining are both > 0.
AS_OF = date(2026, 6, 15)
PERIOD_START = date(2026, 6, 1)
PERIOD_END = date(2026, 6, 30)


# =============================================================================
# Helpers
# =============================================================================


def _pacing_payload(
    *,
    pct: float = 100.0,
    target_value: float = 10000.0,
    warning_pct: float = 10.0,
    critical_pct: float = 20.0,
    will_miss: bool = False,
    on_track: bool = False,
    gap_pct: float = 0.0,
    eom: float = 10000.0,
    metric_type: str = "spend",
    target_name: str = "June Spend",
    days_remaining: int = 15,
    platform: Optional[str] = "meta",
    campaign_id: Optional[str] = None,
    actual: float = 5000.0,
    expected: float = 5000.0,
) -> dict:
    """Build a ``PacingService.get_target_pacing`` success envelope."""
    return {
        "status": "success",
        "target_name": target_name,
        "metric_type": metric_type,
        "target_value": target_value,
        "mtd": {"actual": actual, "expected": expected},
        "pacing": {"pct": pct},
        "projection": {"eom": eom},
        "gap_analysis": {"gap_pct": gap_pct},
        "period": {"days_remaining": days_remaining},
        "scope": {"platform": platform, "campaign_id": campaign_id},
        "status_flags": {
            "on_track": on_track,
            "at_risk": False,
            "will_miss": will_miss,
        },
        "thresholds": {"warning_pct": warning_pct, "critical_pct": critical_pct},
    }


async def _make_target(db_session, tenant_id: int, **overrides) -> Target:
    """Create and flush a Target row (notifications off by default)."""
    fields = dict(
        tenant_id=tenant_id,
        name="June Spend",
        period_type=TargetPeriod.MONTHLY,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        metric_type=TargetMetric.SPEND,
        target_value=3000.0,
        warning_threshold_pct=10.0,
        critical_threshold_pct=20.0,
        is_active=True,
        notify_slack=False,
        notify_email=False,
        notify_whatsapp=False,
    )
    fields.update(overrides)
    target = Target(**fields)
    db_session.add(target)
    await db_session.flush()
    return target


async def _make_kpi(
    db_session,
    tenant_id: int,
    day: date,
    *,
    spend_cents: int = 0,
    platform: Optional[str] = None,
    campaign_id: Optional[str] = None,
    **overrides,
) -> DailyKPI:
    fields = dict(
        tenant_id=tenant_id,
        date=day,
        platform=platform,
        campaign_id=campaign_id,
        spend_cents=spend_cents,
        day_of_week=day.weekday(),
        is_weekend=day.weekday() >= 5,
    )
    fields.update(overrides)
    kpi = DailyKPI(**fields)
    db_session.add(kpi)
    await db_session.flush()
    return kpi


async def _make_alert(
    db_session,
    tenant_id: int,
    target_id=None,
    *,
    alert_type: AlertType = AlertType.UNDERPACING_SPEND,
    severity: AlertSeverity = AlertSeverity.WARNING,
    status: AlertStatus = AlertStatus.ACTIVE,
    pacing_date: date = AS_OF,
    **overrides,
) -> PacingAlert:
    fields = dict(
        tenant_id=tenant_id,
        target_id=target_id,
        alert_type=alert_type,
        severity=severity,
        status=status,
        title="seeded alert",
        message="seeded alert message",
        pacing_date=pacing_date,
    )
    fields.update(overrides)
    alert = PacingAlert(**fields)
    db_session.add(alert)
    await db_session.flush()
    return alert


def _detached_alert(**overrides) -> PacingAlert:
    """A non-persisted PacingAlert for direct notification-method tests."""
    fields = dict(
        tenant_id=1,
        alert_type=AlertType.UNDERPACING_SPEND,
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.ACTIVE,
        title="Critical: June Spend severely underpacing",
        message="Currently at 60.0% of expected pace.",
        pacing_date=AS_OF,
        mtd_actual=3000.0,
        mtd_expected=5000.0,
        deviation_pct=40.0,
        days_remaining=15,
        projected_eom=6000.0,
    )
    fields.update(overrides)
    return PacingAlert(**fields)


@pytest.fixture
async def svc(db_session, test_tenant) -> PacingAlertService:
    return PacingAlertService(db_session, test_tenant["id"])


@pytest.fixture
async def notifier(db_session, test_tenant) -> AlertNotificationService:
    return AlertNotificationService(db_session, test_tenant["id"])


def _patch_pacing(svc: PacingAlertService, payload: dict):
    return patch.object(
        svc.pacing_service,
        "get_target_pacing",
        AsyncMock(return_value=payload),
    )


# =============================================================================
# check_target_alerts — branch coverage via controlled pacing envelopes
# =============================================================================


class TestCheckTargetAlerts:
    async def test_pacing_error_returns_empty(self, svc, db_session, test_tenant):
        target = await _make_target(db_session, test_tenant["id"])
        with _patch_pacing(svc, {"status": "error", "message": "Target not found"}):
            alerts = await svc.check_target_alerts(target.id, AS_OF)
        assert alerts == []

    async def test_default_as_of_date_is_today(self, svc, db_session, test_tenant):
        target = await _make_target(db_session, test_tenant["id"])
        mock = AsyncMock(return_value={"status": "error"})
        with patch.object(svc.pacing_service, "get_target_pacing", mock):
            await svc.check_target_alerts(target.id)
        assert mock.await_args.args[1] == date.today()

    async def test_critical_underpacing_creates_alert(
        self, svc, db_session, test_tenant
    ):
        target = await _make_target(db_session, test_tenant["id"])
        payload = _pacing_payload(pct=60.0, actual=3000.0, expected=5000.0, eom=6000.0)
        with _patch_pacing(svc, payload):
            alerts = await svc.check_target_alerts(target.id, AS_OF)

        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.alert_type == AlertType.UNDERPACING_SPEND
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.status == AlertStatus.ACTIVE
        assert "severely underpacing" in alert.title
        # Persisted metric snapshot
        assert alert.current_value == 3000.0
        assert alert.target_value == 10000.0
        assert alert.mtd_actual == 3000.0
        assert alert.mtd_expected == 5000.0
        assert alert.projected_eom == 6000.0
        assert alert.deviation_pct == pytest.approx(40.0)
        assert alert.days_remaining == 15
        assert alert.platform == "meta"
        assert alert.pacing_date == AS_OF
        # Row actually persisted
        row = await db_session.get(PacingAlert, alert.id)
        assert row is not None

    async def test_warning_underpacing(self, svc, db_session, test_tenant):
        target = await _make_target(db_session, test_tenant["id"])
        with _patch_pacing(svc, _pacing_payload(pct=85.0)):
            alerts = await svc.check_target_alerts(target.id, AS_OF)
        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.WARNING
        assert alerts[0].alert_type == AlertType.UNDERPACING_SPEND
        assert "underpacing" in alerts[0].title

    async def test_critical_overpacing(self, svc, db_session, test_tenant):
        target = await _make_target(db_session, test_tenant["id"])
        with _patch_pacing(svc, _pacing_payload(pct=130.0)):
            alerts = await svc.check_target_alerts(target.id, AS_OF)
        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.CRITICAL
        assert alerts[0].alert_type == AlertType.OVERPACING_SPEND
        assert "severely overpacing" in alerts[0].title
        # Overpacing => negative deviation from expected pace
        assert alerts[0].deviation_pct == pytest.approx(-30.0)

    async def test_warning_overpacing(self, svc, db_session, test_tenant):
        target = await _make_target(db_session, test_tenant["id"])
        with _patch_pacing(svc, _pacing_payload(pct=115.0)):
            alerts = await svc.check_target_alerts(target.id, AS_OF)
        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.WARNING
        assert alerts[0].alert_type == AlertType.OVERPACING_SPEND

    async def test_projected_miss_maps_metric_to_alert_type(
        self, svc, db_session, test_tenant
    ):
        target = await _make_target(
            db_session, test_tenant["id"], metric_type=TargetMetric.ROAS
        )
        # Pacing exactly on 100% (no under/over branch) but projected to miss.
        payload = _pacing_payload(
            pct=100.0, will_miss=True, gap_pct=-30.0, metric_type="roas"
        )
        with _patch_pacing(svc, payload):
            alerts = await svc.check_target_alerts(target.id, AS_OF)
        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.ROAS_BELOW_TARGET
        assert alerts[0].severity == AlertSeverity.CRITICAL
        assert "projected to miss" in alerts[0].title

    async def test_on_track_with_nothing_to_resolve_is_noop(
        self, svc, db_session, test_tenant
    ):
        target = await _make_target(db_session, test_tenant["id"])
        with _patch_pacing(svc, _pacing_payload(pct=100.0, on_track=True)):
            alerts = await svc.check_target_alerts(target.id, AS_OF)
        assert alerts == []
        result = await db_session.execute(
            select(PacingAlert).where(PacingAlert.target_id == target.id)
        )
        assert result.scalars().all() == []

    async def test_duplicate_overpacing_suppressed(self, svc, db_session, test_tenant):
        target = await _make_target(db_session, test_tenant["id"])
        # Critical first, then warning + critical repeats: no new rows either way.
        with _patch_pacing(svc, _pacing_payload(pct=130.0)):
            first = await svc.check_target_alerts(target.id, AS_OF)
            repeat_critical = await svc.check_target_alerts(target.id, AS_OF)
        with _patch_pacing(svc, _pacing_payload(pct=115.0)):
            repeat_warning = await svc.check_target_alerts(target.id, AS_OF)
        assert len(first) == 1
        assert repeat_critical == []
        assert repeat_warning == []
        result = await db_session.execute(
            select(PacingAlert).where(PacingAlert.target_id == target.id)
        )
        assert len(result.scalars().all()) == 1

    async def test_projected_miss_below_critical_gap_no_alert(
        self, svc, db_session, test_tenant
    ):
        target = await _make_target(db_session, test_tenant["id"])
        payload = _pacing_payload(pct=100.0, will_miss=True, gap_pct=15.0)
        with _patch_pacing(svc, payload):
            alerts = await svc.check_target_alerts(target.id, AS_OF)
        assert alerts == []

    async def test_duplicate_alert_suppressed(self, svc, db_session, test_tenant):
        target = await _make_target(db_session, test_tenant["id"])
        with _patch_pacing(svc, _pacing_payload(pct=85.0)):
            first = await svc.check_target_alerts(target.id, AS_OF)
            second = await svc.check_target_alerts(target.id, AS_OF)
        assert len(first) == 1
        assert second == []
        result = await db_session.execute(
            select(PacingAlert).where(PacingAlert.target_id == target.id)
        )
        assert len(result.scalars().all()) == 1

    async def test_warning_escalates_to_critical_in_place(
        self, svc, db_session, test_tenant
    ):
        target = await _make_target(db_session, test_tenant["id"])
        with _patch_pacing(svc, _pacing_payload(pct=85.0)):
            first = await svc.check_target_alerts(target.id, AS_OF)
        assert first[0].severity == AlertSeverity.WARNING

        with _patch_pacing(svc, _pacing_payload(pct=60.0)):
            second = await svc.check_target_alerts(target.id, AS_OF)

        # No new alert row — the existing one was escalated in place.
        assert second == []
        result = await db_session.execute(
            select(PacingAlert).where(PacingAlert.target_id == target.id)
        )
        rows = result.scalars().all()
        assert len(rows) == 1
        assert rows[0].severity == AlertSeverity.CRITICAL
        assert "severely underpacing" in rows[0].title

    async def test_on_track_auto_resolves_pacing_alerts(
        self, svc, db_session, test_tenant
    ):
        target = await _make_target(db_session, test_tenant["id"])
        with _patch_pacing(svc, _pacing_payload(pct=60.0)):
            created = await svc.check_target_alerts(target.id, AS_OF)
        assert len(created) == 1

        with _patch_pacing(svc, _pacing_payload(pct=100.0, on_track=True)):
            alerts = await svc.check_target_alerts(target.id, AS_OF)
        assert alerts == []

        row = await db_session.get(PacingAlert, created[0].id)
        assert row.status == AlertStatus.RESOLVED
        assert row.resolved_at is not None
        assert "Auto-resolved" in row.resolution_notes

    async def test_notification_failure_does_not_block_creation(
        self, svc, db_session, test_tenant
    ):
        target = await _make_target(db_session, test_tenant["id"])
        with patch.object(
            AlertNotificationService,
            "notify_alert",
            AsyncMock(side_effect=ValueError("boom")),
        ):
            with _patch_pacing(svc, _pacing_payload(pct=60.0)):
                alerts = await svc.check_target_alerts(target.id, AS_OF)
        assert len(alerts) == 1
        row = await db_session.get(PacingAlert, alerts[0].id)
        assert row is not None


# =============================================================================
# check_all_targets — real pacing math against seeded rows
# =============================================================================


class TestCheckAllTargets:
    async def test_no_targets(self, svc):
        summary = await svc.check_all_targets(AS_OF)
        assert summary == {
            "status": "success",
            "as_of_date": AS_OF.isoformat(),
            "targets_checked": 0,
            "targets_with_alerts": 0,
            "alerts_created": 0,
        }

    async def test_no_kpi_data_flags_critical_underpacing(
        self, svc, db_session, test_tenant
    ):
        tenant_id = test_tenant["id"]
        await _make_target(db_session, tenant_id, name="meta spend", platform="meta")
        await _make_target(
            db_session, tenant_id, name="google spend", platform="google"
        )
        # Excluded: inactive + out-of-period targets
        await _make_target(
            db_session, tenant_id, name="inactive", platform="tiktok", is_active=False
        )
        await _make_target(
            db_session,
            tenant_id,
            name="last month",
            platform="snapchat",
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
        )

        summary = await svc.check_all_targets(AS_OF)

        assert summary["targets_checked"] == 2
        assert summary["targets_with_alerts"] == 2
        assert summary["alerts_created"] == 2

        alerts = await svc.get_active_alerts()
        assert len(alerts) == 2
        assert all(a.severity == AlertSeverity.CRITICAL for a in alerts)
        assert all(a.alert_type == AlertType.UNDERPACING_SPEND for a in alerts)
        # Zero spend against a positive prorated target
        assert all(a.current_value == 0.0 for a in alerts)

    async def test_on_track_spend_creates_no_alerts_and_resolves_old(
        self, svc, db_session, test_tenant
    ):
        tenant_id = test_tenant["id"]
        # 3000 over 30 days -> 100/day expected; seed exactly 100/day actual.
        target = await _make_target(
            db_session, tenant_id, platform=None, target_value=3000.0
        )
        for offset in range(15):
            await _make_kpi(
                db_session,
                tenant_id,
                PERIOD_START + timedelta(days=offset),
                spend_cents=100_00,
            )
        stale = await _make_alert(db_session, tenant_id, target.id)

        summary = await svc.check_all_targets(AS_OF)

        assert summary["targets_checked"] == 1
        assert summary["alerts_created"] == 0
        row = await db_session.get(PacingAlert, stale.id)
        assert row.status == AlertStatus.RESOLVED

    async def test_default_as_of_date(self, svc):
        summary = await svc.check_all_targets()
        assert summary["as_of_date"] == date.today().isoformat()


# =============================================================================
# check_pacing_cliff
# =============================================================================


class TestCheckPacingCliff:
    async def test_unknown_target_returns_none(self, svc):
        assert await svc.check_pacing_cliff(uuid4()) is None

    async def test_insufficient_data_returns_none(self, svc, db_session, test_tenant):
        tenant_id = test_tenant["id"]
        target = await _make_target(db_session, tenant_id, platform=None)
        await _make_kpi(db_session, tenant_id, AS_OF, spend_cents=100_00)
        await _make_kpi(
            db_session, tenant_id, AS_OF - timedelta(days=1), spend_cents=100_00
        )
        assert await svc.check_pacing_cliff(target.id, AS_OF) is None

    async def test_cliff_detected(self, svc, db_session, test_tenant):
        tenant_id = test_tenant["id"]
        target = await _make_target(db_session, tenant_id, platform=None)
        for offset, cents in ((3, 100_00), (2, 100_00), (1, 100_00), (0, 10_00)):
            await _make_kpi(
                db_session,
                tenant_id,
                AS_OF - timedelta(days=offset),
                spend_cents=cents,
            )

        alert = await svc.check_pacing_cliff(target.id, AS_OF)

        assert alert is not None
        assert alert.alert_type == AlertType.PACING_CLIFF
        assert alert.severity == AlertSeverity.CRITICAL
        assert "Pacing Cliff Detected" in alert.title
        assert alert.details["drop_pct"] == pytest.approx(90.0)
        assert alert.details["latest_value"] == pytest.approx(10.0)
        assert alert.details["previous_avg"] == pytest.approx(100.0)

    async def test_stable_series_no_cliff(self, svc, db_session, test_tenant):
        tenant_id = test_tenant["id"]
        target = await _make_target(db_session, tenant_id, platform=None)
        for offset in range(4):
            await _make_kpi(
                db_session,
                tenant_id,
                AS_OF - timedelta(days=offset),
                spend_cents=100_00,
            )
        assert await svc.check_pacing_cliff(target.id, AS_OF) is None

    async def test_zero_previous_average_guard(self, svc, db_session, test_tenant):
        tenant_id = test_tenant["id"]
        target = await _make_target(db_session, tenant_id, platform=None)
        for offset in range(4):
            await _make_kpi(
                db_session, tenant_id, AS_OF - timedelta(days=offset), spend_cents=0
            )
        # previous_avg == 0 -> division guard, no alert
        assert await svc.check_pacing_cliff(target.id, AS_OF) is None

    async def test_unmapped_metric_yields_no_values(self, svc, db_session, test_tenant):
        tenant_id = test_tenant["id"]
        target = await _make_target(
            db_session, tenant_id, platform=None, metric_type=TargetMetric.CPA
        )
        for offset in range(4):
            await _make_kpi(
                db_session,
                tenant_id,
                AS_OF - timedelta(days=offset),
                spend_cents=100_00,
            )
        # _get_metric_value returns None for CPA -> fewer than 3 usable points
        assert await svc.check_pacing_cliff(target.id, AS_OF) is None

    async def test_scoped_to_platform_and_campaign(self, svc, db_session, test_tenant):
        tenant_id = test_tenant["id"]
        target = await _make_target(
            db_session, tenant_id, platform="meta", campaign_id="cmp-1"
        )
        # Matching scope: cliff series
        for offset, cents in ((3, 200_00), (2, 200_00), (1, 200_00), (0, 20_00)):
            await _make_kpi(
                db_session,
                tenant_id,
                AS_OF - timedelta(days=offset),
                spend_cents=cents,
                platform="meta",
                campaign_id="cmp-1",
            )
        # Non-matching scope rows must be ignored (stable series)
        for offset in range(4):
            await _make_kpi(
                db_session,
                tenant_id,
                AS_OF - timedelta(days=offset),
                spend_cents=999_00,
                platform="google",
                campaign_id="cmp-2",
            )

        alert = await svc.check_pacing_cliff(target.id, AS_OF)
        assert alert is not None
        assert alert.details["previous_avg"] == pytest.approx(200.0)

    async def test_metric_value_extraction_from_real_kpi_row(
        self, svc, db_session, test_tenant
    ):
        """Cover _get_metric_value against a fully-populated DailyKPI row."""
        kpi = await _make_kpi(
            db_session,
            test_tenant["id"],
            AS_OF,
            spend_cents=12345,
            revenue_cents=50000,
            roas=2.5,
            conversions=42,
            leads=3,
            crm_leads=4,
            crm_pipeline_cents=900000,
            crm_won_revenue_cents=250000,
        )
        assert svc._get_metric_value(kpi, TargetMetric.SPEND) == 123.45
        assert svc._get_metric_value(kpi, TargetMetric.REVENUE) == 500.0
        assert svc._get_metric_value(kpi, TargetMetric.ROAS) == 2.5
        assert svc._get_metric_value(kpi, TargetMetric.CONVERSIONS) == 42
        assert svc._get_metric_value(kpi, TargetMetric.LEADS) == 7
        assert svc._get_metric_value(kpi, TargetMetric.PIPELINE_VALUE) == 9000.0
        assert svc._get_metric_value(kpi, TargetMetric.WON_REVENUE) == 2500.0
        assert svc._get_metric_value(kpi, TargetMetric.CPA) is None

    async def test_custom_drop_threshold_not_met(self, svc, db_session, test_tenant):
        tenant_id = test_tenant["id"]
        target = await _make_target(db_session, tenant_id, platform=None)
        for offset, cents in ((3, 100_00), (2, 100_00), (1, 100_00), (0, 60_00)):
            await _make_kpi(
                db_session,
                tenant_id,
                AS_OF - timedelta(days=offset),
                spend_cents=cents,
            )
        # 40% drop < 50% threshold
        assert (
            await svc.check_pacing_cliff(target.id, AS_OF, drop_threshold_pct=50.0)
            is None
        )


# =============================================================================
# Query surfaces — get_active_alerts / get_alerts_by_status
# =============================================================================


class TestAlertQueries:
    async def test_get_active_alerts_filters(self, svc, db_session, test_tenant):
        tenant_id = test_tenant["id"]
        target_a = await _make_target(db_session, tenant_id, platform="meta")
        target_b = await _make_target(db_session, tenant_id, platform="google")

        active_warn = await _make_alert(db_session, tenant_id, target_a.id)
        active_crit = await _make_alert(
            db_session,
            tenant_id,
            target_b.id,
            severity=AlertSeverity.CRITICAL,
            alert_type=AlertType.OVERPACING_SPEND,
        )
        await _make_alert(
            db_session, tenant_id, target_a.id, status=AlertStatus.RESOLVED
        )

        all_active = await svc.get_active_alerts()
        assert {a.id for a in all_active} == {active_warn.id, active_crit.id}

        by_target = await svc.get_active_alerts(target_id=target_a.id)
        assert [a.id for a in by_target] == [active_warn.id]

        by_severity = await svc.get_active_alerts(severity=AlertSeverity.CRITICAL)
        assert [a.id for a in by_severity] == [active_crit.id]

        by_type = await svc.get_active_alerts(alert_type=AlertType.OVERPACING_SPEND)
        assert [a.id for a in by_type] == [active_crit.id]

    async def test_get_alerts_by_status_filters(self, svc, db_session, test_tenant):
        tenant_id = test_tenant["id"]
        target = await _make_target(db_session, tenant_id)
        resolved = await _make_alert(
            db_session,
            tenant_id,
            target.id,
            status=AlertStatus.RESOLVED,
            severity=AlertSeverity.CRITICAL,
        )
        acked = await _make_alert(
            db_session,
            tenant_id,
            target.id,
            status=AlertStatus.ACKNOWLEDGED,
            alert_type=AlertType.PACING_CLIFF,
        )
        await _make_alert(db_session, tenant_id, target.id)  # active

        got_resolved = await svc.get_alerts_by_status(AlertStatus.RESOLVED)
        assert [a.id for a in got_resolved] == [resolved.id]

        got_acked = await svc.get_alerts_by_status(
            AlertStatus.ACKNOWLEDGED,
            target_id=target.id,
            severity=AlertSeverity.WARNING,
            alert_type=AlertType.PACING_CLIFF,
        )
        assert [a.id for a in got_acked] == [acked.id]

        none_match = await svc.get_alerts_by_status(
            AlertStatus.DISMISSED, severity=AlertSeverity.INFO
        )
        assert none_match == []

    async def test_tenant_isolation_on_queries(self, svc, db_session, test_tenant):
        tenant_id = test_tenant["id"]
        target = await _make_target(db_session, tenant_id)
        await _make_alert(db_session, tenant_id, target.id)

        other = PacingAlertService(db_session, tenant_id + 999)
        assert await other.get_active_alerts() == []


# =============================================================================
# Lifecycle — acknowledge / resolve / dismiss
# =============================================================================


class TestAlertLifecycle:
    async def test_acknowledge(self, svc, db_session, test_tenant, test_user):
        alert = await _make_alert(db_session, test_tenant["id"])
        got = await svc.acknowledge_alert(alert.id, user_id=test_user["id"])
        assert got is not None
        assert got.status == AlertStatus.ACKNOWLEDGED
        row = await db_session.get(PacingAlert, alert.id)
        assert row.status == AlertStatus.ACKNOWLEDGED

    async def test_acknowledge_unknown_returns_none(self, svc):
        assert await svc.acknowledge_alert(uuid4()) is None

    async def test_resolve_with_notes(self, svc, db_session, test_tenant, test_user):
        alert = await _make_alert(db_session, test_tenant["id"])
        got = await svc.resolve_alert(
            alert.id, user_id=test_user["id"], resolution_notes="budget fixed"
        )
        assert got.status == AlertStatus.RESOLVED
        assert got.resolved_at is not None
        assert got.resolved_by_user_id == test_user["id"]
        assert got.resolution_notes == "budget fixed"

    async def test_resolve_unknown_returns_none(self, svc):
        assert await svc.resolve_alert(uuid4()) is None

    async def test_dismiss_with_reason(self, svc, db_session, test_tenant, test_user):
        alert = await _make_alert(db_session, test_tenant["id"])
        got = await svc.dismiss_alert(
            alert.id, user_id=test_user["id"], reason="false positive"
        )
        assert got.status == AlertStatus.DISMISSED
        assert got.resolution_notes == "Dismissed: false positive"
        assert got.resolved_at is not None

    async def test_dismiss_without_reason(self, svc, db_session, test_tenant):
        alert = await _make_alert(db_session, test_tenant["id"])
        got = await svc.dismiss_alert(alert.id)
        assert got.resolution_notes == "Dismissed"

    async def test_dismiss_unknown_returns_none(self, svc):
        assert await svc.dismiss_alert(uuid4()) is None

    async def test_lifecycle_respects_tenant(self, svc, db_session, test_tenant):
        alert = await _make_alert(db_session, test_tenant["id"])
        other = PacingAlertService(db_session, test_tenant["id"] + 999)
        assert await other.acknowledge_alert(alert.id) is None
        assert await other.resolve_alert(alert.id) is None
        assert await other.dismiss_alert(alert.id) is None
        row = await db_session.get(PacingAlert, alert.id)
        assert row.status == AlertStatus.ACTIVE


# =============================================================================
# get_alert_summary
# =============================================================================


class TestAlertSummary:
    async def test_empty_period(self, svc):
        summary = await svc.get_alert_summary(
            start_date=date(2025, 1, 1), end_date=date(2025, 1, 31)
        )
        assert summary["total_alerts"] == 0
        assert summary["resolution"] == {"avg_hours": None, "total_resolved": 0}
        assert summary["period"] == {"start": "2025-01-01", "end": "2025-01-31"}
        assert all(v == 0 for v in summary["by_status"].values())

    async def test_counts_and_resolution_time(self, svc, db_session, test_tenant):
        tenant_id = test_tenant["id"]
        now = datetime.now(timezone.utc)

        await _make_alert(db_session, tenant_id, severity=AlertSeverity.INFO)
        await _make_alert(
            db_session,
            tenant_id,
            severity=AlertSeverity.CRITICAL,
            alert_type=AlertType.PACING_CLIFF,
            status=AlertStatus.ACKNOWLEDGED,
        )
        # Two resolved alerts: 4h and 6h to resolve -> avg 5.0h
        await _make_alert(
            db_session,
            tenant_id,
            status=AlertStatus.RESOLVED,
            created_at=now - timedelta(hours=4),
            resolved_at=now,
        )
        await _make_alert(
            db_session,
            tenant_id,
            status=AlertStatus.RESOLVED,
            alert_type=AlertType.OVERPACING_SPEND,
            created_at=now - timedelta(hours=6),
            resolved_at=now,
        )

        summary = await svc.get_alert_summary(
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=1),
        )

        assert summary["total_alerts"] == 4
        assert summary["by_status"]["active"] == 1
        assert summary["by_status"]["acknowledged"] == 1
        assert summary["by_status"]["resolved"] == 2
        assert summary["by_status"]["dismissed"] == 0
        assert summary["by_severity"]["info"] == 1
        assert summary["by_severity"]["critical"] == 1
        assert summary["by_severity"]["warning"] == 2
        assert summary["by_type"]["underpacing_spend"] == 2
        assert summary["by_type"]["overpacing_spend"] == 1
        assert summary["by_type"]["pacing_cliff"] == 1
        assert summary["resolution"]["total_resolved"] == 2
        assert summary["resolution"]["avg_hours"] == pytest.approx(5.0, abs=0.1)

    async def test_default_dates_cover_last_30_days(self, svc, db_session, test_tenant):
        await _make_alert(db_session, test_tenant["id"])
        summary = await svc.get_alert_summary()
        assert summary["total_alerts"] == 1
        assert summary["period"]["end"] == date.today().isoformat()
        assert (
            summary["period"]["start"]
            == (date.today() - timedelta(days=30)).isoformat()
        )


# =============================================================================
# AlertNotificationService — Slack
# =============================================================================


def _mock_slack_service(send_result=True, send_side_effect=None):
    instance = MagicMock()
    instance.send_message = AsyncMock(
        return_value=send_result, side_effect=send_side_effect
    )
    instance.close = AsyncMock()
    cls = MagicMock(return_value=instance)
    return cls, instance


class TestSlackNotification:
    async def test_empty_webhook_url_returns_false(self, notifier):
        alert = _detached_alert()
        assert await notifier.send_slack_notification(alert, "") is False

    async def test_success_builds_block_kit_payload(self, notifier):
        alert = _detached_alert()
        cls, instance = _mock_slack_service(send_result=True)
        with patch("app.services.pacing.alert_service.SlackNotificationService", cls):
            ok = await notifier.send_slack_notification(
                alert, "https://hooks.slack.com/services/T/B/x"
            )

        assert ok is True
        cls.assert_called_once_with("https://hooks.slack.com/services/T/B/x")
        kwargs = instance.send_message.await_args.kwargs
        assert kwargs["text"] == f"[CRITICAL] {alert.title}"
        attachment = kwargs["attachments"][0]
        assert attachment["color"] == "#ef4444"
        blocks = attachment["blocks"]
        assert blocks[0]["type"] == "header"
        assert blocks[0]["text"]["text"] == alert.title
        flat = str(blocks)
        # Context fields for MTD, deviation and days remaining are included
        assert "MTD Actual" in flat
        assert "MTD Expected" in flat
        assert "+40.0%" in flat
        assert "Days Remaining" in flat
        assert "View in Dashboard" in flat
        instance.close.assert_awaited_once()

    async def test_minimal_alert_omits_context_fields(self, notifier):
        alert = _detached_alert(
            severity=AlertSeverity.INFO,
            mtd_actual=None,
            mtd_expected=None,
            deviation_pct=None,
            days_remaining=None,
            projected_eom=None,
        )
        cls, instance = _mock_slack_service(send_result=True)
        with patch("app.services.pacing.alert_service.SlackNotificationService", cls):
            ok = await notifier.send_slack_notification(alert, "https://hook")
        assert ok is True
        blocks = instance.send_message.await_args.kwargs["attachments"][0]["blocks"]
        flat = str(blocks)
        assert "MTD Actual" not in flat
        assert "Days Remaining" not in flat
        assert instance.send_message.await_args.kwargs["text"].startswith("[INFO]")

    async def test_delivery_failure_returns_false(self, notifier):
        alert = _detached_alert()
        cls, instance = _mock_slack_service(send_result=False)
        with patch("app.services.pacing.alert_service.SlackNotificationService", cls):
            ok = await notifier.send_slack_notification(alert, "https://hook")
        assert ok is False
        instance.close.assert_awaited_once()

    async def test_connection_error_returns_false_and_closes(self, notifier):
        alert = _detached_alert()
        cls, instance = _mock_slack_service(send_side_effect=ConnectionError("refused"))
        with patch("app.services.pacing.alert_service.SlackNotificationService", cls):
            ok = await notifier.send_slack_notification(alert, "https://hook")
        assert ok is False
        instance.close.assert_awaited_once()


# =============================================================================
# AlertNotificationService — Email
# =============================================================================


def _mock_email_service(send_result=True, send_side_effect=None):
    service = MagicMock()
    service._create_message = MagicMock(return_value="MIME-MESSAGE")
    service._send_email = MagicMock(
        return_value=send_result, side_effect=send_side_effect
    )
    return service


class TestEmailNotification:
    async def test_no_recipients_returns_false(self, notifier):
        assert await notifier.send_email_notification(_detached_alert(), []) is False

    async def test_success_sends_to_all_recipients(self, notifier):
        alert = _detached_alert()
        email_service = _mock_email_service(send_result=True)
        with patch(
            "app.services.pacing.alert_service.get_email_service",
            return_value=email_service,
        ):
            ok = await notifier.send_email_notification(
                alert, ["a@example.com", "b@example.com"]
            )

        assert ok is True
        assert email_service._send_email.call_count == 2
        kwargs = email_service._create_message.call_args.kwargs
        assert kwargs["subject"] == f"[Stratum AI] CRITICAL Pacing Alert: {alert.title}"
        html = kwargs["html_content"]
        assert "MTD Actual" in html
        assert "MTD Expected" in html
        assert "Projected EOM" in html
        assert "Deviation" in html
        assert "Days Remaining" in html
        assert "View in Dashboard" in html
        assert alert.message in kwargs["text_content"]

    async def test_minimal_alert_has_no_context_table(self, notifier):
        alert = _detached_alert(
            severity=AlertSeverity.WARNING,
            mtd_actual=None,
            mtd_expected=None,
            deviation_pct=None,
            days_remaining=None,
            projected_eom=None,
        )
        email_service = _mock_email_service(send_result=True)
        with patch(
            "app.services.pacing.alert_service.get_email_service",
            return_value=email_service,
        ):
            ok = await notifier.send_email_notification(alert, ["a@example.com"])
        assert ok is True
        html = email_service._create_message.call_args.kwargs["html_content"]
        assert "MTD Actual" not in html
        assert "<table" not in html

    async def test_partial_failure_returns_false(self, notifier):
        email_service = _mock_email_service()
        email_service._send_email.side_effect = [True, False]
        with patch(
            "app.services.pacing.alert_service.get_email_service",
            return_value=email_service,
        ):
            ok = await notifier.send_email_notification(
                _detached_alert(), ["a@example.com", "b@example.com"]
            )
        assert ok is False

    async def test_smtp_exception_returns_false(self, notifier):
        email_service = _mock_email_service(
            send_side_effect=smtplib.SMTPException("relay denied")
        )
        with patch(
            "app.services.pacing.alert_service.get_email_service",
            return_value=email_service,
        ):
            ok = await notifier.send_email_notification(
                _detached_alert(), ["a@example.com"]
            )
        assert ok is False


# =============================================================================
# AlertNotificationService — WhatsApp
# =============================================================================


class TestWhatsAppNotification:
    async def test_no_phone_numbers_returns_false(self, notifier):
        assert await notifier.send_whatsapp_notification(_detached_alert(), []) is False

    async def test_not_configured_returns_false(self, notifier):
        with patch(
            "app.services.pacing.alert_service.is_whatsapp_configured",
            return_value=False,
        ):
            ok = await notifier.send_whatsapp_notification(
                _detached_alert(), ["+15551234567"]
            )
        assert ok is False

    async def test_success_includes_pacing_context(self, notifier):
        alert = _detached_alert()
        wa_client = MagicMock()
        wa_client.send_text_message = AsyncMock(return_value={"messages": [{}]})
        with (
            patch(
                "app.services.pacing.alert_service.is_whatsapp_configured",
                return_value=True,
            ),
            patch(
                "app.services.pacing.alert_service.get_whatsapp_client",
                return_value=wa_client,
            ),
        ):
            ok = await notifier.send_whatsapp_notification(
                alert, ["+15551234567", "+201001234567"]
            )

        assert ok is True
        assert wa_client.send_text_message.await_count == 2
        kwargs = wa_client.send_text_message.await_args.kwargs
        assert kwargs["recipient_phone"] == "+201001234567"
        assert "[CRITICAL] Stratum AI Pacing Alert" in kwargs["text"]
        assert "Deviation: +40.0%" in kwargs["text"]
        assert "Days Remaining: 15" in kwargs["text"]

    async def test_minimal_alert_omits_context_lines(self, notifier):
        alert = _detached_alert(deviation_pct=None, days_remaining=None)
        wa_client = MagicMock()
        wa_client.send_text_message = AsyncMock(return_value={"messages": [{}]})
        with (
            patch(
                "app.services.pacing.alert_service.is_whatsapp_configured",
                return_value=True,
            ),
            patch(
                "app.services.pacing.alert_service.get_whatsapp_client",
                return_value=wa_client,
            ),
        ):
            ok = await notifier.send_whatsapp_notification(alert, ["+15551234567"])
        assert ok is True
        text = wa_client.send_text_message.await_args.kwargs["text"]
        assert "Deviation:" not in text
        assert "Days Remaining:" not in text

    async def test_send_error_returns_false(self, notifier):
        wa_client = MagicMock()
        wa_client.send_text_message = AsyncMock(side_effect=ValueError("bad phone"))
        with (
            patch(
                "app.services.pacing.alert_service.is_whatsapp_configured",
                return_value=True,
            ),
            patch(
                "app.services.pacing.alert_service.get_whatsapp_client",
                return_value=wa_client,
            ),
        ):
            ok = await notifier.send_whatsapp_notification(
                _detached_alert(), ["+15551234567"]
            )
        assert ok is False


# =============================================================================
# AlertNotificationService — notify_alert orchestrator
# =============================================================================


async def _make_slack_integration(db_session, tenant_id: int, **overrides):
    from app.models.settings import SlackIntegration

    fields = dict(
        tenant_id=tenant_id,
        webhook_url="https://hooks.slack.com/services/T/B/secret",
        is_active=True,
    )
    fields.update(overrides)
    integration = SlackIntegration(**fields)
    db_session.add(integration)
    await db_session.flush()
    return integration


class TestNotifyAlert:
    async def test_target_not_found_returns_empty(
        self, notifier, db_session, test_tenant
    ):
        alert = await _make_alert(db_session, test_tenant["id"], target_id=None)
        assert await notifier.notify_alert(alert) == {}

    async def test_all_channels_dispatched(self, notifier, db_session, test_tenant):
        tenant_id = test_tenant["id"]
        target = await _make_target(
            db_session,
            tenant_id,
            notify_slack=True,
            notify_email=True,
            notify_whatsapp=True,
            notification_recipients=[
                "ops@example.com",
                "+15551234567",
                42,  # non-string entries must be ignored
                "not-an-email-or-phone",
            ],
        )
        await _make_slack_integration(db_session, tenant_id)
        alert = await _make_alert(db_session, tenant_id, target.id)

        slack_mock = AsyncMock(return_value=True)
        email_mock = AsyncMock(return_value=True)
        wa_mock = AsyncMock(return_value=False)
        with (
            patch.object(
                AlertNotificationService, "send_slack_notification", slack_mock
            ),
            patch.object(
                AlertNotificationService, "send_email_notification", email_mock
            ),
            patch.object(
                AlertNotificationService, "send_whatsapp_notification", wa_mock
            ),
        ):
            results = await notifier.notify_alert(alert)

        assert results == {"slack": True, "email": True, "whatsapp": False}
        # Slack got the decrypted webhook URL
        assert (
            slack_mock.await_args.args[1]
            == "https://hooks.slack.com/services/T/B/secret"
        )
        # Recipient routing: emails vs phone numbers, junk dropped
        assert email_mock.await_args.args[1] == ["ops@example.com"]
        assert wa_mock.await_args.args[1] == ["+15551234567"]
        # Dispatch results persisted on the alert row
        row = await db_session.get(PacingAlert, alert.id)
        assert row.notifications_sent == {
            "slack": True,
            "email": True,
            "whatsapp": False,
        }

    async def test_slack_enabled_without_integration_is_skipped(
        self, notifier, db_session, test_tenant
    ):
        tenant_id = test_tenant["id"]
        target = await _make_target(db_session, tenant_id, notify_slack=True)
        alert = await _make_alert(db_session, tenant_id, target.id)
        results = await notifier.notify_alert(alert)
        assert results == {}

    async def test_inactive_slack_integration_is_skipped(
        self, notifier, db_session, test_tenant
    ):
        tenant_id = test_tenant["id"]
        target = await _make_target(db_session, tenant_id, notify_slack=True)
        await _make_slack_integration(db_session, tenant_id, is_active=False)
        alert = await _make_alert(db_session, tenant_id, target.id)
        results = await notifier.notify_alert(alert)
        assert "slack" not in results

    async def test_slack_dispatch_exception_recorded_as_false(
        self, notifier, db_session, test_tenant
    ):
        tenant_id = test_tenant["id"]
        target = await _make_target(db_session, tenant_id, notify_slack=True)
        await _make_slack_integration(db_session, tenant_id)
        alert = await _make_alert(db_session, tenant_id, target.id)

        with patch.object(
            AlertNotificationService,
            "send_slack_notification",
            AsyncMock(side_effect=ConnectionError("down")),
        ):
            results = await notifier.notify_alert(alert)
        assert results == {"slack": False}

    async def test_email_enabled_without_recipients_is_skipped(
        self, notifier, db_session, test_tenant
    ):
        tenant_id = test_tenant["id"]
        target = await _make_target(
            db_session,
            tenant_id,
            notify_email=True,
            notification_recipients=["+15551234567"],  # phones only, no emails
        )
        alert = await _make_alert(db_session, tenant_id, target.id)
        results = await notifier.notify_alert(alert)
        assert results == {}

    async def test_email_dispatch_exception_recorded_as_false(
        self, notifier, db_session, test_tenant
    ):
        tenant_id = test_tenant["id"]
        target = await _make_target(
            db_session,
            tenant_id,
            notify_email=True,
            notification_recipients=["ops@example.com"],
        )
        alert = await _make_alert(db_session, tenant_id, target.id)
        with patch.object(
            AlertNotificationService,
            "send_email_notification",
            AsyncMock(side_effect=smtplib.SMTPException("relay")),
        ):
            results = await notifier.notify_alert(alert)
        assert results == {"email": False}

    async def test_whatsapp_enabled_without_phones_is_skipped(
        self, notifier, db_session, test_tenant
    ):
        tenant_id = test_tenant["id"]
        target = await _make_target(
            db_session,
            tenant_id,
            notify_whatsapp=True,
            notification_recipients=["ops@example.com"],  # emails only
        )
        alert = await _make_alert(db_session, tenant_id, target.id)
        results = await notifier.notify_alert(alert)
        assert results == {}

    async def test_whatsapp_dispatch_exception_recorded_as_false(
        self, notifier, db_session, test_tenant
    ):
        tenant_id = test_tenant["id"]
        target = await _make_target(
            db_session,
            tenant_id,
            notify_whatsapp=True,
            notification_recipients=["+15551234567"],
        )
        alert = await _make_alert(db_session, tenant_id, target.id)
        with patch.object(
            AlertNotificationService,
            "send_whatsapp_notification",
            AsyncMock(side_effect=ValueError("bad")),
        ):
            results = await notifier.notify_alert(alert)
        assert results == {"whatsapp": False}

    async def test_null_recipients_defaults_to_empty(
        self, notifier, db_session, test_tenant
    ):
        tenant_id = test_tenant["id"]
        target = await _make_target(
            db_session,
            tenant_id,
            notify_email=True,
            notify_whatsapp=True,
            notification_recipients=None,
        )
        alert = await _make_alert(db_session, tenant_id, target.id)
        results = await notifier.notify_alert(alert)
        assert results == {}
