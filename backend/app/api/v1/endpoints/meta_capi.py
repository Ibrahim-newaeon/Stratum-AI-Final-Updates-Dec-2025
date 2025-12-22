from __future__ import annotations

import os
import time
import hashlib
import re
from datetime import date, datetime, timezone, timedelta
from typing import Any, Optional, Dict, List, Literal

import httpx
from fastapi import APIRouter, Depends, Request, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, cast, Date, Integer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models import CapiQaLog, PixelEventLog

router = APIRouter(prefix="/meta/capi", tags=["Meta CAPI QA"])

# -----------------------
# Schemas
# -----------------------
class MetaUserIn(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    external_id: Optional[str] = None

    fbp: Optional[str] = None
    fbc: Optional[str] = None

    fn: Optional[str] = None
    ln: Optional[str] = None
    ct: Optional[str] = None
    country: Optional[str] = None
    zp: Optional[str] = None

    client_ip_address: Optional[str] = None
    client_user_agent: Optional[str] = None

class MetaCustomDataIn(BaseModel):
    value: Optional[float] = None
    currency: Optional[str] = None
    content_ids: Optional[List[str]] = None
    content_type: Optional[str] = None
    contents: Optional[List[Dict[str, Any]]] = None
    num_items: Optional[int] = None
    extra: Optional[Dict[str, Any]] = None

class MetaCapiCollectIn(BaseModel):
    event_name: str = Field(..., examples=["Lead", "Purchase"])
    event_time: Optional[int] = None
    event_id: str = Field(..., min_length=6)

    action_source: Literal["website"] = "website"
    event_source_url: Optional[str] = None

    pixel_id: Optional[str] = None
    dataset_id: Optional[str] = None
    platform: str = "meta"

    user: MetaUserIn = Field(default_factory=MetaUserIn)
    custom_data: Optional[MetaCustomDataIn] = None

    # optional for test events; prefer env in prod
    test_event_code: Optional[str] = None

class MetaCapiCollectOut(BaseModel):
    ok: bool
    qa_log_id: int
    match_coverage_score: float
    meta_success: bool
    meta_events_received: int
    meta_trace_id: Optional[str] = None
    meta_error_code: Optional[int] = None
    meta_error_message: Optional[str] = None

# -----------------------
# Hash utilities
# -----------------------
def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _norm_email(v: str) -> str:
    return v.strip().lower()

def _norm_phone(v: str) -> str:
    return re.sub(r"[^\d]", "", v.strip())

def _norm_text(v: str) -> str:
    return v.strip().lower()

def _hash_if_present(value: Optional[str], normalizer) -> Optional[str]:
    if not value:
        return None
    nv = normalizer(value)
    return _sha256(nv) if nv else None

# -----------------------
# Match coverage score (0-100)
# -----------------------
def _calc_match_coverage_score(flags: dict[str, bool]) -> float:
    weights = {
        "has_em": 25,
        "has_ph": 20,
        "has_external_id": 20,
        "has_fbp": 15,
        "has_fbc": 10,
        "ip_ua": 10,      # only if both ip and ua present
        "has_fn": 3,
        "has_ln": 3,
        "has_ct": 2,
        "has_country": 2,
        "has_zp": 2,
    }
    score = 0.0
    if flags["has_em"]: score += weights["has_em"]
    if flags["has_ph"]: score += weights["has_ph"]
    if flags["has_external_id"]: score += weights["has_external_id"]
    if flags["has_fbp"]: score += weights["has_fbp"]
    if flags["has_fbc"]: score += weights["has_fbc"]
    if flags["has_ip"] and flags["has_ua"]: score += weights["ip_ua"]
    if flags["has_fn"]: score += weights["has_fn"]
    if flags["has_ln"]: score += weights["has_ln"]
    if flags["has_ct"]: score += weights["has_ct"]
    if flags["has_country"]: score += weights["has_country"]
    if flags["has_zp"]: score += weights["has_zp"]
    return float(min(100.0, score))

# -----------------------
# Meta CAPI sender (async)
# -----------------------
async def _send_meta_capi(pixel_id: str, access_token: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    url = f"https://graph.facebook.com/v20.0/{pixel_id}/events"
    params = {"access_token": access_token}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, params=params, json=payload)
        try:
            data = r.json()
        except Exception:
            data = {"raw": r.text}
        return r.status_code, data

def _resolve_pixel_id(body_pixel_id: Optional[str]) -> str:
    return body_pixel_id or os.getenv("META_PIXEL_ID", "")

# ==========================================================
# POST /api/v1/meta/capi/collect
# ==========================================================
@router.post("/collect", response_model=MetaCapiCollectOut)
async def collect(
    request: Request,
    body: MetaCapiCollectIn,
    session: AsyncSession = Depends(get_async_session),
):
    tenant_id = getattr(request.state, "tenant_id", 1)

    pixel_id = _resolve_pixel_id(body.pixel_id)
    if not pixel_id:
        raise HTTPException(status_code=400, detail="pixel_id missing (provide it or set META_PIXEL_ID).")

    access_token = os.getenv("META_CAPI_TOKEN")
    if not access_token:
        raise HTTPException(status_code=500, detail="META_CAPI_TOKEN env is not set.")

    event_time = body.event_time or int(time.time())
    client_ip = body.user.client_ip_address or (request.client.host if request.client else None)
    client_ua = body.user.client_user_agent or request.headers.get("user-agent")

    # Flags for QA log (your boolean columns)
    flags = {
        "has_em": bool(body.user.email),
        "has_ph": bool(body.user.phone),
        "has_external_id": bool(body.user.external_id),
        "has_fbp": bool(body.user.fbp),
        "has_fbc": bool(body.user.fbc),
        "has_ip": bool(client_ip),
        "has_ua": bool(client_ua),
        "has_fn": bool(body.user.fn),
        "has_ln": bool(body.user.ln),
        "has_ct": bool(body.user.ct),
        "has_country": bool(body.user.country),
        "has_zp": bool(body.user.zp),
    }
    score = _calc_match_coverage_score(flags)

    # Hash for Meta (do NOT store hashed PII in QA log; only store flags + payload if you want)
    em = _hash_if_present(body.user.email, _norm_email)
    ph = _hash_if_present(body.user.phone, _norm_phone)
    external_id = _hash_if_present(body.user.external_id, _norm_text)

    fn = _hash_if_present(body.user.fn, _norm_text)
    ln = _hash_if_present(body.user.ln, _norm_text)
    ct = _hash_if_present(body.user.ct, _norm_text)
    country = _hash_if_present(body.user.country, _norm_text)
    zp = _hash_if_present(body.user.zp, _norm_text)

    user_data: dict[str, Any] = {
        "em": [em] if em else None,
        "ph": [ph] if ph else None,
        "external_id": [external_id] if external_id else None,
        "fn": [fn] if fn else None,
        "ln": [ln] if ln else None,
        "ct": [ct] if ct else None,
        "country": [country] if country else None,
        "zp": [zp] if zp else None,
        "fbp": body.user.fbp,
        "fbc": body.user.fbc,
        "client_ip_address": client_ip,
        "client_user_agent": client_ua,
    }
    user_data = {k: v for k, v in user_data.items() if v}

    event: dict[str, Any] = {
        "event_name": body.event_name,
        "event_time": event_time,
        "event_id": body.event_id,  # dedupe with pixel eventID
        "action_source": body.action_source,
        "event_source_url": body.event_source_url,
        "user_data": user_data,
        "custom_data": (body.custom_data.model_dump(exclude_none=True) if body.custom_data else None),
    }
    event = {k: v for k, v in event.items() if v is not None}

    request_payload: dict[str, Any] = {"data": [event]}
    test_event_code = body.test_event_code or os.getenv("META_TEST_EVENT_CODE")
    if test_event_code:
        request_payload["test_event_code"] = test_event_code

    status_code, resp = await _send_meta_capi(pixel_id=pixel_id, access_token=access_token, payload=request_payload)

    # Parse response
    meta_trace_id = None
    meta_events_received = 0
    meta_success = False
    meta_error_code = None
    meta_error_message = None

    if isinstance(resp, dict):
        meta_trace_id = resp.get("fbtrace_id") or resp.get("trace_id")
        meta_events_received = int(resp.get("events_received") or 0)
        meta_success = (200 <= status_code < 300) and (meta_events_received >= 1)

        if not meta_success:
            err = resp.get("error")
            if isinstance(err, dict):
                meta_error_code = err.get("code")
                meta_error_message = err.get("message")

    # Write QA log row (exact columns)
    qa = CapiQaLog(
        tenant_id=tenant_id,

        event_name=body.event_name,
        event_time=event_time,
        event_id=body.event_id,
        action_source=body.action_source,

        pixel_id=pixel_id,
        dataset_id=body.dataset_id,
        platform=body.platform,

        has_em=flags["has_em"],
        has_ph=flags["has_ph"],
        has_external_id=flags["has_external_id"],
        has_fbp=flags["has_fbp"],
        has_fbc=flags["has_fbc"],
        has_ip=flags["has_ip"],
        has_ua=flags["has_ua"],
        has_fn=flags["has_fn"],
        has_ln=flags["has_ln"],
        has_ct=flags["has_ct"],
        has_country=flags["has_country"],
        has_zp=flags["has_zp"],

        match_coverage_score=score,

        meta_trace_id=meta_trace_id,
        meta_success=meta_success,
        meta_error_code=meta_error_code,
        meta_error_message=meta_error_message,
        meta_events_received=meta_events_received,

        request_payload=request_payload,
        response_payload=resp if isinstance(resp, dict) else {"raw": str(resp)},
    )

    session.add(qa)
    # commit is handled by get_async_session() dependency
    await session.flush()  # ensure qa.id is available before response
    await session.refresh(qa)

    return MetaCapiCollectOut(
        ok=True,
        qa_log_id=qa.id,
        match_coverage_score=qa.match_coverage_score,
        meta_success=qa.meta_success,
        meta_events_received=qa.meta_events_received,
        meta_trace_id=qa.meta_trace_id,
        meta_error_code=qa.meta_error_code,
        meta_error_message=qa.meta_error_message,
    )

# ==========================================================
# GET /api/v1/meta/capi/qa/summary
# ==========================================================
@router.get("/qa/summary")
async def qa_summary(
    request: Request,
    date_from: date = Query(..., alias="from"),
    date_to: date = Query(..., alias="to"),
    event_name: Optional[str] = None,
    platform: Optional[str] = None,
    session: AsyncSession = Depends(get_async_session),
):
    tenant_id = getattr(request.state, "tenant_id", 1)

    dt_from = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc)
    dt_to = datetime.combine(date_to, datetime.max.time(), tzinfo=timezone.utc)

    day = cast(CapiQaLog.created_at, Date)

    stmt = (
        select(
            day.label("day"),
            func.count(CapiQaLog.id).label("events"),
            func.avg(CapiQaLog.match_coverage_score).label("avg_score"),
            func.avg(cast(CapiQaLog.meta_success, Integer)).label("success_rate"),
            func.sum(CapiQaLog.meta_events_received).label("events_received"),

            func.avg(cast(CapiQaLog.has_em, Integer)).label("p_has_em"),
            func.avg(cast(CapiQaLog.has_ph, Integer)).label("p_has_ph"),
            func.avg(cast(CapiQaLog.has_external_id, Integer)).label("p_has_external_id"),
            func.avg(cast(CapiQaLog.has_fbp, Integer)).label("p_has_fbp"),
            func.avg(cast(CapiQaLog.has_fbc, Integer)).label("p_has_fbc"),
            func.avg(cast(CapiQaLog.has_ip, Integer)).label("p_has_ip"),
            func.avg(cast(CapiQaLog.has_ua, Integer)).label("p_has_ua"),
        )
        .where(
            CapiQaLog.tenant_id == tenant_id,
            CapiQaLog.created_at >= dt_from,
            CapiQaLog.created_at <= dt_to,
        )
        .group_by(day)
        .order_by(day.asc())
    )

    if event_name:
        stmt = stmt.where(CapiQaLog.event_name == event_name)
    if platform:
        stmt = stmt.where(CapiQaLog.platform == platform)

    rows = (await session.execute(stmt)).mappings().all()

    series = []
    for r in rows:
        series.append({
            "day": str(r["day"]),
            "events": int(r["events"] or 0),
            "avg_score": float(r["avg_score"] or 0),
            "success_rate": float(r["success_rate"] or 0),  # 0..1
            "events_received": int(r["events_received"] or 0),
            "coverage": {
                "em": float(r["p_has_em"] or 0),
                "ph": float(r["p_has_ph"] or 0),
                "external_id": float(r["p_has_external_id"] or 0),
                "fbp": float(r["p_has_fbp"] or 0),
                "fbc": float(r["p_has_fbc"] or 0),
                "ip": float(r["p_has_ip"] or 0),
                "ua": float(r["p_has_ua"] or 0),
            }
        })

    return {
        "tenant_id": tenant_id,
        "from": str(date_from),
        "to": str(date_to),
        "event_name": event_name,
        "platform": platform,
        "series": series,
    }


# ==========================================================
# GET /api/v1/meta/capi/qa/stats
# Quick stats for dashboard widget
# ==========================================================
@router.get("/qa/stats")
async def qa_stats(
    request: Request,
    days: int = Query(30, ge=1, le=90),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get EMQ stats for the dashboard widget.
    Returns total events, average EMQ score, and quality distribution.
    """
    tenant_id = getattr(request.state, "tenant_id", 1)

    # Calculate date range
    dt_to = datetime.now(timezone.utc)
    dt_from = dt_to - timedelta(days=days)

    # Get total and average
    stmt_totals = (
        select(
            func.count(CapiQaLog.id).label("total_events"),
            func.avg(CapiQaLog.match_coverage_score).label("avg_score"),
        )
        .where(
            CapiQaLog.tenant_id == tenant_id,
            CapiQaLog.created_at >= dt_from,
            CapiQaLog.created_at <= dt_to,
        )
    )

    result = (await session.execute(stmt_totals)).mappings().first()
    total_events = int(result["total_events"] or 0)
    avg_score = float(result["avg_score"] or 0)

    # Convert 0-100 score to 0-10 EMQ scale
    avg_emq = avg_score / 10

    # Get quality distribution counts
    # Excellent: score >= 80 (EMQ >= 8)
    # Good: score >= 60 and < 80 (EMQ 6-8)
    # Fair: score >= 40 and < 60 (EMQ 4-6)
    # Poor: score < 40 (EMQ < 4)

    stmt_excellent = (
        select(func.count(CapiQaLog.id))
        .where(
            CapiQaLog.tenant_id == tenant_id,
            CapiQaLog.created_at >= dt_from,
            CapiQaLog.created_at <= dt_to,
            CapiQaLog.match_coverage_score >= 80,
        )
    )
    excellent_count = (await session.execute(stmt_excellent)).scalar() or 0

    stmt_good = (
        select(func.count(CapiQaLog.id))
        .where(
            CapiQaLog.tenant_id == tenant_id,
            CapiQaLog.created_at >= dt_from,
            CapiQaLog.created_at <= dt_to,
            CapiQaLog.match_coverage_score >= 60,
            CapiQaLog.match_coverage_score < 80,
        )
    )
    good_count = (await session.execute(stmt_good)).scalar() or 0

    stmt_fair = (
        select(func.count(CapiQaLog.id))
        .where(
            CapiQaLog.tenant_id == tenant_id,
            CapiQaLog.created_at >= dt_from,
            CapiQaLog.created_at <= dt_to,
            CapiQaLog.match_coverage_score >= 40,
            CapiQaLog.match_coverage_score < 60,
        )
    )
    fair_count = (await session.execute(stmt_fair)).scalar() or 0

    stmt_poor = (
        select(func.count(CapiQaLog.id))
        .where(
            CapiQaLog.tenant_id == tenant_id,
            CapiQaLog.created_at >= dt_from,
            CapiQaLog.created_at <= dt_to,
            CapiQaLog.match_coverage_score < 40,
        )
    )
    poor_count = (await session.execute(stmt_poor)).scalar() or 0

    return {
        "total_events": total_events,
        "avg_emq": round(avg_emq, 2),
        "excellent_count": excellent_count,
        "good_count": good_count,
        "fair_count": fair_count,
        "poor_count": poor_count,
    }


# ==========================================================
# GET /api/v1/meta/capi/qa/alerts
# EMQ alerts for dashboard
# ==========================================================
@router.get("/qa/alerts")
async def qa_alerts(
    request: Request,
    days: int = Query(7, ge=1, le=30),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get EMQ alerts based on recent performance.
    Returns alerts for low scores, missing parameters, high error rates, etc.
    """
    tenant_id = getattr(request.state, "tenant_id", 1)

    dt_to = datetime.now(timezone.utc)
    dt_from = dt_to - timedelta(days=days)

    alerts = []

    # 1. Check average EMQ score
    stmt_avg = (
        select(
            func.avg(CapiQaLog.match_coverage_score).label("avg_score"),
            func.count(CapiQaLog.id).label("total"),
        )
        .where(
            CapiQaLog.tenant_id == tenant_id,
            CapiQaLog.created_at >= dt_from,
            CapiQaLog.created_at <= dt_to,
        )
    )
    result = (await session.execute(stmt_avg)).mappings().first()
    avg_score = float(result["avg_score"] or 0)
    total_events = int(result["total"] or 0)

    if total_events == 0:
        alerts.append({
            "id": "no_events",
            "severity": "warning",
            "title": "No Events Tracked",
            "message": f"No CAPI events received in the last {days} days. Verify your integration.",
            "metric": None,
            "threshold": None,
        })
    else:
        if avg_score < 40:
            alerts.append({
                "id": "low_emq_critical",
                "severity": "critical",
                "title": "Critical: Very Low EMQ Score",
                "message": f"Average EMQ is {avg_score/10:.1f}/10. Meta may not match most events.",
                "metric": round(avg_score/10, 1),
                "threshold": 4.0,
            })
        elif avg_score < 60:
            alerts.append({
                "id": "low_emq_warning",
                "severity": "warning",
                "title": "Low EMQ Score",
                "message": f"Average EMQ is {avg_score/10:.1f}/10. Consider adding more user parameters.",
                "metric": round(avg_score/10, 1),
                "threshold": 6.0,
            })

    # 2. Check error rate
    stmt_errors = (
        select(func.count(CapiQaLog.id))
        .where(
            CapiQaLog.tenant_id == tenant_id,
            CapiQaLog.created_at >= dt_from,
            CapiQaLog.created_at <= dt_to,
            CapiQaLog.meta_success == False,
        )
    )
    error_count = (await session.execute(stmt_errors)).scalar() or 0

    if total_events > 0:
        error_rate = (error_count / total_events) * 100
        if error_rate > 10:
            alerts.append({
                "id": "high_error_rate",
                "severity": "critical",
                "title": "High Error Rate",
                "message": f"{error_rate:.1f}% of events failed. Check API credentials and event format.",
                "metric": round(error_rate, 1),
                "threshold": 10.0,
            })
        elif error_rate > 5:
            alerts.append({
                "id": "elevated_error_rate",
                "severity": "warning",
                "title": "Elevated Error Rate",
                "message": f"{error_rate:.1f}% of events failed. Review error logs for issues.",
                "metric": round(error_rate, 1),
                "threshold": 5.0,
            })

    # 3. Check parameter coverage
    stmt_coverage = (
        select(
            func.avg(cast(CapiQaLog.has_em, Integer)).label("em_rate"),
            func.avg(cast(CapiQaLog.has_ph, Integer)).label("ph_rate"),
            func.avg(cast(CapiQaLog.has_fbp, Integer)).label("fbp_rate"),
            func.avg(cast(CapiQaLog.has_fbc, Integer)).label("fbc_rate"),
            func.avg(cast(CapiQaLog.has_external_id, Integer)).label("ext_id_rate"),
        )
        .where(
            CapiQaLog.tenant_id == tenant_id,
            CapiQaLog.created_at >= dt_from,
            CapiQaLog.created_at <= dt_to,
        )
    )
    coverage = (await session.execute(stmt_coverage)).mappings().first()

    em_rate = float(coverage["em_rate"] or 0) * 100
    ph_rate = float(coverage["ph_rate"] or 0) * 100
    fbp_rate = float(coverage["fbp_rate"] or 0) * 100
    fbc_rate = float(coverage["fbc_rate"] or 0) * 100

    # Alert for missing email (critical identifier)
    if em_rate < 50 and total_events > 0:
        alerts.append({
            "id": "low_email_coverage",
            "severity": "warning",
            "title": "Low Email Coverage",
            "message": f"Only {em_rate:.0f}% of events include email. Email is key for matching.",
            "metric": round(em_rate, 0),
            "threshold": 50,
        })

    # Alert for missing browser cookies
    if fbp_rate < 30 and total_events > 0:
        alerts.append({
            "id": "low_fbp_coverage",
            "severity": "info",
            "title": "Low Cookie Coverage",
            "message": f"Only {fbp_rate:.0f}% of events include _fbp cookie. Add cookie tracking.",
            "metric": round(fbp_rate, 0),
            "threshold": 30,
        })

    return {
        "tenant_id": tenant_id,
        "period_days": days,
        "total_events": total_events,
        "alerts": alerts,
        "alert_count": len(alerts),
    }


# ==========================================================
# GET /api/v1/meta/capi/qa/recommendations
# EMQ improvement recommendations
# ==========================================================
@router.get("/qa/recommendations")
async def qa_recommendations(
    request: Request,
    days: int = Query(7, ge=1, le=30),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get actionable recommendations to improve EMQ score.
    Analyzes current data and suggests specific improvements.
    """
    tenant_id = getattr(request.state, "tenant_id", 1)

    dt_to = datetime.now(timezone.utc)
    dt_from = dt_to - timedelta(days=days)

    # Get current coverage stats
    stmt = (
        select(
            func.count(CapiQaLog.id).label("total"),
            func.avg(CapiQaLog.match_coverage_score).label("avg_score"),
            func.avg(cast(CapiQaLog.has_em, Integer)).label("em_rate"),
            func.avg(cast(CapiQaLog.has_ph, Integer)).label("ph_rate"),
            func.avg(cast(CapiQaLog.has_fbp, Integer)).label("fbp_rate"),
            func.avg(cast(CapiQaLog.has_fbc, Integer)).label("fbc_rate"),
            func.avg(cast(CapiQaLog.has_external_id, Integer)).label("ext_id_rate"),
            func.avg(cast(CapiQaLog.has_ip, Integer)).label("ip_rate"),
            func.avg(cast(CapiQaLog.has_ua, Integer)).label("ua_rate"),
        )
        .where(
            CapiQaLog.tenant_id == tenant_id,
            CapiQaLog.created_at >= dt_from,
            CapiQaLog.created_at <= dt_to,
        )
    )
    result = (await session.execute(stmt)).mappings().first()

    total = int(result["total"] or 0)
    if total == 0:
        return {
            "tenant_id": tenant_id,
            "period_days": days,
            "current_emq": 0,
            "potential_emq": 0,
            "recommendations": [{
                "id": "start_tracking",
                "priority": "high",
                "category": "setup",
                "title": "Start Sending Events",
                "description": "No events detected. Implement CAPI integration to begin tracking.",
                "impact": "+10.0 EMQ",
                "effort": "medium",
            }],
        }

    avg_score = float(result["avg_score"] or 0)
    current_emq = avg_score / 10

    em_rate = float(result["em_rate"] or 0)
    ph_rate = float(result["ph_rate"] or 0)
    fbp_rate = float(result["fbp_rate"] or 0)
    fbc_rate = float(result["fbc_rate"] or 0)
    ext_id_rate = float(result["ext_id_rate"] or 0)
    ip_rate = float(result["ip_rate"] or 0)
    ua_rate = float(result["ua_rate"] or 0)

    recommendations = []
    potential_gain = 0

    # Priority order based on Meta's matching algorithm weights
    # Email/Phone are highest value, then cookies, then other identifiers

    if em_rate < 0.8:
        gain = (0.8 - em_rate) * 2.5  # Email is worth ~25% of score
        potential_gain += gain
        recommendations.append({
            "id": "add_email",
            "priority": "high",
            "category": "identifier",
            "title": "Increase Email Coverage",
            "description": f"Currently {em_rate*100:.0f}% of events have email. Hash and send user emails for better matching.",
            "impact": f"+{gain:.1f} EMQ",
            "effort": "low",
            "current": round(em_rate * 100),
            "target": 80,
        })

    if ph_rate < 0.5:
        gain = (0.5 - ph_rate) * 1.5  # Phone is worth ~15% of score
        potential_gain += gain
        recommendations.append({
            "id": "add_phone",
            "priority": "high",
            "category": "identifier",
            "title": "Add Phone Numbers",
            "description": f"Currently {ph_rate*100:.0f}% of events have phone. Include hashed phone numbers.",
            "impact": f"+{gain:.1f} EMQ",
            "effort": "low",
            "current": round(ph_rate * 100),
            "target": 50,
        })

    if fbp_rate < 0.7:
        gain = (0.7 - fbp_rate) * 1.5  # _fbp cookie is worth ~15%
        potential_gain += gain
        recommendations.append({
            "id": "add_fbp_cookie",
            "priority": "medium",
            "category": "cookie",
            "title": "Capture _fbp Cookie",
            "description": f"Currently {fbp_rate*100:.0f}% have _fbp. Read and send the Meta Pixel browser cookie.",
            "impact": f"+{gain:.1f} EMQ",
            "effort": "low",
            "current": round(fbp_rate * 100),
            "target": 70,
        })

    if fbc_rate < 0.3:
        gain = (0.3 - fbc_rate) * 1.0  # _fbc click ID is worth ~10%
        potential_gain += gain
        recommendations.append({
            "id": "add_fbc_cookie",
            "priority": "medium",
            "category": "cookie",
            "title": "Capture Click ID (_fbc)",
            "description": f"Currently {fbc_rate*100:.0f}% have _fbc. Capture fbclid from URL and store as _fbc cookie.",
            "impact": f"+{gain:.1f} EMQ",
            "effort": "medium",
            "current": round(fbc_rate * 100),
            "target": 30,
        })

    if ext_id_rate < 0.6:
        gain = (0.6 - ext_id_rate) * 1.0  # External ID worth ~10%
        potential_gain += gain
        recommendations.append({
            "id": "add_external_id",
            "priority": "medium",
            "category": "identifier",
            "title": "Include External ID",
            "description": f"Currently {ext_id_rate*100:.0f}% have external_id. Send your user ID for cross-device matching.",
            "impact": f"+{gain:.1f} EMQ",
            "effort": "low",
            "current": round(ext_id_rate * 100),
            "target": 60,
        })

    if ip_rate < 0.9:
        gain = (0.9 - ip_rate) * 0.5  # IP worth ~5%
        potential_gain += gain
        recommendations.append({
            "id": "add_ip",
            "priority": "low",
            "category": "context",
            "title": "Include Client IP",
            "description": f"Currently {ip_rate*100:.0f}% have IP. Send client_ip_address for geo-matching.",
            "impact": f"+{gain:.1f} EMQ",
            "effort": "low",
            "current": round(ip_rate * 100),
            "target": 90,
        })

    if ua_rate < 0.9:
        gain = (0.9 - ua_rate) * 0.5  # User Agent worth ~5%
        potential_gain += gain
        recommendations.append({
            "id": "add_user_agent",
            "priority": "low",
            "category": "context",
            "title": "Include User Agent",
            "description": f"Currently {ua_rate*100:.0f}% have UA. Send client_user_agent for device matching.",
            "impact": f"+{gain:.1f} EMQ",
            "effort": "low",
            "current": round(ua_rate * 100),
            "target": 90,
        })

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    recommendations.sort(key=lambda x: priority_order.get(x["priority"], 3))

    potential_emq = min(10.0, current_emq + potential_gain)

    return {
        "tenant_id": tenant_id,
        "period_days": days,
        "current_emq": round(current_emq, 2),
        "potential_emq": round(potential_emq, 2),
        "potential_gain": round(potential_gain, 2),
        "recommendations": recommendations[:6],  # Top 6 recommendations
        "recommendation_count": len(recommendations),
    }


# ==========================================================
# GET /api/v1/meta/capi/qa/errors
# ==========================================================
@router.get("/qa/errors")
async def qa_errors(
    request: Request,
    date_from: date = Query(..., alias="from"),
    date_to: date = Query(..., alias="to"),
    event_name: Optional[str] = None,
    platform: Optional[str] = None,
    limit: int = Query(20, ge=1, le=200),
    session: AsyncSession = Depends(get_async_session),
):
    tenant_id = getattr(request.state, "tenant_id", 1)

    dt_from = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc)
    dt_to = datetime.combine(date_to, datetime.max.time(), tzinfo=timezone.utc)

    stmt = (
        select(
            CapiQaLog.meta_error_code.label("code"),
            CapiQaLog.meta_error_message.label("message"),
            func.count(CapiQaLog.id).label("count"),
            func.max(CapiQaLog.created_at).label("last_seen"),
        )
        .where(
            CapiQaLog.tenant_id == tenant_id,
            CapiQaLog.created_at >= dt_from,
            CapiQaLog.created_at <= dt_to,
            CapiQaLog.meta_success == False,  # noqa: E712
        )
        .group_by(CapiQaLog.meta_error_code, CapiQaLog.meta_error_message)
        .order_by(func.count(CapiQaLog.id).desc())
        .limit(limit)
    )

    if event_name:
        stmt = stmt.where(CapiQaLog.event_name == event_name)
    if platform:
        stmt = stmt.where(CapiQaLog.platform == platform)

    rows = (await session.execute(stmt)).mappings().all()

    return {
        "tenant_id": tenant_id,
        "from": str(date_from),
        "to": str(date_to),
        "event_name": event_name,
        "platform": platform,
        "items": [
            {
                "code": r["code"],
                "message": r["message"],
                "count": int(r["count"] or 0),
                "last_seen": r["last_seen"].isoformat() if r["last_seen"] else None,
            }
            for r in rows
        ],
    }


# ==========================================================
# GET /api/v1/meta/capi/qa/event-breakdown
# ==========================================================
@router.get("/qa/event-breakdown")
async def qa_event_breakdown(
    request: Request,
    date_from: date = Query(..., alias="from"),
    date_to: date = Query(..., alias="to"),
    platform: Optional[str] = None,
    session: AsyncSession = Depends(get_async_session),
):
    tenant_id = getattr(request.state, "tenant_id", 1)

    dt_from = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc)
    dt_to = datetime.combine(date_to, datetime.max.time(), tzinfo=timezone.utc)

    stmt = (
        select(
            CapiQaLog.event_name.label("event_name"),
            func.count(CapiQaLog.id).label("events"),
            func.avg(CapiQaLog.match_coverage_score).label("avg_score"),
            func.avg(cast(CapiQaLog.meta_success, Integer)).label("success_rate"),
            func.sum(CapiQaLog.meta_events_received).label("events_received"),
            func.avg(cast(CapiQaLog.has_em, Integer)).label("p_has_em"),
            func.avg(cast(CapiQaLog.has_ph, Integer)).label("p_has_ph"),
            func.avg(cast(CapiQaLog.has_external_id, Integer)).label("p_has_external_id"),
            func.avg(cast(CapiQaLog.has_fbp, Integer)).label("p_has_fbp"),
            func.avg(cast(CapiQaLog.has_fbc, Integer)).label("p_has_fbc"),
            func.avg(cast(CapiQaLog.has_ip, Integer)).label("p_has_ip"),
            func.avg(cast(CapiQaLog.has_ua, Integer)).label("p_has_ua"),
        )
        .where(
            CapiQaLog.tenant_id == tenant_id,
            CapiQaLog.created_at >= dt_from,
            CapiQaLog.created_at <= dt_to,
        )
        .group_by(CapiQaLog.event_name)
        .order_by(func.count(CapiQaLog.id).desc())
    )

    if platform:
        stmt = stmt.where(CapiQaLog.platform == platform)

    rows = (await session.execute(stmt)).mappings().all()

    return {
        "tenant_id": tenant_id,
        "from": str(date_from),
        "to": str(date_to),
        "platform": platform,
        "items": [
            {
                "event_name": r["event_name"],
                "events": int(r["events"] or 0),
                "avg_score": float(r["avg_score"] or 0),
                "success_rate": float(r["success_rate"] or 0),
                "events_received": int(r["events_received"] or 0),
                "coverage": {
                    "em": float(r["p_has_em"] or 0),
                    "ph": float(r["p_has_ph"] or 0),
                    "external_id": float(r["p_has_external_id"] or 0),
                    "fbp": float(r["p_has_fbp"] or 0),
                    "fbc": float(r["p_has_fbc"] or 0),
                    "ip": float(r["p_has_ip"] or 0),
                    "ua": float(r["p_has_ua"] or 0),
                }
            }
            for r in rows
        ],
    }


# ==========================================================
# GET /api/v1/meta/capi/qa/dedupe
# ==========================================================
@router.get("/qa/dedupe")
async def qa_dedupe(
    request: Request,
    date_from: date = Query(..., alias="from"),
    date_to: date = Query(..., alias="to"),
    event_name: Optional[str] = None,
    platform: Optional[str] = None,
    window_minutes: int = Query(10, ge=1, le=120),
    top: int = Query(25, ge=1, le=200),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Detect duplicate CAPI sends by event_id.
    NOTE: This detects duplicates in *CAPI logs*. If you also log Pixel separately, use dedupe-v2.
    """
    tenant_id = getattr(request.state, "tenant_id", 1)

    dt_from = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc)
    dt_to = datetime.combine(date_to, datetime.max.time(), tzinfo=timezone.utc)

    base_filters = [
        CapiQaLog.tenant_id == tenant_id,
        CapiQaLog.created_at >= dt_from,
        CapiQaLog.created_at <= dt_to,
    ]
    if event_name:
        base_filters.append(CapiQaLog.event_name == event_name)
    if platform:
        base_filters.append(CapiQaLog.platform == platform)

    # totals
    total_stmt = select(
        func.count(CapiQaLog.id).label("total"),
        func.count(func.distinct(CapiQaLog.event_id)).label("unique_event_ids"),
    ).where(*base_filters)

    totals = (await session.execute(total_stmt)).mappings().one()
    total = int(totals["total"] or 0)
    unique_event_ids = int(totals["unique_event_ids"] or 0)

    duplicate_rows = max(0, total - unique_event_ids)
    duplicate_rate = float(duplicate_rows / total) if total else 0.0

    # top duplicated event_ids
    dup_stmt = (
        select(
            CapiQaLog.event_id.label("event_id"),
            func.count(CapiQaLog.id).label("count"),
            func.max(CapiQaLog.created_at).label("last_seen"),
            func.min(CapiQaLog.created_at).label("first_seen"),
        )
        .where(*base_filters)
        .group_by(CapiQaLog.event_id)
        .having(func.count(CapiQaLog.id) > 1)
        .order_by(func.count(CapiQaLog.id).desc())
        .limit(top)
    )

    dups = (await session.execute(dup_stmt)).mappings().all()

    items = []
    for r in dups:
        items.append({
            "event_id": r["event_id"],
            "count": int(r["count"] or 0),
            "first_seen": r["first_seen"].isoformat() if r["first_seen"] else None,
            "last_seen": r["last_seen"].isoformat() if r["last_seen"] else None,
        })

    return {
        "tenant_id": tenant_id,
        "from": str(date_from),
        "to": str(date_to),
        "event_name": event_name,
        "platform": platform,
        "window_minutes": window_minutes,
        "total": total,
        "unique_event_ids": unique_event_ids,
        "duplicate_rows": duplicate_rows,
        "duplicate_rate": duplicate_rate,
        "top_duplicates": items,
    }


# ==========================================================
# GET /api/v1/meta/capi/qa/diagnostics
# ==========================================================
@router.get("/qa/diagnostics")
async def qa_diagnostics(
    request: Request,
    date_from: date = Query(..., alias="from"),
    date_to: date = Query(..., alias="to"),
    event_name: Optional[str] = None,
    platform: Optional[str] = None,
    session: AsyncSession = Depends(get_async_session),
):
    tenant_id = getattr(request.state, "tenant_id", 1)

    dt_from = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc)
    dt_to = datetime.combine(date_to, datetime.max.time(), tzinfo=timezone.utc)

    day = cast(CapiQaLog.created_at, Date)

    base_filters = [
        CapiQaLog.tenant_id == tenant_id,
        CapiQaLog.created_at >= dt_from,
        CapiQaLog.created_at <= dt_to,
    ]
    if event_name:
        base_filters.append(CapiQaLog.event_name == event_name)
    if platform:
        base_filters.append(CapiQaLog.platform == platform)

    stmt = (
        select(
            day.label("day"),
            func.count(CapiQaLog.id).label("events"),
            func.avg(CapiQaLog.match_coverage_score).label("avg_score"),
            func.avg(cast(CapiQaLog.meta_success, Integer)).label("success_rate"),
            func.sum(CapiQaLog.meta_events_received).label("events_received"),

            func.avg(cast(CapiQaLog.has_em, Integer)).label("p_has_em"),
            func.avg(cast(CapiQaLog.has_ph, Integer)).label("p_has_ph"),
            func.avg(cast(CapiQaLog.has_external_id, Integer)).label("p_has_external_id"),
            func.avg(cast(CapiQaLog.has_fbp, Integer)).label("p_has_fbp"),
            func.avg(cast(CapiQaLog.has_fbc, Integer)).label("p_has_fbc"),
            func.avg(cast(CapiQaLog.has_ip, Integer)).label("p_has_ip"),
            func.avg(cast(CapiQaLog.has_ua, Integer)).label("p_has_ua"),
        )
        .where(*base_filters)
        .group_by(day)
        .order_by(day.asc())
    )

    rows = (await session.execute(stmt)).mappings().all()
    series = []
    for r in rows:
        series.append({
            "day": str(r["day"]),
            "events": int(r["events"] or 0),
            "avg_score": float(r["avg_score"] or 0),
            "success_rate": float(r["success_rate"] or 0),
            "events_received": int(r["events_received"] or 0),
            "coverage": {
                "em": float(r["p_has_em"] or 0),
                "ph": float(r["p_has_ph"] or 0),
                "external_id": float(r["p_has_external_id"] or 0),
                "fbp": float(r["p_has_fbp"] or 0),
                "fbc": float(r["p_has_fbc"] or 0),
                "ip": float(r["p_has_ip"] or 0),
                "ua": float(r["p_has_ua"] or 0),
            }
        })

    alerts = []
    if len(series) >= 2:
        cur = series[-1]
        prev = series[-2]

        def add_alert(severity: str, title: str, metric: str, current: float, previous: float, recommendation: str):
            alerts.append({
                "severity": severity,
                "title": title,
                "metric": metric,
                "current": current,
                "previous": previous,
                "delta": current - previous,
                "recommendation": recommendation,
                "day": cur["day"],
                "compare_to": prev["day"],
            })

        # Success rate drop
        if cur["success_rate"] < prev["success_rate"] - 0.02:
            add_alert(
                "critical" if cur["success_rate"] < 0.90 else "warning",
                "Meta delivery success rate dropped",
                "success_rate",
                cur["success_rate"],
                prev["success_rate"],
                "Check META_CAPI_TOKEN validity, rate limits, and payload errors. Review /qa/errors and add retry/backoff if needed.",
            )

        # Avg score drop
        if cur["avg_score"] < prev["avg_score"] - 8:
            add_alert(
                "warning",
                "Match coverage score dropped",
                "avg_score",
                cur["avg_score"],
                prev["avg_score"],
                "Check which identifiers lost coverage (email/phone/external_id/fbp/fbc/ip/ua). This usually indicates consent changes, cookie loss, or form field changes.",
            )

        # Coverage drops (per identifier)
        for k in ["em", "ph", "external_id", "fbp", "fbc", "ip", "ua"]:
            c = float(cur["coverage"][k])
            p = float(prev["coverage"][k])
            if c < p - 0.10:
                rec = {
                    "em": "Email missing: check form capture, normalization, hashing (lowercase/trim), and that you're not sending empty strings.",
                    "ph": "Phone missing: check E.164 formatting, normalization, and that phone is passed to server before hashing.",
                    "external_id": "External_id missing: ensure user/lead id exists at event time and is stable (don't regenerate ids).",
                    "fbp": "fbp coverage drop: cookie loss likely. Check consent mode, subdomain/cross-domain, and ensure _fbp cookie is readable on the page where event fires.",
                    "fbc": "fbc coverage drop: click id not captured. Ensure fbclid is preserved in landing URLs and stored. Check redirects/UTM propagation.",
                    "ip": "IP missing: check reverse proxy headers and whether request.client.host is correct behind your load balancer (set trusted proxies).",
                    "ua": "User-Agent missing: check proxy stripping headers. Ensure you pass UA from request headers into CAPI user_data.",
                }[k]
                add_alert(
                    "warning",
                    f"{k} coverage dropped",
                    f"coverage.{k}",
                    c, p,
                    rec,
                )

        # events_received mismatch
        if cur["events"] > 0:
            ratio = (cur["events_received"] / cur["events"]) if cur["events"] else 0.0
            prev_ratio = (prev["events_received"] / prev["events"]) if prev["events"] else 0.0
            if ratio < prev_ratio - 0.10:
                add_alert(
                    "warning",
                    "Meta events_received ratio dropped",
                    "events_received_ratio",
                    ratio,
                    prev_ratio,
                    "Meta is accepting fewer events per logged send. Check /qa/errors for invalid payloads, permissions, or event formatting issues.",
                )

    return {
        "tenant_id": tenant_id,
        "from": str(date_from),
        "to": str(date_to),
        "event_name": event_name,
        "platform": platform,
        "series_points": len(series),
        "alerts": alerts,
        "series_tail": series[-7:],
    }


# ==========================================================
# Pixel Event Log Schema
# ==========================================================
class PixelLogIn(BaseModel):
    event_name: str
    event_time: Optional[int] = None
    event_id: str = Field(..., min_length=6)
    event_source_url: Optional[str] = None


# ==========================================================
# POST /api/v1/meta/capi/pixel/log
# ==========================================================
@router.post("/pixel/log")
async def pixel_log(
    request: Request,
    body: PixelLogIn,
    session: AsyncSession = Depends(get_async_session),
):
    """Log a pixel event for dedupe tracking."""
    tenant_id = getattr(request.state, "tenant_id", 1)
    event_time = body.event_time or int(time.time())
    ua = request.headers.get("user-agent")

    row = PixelEventLog(
        tenant_id=tenant_id,
        event_id=body.event_id,
        event_name=body.event_name,
        event_time=event_time,
        event_source_url=body.event_source_url,
        user_agent=ua,
    )

    session.add(row)
    await session.flush()
    return {"ok": True, "id": row.id}


# ==========================================================
# GET /api/v1/meta/capi/qa/dedupe-v2 (Pixel vs CAPI)
# ==========================================================
@router.get("/qa/dedupe-v2")
async def qa_dedupe_v2(
    request: Request,
    date_from: date = Query(..., alias="from"),
    date_to: date = Query(..., alias="to"),
    event_name: Optional[str] = None,
    session: AsyncSession = Depends(get_async_session),
    top: int = Query(20, ge=1, le=200),
):
    """
    Compare Pixel vs CAPI event coverage.
    Returns: both_count, pixel_only, capi_only, mismatch_rate, top_missing lists.
    """
    tenant_id = getattr(request.state, "tenant_id", 1)

    dt_from = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc)
    dt_to = datetime.combine(date_to, datetime.max.time(), tzinfo=timezone.utc)

    pixel_filters = [
        PixelEventLog.tenant_id == tenant_id,
        PixelEventLog.created_at >= dt_from,
        PixelEventLog.created_at <= dt_to,
    ]
    capi_filters = [
        CapiQaLog.tenant_id == tenant_id,
        CapiQaLog.created_at >= dt_from,
        CapiQaLog.created_at <= dt_to,
    ]
    if event_name:
        pixel_filters.append(PixelEventLog.event_name == event_name)
        capi_filters.append(CapiQaLog.event_name == event_name)

    # Totals
    pixel_total = int((await session.execute(
        select(func.count(PixelEventLog.id)).where(*pixel_filters)
    )).scalar() or 0)

    capi_total = int((await session.execute(
        select(func.count(CapiQaLog.id)).where(*capi_filters)
    )).scalar() or 0)

    # Distinct event_id counts
    pixel_distinct = int((await session.execute(
        select(func.count(func.distinct(PixelEventLog.event_id))).where(*pixel_filters)
    )).scalar() or 0)

    capi_distinct = int((await session.execute(
        select(func.count(func.distinct(CapiQaLog.event_id))).where(*capi_filters)
    )).scalar() or 0)

    # Both (event_id exists in both tables)
    both_stmt = (
        select(func.count(func.distinct(PixelEventLog.event_id)))
        .select_from(PixelEventLog)
        .join(CapiQaLog, (CapiQaLog.event_id == PixelEventLog.event_id) & (CapiQaLog.tenant_id == PixelEventLog.tenant_id))
        .where(*pixel_filters)
    )
    both_count = int((await session.execute(both_stmt)).scalar() or 0)

    pixel_only = max(0, pixel_distinct - both_count)
    capi_only = max(0, capi_distinct - both_count)

    denom = max(1, pixel_distinct + capi_distinct - both_count)
    mismatch_rate = float((pixel_only + capi_only) / denom)

    # Top missing CAPI (pixel ids not in capi)
    missing_capi_stmt = (
        select(PixelEventLog.event_id, func.count(PixelEventLog.id).label("count"), func.max(PixelEventLog.created_at).label("last_seen"))
        .where(*pixel_filters)
        .where(~PixelEventLog.event_id.in_(select(CapiQaLog.event_id).where(*capi_filters)))
        .group_by(PixelEventLog.event_id)
        .order_by(func.count(PixelEventLog.id).desc())
        .limit(top)
    )
    missing_capi = (await session.execute(missing_capi_stmt)).mappings().all()

    # Top missing Pixel (capi ids not in pixel)
    missing_pixel_stmt = (
        select(CapiQaLog.event_id, func.count(CapiQaLog.id).label("count"), func.max(CapiQaLog.created_at).label("last_seen"))
        .where(*capi_filters)
        .where(~CapiQaLog.event_id.in_(select(PixelEventLog.event_id).where(*pixel_filters)))
        .group_by(CapiQaLog.event_id)
        .order_by(func.count(CapiQaLog.id).desc())
        .limit(top)
    )
    missing_pixel = (await session.execute(missing_pixel_stmt)).mappings().all()

    return {
        "tenant_id": tenant_id,
        "from": str(date_from),
        "to": str(date_to),
        "event_name": event_name,
        "pixel_total": pixel_total,
        "capi_total": capi_total,
        "pixel_distinct_event_ids": pixel_distinct,
        "capi_distinct_event_ids": capi_distinct,
        "both_distinct_event_ids": both_count,
        "pixel_only_distinct_event_ids": pixel_only,
        "capi_only_distinct_event_ids": capi_only,
        "mismatch_rate": mismatch_rate,
        "top_missing_capi": [
            {"event_id": r["event_id"], "count": int(r["count"]), "last_seen": r["last_seen"].isoformat() if r["last_seen"] else None}
            for r in missing_capi
        ],
        "top_missing_pixel": [
            {"event_id": r["event_id"], "count": int(r["count"]), "last_seen": r["last_seen"].isoformat() if r["last_seen"] else None}
            for r in missing_pixel
        ],
    }
