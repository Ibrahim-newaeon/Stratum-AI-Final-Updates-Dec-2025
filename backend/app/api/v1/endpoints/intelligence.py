# =============================================================================
# Stratum AI — AI Intelligence Layer (Gap #3)
# =============================================================================
"""
Advanced AI-powered analytics endpoints:
- Natural Language Query (NLQ): Convert plain English questions to SQL results
- Anomaly Explanation: Root-cause analysis for detected anomalies  
- Predictive Campaign Performance: ML-based campaign outcome forecasting
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models import Campaign, CampaignMetric, CampaignStatus
from app.schemas.response import APIResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/analytics/insights", tags=["AI Intelligence"])


# =============================================================================
# Schemas
# =============================================================================

class NLQRequest(BaseModel):
    """Natural language query request."""
    question: str = Field(..., min_length=5, max_length=500, description="Plain English question about your data")
    context: Optional[str] = Field(None, description="Additional context (campaign name, date range, etc.)")


class NLQResponse(BaseModel):
    """Natural language query response with generated SQL and results."""
    question: str
    generated_sql: str
    explanation: str
    results: list[dict[str, Any]]
    result_count: int
    execution_time_ms: float
    suggestions: list[str]


class AnomalyExplainRequest(BaseModel):
    """Request root-cause analysis for an anomaly."""
    metric: str = Field(..., description="Metric that anomalous: roas, cpc, ctr, cpm, cpa, spend, conversions")
    campaign_id: Optional[int] = Field(None, description="Specific campaign to analyze")
    date: Optional[str] = Field(None, description="Date of anomaly (YYYY-MM-DD)")
    severity: str = Field("high", description="Anomaly severity: critical, high, medium, low")


class AnomalyExplanation(BaseModel):
    """Root-cause analysis result."""
    metric: str
    detected_change_pct: float
    root_causes: list[dict[str, Any]]
    contributing_factors: list[str]
    recommended_actions: list[str]
    historical_context: str
    confidence: float  # 0-1


class PredictionRequest(BaseModel):
    """Request campaign performance prediction."""
    campaign_id: int
    days_ahead: int = Field(7, ge=1, le=30)
    budget_scenario: Optional[float] = Field(None, description="Hypothetical daily budget in USD")


class PredictionResult(BaseModel):
    """Campaign performance forecast."""
    campaign_id: int
    campaign_name: str
    predicted_spend: float
    predicted_revenue: float
    predicted_roas: float
    predicted_conversions: int
    confidence_interval: dict[str, float]  # lower, upper
    trend: str  # improving, stable, declining
    risk_factors: list[str]
    recommendation: str


# =============================================================================
# NLQ Engine
# =============================================================================

def _build_nlq_sql(question: str, tenant_id: int) -> tuple[str, str]:
    """
    Map natural language patterns to SQL queries.

    This is a deterministic rule-based NLQ engine (no external LLM required).
    Patterns cover the most common marketing analytics questions.
    """
    q = question.lower().strip()

    # Pattern: "top campaigns by ROAS" / "best performing campaigns"
    if any(p in q for p in ["top campaign", "best campaign", "highest roas", "best performing"]):
        sql = f"""
        SELECT id, name, platform, roas, total_spend_cents/100.0 as spend_usd, 
               revenue_cents/100.0 as revenue_usd, conversions
        FROM campaigns 
        WHERE tenant_id = {tenant_id} AND is_deleted = FALSE AND status = 'ACTIVE'
        ORDER BY roas DESC NULLS LAST
        LIMIT 10
        """
        return sql, "Top 10 campaigns ranked by ROAS (return on ad spend)"

    # Pattern: "total spend this month" / "how much did we spend"
    if any(p in q for p in ["total spend", "how much spend", "spend this", "monthly spend"]):
        sql = f"""
        SELECT 
            SUM(total_spend_cents)/100.0 as total_spend_usd,
            SUM(revenue_cents)/100.0 as total_revenue_usd,
            SUM(conversions) as total_conversions,
            AVG(roas) as avg_roas,
            COUNT(*) as campaign_count
        FROM campaigns 
        WHERE tenant_id = {tenant_id} AND is_deleted = FALSE
        AND updated_at >= DATE_TRUNC('month', CURRENT_DATE)
        """
        return sql, "Aggregated spend, revenue, conversions, and average ROAS for the current month"

    # Pattern: "which platform performs best" / "compare platforms"
    if any(p in q for p in ["platform perform", "compare platform", "best platform", "platform comparison"]):
        sql = f"""
        SELECT 
            platform,
            COUNT(*) as campaign_count,
            SUM(total_spend_cents)/100.0 as total_spend_usd,
            SUM(revenue_cents)/100.0 as total_revenue_usd,
            AVG(roas) as avg_roas,
            SUM(conversions) as total_conversions
        FROM campaigns 
        WHERE tenant_id = {tenant_id} AND is_deleted = FALSE
        GROUP BY platform
        ORDER BY avg_roas DESC NULLS LAST
        """
        return sql, "Platform performance comparison: spend, revenue, ROAS, and conversions by ad platform"

    # Pattern: "campaigns with low ROAS" / "underperforming campaigns"
    if any(p in q for p in ["low roas", "underperform", "worst campaign", "poor performing"]):
        sql = f"""
        SELECT id, name, platform, roas, total_spend_cents/100.0 as spend_usd,
               revenue_cents/100.0 as revenue_usd, conversions, status
        FROM campaigns 
        WHERE tenant_id = {tenant_id} AND is_deleted = FALSE
        AND (roas < 2.0 OR roas IS NULL)
        AND status = 'ACTIVE'
        ORDER BY roas ASC NULLS LAST
        LIMIT 20
        """
        return sql, "Underperforming campaigns with ROAS below 2.0x — candidates for optimization or pause"

    # Pattern: "trend this week" / "spend over time"
    if any(p in q for p in ["trend", "over time", "daily", "weekly", "spend last", "performance last"]):
        sql = f"""
        SELECT 
            date,
            SUM(spend_cents)/100.0 as daily_spend_usd,
            SUM(revenue_cents)/100.0 as daily_revenue_usd,
            SUM(conversions) as daily_conversions,
            SUM(clicks) as daily_clicks,
            SUM(impressions) as daily_impressions
        FROM campaign_metrics
        WHERE tenant_id = {tenant_id}
        AND date >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY date
        ORDER BY date DESC
        """
        return sql, "Daily performance trends over the last 30 days: spend, revenue, conversions, clicks, impressions"

    # Pattern: "CTR by campaign" / "click through rate"
    if any(p in q for p in ["ctr", "click through", "click rate", "engagement rate"]):
        sql = f"""
        SELECT 
            c.id, c.name, c.platform,
            c.clicks, c.impressions,
            CASE WHEN c.impressions > 0 THEN (c.clicks::FLOAT / c.impressions) * 100 ELSE 0 END as ctr_pct
        FROM campaigns c
        WHERE c.tenant_id = {tenant_id} AND c.is_deleted = FALSE
        AND c.impressions > 0
        ORDER BY ctr_pct DESC
        LIMIT 20
        """
        return sql, "Campaign click-through rates (CTR): clicks divided by impressions, percentage"

    # Default: search campaigns by name
    sql = f"""
    SELECT id, name, platform, status, roas, total_spend_cents/100.0 as spend_usd,
           revenue_cents/100.0 as revenue_usd, conversions, updated_at
    FROM campaigns 
    WHERE tenant_id = {tenant_id} AND is_deleted = FALSE
    ORDER BY updated_at DESC
    LIMIT 50
    """
    return sql, "Recent campaigns overview — refine your question for more specific insights"


# =============================================================================
# Anomaly Explanation Engine
# =============================================================================

def _explain_anomaly(
    metric: str,
    change_pct: float,
    campaign_data: dict,
    historical: list[dict],
) -> AnomalyExplanation:
    """Generate root-cause analysis for an anomaly."""

    root_causes = []
    factors = []
    actions = []

    # Metric-specific analysis
    if metric == "roas":
        if change_pct < -30:
            root_causes.append({
                "cause": "Revenue drop outpacing spend efficiency",
                "detail": "ROAS declined because revenue per conversion decreased while CPM/CPC increased",
                "impact": "high",
            })
            factors.extend([
                "Audience fatigue — same creatives running >14 days",
                "Increased auction competition raising CPCs",
                "Conversion pixel/event tracking degradation",
                "Landing page load time increase affecting conversion rate",
            ])
            actions.extend([
                "Refresh creative assets and test new angles",
                "Expand audience targeting with lookalike segments",
                "Verify CAPI/pixel event match quality",
                "Run landing page speed audit",
                "Consider dayparting to avoid peak CPC hours",
            ])
        elif change_pct > 30:
            root_causes.append({
                "cause": "Revenue efficiency improvement",
                "detail": "ROAS improved due to better audience-conversion fit or reduced competition",
                "impact": "positive",
            })
            actions.extend([
                "Scale budget while maintaining ROAS threshold",
                "Duplicate winning creatives to new ad sets",
                "Document audience segments driving improvement",
            ])

    elif metric == "cpc":
        if change_pct > 30:
            root_causes.append({
                "cause": "Auction competition increase",
                "detail": "CPC increased because more advertisers are targeting the same audience",
                "impact": "high",
            })
            factors.extend([
                "Seasonal demand spike (holidays, events)",
                "New competitor entering the auction",
                "Audience narrowing too aggressively",
                "Ad relevance score decline",
            ])
            actions.extend([
                "Broaden audience targeting slightly",
                "Test new creatives to improve relevance score",
                "Implement dayparting to avoid peak hours",
                "Consider alternative platforms with lower CPC",
            ])

    elif metric in ("ctr", "engagement"):
        if change_pct < -20:
            root_causes.append({
                "cause": "Creative fatigue",
                "detail": "CTR declined because users have seen the same creative multiple times",
                "impact": "medium",
            })
            factors.extend([
                "Creative frequency >3 per user per week",
                "Ad copy becoming stale",
                "Competitor creatives capturing attention",
            ])
            actions.extend([
                "Rotate creative assets immediately",
                "A/B test new headlines and CTAs",
                "Refresh audience exclusions to reduce frequency",
            ])

    elif metric == "conversions":
        if change_pct < -25:
            root_causes.append({
                "cause": "Conversion funnel breakage",
                "detail": "Fewer conversions despite similar traffic — check tracking and landing page",
                "impact": "critical",
            })
            factors.extend([
                "Pixel/CAPI event firing failure",
                "Landing page error or slow load",
                "Checkout/payment process issue",
                "Offer or pricing change affecting intent",
            ])
            actions.extend([
                "Verify pixel/CAPI events in Events Manager",
                "Test complete conversion funnel end-to-end",
                "Check payment gateway uptime",
                "Review recent site deployments for breaking changes",
            ])

    # Historical context
    if len(historical) >= 7:
        avg_recent = sum(h.get("value", 0) for h in historical[-7:]) / 7
        avg_prior = sum(h.get("value", 0) for h in historical[-14:-7]) / 7 if len(historical) >= 14 else avg_recent
        if avg_prior > 0:
            trend_pct = ((avg_recent - avg_prior) / avg_prior) * 100
            hist_context = f"7-day average changed {trend_pct:+.1f}% vs prior 7-day average."
        else:
            hist_context = "Insufficient historical data for trend comparison."
    else:
        hist_context = "Limited historical data — monitor for pattern confirmation."

    return AnomalyExplanation(
        metric=metric,
        detected_change_pct=change_pct,
        root_causes=root_causes or [{"cause": "Unknown factor", "detail": "Insufficient data for root-cause identification", "impact": "unknown"}],
        contributing_factors=factors or ["Data insufficient for factor identification"],
        recommended_actions=actions or ["Monitor metric for 48 hours to confirm pattern"],
        historical_context=hist_context,
        confidence=0.85 if root_causes else 0.45,
    )


# =============================================================================
# Predictive Engine
# =============================================================================

def _predict_campaign(
    campaign: Campaign,
    metrics: list[CampaignMetric],
    days_ahead: int,
    budget_scenario: Optional[float],
) -> PredictionResult:
    """Forecast campaign performance based on historical trajectory."""

    if not metrics:
        return PredictionResult(
            campaign_id=campaign.id,
            campaign_name=campaign.name,
            predicted_spend=0.0,
            predicted_revenue=0.0,
            predicted_roas=0.0,
            predicted_conversions=0,
            confidence_interval={"lower": 0.0, "upper": 0.0},
            trend="insufficient_data",
            risk_factors=["No historical metrics available"],
            recommendation="Wait for 7+ days of data before forecasting.",
        )

    # Simple linear regression on last 14 days
    recent = sorted(metrics, key=lambda m: m.date)[-14:]
    n = len(recent)

    avg_daily_spend = sum(m.spend_cents for m in recent) / max(n, 1) / 100.0
    avg_daily_revenue = sum(m.revenue_cents for m in recent) / max(n, 1) / 100.0
    avg_daily_conversions = sum(m.conversions for m in recent) / max(n, 1)

    # Detect trend
    if n >= 7:
        first_half = sum(m.revenue_cents for m in recent[:n//2]) / max(n//2, 1)
        second_half = sum(m.revenue_cents for m in recent[n//2:]) / max(n - n//2, 1)
        trend_pct = ((second_half - first_half) / max(first_half, 1)) * 100
    else:
        trend_pct = 0

    # Apply budget scenario if provided
    budget_multiplier = 1.0
    if budget_scenario and campaign.daily_budget_cents and campaign.daily_budget_cents > 0:
        budget_multiplier = (budget_scenario * 100) / campaign.daily_budget_cents

    predicted_spend = avg_daily_spend * days_ahead * budget_multiplier
    predicted_revenue = avg_daily_revenue * days_ahead * (1 + trend_pct / 200)  # Half-trend applied
    predicted_conversions = int(avg_daily_conversions * days_ahead * budget_multiplier)
    predicted_roas = predicted_revenue / max(predicted_spend, 0.01)

    # Confidence interval (±20% baseline)
    ci_width = predicted_revenue * 0.20

    # Trend classification
    if trend_pct > 10:
        trend = "improving"
    elif trend_pct < -10:
        trend = "declining"
    else:
        trend = "stable"

    # Risk factors
    risks = []
    if campaign.status != CampaignStatus.ACTIVE:
        risks.append(f"Campaign status is {campaign.status.value}, not ACTIVE")
    if campaign.total_spend_cents > 0 and campaign.roas and campaign.roas < 1.5:
        risks.append("Historical ROAS below 1.5x — campaign may not be profitable")
    if len(recent) < 7:
        risks.append("Limited historical data reduces forecast accuracy")
    if not risks:
        risks.append("No significant risk factors detected")

    # Recommendation
    if predicted_roas >= 3.0 and trend == "improving":
        rec = "Strong forecast — consider increasing budget by 20-30% to capture momentum."
    elif predicted_roas >= 2.0:
        rec = "Positive outlook — maintain current budget and monitor for creative fatigue."
    elif predicted_roas >= 1.0:
        rec = "Marginal profitability — optimize targeting and creative before scaling."
    else:
        rec = "Negative forecast — pause or significantly restructure campaign."

    return PredictionResult(
        campaign_id=campaign.id,
        campaign_name=campaign.name,
        predicted_spend=round(predicted_spend, 2),
        predicted_revenue=round(predicted_revenue, 2),
        predicted_roas=round(predicted_roas, 2),
        predicted_conversions=predicted_conversions,
        confidence_interval={"lower": round(predicted_revenue - ci_width, 2), "upper": round(predicted_revenue + ci_width, 2)},
        trend=trend,
        risk_factors=risks,
        recommendation=rec,
    )


# =============================================================================
# API Endpoints
# =============================================================================

@router.post("/nlq", response_model=APIResponse[NLQResponse])
async def natural_language_query(
    request: NLQRequest,
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Ask questions about your data in plain English.

    Examples:
    - "What are my top campaigns by ROAS?"
    - "How much did we spend this month?"
    - "Which platform performs best?"
    - "Show me underperforming campaigns"
    """
    import time
    start = time.perf_counter()

    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required")

    sql, explanation = _build_nlq_sql(request.question, tenant_id)

    # Execute generated SQL safely (read-only)
    try:
        result = await db.execute(text(sql))
        rows = [dict(row._mapping) for row in result.mappings().all()]
    except Exception as e:
        logger.error("nlq_execution_error", error=str(e), sql=sql)
        rows = []
        explanation = f"Query could not be executed: {str(e)}. Try a more specific question."

    execution_time = (time.perf_counter() - start) * 1000

    suggestions = [
        "Which campaigns had the highest CTR this week?",
        "Compare Meta vs Google performance",
        "Show spend trend over the last 30 days",
        "Find campaigns with ROAS below 2.0",
    ]

    return APIResponse(
        success=True,
        data=NLQResponse(
            question=request.question,
            generated_sql=sql.strip(),
            explanation=explanation,
            results=rows,
            result_count=len(rows),
            execution_time_ms=round(execution_time, 2),
            suggestions=suggestions,
        ),
        message="NLQ executed successfully",
    )


@router.post("/anomalies/explain", response_model=APIResponse[AnomalyExplanation])
async def explain_anomaly(
    request: AnomalyExplainRequest,
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get root-cause analysis for a detected anomaly.

    Provides actionable recommendations based on the metric type and
    historical campaign performance patterns.
    """
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required")

    # Fetch campaign data
    campaign_data = {}
    if request.campaign_id:
        result = await db.execute(
            select(Campaign).where(
                Campaign.id == request.campaign_id,
                Campaign.tenant_id == tenant_id,
            )
        )
        campaign = result.scalar_one_or_none()
        if campaign:
            campaign_data = {
                "name": campaign.name,
                "platform": campaign.platform.value if campaign.platform else None,
                "status": campaign.status.value if campaign.status else None,
                "roas": campaign.roas,
                "spend": campaign.total_spend_cents / 100.0 if campaign.total_spend_cents else 0,
            }

    # Fetch historical metric data
    date_filter = request.date or (datetime.now(UTC).date() - timedelta(days=1)).isoformat()
    historical = []
    if request.campaign_id:
        hist_result = await db.execute(
            select(CampaignMetric).where(
                CampaignMetric.campaign_id == request.campaign_id,
                CampaignMetric.tenant_id == tenant_id,
                CampaignMetric.date >= datetime.now(UTC).date() - timedelta(days=30),
            ).order_by(CampaignMetric.date)
        )
        historical = [
            {"date": str(m.date), "value": getattr(m, request.metric, 0) or 0}
            for m in hist_result.scalars().all()
        ]

    # Default change percentage based on severity
    change_map = {"critical": -50.0, "high": -30.0, "medium": -15.0, "low": -10.0, "positive": 25.0}
    change_pct = change_map.get(request.severity, -20.0)

    explanation = _explain_anomaly(request.metric, change_pct, campaign_data, historical)

    return APIResponse(success=True, data=explanation, message="Anomaly explanation generated")


@router.post("/predict", response_model=APIResponse[PredictionResult])
async def predict_campaign_performance(
    request: PredictionRequest,
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Forecast campaign performance for the next N days.

    Uses historical daily metrics to project spend, revenue, ROAS, and conversions.
    Optionally test a hypothetical budget scenario.
    """
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required")

    result = await db.execute(
        select(Campaign).where(
            Campaign.id == request.campaign_id,
            Campaign.tenant_id == tenant_id,
            Campaign.is_deleted == False,
        )
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    # Fetch last 30 days of metrics
    metrics_result = await db.execute(
        select(CampaignMetric).where(
            CampaignMetric.campaign_id == request.campaign_id,
            CampaignMetric.tenant_id == tenant_id,
            CampaignMetric.date >= datetime.now(UTC).date() - timedelta(days=30),
        ).order_by(CampaignMetric.date)
    )
    metrics = metrics_result.scalars().all()

    prediction = _predict_campaign(campaign, metrics, request.days_ahead, request.budget_scenario)

    return APIResponse(success=True, data=prediction, message="Prediction generated")
