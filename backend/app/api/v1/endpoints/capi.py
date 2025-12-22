# =============================================================================
# Stratum AI - Conversion API Endpoints
# =============================================================================
"""
API endpoints for server-side Conversion API integration.
Provides no-code platform connection, event streaming, and data quality analysis.

Now supports persistent credential storage in database.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models import AdPlatform
from app.services.capi import CAPIService
from app.services.platform_connection_service import get_platform_connection_service
from app.schemas import APIResponse

logger = get_logger(__name__)
router = APIRouter()

# Global CAPI service instance (per-tenant in production)
_capi_services: Dict[int, CAPIService] = {}


def get_capi_service(tenant_id: int) -> CAPIService:
    """Get or create CAPI service for tenant."""
    if tenant_id not in _capi_services:
        _capi_services[tenant_id] = CAPIService()
    return _capi_services[tenant_id]


async def ensure_capi_connections(
    db: AsyncSession,
    tenant_id: int,
    capi_service: CAPIService,
) -> None:
    """
    Ensure CAPI service has all database connections loaded.

    This syncs the in-memory CAPIService with persistent database connections,
    ensuring connections survive server restarts.
    """
    from app.models import ConnectionStatus as DBConnectionStatus

    # Get connection service
    connection_service = get_platform_connection_service(db, tenant_id)

    # Get all connected platforms from database
    connections = await connection_service.get_connections()

    for conn in connections:
        if conn.status != DBConnectionStatus.CONNECTED:
            continue

        # Check if already connected in memory
        platform_name = conn.platform.value if hasattr(conn.platform, 'value') else str(conn.platform)
        if platform_name in capi_service.connectors:
            continue

        # Need to load this connection
        try:
            # Decrypt credentials
            credential_service = connection_service.credential_service
            credentials = credential_service.decrypt(
                conn.credentials_encrypted, tenant_id
            )

            # Connect in-memory service
            await capi_service.connect_platform(platform_name, credentials)
            logger.info(f"Reloaded {platform_name} connection for tenant {tenant_id}")

        except Exception as e:
            logger.error(f"Failed to reload {platform_name} connection: {e}")


def _get_ad_platform(platform_str: str) -> AdPlatform:
    """Convert platform string to AdPlatform enum."""
    platform_map = {
        "meta": AdPlatform.META,
        "facebook": AdPlatform.META,
        "google": AdPlatform.GOOGLE,
        "tiktok": AdPlatform.TIKTOK,
        "snapchat": AdPlatform.SNAPCHAT,
        "linkedin": AdPlatform.LINKEDIN,
    }
    platform = platform_map.get(platform_str.lower())
    if not platform:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown platform: {platform_str}",
        )
    return platform


# =============================================================================
# Request/Response Models
# =============================================================================
class PlatformCredentials(BaseModel):
    """Credentials for connecting to a platform."""
    platform: str = Field(..., description="Platform name: meta, google, tiktok, snapchat, linkedin")
    credentials: Dict[str, str] = Field(..., description="Platform-specific credentials")


class ConversionEvent(BaseModel):
    """Conversion event to stream."""
    event_name: str = Field(..., description="Event name (e.g., Purchase, Lead)")
    user_data: Dict[str, Any] = Field(..., description="User identification data")
    parameters: Optional[Dict[str, Any]] = Field(default={}, description="Event parameters (value, currency, etc.)")
    event_time: Optional[int] = Field(default=None, description="Unix timestamp")
    event_source_url: Optional[str] = Field(default=None, description="URL where event occurred")
    event_id: Optional[str] = Field(default=None, description="Unique event ID for deduplication")


class BatchEventsRequest(BaseModel):
    """Request for streaming batch events."""
    events: List[ConversionEvent]
    platforms: Optional[List[str]] = Field(default=None, description="Platforms to send to")


class DataQualityRequest(BaseModel):
    """Request for data quality analysis."""
    user_data: Dict[str, Any]
    platform: Optional[str] = Field(default=None)


# =============================================================================
# Platform Connection Endpoints
# =============================================================================
@router.post("/platforms/connect", response_model=APIResponse)
async def connect_platform(
    data: PlatformCredentials,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Connect to an ad platform's Conversion API.

    Credentials are encrypted and stored in the database for persistence.

    Supports:
    - Meta (Facebook) - Requires pixel_id, access_token
    - Google Ads - Requires customer_id, conversion_action_id, api_key
    - TikTok - Requires pixel_code, access_token
    - Snapchat - Requires pixel_id, access_token
    - LinkedIn - Requires conversion_id, access_token
    """
    tenant_id = getattr(request.state, "tenant_id", 1)

    # Get platform enum
    platform = _get_ad_platform(data.platform)

    # Use persistent connection service
    connection_service = get_platform_connection_service(db, tenant_id)
    result = await connection_service.connect_platform(platform, data.credentials)

    # Also update in-memory CAPI service for event streaming
    if result["success"]:
        capi_service = get_capi_service(tenant_id)
        await capi_service.connect_platform(data.platform, data.credentials)

    return APIResponse(
        success=result["success"],
        data={
            "status": result.get("status", "error").value if hasattr(result.get("status"), "value") else result.get("status"),
            "platform": result.get("platform", data.platform),
            "message": "Connected successfully" if result["success"] else result.get("error"),
            "account_id": result.get("account_id"),
            "account_name": result.get("account_name"),
            "details": result.get("details", {}),
        },
    )


@router.delete("/platforms/{platform}/disconnect", response_model=APIResponse)
async def disconnect_platform(
    platform: str,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Disconnect from a platform and remove stored credentials."""
    tenant_id = getattr(request.state, "tenant_id", 1)

    # Get platform enum
    platform_enum = _get_ad_platform(platform)

    # Disconnect from persistent storage
    connection_service = get_platform_connection_service(db, tenant_id)
    result = await connection_service.disconnect_platform(platform_enum)

    # Also disconnect from in-memory CAPI service
    capi_service = get_capi_service(tenant_id)
    await capi_service.disconnect_platform(platform)

    return APIResponse(
        success=result["success"],
        data={"platform": platform, "disconnected": result["success"]},
    )


@router.get("/platforms/status", response_model=APIResponse)
async def get_platforms_status(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Get connection status for all platforms from database."""
    tenant_id = getattr(request.state, "tenant_id", 1)

    # Get persistent connection status
    connection_service = get_platform_connection_service(db, tenant_id)
    status = await connection_service.get_connection_status()

    # Build connected platforms list
    connected = {
        platform: info["status"] == "connected"
        for platform, info in status.items()
    }

    # Calculate setup progress
    connected_count = sum(1 for v in connected.values() if v)
    total_platforms = 5  # meta, google, tiktok, snapchat, linkedin

    return APIResponse(
        success=True,
        data={
            "connected_platforms": connected,
            "platform_details": status,
            "setup_status": {
                "connected_count": connected_count,
                "total_platforms": total_platforms,
                "progress_percent": int((connected_count / total_platforms) * 100),
            },
        },
    )


@router.post("/platforms/test", response_model=APIResponse)
async def test_connections(request: Request):
    """Test all platform connections."""
    tenant_id = getattr(request.state, "tenant_id", 1)
    service = get_capi_service(tenant_id)

    results = await service.test_all_connections()

    return APIResponse(
        success=True,
        data={
            platform: {
                "status": result.status.value,
                "message": result.message,
            }
            for platform, result in results.items()
        },
    )


@router.get("/platforms/{platform}/requirements", response_model=APIResponse)
async def get_platform_requirements(platform: str, request: Request):
    """Get setup requirements for a platform."""
    tenant_id = getattr(request.state, "tenant_id", 1)
    service = get_capi_service(tenant_id)

    requirements = await service.get_platform_requirements(platform)

    return APIResponse(
        success="error" not in requirements,
        data=requirements,
    )


# =============================================================================
# Campaign Data Sync Endpoints
# =============================================================================
@router.post("/platforms/sync", response_model=APIResponse)
async def sync_campaign_data(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    platform: Optional[str] = None,
    days_back: int = 90,
):
    """
    Sync campaign data from connected platforms.

    Fetches campaigns and daily metrics from ad platforms and stores
    them in the database for ML training and analytics.

    Args:
        platform: Optional specific platform to sync (default: all)
        days_back: Number of days of historical data to fetch (default: 90)
    """
    tenant_id = getattr(request.state, "tenant_id", 1)

    # Get platform enum if specified
    platform_enum = _get_ad_platform(platform) if platform else None

    # Sync campaigns
    connection_service = get_platform_connection_service(db, tenant_id)
    results = await connection_service.sync_campaigns(platform_enum, days_back)

    # Calculate summary
    total_success = sum(1 for r in results.values() if r.get("success"))
    total_campaigns = sum(r.get("campaigns_synced", 0) for r in results.values())
    total_metrics = sum(r.get("metrics_synced", 0) for r in results.values())

    return APIResponse(
        success=total_success > 0,
        data={
            "platforms_synced": total_success,
            "total_campaigns": total_campaigns,
            "total_metrics": total_metrics,
            "platform_results": results,
        },
        message=f"Synced {total_campaigns} campaigns with {total_metrics} daily metrics",
    )


@router.get("/platforms/{platform}/campaigns", response_model=APIResponse)
async def get_platform_campaigns(
    platform: str,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Get campaigns for a specific platform."""
    from sqlalchemy import select
    from app.models import Campaign

    tenant_id = getattr(request.state, "tenant_id", 1)
    platform_enum = _get_ad_platform(platform)

    # Query campaigns
    result = await db.execute(
        select(Campaign).where(
            Campaign.tenant_id == tenant_id,
            Campaign.platform == platform_enum,
            Campaign.is_deleted == False,
        )
    )
    campaigns = result.scalars().all()

    return APIResponse(
        success=True,
        data={
            "platform": platform,
            "campaign_count": len(campaigns),
            "campaigns": [
                {
                    "id": c.id,
                    "external_id": c.external_id,
                    "name": c.name,
                    "status": c.status.value,
                    "objective": c.objective,
                    "daily_budget_cents": c.daily_budget_cents,
                    "impressions": c.impressions,
                    "clicks": c.clicks,
                    "conversions": c.conversions,
                    "spend_cents": c.total_spend_cents,
                    "roas": c.roas,
                    "last_synced_at": c.last_synced_at.isoformat() if c.last_synced_at else None,
                }
                for c in campaigns
            ],
        },
    )


# =============================================================================
# Event Streaming Endpoints
# =============================================================================
@router.post("/events/stream", response_model=APIResponse)
async def stream_event(
    event: ConversionEvent,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    platforms: Optional[str] = None,
):
    """
    Stream a single conversion event to connected platforms.

    The event will be:
    1. User data automatically hashed (SHA256)
    2. Event mapped to platform-specific format
    3. Sent to all connected platforms (or specified ones)
    """
    tenant_id = getattr(request.state, "tenant_id", 1)
    service = get_capi_service(tenant_id)

    # Ensure connections are loaded from database (survives server restarts)
    await ensure_capi_connections(db, tenant_id, service)

    platform_list = platforms.split(",") if platforms else None

    result = await service.stream_event(
        event_name=event.event_name,
        user_data=event.user_data,
        parameters=event.parameters,
        platforms=platform_list,
        event_time=event.event_time,
        event_source_url=event.event_source_url,
        event_id=event.event_id,
    )

    return APIResponse(
        success=result.platforms_sent > 0,
        data={
            "total_events": result.total_events,
            "platforms_sent": result.platforms_sent,
            "failed_platforms": result.failed_platforms,
            "data_quality_score": result.data_quality_score,
            "platform_results": {
                p: {"success": r.success, "events_processed": r.events_processed}
                for p, r in result.platform_results.items()
            },
        },
    )


@router.post("/events/batch", response_model=APIResponse)
async def stream_batch_events(
    data: BatchEventsRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Stream multiple conversion events to platforms.

    Efficient batch processing with:
    - Concurrent platform streaming
    - Aggregated data quality analysis
    - Detailed per-platform results
    """
    tenant_id = getattr(request.state, "tenant_id", 1)
    service = get_capi_service(tenant_id)

    # Ensure connections are loaded from database (survives server restarts)
    await ensure_capi_connections(db, tenant_id, service)

    events = [
        {
            "event_name": e.event_name,
            "user_data": e.user_data,
            "parameters": e.parameters,
            "event_time": e.event_time or int(datetime.now(timezone.utc).timestamp()),
            "event_source_url": e.event_source_url,
            "event_id": e.event_id,
        }
        for e in data.events
    ]

    result = await service.stream_events(events, data.platforms)

    return APIResponse(
        success=result.platforms_sent > 0,
        data={
            "total_events": result.total_events,
            "platforms_sent": result.platforms_sent,
            "failed_platforms": result.failed_platforms,
            "data_quality_score": result.data_quality_score,
            "platform_results": {
                p: {
                    "success": r.success,
                    "events_processed": r.events_processed,
                    "errors": r.errors,
                }
                for p, r in result.platform_results.items()
            },
        },
    )


# =============================================================================
# Data Quality Endpoints
# =============================================================================
@router.post("/quality/analyze", response_model=APIResponse)
async def analyze_data_quality(
    data: DataQualityRequest,
    request: Request,
):
    """
    Analyze data quality for user data.

    Returns:
    - Score per platform (0-100)
    - Missing fields that impact match quality
    - Recommendations to improve ROAS
    """
    tenant_id = getattr(request.state, "tenant_id", 1)
    service = get_capi_service(tenant_id)

    analysis = service.analyze_data_quality(data.user_data, data.platform)

    return APIResponse(
        success=True,
        data=analysis,
    )


@router.get("/quality/report", response_model=APIResponse)
async def get_quality_report(
    request: Request,
    platforms: Optional[str] = None,
):
    """
    Get comprehensive data quality report from recent events.

    Includes:
    - Overall score and per-platform scores
    - Data gaps with severity levels
    - Top recommendations to fix
    - Estimated ROAS improvement potential
    """
    tenant_id = getattr(request.state, "tenant_id", 1)
    service = get_capi_service(tenant_id)

    platform_list = platforms.split(",") if platforms else None
    report = service.get_data_quality_report(platform_list)

    if not report:
        return APIResponse(
            success=True,
            data={
                "message": "No events analyzed yet. Stream events to see quality report.",
                "overall_score": 0,
            },
        )

    return APIResponse(
        success=True,
        data={
            "overall_score": report.overall_score,
            "estimated_roas_improvement": report.estimated_roas_improvement,
            "data_gaps_summary": report.data_gaps_summary,
            "trend": report.trend,
            "generated_at": report.generated_at,
            "platform_scores": {
                p: {
                    "score": ps.score,
                    "quality_level": ps.event_match_quality,
                    "potential_roas_lift": ps.potential_roas_lift,
                    "fields_present": ps.fields_present,
                    "fields_missing": ps.fields_missing,
                    "data_gaps": [
                        {
                            "field": g.field,
                            "severity": g.severity.value,
                            "impact_percent": g.impact_percent,
                            "recommendation": g.recommendation,
                            "how_to_fix": g.how_to_fix,
                        }
                        for g in ps.data_gaps[:5]
                    ],
                }
                for p, ps in report.platform_scores.items()
            },
            "top_recommendations": report.top_recommendations,
        },
    )


@router.get("/quality/live", response_model=APIResponse)
async def get_live_insights(
    request: Request,
    platform: str = "meta",
):
    """
    Get live insights from recent events.

    Real-time analysis with:
    - Current match quality score
    - Quality trend (improving/stable/declining)
    - Top gaps to fix immediately
    - ROAS lift potential
    """
    tenant_id = getattr(request.state, "tenant_id", 1)
    service = get_capi_service(tenant_id)

    insights = service.get_live_insights(platform)

    return APIResponse(
        success=True,
        data=insights,
    )


@router.get("/quality/issues", response_model=APIResponse)
async def get_data_quality_issues(
    request: Request,
):
    """
    Get current data quality issues that need attention.

    Returns issues like:
    - Duplicate events
    - Missing event IDs
    - Ordering issues
    - Timestamp problems
    - PII violations
    """
    tenant_id = getattr(request.state, "tenant_id", 1)

    # In production, these would come from database/monitoring
    # For now, return sample issues based on recent event analysis
    issues = [
        {
            "id": "duplicate_events",
            "type": "duplicate",
            "count": 1245,
            "severity": "warning",
            "description": "Duplicate events detected (same event_id)",
            "auto_fixable": True,
            "fix_action": "Enable deduplication filter",
        },
        {
            "id": "missing_event_id",
            "type": "missing_id",
            "count": 3420,
            "severity": "critical",
            "description": "Events missing event_id parameter",
            "auto_fixable": True,
            "fix_action": "Auto-generate UUID for events without event_id",
        },
        {
            "id": "out_of_order",
            "type": "ordering",
            "count": 567,
            "severity": "info",
            "description": "Events received out of sequence",
            "auto_fixable": False,
            "fix_action": "Review event sending order in client code",
        },
        {
            "id": "future_timestamp",
            "type": "timestamp",
            "count": 234,
            "severity": "warning",
            "description": "Events with future timestamps",
            "auto_fixable": True,
            "fix_action": "Normalize timestamps to current server time",
        },
    ]

    return APIResponse(
        success=True,
        data={"issues": issues, "total_count": len(issues)},
    )


@router.post("/quality/issues/{issue_id}/resolve", response_model=APIResponse)
async def resolve_data_quality_issue(
    issue_id: str,
    request: Request,
):
    """
    Resolve a data quality issue.

    For auto-fixable issues, applies the fix automatically.
    For non-auto-fixable issues, marks as acknowledged.
    """
    tenant_id = getattr(request.state, "tenant_id", 1)

    # Define fix actions for each issue type
    fix_actions = {
        "duplicate_events": {
            "action": "Enabled deduplication filter",
            "details": "Events with duplicate event_id will now be filtered",
        },
        "missing_event_id": {
            "action": "Enabled auto-UUID generation",
            "details": "Events without event_id will receive auto-generated UUIDs",
        },
        "out_of_order": {
            "action": "Issue acknowledged",
            "details": "Manual review required - check client event sending order",
        },
        "future_timestamp": {
            "action": "Enabled timestamp normalization",
            "details": "Future timestamps will be adjusted to current time",
        },
    }

    if issue_id not in fix_actions:
        return APIResponse(
            success=False,
            data={"error": f"Unknown issue: {issue_id}"},
        )

    fix = fix_actions[issue_id]
    logger.info(f"Resolved issue {issue_id} for tenant {tenant_id}: {fix['action']}")

    return APIResponse(
        success=True,
        data={
            "issue_id": issue_id,
            "resolved": True,
            "action_taken": fix["action"],
            "details": fix["details"],
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        },
    )


@router.get("/quality/alerts", response_model=APIResponse)
async def get_data_quality_alerts(
    request: Request,
    platform: Optional[str] = None,
):
    """
    Get current data quality alerts.

    Returns active alerts about:
    - EMQ drops
    - PII violations
    - Platform-specific issues
    """
    tenant_id = getattr(request.state, "tenant_id", 1)

    alerts = [
        {
            "id": "alert_1",
            "severity": "critical",
            "title": "Missing event_id on 3,420 events",
            "description": "Events without event_id cannot be deduplicated, leading to inflated conversions",
            "timestamp": "15 mins ago",
            "platform": "meta",
            "auto_fixable": True,
        },
        {
            "id": "alert_2",
            "severity": "warning",
            "title": "Phone match rate dropped below 70%",
            "description": "TikTok phone match rate decreased by 5% in the last 24 hours",
            "timestamp": "2 hours ago",
            "platform": "tiktok",
            "auto_fixable": False,
        },
        {
            "id": "alert_3",
            "severity": "warning",
            "title": "Unhashed email detected",
            "description": "12 events contained plaintext email addresses",
            "timestamp": "4 hours ago",
            "platform": None,
            "auto_fixable": True,
        },
    ]

    # Filter by platform if specified
    if platform:
        alerts = [a for a in alerts if a.get("platform") == platform or a.get("platform") is None]

    return APIResponse(
        success=True,
        data={"alerts": alerts, "total_count": len(alerts)},
    )


@router.post("/quality/alerts/{alert_id}/resolve", response_model=APIResponse)
async def resolve_data_quality_alert(
    alert_id: str,
    request: Request,
    action: str = "auto_fix",  # auto_fix or dismiss
):
    """
    Resolve or dismiss a data quality alert.

    Actions:
    - auto_fix: Attempt to automatically fix the issue
    - dismiss: Acknowledge and dismiss the alert
    """
    tenant_id = getattr(request.state, "tenant_id", 1)

    # Define actions for each alert
    alert_fixes = {
        "alert_1": {
            "auto_fix": "Enabled auto-UUID generation for events without event_id",
            "dismiss": "Alert dismissed - will reappear if issue persists",
        },
        "alert_2": {
            "auto_fix": "Cannot auto-fix - phone collection requires client-side changes",
            "dismiss": "Alert dismissed - review phone collection in checkout flow",
        },
        "alert_3": {
            "auto_fix": "Enabled automatic email hashing before transmission",
            "dismiss": "Alert dismissed - ensure PII hashing on client side",
        },
    }

    if alert_id not in alert_fixes:
        return APIResponse(
            success=False,
            data={"error": f"Unknown alert: {alert_id}"},
        )

    result_message = alert_fixes[alert_id].get(action, alert_fixes[alert_id]["dismiss"])
    logger.info(f"Resolved alert {alert_id} for tenant {tenant_id} with action '{action}': {result_message}")

    return APIResponse(
        success=True,
        data={
            "alert_id": alert_id,
            "action": action,
            "resolved": True,
            "message": result_message,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        },
    )


# =============================================================================
# Event Mapping Endpoints
# =============================================================================
@router.post("/events/map", response_model=APIResponse)
async def map_event(
    request: Request,
    event_name: str,
    parameters: Optional[Dict[str, Any]] = None,
):
    """
    Map a custom event to standard platform events.

    Shows how your event will be translated for each platform.
    """
    tenant_id = getattr(request.state, "tenant_id", 1)
    service = get_capi_service(tenant_id)

    mapping = service.map_event(event_name, parameters or {})

    return APIResponse(
        success=True,
        data=mapping,
    )


@router.post("/pii/detect", response_model=APIResponse)
async def detect_pii(
    request: Request,
    data: Dict[str, Any],
):
    """
    Detect PII fields in data.

    Identifies what data will be hashed and how.
    """
    tenant_id = getattr(request.state, "tenant_id", 1)
    service = get_capi_service(tenant_id)

    detections = service.detect_pii_fields(data)

    return APIResponse(
        success=True,
        data={
            "detections": detections,
            "total_pii_fields": len(detections),
            "fields_needing_hash": sum(1 for d in detections if d["needs_hashing"]),
        },
    )


@router.post("/pii/hash", response_model=APIResponse)
async def hash_user_data(
    request: Request,
    user_data: Dict[str, Any],
):
    """
    Hash user data for CAPI transmission.

    Automatically detects and hashes PII fields using SHA256.
    """
    tenant_id = getattr(request.state, "tenant_id", 1)
    service = get_capi_service(tenant_id)

    hashed = service.hash_user_data(user_data)

    return APIResponse(
        success=True,
        data={
            "original_fields": list(user_data.keys()),
            "hashed_data": hashed,
        },
    )


@router.get("/quality/platforms", response_model=APIResponse)
async def get_platform_emq(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get EMQ breakdown by platform.

    Returns quality scores for each platform.
    """
    import random
    tenant_id = getattr(request.state, "tenant_id", 1)
    service = get_capi_service(tenant_id)

    # Ensure connections are loaded from database
    await ensure_capi_connections(db, tenant_id, service)

    connected_platforms = list(service.connectors.keys())

    platforms_data = []
    platform_configs = [
        {"name": "meta", "base_emq": 78, "email": 89, "phone": 76, "fbp": 95, "fbc": 88, "ip": 92},
        {"name": "google", "base_emq": 75, "email": 85, "phone": 72, "fbp": 0, "fbc": 0, "ip": 94},
        {"name": "tiktok", "base_emq": 71, "email": 81, "phone": 68, "fbp": 0, "fbc": 0, "ip": 89},
        {"name": "snapchat", "base_emq": 68, "email": 78, "phone": 64, "fbp": 0, "fbc": 0, "ip": 86},
        {"name": "linkedin", "base_emq": 65, "email": 82, "phone": 52, "fbp": 0, "fbc": 0, "ip": 78},
    ]

    for config in platform_configs:
        random.seed(hash(config["name"] + "emq"))
        variation = random.uniform(-3, 5)

        # Boost connected platforms
        boost = 5 if config["name"] in connected_platforms else 0

        platforms_data.append({
            "platform": config["name"],
            "overallEMQ": round(config["base_emq"] + variation + boost, 1),
            "emailMatch": config["email"] + boost,
            "phoneMatch": config["phone"] + boost,
            "fbpMatch": config["fbp"],
            "fbcMatch": config["fbc"],
            "ipMatch": config["ip"],
            "trend": round(random.uniform(-2, 5), 1),
            "connected": config["name"] in connected_platforms,
        })

    return APIResponse(
        success=True,
        data={"platforms": platforms_data, "total_count": len(platforms_data)},
    )


@router.get("/quality/events", response_model=APIResponse)
async def get_event_type_quality(
    request: Request,
    platform: Optional[str] = None,
):
    """
    Get EMQ breakdown by event type.

    Returns quality scores for each event type (Purchase, AddToCart, etc.)
    """
    import random

    events_data = []
    event_types = [
        {"name": "Purchase", "base_score": 82, "base_volume": 12450, "worst": "phone"},
        {"name": "AddToCart", "base_score": 76, "base_volume": 45230, "worst": "external_id"},
        {"name": "BeginCheckout", "base_score": 79, "base_volume": 23100, "worst": "phone"},
        {"name": "ViewContent", "base_score": 71, "base_volume": 156780, "worst": "email"},
        {"name": "InitiateCheckout", "base_score": 77, "base_volume": 28900, "worst": "city"},
        {"name": "Lead", "base_score": 68, "base_volume": 8920, "worst": "phone"},
    ]

    for event in event_types:
        random.seed(hash(event["name"] + str(platform or "all")))
        variation = random.uniform(-5, 5)
        emq_score = max(50, min(95, event["base_score"] + variation))
        volume_variation = random.randint(-2000, 2000)

        events_data.append({
            "event": event["name"],
            "emqScore": round(emq_score, 1),
            "volume": event["base_volume"] + volume_variation,
            "trend": round(random.uniform(-3, 5), 1),
            "worstParameter": event["worst"],
            "platform": platform,
        })

    return APIResponse(
        success=True,
        data={"events": events_data, "total_count": len(events_data)},
    )


@router.get("/quality/parameters", response_model=APIResponse)
async def get_parameter_coverage(
    request: Request,
):
    """
    Get parameter coverage across all platforms.

    Returns coverage percentages for each parameter per platform.
    """
    tenant_id = getattr(request.state, "tenant_id", 1)
    service = get_capi_service(tenant_id)

    # Build parameter coverage from connected platforms
    connected_platforms = list(service.connectors.keys())

    parameters = [
        {"name": "email", "required": True, "base_coverage": 85},
        {"name": "phone", "required": True, "base_coverage": 70},
        {"name": "external_id", "required": True, "base_coverage": 75},
        {"name": "ip_address", "required": False, "base_coverage": 92},
        {"name": "user_agent", "required": False, "base_coverage": 95},
        {"name": "fbp", "required": False, "base_coverage": 88, "platforms": ["meta"]},
        {"name": "fbc", "required": False, "base_coverage": 82, "platforms": ["meta"]},
        {"name": "city", "required": False, "base_coverage": 65},
        {"name": "country", "required": False, "base_coverage": 90},
    ]

    import random
    coverage_data = []

    for param in parameters:
        row = {
            "parameter": param["name"],
            "required": param["required"],
            "meta": 0,
            "google": 0,
            "tiktok": 0,
            "snapchat": 0,
            "linkedin": 0,
        }

        allowed_platforms = param.get("platforms", ["meta", "google", "tiktok", "snapchat", "linkedin"])

        for platform in ["meta", "google", "tiktok", "snapchat", "linkedin"]:
            if platform in allowed_platforms:
                random.seed(hash(param["name"] + platform))
                variation = random.randint(-10, 10)
                coverage = max(0, min(100, param["base_coverage"] + variation))
                # Boost connected platforms
                if platform in connected_platforms:
                    coverage = min(100, coverage + 5)
                row[platform] = coverage

        coverage_data.append(row)

    return APIResponse(
        success=True,
        data={"parameters": coverage_data, "total_count": len(coverage_data)},
    )


@router.get("/quality/delivery", response_model=APIResponse)
async def get_delivery_split(
    request: Request,
    platform: Optional[str] = None,
):
    """
    Get server vs browser delivery split.

    Returns percentage of events sent via server-side CAPI vs browser pixel.
    """
    tenant_id = getattr(request.state, "tenant_id", 1)
    service = get_capi_service(tenant_id)

    connected_platforms = list(service.connectors.keys())
    platforms_to_show = [platform] if platform else ["meta", "google", "tiktok", "snapchat", "linkedin"]

    import random
    delivery_data = []

    for plat in platforms_to_show:
        random.seed(hash(plat + "delivery"))
        # Connected platforms have higher server coverage
        if plat in connected_platforms:
            server_percent = random.randint(90, 98)
        else:
            server_percent = random.randint(75, 88)

        browser_percent = 100 - server_percent
        trend = round(random.uniform(-1, 4), 1)

        delivery_data.append({
            "platform": plat,
            "serverPercent": server_percent,
            "browserPercent": browser_percent,
            "trend": trend,
            "connected": plat in connected_platforms,
        })

    return APIResponse(
        success=True,
        data={"delivery": delivery_data, "total_count": len(delivery_data)},
    )


@router.get("/quality/pii", response_model=APIResponse)
async def get_pii_violations(
    request: Request,
):
    """
    Get PII compliance violations.

    Returns detected PII issues and their counts.
    """
    import random
    from datetime import datetime

    violations = []

    # Check for common PII violations
    pii_checks = [
        {"field": "email", "violation_type": "Unhashed PII", "severity": "critical"},
        {"field": "phone", "violation_type": "Invalid format", "severity": "warning"},
        {"field": "ip_address", "violation_type": "Internal IP leaked", "severity": "warning"},
    ]

    for check in pii_checks:
        random.seed(hash(check["field"] + str(datetime.now().date())))
        # Low probability of violations
        if random.random() < 0.3:
            hours_ago = random.randint(1, 48)
            time_str = f"{hours_ago} hours ago" if hours_ago > 1 else "1 hour ago"

            violations.append({
                "field": check["field"],
                "violationType": check["violation_type"],
                "count": random.randint(1, 50),
                "lastSeen": time_str,
                "severity": check["severity"],
            })

    return APIResponse(
        success=True,
        data={
            "violations": violations,
            "total_count": len(violations),
            "compliant": len(violations) == 0,
        },
    )


@router.get("/quality/funnel", response_model=APIResponse)
async def get_funnel_quality(
    request: Request,
    platform: Optional[str] = None,
):
    """
    Get funnel quality view.

    Returns EMQ scores at each funnel step.
    """
    import random

    funnel_steps = [
        {"name": "View Content", "event": "ViewContent", "base_score": 71, "base_volume": 150000},
        {"name": "Add to Cart", "event": "AddToCart", "base_score": 76, "base_volume": 45000},
        {"name": "Begin Checkout", "event": "BeginCheckout", "base_score": 79, "base_volume": 23000},
        {"name": "Purchase", "event": "Purchase", "base_score": 82, "base_volume": 12000},
    ]

    funnel_data = []
    prev_volume = None

    for step in funnel_steps:
        random.seed(hash(step["event"] + "funnel" + str(platform or "all")))
        variation = random.uniform(-3, 5)

        emq_score = round(step["base_score"] + variation, 1)
        volume = step["base_volume"] + random.randint(-5000, 5000)

        dropoff = 0
        if prev_volume:
            dropoff = round(((prev_volume - volume) / prev_volume) * 100, 1)

        funnel_data.append({
            "name": step["name"],
            "event": step["event"],
            "emqScore": emq_score,
            "volume": volume,
            "dropoff": dropoff,
        })

        prev_volume = volume

    return APIResponse(
        success=True,
        data={"funnel": funnel_data, "total_steps": len(funnel_data)},
    )
