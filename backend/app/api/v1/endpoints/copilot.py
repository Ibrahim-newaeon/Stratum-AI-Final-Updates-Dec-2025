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
from typing import Optional, Tuple
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
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
from app.services.agents.copilot_llm_stream import stream_llm_message

logger = get_logger(__name__)
router = APIRouter(prefix="/copilot", tags=["copilot"])


# =============================================================================
# Schemas
# =============================================================================


class CopilotMessageRequest(BaseModel):
    """Request to send a message to the copilot."""

    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = Field(
        None, description="Optional session ID for continuity"
    )


class CopilotCitation(BaseModel):
    """A doc reference returned by the RAG bridge."""

    source_path: str = Field(..., description="Repo-relative path of the cited doc")
    title: str = Field(
        ..., description="Human-readable title (heading path or filename)"
    )
    distance: float = Field(..., description="Cosine distance — lower is more relevant")


class CopilotMessageResponse(BaseModel):
    """Response from the copilot."""

    session_id: str
    message: str
    suggestions: list[str] = []
    data_cards: list[dict] = []
    intent: str = "unknown"
    citations: list[CopilotCitation] = []
    timestamp: str


# =============================================================================
# Context gathering (shared between /chat and /chat/stream)
# =============================================================================


async def _gather_context(
    *,
    db: AsyncSession,
    tenant_id: int,
) -> Tuple[Optional[dict], dict, Optional[dict]]:
    """
    Fetch the live tenant signals the copilot needs: campaign rollup,
    signal-health snapshot, lightweight anomaly summary. Each block
    fails open — partial context is better than no response.
    """
    metrics: Optional[dict] = None
    try:
        campaign_result = await db.execute(
            select(
                func.count(Campaign.id).label("total"),
                func.count(Campaign.id)
                .filter(Campaign.status == CampaignStatus.ACTIVE)
                .label("active"),
                func.coalesce(func.sum(Campaign.total_spend_cents), 0).label(
                    "spend_cents"
                ),
                func.coalesce(func.sum(Campaign.revenue_cents), 0).label(
                    "revenue_cents"
                ),
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
                "spend_change_pct": None,
                "revenue_change_pct": None,
            }
    except (SQLAlchemyError, ValueError, TypeError) as e:
        logger.debug("copilot_metrics_fetch_error", error=str(e))

    health_data: dict
    try:
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
            "issues": (
                []
                if health_status == "healthy"
                else [f"{emq_degraded} EMQ degradation alerts active"]
            ),
        }
    except (SQLAlchemyError, TypeError, KeyError) as e:
        logger.debug("copilot_health_fetch_error", error=str(e))
        health_data = {
            "overall_score": None,
            "status": "unknown",
            "emq_score": None,
            "autopilot_enabled": False,
            "issues": ["Unable to fetch signal health data"],
        }

    anomaly_data: Optional[dict] = None
    if metrics and metrics.get("spend", 0) > 0:
        anomaly_data = {
            "total_anomalies": 0,
            "critical_count": 0,
            "high_count": 0,
            "portfolio_risk": "low",
            "executive_summary": "No anomalies detected.",
            "narratives": [],
            "correlations": [],
        }

    return metrics, health_data, anomaly_data


def _resolve_user_name(user) -> Tuple[Optional[str], Optional[str]]:
    """Return (display_name, first_name) — the bridge wants the first name only."""
    user_name = getattr(user, "full_name", None) or getattr(user, "email", "User")
    if user_name and "@" in user_name:
        user_name = user_name.split("@")[0].title()
    first_name = user_name.split()[0] if user_name else None
    return user_name, first_name


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
    _, first_name = _resolve_user_name(user)

    session_id = request.session_id or str(uuid4())

    # ── Gather context data for the copilot ──────────────────────
    metrics, health_data, anomaly_data = await _gather_context(
        db=db, tenant_id=tenant_id
    )

    # ── Process message through copilot agent ────────────────────
    # The keyword classifier always runs first — it produces the intent,
    # the suggestion chips, and the structured data cards that the
    # frontend renders deterministically. When the LLM bridge is
    # enabled we additionally swap in a Claude-generated response text
    # using the same live context. On any LLM failure the template
    # message stays in place — the user never sees a degraded experience.

    response = process_message(
        message=request.message,
        user_name=first_name,
        metrics=metrics,
        health_data=health_data,
        anomaly_data=anomaly_data,
    )

    llm_result = await generate_llm_message(
        message=request.message,
        user_name=first_name,
        metrics=metrics,
        health_data=health_data,
        anomaly_data=anomaly_data,
        intent=response.intent,
        db=db,
    )
    if llm_result.text:
        response = response.model_copy(update={"message": llm_result.text})

    citations = [
        CopilotCitation(
            source_path=c.source_path,
            title=c.title,
            distance=c.distance,
        )
        for c in llm_result.citations
    ]

    logger.info(
        "copilot_response_generated",
        tenant_id=tenant_id,
        intent=response.intent,
        message_len=len(response.message),
        llm_used=llm_result.text is not None,
        citation_count=len(citations),
    )

    return APIResponse(
        success=True,
        data=CopilotMessageResponse(
            session_id=session_id,
            message=response.message,
            suggestions=response.suggestions,
            data_cards=response.data_cards,
            intent=response.intent,
            citations=citations,
            timestamp=datetime.now(UTC).isoformat(),
        ),
        message="Copilot response generated",
    )


# =============================================================================
# Streaming endpoint
# =============================================================================


@router.post("/chat/stream")
async def copilot_chat_stream(
    request: CopilotMessageRequest,
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Stream the AI Copilot response as Server-Sent Events.

    Wire format (per `app.services.agents.copilot_llm_stream`):

        event: token   data: <text fragment>     ← multiple, in order
        event: meta    data: {citations, intent, suggestions, data_cards,
                              fallback_message?}  ← exactly one
        event: error   data: <short reason>      ← optional, before meta
        data: [DONE]                              ← always last

    The frontend appends `token` events to a growing assistant bubble,
    swaps in `fallback_message` if it's present (LLM failed before any
    tokens), and renders citations + suggestions + data_cards from the
    `meta` payload once the stream completes.
    """
    tenant_id = getattr(user, "tenant_id", None) or 1
    _, first_name = _resolve_user_name(user)
    session_id = request.session_id or str(uuid4())

    metrics, health_data, anomaly_data = await _gather_context(
        db=db, tenant_id=tenant_id
    )
    base_response = process_message(
        message=request.message,
        user_name=first_name,
        metrics=metrics,
        health_data=health_data,
        anomaly_data=anomaly_data,
    )

    async def _event_stream():
        # Emit a session_id event up front so the frontend can pin
        # this stream to a conversation without waiting for meta.
        yield (f"event: session\ndata: {session_id}\n\n")
        async for chunk in stream_llm_message(
            message=request.message,
            user_name=first_name,
            metrics=metrics,
            health_data=health_data,
            anomaly_data=anomaly_data,
            intent=base_response.intent,
            suggestions=base_response.suggestions,
            data_cards=base_response.data_cards,
            fallback_message=base_response.message,
            db=db,
        ):
            yield chunk

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            # Disable buffering on Cloudflare / nginx so tokens render
            # in real time rather than getting batched at proxy edges.
            "X-Accel-Buffering": "no",
        },
    )
