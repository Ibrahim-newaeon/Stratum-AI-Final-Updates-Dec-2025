# =============================================================================
# Stratum AI - Insights & Recommendations API Router
# =============================================================================
"""
API endpoints for Intelligence Layer features:
- Insights (aggregated daily view)
- Recommendations (actionable suggestions)
- Anomaly alerts
"""

from datetime import date, timedelta
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.session import get_async_session
from app.features.service import can_access_feature, get_tenant_features
from app.quality.trust_layer_service import SignalHealthService
from app.analytics.logic.recommend import RecommendationsEngine, generate_recommendations
from app.analytics.logic.types import EntityMetrics, BaselineMetrics
from app.schemas.response import APIResponse


router = APIRouter(prefix="/tenant/{tenant_id}", tags=["insights"])


# =============================================================================
# Helper Functions
# =============================================================================

async def get_entity_metrics(db: AsyncSession, tenant_id: int, target_date: date) -> List[EntityMetrics]:
    """
    Fetch entity metrics for recommendations.
    In production, this queries fact_daily_metrics.
    """
    # Placeholder - in production query actual metrics
    return []


async def get_baseline_metrics(db: AsyncSession, tenant_id: int) -> Dict[str, BaselineMetrics]:
    """
    Fetch baseline metrics for entities.
    In production, this queries aggregated historical data.
    """
    # Placeholder - in production query actual baselines
    return {}


async def check_signal_health_for_autopilot(db: AsyncSession, tenant_id: int, target_date: date) -> Dict[str, Any]:
    """Check if autopilot should be blocked due to signal health."""
    service = SignalHealthService(db)
    health_data = await service.get_signal_health(tenant_id, target_date)

    status = health_data.get("status", "unknown")
    blocked = status in ["degraded", "critical"]
    reason = None

    if blocked:
        reason = f"Signal health is {status}. Automation blocked for data quality protection."

    return {
        "blocked": blocked,
        "reason": reason,
        "status": status,
    }


# =============================================================================
# Insights Endpoint
# =============================================================================

@router.get("/insights", response_model=APIResponse[Dict[str, Any]])
async def get_insights(
    request: Request,
    tenant_id: int,
    target_date: Optional[date] = Query(default=None, alias="date"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get daily insights for a tenant.

    Returns aggregated view of:
    - KPIs and trends
    - Top actions/recommendations
    - Risks and opportunities
    - Autopilot status

    Requires feature flag: ai_recommendations
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    if not await can_access_feature(db, tenant_id, "ai_recommendations"):
        raise HTTPException(
            status_code=403,
            detail="AI recommendations feature is not enabled for this tenant"
        )

    if target_date is None:
        target_date = date.today()

    # Get tenant features for autopilot level
    features = await get_tenant_features(db, tenant_id)
    autopilot_level = features.get("autopilot_level", 0)

    # Check signal health for autopilot blocking
    autopilot_status = await check_signal_health_for_autopilot(db, tenant_id, target_date)

    # Get metrics (placeholder data for now)
    entities_today = await get_entity_metrics(db, tenant_id, target_date)
    baselines = await get_baseline_metrics(db, tenant_id)

    # Generate recommendations if we have data
    if entities_today and baselines:
        engine = RecommendationsEngine()
        recommendations_data = engine.generate_recommendations(
            entities_today=entities_today,
            baselines=baselines,
        )
    else:
        # Return placeholder insights when no data
        recommendations_data = {
            "recommendations": [],
            "actions": [],
            "alerts": [],
            "insights": [],
            "health": {"status": "no_data"},
            "scaling_summary": {
                "scale_candidates": 0,
                "fix_candidates": 0,
                "watch_candidates": 0,
            },
            "generated_at": None,
            "automation_blocked": autopilot_status["blocked"],
        }

    # Build insights response
    response = {
        "date": target_date.isoformat(),
        "kpis": {
            "total_spend": 0,
            "total_revenue": 0,
            "roas": 0,
            "cpa": 0,
            "trend_vs_yesterday": 0,
            "trend_vs_last_week": 0,
        },
        "actions": recommendations_data.get("recommendations", [])[:5],  # Top 5 actions
        "risks": [
            alert for alert in recommendations_data.get("alerts", [])
            if alert.get("severity") in ["high", "critical"]
        ],
        "opportunities": recommendations_data.get("insights", [])[:3],  # Top 3 opportunities
        "autopilot": {
            "level": autopilot_level,
            "level_name": {0: "Suggest Only", 1: "Guarded Auto", 2: "Approval Required"}.get(autopilot_level, "Unknown"),
            "blocked": autopilot_status["blocked"],
            "reason": autopilot_status["reason"],
        },
        "signal_health_status": autopilot_status["status"],
        "scaling_summary": recommendations_data.get("scaling_summary", {}),
    }

    return APIResponse(success=True, data=response)


# =============================================================================
# Recommendations Endpoint
# =============================================================================

@router.get("/recommendations", response_model=APIResponse[Dict[str, Any]])
async def get_recommendations(
    request: Request,
    tenant_id: int,
    target_date: Optional[date] = Query(default=None, alias="date"),
    entity_type: Optional[str] = Query(default=None, description="Filter by entity type: campaign, adset, creative"),
    priority: Optional[str] = Query(default=None, description="Filter by priority: critical, high, medium, low"),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get detailed recommendations for a tenant.

    Each recommendation includes:
    - type: budget_shift, creative_refresh, fix_campaign, etc.
    - entity: campaign/adset/creative with ID and name
    - title: human-readable action title
    - why: list of reasons/factors
    - confidence: 0-1 confidence score
    - risk: low/medium/high
    - guardrails: any caps or limits applied
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    if not await can_access_feature(db, tenant_id, "ai_recommendations"):
        raise HTTPException(
            status_code=403,
            detail="AI recommendations feature is not enabled for this tenant"
        )

    if target_date is None:
        target_date = date.today()

    # Get metrics
    entities_today = await get_entity_metrics(db, tenant_id, target_date)
    baselines = await get_baseline_metrics(db, tenant_id)

    # Generate recommendations
    if entities_today and baselines:
        engine = RecommendationsEngine()
        recommendations_data = engine.generate_recommendations(
            entities_today=entities_today,
            baselines=baselines,
        )
        recommendations = recommendations_data.get("recommendations", [])
    else:
        recommendations = []

    # Apply filters
    if entity_type:
        recommendations = [r for r in recommendations if r.get("entity_type") == entity_type]

    if priority:
        recommendations = [r for r in recommendations if r.get("priority") == priority]

    # Apply limit
    recommendations = recommendations[:limit]

    # Add guardrails info to each recommendation
    from app.features.flags import get_autopilot_caps
    caps = get_autopilot_caps()

    for rec in recommendations:
        rec["guardrails"] = {
            "max_budget_change_pct": caps["max_budget_pct_change"],
            "max_daily_budget_change": caps["max_daily_budget_change"],
            "requires_approval": caps.get("requires_approval", False),
        }

    return APIResponse(
        success=True,
        data={
            "date": target_date.isoformat(),
            "recommendations": recommendations,
            "total": len(recommendations),
            "filters_applied": {
                "entity_type": entity_type,
                "priority": priority,
            },
        },
    )


# =============================================================================
# Anomalies Endpoint
# =============================================================================

@router.get("/anomalies", response_model=APIResponse[Dict[str, Any]])
async def get_anomalies(
    request: Request,
    tenant_id: int,
    target_date: Optional[date] = Query(default=None, alias="date"),
    days: int = Query(default=7, ge=1, le=30, description="Days to look back for anomaly detection"),
    severity: Optional[str] = Query(default=None, description="Filter by severity: critical, high, medium, low"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get anomaly alerts for a tenant.

    Detects unusual patterns in:
    - Spend spikes/drops
    - ROAS changes
    - CPA anomalies
    - Conversion rate shifts

    Requires feature flag: anomaly_alerts
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    if not await can_access_feature(db, tenant_id, "anomaly_alerts"):
        raise HTTPException(
            status_code=403,
            detail="Anomaly alerts feature is not enabled for this tenant"
        )

    if target_date is None:
        target_date = date.today()

    # In production, this would:
    # 1. Fetch historical metrics for the lookback period
    # 2. Run anomaly detection algorithms
    # 3. Return detected anomalies

    # Placeholder response
    anomalies = []

    # Example anomaly structure
    # anomalies = [
    #     {
    #         "id": "anomaly_123",
    #         "detected_at": "2026-01-02T10:30:00Z",
    #         "metric": "spend",
    #         "entity_type": "campaign",
    #         "entity_id": "camp_456",
    #         "entity_name": "Summer Sale Campaign",
    #         "severity": "high",
    #         "direction": "spike",
    #         "current_value": 5000,
    #         "expected_value": 2000,
    #         "zscore": 3.5,
    #         "description": "Spend is 150% above expected baseline",
    #         "possible_causes": ["Budget auto-increase", "CPC spike", "Expanded targeting"],
    #         "recommended_actions": ["Review targeting settings", "Check bid strategy"],
    #     }
    # ]

    # Apply severity filter
    if severity:
        anomalies = [a for a in anomalies if a.get("severity") == severity]

    return APIResponse(
        success=True,
        data={
            "date": target_date.isoformat(),
            "lookback_days": days,
            "anomalies": anomalies,
            "total": len(anomalies),
            "by_severity": {
                "critical": len([a for a in anomalies if a.get("severity") == "critical"]),
                "high": len([a for a in anomalies if a.get("severity") == "high"]),
                "medium": len([a for a in anomalies if a.get("severity") == "medium"]),
                "low": len([a for a in anomalies if a.get("severity") == "low"]),
            },
        },
    )


# =============================================================================
# KPIs Endpoint
# =============================================================================

@router.get("/kpis", response_model=APIResponse[Dict[str, Any]])
async def get_kpis(
    request: Request,
    tenant_id: int,
    target_date: Optional[date] = Query(default=None, alias="date"),
    comparison: str = Query(default="yesterday", description="Comparison period: yesterday, last_week, last_month"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get key performance indicators for a tenant.

    Returns aggregated metrics with trends:
    - Total spend
    - Total revenue
    - ROAS
    - CPA
    - Conversions
    - CTR
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    if target_date is None:
        target_date = date.today()

    # Calculate comparison date
    if comparison == "yesterday":
        compare_date = target_date - timedelta(days=1)
    elif comparison == "last_week":
        compare_date = target_date - timedelta(days=7)
    elif comparison == "last_month":
        compare_date = target_date - timedelta(days=30)
    else:
        compare_date = target_date - timedelta(days=1)

    # In production, query fact_daily_metrics for actual KPIs
    # Placeholder response
    kpis = {
        "date": target_date.isoformat(),
        "comparison_date": compare_date.isoformat(),
        "comparison_type": comparison,
        "metrics": {
            "spend": {
                "value": 0,
                "previous": 0,
                "change_pct": 0,
                "trend": "neutral",
            },
            "revenue": {
                "value": 0,
                "previous": 0,
                "change_pct": 0,
                "trend": "neutral",
            },
            "roas": {
                "value": 0,
                "previous": 0,
                "change_pct": 0,
                "trend": "neutral",
            },
            "cpa": {
                "value": 0,
                "previous": 0,
                "change_pct": 0,
                "trend": "neutral",
            },
            "conversions": {
                "value": 0,
                "previous": 0,
                "change_pct": 0,
                "trend": "neutral",
            },
            "ctr": {
                "value": 0,
                "previous": 0,
                "change_pct": 0,
                "trend": "neutral",
            },
        },
        "by_platform": {},
    }

    return APIResponse(success=True, data=kpis)
