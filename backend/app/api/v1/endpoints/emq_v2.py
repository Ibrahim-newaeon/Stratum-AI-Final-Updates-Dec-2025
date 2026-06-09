# =============================================================================
# Stratum AI - EMQ v2 API Router
# =============================================================================
"""
EMQ (Event Measurement Quality) v2 API endpoints.

Provides endpoints for:
- EMQ score and drivers
- Confidence band details
- Fix playbook management
- Incident timeline
- ROAS impact estimation
- Signal volatility tracking
- Autopilot state management
- Platform benchmarks (super admin)
- Portfolio overview (super admin)
"""

from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, require_superadmin
from app.db.session import get_async_session
from app.schemas.emq_v2 import (
    AutopilotModeUpdate,
    AutopilotStateResponse,
    BandDistribution,
    ConfidenceDataResponse,
    ConfidenceFactor,
    ConfidenceThresholds,
    EmqBenchmarkResponse,
    EmqDriver,
    EmqImpactResponse,
    EmqIncidentResponse,
    EmqPortfolioResponse,
    EmqScoreResponse,
    EmqVolatilityResponse,
    ImpactBreakdown,
    PlaybookItemResponse,
    PlaybookItemUpdate,
    TopIssue,
    VolatilityDataPoint,
)
from app.schemas.response import APIResponse
from app.services.emq_service import EmqAdminService, EmqService

router = APIRouter(
    tags=["EMQ v2"],
    dependencies=[Depends(get_current_user)],
)


# =============================================================================
# Helper Functions
# =============================================================================
def validate_tenant_access(request: Request, tenant_id: int) -> None:
    """Validate that the request has access to the specified tenant."""
    # Superadmins operate across all tenants (TenantMiddleware flags them).
    # They may still carry their own tenant_id, so check the role explicitly
    # rather than relying on an absent tenant context.
    if getattr(request.state, "is_superadmin", False):
        return
    request_tenant_id = getattr(request.state, "tenant_id", None)
    # Allow access if no tenant context or matching tenant
    if request_tenant_id is not None and request_tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")


def parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse date string to date object."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid date format. Use YYYY-MM-DD."
        )


# =============================================================================
# Tenant-Scoped Endpoints
# =============================================================================
@router.get(
    "/tenants/{tenant_id}/emq/score",
    response_model=APIResponse[EmqScoreResponse],
    summary="Get EMQ Score",
    description="Get the current EMQ score and drivers for a tenant.",
)
async def get_emq_score(
    request: Request,
    tenant_id: int,
    date: Optional[str] = Query(
        default=None,
        description="Target date in YYYY-MM-DD format",
    ),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get current EMQ score for a tenant.

    Returns:
    - score: Overall EMQ score (0-100)
    - previousScore: Previous period score for comparison
    - confidenceBand: Data quality band (reliable/directional/unsafe)
    - drivers: Individual EMQ driver components
    - lastUpdated: Timestamp of last score calculation
    """
    validate_tenant_access(request, tenant_id)

    target_date = parse_date(date)
    service = EmqService(db)
    data = await service.get_emq_score(tenant_id, target_date)

    # Convert to response schema
    drivers = [
        EmqDriver(
            name=d["name"],
            value=d["value"],
            weight=d["weight"],
            status=d["status"],
            trend=d["trend"],
        )
        for d in data["drivers"]
    ]

    response_data = EmqScoreResponse(
        score=data["score"],
        previousScore=data.get("previousScore"),
        confidenceBand=data["confidenceBand"],
        drivers=drivers,
        lastUpdated=data["lastUpdated"],
    )

    return APIResponse(success=True, data=response_data)


@router.get(
    "/tenants/{tenant_id}/emq/confidence",
    response_model=APIResponse[ConfidenceDataResponse],
    summary="Get Confidence Band Details",
    description="Get detailed confidence band information and contributing factors.",
)
async def get_confidence(
    request: Request,
    tenant_id: int,
    date: Optional[str] = Query(default=None, description="Target date"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get confidence band details for a tenant.

    Returns:
    - band: Current confidence band classification
    - score: Confidence score value
    - thresholds: Band threshold values
    - factors: Contributing factors with their status
    """
    validate_tenant_access(request, tenant_id)

    target_date = parse_date(date)
    service = EmqService(db)
    data = await service.get_confidence_data(tenant_id, target_date)

    response_data = ConfidenceDataResponse(
        band=data["band"],
        score=data["score"],
        thresholds=ConfidenceThresholds(**data["thresholds"]),
        factors=[ConfidenceFactor(**f) for f in data["factors"]],
    )

    return APIResponse(success=True, data=response_data)


# Static catalog of every possible EMQ fix, keyed by a stable item_key. The
# generated playbook selects a subset based on driver scores; persisted progress
# (status/owner) is keyed off the same item_key so updates survive across
# requests (the old implementation used a fresh uuid4 per request, which made
# items un-updatable).
PLAYBOOK_CATALOG: dict[str, dict] = {
    "enhanced_conversions": {
        "title": "Enable Enhanced Conversions",
        "description": "Implement Google Enhanced Conversions to improve match rates by 15-25%",
        "priority": "critical",
        "estimatedImpact": 8.5,
        "estimatedTime": "2-4 hours",
        "platform": "Google Ads",
        "actionUrl": "https://ads.google.com/settings/conversions",
    },
    "meta_capi_dedup": {
        "title": "Fix Meta CAPI Event Deduplication",
        "description": "Configure event_id parameter to prevent duplicate conversions",
        "priority": "high",
        "estimatedImpact": 5.2,
        "estimatedTime": "1-2 hours",
        "platform": "Meta",
        "actionUrl": None,
    },
    "consent_mode_v2": {
        "title": "Update Consent Mode v2",
        "description": "Migrate to Consent Mode v2 for improved EU data quality",
        "priority": "high",
        "estimatedImpact": 4.8,
        "estimatedTime": "4-6 hours",
        "platform": None,
        "actionUrl": None,
    },
    "reduce_conversion_latency": {
        "title": "Reduce Conversion Latency",
        "description": "Optimize server-side event processing to reduce latency below 1 hour",
        "priority": "medium",
        "estimatedImpact": 3.1,
        "estimatedTime": "1-2 days",
        "platform": None,
        "actionUrl": None,
    },
    "tiktok_events_api": {
        "title": "Add TikTok Events API",
        "description": "Implement server-side tracking for TikTok campaigns",
        "priority": "low",
        "estimatedImpact": 2.0,
        "estimatedTime": "3-4 hours",
        "platform": "TikTok",
        "actionUrl": None,
    },
}


def _build_playbook_item(
    item_key: str, status: str = "pending", owner: Optional[str] = None
) -> PlaybookItemResponse:
    """Build a playbook item response from the static catalog + persisted state."""
    meta = PLAYBOOK_CATALOG[item_key]
    return PlaybookItemResponse(
        id=item_key,
        title=meta["title"],
        description=meta["description"],
        priority=meta["priority"],
        owner=owner,
        estimatedImpact=meta["estimatedImpact"],
        estimatedTime=meta["estimatedTime"],
        platform=meta["platform"],
        status=status,
        actionUrl=meta["actionUrl"],
    )


@router.get(
    "/tenants/{tenant_id}/emq/playbook",
    response_model=APIResponse[List[PlaybookItemResponse]],
    summary="Get Fix Playbook",
    description="Get prioritized list of recommended fixes to improve EMQ score.",
)
async def get_playbook(
    request: Request,
    tenant_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get fix playbook items for a tenant.

    Returns a prioritized list of recommended actions to improve EMQ score,
    including estimated impact and implementation time.
    """
    validate_tenant_access(request, tenant_id)

    # Get EMQ data to generate relevant playbook
    service = EmqService(db)
    emq_data = await service.get_emq_score(tenant_id)

    # Select which fixes apply based on driver scores (stable item_keys).
    drivers = {d["name"]: d for d in emq_data["drivers"]}
    active_keys: List[str] = []
    if drivers.get("Event Match Rate", {}).get("value", 100) < 85:
        active_keys.append("enhanced_conversions")
        active_keys.append("meta_capi_dedup")
    if drivers.get("Pixel Coverage", {}).get("value", 100) < 90:
        active_keys.append("consent_mode_v2")
    if drivers.get("Conversion Latency", {}).get("value", 100) < 70:
        active_keys.append("reduce_conversion_latency")
    if emq_data["score"] < 95:
        active_keys.append("tiktok_events_api")

    # Merge persisted user state (status/owner) onto the generated items.
    from sqlalchemy import select

    from app.models.emq_playbook import EmqPlaybookItemState

    state_rows = await db.execute(
        select(EmqPlaybookItemState).where(EmqPlaybookItemState.tenant_id == tenant_id)
    )
    state_by_key = {s.item_key: s for s in state_rows.scalars().all()}

    playbook_items = [
        _build_playbook_item(
            key,
            status=state_by_key[key].status if key in state_by_key else "pending",
            owner=state_by_key[key].owner if key in state_by_key else None,
        )
        for key in active_keys
    ]

    # Sort by priority
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    playbook_items.sort(key=lambda x: priority_order.get(x.priority, 99))

    return APIResponse(success=True, data=playbook_items)


@router.patch(
    "/tenants/{tenant_id}/emq/playbook/{item_id}",
    response_model=APIResponse[PlaybookItemResponse],
    summary="Update Playbook Item",
    description="Update the status or owner of a playbook item.",
)
async def update_playbook_item(
    request: Request,
    tenant_id: int,
    item_id: str,
    updates: PlaybookItemUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Update a playbook item's status or owner.

    Used to track progress on EMQ improvement tasks.
    """
    validate_tenant_access(request, tenant_id)

    if item_id not in PLAYBOOK_CATALOG:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown playbook item: {item_id}",
        )

    from sqlalchemy import select

    from app.models.emq_playbook import EmqPlaybookItemState

    result = await db.execute(
        select(EmqPlaybookItemState).where(
            EmqPlaybookItemState.tenant_id == tenant_id,
            EmqPlaybookItemState.item_key == item_id,
        )
    )
    state = result.scalar_one_or_none()
    if state is None:
        state = EmqPlaybookItemState(
            tenant_id=tenant_id, item_key=item_id, status="pending"
        )
        db.add(state)

    if updates.status is not None:
        state.status = updates.status
    if updates.owner is not None:
        state.owner = updates.owner

    await db.commit()
    await db.refresh(state)

    return APIResponse(
        success=True,
        data=_build_playbook_item(item_id, status=state.status, owner=state.owner),
        message="Playbook item updated",
    )


@router.get(
    "/tenants/{tenant_id}/emq/incidents",
    response_model=APIResponse[List[EmqIncidentResponse]],
    summary="Get Incident Timeline",
    description="Get EMQ-related incidents and events within a date range.",
)
async def get_incidents(
    request: Request,
    tenant_id: int,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get incident timeline for a tenant.

    Returns EMQ-related incidents including:
    - Signal degradations
    - Recovery events
    - Platform outages
    - Configuration changes
    """
    validate_tenant_access(request, tenant_id)

    start = parse_date(start_date)
    end = parse_date(end_date)

    if not start or not end:
        raise HTTPException(
            status_code=400, detail="Both start_date and end_date are required"
        )

    service = EmqService(db)
    incidents_data = await service.get_incidents(tenant_id, start, end)

    incidents = [EmqIncidentResponse(**i) for i in incidents_data]

    return APIResponse(success=True, data=incidents)


@router.get(
    "/tenants/{tenant_id}/emq/impact",
    response_model=APIResponse[EmqImpactResponse],
    summary="Get ROAS Impact",
    description="Get estimated ROAS impact due to EMQ issues.",
)
async def get_impact(
    request: Request,
    tenant_id: int,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get ROAS impact estimate for a tenant.

    Calculates the estimated revenue impact of EMQ issues by comparing
    actual ROAS to expected ROAS based on historical data quality.
    """
    validate_tenant_access(request, tenant_id)

    start = parse_date(start_date)
    end = parse_date(end_date)

    if not start or not end:
        raise HTTPException(
            status_code=400, detail="Both start_date and end_date are required"
        )

    service = EmqService(db)
    impact_data = await service.get_impact(tenant_id, start, end)

    response_data = EmqImpactResponse(
        totalImpact=impact_data["totalImpact"],
        currency=impact_data["currency"],
        breakdown=[ImpactBreakdown(**b) for b in impact_data["breakdown"]],
    )

    return APIResponse(success=True, data=response_data)


@router.get(
    "/tenants/{tenant_id}/emq/volatility",
    response_model=APIResponse[EmqVolatilityResponse],
    summary="Get Signal Volatility",
    description="Get signal volatility index and trend data.",
)
async def get_volatility(
    request: Request,
    tenant_id: int,
    weeks: int = Query(default=8, ge=1, le=52, description="Number of weeks of data"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get signal volatility data for a tenant.

    Returns:
    - svi: Signal Volatility Index (lower is better)
    - trend: Volatility trend direction
    - weeklyData: Historical volatility data points
    """
    validate_tenant_access(request, tenant_id)

    service = EmqService(db)
    volatility_data = await service.get_volatility(tenant_id, weeks)

    response_data = EmqVolatilityResponse(
        svi=volatility_data["svi"],
        trend=volatility_data["trend"],
        weeklyData=[VolatilityDataPoint(**d) for d in volatility_data["weeklyData"]],
    )

    return APIResponse(success=True, data=response_data)


@router.get(
    "/tenants/{tenant_id}/emq/autopilot-state",
    response_model=APIResponse[AutopilotStateResponse],
    summary="Get Autopilot State",
    description="Get current autopilot mode and restrictions based on EMQ.",
)
async def get_autopilot_state(
    request: Request,
    tenant_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get autopilot state for a tenant.

    Autopilot mode is determined by EMQ score:
    - normal: Full automation allowed (EMQ >= 80)
    - limited: Conservative automation (EMQ 60-79)
    - cuts_only: Only budget cuts allowed (EMQ 40-59)
    - frozen: No automation allowed (EMQ < 40)
    """
    validate_tenant_access(request, tenant_id)

    service = EmqService(db)
    state_data = await service.get_autopilot_state(tenant_id)

    response_data = AutopilotStateResponse(
        mode=state_data["mode"],
        reason=state_data["reason"],
        budgetAtRisk=state_data["budgetAtRisk"],
        allowedActions=state_data["allowedActions"],
        restrictedActions=state_data["restrictedActions"],
    )

    return APIResponse(success=True, data=response_data)


@router.put(
    "/tenants/{tenant_id}/emq/autopilot-mode",
    response_model=APIResponse[AutopilotStateResponse],
    summary="Update Autopilot Mode",
    description="Manually override autopilot mode (requires elevated permissions).",
)
async def update_autopilot_mode(
    request: Request,
    tenant_id: int,
    update: AutopilotModeUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Update autopilot mode for a tenant.

    Allows manual override of the autopilot mode. Useful when:
    - Temporarily disabling automation for testing
    - Emergency freezes during platform issues
    - Gradual rollback after EMQ improvements
    """
    validate_tenant_access(request, tenant_id)

    # Map modes to allowed/restricted actions
    mode_config = {
        "normal": {
            "allowed": [
                "pause_underperforming",
                "reduce_budget",
                "increase_budget",
                "update_audiences",
                "launch_new_campaigns",
                "expand_targeting",
            ],
            "restricted": [],
        },
        "limited": {
            "allowed": [
                "pause_underperforming",
                "reduce_budget",
                "update_audiences",
            ],
            "restricted": [
                "increase_budget",
                "launch_new_campaigns",
                "expand_targeting",
            ],
        },
        "cuts_only": {
            "allowed": [
                "pause_underperforming",
                "reduce_budget",
            ],
            "restricted": [
                "update_audiences",
                "increase_budget",
                "launch_new_campaigns",
                "expand_targeting",
            ],
        },
        "frozen": {
            "allowed": [],
            "restricted": [
                "pause_underperforming",
                "reduce_budget",
                "update_audiences",
                "increase_budget",
                "launch_new_campaigns",
                "expand_targeting",
            ],
        },
    }

    config = mode_config.get(update.mode)
    if config is None:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {update.mode}")

    # Query actual tenant spend for budget-at-risk calculation
    from sqlalchemy import func, select

    from app.models import Campaign

    spend_result = await db.execute(
        select(func.coalesce(func.sum(Campaign.total_spend_cents), 0)).where(
            Campaign.tenant_id == tenant_id,
            Campaign.status == "active",
        )
    )
    total_spend_cents = spend_result.scalar() or 0
    budget_at_risk = round(total_spend_cents / 100, 2)

    response_data = AutopilotStateResponse(
        mode=update.mode,
        reason=update.reason or f"Manual override to {update.mode} mode",
        budgetAtRisk=budget_at_risk,
        allowedActions=config["allowed"],
        restrictedActions=config["restricted"],
    )

    return APIResponse(success=True, data=response_data)


# =============================================================================
# Super Admin Endpoints
# =============================================================================
@router.get(
    "/emq/benchmarks",
    response_model=APIResponse[List[EmqBenchmarkResponse]],
    summary="Get EMQ Benchmarks",
    description="Get platform-wide EMQ benchmarks (super admin only).",
)
async def get_benchmarks(
    request: Request,
    date: Optional[str] = Query(default=None, description="Target date"),
    platform: Optional[str] = Query(default=None, description="Filter by platform"),
    db: AsyncSession = Depends(get_async_session),
    _superadmin=Depends(require_superadmin()),
):
    """
    Get EMQ benchmarks across all tenants.

    Returns percentile distributions (p25, p50, p75) for EMQ scores,
    optionally filtered by platform. Super admin only.
    """
    target_date = parse_date(date)
    service = EmqAdminService(db)
    benchmarks_data = await service.get_benchmarks(target_date, platform)

    benchmarks = [EmqBenchmarkResponse(**b) for b in benchmarks_data]

    return APIResponse(success=True, data=benchmarks)


@router.get(
    "/emq/portfolio",
    response_model=APIResponse[EmqPortfolioResponse],
    summary="Get Portfolio Overview",
    description="Get portfolio-wide EMQ overview (super admin only).",
)
async def get_portfolio(
    request: Request,
    date: Optional[str] = Query(default=None, description="Target date"),
    db: AsyncSession = Depends(get_async_session),
    _superadmin=Depends(require_superadmin()),
):
    """
    Get portfolio overview for super admin.

    Returns aggregate EMQ metrics across all tenants including:
    - Distribution by confidence band
    - Total at-risk budget
    - Average EMQ score
    - Top issues affecting multiple tenants
    """
    target_date = parse_date(date)
    service = EmqAdminService(db)
    portfolio_data = await service.get_portfolio(target_date)

    response_data = EmqPortfolioResponse(
        totalTenants=portfolio_data["totalTenants"],
        byBand=BandDistribution(**portfolio_data["byBand"]),
        atRiskBudget=portfolio_data["atRiskBudget"],
        avgScore=portfolio_data["avgScore"],
        topIssues=[TopIssue(**i) for i in portfolio_data["topIssues"]],
    )

    return APIResponse(success=True, data=response_data)
