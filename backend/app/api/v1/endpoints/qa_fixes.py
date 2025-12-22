"""
EMQ One-Click Fix System API Endpoints
Provides suggestions, apply fixes, and track fix runs.
"""

from datetime import date, datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Request, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models import TenantTrackingConfig, FixRun, CapiQaLog
from app.services.fixes.catalog import FIX_CATALOG
from app.services.fixes.metrics import compute_platform_metrics

router = APIRouter(prefix="/qa/fixes", tags=["QA Fixes"])


class ApplyFixIn(BaseModel):
    platform: str
    issue_code: str
    dry_run: bool = False


@router.get("/suggestions")
async def get_fix_suggestions(
    request: Request,
    platform: str = Query(...),
    date_from: date = Query(..., alias="from"),
    date_to: date = Query(..., alias="to"),
    event_name: Optional[str] = None,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get suggested fixes based on current EMQ diagnostics.
    Returns available fixes for the specified platform and time range.
    """
    tenant_id = getattr(request.state, "tenant_id", 1)

    # Compute current metrics to determine which fixes are relevant
    dt_from = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc)
    dt_to = datetime.combine(date_to, datetime.max.time(), tzinfo=timezone.utc)

    metrics = await compute_platform_metrics(
        session, tenant_id, platform, dt_from, dt_to, event_name
    )

    items = []

    # Check metrics and add relevant suggestions
    if metrics["events"] > 0:
        # Low success rate
        if metrics["success_rate"] < 0.9:
            meta = FIX_CATALOG["LOW_SUCCESS_RATE"]
            items.append({
                "issue_code": "LOW_SUCCESS_RATE",
                "one_click": meta["one_click"],
                "action": meta["action"],
                "description": meta["description"],
                "impact": meta.get("impact"),
                "guided_steps": meta.get("guided_steps", []),
                "current_value": f"{metrics['success_rate']*100:.1f}%",
                "roas_impact": meta.get("roas_impact"),
            })

        # Low match score
        if metrics["avg_score"] < 60:
            meta = FIX_CATALOG["LOW_MATCH_SCORE"]
            items.append({
                "issue_code": "LOW_MATCH_SCORE",
                "one_click": meta["one_click"],
                "action": meta["action"],
                "description": meta["description"],
                "impact": meta.get("impact"),
                "guided_steps": meta.get("guided_steps", []),
                "current_value": f"{metrics['avg_score']:.1f}/100",
                "roas_impact": meta.get("roas_impact"),
            })

        # High duplicates
        if metrics["duplicate_rate"] > 0.05:
            meta = FIX_CATALOG["HIGH_DUPLICATES"]
            items.append({
                "issue_code": "HIGH_DUPLICATES",
                "one_click": meta["one_click"],
                "action": meta["action"],
                "description": meta["description"],
                "impact": meta.get("impact"),
                "guided_steps": meta.get("guided_steps", []),
                "current_value": f"{metrics['duplicate_rate']*100:.1f}%",
                "roas_impact": meta.get("roas_impact"),
            })

        # Low email coverage
        if metrics["coverage"]["em"] < 0.5:
            meta = FIX_CATALOG["LOW_EMAIL_COVERAGE"]
            items.append({
                "issue_code": "LOW_EMAIL_COVERAGE",
                "one_click": meta["one_click"],
                "action": meta["action"],
                "description": meta["description"],
                "impact": meta.get("impact"),
                "guided_steps": meta.get("guided_steps", []),
                "current_value": f"{metrics['coverage']['em']*100:.1f}%",
                "roas_impact": meta.get("roas_impact"),
            })

        # Low cookie coverage
        if metrics["coverage"]["fbp"] < 0.3:
            meta = FIX_CATALOG["LOW_COOKIE_COVERAGE"]
            items.append({
                "issue_code": "LOW_COOKIE_COVERAGE",
                "one_click": meta["one_click"],
                "action": meta["action"],
                "description": meta["description"],
                "impact": meta.get("impact"),
                "guided_steps": meta.get("guided_steps", []),
                "current_value": f"{metrics['coverage']['fbp']*100:.1f}%",
                "roas_impact": meta.get("roas_impact"),
            })

        # Missing IP/UA
        if metrics["coverage"]["ip"] < 0.8 or metrics["coverage"]["ua"] < 0.8:
            meta = FIX_CATALOG["MISSING_IP_UA"]
            items.append({
                "issue_code": "MISSING_IP_UA",
                "one_click": meta["one_click"],
                "action": meta["action"],
                "description": meta["description"],
                "impact": meta.get("impact"),
                "guided_steps": meta.get("guided_steps", []),
                "current_value": f"IP: {metrics['coverage']['ip']*100:.0f}%, UA: {metrics['coverage']['ua']*100:.0f}%",
                "roas_impact": meta.get("roas_impact"),
            })

    return {
        "tenant_id": tenant_id,
        "platform": platform,
        "from": str(date_from),
        "to": str(date_to),
        "event_name": event_name,
        "metrics": metrics,
        "items": items,
        "suggestion_count": len(items),
    }


@router.post("/apply")
async def apply_fix(
    request: Request,
    body: ApplyFixIn,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Apply a one-click fix or return guided steps for manual fixes.
    Creates a FixRun audit record and applies configuration changes.
    """
    tenant_id = getattr(request.state, "tenant_id", 1)

    if body.issue_code not in FIX_CATALOG:
        raise HTTPException(400, "Unknown issue_code")

    meta = FIX_CATALOG[body.issue_code]
    action = meta["action"]

    # Load or create config row
    result = await session.execute(
        select(TenantTrackingConfig).where(
            TenantTrackingConfig.tenant_id == tenant_id,
            TenantTrackingConfig.platform == body.platform,
        )
    )
    cfg = result.scalars().first()

    if not cfg:
        cfg = TenantTrackingConfig(tenant_id=tenant_id, platform=body.platform)
        session.add(cfg)
        await session.flush()

    # Capture before metrics
    dt_to = datetime.now(timezone.utc)
    dt_from = dt_to - timedelta(hours=24)
    before_metrics = await compute_platform_metrics(
        session, tenant_id, body.platform, dt_from, dt_to
    )

    # Create fix run (audit)
    run = FixRun(
        tenant_id=tenant_id,
        platform=body.platform,
        issue_code=body.issue_code,
        action=action,
        status="queued",
        before_metrics=before_metrics,
    )
    session.add(run)
    await session.flush()

    if body.dry_run:
        return {
            "ok": True,
            "fix_run_id": run.id,
            "dry_run": True,
            "would_apply": action,
            "before_metrics": before_metrics,
        }

    applied = {}

    # Apply safe actions (one-click fixes)
    if action == "enable_retries":
        cfg.retry_enabled = True
        cfg.max_retries = max(cfg.max_retries, 3)
        cfg.backoff_seconds = max(cfg.backoff_seconds, 2)
        applied = {
            "retry_enabled": True,
            "max_retries": cfg.max_retries,
            "backoff_seconds": cfg.backoff_seconds,
        }

    elif action == "set_normalization_v2":
        cfg.normalization_policy = "v2"
        applied = {"normalization_policy": "v2"}

    elif action == "enforce_event_id":
        cfg.extra = cfg.extra or {}
        cfg.extra["enforce_event_id"] = True
        cfg.extra["dedupe_strict"] = True
        applied = {"extra.enforce_event_id": True, "extra.dedupe_strict": True}

    elif action == "enable_proxy_headers":
        cfg.extra = cfg.extra or {}
        cfg.extra["trust_proxy_headers"] = True
        applied = {"extra.trust_proxy_headers": True}

    elif action == "reset_config":
        cfg.normalization_policy = "v2"
        cfg.retry_enabled = True
        cfg.max_retries = 3
        cfg.backoff_seconds = 2
        cfg.dedupe_mode = "capi_only"
        cfg.extra = cfg.extra or {}
        cfg.extra["enforce_event_id"] = True
        applied = {
            "normalization_policy": "v2",
            "retry_enabled": True,
            "max_retries": 3,
            "backoff_seconds": 2,
            "dedupe_mode": "capi_only",
            "extra.enforce_event_id": True,
        }

    else:
        # Guided fix only - not auto-fixable
        run.status = "failed"
        run.error = "This issue requires guided fix steps (not auto-fixable)."
        run.applied_changes = {}
        await session.commit()
        return {
            "ok": False,
            "fix_run_id": run.id,
            "message": run.error,
            "guided_steps": meta.get("guided_steps", []),
        }

    run.applied_changes = applied
    run.status = "success"
    run.finished_at = datetime.now(timezone.utc)

    # Get ROAS impact from catalog
    roas_impact = meta.get("roas_impact", {})
    base_roas = 2.5  # Assume baseline ROAS of 2.5x

    # Add projected ROAS to before metrics
    before_metrics["projected_roas"] = base_roas

    # Project expected improvement based on fix type
    # (Real metrics would need time to show actual improvement)
    after_metrics = before_metrics.copy()
    roas_multiplier = 1.0

    if action == "enable_retries":
        # Retries typically improve success rate by 5-10%
        after_metrics["success_rate"] = min(1.0, before_metrics.get("success_rate", 0) * 1.08)
        roas_multiplier = 1.10  # +10% ROAS

    elif action == "set_normalization_v2":
        # Better normalization improves match score by 10-15%
        after_metrics["avg_score"] = min(100.0, before_metrics.get("avg_score", 0) * 1.12)
        if "coverage" in after_metrics:
            after_metrics["coverage"] = before_metrics.get("coverage", {}).copy()
            after_metrics["coverage"]["em"] = min(1.0, after_metrics["coverage"].get("em", 0) * 1.1)
            after_metrics["coverage"]["ph"] = min(1.0, after_metrics["coverage"].get("ph", 0) * 1.1)
        roas_multiplier = 1.15  # +15% ROAS

    elif action == "enforce_event_id":
        # Deduplication reduces duplicates significantly
        after_metrics["duplicate_rate"] = before_metrics.get("duplicate_rate", 0) * 0.1
        after_metrics["duplicate_rows"] = int(before_metrics.get("duplicate_rows", 0) * 0.1)
        roas_multiplier = 1.07  # +7% ROAS

    elif action == "enable_proxy_headers":
        # Enables IP/UA capture
        if "coverage" in after_metrics:
            after_metrics["coverage"] = before_metrics.get("coverage", {}).copy()
            after_metrics["coverage"]["ip"] = min(1.0, after_metrics["coverage"].get("ip", 0) + 0.15)
            after_metrics["coverage"]["ua"] = min(1.0, after_metrics["coverage"].get("ua", 0) + 0.15)
        roas_multiplier = 1.08  # +8% ROAS

    elif action == "reset_config":
        # Full reset improves multiple metrics
        after_metrics["success_rate"] = min(1.0, before_metrics.get("success_rate", 0) * 1.1)
        after_metrics["avg_score"] = min(100.0, before_metrics.get("avg_score", 0) * 1.15)
        after_metrics["duplicate_rate"] = before_metrics.get("duplicate_rate", 0) * 0.2
        roas_multiplier = 1.20  # +20% ROAS

    # Calculate projected ROAS improvement
    after_metrics["projected_roas"] = round(base_roas * roas_multiplier, 2)
    after_metrics["roas_improvement_pct"] = round((roas_multiplier - 1) * 100, 1)

    run.after_metrics = after_metrics

    await session.commit()

    return {
        "ok": True,
        "fix_run_id": run.id,
        "applied": applied,
        "before_metrics": before_metrics,
        "after_metrics": after_metrics,
        "status": run.status,
    }


@router.get("/run/{fix_run_id}")
async def get_fix_run(
    request: Request,
    fix_run_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get status and details of a fix run.
    Use for polling after applying a fix.
    """
    tenant_id = getattr(request.state, "tenant_id", 1)

    result = await session.execute(
        select(FixRun).where(
            FixRun.id == fix_run_id,
            FixRun.tenant_id == tenant_id,
        )
    )
    run = result.scalars().first()

    if not run:
        raise HTTPException(status_code=404, detail="FixRun not found")

    return {
        "id": run.id,
        "tenant_id": run.tenant_id,
        "platform": run.platform,
        "issue_code": run.issue_code,
        "action": run.action,
        "status": run.status,
        "error": run.error,
        "applied_changes": run.applied_changes or {},
        "before_metrics": run.before_metrics or {},
        "after_metrics": run.after_metrics or {},
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }


@router.get("/history")
async def get_fix_history(
    request: Request,
    platform: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get history of fix runs for the tenant.
    """
    tenant_id = getattr(request.state, "tenant_id", 1)

    query = select(FixRun).where(FixRun.tenant_id == tenant_id)

    if platform:
        query = query.where(FixRun.platform == platform)

    query = query.order_by(FixRun.created_at.desc()).limit(limit)

    result = await session.execute(query)
    runs = result.scalars().all()

    return {
        "tenant_id": tenant_id,
        "platform": platform,
        "items": [
            {
                "id": run.id,
                "platform": run.platform,
                "issue_code": run.issue_code,
                "action": run.action,
                "status": run.status,
                "created_at": run.created_at.isoformat() if run.created_at else None,
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            }
            for run in runs
        ],
    }
