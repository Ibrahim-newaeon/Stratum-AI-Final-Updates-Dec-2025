# =============================================================================
# Stratum AI - Report Scheduler Deep Integration Tests (#342 Batch 4)
# =============================================================================
"""DB-backed integration tests for ``app.services.reporting.scheduler``.

Covers the orchestration paths that the CronParser unit tests
(``tests/unit/test_cron_parser.py``) and the schedules API tests leave out:

- ``calculate_next_run`` frequency rollover math (weekly, biweekly, monthly
  incl. last-day/-1 and invalid-day fallbacks, quarterly incl. year wrap,
  custom-cron, and the default branch) plus timezone conversion.
- ``get_due_schedules`` against real schedule rows (due/paused/inactive/
  future/foreign-tenant filtering and ordering).
- ``execute_schedule`` / ``run_now`` dispatch with generation + delivery
  mocked at the service boundary, asserting schedule bookkeeping for both
  success and failure.
- ``process_due_schedules`` batch accounting (and its logger bug, see
  TestProcessDueSchedules).
- ``SchedulerWorker`` start/stop loop and per-tenant fan-out.
"""

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.models.reporting import (
    ExecutionStatus,
    ReportExecution,
    ReportFormat,
    ReportTemplate,
    ReportType,
    ScheduledReport,
    ScheduleFrequency,
)
from app.services.reporting.scheduler import ReportScheduler, SchedulerWorker

pytestmark = pytest.mark.integration


# =============================================================================
# Builders
# =============================================================================


def _naive_utc(dt: datetime) -> datetime:
    """Normalize naive/aware datetimes to naive UTC for comparisons."""
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _sched(frequency, **overrides) -> ScheduledReport:
    """Unsaved ScheduledReport for pure next-run math (no DB defaults yet)."""
    base = dict(
        frequency=frequency,
        timezone="UTC",
        hour=8,
        minute=0,
        cron_expression=None,
        day_of_week=None,
        day_of_month=None,
    )
    base.update(overrides)
    return ScheduledReport(**base)


async def _seed_template(db_session, tenant_id, name) -> ReportTemplate:
    template = ReportTemplate(
        tenant_id=tenant_id,
        name=name,
        report_type=ReportType.CAMPAIGN_PERFORMANCE,
        config={"metrics": ["spend"], "sections": ["summary"]},
        default_format=ReportFormat.PDF,
        available_formats=["pdf", "csv"],
    )
    db_session.add(template)
    await db_session.flush()
    return template


async def _seed_schedule(db_session, tenant_id, template, **overrides):
    base = dict(
        tenant_id=tenant_id,
        template_id=template.id,
        name=f"Sched {uuid.uuid4().hex[:8]}",
        frequency=ScheduleFrequency.DAILY,
        timezone="UTC",
        hour=8,
        minute=0,
        date_range_type="last_7_days",
        delivery_channels=["slack"],
        delivery_config={"slack": {"webhook_url": "https://hooks.slack.com/x"}},
        next_run_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    base.update(overrides)
    schedule = ScheduledReport(**base)
    # Preload the relationship so execute_schedule never lazy-loads on the
    # async session.
    schedule.template = template
    db_session.add(schedule)
    await db_session.flush()
    return schedule


@pytest.fixture
def scheduler(db_session, test_tenant) -> ReportScheduler:
    return ReportScheduler(db_session, test_tenant["id"])


# =============================================================================
# calculate_next_run — frequency math
# =============================================================================
# Reference dates: 2026-07-06 = Monday, 2026-07-08 = Wednesday,
# 2026-07-10 = Friday. `after` is naive UTC (matches production call sites).


class TestCalculateNextRunFrequencies:
    def test_daily_before_target_time_runs_today(self, scheduler):
        run = scheduler.calculate_next_run(
            _sched(ScheduleFrequency.DAILY), after=datetime(2026, 7, 8, 6, 0)
        )
        assert run == datetime(2026, 7, 8, 8, 0)

    def test_daily_after_target_time_runs_tomorrow(self, scheduler):
        run = scheduler.calculate_next_run(
            _sched(ScheduleFrequency.DAILY), after=datetime(2026, 7, 8, 10, 0)
        )
        assert run == datetime(2026, 7, 9, 8, 0)

    def test_weekly_later_this_week(self, scheduler):
        run = scheduler.calculate_next_run(
            _sched(ScheduleFrequency.WEEKLY, day_of_week=4),  # Friday
            after=datetime(2026, 7, 8, 10, 0),  # Wednesday
        )
        assert run == datetime(2026, 7, 10, 8, 0)

    def test_weekly_day_already_passed_rolls_to_next_week(self, scheduler):
        run = scheduler.calculate_next_run(
            _sched(ScheduleFrequency.WEEKLY, day_of_week=0),  # Monday
            after=datetime(2026, 7, 8, 10, 0),  # Wednesday
        )
        assert run == datetime(2026, 7, 13, 8, 0)

    def test_biweekly_later_this_week(self, scheduler):
        run = scheduler.calculate_next_run(
            _sched(ScheduleFrequency.BIWEEKLY, day_of_week=4),
            after=datetime(2026, 7, 8, 10, 0),
        )
        assert run == datetime(2026, 7, 10, 8, 0)

    def test_biweekly_day_passed_rolls_two_weeks(self, scheduler):
        run = scheduler.calculate_next_run(
            _sched(ScheduleFrequency.BIWEEKLY, day_of_week=0),  # Monday
            after=datetime(2026, 7, 8, 10, 0),  # Wednesday
        )
        assert run == datetime(2026, 7, 20, 8, 0)

    def test_biweekly_same_day_past_time_rolls_two_weeks(self, scheduler):
        run = scheduler.calculate_next_run(
            _sched(ScheduleFrequency.BIWEEKLY, day_of_week=2),  # Wednesday
            after=datetime(2026, 7, 8, 10, 0),  # Wednesday 10:00 > 08:00
        )
        assert run == datetime(2026, 7, 22, 8, 0)

    def test_monthly_upcoming_day_this_month(self, scheduler):
        run = scheduler.calculate_next_run(
            _sched(ScheduleFrequency.MONTHLY, day_of_month=15),
            after=datetime(2026, 7, 8, 10, 0),
        )
        assert run == datetime(2026, 7, 15, 8, 0)

    def test_monthly_day_passed_rolls_to_next_month(self, scheduler):
        run = scheduler.calculate_next_run(
            _sched(ScheduleFrequency.MONTHLY, day_of_month=1),
            after=datetime(2026, 7, 8, 10, 0),
        )
        assert run == datetime(2026, 8, 1, 8, 0)

    def test_monthly_last_day_flag(self, scheduler):
        run = scheduler.calculate_next_run(
            _sched(ScheduleFrequency.MONTHLY, day_of_month=-1),
            after=datetime(2026, 7, 8, 10, 0),
        )
        assert run == datetime(2026, 7, 31, 8, 0)

    def test_monthly_last_day_flag_rolls_to_next_month_end(self, scheduler):
        run = scheduler.calculate_next_run(
            _sched(ScheduleFrequency.MONTHLY, day_of_month=-1),
            after=datetime(2026, 7, 31, 10, 0),
        )
        assert run == datetime(2026, 8, 31, 8, 0)

    def test_monthly_day_missing_this_month_falls_back_to_month_end(self, scheduler):
        # June has no 31st -> fall back to June 30.
        run = scheduler.calculate_next_run(
            _sched(ScheduleFrequency.MONTHLY, day_of_month=31),
            after=datetime(2026, 6, 10, 10, 0),
        )
        assert run == datetime(2026, 6, 30, 8, 0)

    def test_monthly_day_missing_next_month_falls_back_to_month_end(self, scheduler):
        # Aug 31 already passed; September has no 31st -> Sep 30.
        run = scheduler.calculate_next_run(
            _sched(ScheduleFrequency.MONTHLY, day_of_month=31),
            after=datetime(2026, 8, 31, 10, 0),
        )
        assert run == datetime(2026, 9, 30, 8, 0)

    def test_quarterly_next_quarter_same_year(self, scheduler):
        run = scheduler.calculate_next_run(
            _sched(ScheduleFrequency.QUARTERLY, day_of_month=1),
            after=datetime(2026, 2, 10, 10, 0),
        )
        assert run == datetime(2026, 4, 1, 8, 0)

    def test_quarterly_q4_wraps_to_next_year(self, scheduler):
        run = scheduler.calculate_next_run(
            _sched(ScheduleFrequency.QUARTERLY, day_of_month=1),
            after=datetime(2026, 11, 10, 10, 0),
        )
        assert run == datetime(2027, 1, 1, 8, 0)

    def test_quarterly_invalid_day_falls_back_to_first(self, scheduler):
        # April has no 31st -> first of the quarter month.
        run = scheduler.calculate_next_run(
            _sched(ScheduleFrequency.QUARTERLY, day_of_month=31),
            after=datetime(2026, 2, 10, 10, 0),
        )
        assert run == datetime(2026, 4, 1, 8, 0)

    def test_custom_with_cron_expression(self, scheduler):
        run = scheduler.calculate_next_run(
            _sched(ScheduleFrequency.CUSTOM, cron_expression="0 9 * * *"),
            after=datetime(2026, 7, 8, 10, 0),
        )
        assert run == datetime(2026, 7, 9, 9, 0)

    def test_custom_without_cron_defaults_to_tomorrow(self, scheduler):
        run = scheduler.calculate_next_run(
            _sched(ScheduleFrequency.CUSTOM), after=datetime(2026, 7, 8, 10, 0)
        )
        assert run == datetime(2026, 7, 9, 8, 0)

    def test_timezone_conversion_back_to_utc(self, scheduler):
        # 08:00 America/New_York (EDT, UTC-4) == 12:00 UTC.
        run = scheduler.calculate_next_run(
            _sched(ScheduleFrequency.DAILY, timezone="America/New_York"),
            after=datetime(2026, 7, 8, 10, 0),
        )
        assert run == datetime(2026, 7, 8, 12, 0)

    def test_after_defaults_to_now(self, scheduler):
        run = scheduler.calculate_next_run(_sched(ScheduleFrequency.DAILY))
        assert run > datetime.now(timezone.utc).replace(tzinfo=None)


# =============================================================================
# get_due_schedules
# =============================================================================


class TestGetDueSchedules:
    async def test_filters_and_orders_due_schedules(
        self, db_session, test_tenant, scheduler
    ):
        template = await _seed_template(db_session, test_tenant["id"], "Due Tmpl")
        now = datetime.now(timezone.utc)

        due_recent = await _seed_schedule(
            db_session,
            test_tenant["id"],
            template,
            next_run_at=now - timedelta(hours=1),
        )
        due_older = await _seed_schedule(
            db_session,
            test_tenant["id"],
            template,
            next_run_at=now - timedelta(hours=2),
        )
        await _seed_schedule(  # paused
            db_session,
            test_tenant["id"],
            template,
            next_run_at=now - timedelta(hours=1),
            is_paused=True,
        )
        await _seed_schedule(  # inactive
            db_session,
            test_tenant["id"],
            template,
            next_run_at=now - timedelta(hours=1),
            is_active=False,
        )
        await _seed_schedule(  # not yet due
            db_session,
            test_tenant["id"],
            template,
            next_run_at=now + timedelta(hours=1),
        )

        # Foreign tenant with a due schedule must not leak in.
        from app.base_models import Tenant

        other = Tenant(name="Other T", slug="other-t-sched", plan="starter")
        db_session.add(other)
        await db_session.flush()
        other_template = await _seed_template(db_session, other.id, "Other Tmpl")
        await _seed_schedule(
            db_session, other.id, other_template, next_run_at=now - timedelta(hours=3)
        )

        due = await scheduler.get_due_schedules()

        assert [s.id for s in due] == [due_older.id, due_recent.id]

    async def test_empty_when_nothing_due(self, scheduler):
        assert await scheduler.get_due_schedules() == []


# =============================================================================
# execute_schedule / run_now
# =============================================================================


class TestExecuteSchedule:
    async def test_success_updates_bookkeeping_and_delivers(
        self, db_session, test_tenant, scheduler
    ):
        template = await _seed_template(db_session, test_tenant["id"], "Exec Tmpl")
        schedule = await _seed_schedule(
            db_session,
            test_tenant["id"],
            template,
            format_override=ReportFormat.CSV,
            config_override={"metrics": ["roas"]},
        )
        execution = ReportExecution(
            tenant_id=test_tenant["id"],
            template_id=template.id,
            schedule_id=schedule.id,
            execution_type="scheduled",
            status=ExecutionStatus.COMPLETED,
            report_type=ReportType.CAMPAIGN_PERFORMANCE,
            format=ReportFormat.CSV,
            date_range_start=datetime.now(timezone.utc).date() - timedelta(days=6),
            date_range_end=datetime.now(timezone.utc).date(),
        )
        db_session.add(execution)
        await db_session.flush()

        gen_mock = AsyncMock(
            return_value={"success": True, "execution_id": execution.id}
        )
        deliver_mock = AsyncMock(return_value={"successful": 1, "failed": 0})
        scheduler.report_generator.generate_report = gen_mock
        scheduler.delivery_service.deliver_report = deliver_mock

        result = await scheduler.execute_schedule(schedule, triggered_by_user_id=None)

        assert result.id == execution.id

        # Generation dispatched with override format + merged config.
        gen_kwargs = gen_mock.await_args.kwargs
        assert gen_kwargs["template_id"] == schedule.template_id
        assert gen_kwargs["format"] == ReportFormat.CSV
        assert gen_kwargs["config_override"] == {
            "metrics": ["roas"],  # override wins
            "sections": ["summary"],  # template value preserved
        }
        assert gen_kwargs["schedule_id"] == schedule.id
        assert gen_kwargs["execution_type"] == "scheduled"
        today = datetime.now(timezone.utc).date()
        assert gen_kwargs["start_date"] == today - timedelta(days=6)
        assert gen_kwargs["end_date"] == today

        # Delivery dispatched with schedule's channels + config.
        deliver_kwargs = deliver_mock.await_args.kwargs
        assert deliver_kwargs["execution_id"] == execution.id
        assert deliver_kwargs["channels"] == ["slack"]
        assert deliver_kwargs["delivery_config"] == {
            "slack": {"webhook_url": "https://hooks.slack.com/x"}
        }

        # Schedule bookkeeping.
        assert schedule.last_run_status == ExecutionStatus.COMPLETED
        assert schedule.run_count == 1
        assert schedule.failure_count == 0
        assert schedule.last_run_at is not None
        assert _naive_utc(schedule.next_run_at) > _naive_utc(datetime.now(timezone.utc))

    async def test_default_format_from_template_when_no_override(
        self, db_session, test_tenant, scheduler
    ):
        template = await _seed_template(db_session, test_tenant["id"], "Fmt Tmpl")
        schedule = await _seed_schedule(db_session, test_tenant["id"], template)
        execution = ReportExecution(
            tenant_id=test_tenant["id"],
            execution_type="scheduled",
            status=ExecutionStatus.COMPLETED,
            report_type=ReportType.CAMPAIGN_PERFORMANCE,
            format=ReportFormat.PDF,
            date_range_start=datetime.now(timezone.utc).date(),
            date_range_end=datetime.now(timezone.utc).date(),
        )
        db_session.add(execution)
        await db_session.flush()

        scheduler.report_generator.generate_report = AsyncMock(
            return_value={"execution_id": execution.id}
        )
        scheduler.delivery_service.deliver_report = AsyncMock(return_value={})

        await scheduler.execute_schedule(schedule)

        gen_kwargs = scheduler.report_generator.generate_report.await_args.kwargs
        assert gen_kwargs["format"] == ReportFormat.PDF

    async def test_failure_records_failed_status_and_reraises(
        self, db_session, test_tenant, scheduler
    ):
        template = await _seed_template(db_session, test_tenant["id"], "Fail Tmpl")
        schedule = await _seed_schedule(db_session, test_tenant["id"], template)

        scheduler.report_generator.generate_report = AsyncMock(
            side_effect=ValueError("generation exploded")
        )
        scheduler.delivery_service.deliver_report = AsyncMock()

        with pytest.raises(ValueError, match="generation exploded"):
            await scheduler.execute_schedule(schedule)

        assert schedule.last_run_status == ExecutionStatus.FAILED
        assert schedule.failure_count == 1
        assert schedule.run_count == 0
        assert schedule.last_run_at is not None
        assert schedule.next_run_at is not None
        scheduler.delivery_service.deliver_report.assert_not_awaited()


class TestRunNow:
    async def test_unknown_schedule_raises(self, scheduler):
        with pytest.raises(ValueError, match="Schedule not found"):
            await scheduler.run_now(uuid.uuid4())

    async def test_foreign_tenant_schedule_raises(
        self, db_session, test_tenant, scheduler
    ):
        from app.base_models import Tenant

        other = Tenant(name="Other RN", slug="other-run-now", plan="starter")
        db_session.add(other)
        await db_session.flush()
        template = await _seed_template(db_session, other.id, "RN Tmpl")
        schedule = await _seed_schedule(db_session, other.id, template)

        with pytest.raises(ValueError, match="Schedule not found"):
            await scheduler.run_now(schedule.id)

    async def test_run_now_dispatches_execute_schedule(
        self, db_session, test_tenant, scheduler
    ):
        template = await _seed_template(db_session, test_tenant["id"], "RN2 Tmpl")
        schedule = await _seed_schedule(db_session, test_tenant["id"], template)

        with patch.object(
            ReportScheduler, "execute_schedule", AsyncMock(return_value="EXECUTED")
        ) as exec_mock:
            result = await scheduler.run_now(schedule.id, triggered_by_user_id=42)

        assert result == "EXECUTED"
        args = exec_mock.await_args.args
        assert args[0].id == schedule.id
        assert args[1] == 42


# =============================================================================
# process_due_schedules
# =============================================================================


class TestProcessDueSchedules:
    async def test_no_due_schedules(self, scheduler):
        results = await scheduler.process_due_schedules()
        assert results == {"processed": 0, "succeeded": 0, "failed": 0, "errors": []}

    async def test_success_accounting(self, db_session, test_tenant, scheduler):
        template = await _seed_template(db_session, test_tenant["id"], "Batch Tmpl")
        await _seed_schedule(db_session, test_tenant["id"], template)

        scheduler.execute_schedule = AsyncMock()

        results = await scheduler.process_due_schedules()

        assert results["processed"] == 1
        assert results["succeeded"] == 1
        assert results["failed"] == 0
        scheduler.execute_schedule.assert_awaited_once()

    async def test_failure_accounting_with_logger_patched(
        self, db_session, test_tenant, scheduler
    ):
        # The failure branch calls logging's stdlib logger with structlog-style
        # kwargs (see test below); patch the module logger to reach the
        # accounting lines.
        template = await _seed_template(db_session, test_tenant["id"], "Batch Tmpl F")
        schedule = await _seed_schedule(db_session, test_tenant["id"], template)

        scheduler.execute_schedule = AsyncMock(side_effect=ValueError("kaboom"))

        with patch("app.services.reporting.scheduler.logger"):
            results = await scheduler.process_due_schedules()

        assert results["processed"] == 1
        assert results["succeeded"] == 0
        assert results["failed"] == 1
        assert results["errors"] == [
            {
                "schedule_id": str(schedule.id),
                "name": schedule.name,
                "error": "kaboom",
            }
        ]

    async def test_bug_failure_branch_crashes_when_logger_enabled(
        self, db_session, test_tenant, scheduler
    ):
        # PRODUCTION BUG (documented, not fixed here): scheduler.py:539-543
        # calls ``logger.error("schedule_execution_failed", schedule_id=...,
        # error=...)`` on a *stdlib* logger (``logging.getLogger(__name__)``),
        # whose kwargs validation rejects unknown keywords. Whenever the
        # module logger is enabled (it is disabled by setup_logging's
        # dictConfig in this test session, which is why the previous test
        # passes), a schedule failure raises TypeError instead of being
        # recorded, aborting the whole batch. When the logger is disabled,
        # the failure log line is silently dropped instead.
        import logging

        template = await _seed_template(db_session, test_tenant["id"], "Bug Tmpl")
        await _seed_schedule(db_session, test_tenant["id"], template)

        scheduler.execute_schedule = AsyncMock(side_effect=ValueError("kaboom"))

        sched_logger = logging.getLogger("app.services.reporting.scheduler")
        prev_disabled = sched_logger.disabled
        prev_manager_disable = logging.root.manager.disable
        sched_logger.disabled = False
        logging.disable(logging.NOTSET)
        try:
            with pytest.raises(TypeError, match="unexpected keyword"):
                await scheduler.process_due_schedules()
        finally:
            sched_logger.disabled = prev_disabled
            logging.disable(prev_manager_disable)


# =============================================================================
# Schedule management (create / update / pause / resume / delete)
# =============================================================================


class TestScheduleManagement:
    async def test_create_schedule_persists_and_computes_next_run(
        self, db_session, test_tenant, scheduler
    ):
        template = await _seed_template(db_session, test_tenant["id"], "Create Tmpl")

        schedule = await scheduler.create_schedule(
            template_id=template.id,
            name="Nightly digest",
            frequency=ScheduleFrequency.DAILY,
            delivery_config={"email": {"recipients": ["a@x.com"]}},
            description="every night",
            hour=6,
            minute=30,
            created_by_user_id=None,
        )

        assert schedule.id is not None
        assert schedule.tenant_id == test_tenant["id"]
        assert schedule.name == "Nightly digest"
        assert schedule.delivery_channels == ["email"]  # default applied
        assert schedule.next_run_at is not None
        assert schedule.is_active is True
        assert schedule.is_paused is False

    async def test_create_schedule_unknown_template_raises(self, scheduler):
        with pytest.raises(ValueError, match="Template not found"):
            await scheduler.create_schedule(
                template_id=uuid.uuid4(),
                name="Orphan",
                frequency=ScheduleFrequency.DAILY,
                delivery_config={},
            )

    async def test_create_schedule_foreign_tenant_template_raises(
        self, db_session, test_tenant, scheduler
    ):
        from app.base_models import Tenant

        other = Tenant(name="Other CT", slug="other-create-t", plan="starter")
        db_session.add(other)
        await db_session.flush()
        template = await _seed_template(db_session, other.id, "Foreign Tmpl")

        with pytest.raises(ValueError, match="Template not found"):
            await scheduler.create_schedule(
                template_id=template.id,
                name="Cross tenant",
                frequency=ScheduleFrequency.DAILY,
                delivery_config={},
            )

    async def test_update_non_timing_field_keeps_next_run(
        self, db_session, test_tenant, scheduler
    ):
        template = await _seed_template(db_session, test_tenant["id"], "Upd Tmpl")
        schedule = await _seed_schedule(db_session, test_tenant["id"], template)
        original_next_run = schedule.next_run_at

        updated = await scheduler.update_schedule(
            schedule.id, name="Renamed", not_a_real_field="ignored"
        )

        assert updated.name == "Renamed"
        assert not hasattr(updated, "not_a_real_field")
        assert updated.next_run_at == original_next_run

    async def test_update_timing_field_recalculates_next_run(
        self, db_session, test_tenant, scheduler
    ):
        template = await _seed_template(db_session, test_tenant["id"], "Upd2 Tmpl")
        schedule = await _seed_schedule(
            db_session,
            test_tenant["id"],
            template,
            next_run_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )

        updated = await scheduler.update_schedule(schedule.id, hour=23)

        assert updated.hour == 23
        # Recalculated into the future (old value was 1h in the past).
        assert _naive_utc(updated.next_run_at) > _naive_utc(datetime.now(timezone.utc))

    async def test_update_unknown_schedule_raises(self, scheduler):
        with pytest.raises(ValueError, match="Schedule not found"):
            await scheduler.update_schedule(uuid.uuid4(), name="nope")

    async def test_pause_and_resume_lifecycle(self, db_session, test_tenant, scheduler):
        template = await _seed_template(db_session, test_tenant["id"], "PR Tmpl")
        schedule = await _seed_schedule(db_session, test_tenant["id"], template)

        paused = await scheduler.pause_schedule(schedule.id)
        assert paused.is_paused is True

        resumed = await scheduler.resume_schedule(schedule.id)
        assert resumed.is_paused is False
        assert _naive_utc(resumed.next_run_at) > _naive_utc(datetime.now(timezone.utc))

    async def test_resume_unknown_schedule_raises(self, scheduler):
        with pytest.raises(ValueError, match="Schedule not found"):
            await scheduler.resume_schedule(uuid.uuid4())

    async def test_delete_schedule(self, db_session, test_tenant, scheduler):
        template = await _seed_template(db_session, test_tenant["id"], "Del Tmpl")
        schedule = await _seed_schedule(db_session, test_tenant["id"], template)

        assert await scheduler.delete_schedule(schedule.id) is True
        assert await scheduler.get_schedule(schedule.id) is None
        # Second delete: row is gone.
        assert await scheduler.delete_schedule(schedule.id) is False


# =============================================================================
# Query methods
# =============================================================================


class TestQueryMethods:
    async def test_get_schedule_scoping(self, db_session, test_tenant, scheduler):
        template = await _seed_template(db_session, test_tenant["id"], "Get Tmpl")
        schedule = await _seed_schedule(db_session, test_tenant["id"], template)

        found = await scheduler.get_schedule(schedule.id)
        assert found is not None and found.id == schedule.id

        assert await scheduler.get_schedule(uuid.uuid4()) is None

        foreign = ReportScheduler(db_session, test_tenant["id"] + 999)
        assert await foreign.get_schedule(schedule.id) is None

    async def test_list_schedules_filters_and_total(
        self, db_session, test_tenant, scheduler
    ):
        template_a = await _seed_template(db_session, test_tenant["id"], "List Tmpl A")
        template_b = await _seed_template(db_session, test_tenant["id"], "List Tmpl B")
        active = await _seed_schedule(db_session, test_tenant["id"], template_a)
        inactive = await _seed_schedule(
            db_session, test_tenant["id"], template_b, is_active=False
        )

        all_schedules, total = await scheduler.list_schedules()
        assert total == 2
        assert {s.id for s in all_schedules} == {active.id, inactive.id}

        active_only, total_active = await scheduler.list_schedules(is_active=True)
        assert total_active == 1
        assert [s.id for s in active_only] == [active.id]

        by_template, total_tmpl = await scheduler.list_schedules(
            template_id=template_b.id
        )
        assert total_tmpl == 1
        assert [s.id for s in by_template] == [inactive.id]

        paged, total_paged = await scheduler.list_schedules(limit=1, offset=0)
        assert total_paged == 2
        assert len(paged) == 1

    async def test_get_execution_history_ordered_desc(
        self, db_session, test_tenant, scheduler
    ):
        template = await _seed_template(db_session, test_tenant["id"], "Hist Tmpl")
        schedule = await _seed_schedule(db_session, test_tenant["id"], template)

        older = ReportExecution(
            tenant_id=test_tenant["id"],
            schedule_id=schedule.id,
            execution_type="scheduled",
            status=ExecutionStatus.COMPLETED,
            report_type=ReportType.CAMPAIGN_PERFORMANCE,
            format=ReportFormat.PDF,
            date_range_start=datetime.now(timezone.utc).date(),
            date_range_end=datetime.now(timezone.utc).date(),
            started_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        newer = ReportExecution(
            tenant_id=test_tenant["id"],
            schedule_id=schedule.id,
            execution_type="scheduled",
            status=ExecutionStatus.FAILED,
            report_type=ReportType.CAMPAIGN_PERFORMANCE,
            format=ReportFormat.PDF,
            date_range_start=datetime.now(timezone.utc).date(),
            date_range_end=datetime.now(timezone.utc).date(),
            started_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        db_session.add_all([older, newer])
        await db_session.flush()

        history = await scheduler.get_execution_history(schedule.id)
        assert [e.id for e in history] == [newer.id, older.id]

        assert await scheduler.get_execution_history(uuid.uuid4()) == []


# =============================================================================
# CronParser — coverage completeness for this module's standalone run
# =============================================================================
# The pure parsing behavior is unit-tested in tests/unit/test_cron_parser.py;
# these only exercise lines that suite doesn't reach (step-with-base parsing
# and the exhausted-search guard).


class TestCronParserEdges:
    def test_step_with_single_base_runs_to_max(self):
        from app.services.reporting.scheduler import CronParser

        # "10/20" -> start at 10, step 20 until max.
        assert CronParser.parse_field("10/20", 0, 59) == [10, 30, 50]

    def test_step_with_range_base(self):
        from app.services.reporting.scheduler import CronParser

        assert CronParser.parse_field("1-10/3", 0, 59) == [1, 4, 7, 10]

    def test_wildcard_step_and_plain_range(self):
        from app.services.reporting.scheduler import CronParser

        assert CronParser.parse_field("*/15", 0, 59) == [0, 15, 30, 45]
        assert CronParser.parse_field("1-5", 0, 59) == [1, 2, 3, 4, 5]

    def test_invalid_expression_raises(self):
        from app.services.reporting.scheduler import CronParser

        with pytest.raises(ValueError, match="Invalid cron expression"):
            CronParser.get_next_run("* * *", datetime(2026, 7, 8, 10, 0))

    @pytest.mark.slow
    def test_impossible_schedule_raises_after_search_window(self):
        from app.services.reporting.scheduler import CronParser

        # Feb 30 never exists -> the 1-year search window is exhausted.
        with pytest.raises(ValueError, match="Could not find next run time"):
            CronParser.get_next_run("0 0 30 2 *", datetime(2026, 7, 8, 10, 0))


# =============================================================================
# SchedulerWorker
# =============================================================================


class TestSchedulerWorker:
    async def test_start_loops_swallows_errors_and_stops(self):
        worker = SchedulerWorker(db_session_factory=None, check_interval=0)
        calls = {"n": 0}

        async def fake_process():
            calls["n"] += 1
            if calls["n"] == 1:
                raise ValueError("transient")
            worker.stop()

        worker._process_all_tenants = fake_process

        await worker.start()

        assert calls["n"] == 2
        assert worker._running is False

    async def test_process_all_tenants_fans_out_per_tenant(
        self, db_session, test_tenant
    ):
        template = await _seed_template(db_session, test_tenant["id"], "Worker Tmpl")
        await _seed_schedule(db_session, test_tenant["id"], template)

        @asynccontextmanager
        async def session_factory():
            yield db_session

        worker = SchedulerWorker(db_session_factory=session_factory, check_interval=0)

        with patch.object(
            ReportScheduler,
            "process_due_schedules",
            AsyncMock(
                return_value={
                    "processed": 1,
                    "succeeded": 1,
                    "failed": 0,
                    "errors": [],
                }
            ),
        ) as process_mock:
            await worker._process_all_tenants()

        process_mock.assert_awaited_once()

    async def test_process_all_tenants_noop_without_due_schedules(self, db_session):
        @asynccontextmanager
        async def session_factory():
            yield db_session

        worker = SchedulerWorker(db_session_factory=session_factory, check_interval=0)

        with patch.object(
            ReportScheduler, "process_due_schedules", AsyncMock()
        ) as process_mock:
            await worker._process_all_tenants()

        process_mock.assert_not_awaited()
