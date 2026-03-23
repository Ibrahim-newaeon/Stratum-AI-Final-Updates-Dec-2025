# =============================================================================
# Stratum AI - Meta CAPI QA Endpoints
# =============================================================================
"""
Meta Conversion API (CAPI) Quality Assurance endpoints.
Handles event collection with quality tracking.

Routes:
- GET /meta-capi/health - Health check
- POST /meta-capi/events - Send conversion events
- POST /meta-capi/events/validate - Validate event payload
- GET /meta-capi/quality/{tenant_id} - Get quality metrics
- GET /meta-capi/quality/{tenant_id}/report - Full quality report
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_async_session
from app.schemas.response import APIResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/meta-capi")


# =============================================================================
# Request/Response Schemas
# =============================================================================


class CAPIEventData(BaseModel):
    """Single CAPI conversion event."""
    event_name: str = Field(..., description="Event name (e.g. Purchase, Lead, AddToCart)")
    event_time: int = Field(..., description="Unix timestamp of the event")
    user_data: Dict[str, Any] = Field(default_factory=dict, description="Hashed user data")
    custom_data: Optional[Dict[str, Any]] = Field(None, description="Custom event properties")
    event_source_url: Optional[str] = Field(None, description="URL where event occurred")
    action_source: str = Field("website", description="Event source: website, app, email, etc.")


class CAPIEventBatch(BaseModel):
    """Batch of CAPI events."""
    events: List[CAPIEventData] = Field(..., min_length=1, max_length=1000)
    pixel_id: Optional[str] = Field(None, description="Meta Pixel ID")
    test_event_code: Optional[str] = Field(None, description="Test event code for debugging")


class CAPIValidationRequest(BaseModel):
    """Request to validate event payloads."""
    events: List[CAPIEventData] = Field(..., min_length=1, max_length=100)


# =============================================================================
# Health Check
# =============================================================================


@router.get("/health")
async def meta_capi_health():
    """Health check for Meta CAPI QA module."""
    return {"status": "healthy", "module": "meta_capi"}


# =============================================================================
# Event Ingestion
# =============================================================================


@router.post("/events", response_model=APIResponse[Dict[str, Any]])
async def send_capi_events(
    request: Request,
    batch: CAPIEventBatch,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Send conversion events via CAPI.

    Validates, hashes PII, and forwards events to Meta Conversions API.
    Returns quality metrics for each event processed.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Tenant context required")

    from app.services.capi.capi_service import CAPIService

    capi_service = CAPIService(db)

    results = []
    quality_issues = []

    for event in batch.events:
        # Validate user data completeness
        event_quality = _assess_event_quality(event)

        if event_quality["score"] < 30:
            quality_issues.append({
                "event_name": event.event_name,
                "issues": event_quality["issues"],
                "score": event_quality["score"],
            })

        results.append({
            "event_name": event.event_name,
            "event_time": event.event_time,
            "quality_score": event_quality["score"],
            "issues": event_quality["issues"],
            "status": "accepted",
        })

    # Stream events through CAPI service
    try:
        stream_result = await capi_service.stream_events(
            tenant_id=tenant_id,
            events=[
                {
                    "event_name": e.event_name,
                    "event_time": datetime.fromtimestamp(e.event_time, tz=timezone.utc),
                    "user_data": e.user_data,
                    "custom_data": e.custom_data or {},
                    "event_source_url": e.event_source_url,
                    "action_source": e.action_source,
                }
                for e in batch.events
            ],
            platforms=["meta"],
            test_event_code=batch.test_event_code,
        )

        logger.info(
            "capi_events_sent",
            tenant_id=tenant_id,
            total_events=len(batch.events),
            platforms_sent=getattr(stream_result, "platforms_sent", 1),
        )
    except Exception as e:
        logger.error("capi_events_failed", tenant_id=tenant_id, error=str(e))
        # Still return validation results even if send fails
        for r in results:
            r["status"] = "send_failed"

    avg_quality = sum(r["quality_score"] for r in results) / len(results) if results else 0

    return APIResponse(
        success=True,
        data={
            "total_events": len(batch.events),
            "accepted": len([r for r in results if r["status"] == "accepted"]),
            "rejected": len([r for r in results if r["status"] != "accepted"]),
            "average_quality_score": round(avg_quality, 1),
            "quality_issues": quality_issues,
            "results": results,
        },
    )


# =============================================================================
# Event Validation
# =============================================================================


@router.post("/events/validate", response_model=APIResponse[Dict[str, Any]])
async def validate_capi_events(
    payload: CAPIValidationRequest,
):
    """
    Validate CAPI event payloads without sending them.

    Returns quality scores and improvement suggestions for each event.
    """
    validations = []

    for event in payload.events:
        quality = _assess_event_quality(event)
        validations.append({
            "event_name": event.event_name,
            "valid": quality["score"] >= 30,
            "quality_score": quality["score"],
            "issues": quality["issues"],
            "suggestions": quality["suggestions"],
        })

    all_valid = all(v["valid"] for v in validations)
    avg_score = sum(v["quality_score"] for v in validations) / len(validations) if validations else 0

    return APIResponse(
        success=True,
        data={
            "all_valid": all_valid,
            "total_events": len(payload.events),
            "average_quality_score": round(avg_score, 1),
            "validations": validations,
        },
    )


# =============================================================================
# Quality Metrics
# =============================================================================


@router.get("/quality/{tenant_id}", response_model=APIResponse[Dict[str, Any]])
async def get_quality_metrics(
    request: Request,
    tenant_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get CAPI data quality metrics for a tenant.

    Returns EMQ-related quality scores and recommendations.
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    from app.services.capi.capi_service import CAPIService

    capi_service = CAPIService(db)

    try:
        quality_report = await capi_service.analyze_data_quality(tenant_id)
    except Exception as e:
        logger.warning("quality_analysis_failed", tenant_id=tenant_id, error=str(e))
        quality_report = None

    if quality_report:
        return APIResponse(
            success=True,
            data={
                "overall_score": quality_report.overall_score,
                "platform_scores": {
                    platform: {
                        "score": score.score,
                        "event_coverage": score.event_coverage,
                        "data_completeness": score.data_completeness,
                    }
                    for platform, score in quality_report.platform_scores.items()
                },
                "top_recommendations": quality_report.top_recommendations,
                "estimated_roas_improvement": quality_report.estimated_roas_improvement,
                "trend": quality_report.trend,
            },
        )

    return APIResponse(
        success=True,
        data={
            "overall_score": None,
            "platform_scores": {},
            "top_recommendations": [],
            "estimated_roas_improvement": 0,
            "trend": "unknown",
            "message": "No quality data available yet. Connect a platform and send events to begin tracking.",
        },
    )


@router.get("/quality/{tenant_id}/report", response_model=APIResponse[Dict[str, Any]])
async def get_quality_report(
    request: Request,
    tenant_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get detailed quality report with data gap analysis.
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    from app.services.capi.data_quality import DataQualityAnalyzer

    analyzer = DataQualityAnalyzer()

    try:
        report = await analyzer.generate_report(db, tenant_id)
        return APIResponse(success=True, data=report)
    except Exception as e:
        logger.warning("quality_report_failed", tenant_id=tenant_id, error=str(e))
        return APIResponse(
            success=True,
            data={
                "overall_score": None,
                "data_gaps": [],
                "recommendations": [],
                "message": "Unable to generate quality report. Ensure platform connections are active.",
            },
        )


# =============================================================================
# Helper Functions
# =============================================================================


def _assess_event_quality(event: CAPIEventData) -> Dict[str, Any]:
    """Assess quality of a single CAPI event."""
    score = 100.0
    issues: List[str] = []
    suggestions: List[str] = []

    # Check user data completeness
    user_data = event.user_data
    if not user_data:
        score -= 40
        issues.append("No user data provided")
        suggestions.append("Include hashed email (em) or phone (ph) for better match rates")
    else:
        # Check for key identifiers
        has_email = "em" in user_data or "email" in user_data
        has_phone = "ph" in user_data or "phone" in user_data
        has_fbp = "fbp" in user_data or "fbc" in user_data
        has_ip = "client_ip_address" in user_data
        has_ua = "client_user_agent" in user_data

        if not has_email and not has_phone:
            score -= 25
            issues.append("Missing email or phone identifiers")
            suggestions.append("Include hashed email (em) and/or phone (ph) for higher match rates")

        if not has_fbp:
            score -= 10
            issues.append("Missing Facebook browser ID (fbp/fbc)")
            suggestions.append("Include fbp and fbc cookies for better attribution")

        if not has_ip:
            score -= 5
            issues.append("Missing client IP address")
            suggestions.append("Include client_ip_address for geo-matching")

        if not has_ua:
            score -= 5
            issues.append("Missing user agent")
            suggestions.append("Include client_user_agent for device matching")

    # Check event data
    if not event.event_source_url:
        score -= 5
        issues.append("Missing event_source_url")
        suggestions.append("Include the page URL where the event occurred")

    if event.event_name in ("Purchase", "CompleteRegistration") and not event.custom_data:
        score -= 10
        issues.append(f"Missing custom_data for {event.event_name}")
        suggestions.append(f"Include value and currency in custom_data for {event.event_name}")

    if event.custom_data and event.event_name == "Purchase":
        if "value" not in event.custom_data:
            score -= 10
            issues.append("Purchase event missing value")
            suggestions.append("Include purchase value in custom_data.value")
        if "currency" not in event.custom_data:
            score -= 5
            issues.append("Purchase event missing currency")
            suggestions.append("Include currency code in custom_data.currency (e.g. USD)")

    return {
        "score": max(0, score),
        "issues": issues,
        "suggestions": suggestions,
    }
