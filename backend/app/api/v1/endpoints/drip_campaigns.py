# =============================================================================
# Stratum AI — Drip Campaigns / Email Sequences
# =============================================================================
"""
Automated email sequences triggered by user behavior, time delays, or events.
Visual flow builder backend supporting drag-and-drop node graphs.
"""

from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_async_session
from app.schemas.response import APIResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/drip-campaigns", tags=["Drip Campaigns"])


# =============================================================================
# Enums
# =============================================================================

class TriggerType(str, Enum):
    USER_SUBSCRIBED = "user_subscribed"
    CART_ABANDONED = "cart_abandoned"
    CAMPAIGN_ROAS_DROP = "campaign_roas_drop"
    DAYS_SINCE_LOGIN = "days_since_login"
    POST_PURCHASE = "post_purchase"
    CUSTOM_EVENT = "custom_event"
    MANUAL = "manual"


class NodeType(str, Enum):
    TRIGGER = "trigger"
    EMAIL = "email"
    WAIT = "wait"
    CONDITION = "condition"
    NOTIFICATION = "notification"
    END = "end"


class DripStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


# =============================================================================
# Schemas — Flow Nodes (for drag-and-drop builder)
# =============================================================================

class FlowNode(BaseModel):
    """A single node in the drip sequence flow graph."""
    id: str
    type: NodeType
    position: dict[str, float] = Field(default_factory=dict)  # {x, y} for canvas
    data: dict[str, Any] = Field(default_factory=dict)


class FlowEdge(BaseModel):
    """Connection between two nodes."""
    id: str
    source: str  # source node id
    target: str  # target node id
    label: Optional[str] = None  # e.g. "yes", "no", "opened"


# =============================================================================
# Schemas — Drip Sequence
# =============================================================================

class DripStep(BaseModel):
    """A step in a drip sequence (execution model)."""
    step_order: int
    node_type: NodeType
    config: dict[str, Any]  # email_id, delay_hours, condition, etc.
    next_step_yes: Optional[int] = None
    next_step_no: Optional[int] = None


class DripSequenceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    trigger_type: TriggerType
    trigger_config: dict[str, Any] = Field(default_factory=dict)
    nodes: list[FlowNode] = Field(default_factory=list)
    edges: list[FlowEdge] = Field(default_factory=list)
    status: DripStatus = DripStatus.DRAFT


class DripSequenceResponse(BaseModel):
    id: str
    name: str
    description: str
    trigger_type: str
    trigger_config: dict[str, Any]
    status: str
    nodes: list[FlowNode]
    edges: list[FlowEdge]
    entry_count: int
    active_recipient_count: int
    completion_rate: float
    revenue_attributed_cents: int
    created_at: str
    updated_at: str


class DripExecutionLog(BaseModel):
    id: str
    sequence_id: str
    recipient_email: str
    step_number: int
    node_type: str
    status: str  # queued, sent, opened, clicked, bounced, failed
    sent_at: Optional[str]
    opened_at: Optional[str]
    clicked_at: Optional[str]
    metadata: dict[str, Any]


class DripAnalytics(BaseModel):
    sequence_id: str
    total_entries: int
    emails_sent: int
    emails_opened: int
    emails_clicked: int
    open_rate: float
    click_rate: float
    conversion_rate: float
    revenue_cents: int
    step_performance: list[dict[str, Any]]


# =============================================================================
# In-Memory Store (replace with DB table in production)
# =============================================================================

_drip_store: dict[str, dict] = {}
_execution_logs: list[dict] = []


def _generate_id() -> str:
    import secrets
    return f"drip_{secrets.token_hex(8)}"


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("", response_model=APIResponse[list[DripSequenceResponse]])
async def list_drip_sequences(
    req: Request,
    db: AsyncSession = Depends(get_async_session),
    status_filter: Optional[str] = Query(None),
):
    """List all drip sequences for the tenant."""
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required")

    sequences = [
        _serialize_sequence(s) for s in _drip_store.values()
        if s.get("tenant_id") == tenant_id
        and (not status_filter or s.get("status") == status_filter)
    ]
    return APIResponse(success=True, data=sequences, message=f"Found {len(sequences)} sequences")


@router.post("", response_model=APIResponse[DripSequenceResponse])
async def create_drip_sequence(
    request: DripSequenceCreate,
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Create a new drip sequence from a drag-and-drop flow graph.

    The frontend sends nodes (trigger, email, wait, condition) and edges
    (connections with labels like 'yes'/'no'). We store the graph and
    compile it to an execution plan.
    """
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required")

    sequence_id = _generate_id()
    now = datetime.now(UTC).isoformat()

    sequence = {
        "id": sequence_id,
        "tenant_id": tenant_id,
        "name": request.name,
        "description": request.description or "",
        "trigger_type": request.trigger_type.value,
        "trigger_config": request.trigger_config,
        "status": request.status.value,
        "nodes": [n.model_dump() for n in request.nodes],
        "edges": [e.model_dump() for e in request.edges],
        "entry_count": 0,
        "active_recipient_count": 0,
        "completion_rate": 0.0,
        "revenue_attributed_cents": 0,
        "created_at": now,
        "updated_at": now,
    }

    _drip_store[sequence_id] = sequence

    logger.info("drip_sequence_created", tenant_id=tenant_id, sequence_id=sequence_id, name=request.name)

    return APIResponse(success=True, data=_serialize_sequence(sequence), message="Sequence created")


@router.get("/{sequence_id}", response_model=APIResponse[DripSequenceResponse])
async def get_drip_sequence(
    sequence_id: str,
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Get a single drip sequence with its full flow graph."""
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required")

    sequence = _drip_store.get(sequence_id)
    if not sequence or sequence.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sequence not found")

    return APIResponse(success=True, data=_serialize_sequence(sequence), message="Sequence retrieved")


@router.put("/{sequence_id}", response_model=APIResponse[DripSequenceResponse])
async def update_drip_sequence(
    sequence_id: str,
    request: DripSequenceCreate,
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Update a drip sequence — save changes from the flow builder."""
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required")

    sequence = _drip_store.get(sequence_id)
    if not sequence or sequence.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sequence not found")

    sequence["name"] = request.name
    sequence["description"] = request.description or ""
    sequence["trigger_type"] = request.trigger_type.value
    sequence["trigger_config"] = request.trigger_config
    sequence["nodes"] = [n.model_dump() for n in request.nodes]
    sequence["edges"] = [e.model_dump() for e in request.edges]
    sequence["updated_at"] = datetime.now(UTC).isoformat()

    logger.info("drip_sequence_updated", tenant_id=tenant_id, sequence_id=sequence_id)

    return APIResponse(success=True, data=_serialize_sequence(sequence), message="Sequence updated")


@router.post("/{sequence_id}/activate", response_model=APIResponse[dict])
async def activate_sequence(
    sequence_id: str,
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Activate a sequence — start watching for triggers."""
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required")

    sequence = _drip_store.get(sequence_id)
    if not sequence or sequence.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sequence not found")

    sequence["status"] = DripStatus.ACTIVE.value
    sequence["updated_at"] = datetime.now(UTC).isoformat()

    return APIResponse(success=True, data={"id": sequence_id, "status": "active"}, message="Sequence activated")


@router.post("/{sequence_id}/pause", response_model=APIResponse[dict])
async def pause_sequence(
    sequence_id: str,
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Pause a sequence — no new entries, existing continue."""
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required")

    sequence = _drip_store.get(sequence_id)
    if not sequence or sequence.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sequence not found")

    sequence["status"] = DripStatus.PAUSED.value
    sequence["updated_at"] = datetime.now(UTC).isoformat()

    return APIResponse(success=True, data={"id": sequence_id, "status": "paused"}, message="Sequence paused")


@router.delete("/{sequence_id}", response_model=APIResponse[dict])
async def delete_sequence(
    sequence_id: str,
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Archive a sequence (soft delete)."""
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required")

    sequence = _drip_store.get(sequence_id)
    if not sequence or sequence.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sequence not found")

    sequence["status"] = DripStatus.ARCHIVED.value
    sequence["updated_at"] = datetime.now(UTC).isoformat()

    return APIResponse(success=True, data={"id": sequence_id, "deleted": True}, message="Sequence archived")


@router.post("/{sequence_id}/trigger", response_model=APIResponse[dict])
async def manual_trigger(
    sequence_id: str,
    recipient_email: str,
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Manually trigger a sequence for a specific recipient (testing)."""
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required")

    sequence = _drip_store.get(sequence_id)
    if not sequence or sequence.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sequence not found")

    # Simulate execution
    log_entry = {
        "id": f"exec_{len(_execution_logs) + 1:04d}",
        "sequence_id": sequence_id,
        "recipient_email": recipient_email,
        "step_number": 0,
        "node_type": "trigger",
        "status": "sent",
        "sent_at": datetime.now(UTC).isoformat(),
        "opened_at": None,
        "clicked_at": None,
        "metadata": {"trigger_type": "manual"},
    }
    _execution_logs.append(log_entry)
    sequence["entry_count"] = sequence.get("entry_count", 0) + 1

    return APIResponse(
        success=True,
        data={"sequence_id": sequence_id, "recipient": recipient_email, "status": "triggered"},
        message=f"Sequence triggered for {recipient_email}",
    )


@router.get("/{sequence_id}/logs", response_model=APIResponse[list[DripExecutionLog]])
async def get_execution_logs(
    sequence_id: str,
    req: Request,
    db: AsyncSession = Depends(get_async_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Get execution logs for a sequence."""
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required")

    logs = [
        DripExecutionLog(**log)
        for log in _execution_logs
        if log["sequence_id"] == sequence_id
    ]
    logs.sort(key=lambda x: x.sent_at or "", reverse=True)

    start = (page - 1) * page_size
    paginated = logs[start:start + page_size]

    return APIResponse(success=True, data=paginated, message=f"Found {len(logs)} log entries")


@router.get("/{sequence_id}/analytics", response_model=APIResponse[DripAnalytics])
async def get_drip_analytics(
    sequence_id: str,
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Get aggregated analytics for a drip sequence."""
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required")

    sequence = _drip_store.get(sequence_id)
    if not sequence or sequence.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sequence not found")

    logs = [log for log in _execution_logs if log["sequence_id"] == sequence_id]

    total_sent = len([l for l in logs if l["status"] in ("sent", "opened", "clicked")])
    total_opened = len([l for l in logs if l["opened_at"]])
    total_clicked = len([l for l in logs if l["clicked_at"]])

    open_rate = (total_opened / total_sent * 100) if total_sent > 0 else 0
    click_rate = (total_clicked / total_sent * 100) if total_sent > 0 else 0

    # Step performance
    step_stats = {}
    for log in logs:
        sn = log["step_number"]
        if sn not in step_stats:
            step_stats[sn] = {"sent": 0, "opened": 0, "clicked": 0}
        step_stats[sn]["sent"] += 1
        if log["opened_at"]:
            step_stats[sn]["opened"] += 1
        if log["clicked_at"]:
            step_stats[sn]["clicked"] += 1

    step_performance = [
        {
            "step": step,
            "sent": stats["sent"],
            "opened": stats["opened"],
            "clicked": stats["clicked"],
            "open_rate": round(stats["opened"] / stats["sent"] * 100, 1) if stats["sent"] > 0 else 0,
        }
        for step, stats in sorted(step_stats.items())
    ]

    analytics = DripAnalytics(
        sequence_id=sequence_id,
        total_entries=sequence.get("entry_count", 0),
        emails_sent=total_sent,
        emails_opened=total_opened,
        emails_clicked=total_clicked,
        open_rate=round(open_rate, 2),
        click_rate=round(click_rate, 2),
        conversion_rate=round(click_rate * 0.3, 2),  # estimated
        revenue_cents=sequence.get("revenue_attributed_cents", 0),
        step_performance=step_performance,
    )

    return APIResponse(success=True, data=analytics, message="Analytics retrieved")


@router.get("/templates/prebuilt", response_model=APIResponse[list[dict]])
async def get_prebuilt_templates(
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Get pre-built drip sequence templates users can clone."""
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required")

    templates = [
        {
            "id": "tpl_welcome",
            "name": "Welcome Series",
            "description": "Onboard new subscribers with a 4-email welcome sequence",
            "trigger": "user_subscribed",
            "steps": 4,
            "estimated_days": 7,
            "preview": ["Welcome email", "Brand story", "Tutorial", "First offer"],
        },
        {
            "id": "tpl_abandon",
            "name": "Cart Abandonment",
            "description": "Recover lost sales with a 3-email recovery sequence",
            "trigger": "cart_abandoned",
            "steps": 3,
            "estimated_days": 3,
            "preview": ["Gentle reminder", "Social proof", "Discount offer"],
        },
        {
            "id": "tpl_reengagement",
            "name": "Re-engagement",
            "description": "Win back inactive users before they churn",
            "trigger": "days_since_login",
            "steps": 3,
            "estimated_days": 14,
            "preview": ["We miss you", "What's new", "Last chance + incentive"],
        },
        {
            "id": "tpl_postpurchase",
            "name": "Post-Purchase",
            "description": "Maximize customer LTV after first purchase",
            "trigger": "post_purchase",
            "steps": 4,
            "estimated_days": 21,
            "preview": ["Thank you", "Usage tips", "Review request", "Referral ask"],
        },
        {
            "id": "tpl_roasalert",
            "name": "ROAS Alert Sequence",
            "description": "Auto-alert and suggest actions when campaign ROAS drops",
            "trigger": "campaign_roas_drop",
            "steps": 3,
            "estimated_days": 2,
            "preview": ["Alert notification", "Diagnostic guide", "Escalation"],
        },
    ]

    return APIResponse(success=True, data=templates, message="Templates retrieved")


# =============================================================================
# Helpers
# =============================================================================

def _serialize_sequence(sequence: dict) -> DripSequenceResponse:
    return DripSequenceResponse(
        id=sequence["id"],
        name=sequence["name"],
        description=sequence.get("description", ""),
        trigger_type=sequence["trigger_type"],
        trigger_config=sequence.get("trigger_config", {}),
        status=sequence["status"],
        nodes=[FlowNode(**n) for n in sequence.get("nodes", [])],
        edges=[FlowEdge(**e) for e in sequence.get("edges", [])],
        entry_count=sequence.get("entry_count", 0),
        active_recipient_count=sequence.get("active_recipient_count", 0),
        completion_rate=sequence.get("completion_rate", 0.0),
        revenue_attributed_cents=sequence.get("revenue_attributed_cents", 0),
        created_at=sequence["created_at"],
        updated_at=sequence["updated_at"],
    )
