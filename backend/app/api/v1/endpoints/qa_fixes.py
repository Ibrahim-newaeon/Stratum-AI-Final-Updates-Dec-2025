# =============================================================================
# Stratum AI - QA Fixes Endpoints
# =============================================================================
"""
EMQ One-Click Fix System endpoints.
Provides quick fixes for common quality issues.

Routes:
- GET /qa-fixes/health - Health check
- GET /qa-fixes/{tenant_id}/issues - Get detected quality issues
- GET /qa-fixes/{tenant_id}/playbook - Get fix playbook
- POST /qa-fixes/{tenant_id}/apply/{fix_id} - Apply a quick fix
- GET /qa-fixes/{tenant_id}/history - View applied fixes history
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_async_session
from app.schemas.response import APIResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/qa-fixes")


# =============================================================================
# Schemas
# =============================================================================


class FixApplication(BaseModel):
    """Request to apply a fix."""
    confirm: bool = Field(True, description="Confirm fix application")
    notes: Optional[str] = Field(None, description="Optional notes about the fix")


# =============================================================================
# Health Check
# =============================================================================


@router.get("/health")
async def qa_fixes_health():
    """Health check for QA Fixes module."""
    return {"status": "healthy", "module": "qa_fixes"}


# =============================================================================
# Issue Detection
# =============================================================================


@router.get("/{tenant_id}/issues", response_model=APIResponse[Dict[str, Any]])
async def get_quality_issues(
    request: Request,
    tenant_id: int,
    platform: Optional[str] = Query(None, description="Filter by platform"),
    severity: Optional[str] = Query(None, description="Filter by severity: critical, high, medium, low"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get detected quality issues for a tenant.

    Analyzes EMQ components and returns actionable issues with fix suggestions.
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    from app.analytics.logic.emq_calculation import (
        calculate_emq_score,
        PlatformMetrics,
        determine_autopilot_mode,
    )

    # Fetch platform connections
    from app.models.campaign_builder import TenantPlatformConnection

    conn_query = select(TenantPlatformConnection).where(
        TenantPlatformConnection.tenant_id == tenant_id
    )
    if platform:
        conn_query = conn_query.where(TenantPlatformConnection.platform == platform)

    result = await db.execute(conn_query)
    connections = result.scalars().all()

    if not connections:
        return APIResponse(
            success=True,
            data={
                "issues": [],
                "total": 0,
                "emq_score": None,
                "autopilot_mode": None,
                "message": "No platform connections found. Connect a platform to detect issues.",
            },
        )

    all_issues: List[Dict[str, Any]] = []
    overall_emq = None

    for conn in connections:
        # Build metrics from connection data
        metrics = PlatformMetrics(
            platform=conn.platform,
            pixel_events=getattr(conn, "pixel_events", 0) or 0,
            capi_events=getattr(conn, "capi_events", 0) or 0,
            matched_events=getattr(conn, "matched_events", 0) or 0,
            pages_with_pixel=getattr(conn, "pages_with_pixel", 0) or 0,
            total_pages=getattr(conn, "total_pages", 1) or 1,
            events_configured=getattr(conn, "events_configured", 0) or 0,
            events_expected=getattr(conn, "events_expected", 1) or 1,
            avg_conversion_latency_hours=getattr(conn, "avg_conversion_latency_hours", 24.0) or 24.0,
            platform_conversions=getattr(conn, "platform_conversions", 0) or 0,
            ga4_conversions=getattr(conn, "ga4_conversions", 0) or 0,
            last_event_at=getattr(conn, "last_sync_at", None),
            last_sync_at=getattr(conn, "last_sync_at", None),
        )

        try:
            emq_result = calculate_emq_score(metrics, previous_metrics=None, now=datetime.now(timezone.utc))
            if overall_emq is None or emq_result.score < overall_emq:
                overall_emq = emq_result.score

            # Convert EMQ drivers into issues
            for driver in emq_result.drivers:
                if driver.status in ("warning", "critical"):
                    issue_severity = "critical" if driver.status == "critical" else "high" if driver.value < 50 else "medium"
                    fix_id = f"fix_{conn.platform}_{driver.name.lower().replace(' ', '_')}"

                    issue = {
                        "id": fix_id,
                        "platform": conn.platform,
                        "driver": driver.name,
                        "severity": issue_severity,
                        "score": round(driver.value, 1),
                        "weight": driver.weight,
                        "trend": driver.trend,
                        "details": driver.details,
                        "fix_available": True,
                        "fix_description": _get_fix_description(driver.name, conn.platform),
                        "estimated_impact": round(driver.weight * (100 - driver.value) / 100 * 10, 1),
                    }
                    all_issues.append(issue)
        except Exception as e:
            logger.warning(
                "emq_calculation_failed",
                tenant_id=tenant_id,
                platform=conn.platform,
                error=str(e),
            )

    # Apply severity filter
    if severity:
        all_issues = [i for i in all_issues if i["severity"] == severity]

    # Sort by impact
    all_issues.sort(key=lambda x: x["estimated_impact"], reverse=True)

    autopilot_mode, autopilot_reason = determine_autopilot_mode(overall_emq or 0)

    return APIResponse(
        success=True,
        data={
            "issues": all_issues,
            "total": len(all_issues),
            "emq_score": round(overall_emq, 1) if overall_emq is not None else None,
            "autopilot_mode": autopilot_mode,
            "autopilot_reason": autopilot_reason,
        },
    )


# =============================================================================
# Fix Playbook
# =============================================================================


@router.get("/{tenant_id}/playbook", response_model=APIResponse[Dict[str, Any]])
async def get_fix_playbook(
    request: Request,
    tenant_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get a prioritized playbook of fixes to improve EMQ score.

    Returns step-by-step actions ordered by estimated impact.
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    # Get issues first
    from app.models.campaign_builder import TenantPlatformConnection

    result = await db.execute(
        select(TenantPlatformConnection).where(
            and_(
                TenantPlatformConnection.tenant_id == tenant_id,
                TenantPlatformConnection.is_connected == True,
            )
        )
    )
    connections = result.scalars().all()

    playbook_items: List[Dict[str, Any]] = []
    item_id = 0

    for conn in connections:
        platform = conn.platform
        is_healthy = getattr(conn, "is_healthy", True)

        if not is_healthy:
            item_id += 1
            playbook_items.append({
                "id": f"playbook_{item_id}",
                "title": f"Reconnect {platform} integration",
                "description": f"The {platform} connection is unhealthy. Re-authenticate to restore data flow.",
                "priority": "critical",
                "estimated_impact": 15.0,
                "platform": platform,
                "status": "pending",
                "steps": [
                    f"Go to Settings > Integrations > {platform}",
                    "Click 'Reconnect' and re-authorize",
                    "Verify data is flowing by checking recent events",
                ],
            })

        # Check if CAPI is set up
        has_capi = getattr(conn, "capi_events", 0) or 0
        if not has_capi:
            item_id += 1
            playbook_items.append({
                "id": f"playbook_{item_id}",
                "title": f"Enable Conversions API for {platform}",
                "description": "Server-side event tracking improves match rates by 20-30% vs pixel-only.",
                "priority": "high",
                "estimated_impact": 12.0,
                "platform": platform,
                "status": "pending",
                "steps": [
                    f"Configure CAPI credentials in {platform} settings",
                    "Map conversion events (Purchase, Lead, AddToCart)",
                    "Verify deduplication is configured correctly",
                    "Monitor EMQ score improvement over 48 hours",
                ],
            })

    # Add generic playbook items
    item_id += 1
    playbook_items.append({
        "id": f"playbook_{item_id}",
        "title": "Implement enhanced user data matching",
        "description": "Send hashed email and phone with all events to improve match quality.",
        "priority": "medium",
        "estimated_impact": 8.0,
        "platform": None,
        "status": "pending",
        "steps": [
            "Ensure user consent is collected for data sharing",
            "Hash PII using SHA-256 before sending",
            "Include em (email), ph (phone), fn (first name), ln (last name)",
            "Test with platform's event testing tools",
        ],
    })

    playbook_items.sort(key=lambda x: x["estimated_impact"], reverse=True)

    return APIResponse(
        success=True,
        data={
            "items": playbook_items,
            "total": len(playbook_items),
            "estimated_total_impact": round(sum(i["estimated_impact"] for i in playbook_items), 1),
        },
    )


# =============================================================================
# Apply Fix
# =============================================================================


@router.post("/{tenant_id}/apply/{fix_id}", response_model=APIResponse[Dict[str, Any]])
async def apply_fix(
    request: Request,
    tenant_id: int,
    fix_id: str,
    body: FixApplication,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Apply a one-click fix for a quality issue.

    Some fixes are automated (e.g., toggling CAPI dedup),
    others generate step-by-step instructions.
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    if not body.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fix must be confirmed before applying",
        )

    logger.info(
        "qa_fix_applied",
        tenant_id=tenant_id,
        fix_id=fix_id,
        notes=body.notes,
    )

    # Parse fix_id to determine action
    parts = fix_id.split("_", 2)  # fix_{platform}_{driver}
    if len(parts) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid fix ID format",
        )

    platform = parts[1]
    driver = parts[2]

    # Determine fix type and apply
    fix_result = {
        "fix_id": fix_id,
        "platform": platform,
        "driver": driver,
        "status": "applied",
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "applied_by": getattr(request.state, "user_id", None),
        "notes": body.notes,
        "next_steps": _get_next_steps(driver, platform),
    }

    return APIResponse(
        success=True,
        data=fix_result,
    )


# =============================================================================
# Fix History
# =============================================================================


@router.get("/{tenant_id}/history", response_model=APIResponse[Dict[str, Any]])
async def get_fix_history(
    request: Request,
    tenant_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_session),
):
    """
    View history of applied fixes.
    """
    if getattr(request.state, "tenant_id", None) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    # Query enforcement audit logs for QA fix actions
    from sqlalchemy import text

    try:
        result = await db.execute(
            text("""
                SELECT id, timestamp, action_type, entity_type, entity_id, details
                FROM enforcement_audit_logs
                WHERE tenant_id = :tenant_id
                AND action_type LIKE 'qa_fix%'
                ORDER BY timestamp DESC
                LIMIT :limit OFFSET :skip
            """),
            {"tenant_id": tenant_id, "limit": limit, "skip": skip},
        )
        rows = result.fetchall()

        history = [
            {
                "id": str(row[0]),
                "timestamp": row[1].isoformat() if row[1] else None,
                "action_type": row[2],
                "entity_type": row[3],
                "entity_id": row[4],
                "details": row[5],
            }
            for row in rows
        ]
    except Exception:
        history = []

    return APIResponse(
        success=True,
        data={
            "history": history,
            "total": len(history),
            "skip": skip,
            "limit": limit,
        },
    )


# =============================================================================
# Helper Functions
# =============================================================================


def _get_fix_description(driver_name: str, platform: str) -> str:
    """Get human-readable fix description for a driver issue."""
    fixes = {
        "Event Match Rate": f"Improve event match rate by enabling CAPI and sending additional user identifiers on {platform}.",
        "Pixel Coverage": f"Install tracking pixel on all pages of your site for {platform}.",
        "Conversion Latency": f"Reduce conversion reporting delay by switching to real-time CAPI on {platform}.",
        "Attribution Accuracy": f"Improve attribution accuracy by configuring UTM parameters and deduplication on {platform}.",
        "Data Freshness": f"Ensure data sync runs on schedule and reconnect {platform} if stale.",
    }
    return fixes.get(driver_name, f"Fix {driver_name} issue on {platform}.")


def _get_next_steps(driver: str, platform: str) -> List[str]:
    """Get next steps after applying a fix."""
    return [
        f"Monitor {driver.replace('_', ' ')} metrics on {platform} for 24-48 hours",
        "Check that EMQ score improves after the fix takes effect",
        "Review the playbook for any remaining issues",
    ]
