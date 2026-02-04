# =============================================================================
# Stratum AI - Conversion API Endpoints
# =============================================================================
"""
API endpoints for server-side Conversion API integration.
Provides no-code platform connection, event streaming, and data quality analysis.
"""

from datetime import UTC, datetime
from typing import Any, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.schemas import APIResponse
from app.services.capi import CAPIService

logger = get_logger(__name__)
router = APIRouter()

# Global CAPI service instance (per-tenant in production)
_capi_services: dict[int, CAPIService] = {}


def get_capi_service(tenant_id: int) -> CAPIService:
    """Get or create CAPI service for tenant."""
    if tenant_id not in _capi_services:
        _capi_services[tenant_id] = CAPIService()
    return _capi_services[tenant_id]


# =============================================================================
# Request/Response Models
# =============================================================================
class PlatformCredentials(BaseModel):
    """Credentials for connecting to a platform."""

    platform: str = Field(
        ..., description="Platform name: meta, google, tiktok, snapchat, linkedin"
    )
    credentials: dict[str, str] = Field(..., description="Platform-specific credentials")


class ConversionEvent(BaseModel):
    """Conversion event to stream."""

    event_name: str = Field(..., description="Event name (e.g., Purchase, Lead)")
    user_data: dict[str, Any] = Field(..., description="User identification data")
    parameters: Optional[dict[str, Any]] = Field(
        default={}, description="Event parameters (value, currency, etc.)"
    )
    event_time: Optional[int] = Field(default=None, description="Unix timestamp")
    event_source_url: Optional[str] = Field(default=None, description="URL where event occurred")
    event_id: Optional[str] = Field(default=None, description="Unique event ID for deduplication")


class BatchEventsRequest(BaseModel):
    """Request for streaming batch events."""

    events: list[ConversionEvent]
    platforms: Optional[list[str]] = Field(default=None, description="Platforms to send to")


class DataQualityRequest(BaseModel):
    """Request for data quality analysis."""

    user_data: dict[str, Any]
    platform: Optional[str] = Field(default=None)


# =============================================================================
# Platform Connection Endpoints
# =============================================================================
@router.post("/platforms/connect", response_model=APIResponse)
async def connect_platform(
    data: PlatformCredentials,
    request: Request,
):
    """
    Connect to an ad platform's Conversion API.

    Supports:
    - Meta (Facebook) - Requires pixel_id, access_token
    - Google Ads - Requires customer_id, conversion_action_id, api_key
    - TikTok - Requires pixel_code, access_token
    - Snapchat - Requires pixel_id, access_token
    - LinkedIn - Requires conversion_id, access_token
    """
    tenant_id = getattr(request.state, "tenant_id", 1)
    service = get_capi_service(tenant_id)

    result = await service.connect_platform(data.platform, data.credentials)

    return APIResponse(
        success=result.status.value == "connected",
        data={
            "status": result.status.value,
            "platform": result.platform,
            "message": result.message,
            "details": result.details,
        },
    )


@router.delete("/platforms/{platform}/disconnect", response_model=APIResponse)
async def disconnect_platform(
    platform: str,
    request: Request,
):
    """Disconnect from a platform."""
    tenant_id = getattr(request.state, "tenant_id", 1)
    service = get_capi_service(tenant_id)

    success = await service.disconnect_platform(platform)

    return APIResponse(
        success=success,
        data={"platform": platform, "disconnected": success},
    )


@router.get("/platforms/status", response_model=APIResponse)
async def get_platforms_status(request: Request):
    """Get connection status for all platforms."""
    tenant_id = getattr(request.state, "tenant_id", 1)
    service = get_capi_service(tenant_id)

    connected = service.get_connected_platforms()
    setup_status = service.get_setup_status()

    return APIResponse(
        success=True,
        data={
            "connected_platforms": connected,
            "setup_status": setup_status,
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
# Event Streaming Endpoints
# =============================================================================
@router.post("/events/stream", response_model=APIResponse)
async def stream_event(
    event: ConversionEvent,
    request: Request,
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

    events = [
        {
            "event_name": e.event_name,
            "user_data": e.user_data,
            "parameters": e.parameters,
            "event_time": e.event_time or int(datetime.now(UTC).timestamp()),
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


# =============================================================================
# Event Mapping Endpoints
# =============================================================================
@router.post("/events/map", response_model=APIResponse)
async def map_event(
    request: Request,
    event_name: str,
    parameters: Optional[dict[str, Any]] = None,
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
    data: dict[str, Any],
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
    user_data: dict[str, Any],
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
