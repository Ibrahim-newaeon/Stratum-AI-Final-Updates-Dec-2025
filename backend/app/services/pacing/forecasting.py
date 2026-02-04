# =============================================================================
# Stratum AI - Forecasting Service
# =============================================================================
"""
Forecasting service using EWMA with day-of-week seasonality.

Features:
- Exponentially Weighted Moving Average (EWMA) for trend
- Day-of-week seasonality adjustment
- Confidence intervals based on residual variance
- Support for spend, revenue, ROAS, conversions forecasting
"""

import math
from datetime import UTC, date, datetime, timedelta
from typing import Any, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.pacing import (
    DailyKPI,
    Forecast,
    TargetMetric,
)

logger = get_logger(__name__)


class ForecastingService:
    """
    Forecasting service using EWMA with seasonality.

    Algorithm:
    1. Calculate EWMA trend from historical data
    2. Compute day-of-week factors from recent data
    3. Generate point forecast: EWMA * DoW_factor
    4. Calculate confidence intervals from residual variance
    """

    # Default parameters
    DEFAULT_EWMA_ALPHA = 0.3  # Higher = more weight on recent data
    DEFAULT_SEASONALITY_WINDOW = 28  # Days to calculate DoW factors
    DEFAULT_TREND_WINDOW = 14  # Days for trend calculation
    DEFAULT_CONFIDENCE_LEVEL = 0.9  # 90% confidence intervals

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: int,
        ewma_alpha: float = DEFAULT_EWMA_ALPHA,
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.ewma_alpha = ewma_alpha

    async def forecast_metric(
        self,
        metric: TargetMetric,
        forecast_days: int = 30,
        platform: Optional[str] = None,
        campaign_id: Optional[str] = None,
        as_of_date: Optional[date] = None,
    ) -> dict[str, Any]:
        """
        Generate forecast for a metric.

        Args:
            metric: Metric to forecast (spend, revenue, roas, etc.)
            forecast_days: Number of days to forecast
            platform: Optional platform filter
            campaign_id: Optional campaign filter
            as_of_date: Date to forecast from (default: today)

        Returns:
            Forecast results with daily predictions and confidence intervals
        """
        if as_of_date is None:
            as_of_date = datetime.now(UTC).date()

        # Load historical data
        historical = await self._load_historical_data(metric, platform, campaign_id, as_of_date)

        if len(historical) < 7:
            return {
                "status": "insufficient_data",
                "message": f"Need at least 7 days of data, have {len(historical)}",
                "metric": metric.value,
            }

        # Calculate EWMA trend
        ewma_value = self._calculate_ewma(historical)

        # Calculate day-of-week factors
        dow_factors = self._calculate_dow_factors(historical)

        # Calculate residual variance for confidence intervals
        residual_std = self._calculate_residual_std(historical, ewma_value, dow_factors)

        # Generate forecasts
        forecasts = []
        cumulative = 0.0

        for i in range(forecast_days):
            forecast_date = as_of_date + timedelta(days=i + 1)
            dow = forecast_date.weekday()

            # Point forecast
            point_forecast = ewma_value * dow_factors[dow]

            # Confidence intervals (widen with forecast horizon)
            horizon_factor = math.sqrt(1 + i * 0.1)  # Uncertainty grows with horizon
            ci_width = 1.645 * residual_std * horizon_factor  # 90% CI

            lower = max(0, point_forecast - ci_width)
            upper = point_forecast + ci_width

            cumulative += point_forecast

            forecasts.append(
                {
                    "date": forecast_date.isoformat(),
                    "day_of_week": dow,
                    "point_forecast": round(point_forecast, 2),
                    "lower_bound": round(lower, 2),
                    "upper_bound": round(upper, 2),
                    "cumulative": round(cumulative, 2),
                }
            )

        # Calculate EOM projection if within current month
        eom_date = self._get_end_of_month(as_of_date)
        days_to_eom = (eom_date - as_of_date).days

        eom_projection = None
        if days_to_eom <= forecast_days:
            eom_projection = {
                "date": eom_date.isoformat(),
                "projected": round(sum(f["point_forecast"] for f in forecasts[:days_to_eom]), 2),
                "lower": round(sum(f["lower_bound"] for f in forecasts[:days_to_eom]), 2),
                "upper": round(sum(f["upper_bound"] for f in forecasts[:days_to_eom]), 2),
            }

        return {
            "status": "success",
            "metric": metric.value,
            "as_of_date": as_of_date.isoformat(),
            "platform": platform,
            "campaign_id": campaign_id,
            "model": {
                "type": "ewma_dow",
                "ewma_alpha": self.ewma_alpha,
                "ewma_value": round(ewma_value, 2),
                "dow_factors": {str(k): round(v, 3) for k, v in dow_factors.items()},
                "residual_std": round(residual_std, 2),
            },
            "historical_days": len(historical),
            "forecast_days": forecast_days,
            "daily_forecasts": forecasts,
            "eom_projection": eom_projection,
        }

    async def forecast_eom(
        self,
        metric: TargetMetric,
        platform: Optional[str] = None,
        campaign_id: Optional[str] = None,
        month: Optional[date] = None,
    ) -> dict[str, Any]:
        """
        Forecast end-of-month value for a metric.

        Args:
            metric: Metric to forecast
            platform: Optional platform filter
            campaign_id: Optional campaign filter
            month: Month to forecast (default: current month)

        Returns:
            EOM forecast with MTD actual and projections
        """
        today = datetime.now(UTC).date()
        month = today.replace(day=1) if month is None else month.replace(day=1)

        # Get MTD actual
        eom = self._get_end_of_month(month)
        mtd_actual = await self._get_mtd_actual(metric, platform, campaign_id, month, today)

        # Calculate days
        days_elapsed = (today - month).days + 1
        days_in_month = (eom - month).days + 1
        days_remaining = max(0, (eom - today).days)

        # Get forecast for remaining days
        if days_remaining > 0:
            forecast_result = await self.forecast_metric(
                metric, days_remaining, platform, campaign_id, today
            )

            if forecast_result["status"] == "success":
                remaining_forecast = sum(
                    f["point_forecast"] for f in forecast_result["daily_forecasts"]
                )
                remaining_lower = sum(f["lower_bound"] for f in forecast_result["daily_forecasts"])
                remaining_upper = sum(f["upper_bound"] for f in forecast_result["daily_forecasts"])
            else:
                # Fallback: linear projection
                daily_avg = mtd_actual / days_elapsed if days_elapsed > 0 else 0
                remaining_forecast = daily_avg * days_remaining
                remaining_lower = remaining_forecast * 0.8
                remaining_upper = remaining_forecast * 1.2
        else:
            remaining_forecast = 0
            remaining_lower = 0
            remaining_upper = 0

        projected_eom = mtd_actual + remaining_forecast

        return {
            "status": "success",
            "metric": metric.value,
            "month": month.isoformat(),
            "platform": platform,
            "campaign_id": campaign_id,
            "period": {
                "start": month.isoformat(),
                "end": eom.isoformat(),
                "days_elapsed": days_elapsed,
                "days_remaining": days_remaining,
                "days_total": days_in_month,
            },
            "mtd_actual": round(mtd_actual, 2),
            "remaining_forecast": round(remaining_forecast, 2),
            "projected_eom": round(projected_eom, 2),
            "projected_lower": round(mtd_actual + remaining_lower, 2),
            "projected_upper": round(mtd_actual + remaining_upper, 2),
            "daily_average": round(mtd_actual / days_elapsed, 2) if days_elapsed > 0 else 0,
            "daily_needed": round((projected_eom - mtd_actual) / days_remaining, 2)
            if days_remaining > 0
            else 0,
        }

    async def _load_historical_data(
        self,
        metric: TargetMetric,
        platform: Optional[str],
        campaign_id: Optional[str],
        as_of_date: date,
        days: int = 60,
    ) -> list[dict[str, Any]]:
        """Load historical daily data for forecasting."""
        start_date = as_of_date - timedelta(days=days)

        # Build conditions
        conditions = [
            DailyKPI.tenant_id == self.tenant_id,
            DailyKPI.date >= start_date,
            DailyKPI.date <= as_of_date,
        ]

        if platform:
            conditions.append(DailyKPI.platform == platform)
        else:
            conditions.append(DailyKPI.platform.is_(None))  # Account-level

        if campaign_id:
            conditions.append(DailyKPI.campaign_id == campaign_id)
        else:
            conditions.append(DailyKPI.campaign_id.is_(None))  # All campaigns

        result = await self.db.execute(
            select(DailyKPI).where(and_(*conditions)).order_by(DailyKPI.date)
        )
        records = result.scalars().all()

        # Extract metric values
        historical = []
        for r in records:
            value = self._get_metric_value(r, metric)
            if value is not None:
                historical.append(
                    {
                        "date": r.date,
                        "value": value,
                        "dow": r.day_of_week,
                    }
                )

        return historical

    def _get_metric_value(self, record: DailyKPI, metric: TargetMetric) -> Optional[float]:
        """Extract metric value from DailyKPI record."""
        if metric == TargetMetric.SPEND:
            return (record.spend_cents or 0) / 100
        elif metric == TargetMetric.REVENUE:
            return (record.revenue_cents or 0) / 100
        elif metric == TargetMetric.ROAS:
            return record.roas
        elif metric == TargetMetric.CONVERSIONS:
            return record.conversions
        elif metric == TargetMetric.LEADS:
            return record.leads + record.crm_leads
        elif metric == TargetMetric.PIPELINE_VALUE:
            return (record.crm_pipeline_cents or 0) / 100
        elif metric == TargetMetric.WON_REVENUE:
            return (record.crm_won_revenue_cents or 0) / 100
        elif metric == TargetMetric.CPA:
            return (record.cpa_cents or 0) / 100
        elif metric == TargetMetric.CPL:
            return (record.cpl_cents or 0) / 100
        return None

    def _calculate_ewma(self, historical: list[dict[str, Any]]) -> float:
        """Calculate EWMA from historical data."""
        if not historical:
            return 0.0

        ewma = historical[0]["value"]
        for record in historical[1:]:
            ewma = self.ewma_alpha * record["value"] + (1 - self.ewma_alpha) * ewma

        return ewma

    def _calculate_dow_factors(self, historical: list[dict[str, Any]]) -> dict[int, float]:
        """Calculate day-of-week seasonality factors."""
        # Group by day of week
        dow_sums = {i: [] for i in range(7)}
        for record in historical[-self.DEFAULT_SEASONALITY_WINDOW :]:
            dow_sums[record["dow"]].append(record["value"])

        # Calculate average for each day
        overall_mean = sum(r["value"] for r in historical) / len(historical) if historical else 1

        factors = {}
        for dow in range(7):
            if dow_sums[dow]:
                dow_mean = sum(dow_sums[dow]) / len(dow_sums[dow])
                factors[dow] = dow_mean / overall_mean if overall_mean > 0 else 1.0
            else:
                factors[dow] = 1.0

        return factors

    def _calculate_residual_std(
        self,
        historical: list[dict[str, Any]],
        ewma: float,
        dow_factors: dict[int, float],
    ) -> float:
        """Calculate standard deviation of residuals for confidence intervals."""
        if len(historical) < 3:
            return ewma * 0.2  # Default to 20% of EWMA

        residuals = []
        for record in historical[-self.DEFAULT_TREND_WINDOW :]:
            expected = ewma * dow_factors.get(record["dow"], 1.0)
            residual = record["value"] - expected
            residuals.append(residual**2)

        variance = sum(residuals) / len(residuals)
        return math.sqrt(variance)

    async def _get_mtd_actual(
        self,
        metric: TargetMetric,
        platform: Optional[str],
        campaign_id: Optional[str],
        month_start: date,
        as_of_date: date,
    ) -> float:
        """Get month-to-date actual for a metric."""
        conditions = [
            DailyKPI.tenant_id == self.tenant_id,
            DailyKPI.date >= month_start,
            DailyKPI.date <= as_of_date,
        ]

        if platform:
            conditions.append(DailyKPI.platform == platform)
        else:
            conditions.append(DailyKPI.platform.is_(None))

        if campaign_id:
            conditions.append(DailyKPI.campaign_id == campaign_id)
        else:
            conditions.append(DailyKPI.campaign_id.is_(None))

        result = await self.db.execute(select(DailyKPI).where(and_(*conditions)))
        records = result.scalars().all()

        total = 0.0
        for r in records:
            value = self._get_metric_value(r, metric)
            if value is not None:
                total += value

        return total

    def _get_end_of_month(self, d: date) -> date:
        """Get the last day of the month for a given date."""
        if d.month == 12:
            return date(d.year + 1, 1, 1) - timedelta(days=1)
        return date(d.year, d.month + 1, 1) - timedelta(days=1)

    async def save_forecast(
        self,
        forecast_result: dict[str, Any],
        metric: TargetMetric,
        platform: Optional[str] = None,
        campaign_id: Optional[str] = None,
    ) -> None:
        """Save forecast to database for tracking accuracy."""
        today = datetime.now(UTC).date()

        for daily in forecast_result.get("daily_forecasts", []):
            forecast_date = date.fromisoformat(daily["date"])

            forecast = Forecast(
                tenant_id=self.tenant_id,
                forecast_date=today,
                forecast_for_date=forecast_date,
                forecast_type="daily",
                platform=platform,
                campaign_id=campaign_id,
                metric_type=metric,
                forecasted_value=daily["point_forecast"],
                confidence_lower=daily["lower_bound"],
                confidence_upper=daily["upper_bound"],
                confidence_level=self.DEFAULT_CONFIDENCE_LEVEL,
                model_type="ewma_dow",
                model_params=forecast_result.get("model"),
            )
            self.db.add(forecast)

        await self.db.commit()
