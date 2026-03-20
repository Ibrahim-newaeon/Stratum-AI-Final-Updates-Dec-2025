# =============================================================================
# Stratum AI - Super Admin Dashboard Endpoints
# =============================================================================
"""
Super Admin endpoints for platform-level management.
Implements Multi_Tenant_and_Super_Admin_Spec.md requirements.

Features:
- MRR/ARR/NRR revenue metrics
- Tenant portfolio with health indicators
- System health monitoring
- Churn risk predictions
- Audit logging
"""

from datetime import datetime, timedelta, timezone, date
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models import Tenant, User, UserRole, Campaign
from app.schemas import APIResponse

logger = get_logger(__name__)
router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================
class RevenueMetrics(BaseModel):
    """Platform revenue metrics."""
    mrr: float  # Monthly Recurring Revenue
    arr: float  # Annual Recurring Revenue
    mrr_growth_pct: float
    gross_margin_pct: float
    arpa: float  # Average Revenue Per Account
    nrr: float  # Net Revenue Retention
    churn_rate: float  # Logo churn %
    revenue_churn_rate: float


class TenantPortfolioItem(BaseModel):
    """Tenant in the portfolio table."""
    id: int
    name: str
    slug: str
    plan: str
    status: str
    mrr: float
    users_count: int
    users_limit: int
    campaigns_count: int
    connectors: List[str]
    data_freshness_hours: Optional[float]
    signal_health: str  # healthy/risk/degraded/critical
    open_alerts: int
    churn_risk: Optional[float]
    last_admin_login: Optional[datetime]
    created_at: datetime


class SystemHealthMetrics(BaseModel):
    """System health indicators."""
    pipeline_success_rate_24h: float
    pipeline_success_rate_7d: float
    api_error_rate: float
    api_latency_p50_ms: float
    api_latency_p99_ms: float
    queue_depth: int
    queue_latency_ms: float
    platform_health: dict  # meta/google/tiktok/snap
    warehouse_cost_daily: float


class ChurnRiskItem(BaseModel):
    """Tenant with churn risk."""
    tenant_id: int
    tenant_name: str
    risk_score: float
    risk_factors: List[str]
    recommended_actions: List[str]
    mrr_at_risk: float


# =============================================================================
# Dependencies
# =============================================================================
def require_superadmin(request: Request) -> int:
    """Verify user has superadmin role."""
    user_role = getattr(request.state, "role", None)
    user_id = getattr(request.state, "user_id", None)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    if user_role != UserRole.SUPERADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required",
        )

    return user_id


# =============================================================================
# Revenue Endpoints
# =============================================================================
@router.get("/revenue", response_model=APIResponse)
async def get_revenue_metrics(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get platform revenue metrics (MRR, ARR, NRR, churn).
    SuperAdmin only.
    """
    require_superadmin(request)

    # Get all active tenants
    result = await db.execute(
        select(Tenant).where(Tenant.is_deleted == False)
    )
    tenants = result.scalars().all()

    # Calculate MRR
    total_mrr = sum(getattr(t, 'mrr_cents', 0) or 0 for t in tenants) / 100

    # Count tenants by status
    active_count = len([t for t in tenants if getattr(t, 'status', 'active') == 'active'])
    trial_count = len([t for t in tenants if t.plan == 'trial' or getattr(t, 'status', '') == 'trialing'])

    # Calculate ARPA
    arpa = total_mrr / max(active_count, 1)

    # These metrics require historical revenue data (monthly snapshots).
    # Until the tenant_revenue_monthly table is migrated, return 0.
    # Do NOT return fabricated numbers — dashboards must show real data.
    mrr_growth = 0.0
    gross_margin = 0.0
    nrr = 0.0
    logo_churn = 0.0
    revenue_churn = 0.0
    trial_conversion_rate = 0.0

    return APIResponse(
        success=True,
        data={
            "mrr": total_mrr,
            "arr": total_mrr * 12,
            "mrr_growth_pct": mrr_growth,
            "gross_margin_pct": gross_margin,
            "arpa": round(arpa, 2),
            "nrr": nrr,
            "churn_rate": logo_churn,
            "revenue_churn_rate": revenue_churn,
            "active_tenants": active_count,
            "trial_tenants": trial_count,
            "total_tenants": len(tenants),
            "trial_conversion_rate": trial_conversion_rate,
            "_note": "Growth/churn metrics require tenant_revenue_monthly migration",
        },
    )


@router.get("/revenue/breakdown", response_model=APIResponse)
async def get_revenue_breakdown(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get revenue breakdown by plan tier.
    """
    require_superadmin(request)

    result = await db.execute(
        select(Tenant).where(Tenant.is_deleted == False)
    )
    tenants = result.scalars().all()

    # Group by plan
    by_plan = {}
    for t in tenants:
        plan = t.plan
        if plan not in by_plan:
            by_plan[plan] = {"count": 0, "mrr": 0}
        by_plan[plan]["count"] += 1
        by_plan[plan]["mrr"] += (getattr(t, 'mrr_cents', 0) or 0) / 100

    return APIResponse(
        success=True,
        data={
            "by_plan": by_plan,
            "total_mrr": sum(p["mrr"] for p in by_plan.values()),
        },
    )


# =============================================================================
# Tenant Portfolio Endpoints
# =============================================================================
@router.get("/tenants/portfolio", response_model=APIResponse)
async def get_tenant_portfolio(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status_filter: Optional[str] = Query(None),
    plan_filter: Optional[str] = Query(None),
    sort_by: str = Query("mrr", pattern="^(mrr|name|created_at|churn_risk|users)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
):
    """
    Get tenant portfolio table with health indicators.
    SuperAdmin only.
    """
    require_superadmin(request)

    # Build query
    query = select(Tenant).where(Tenant.is_deleted == False)

    if status_filter:
        query = query.where(Tenant.status == status_filter)
    if plan_filter:
        query = query.where(Tenant.plan == plan_filter)

    # Execute
    result = await db.execute(query.offset(skip).limit(limit))
    tenants = result.scalars().all()

    # Get user counts
    user_counts = {}
    for t in tenants:
        count_result = await db.execute(
            select(func.count(User.id)).where(
                User.tenant_id == t.id,
                User.is_deleted == False
            )
        )
        user_counts[t.id] = count_result.scalar() or 0

    # Get campaign counts
    campaign_counts = {}
    for t in tenants:
        count_result = await db.execute(
            select(func.count(Campaign.id)).where(
                Campaign.tenant_id == t.id,
                Campaign.is_deleted == False
            )
        )
        campaign_counts[t.id] = count_result.scalar() or 0

    # Build portfolio
    portfolio = []
    for t in tenants:
        # Determine signal health (would come from real data)
        signal_health = "healthy"
        if hasattr(t, 'health_score') and t.health_score:
            if t.health_score < 50:
                signal_health = "critical"
            elif t.health_score < 70:
                signal_health = "degraded"
            elif t.health_score < 85:
                signal_health = "risk"

        portfolio.append({
            "id": t.id,
            "name": t.name,
            "slug": t.slug,
            "plan": t.plan,
            "status": getattr(t, 'status', 'active'),
            "mrr": (getattr(t, 'mrr_cents', 0) or 0) / 100,
            "users_count": user_counts.get(t.id, 0),
            "users_limit": t.max_users,
            "campaigns_count": campaign_counts.get(t.id, 0),
            "connectors": [],  # Would come from platform_connectors table
            "data_freshness_hours": None,
            "signal_health": signal_health,
            "open_alerts": 0,  # Would come from alerts table
            "churn_risk": getattr(t, 'churn_risk_score', None),
            "last_admin_login": getattr(t, 'last_admin_login_at', None),
            "created_at": t.created_at,
        })

    # Sort
    if sort_by == "mrr":
        portfolio.sort(key=lambda x: x["mrr"], reverse=(sort_order == "desc"))
    elif sort_by == "name":
        portfolio.sort(key=lambda x: x["name"].lower(), reverse=(sort_order == "desc"))
    elif sort_by == "churn_risk":
        portfolio.sort(key=lambda x: x["churn_risk"] or 0, reverse=(sort_order == "desc"))
    elif sort_by == "users":
        portfolio.sort(key=lambda x: x["users_count"], reverse=(sort_order == "desc"))

    return APIResponse(
        success=True,
        data={
            "tenants": portfolio,
            "total": len(tenants),
        },
    )


# =============================================================================
# System Health Endpoints
# =============================================================================
@router.get("/system/health", response_model=APIResponse)
async def get_system_health(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get system health metrics.
    SuperAdmin only.
    """
    require_superadmin(request)

    # Collect real system health where possible
    import redis.asyncio as aioredis
    from app.core.config import settings

    # Check Redis/Celery queue depth (real data)
    queue_depth = 0
    redis_healthy = False
    try:
        redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
        queue_depth = await redis_client.llen("celery") or 0
        redis_healthy = await redis_client.ping()
        await redis_client.close()
    except (ConnectionError, TimeoutError, OSError) as exc:
        logger.warning(f"Redis health check failed: {exc}")

    # Check DB connectivity (real data)
    db_healthy = False
    try:
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        db_healthy = True
    except (ConnectionError, TimeoutError, OSError) as exc:
        logger.warning(f"DB health check failed: {exc}")

    return APIResponse(
        success=True,
        data={
            "pipeline": {
                "success_rate_24h": None,
                "success_rate_7d": None,
                "jobs_total_24h": None,
                "jobs_failed_24h": None,
                "_note": "Requires system_health_hourly table migration",
            },
            "api": {
                "requests_24h": None,
                "error_rate": None,
                "latency_p50_ms": None,
                "latency_p99_ms": None,
                "_note": "Wire Prometheus metrics for real data",
            },
            "queue": {
                "depth": queue_depth,
                "latency_ms": None,
            },
            "platforms": {
                "meta": {"status": "unknown"},
                "google": {"status": "unknown"},
                "tiktok": {"status": "unknown"},
                "snap": {"status": "unknown"},
                "_note": "Wire platform health checks for real status",
            },
            "services": {
                "database": "healthy" if db_healthy else "unhealthy",
                "redis": "healthy" if redis_healthy else "unhealthy",
            },
        },
    )


# =============================================================================
# Churn Risk Endpoints
# =============================================================================
@router.get("/churn/risks", response_model=APIResponse)
async def get_churn_risks(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    min_risk: float = Query(0.3, ge=0, le=1),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Get tenants at churn risk with AI-predicted risk factors.
    SuperAdmin only.
    """
    require_superadmin(request)

    # Get tenants with churn risk score
    result = await db.execute(
        select(Tenant).where(Tenant.is_deleted == False)
    )
    tenants = result.scalars().all()

    # Calculate churn risk for each tenant
    risks = []
    for t in tenants:
        risk_score, risk_factors = calculate_churn_risk(t)

        if risk_score >= min_risk:
            mrr = (getattr(t, 'mrr_cents', 0) or 0) / 100
            risks.append({
                "tenant_id": t.id,
                "tenant_name": t.name,
                "plan": t.plan,
                "risk_score": round(risk_score, 2),
                "risk_factors": risk_factors,
                "recommended_actions": get_churn_actions(risk_factors),
                "mrr_at_risk": mrr,
            })

    # Sort by risk score (highest first)
    risks.sort(key=lambda x: x["risk_score"], reverse=True)
    risks = risks[:limit]

    total_mrr_at_risk = sum(r["mrr_at_risk"] for r in risks)

    return APIResponse(
        success=True,
        data={
            "at_risk_tenants": risks,
            "total_count": len(risks),
            "total_mrr_at_risk": total_mrr_at_risk,
        },
    )


def calculate_churn_risk(tenant) -> tuple[float, list[str]]:
    """
    Calculate churn risk score for a tenant.
    Based on Multi_Tenant_and_Super_Admin_Spec.md Section 6.

    risk = 0
    risk += 0.35 * usage_drop_30d
    risk += 0.25 * data_failures_14d
    risk += 0.20 * unresolved_alerts
    risk += 0.20 * low_time_to_value
    if status == past_due: risk += 0.25
    """
    risk = 0.0
    factors = []

    # Usage drop (simulated - would check tenant_usage_daily)
    last_activity = getattr(tenant, 'last_activity_at', None)
    if last_activity:
        days_inactive = (datetime.now(timezone.utc) - last_activity).days
        if days_inactive > 14:
            usage_drop = min(1.0, days_inactive / 30)
            risk += 0.35 * usage_drop
            factors.append(f"Low activity ({days_inactive} days since last login)")
    else:
        risk += 0.35 * 0.5  # No activity data = medium risk
        factors.append("No recent activity data")

    # Data failures (simulated)
    health_score = getattr(tenant, 'health_score', 100) or 100
    if health_score < 80:
        data_failure_risk = (80 - health_score) / 80
        risk += 0.25 * data_failure_risk
        factors.append(f"Data quality issues (health score: {health_score:.0f})")

    # Onboarding incomplete
    onboarding = getattr(tenant, 'onboarding_completed', True)
    if not onboarding:
        risk += 0.20 * 0.7
        factors.append("Onboarding not completed")

    # Trial expiring soon
    trial_ends = getattr(tenant, 'trial_ends_at', None)
    if trial_ends:
        days_left = (trial_ends - datetime.now(timezone.utc)).days
        if 0 < days_left < 7:
            risk += 0.15
            factors.append(f"Trial ending in {days_left} days")

    # Status past due
    status = getattr(tenant, 'status', 'active')
    if status == 'past_due':
        risk += 0.25
        factors.append("Payment past due")
    elif status == 'cancelled':
        risk += 0.50
        factors.append("Subscription cancelled")

    # Clamp to 0-1
    risk = max(0.0, min(1.0, risk))

    return risk, factors


def get_churn_actions(factors: list[str]) -> list[str]:
    """Get recommended actions based on churn risk factors."""
    actions = []

    factor_str = " ".join(factors).lower()

    if "activity" in factor_str or "login" in factor_str:
        actions.append("Schedule check-in call with customer success")
        actions.append("Send re-engagement email with new features")

    if "data quality" in factor_str or "health" in factor_str:
        actions.append("Review data pipeline and connectors")
        actions.append("Offer technical support session")

    if "onboarding" in factor_str:
        actions.append("Assign dedicated onboarding specialist")
        actions.append("Offer guided setup call")

    if "trial" in factor_str:
        actions.append("Send trial extension offer")
        actions.append("Schedule demo of premium features")

    if "payment" in factor_str or "past due" in factor_str:
        actions.append("Send dunning email sequence")
        actions.append("Offer payment plan options")

    if not actions:
        actions.append("Monitor and gather more data")

    return actions


# =============================================================================
# Audit Log Endpoints
# =============================================================================
@router.get("/audit", response_model=APIResponse)
async def get_audit_logs(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    tenant_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """
    Get audit logs with filtering.
    SuperAdmin only.
    """
    require_superadmin(request)

    try:
        from sqlalchemy import Table, MetaData
        metadata = MetaData()

        # Build query for audit_logs table
        query = """
            SELECT id, timestamp, tenant_id, user_id, user_email, action,
                   resource_type, resource_id, details, ip_address, success, error_message
            FROM audit_logs
            WHERE 1=1
        """
        params = {}

        if tenant_id:
            query += " AND tenant_id = :tenant_id"
            params["tenant_id"] = tenant_id
        if action:
            query += " AND action ILIKE :action"
            params["action"] = f"%{action}%"
        if user_id:
            query += " AND user_id = :user_id"
            params["user_id"] = user_id
        if start_date:
            query += " AND timestamp >= :start_date"
            params["start_date"] = start_date
        if end_date:
            query += " AND timestamp <= :end_date"
            params["end_date"] = end_date

        query += " ORDER BY timestamp DESC LIMIT :limit OFFSET :skip"
        params["limit"] = limit
        params["skip"] = skip

        from sqlalchemy import text
        result = await db.execute(text(query), params)
        rows = result.fetchall()

        logs = []
        for row in rows:
            logs.append({
                "id": row[0],
                "timestamp": row[1].isoformat() if row[1] else None,
                "tenant_id": row[2],
                "user_id": row[3],
                "user_email": row[4],
                "action": row[5],
                "resource_type": row[6],
                "resource_id": row[7],
                "details": row[8],
                "ip_address": row[9],
                "success": row[10],
                "error_message": row[11],
            })

        # Get total count
        count_query = "SELECT COUNT(*) FROM audit_logs WHERE 1=1"
        count_params = {}
        if tenant_id:
            count_query += " AND tenant_id = :tenant_id"
            count_params["tenant_id"] = tenant_id
        count_result = await db.execute(text(count_query), count_params)
        total = count_result.scalar() or 0

        return APIResponse(
            success=True,
            data={
                "logs": logs,
                "total": total,
                "skip": skip,
                "limit": limit,
            },
        )
    except (SQLAlchemyError, ValueError) as e:
        logger.warning("audit_logs_query_failed", error=str(e))
        return APIResponse(
            success=True,
            data={
                "logs": [],
                "total": 0,
                "message": "Audit logs table not yet migrated",
            },
        )


async def create_audit_log(
    db: AsyncSession,
    action: str,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    tenant_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None,
):
    """
    Create an audit log entry.
    Used by other endpoints to track admin actions.
    """
    try:
        from sqlalchemy import text
        import json

        query = text("""
            INSERT INTO audit_logs
            (timestamp, tenant_id, user_id, user_email, action, resource_type,
             resource_id, details, ip_address, user_agent, success, error_message)
            VALUES
            (NOW(), :tenant_id, :user_id, :user_email, :action, :resource_type,
             :resource_id, :details, :ip_address, :user_agent, :success, :error_message)
        """)

        await db.execute(query, {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "user_email": user_email,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": json.dumps(details) if details else None,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "success": success,
            "error_message": error_message,
        })
        await db.commit()
    except (SQLAlchemyError, ValueError) as e:
        logger.warning("create_audit_log_failed", error=str(e))


# =============================================================================
# Billing Admin Endpoints
# =============================================================================
@router.get("/billing/plans", response_model=APIResponse)
async def get_subscription_plans(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get all subscription plans with limits.
    SuperAdmin only.
    """
    require_superadmin(request)

    try:
        from sqlalchemy import text
        result = await db.execute(text("""
            SELECT id, name, display_name, tier, billing_period, price_cents,
                   currency, max_users, max_campaigns, max_connectors,
                   max_refresh_frequency_mins, features, is_active, sort_order
            FROM subscription_plans
            WHERE is_active = true
            ORDER BY sort_order
        """))
        rows = result.fetchall()

        plans = []
        for row in rows:
            plans.append({
                "id": row[0],
                "name": row[1],
                "display_name": row[2],
                "tier": row[3],
                "billing_period": row[4],
                "price_cents": row[5],
                "price": row[5] / 100,
                "currency": row[6],
                "limits": {
                    "max_users": row[7],
                    "max_campaigns": row[8],
                    "max_connectors": row[9],
                    "max_refresh_frequency_mins": row[10],
                },
                "features": row[11] or {},
                "is_active": row[12],
            })

        return APIResponse(success=True, data={"plans": plans})
    except (SQLAlchemyError, ValueError) as e:
        logger.warning("plans_query_failed", error=str(e))
        # Return default plans
        return APIResponse(
            success=True,
            data={
                "plans": [
                    {"id": "free", "name": "Free", "tier": "free", "price": 0, "limits": {"max_users": 5, "max_campaigns": 10, "max_connectors": 2}},
                    {"id": "starter_monthly", "name": "Starter", "tier": "starter", "price": 99, "limits": {"max_users": 10, "max_campaigns": 50, "max_connectors": 3}},
                    {"id": "professional_monthly", "name": "Professional", "tier": "professional", "price": 299, "limits": {"max_users": 25, "max_campaigns": 200, "max_connectors": 5}},
                    {"id": "enterprise_monthly", "name": "Enterprise", "tier": "enterprise", "price": 999, "limits": {"max_users": 100, "max_campaigns": 1000, "max_connectors": 10}},
                ],
            },
        )


class PlanUpdate(BaseModel):
    """Plan update request."""
    price_cents: Optional[int] = None
    max_users: Optional[int] = None
    max_campaigns: Optional[int] = None
    max_connectors: Optional[int] = None
    features: Optional[dict] = None
    is_active: Optional[bool] = None


@router.patch("/billing/plans/{plan_id}", response_model=APIResponse)
async def update_subscription_plan(
    plan_id: str,
    update: PlanUpdate,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Update a subscription plan.
    SuperAdmin only.
    """
    user_id = require_superadmin(request)

    try:
        from sqlalchemy import text
        import json

        updates = []
        params = {"plan_id": plan_id}

        if update.price_cents is not None:
            updates.append("price_cents = :price_cents")
            params["price_cents"] = update.price_cents
        if update.max_users is not None:
            updates.append("max_users = :max_users")
            params["max_users"] = update.max_users
        if update.max_campaigns is not None:
            updates.append("max_campaigns = :max_campaigns")
            params["max_campaigns"] = update.max_campaigns
        if update.max_connectors is not None:
            updates.append("max_connectors = :max_connectors")
            params["max_connectors"] = update.max_connectors
        if update.features is not None:
            updates.append("features = :features")
            params["features"] = json.dumps(update.features)
        if update.is_active is not None:
            updates.append("is_active = :is_active")
            params["is_active"] = update.is_active

        if updates:
            updates.append("updated_at = NOW()")
            query = text(f"UPDATE subscription_plans SET {', '.join(updates)} WHERE id = :plan_id")
            await db.execute(query, params)
            await db.commit()

            # Create audit log
            await create_audit_log(
                db, action="plan_updated", user_id=user_id,
                resource_type="subscription_plan", resource_id=plan_id,
                details=update.dict(exclude_none=True)
            )

        return APIResponse(success=True, message=f"Plan {plan_id} updated")
    except (SQLAlchemyError, ValueError) as e:
        logger.error("update_plan_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/billing/invoices", response_model=APIResponse)
async def get_invoices(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status_filter: Optional[str] = Query(None),
    tenant_id: Optional[int] = Query(None),
):
    """
    Get all invoices across tenants.
    SuperAdmin only.
    """
    require_superadmin(request)

    try:
        from sqlalchemy import text

        query = """
            SELECT i.id, i.tenant_id, t.name as tenant_name, i.invoice_number,
                   i.status, i.amount_cents, i.tax_cents, i.total_cents,
                   i.currency, i.due_date, i.paid_at, i.created_at
            FROM invoices i
            LEFT JOIN tenants t ON i.tenant_id = t.id
            WHERE 1=1
        """
        params = {}

        if status_filter:
            query += " AND i.status = :status"
            params["status"] = status_filter
        if tenant_id:
            query += " AND i.tenant_id = :tenant_id"
            params["tenant_id"] = tenant_id

        query += " ORDER BY i.created_at DESC LIMIT :limit OFFSET :skip"
        params["limit"] = limit
        params["skip"] = skip

        result = await db.execute(text(query), params)
        rows = result.fetchall()

        invoices = []
        for row in rows:
            invoices.append({
                "id": row[0],
                "tenant_id": row[1],
                "tenant_name": row[2],
                "invoice_number": row[3],
                "status": row[4],
                "amount_cents": row[5],
                "amount": row[5] / 100 if row[5] else 0,
                "tax_cents": row[6],
                "total_cents": row[7],
                "total": row[7] / 100 if row[7] else 0,
                "currency": row[8],
                "due_date": row[9].isoformat() if row[9] else None,
                "paid_at": row[10].isoformat() if row[10] else None,
                "created_at": row[11].isoformat() if row[11] else None,
            })

        # Get summary
        summary_result = await db.execute(text("""
            SELECT
                SUM(CASE WHEN status = 'paid' THEN total_cents ELSE 0 END) as paid,
                SUM(CASE WHEN status = 'pending' THEN total_cents ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'overdue' THEN total_cents ELSE 0 END) as overdue
            FROM invoices
        """))
        summary_row = summary_result.fetchone()

        return APIResponse(
            success=True,
            data={
                "invoices": invoices,
                "total": len(invoices),
                "summary": {
                    "paid": (summary_row[0] or 0) / 100,
                    "pending": (summary_row[1] or 0) / 100,
                    "overdue": (summary_row[2] or 0) / 100,
                },
            },
        )
    except (SQLAlchemyError, ValueError) as e:
        logger.warning("invoices_query_failed", error=str(e))
        return APIResponse(
            success=True,
            data={
                "invoices": [],
                "total": 0,
                "summary": {"paid": 0, "pending": 0, "overdue": 0},
                "message": "Invoices table not yet migrated",
            },
        )


@router.get("/billing/subscriptions", response_model=APIResponse)
async def get_subscriptions(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status_filter: Optional[str] = Query(None),
):
    """
    Get all active subscriptions.
    SuperAdmin only.
    """
    require_superadmin(request)

    try:
        from sqlalchemy import text

        query = """
            SELECT s.id, s.tenant_id, t.name as tenant_name, s.plan_id,
                   p.display_name as plan_name, s.status, s.current_period_start,
                   s.current_period_end, s.cancel_at_period_end, s.discount_percent
            FROM subscriptions s
            LEFT JOIN tenants t ON s.tenant_id = t.id
            LEFT JOIN subscription_plans p ON s.plan_id = p.id
            WHERE 1=1
        """
        params = {}

        if status_filter:
            query += " AND s.status = :status"
            params["status"] = status_filter

        query += " ORDER BY s.created_at DESC LIMIT :limit OFFSET :skip"
        params["limit"] = limit
        params["skip"] = skip

        result = await db.execute(text(query), params)
        rows = result.fetchall()

        subscriptions = []
        for row in rows:
            subscriptions.append({
                "id": row[0],
                "tenant_id": row[1],
                "tenant_name": row[2],
                "plan_id": row[3],
                "plan_name": row[4],
                "status": row[5],
                "current_period_start": row[6].isoformat() if row[6] else None,
                "current_period_end": row[7].isoformat() if row[7] else None,
                "cancel_at_period_end": row[8],
                "discount_percent": row[9],
            })

        return APIResponse(
            success=True,
            data={"subscriptions": subscriptions, "total": len(subscriptions)},
        )
    except (SQLAlchemyError, ValueError) as e:
        logger.warning("subscriptions_query_failed", error=str(e))
        return APIResponse(
            success=True,
            data={"subscriptions": [], "total": 0, "message": "Table not yet migrated"},
        )


class SubscriptionAction(BaseModel):
    """Subscription action request."""
    action: str  # upgrade, downgrade, cancel, pause, resume, extend_trial
    new_plan_id: Optional[str] = None
    reason: Optional[str] = None
    extend_days: Optional[int] = None


@router.post("/billing/subscriptions/{subscription_id}/action", response_model=APIResponse)
async def perform_subscription_action(
    subscription_id: int,
    action_req: SubscriptionAction,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Perform action on subscription (upgrade, downgrade, cancel, etc).
    SuperAdmin only.
    """
    user_id = require_superadmin(request)

    try:
        from sqlalchemy import text

        if action_req.action == "cancel":
            await db.execute(text("""
                UPDATE subscriptions
                SET cancel_at_period_end = true, updated_at = NOW()
                WHERE id = :id
            """), {"id": subscription_id})

        elif action_req.action == "upgrade" and action_req.new_plan_id:
            await db.execute(text("""
                UPDATE subscriptions
                SET plan_id = :plan_id, updated_at = NOW()
                WHERE id = :id
            """), {"id": subscription_id, "plan_id": action_req.new_plan_id})

        elif action_req.action == "extend_trial" and action_req.extend_days:
            await db.execute(text("""
                UPDATE subscriptions
                SET current_period_end = current_period_end + make_interval(days => :days),
                    updated_at = NOW()
                WHERE id = :id
            """), {"id": subscription_id, "days": int(action_req.extend_days)})

        elif action_req.action == "resume":
            await db.execute(text("""
                UPDATE subscriptions
                SET cancel_at_period_end = false, status = 'active', updated_at = NOW()
                WHERE id = :id
            """), {"id": subscription_id})

        await db.commit()

        # Audit log
        await create_audit_log(
            db, action=f"subscription_{action_req.action}", user_id=user_id,
            resource_type="subscription", resource_id=str(subscription_id),
            details=action_req.dict()
        )

        return APIResponse(success=True, message=f"Subscription {action_req.action} successful")
    except (SQLAlchemyError, ValueError) as e:
        logger.error("subscription_action_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Subscription Limits Enforcement
# =============================================================================
@router.get("/tenants/{tenant_id}/usage", response_model=APIResponse)
async def get_tenant_usage(
    tenant_id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get tenant usage vs limits (for overage warnings).
    SuperAdmin only.
    """
    require_superadmin(request)

    # Get tenant
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Get user count
    user_result = await db.execute(
        select(func.count(User.id)).where(User.tenant_id == tenant_id, User.is_deleted == False)
    )
    users_count = user_result.scalar() or 0

    # Get campaign count
    campaign_result = await db.execute(
        select(func.count(Campaign.id)).where(Campaign.tenant_id == tenant_id, Campaign.is_deleted == False)
    )
    campaigns_count = campaign_result.scalar() or 0

    # Get connector count (from platform_connectors)
    try:
        from sqlalchemy import text
        connector_result = await db.execute(text("""
            SELECT COUNT(*) FROM platform_connectors WHERE tenant_id = :tenant_id AND status = 'connected'
        """), {"tenant_id": tenant_id})
        connectors_count = connector_result.scalar() or 0
    except (ConnectionError, TimeoutError, OSError) as exc:
        logger.warning(f"Failed to count connectors for tenant {tenant_id}: {exc}")
        connectors_count = 0

    # Get limits from tenant or default
    max_users = tenant.max_users
    max_campaigns = getattr(tenant, 'max_campaigns', 1000)
    max_connectors = getattr(tenant, 'max_connectors', 5)

    # Calculate usage percentages
    users_pct = (users_count / max_users * 100) if max_users > 0 else 0
    campaigns_pct = (campaigns_count / max_campaigns * 100) if max_campaigns > 0 else 0
    connectors_pct = (connectors_count / max_connectors * 100) if max_connectors > 0 else 0

    # Determine warnings
    warnings = []
    if users_pct >= 90:
        warnings.append({"type": "users", "message": f"User limit nearly reached ({users_count}/{max_users})", "severity": "high"})
    elif users_pct >= 75:
        warnings.append({"type": "users", "message": f"User usage at {users_pct:.0f}%", "severity": "medium"})

    if campaigns_pct >= 90:
        warnings.append({"type": "campaigns", "message": f"Campaign limit nearly reached ({campaigns_count}/{max_campaigns})", "severity": "high"})
    elif campaigns_pct >= 75:
        warnings.append({"type": "campaigns", "message": f"Campaign usage at {campaigns_pct:.0f}%", "severity": "medium"})

    if connectors_pct >= 100:
        warnings.append({"type": "connectors", "message": f"Connector limit reached ({connectors_count}/{max_connectors})", "severity": "critical"})

    return APIResponse(
        success=True,
        data={
            "tenant_id": tenant_id,
            "tenant_name": tenant.name,
            "plan": tenant.plan,
            "usage": {
                "users": {"current": users_count, "limit": max_users, "percent": round(users_pct, 1)},
                "campaigns": {"current": campaigns_count, "limit": max_campaigns, "percent": round(campaigns_pct, 1)},
                "connectors": {"current": connectors_count, "limit": max_connectors, "percent": round(connectors_pct, 1)},
            },
            "warnings": warnings,
            "needs_upgrade": len([w for w in warnings if w["severity"] in ["high", "critical"]]) > 0,
        },
    )


# =============================================================================
# Dashboard Summary
# =============================================================================
@router.get("/dashboard", response_model=APIResponse)
async def get_superadmin_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get Super Admin dashboard summary.
    Combines revenue, health, and alerts.
    """
    require_superadmin(request)

    # Get tenant counts
    result = await db.execute(
        select(Tenant).where(Tenant.is_deleted == False)
    )
    tenants = result.scalars().all()

    total_tenants = len(tenants)
    # NOTE: Tenant.status and Tenant.mrr_cents are not yet on the model;
    # getattr defaults keep this safe but return placeholder values.
    active_tenants = len([t for t in tenants if getattr(t, 'status', 'active') == 'active'])
    trial_tenants = len([t for t in tenants if t.plan == 'trial'])
    total_mrr = sum((getattr(t, 'mrr_cents', 0) or 0) for t in tenants) / 100

    # Get user count
    user_result = await db.execute(
        select(func.count(User.id)).where(User.is_deleted == False)
    )
    total_users = user_result.scalar() or 0

    # Get campaign count
    campaign_result = await db.execute(
        select(func.count(Campaign.id)).where(Campaign.is_deleted == False)
    )
    total_campaigns = campaign_result.scalar() or 0

    # Calculate churn risks
    high_risk_count = 0
    for t in tenants:
        risk, _ = calculate_churn_risk(t)
        if risk >= 0.5:
            high_risk_count += 1

    return APIResponse(
        success=True,
        data={
            "revenue": {
                "mrr": total_mrr,
                "arr": total_mrr * 12,
                "growth_pct": None,  # Requires revenue history
            },
            "tenants": {
                "total": total_tenants,
                "active": active_tenants,
                "trial": trial_tenants,
                "at_churn_risk": high_risk_count,
            },
            "usage": {
                "total_users": total_users,
                "total_campaigns": total_campaigns,
            },
            "health": {
                "platform_status": None,
                "pipeline_success_rate": None,
                "api_uptime": None,
                "_note": "Wire Prometheus/system_health_hourly for real data",
            },
            "alerts": {
                "critical": None,
                "high": None,
                "medium": None,
                "_note": "Wire alerts table for real counts",
            },
        },
    )


# =============================================================================
# Seed Platform Connections from Env Vars
# =============================================================================
class SeedPlatformsRequest(BaseModel):
    """Request to bootstrap platform connections from env vars."""
    tenant_id: int = 1
    trigger_sync: bool = True


@router.post("/seed-platforms", response_model=APIResponse)
async def seed_platforms(
    body: SeedPlatformsRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Bootstrap TenantPlatformConnection and TenantAdAccount records from
    environment-variable tokens.  SuperAdmin only.

    This replaces the normal OAuth callback flow for initial setup when
    tokens are already provisioned as Railway env vars.
    """
    user_id = require_superadmin(request)

    from app.core.config import settings
    from app.core.security import encrypt_pii
    from app.models.campaign_builder import (
        TenantPlatformConnection,
        TenantAdAccount,
        ConnectionStatus,
    )
    from app.base_models import AdPlatform

    # Verify tenant exists
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == body.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Platform config: (platform, access_token_setting, account_ids_fn, extra_fields)
    platform_configs = [
        {
            "platform": "meta",
            "access_token": settings.meta_access_token,
            "account_ids_fn": lambda: _parse_meta_account_ids(settings.meta_ad_account_ids),
            "extra": {
                "meta_app_id": settings.meta_app_id,
                "meta_app_secret": settings.meta_app_secret,
            },
        },
        {
            "platform": "google",
            "access_token": settings.google_ads_refresh_token,
            "account_ids_fn": lambda: _parse_google_account_ids(settings.google_ads_customer_id),
            "extra": {
                "google_ads_developer_token": settings.google_ads_developer_token,
                "google_ads_client_id": settings.google_ads_client_id,
                "google_ads_client_secret": settings.google_ads_client_secret,
            },
        },
        {
            "platform": "tiktok",
            "access_token": settings.tiktok_access_token,
            "account_ids_fn": lambda: [settings.tiktok_advertiser_id] if settings.tiktok_advertiser_id else [],
            "extra": {
                "tiktok_app_id": settings.tiktok_app_id,
                "tiktok_secret": settings.tiktok_secret,
            },
        },
        {
            "platform": "snapchat",
            "access_token": settings.snapchat_access_token,
            "account_ids_fn": lambda: [settings.snapchat_ad_account_id] if settings.snapchat_ad_account_id else [],
            "extra": {
                "snapchat_client_id": settings.snapchat_client_id,
                "snapchat_client_secret": settings.snapchat_client_secret,
            },
        },
    ]

    connections_created = []
    accounts_created = []
    sync_results = []
    now = datetime.now(timezone.utc)

    for cfg in platform_configs:
        token = cfg["access_token"]
        if not token:
            continue

        platform_name = cfg["platform"]

        # --- Upsert TenantPlatformConnection ---
        conn_result = await db.execute(
            select(TenantPlatformConnection).where(
                TenantPlatformConnection.tenant_id == body.tenant_id,
                TenantPlatformConnection.platform == platform_name,
            )
        )
        conn = conn_result.scalar_one_or_none()

        if conn:
            conn.access_token_encrypted = encrypt_pii(token)
            conn.status = ConnectionStatus.CONNECTED.value
            conn.connected_at = now
            conn.updated_at = now
            conn.last_error = None
            conn.error_count = 0
        else:
            conn = TenantPlatformConnection(
                id=uuid4(),
                tenant_id=body.tenant_id,
                platform=platform_name,
                status=ConnectionStatus.CONNECTED.value,
                access_token_encrypted=encrypt_pii(token),
                connected_at=now,
                granted_by_user_id=user_id,
                scopes=[],
            )
            db.add(conn)

        # Store refresh token for Google (uses refresh_token flow)
        if platform_name == "google" and settings.google_ads_refresh_token:
            conn.refresh_token_encrypted = encrypt_pii(settings.google_ads_refresh_token)

        # Flush to get conn.id for ad accounts
        await db.flush()
        connections_created.append(platform_name)

        # --- Create TenantAdAccount records ---
        account_ids = cfg["account_ids_fn"]()
        for acct_id in account_ids:
            if not acct_id:
                continue
            acct_result = await db.execute(
                select(TenantAdAccount).where(
                    TenantAdAccount.tenant_id == body.tenant_id,
                    TenantAdAccount.platform == platform_name,
                    TenantAdAccount.platform_account_id == acct_id,
                )
            )
            existing_acct = acct_result.scalar_one_or_none()

            if existing_acct:
                existing_acct.is_enabled = True
                existing_acct.connection_id = conn.id
                existing_acct.updated_at = now
            else:
                new_acct = TenantAdAccount(
                    id=uuid4(),
                    tenant_id=body.tenant_id,
                    connection_id=conn.id,
                    platform=platform_name,
                    platform_account_id=acct_id,
                    name=f"{platform_name.title()} - {acct_id}",
                    is_enabled=True,
                    currency="USD",
                    timezone="UTC",
                )
                db.add(new_acct)

            accounts_created.append({"platform": platform_name, "account_id": acct_id})

    await db.commit()

    # --- Trigger sync (optional) ---
    if body.trigger_sync and connections_created:
        from app.services.sync.orchestrator import PlatformSyncOrchestrator
        from app.base_models import AdPlatform as AP

        orchestrator = PlatformSyncOrchestrator(db)
        platform_map = {
            "meta": AP.META,
            "google": AP.GOOGLE,
            "tiktok": AP.TIKTOK,
            "snapchat": AP.SNAPCHAT,
        }
        for pname in connections_created:
            ap = platform_map.get(pname)
            if not ap:
                continue
            try:
                sr = await orchestrator.sync_platform(body.tenant_id, ap, days_back=30)
                sync_results.append({
                    "platform": pname,
                    "campaigns_synced": sr.campaigns_synced,
                    "metrics_upserted": sr.metrics_upserted,
                    "errors": sr.errors,
                    "duration_seconds": round(sr.duration_seconds, 2),
                })
            except (ConnectionError, TimeoutError, OSError, ValueError) as e:
                logger.error("seed_sync_failed", platform=pname, error=str(e))
                sync_results.append({
                    "platform": pname,
                    "campaigns_synced": 0,
                    "metrics_upserted": 0,
                    "errors": [str(e)],
                })

    # Audit log
    await create_audit_log(
        db,
        action="seed_platforms",
        user_id=user_id,
        tenant_id=body.tenant_id,
        resource_type="platform_connections",
        details={
            "connections": connections_created,
            "accounts": accounts_created,
        },
    )

    return APIResponse(
        success=True,
        data={
            "connections_created": connections_created,
            "accounts_created": accounts_created,
            "sync_results": sync_results,
        },
        message=f"Seeded {len(connections_created)} platform(s) with {len(accounts_created)} ad account(s)",
    )


def _parse_meta_account_ids(raw: Optional[str]) -> list[str]:
    """Parse comma-separated Meta ad account IDs, adding act_ prefix if missing."""
    if not raw:
        return []
    ids = []
    for part in raw.split(","):
        aid = part.strip()
        if not aid:
            continue
        if not aid.startswith("act_"):
            aid = f"act_{aid}"
        ids.append(aid)
    return ids


def _parse_google_account_ids(raw: Optional[str]) -> list[str]:
    """Parse Google Ads customer ID, stripping hyphens."""
    if not raw:
        return []
    return [raw.replace("-", "").strip()]


# =============================================================================
# Seed Demo Data
# =============================================================================
@router.post("/seed-demo-data", response_model=APIResponse)
async def seed_demo_data(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    tenant_id: int = Query(1, description="Tenant to seed data for"),
):
    """
    Seed realistic demo campaign data for a tenant.
    Creates 14 campaigns across 5 platforms with 90 days of daily metrics.
    SuperAdmin only.
    """
    user_id = require_superadmin(request)

    from sqlalchemy import text

    # Verify tenant exists
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    params = {"tid": tenant_id}

    # Each SQL statement must be executed separately (asyncpg limitation)
    sql_steps = [
        # Step 1: Clean existing demo data
        text("DELETE FROM fact_platform_daily WHERE tenant_id = :tid"),
        text("DELETE FROM campaign_metrics WHERE tenant_id = :tid"),
        text("DELETE FROM campaigns WHERE tenant_id = :tid"),

        # Step 2: Insert campaigns
        text("""INSERT INTO campaigns (tenant_id, platform, external_id, account_id, name, status, objective, daily_budget_cents, total_spend_cents, impressions, clicks, conversions, revenue_cents, ctr, roas, start_date, currency, labels, created_at, updated_at)
VALUES
(:tid, 'meta',   'camp_meta_001',  'act_100001', 'Summer Sale - Lookalike Audiences',  'active', 'conversions', 15000, 1350000, 2800000, 56000, 1680, 5400000, 2.0, 4.0, CURRENT_DATE - 90, 'USD', '["high-performer","retargeting"]', NOW(), NOW()),
(:tid, 'google', 'camp_goog_001',  'act_200001', 'Brand Search - Exact Match',         'active', 'conversions', 12000, 1080000, 1500000, 105000, 3150, 4320000, 7.0, 4.0, CURRENT_DATE - 90, 'USD', '["brand","search"]', NOW(), NOW()),
(:tid, 'meta',   'camp_meta_002',  'act_100001', 'Retargeting - Cart Abandoners',      'active', 'conversions', 8000, 720000, 1200000, 36000, 1440, 2880000, 3.0, 4.0, CURRENT_DATE - 90, 'USD', '["retargeting"]', NOW(), NOW()),
(:tid, 'google', 'camp_goog_002',  'act_200001', 'Shopping - Product Listing Ads',     'active', 'sales',       20000, 1800000, 3500000, 52500, 1050, 3960000, 1.5, 2.2, CURRENT_DATE - 90, 'USD', '["shopping"]', NOW(), NOW()),
(:tid, 'tiktok', 'camp_tik_001',   'act_300001', 'UGC Creative - Gen Z Audience',      'active', 'conversions', 10000, 900000, 4500000, 67500, 900, 1800000, 1.5, 2.0, CURRENT_DATE - 90, 'USD', '["ugc","genZ"]', NOW(), NOW()),
(:tid, 'meta',   'camp_meta_003',  'act_100001', 'Video Views - Product Demo',         'active', 'video_views', 6000, 540000, 3200000, 32000, 480, 1080000, 1.0, 2.0, CURRENT_DATE - 90, 'USD', '["video","awareness"]', NOW(), NOW()),
(:tid, 'snapchat','camp_snap_001', 'act_400001', 'Story Ads - Flash Sale',             'active', 'conversions', 7000, 630000, 2100000, 42000, 630, 1260000, 2.0, 2.0, CURRENT_DATE - 90, 'USD', '["stories"]', NOW(), NOW()),
(:tid, 'linkedin','camp_li_001',   'act_500001', 'Lead Gen - Decision Makers',         'active', 'leads',       15000, 1350000, 800000, 8000, 400, 2700000, 1.0, 2.0, CURRENT_DATE - 90, 'USD', '["b2b","leads"]', NOW(), NOW()),
(:tid, 'google', 'camp_goog_003',  'act_200001', 'Display - Remarketing',              'active', 'conversions', 5000, 450000, 5000000, 25000, 375, 900000, 0.5, 2.0, CURRENT_DATE - 90, 'USD', '["display","remarketing"]', NOW(), NOW()),
(:tid, 'tiktok', 'camp_tik_002',   'act_300001', 'Spark Ads - Influencer Collab',      'active', 'engagement',  8000, 720000, 3800000, 57000, 570, 1440000, 1.5, 2.0, CURRENT_DATE - 90, 'USD', '["influencer"]', NOW(), NOW()),
(:tid, 'meta',   'camp_meta_004',  'act_100001', 'Cold Audience - Interest Targeting', 'active', 'conversions', 12000, 1080000, 2000000, 20000, 200, 540000, 1.0, 0.5, CURRENT_DATE - 90, 'USD', '["prospecting"]', NOW(), NOW()),
(:tid, 'snapchat','camp_snap_002', 'act_400001', 'AR Lens - Brand Awareness',          'paused', 'awareness',   9000, 810000, 1800000, 9000, 90, 324000, 0.5, 0.4, CURRENT_DATE - 90, 'USD', '["ar","awareness"]', NOW(), NOW()),
(:tid, 'google', 'camp_goog_004',  'act_200001', 'Broad Match - New Markets',          'active', 'conversions', 10000, 900000, 1800000, 18000, 180, 720000, 1.0, 0.8, CURRENT_DATE - 90, 'USD', '["expansion"]', NOW(), NOW()),
(:tid, 'tiktok', 'camp_tik_003',   'act_300001', 'Hashtag Challenge - Brand Launch',   'paused', 'awareness',   15000, 1350000, 6000000, 60000, 300, 675000, 1.0, 0.5, CURRENT_DATE - 90, 'USD', '["hashtag","brand"]', NOW(), NOW())"""),

        # Step 3: Generate daily metrics
        text("""INSERT INTO campaign_metrics (tenant_id, campaign_id, date, impressions, clicks, conversions, spend_cents, revenue_cents)
SELECT :tid, c.id, d.date,
  GREATEST(100, (c.impressions / 90.0 * (0.7 + random() * 0.6))::INT),
  GREATEST(10, (c.clicks / 90.0 * (0.7 + random() * 0.6))::INT),
  GREATEST(0, (c.conversions / 90.0 * (0.6 + random() * 0.8))::INT),
  GREATEST(100, (c.total_spend_cents / 90.0 * (0.75 + random() * 0.5))::INT),
  GREATEST(0, (c.revenue_cents / 90.0 * (0.65 + random() * 0.7))::INT)
FROM campaigns c
CROSS JOIN generate_series(CURRENT_DATE - 89, CURRENT_DATE, '1 day'::interval) AS d(date)
WHERE c.tenant_id = :tid"""),

        # Step 4: Populate analytics warehouse
        text("""INSERT INTO fact_platform_daily (date, platform, tenant_id, account_id, campaign_id, spend, impressions, clicks, conversions, revenue, ctr, cvr, cpm, cpc, cpa, roas, ingestion_time)
SELECT cm.date, c.platform::TEXT, :tid, c.account_id, c.external_id,
  cm.spend_cents / 100.0, cm.impressions, cm.clicks, cm.conversions, cm.revenue_cents / 100.0,
  CASE WHEN cm.impressions > 0 THEN ROUND((cm.clicks::NUMERIC / cm.impressions * 100)::NUMERIC, 2) ELSE 0 END,
  CASE WHEN cm.clicks > 0 THEN ROUND((cm.conversions::NUMERIC / cm.clicks * 100)::NUMERIC, 2) ELSE 0 END,
  CASE WHEN cm.impressions > 0 THEN ROUND((cm.spend_cents / 100.0 / cm.impressions * 1000)::NUMERIC, 2) ELSE 0 END,
  CASE WHEN cm.clicks > 0 THEN ROUND((cm.spend_cents / 100.0 / cm.clicks)::NUMERIC, 2) ELSE 0 END,
  CASE WHEN cm.conversions > 0 THEN ROUND((cm.spend_cents / 100.0 / cm.conversions)::NUMERIC, 2) ELSE 0 END,
  CASE WHEN cm.spend_cents > 0 THEN ROUND((cm.revenue_cents::NUMERIC / cm.spend_cents)::NUMERIC, 2) ELSE 0 END,
  NOW()
FROM campaign_metrics cm
JOIN campaigns c ON c.id = cm.campaign_id
WHERE cm.tenant_id = :tid"""),

        # Step 5: Update campaign aggregates
        text("""UPDATE campaigns SET
  total_spend_cents = sub.total_spend,
  impressions = sub.total_impressions,
  clicks = sub.total_clicks,
  conversions = sub.total_conversions,
  revenue_cents = sub.total_revenue,
  ctr = CASE WHEN sub.total_impressions > 0 THEN ROUND((sub.total_clicks::NUMERIC / sub.total_impressions * 100)::NUMERIC, 2) ELSE 0 END,
  roas = CASE WHEN sub.total_spend > 0 THEN ROUND((sub.total_revenue::NUMERIC / sub.total_spend)::NUMERIC, 2) ELSE 0 END,
  last_synced_at = NOW(), updated_at = NOW()
FROM (
  SELECT campaign_id, SUM(spend_cents) AS total_spend, SUM(impressions) AS total_impressions,
         SUM(clicks) AS total_clicks, SUM(conversions) AS total_conversions, SUM(revenue_cents) AS total_revenue
  FROM campaign_metrics WHERE tenant_id = :tid GROUP BY campaign_id
) sub
WHERE campaigns.id = sub.campaign_id AND campaigns.tenant_id = :tid"""),
    ]

    try:
        for step in sql_steps:
            await db.execute(step, params)
        await db.commit()
    except (SQLAlchemyError, ValueError) as e:
        await db.rollback()
        logger.error("seed_demo_data_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Seed failed: {str(e)}")

    # Count results
    camp_count = (await db.execute(
        text("SELECT COUNT(*) FROM campaigns WHERE tenant_id = :tid"),
        {"tid": tenant_id},
    )).scalar()
    metric_count = (await db.execute(
        text("SELECT COUNT(*) FROM campaign_metrics WHERE tenant_id = :tid"),
        {"tid": tenant_id},
    )).scalar()
    fact_count = (await db.execute(
        text("SELECT COUNT(*) FROM fact_platform_daily WHERE tenant_id = :tid"),
        {"tid": tenant_id},
    )).scalar()

    logger.info("seed_demo_data_complete", tenant_id=tenant_id,
                campaigns=camp_count, metrics=metric_count, facts=fact_count)

    return APIResponse(
        success=True,
        data={
            "campaigns_created": camp_count,
            "daily_metrics_rows": metric_count,
            "fact_rows": fact_count,
            "tenant_id": tenant_id,
        },
        message=f"Seeded {camp_count} campaigns with {metric_count} daily metric rows",
    )
