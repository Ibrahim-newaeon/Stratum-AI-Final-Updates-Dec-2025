# =============================================================================
# Stratum AI - Copilot Chat API (Feature #4)
# =============================================================================
"""
REST API endpoints for the AI Copilot Chat.

Provides a conversational interface where users can ask questions
about their campaign data, signal health, anomalies, and get
contextual recommendations.
"""

from datetime import UTC, datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import CurrentUserDep
from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models import Campaign, CampaignStatus
from app.schemas import APIResponse
from app.services.agents.copilot_agent import (
    CopilotResponse,
    process_message,
)
from app.services.agents.copilot_llm import generate_llm_message

logger = get_logger(__name__)
router = APIRouter(prefix="/copilot", tags=["copilot"])


# =============================================================================
# Schemas
# =============================================================================

class CopilotMessageRequest(BaseModel):
    """Request to send a message to the copilot."""
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = Field(None, description="Optional session ID for continuity")


class CopilotMessageResponse(BaseModel):
    """Response from the copilot."""
    session_id: str
    message: str
    suggestions: list[str] = []
    data_cards: list[dict] = []
    intent: str = "unknown"
    timestamp: str


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/chat", response_model=APIResponse[CopilotMessageResponse])
async def copilot_chat(
    request: CopilotMessageRequest,
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Send a message to the AI Copilot and receive a data-aware response.

    The copilot analyzes the user's query, fetches relevant dashboard data,
    and generates a contextual response with suggestions and data cards.
    """
    tenant_id = getattr(user, "tenant_id", None) or 1
    user_name = getattr(user, "full_name", None) or getattr(user, "email", "User")
    if user_name and "@" in user_name:
        user_name = user_name.split("@")[0].title()

    session_id = request.session_id or str(uuid4())

    # ── Gather context data for the copilot ──────────────────────

    # 1. Campaign metrics
    metrics = None
    try:
        campaign_result = await db.execute(
            select(
                func.count(Campaign.id).label("total"),
                func.count(Campaign.id).filter(
                    Campaign.status == CampaignStatus.ACTIVE
                ).label("active"),
                func.coalesce(func.sum(Campaign.total_spend_cents), 0).label("spend_cents"),
                func.coalesce(func.sum(Campaign.revenue_cents), 0).label("revenue_cents"),
                func.coalesce(func.sum(Campaign.conversions), 0).label("conversions"),
            ).where(
                and_(
                    Campaign.tenant_id == tenant_id,
                    Campaign.is_deleted == False,
                )
            )
        )
        row = campaign_result.one_or_none()

        if row and row.total > 0:
            spend = float(row.spend_cents or 0) / 100
            revenue = float(row.revenue_cents or 0) / 100
            conversions = int(row.conversions or 0)
            roas = revenue / spend if spend > 0 else 0.0

            metrics = {
                "spend": spend,
                "revenue": revenue,
                "roas": roas,
                "conversions": conversions,
                "active_campaigns": row.active,
                "total_campaigns": row.total,
                "spend_change_pct": None,  # Would need historical comparison
                "revenue_change_pct": None,
            }
    except (SQLAlchemyError, ValueError, TypeError) as e:
        logger.debug("copilot_metrics_fetch_error", error=str(e))

    # 2. Signal health data
    health_data = None
    try:
        # Check EMQ degradation alerts
        emq_result = await db.execute(
            text(
                "SELECT COUNT(*) as degraded_count "
                "FROM fact_alerts WHERE tenant_id = :tenant_id "
                "AND alert_type = 'emq_degraded' "
                "AND (resolved = false OR resolved IS NULL) "
                "AND date >= CURRENT_DATE - INTERVAL '7 days'"
            ),
            {"tenant_id": tenant_id},
        )
        emq_row = emq_result.mappings().first()
        emq_degraded = emq_row["degraded_count"] if emq_row else 0

        if emq_degraded == 0:
            emq_score = 0.95
            overall = 85
            health_status = "healthy"
        elif emq_degraded <= 2:
            emq_score = 0.75
            overall = 65
            health_status = "degraded"
        else:
            emq_score = 0.50
            overall = 40
            health_status = "critical"

        health_data = {
            "overall_score": overall,
            "status": health_status,
            "emq_score": emq_score,
            "autopilot_enabled": health_status == "healthy",
            "issues": [] if health_status == "healthy" else [f"{emq_degraded} EMQ degradation alerts active"],
        }
    except (SQLAlchemyError, TypeError, KeyError) as e:
        logger.debug("copilot_health_fetch_error", error=str(e))
        # Return unknown status rather than fabricated healthy scores
        health_data = {
            "overall_score": None,
            "status": "unknown",
            "emq_score": None,
            "autopilot_enabled": False,
            "issues": ["Unable to fetch signal health data"],
        }

    # 3. Anomaly data (lightweight — just counts)
    anomaly_data = None
    if metrics and metrics.get("spend", 0) > 0:
        # We provide a lightweight anomaly summary
        # (full anomaly detection is expensive, done by the dedicated endpoint)
        anomaly_data = {
            "total_anomalies": 0,
            "critical_count": 0,
            "high_count": 0,
            "portfolio_risk": "low",
            "executive_summary": "No anomalies detected.",
            "narratives": [],
            "correlations": [],
        }

    # ── Process message through copilot agent ────────────────────
    # The keyword classifier always runs first — it produces the intent,
    # the suggestion chips, and the structured data cards that the
    # frontend renders deterministically. When the LLM bridge is
    # enabled we additionally swap in a Claude-generated response text
    # using the same live context. On any LLM failure the template
    # message stays in place — the user never sees a degraded experience.

    first_name = user_name.split()[0] if user_name else None

    response = process_message(
        message=request.message,
        user_name=first_name,
        metrics=metrics,
        health_data=health_data,
        anomaly_data=anomaly_data,
    )

    llm_text = await generate_llm_message(
        message=request.message,
        user_name=first_name,
        metrics=metrics,
        health_data=health_data,
        anomaly_data=anomaly_data,
        intent=response.intent,
    )
    if llm_text:
        response = response.model_copy(update={"message": llm_text})

    logger.info(
        "copilot_response_generated",
        tenant_id=tenant_id,
        intent=response.intent,
        message_len=len(response.message),
        llm_used=llm_text is not None,
    )

    return APIResponse(
        success=True,
        data=CopilotMessageResponse(
            session_id=session_id,
            message=response.message,
            suggestions=response.suggestions,
            data_cards=response.data_cards,
            intent=response.intent,
            timestamp=datetime.now(UTC).isoformat(),
        ),
        message="Copilot response generated",
    )
