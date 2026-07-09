# =============================================================================
# Stratum AI - Forecasting Service Deep Integration Tests
# =============================================================================
"""DB-backed integration tests for ``app.services.pacing.forecasting``.

The unit suite (tests/unit/test_forecasting_helpers.py) covers the pure EWMA
and end-of-month helpers; this file drives the DB-backed pipeline with real
``daily_kpis`` rows:

- ``forecast_metric`` success path: EWMA model block, DoW factors, residual
  std, daily forecast rows, cumulative totals, and the EOM projection branch
  (present when the horizon reaches EOM, absent when it does not).
- ``forecast_eom``: forecast-backed, linear-fallback (insufficient data), and
  past-month (days_remaining == 0) branches.
- ``_load_historical_data`` scope filtering (platform / campaign / null-value
  skipping) and the 60-day window.
- ``_calculate_dow_factors`` / ``_calculate_residual_std`` edge branches that
  the pipeline cannot reach with rich data.
- ``save_forecast`` row persistence, and ``_get_metric_value`` branches.

Fixed-date tests are pinned to June 2026 with constant spend (100/day) so the
EWMA forecast is exactly 100/day. ``forecast_eom`` uses ``date.today()``
internally, so those tests seed data relative to today and compute
expectations dynamically.
"""

from datetime import date, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.pacing import DailyKPI, Forecast, TargetMetric
from app.services.pacing.forecasting import ForecastingService

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

AS_OF = date(2026, 6, 15)  # mid-June: EOM 2026-06-30 is 15 days out


def _kpi(
    tenant_id: int,
    d: date,
    *,
    spend: float = 100.0,
    revenue: float = 200.0,
    platform: str | None = "meta",
    campaign_id: str | None = None,
    roas: float | None = None,
) -> DailyKPI:
    return DailyKPI(
        tenant_id=tenant_id,
        date=d,
        platform=platform,
        campaign_id=campaign_id,
        account_id=None,
        spend_cents=int(spend * 100),
        revenue_cents=int(revenue * 100),
        conversions=2,
        leads=1,
        crm_leads=1,
        roas=roas,
        day_of_week=d.weekday(),
        is_weekend=d.weekday() >= 5,
    )


@pytest_asyncio.fixture
async def forecasting(db_session, test_tenant) -> ForecastingService:
    return ForecastingService(db_session, test_tenant["id"])


@pytest_asyncio.fixture
async def constant_meta_history(db_session, test_tenant) -> None:
    """56 days of constant meta spend (100/day) ending at AS_OF."""
    start = AS_OF - timedelta(days=55)
    db_session.add_all(
        _kpi(test_tenant["id"], start + timedelta(days=i)) for i in range(56)
    )
    await db_session.flush()


# =============================================================================
# forecast_metric
# =============================================================================


class TestForecastMetric:
    async def test_insufficient_data(self, forecasting):
        result = await forecasting.forecast_metric(
            TargetMetric.SPEND, forecast_days=10, platform="meta", as_of_date=AS_OF
        )
        assert result["status"] == "insufficient_data"
        assert "at least 7 days" in result["message"]
        assert result["metric"] == "spend"

    async def test_constant_series_success(self, forecasting, constant_meta_history):
        result = await forecasting.forecast_metric(
            TargetMetric.SPEND, forecast_days=30, platform="meta", as_of_date=AS_OF
        )

        assert result["status"] == "success"
        assert result["metric"] == "spend"
        assert result["as_of_date"] == AS_OF.isoformat()
        assert result["platform"] == "meta"
        assert result["historical_days"] == 56
        assert result["forecast_days"] == 30

        model = result["model"]
        assert model["type"] == "ewma_dow"
        assert model["ewma_value"] == pytest.approx(100.0)
        assert all(
            f == pytest.approx(1.0, abs=0.01) for f in model["dow_factors"].values()
        )
        assert model["residual_std"] == pytest.approx(0.0, abs=0.5)

        daily = result["daily_forecasts"]
        assert len(daily) == 30
        first = daily[0]
        assert first["date"] == (AS_OF + timedelta(days=1)).isoformat()
        assert first["day_of_week"] == (AS_OF + timedelta(days=1)).weekday()
        assert first["point_forecast"] == pytest.approx(100.0, rel=0.02)
        assert first["lower_bound"] <= first["point_forecast"] <= first["upper_bound"]
        # Cumulative is a running sum of point forecasts.
        assert daily[-1]["cumulative"] == pytest.approx(3000.0, rel=0.02)

        # 15 days to EOM <= 30-day horizon: projection present and equal to
        # the first 15 forecast days.
        eom = result["eom_projection"]
        assert eom is not None
        assert eom["date"] == "2026-06-30"
        assert eom["projected"] == pytest.approx(1500.0, rel=0.02)
        assert eom["lower"] <= eom["projected"] <= eom["upper"]

    async def test_eom_projection_absent_for_short_horizon(
        self, forecasting, constant_meta_history
    ):
        result = await forecasting.forecast_metric(
            TargetMetric.SPEND, forecast_days=5, platform="meta", as_of_date=AS_OF
        )
        assert result["status"] == "success"
        assert len(result["daily_forecasts"]) == 5
        # 15 days to EOM > 5-day horizon.
        assert result["eom_projection"] is None

    async def test_dow_seasonality_and_ci_widening(
        self, db_session, test_tenant, forecasting
    ):
        # Weekdays 100, weekends 40: DoW factors split around 1.0 and the
        # residual std becomes non-zero so CIs widen with the horizon.
        start = AS_OF - timedelta(days=41)
        for i in range(42):
            d = start + timedelta(days=i)
            spend = 40.0 if d.weekday() >= 5 else 100.0
            db_session.add(_kpi(test_tenant["id"], d, spend=spend))
        await db_session.flush()

        result = await forecasting.forecast_metric(
            TargetMetric.SPEND, forecast_days=14, platform="meta", as_of_date=AS_OF
        )
        assert result["status"] == "success"

        factors = result["model"]["dow_factors"]
        assert factors["5"] < 1.0 < factors["0"]  # Saturday < mean < Monday
        assert factors["6"] < 1.0

        daily = result["daily_forecasts"]
        widths = [f["upper_bound"] - f["lower_bound"] for f in daily]
        assert widths[-1] > widths[0] > 0  # horizon factor widens the CI
        assert all(f["lower_bound"] >= 0 for f in daily)

    async def test_campaign_scope(self, db_session, test_tenant, forecasting):
        for i in range(10):
            db_session.add(
                _kpi(
                    test_tenant["id"],
                    AS_OF - timedelta(days=i),
                    spend=20.0,
                    campaign_id="camp-fc",
                )
            )
        await db_session.flush()

        result = await forecasting.forecast_metric(
            TargetMetric.SPEND,
            forecast_days=7,
            platform="meta",
            campaign_id="camp-fc",
            as_of_date=AS_OF,
        )
        assert result["status"] == "success"
        assert result["campaign_id"] == "camp-fc"
        assert result["historical_days"] == 10
        assert result["model"]["ewma_value"] == pytest.approx(20.0)

    async def test_null_metric_values_are_skipped(
        self, forecasting, constant_meta_history
    ):
        # All seeded rows have roas=None, so ROAS history is empty and the
        # insufficient-data envelope comes back despite 56 KPI rows.
        result = await forecasting.forecast_metric(
            TargetMetric.ROAS, forecast_days=10, platform="meta", as_of_date=AS_OF
        )
        assert result["status"] == "insufficient_data"


# =============================================================================
# forecast_eom (today-relative)
# =============================================================================


class TestForecastEom:
    async def test_current_month_with_history(
        self, db_session, test_tenant, forecasting
    ):
        # 45 days of tenant-level (platform=None) revenue through today.
        today = date.today()
        for i in range(45):
            d = today - timedelta(days=i)
            db_session.add(_kpi(test_tenant["id"], d, revenue=200.0, platform=None))
        await db_session.flush()

        result = await forecasting.forecast_eom(TargetMetric.REVENUE)

        assert result["status"] == "success"
        month_start = today.replace(day=1)
        assert result["month"] == month_start.isoformat()
        assert result["period"]["start"] == month_start.isoformat()
        assert result["period"]["days_elapsed"] == today.day
        assert result["mtd_actual"] == pytest.approx(200.0 * today.day)
        assert result["daily_average"] == pytest.approx(200.0)
        assert result["projected_eom"] == pytest.approx(
            result["mtd_actual"] + result["remaining_forecast"], abs=0.05
        )
        if result["period"]["days_remaining"] > 0:
            # 45 days of history -> real forecast, ~200/day remaining.
            assert result["remaining_forecast"] == pytest.approx(
                200.0 * result["period"]["days_remaining"], rel=0.05
            )
            assert result["daily_needed"] > 0
        assert result["projected_lower"] <= result["projected_upper"]

    async def test_linear_fallback_when_insufficient_history(
        self, db_session, test_tenant, forecasting
    ):
        # Only 3 days of campaign data: forecast_metric returns
        # insufficient_data, so the linear +-20% fallback is used.
        today = date.today()
        month_start = today.replace(day=1)
        seeded_in_month = 0
        for i in range(3):
            d = today - timedelta(days=i)
            db_session.add(
                _kpi(
                    test_tenant["id"],
                    d,
                    spend=50.0,
                    platform=None,
                    campaign_id="sparse-eom",
                )
            )
            if d >= month_start:
                seeded_in_month += 1
        await db_session.flush()

        result = await forecasting.forecast_eom(
            TargetMetric.SPEND, campaign_id="sparse-eom"
        )

        assert result["status"] == "success"
        assert result["campaign_id"] == "sparse-eom"
        mtd = result["mtd_actual"]
        assert mtd == pytest.approx(50.0 * seeded_in_month)
        remaining = result["remaining_forecast"]
        if result["period"]["days_remaining"] > 0:
            daily_avg = mtd / result["period"]["days_elapsed"]
            assert remaining == pytest.approx(
                daily_avg * result["period"]["days_remaining"], abs=0.05
            )
            assert result["projected_lower"] == pytest.approx(
                mtd + remaining * 0.8, abs=0.05
            )
            assert result["projected_upper"] == pytest.approx(
                mtd + remaining * 1.2, abs=0.05
            )

    async def test_past_month_no_days_remaining(self, forecasting):
        # A fully elapsed month: days_remaining == 0, no forecast is run.
        past = date.today().replace(day=1) - timedelta(days=45)
        result = await forecasting.forecast_eom(
            TargetMetric.SPEND, campaign_id="no-data", month=past
        )

        assert result["status"] == "success"
        assert result["month"] == past.replace(day=1).isoformat()
        assert result["period"]["days_remaining"] == 0
        assert result["remaining_forecast"] == 0
        assert result["mtd_actual"] == 0.0
        assert result["projected_eom"] == 0.0
        assert result["daily_needed"] == 0

    async def test_past_month_caps_actuals_window_at_eom(
        self, db_session, test_tenant, forecasting
    ):
        # forecast_eom must cap the actuals window at min(today, eom): for a
        # fully elapsed past month, spend logged *after* that month ends must
        # not leak into mtd_actual, and days_elapsed must not exceed the
        # number of days in the month.
        month_start = date.today().replace(day=1) - timedelta(days=45)
        month_start = month_start.replace(day=1)
        eom = forecasting._get_end_of_month(month_start)
        days_in_month = (eom - month_start).days + 1

        # One row inside the target month, one after it ends (still <= today).
        in_month_day = month_start + timedelta(days=10)
        after_month_day = eom + timedelta(days=5)
        db_session.add(
            _kpi(
                test_tenant["id"],
                in_month_day,
                spend=50.0,
                platform=None,
                campaign_id="past-eom-cap",
            )
        )
        db_session.add(
            _kpi(
                test_tenant["id"],
                after_month_day,
                spend=999.0,
                platform=None,
                campaign_id="past-eom-cap",
            )
        )
        await db_session.flush()

        result = await forecasting.forecast_eom(
            TargetMetric.SPEND, campaign_id="past-eom-cap", month=month_start
        )

        assert result["status"] == "success"
        assert result["period"]["days_remaining"] == 0
        # Only the in-month row counts; the post-month row is excluded.
        assert result["mtd_actual"] == pytest.approx(50.0)
        # Window capped at eom, so days_elapsed equals the month length.
        assert result["period"]["days_elapsed"] == days_in_month


# =============================================================================
# _load_historical_data
# =============================================================================


class TestLoadHistoricalData:
    async def test_window_scope_and_ordering(
        self, db_session, test_tenant, forecasting, constant_meta_history
    ):
        # Rows outside the 60-day window and other scopes must be excluded.
        db_session.add(_kpi(test_tenant["id"], AS_OF - timedelta(days=90), spend=999.0))
        db_session.add(_kpi(test_tenant["id"], AS_OF, spend=999.0, campaign_id="other"))
        db_session.add(_kpi(test_tenant["id"], AS_OF, spend=999.0, platform="google"))
        await db_session.flush()

        hist = await forecasting._load_historical_data(
            TargetMetric.SPEND, "meta", None, AS_OF
        )

        assert len(hist) == 56
        assert all(h["value"] == pytest.approx(100.0) for h in hist)
        dates = [h["date"] for h in hist]
        assert dates == sorted(dates)
        assert hist[-1]["date"] == AS_OF
        assert hist[-1]["dow"] == AS_OF.weekday()

    async def test_tenant_level_scope_excludes_platform_rows(
        self, db_session, test_tenant, forecasting, constant_meta_history
    ):
        # platform=None loads only tenant-level rows; the 56 meta rows are
        # invisible at this scope.
        db_session.add(_kpi(test_tenant["id"], AS_OF, spend=77.0, platform=None))
        await db_session.flush()

        hist = await forecasting._load_historical_data(
            TargetMetric.SPEND, None, None, AS_OF
        )
        assert len(hist) == 1
        assert hist[0]["value"] == pytest.approx(77.0)


# =============================================================================
# Pure-helper edge branches (not covered by the unit suite)
# =============================================================================


class TestHelperEdgeCases:
    async def test_forecast_metric_default_as_of_date(self, forecasting):
        # No as_of_date -> today; no data -> insufficient envelope.
        result = await forecasting.forecast_metric(TargetMetric.SPEND)
        assert result["status"] == "insufficient_data"

    async def test_ewma_empty_history(self, forecasting):
        assert forecasting._calculate_ewma([]) == 0.0

    async def test_end_of_month_december_rollover(self, forecasting):
        assert forecasting._get_end_of_month(date(2026, 12, 5)) == date(2026, 12, 31)

    async def test_mtd_actual_platform_scope_skips_null_values(
        self, forecasting, constant_meta_history
    ):
        # platform="meta" branch of _get_mtd_actual; roas is None on every
        # seeded row so each record hits the null-skip branch.
        total = await forecasting._get_mtd_actual(
            TargetMetric.ROAS, "meta", None, AS_OF - timedelta(days=10), AS_OF
        )
        assert total == 0.0

    async def test_dow_factors_missing_days_default_to_one(self, forecasting):
        # Only Mondays (dow 0) present: every other dow falls back to 1.0.
        hist = [{"value": 50.0, "dow": 0}, {"value": 150.0, "dow": 0}]
        factors = forecasting._calculate_dow_factors(hist)
        assert factors[0] == pytest.approx(1.0)  # dow mean == overall mean
        assert all(factors[d] == 1.0 for d in range(1, 7))

    async def test_dow_factors_zero_mean(self, forecasting):
        hist = [{"value": 0.0, "dow": d} for d in range(7)]
        factors = forecasting._calculate_dow_factors(hist)
        assert all(f == 1.0 for f in factors.values())

    async def test_residual_std_short_history_default(self, forecasting):
        hist = [{"value": 10.0, "dow": 0}, {"value": 10.0, "dow": 1}]
        assert forecasting._calculate_residual_std(hist, 50.0, {}) == pytest.approx(
            10.0  # 20% of EWMA
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
    async def test_get_metric_value_branches(
        self, forecasting, test_tenant, metric, expected
    ):
        record = DailyKPI(
            tenant_id=test_tenant["id"],
            date=AS_OF,
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
            day_of_week=AS_OF.weekday(),
            is_weekend=False,
        )
        assert forecasting._get_metric_value(record, metric) == pytest.approx(expected)
        assert forecasting._get_metric_value(record, "bogus") is None


# =============================================================================
# save_forecast
# =============================================================================


class TestSaveForecast:
    async def test_persists_daily_rows(
        self, db_session, test_tenant, forecasting, constant_meta_history
    ):
        forecast = await forecasting.forecast_metric(
            TargetMetric.SPEND, forecast_days=5, platform="meta", as_of_date=AS_OF
        )
        assert forecast["status"] == "success"

        await forecasting.save_forecast(forecast, TargetMetric.SPEND, platform="meta")

        rows = (
            (
                await db_session.execute(
                    select(Forecast)
                    .where(Forecast.tenant_id == test_tenant["id"])
                    .order_by(Forecast.forecast_for_date)
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 5
        first = rows[0]
        assert first.forecast_date == date.today()
        assert first.forecast_for_date == AS_OF + timedelta(days=1)
        assert first.forecast_type == "daily"
        assert first.platform == "meta"
        assert first.metric_type == TargetMetric.SPEND
        assert first.forecasted_value == pytest.approx(100.0, rel=0.02)
        assert first.confidence_lower <= first.forecasted_value
        assert first.confidence_upper >= first.forecasted_value
        assert first.confidence_level == pytest.approx(0.9)
        assert first.model_type == "ewma_dow"
        assert first.model_params["type"] == "ewma_dow"

    async def test_empty_result_saves_nothing(
        self, db_session, test_tenant, forecasting
    ):
        await forecasting.save_forecast({}, TargetMetric.SPEND)

        count = (
            (
                await db_session.execute(
                    select(Forecast).where(Forecast.tenant_id == test_tenant["id"])
                )
            )
            .scalars()
            .all()
        )
        assert count == []
