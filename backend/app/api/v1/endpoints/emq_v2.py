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
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session
from app.schemas.response import APIResponse
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


router = APIRouter(prefix="/emq/v2", tags=["EMQ v2"])


# =============================================================================
# Helper Functions
# =============================================================================
def validate_tenant_access(request: Request, tenant_id: int) -> None:
    """Validate that the request has access to the specified tenant."""
    request_tenant_id = getattr(request.state, "tenant_id", None)
    # Allow access if no tenant context (e.g., super admin) or matching tenant
    if request_tenant_id is not None and request_tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")


def generate_mock_drivers() -> List[EmqDriver]:
    """Generate mock EMQ drivers for demo purposes."""
    return [
        EmqDriver(
            name="Event Match Rate",
            value=87.5,
            weight=0.30,
            status="good",
            trend="up",
        ),
        EmqDriver(
            name="Pixel Coverage",
            value=92.3,
            weight=0.25,
            status="good",
            trend="flat",
        ),
        EmqDriver(
            name="Conversion Latency",
            value=68.2,
            weight=0.20,
            status="warning",
            trend="down",
        ),
        EmqDriver(
            name="Attribution Accuracy",
            value=78.9,
            weight=0.15,
            status="good",
            trend="up",
        ),
        EmqDriver(
            name="Data Freshness",
            value=95.1,
            weight=0.10,
            status="good",
            trend="flat",
        ),
    ]


# =============================================================================
# Tenant-Scoped Endpoints
# =============================================================================
@router.get(
    "/tenants/{tenant_id}/score",
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

    # Mock data - replace with actual service call
    drivers = generate_mock_drivers()
    score = sum(d.value * d.weight for d in drivers)

    response_data = EmqScoreResponse(
        score=round(score, 1),
        previousScore=round(score - 2.3, 1),
        confidenceBand="reliable" if score >= 80 else "directional" if score >= 60 else "unsafe",
        drivers=drivers,
        lastUpdated=datetime.utcnow().isoformat() + "Z",
    )

    return APIResponse(success=True, data=response_data)


@router.get(
    "/tenants/{tenant_id}/confidence",
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

    # Mock data
    response_data = ConfidenceDataResponse(
        band="reliable",
        score=85.2,
        thresholds=ConfidenceThresholds(reliable=80.0, directional=60.0),
        factors=[
            ConfidenceFactor(name="Event Coverage", contribution=25.5, status="positive"),
            ConfidenceFactor(name="Match Rate", contribution=22.3, status="positive"),
            ConfidenceFactor(name="Data Latency", contribution=18.7, status="neutral"),
            ConfidenceFactor(name="Attribution Window", contribution=12.4, status="positive"),
            ConfidenceFactor(name="Signal Loss", contribution=-6.3, status="negative"),
        ],
    )

    return APIResponse(success=True, data=response_data)


@router.get(
    "/tenants/{tenant_id}/playbook",
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

    # Mock data
    playbook_items = [
        PlaybookItemResponse(
            id=str(uuid.uuid4()),
            title="Enable Enhanced Conversions",
            description="Implement Google Enhanced Conversions to improve match rates by 15-25%",
            priority="critical",
            owner=None,
            estimatedImpact=8.5,
            estimatedTime="2-4 hours",
            platform="Google Ads",
            status="pending",
            actionUrl="https://ads.google.com/settings/conversions",
        ),
        PlaybookItemResponse(
            id=str(uuid.uuid4()),
            title="Fix Meta CAPI Event Deduplication",
            description="Configure event_id parameter to prevent duplicate conversions",
            priority="high",
            owner=None,
            estimatedImpact=5.2,
            estimatedTime="1-2 hours",
            platform="Meta",
            status="pending",
            actionUrl=None,
        ),
        PlaybookItemResponse(
            id=str(uuid.uuid4()),
            title="Update Consent Mode v2",
            description="Migrate to Consent Mode v2 for improved EU data quality",
            priority="high",
            owner=None,
            estimatedImpact=4.8,
            estimatedTime="4-6 hours",
            platform=None,
            status="in_progress",
            actionUrl=None,
        ),
        PlaybookItemResponse(
            id=str(uuid.uuid4()),
            title="Reduce Conversion Latency",
            description="Optimize server-side event processing to reduce latency below 1 hour",
            priority="medium",
            owner=None,
            estimatedImpact=3.1,
            estimatedTime="1-2 days",
            platform=None,
            status="pending",
            actionUrl=None,
        ),
        PlaybookItemResponse(
            id=str(uuid.uuid4()),
            title="Add TikTok Events API",
            description="Implement server-side tracking for TikTok campaigns",
            priority="low",
            owner=None,
            estimatedImpact=2.0,
            estimatedTime="3-4 hours",
            platform="TikTok",
            status="pending",
            actionUrl=None,
        ),
    ]

    return APIResponse(success=True, data=playbook_items)


@router.patch(
    "/tenants/{tenant_id}/playbook/{item_id}",
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

    # Mock response - in production, fetch and update from database
    response_data = PlaybookItemResponse(
        id=item_id,
        title="Enable Enhanced Conversions",
        description="Implement Google Enhanced Conversions to improve match rates",
        priority="critical",
        owner=updates.owner,
        estimatedImpact=8.5,
        estimatedTime="2-4 hours",
        platform="Google Ads",
        status=updates.status or "pending",
        actionUrl="https://ads.google.com/settings/conversions",
    )

    return APIResponse(success=True, data=response_data)


@router.get(
    "/tenants/{tenant_id}/incidents",
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

    # Validate date parameters
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD.",
        )

    # Mock data
    base_time = datetime.utcnow() - timedelta(days=5)
    incidents = [
        EmqIncidentResponse(
            id=str(uuid.uuid4()),
            type="incident_opened",
            title="Meta Pixel Signal Drop",
            description="Detected 40% drop in Meta pixel events due to iOS 18 update",
            timestamp=(base_time).isoformat() + "Z",
            platform="Meta",
            severity="high",
            recoveryHours=None,
            emqImpact=-12.5,
        ),
        EmqIncidentResponse(
            id=str(uuid.uuid4()),
            type="degradation",
            title="Google Enhanced Conversions Latency",
            description="Conversion data delayed by 4+ hours",
            timestamp=(base_time + timedelta(days=1)).isoformat() + "Z",
            platform="Google Ads",
            severity="medium",
            recoveryHours=None,
            emqImpact=-5.2,
        ),
        EmqIncidentResponse(
            id=str(uuid.uuid4()),
            type="recovery",
            title="Google Enhanced Conversions Recovered",
            description="Latency returned to normal levels",
            timestamp=(base_time + timedelta(days=2)).isoformat() + "Z",
            platform="Google Ads",
            severity="low",
            recoveryHours=18.5,
            emqImpact=5.2,
        ),
        EmqIncidentResponse(
            id=str(uuid.uuid4()),
            type="incident_closed",
            title="Meta Pixel Signal Restored",
            description="Implemented CAPI fallback to restore signal coverage",
            timestamp=(base_time + timedelta(days=3)).isoformat() + "Z",
            platform="Meta",
            severity="low",
            recoveryHours=72.0,
            emqImpact=10.8,
        ),
    ]

    return APIResponse(success=True, data=incidents)


@router.get(
    "/tenants/{tenant_id}/impact",
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

    # Mock data
    response_data = EmqImpactResponse(
        totalImpact=24350.00,
        currency="USD",
        breakdown=[
            ImpactBreakdown(
                platform="Meta",
                actualRoas=2.8,
                estimatedRoas=3.4,
                confidence=0.85,
                revenueImpact=15200.00,
            ),
            ImpactBreakdown(
                platform="Google Ads",
                actualRoas=3.2,
                estimatedRoas=3.5,
                confidence=0.92,
                revenueImpact=6850.00,
            ),
            ImpactBreakdown(
                platform="TikTok",
                actualRoas=1.9,
                estimatedRoas=2.3,
                confidence=0.72,
                revenueImpact=2300.00,
            ),
        ],
    )

    return APIResponse(success=True, data=response_data)


@router.get(
    "/tenants/{tenant_id}/volatility",
    response_model=APIResponse[EmqVolatilityResponse],
    summary="Get Signal Volatility",
    description="Get signal volatility index and trend data.",
)
async def get_volatility(
    request: Request,
    tenant_id: int,
    week: Optional[str] = Query(default=None, description="Week identifier"),
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

    # Generate mock weekly data
    today = date.today()
    weekly_data = []
    for i in range(8):
        week_date = today - timedelta(weeks=7-i)
        weekly_data.append(
            VolatilityDataPoint(
                date=week_date.isoformat(),
                value=round(12.5 + (i * 0.8) - (i % 3) * 2.1, 1),
            )
        )

    response_data = EmqVolatilityResponse(
        svi=15.3,
        trend="decreasing",
        weeklyData=weekly_data,
    )

    return APIResponse(success=True, data=response_data)


@router.get(
    "/tenants/{tenant_id}/autopilot",
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

    # Mock data - would be calculated from actual EMQ score
    response_data = AutopilotStateResponse(
        mode="limited",
        reason="EMQ score below reliable threshold (78.5 < 80)",
        budgetAtRisk=45000.00,
        allowedActions=[
            "pause_underperforming",
            "reduce_budget",
            "update_audiences",
        ],
        restrictedActions=[
            "increase_budget",
            "launch_new_campaigns",
            "expand_targeting",
        ],
    )

    return APIResponse(success=True, data=response_data)


@router.put(
    "/tenants/{tenant_id}/autopilot",
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

    config = mode_config[update.mode]

    response_data = AutopilotStateResponse(
        mode=update.mode,
        reason=update.reason or f"Manual override to {update.mode} mode",
        budgetAtRisk=45000.00,
        allowedActions=config["allowed"],
        restrictedActions=config["restricted"],
    )

    return APIResponse(success=True, data=response_data)


# =============================================================================
# Super Admin Endpoints
# =============================================================================
@router.get(
    "/benchmarks",
    response_model=APIResponse[List[EmqBenchmarkResponse]],
    summary="Get EMQ Benchmarks",
    description="Get platform-wide EMQ benchmarks (super admin only).",
)
async def get_benchmarks(
    request: Request,
    date: Optional[str] = Query(default=None, description="Target date"),
    platform: Optional[str] = Query(default=None, description="Filter by platform"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get EMQ benchmarks across all tenants.

    Returns percentile distributions (p25, p50, p75) for EMQ scores,
    optionally filtered by platform. Super admin only.
    """
    # In production, verify super admin permissions

    benchmarks = [
        EmqBenchmarkResponse(
            platform="Meta",
            p25=62.5,
            p50=74.8,
            p75=86.2,
            tenantScore=78.5,
            percentile=58.3,
        ),
        EmqBenchmarkResponse(
            platform="Google Ads",
            p25=68.2,
            p50=79.5,
            p75=89.1,
            tenantScore=82.3,
            percentile=62.7,
        ),
        EmqBenchmarkResponse(
            platform="TikTok",
            p25=55.8,
            p50=67.2,
            p75=78.9,
            tenantScore=71.2,
            percentile=55.1,
        ),
        EmqBenchmarkResponse(
            platform="LinkedIn",
            p25=71.5,
            p50=81.2,
            p75=90.5,
            tenantScore=84.8,
            percentile=68.9,
        ),
    ]

    # Filter by platform if specified
    if platform:
        benchmarks = [b for b in benchmarks if b.platform.lower() == platform.lower()]

    return APIResponse(success=True, data=benchmarks)


@router.get(
    "/portfolio",
    response_model=APIResponse[EmqPortfolioResponse],
    summary="Get Portfolio Overview",
    description="Get portfolio-wide EMQ overview (super admin only).",
)
async def get_portfolio(
    request: Request,
    date: Optional[str] = Query(default=None, description="Target date"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get portfolio overview for super admin.

    Returns aggregate EMQ metrics across all tenants including:
    - Distribution by confidence band
    - Total at-risk budget
    - Average EMQ score
    - Top issues affecting multiple tenants
    """
    # In production, verify super admin permissions

    response_data = EmqPortfolioResponse(
        totalTenants=156,
        byBand=BandDistribution(
            reliable=89,
            directional=52,
            unsafe=15,
        ),
        atRiskBudget=2450000.00,
        avgScore=76.8,
        topIssues=[
            TopIssue(driver="iOS Signal Loss", affectedTenants=78),
            TopIssue(driver="Consent Mode v2 Migration", affectedTenants=45),
            TopIssue(driver="CAPI Implementation", affectedTenants=38),
            TopIssue(driver="Conversion Latency", affectedTenants=29),
            TopIssue(driver="Event Deduplication", affectedTenants=21),
        ],
    )

    return APIResponse(success=True, data=response_data)
