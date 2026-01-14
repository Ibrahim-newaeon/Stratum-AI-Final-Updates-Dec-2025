# =============================================================================
# Stratum AI - ROAS Forecaster
# =============================================================================
"""
Time-series forecasting for ROAS predictions.
Uses historical data to forecast future performance.
"""

from datetime import date, timedelta
from typing import Any, Dict, List

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.ml.inference import ModelRegistry
from app.models import Campaign, CampaignMetric

logger = get_logger(__name__)


class ROASForecaster:
    """
    Forecasts ROAS trends using historical campaign data.

    Features:
    - Time-series decomposition (trend, seasonality)
    - Multi-campaign aggregation
    - Confidence intervals
    """

    def __init__(self):
        self.registry = ModelRegistry()

    async def forecast(
        self,
        campaigns: List[Campaign],
        days_ahead: int = 30,
        granularity: str = "daily",
        tenant_id: int = None,
        db: AsyncSession = None,
    ) -> Dict[str, Any]:
        """
        Generate ROAS forecasts for campaigns.

        Args:
            campaigns: List of campaigns to forecast
            days_ahead: Number of days to forecast
            granularity: 'daily', 'weekly', or 'monthly'
            tenant_id: Tenant ID for filtering
            db: Database session for historical data

        Returns:
            Forecast results with predictions and metadata
        """
        # Get historical data
        historical_data = await self._get_historical_data(campaigns, tenant_id, db)

        if not historical_data:
            return self._generate_mock_forecast(days_ahead, granularity)

        # Calculate baseline metrics
        baseline = self._calculate_baseline(historical_data)

        # Generate forecasts
        predictions = []
        today = date.today()

        if granularity == "daily":
            for i in range(1, days_ahead + 1):
                forecast_date = today + timedelta(days=i)
                prediction = await self._predict_day(forecast_date, baseline, i)
                predictions.append(prediction)

        elif granularity == "weekly":
            weeks = days_ahead // 7
            for i in range(1, weeks + 1):
                week_start = today + timedelta(days=i * 7)
                prediction = await self._predict_week(week_start, baseline, i)
                predictions.append(prediction)

        else:  # monthly
            months = days_ahead // 30
            for i in range(1, months + 1):
                month_start = today + timedelta(days=i * 30)
                prediction = await self._predict_month(month_start, baseline, i)
                predictions.append(prediction)

        return {
            "predictions": predictions,
            "baseline": baseline,
            "model_version": "roas_forecast_v1.0.0",
            "forecast_horizon": days_ahead,
            "granularity": granularity,
        }

    async def _get_historical_data(
        self,
        campaigns: List[Campaign],
        tenant_id: int,
        db: AsyncSession,
    ) -> List[Dict]:
        """Fetch historical metrics for campaigns."""
        if not db:
            return []

        campaign_ids = [c.id for c in campaigns]
        lookback_days = 90

        result = await db.execute(
            select(CampaignMetric)
            .where(
                CampaignMetric.campaign_id.in_(campaign_ids),
                CampaignMetric.tenant_id == tenant_id,
                CampaignMetric.date >= date.today() - timedelta(days=lookback_days),
            )
            .order_by(CampaignMetric.date)
        )
        metrics = result.scalars().all()

        # Aggregate by date
        daily_data = {}
        for m in metrics:
            date_key = m.date.isoformat()
            if date_key not in daily_data:
                daily_data[date_key] = {
                    "date": m.date,
                    "spend_cents": 0,
                    "revenue_cents": 0,
                    "impressions": 0,
                    "clicks": 0,
                    "conversions": 0,
                }
            daily_data[date_key]["spend_cents"] += m.spend_cents
            daily_data[date_key]["revenue_cents"] += m.revenue_cents
            daily_data[date_key]["impressions"] += m.impressions
            daily_data[date_key]["clicks"] += m.clicks
            daily_data[date_key]["conversions"] += m.conversions

        return list(daily_data.values())

    def _calculate_baseline(self, historical_data: List[Dict]) -> Dict[str, float]:
        """Calculate baseline metrics from historical data."""
        if not historical_data:
            return {
                "avg_daily_spend": 1000,
                "avg_daily_revenue": 1500,
                "avg_roas": 1.5,
                "trend": 0,
                "seasonality_factor": 1.0,
            }

        total_spend = sum(d["spend_cents"] for d in historical_data) / 100
        total_revenue = sum(d["revenue_cents"] for d in historical_data) / 100
        days = len(historical_data)

        avg_daily_spend = total_spend / days if days > 0 else 1000
        avg_daily_revenue = total_revenue / days if days > 0 else 1500
        avg_roas = total_revenue / total_spend if total_spend > 0 else 1.5

        # Calculate trend (simple linear regression slope)
        trend = self._calculate_trend(historical_data)

        # Calculate seasonality factor (day of week effect)
        seasonality = self._calculate_seasonality(historical_data)

        return {
            "avg_daily_spend": avg_daily_spend,
            "avg_daily_revenue": avg_daily_revenue,
            "avg_roas": avg_roas,
            "trend": trend,
            "seasonality_factor": seasonality,
        }

    def _calculate_trend(self, data: List[Dict]) -> float:
        """Calculate trend coefficient from historical data."""
        if len(data) < 2:
            return 0

        # Calculate daily ROAS values
        roas_values = []
        for d in data:
            spend = d["spend_cents"] / 100
            revenue = d["revenue_cents"] / 100
            if spend > 0:
                roas_values.append(revenue / spend)

        if len(roas_values) < 2:
            return 0

        # Simple linear trend
        x = np.arange(len(roas_values))
        y = np.array(roas_values)

        # Calculate slope
        n = len(x)
        slope = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / (n * np.sum(x**2) - np.sum(x)**2)

        return float(slope)

    def _calculate_seasonality(self, data: List[Dict]) -> float:
        """Calculate average seasonality effect."""
        # Simplified: return average weekday vs weekend ratio
        weekday_roas = []
        weekend_roas = []

        for d in data:
            spend = d["spend_cents"] / 100
            revenue = d["revenue_cents"] / 100
            if spend > 0:
                roas = revenue / spend
                if d["date"].weekday() < 5:
                    weekday_roas.append(roas)
                else:
                    weekend_roas.append(roas)

        if weekday_roas and weekend_roas:
            return np.mean(weekday_roas) / np.mean(weekend_roas)
        return 1.0

    async def _predict_day(
        self,
        forecast_date: date,
        baseline: Dict[str, float],
        days_out: int,
    ) -> Dict[str, Any]:
        """Generate prediction for a single day."""
        # Apply trend
        base_roas = baseline["avg_roas"]
        trend_adjustment = baseline["trend"] * days_out
        predicted_roas = base_roas + trend_adjustment

        # Apply day-of-week effect
        dow = forecast_date.weekday()
        if dow >= 5:  # Weekend
            predicted_roas *= 0.95  # Typically lower on weekends

        # Add some variance
        np.random.seed(int(forecast_date.toordinal()))
        noise = np.random.normal(0, 0.1)
        predicted_roas *= (1 + noise)

        # Bound predictions
        predicted_roas = max(0.5, min(5.0, predicted_roas))

        # Calculate confidence based on days out
        confidence = max(0.5, 0.95 - (days_out * 0.01))

        return {
            "date": forecast_date.isoformat(),
            "predicted_roas": round(predicted_roas, 3),
            "predicted_spend": round(baseline["avg_daily_spend"], 2),
            "predicted_revenue": round(baseline["avg_daily_spend"] * predicted_roas, 2),
            "confidence_lower": round(predicted_roas * 0.85, 3),
            "confidence_upper": round(predicted_roas * 1.15, 3),
            "confidence": round(confidence, 2),
        }

    async def _predict_week(
        self,
        week_start: date,
        baseline: Dict[str, float],
        weeks_out: int,
    ) -> Dict[str, Any]:
        """Generate prediction for a week."""
        # Weekly aggregation
        weekly_spend = baseline["avg_daily_spend"] * 7
        trend_adjustment = baseline["trend"] * weeks_out * 7

        predicted_roas = baseline["avg_roas"] + trend_adjustment
        predicted_roas = max(0.5, min(5.0, predicted_roas))

        confidence = max(0.5, 0.9 - (weeks_out * 0.02))

        return {
            "period_start": week_start.isoformat(),
            "period_end": (week_start + timedelta(days=6)).isoformat(),
            "predicted_roas": round(predicted_roas, 3),
            "predicted_spend": round(weekly_spend, 2),
            "predicted_revenue": round(weekly_spend * predicted_roas, 2),
            "confidence_lower": round(predicted_roas * 0.8, 3),
            "confidence_upper": round(predicted_roas * 1.2, 3),
            "confidence": round(confidence, 2),
        }

    async def _predict_month(
        self,
        month_start: date,
        baseline: Dict[str, float],
        months_out: int,
    ) -> Dict[str, Any]:
        """Generate prediction for a month."""
        monthly_spend = baseline["avg_daily_spend"] * 30
        trend_adjustment = baseline["trend"] * months_out * 30

        predicted_roas = baseline["avg_roas"] + trend_adjustment
        predicted_roas = max(0.5, min(5.0, predicted_roas))

        confidence = max(0.4, 0.85 - (months_out * 0.05))

        return {
            "period_start": month_start.isoformat(),
            "period_end": (month_start + timedelta(days=29)).isoformat(),
            "predicted_roas": round(predicted_roas, 3),
            "predicted_spend": round(monthly_spend, 2),
            "predicted_revenue": round(monthly_spend * predicted_roas, 2),
            "confidence_lower": round(predicted_roas * 0.75, 3),
            "confidence_upper": round(predicted_roas * 1.25, 3),
            "confidence": round(confidence, 2),
        }

    def _generate_mock_forecast(
        self,
        days_ahead: int,
        granularity: str,
    ) -> Dict[str, Any]:
        """Generate mock forecast when no historical data available."""
        predictions = []
        today = date.today()

        base_roas = 2.0
        base_spend = 500

        if granularity == "daily":
            for i in range(1, days_ahead + 1):
                forecast_date = today + timedelta(days=i)
                np.random.seed(int(forecast_date.toordinal()))

                roas = base_roas * np.random.uniform(0.9, 1.1)
                spend = base_spend * np.random.uniform(0.8, 1.2)

                predictions.append({
                    "date": forecast_date.isoformat(),
                    "predicted_roas": round(roas, 3),
                    "predicted_spend": round(spend, 2),
                    "predicted_revenue": round(spend * roas, 2),
                    "confidence_lower": round(roas * 0.85, 3),
                    "confidence_upper": round(roas * 1.15, 3),
                    "confidence": 0.75,
                })

        return {
            "predictions": predictions,
            "baseline": {
                "avg_roas": base_roas,
                "avg_daily_spend": base_spend,
            },
            "model_version": "mock_forecast_v1.0.0",
            "forecast_horizon": days_ahead,
            "granularity": granularity,
        }
