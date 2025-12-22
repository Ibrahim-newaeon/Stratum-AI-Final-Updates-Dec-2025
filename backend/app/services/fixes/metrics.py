"""
EMQ Metrics Computation
Shared function to compute before/after metrics for fix verification.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select, func, cast, Integer
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CapiQaLog


async def compute_platform_metrics(
    session: AsyncSession,
    tenant_id: int,
    platform: str,
    dt_from: datetime,
    dt_to: datetime,
    event_name: Optional[str] = None,
) -> dict:
    """
    Compute EMQ metrics for a given tenant, platform, and time range.
    Used for before/after comparison in fix runs.
    """
    filters = [
        CapiQaLog.tenant_id == tenant_id,
        CapiQaLog.platform == platform,
        CapiQaLog.created_at >= dt_from,
        CapiQaLog.created_at <= dt_to,
    ]
    if event_name:
        filters.append(CapiQaLog.event_name == event_name)

    stmt = select(
        func.count(CapiQaLog.id).label("events"),
        func.count(func.distinct(CapiQaLog.event_id)).label("unique_event_ids"),
        func.avg(CapiQaLog.match_coverage_score).label("avg_score"),
        func.avg(cast(CapiQaLog.meta_success, Integer)).label("success_rate"),
        func.avg(cast(CapiQaLog.has_em, Integer)).label("p_has_em"),
        func.avg(cast(CapiQaLog.has_ph, Integer)).label("p_has_ph"),
        func.avg(cast(CapiQaLog.has_external_id, Integer)).label("p_has_external_id"),
        func.avg(cast(CapiQaLog.has_fbp, Integer)).label("p_has_fbp"),
        func.avg(cast(CapiQaLog.has_fbc, Integer)).label("p_has_fbc"),
        func.avg(cast(CapiQaLog.has_ip, Integer)).label("p_has_ip"),
        func.avg(cast(CapiQaLog.has_ua, Integer)).label("p_has_ua"),
    ).where(*filters)

    result = await session.execute(stmt)
    r = result.mappings().one()

    events = int(r["events"] or 0)
    unique_event_ids = int(r["unique_event_ids"] or 0)
    dup_rows = max(0, events - unique_event_ids)
    dup_rate = float(dup_rows / events) if events else 0.0

    return {
        "events": events,
        "unique_event_ids": unique_event_ids,
        "duplicate_rows": dup_rows,
        "duplicate_rate": round(dup_rate, 4),
        "avg_score": round(float(r["avg_score"] or 0.0), 2),
        "success_rate": round(float(r["success_rate"] or 0.0), 4),
        "coverage": {
            "em": round(float(r["p_has_em"] or 0.0), 4),
            "ph": round(float(r["p_has_ph"] or 0.0), 4),
            "external_id": round(float(r["p_has_external_id"] or 0.0), 4),
            "fbp": round(float(r["p_has_fbp"] or 0.0), 4),
            "fbc": round(float(r["p_has_fbc"] or 0.0), 4),
            "ip": round(float(r["p_has_ip"] or 0.0), 4),
            "ua": round(float(r["p_has_ua"] or 0.0), 4),
        },
    }
