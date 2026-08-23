# =============================================================================
# Stratum AI — Drip Campaigns / Email Sequences
# =============================================================================
"""
Automated email sequences triggered by user behavior, time delays, or events.
Visual flow builder backend supporting drag-and-drop node graphs.

Sequences and their execution logs are persisted to PostgreSQL (see
``app.models.drip``) so they survive restarts and are shared across API
workers — replacing the former per-process in-memory store.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models.drip import (
    ENROLLMENT_CANCELLED,
    ENROLLMENT_IN_FLIGHT,
    DripEnrollment,
    DripExecutionRecord,
    DripSequence,
    DripSequenceVersion,
)
from app.schemas.response import APIResponse
from app.services.drip.enrollment import (
    CANCEL_SEQUENCE_ARCHIVED,
    CANCEL_UNSUBSCRIBED,
    EnrollmentBlocked,
    EnrollmentRequest,
    cancel_sequence_enrollments_async,
    enroll_async,
)
from app.services.drip.interpreter import index_graph, validate_graph
from app.services.drip.render import verify_unsubscribe_token

logger = get_logger(__name__)


async def require_drip_enabled() -> None:
    """
    Gate Drip Campaigns behind a feature flag.

    Drip has no execution engine — no drip Celery task exists, ``activate`` only
    flips a flag, and ``manual_trigger`` writes a "simulated" record. Shelved
    off for launch: every route returns 503 instead of shipping a builder whose
    sequences never actually send.
    """
    if not settings.feature_drip_campaigns:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Drip Campaigns are not enabled on this deployment.",
        )


router = APIRouter(
    prefix="/drip-campaigns",
    tags=["Drip Campaigns"],
    dependencies=[Depends(require_drip_enabled)],
)

#: Open-pixel, click and unsubscribe routes.
#:
#: Deliberately outside the feature gate above, and deliberately unauthenticated.
#: These URLs live inside emails that have already been delivered — an inbox is
#: forever, and turning the feature off later must not turn a recipient's
#: unsubscribe link into a 503. Refusing an opt-out is the one failure mode this
#: whole surface cannot have.
public_router = APIRouter(prefix="/drip-campaigns", tags=["Drip Campaigns"])


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
# Helpers
# =============================================================================


def _serialize_sequence(seq: DripSequence) -> DripSequenceResponse:
    """Map a persisted drip sequence to its API response shape."""
    return DripSequenceResponse(
        id=seq.id,
        name=seq.name,
        description=seq.description or "",
        trigger_type=seq.trigger_type,
        trigger_config=seq.trigger_config or {},
        status=seq.status,
        nodes=[FlowNode(**n) for n in (seq.nodes or [])],
        edges=[FlowEdge(**e) for e in (seq.edges or [])],
        entry_count=seq.entry_count,
        active_recipient_count=seq.active_recipient_count,
        completion_rate=seq.completion_rate,
        revenue_attributed_cents=seq.revenue_attributed_cents,
        created_at=seq.created_at.isoformat(),
        updated_at=seq.updated_at.isoformat(),
    )


def _serialize_log(log: DripExecutionRecord) -> DripExecutionLog:
    """Map a persisted execution record to its API response shape."""
    return DripExecutionLog(
        id=log.id,
        sequence_id=log.sequence_id,
        recipient_email=log.recipient_email,
        step_number=log.step_number,
        node_type=log.node_type,
        status=log.status,
        sent_at=log.sent_at.isoformat() if log.sent_at else None,
        opened_at=log.opened_at.isoformat() if log.opened_at else None,
        clicked_at=log.clicked_at.isoformat() if log.clicked_at else None,
        metadata=log.extra or {},
    )


def _require_tenant(req: Request) -> int:
    """Return the request tenant_id or raise 401 if absent."""
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required"
        )
    return tenant_id


async def _get_sequence(
    db: AsyncSession, tenant_id: int, sequence_id: str
) -> Optional[DripSequence]:
    """Fetch a tenant-scoped sequence by id (None if not found)."""
    result = await db.execute(
        select(DripSequence).where(
            DripSequence.id == sequence_id,
            DripSequence.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


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
    tenant_id = _require_tenant(req)

    stmt = select(DripSequence).where(DripSequence.tenant_id == tenant_id)
    if status_filter:
        stmt = stmt.where(DripSequence.status == status_filter)
    stmt = stmt.order_by(DripSequence.created_at.desc())

    rows = (await db.execute(stmt)).scalars().all()
    sequences = [_serialize_sequence(s) for s in rows]
    return APIResponse(
        success=True, data=sequences, message=f"Found {len(sequences)} sequences"
    )


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
    tenant_id = _require_tenant(req)
    user_id = getattr(req.state, "user_id", None)

    sequence = DripSequence(
        tenant_id=tenant_id,
        name=request.name,
        description=request.description or "",
        trigger_type=request.trigger_type.value,
        trigger_config=request.trigger_config,
        status=request.status.value,
        nodes=[n.model_dump() for n in request.nodes],
        edges=[e.model_dump() for e in request.edges],
        created_by_user_id=user_id,
    )
    db.add(sequence)
    await db.commit()
    await db.refresh(sequence)

    logger.info(
        "drip_sequence_created",
        tenant_id=tenant_id,
        sequence_id=sequence.id,
        name=sequence.name,
    )

    return APIResponse(
        success=True, data=_serialize_sequence(sequence), message="Sequence created"
    )


@router.get("/{sequence_id}", response_model=APIResponse[DripSequenceResponse])
async def get_drip_sequence(
    sequence_id: str,
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Get a single drip sequence with its full flow graph."""
    tenant_id = _require_tenant(req)

    sequence = await _get_sequence(db, tenant_id, sequence_id)
    if not sequence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sequence not found"
        )

    return APIResponse(
        success=True, data=_serialize_sequence(sequence), message="Sequence retrieved"
    )


@router.put("/{sequence_id}", response_model=APIResponse[DripSequenceResponse])
async def update_drip_sequence(
    sequence_id: str,
    request: DripSequenceCreate,
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Update a drip sequence — save changes from the flow builder."""
    tenant_id = _require_tenant(req)

    sequence = await _get_sequence(db, tenant_id, sequence_id)
    if not sequence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sequence not found"
        )

    was_active = sequence.status == DripStatus.ACTIVE.value

    sequence.name = request.name
    sequence.description = request.description or ""
    sequence.trigger_type = request.trigger_type.value
    sequence.trigger_config = request.trigger_config
    sequence.nodes = [n.model_dump() for n in request.nodes]
    sequence.edges = [e.model_dump() for e in request.edges]

    # An edit changes the draft, never the published version. Recipients in
    # flight keep walking the graph they entered on; the new one takes effect
    # for new entrants at the next activate. That is why `status` is not taken
    # from the request while a sequence is live — a PUT must not be able to
    # deactivate a running sequence as a side effect of saving the canvas.
    if not was_active:
        sequence.status = request.status.value

    await db.commit()
    await db.refresh(sequence)

    message = "Sequence updated"
    if was_active:
        message = (
            "Draft updated. Recipients already in the sequence continue on the "
            "published version; activate again to publish these changes."
        )

    return APIResponse(
        success=True, data=_serialize_sequence(sequence), message=message
    )


@router.post("/{sequence_id}/activate", response_model=APIResponse[dict])
async def activate_sequence(
    sequence_id: str,
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Activate a sequence — start watching for triggers."""
    tenant_id = _require_tenant(req)

    sequence = await _get_sequence(db, tenant_id, sequence_id)
    if not sequence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sequence not found"
        )

    # Validate before publishing. This used to flip `status` on any graph at
    # all — including an empty one — which produced a sequence that reported
    # itself active and could never send anything.
    errors = validate_graph(sequence.nodes or [], sequence.edges or [])
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Sequence cannot be activated.",
                "errors": errors,
            },
        )

    index = index_graph(sequence.nodes or [], sequence.edges or [])

    # Freeze the draft. Recipients already walking an earlier version keep
    # walking it; only new entrants get this one.
    next_version = (
        await db.execute(
            select(func.coalesce(func.max(DripSequenceVersion.version), 0)).where(
                DripSequenceVersion.sequence_id == sequence_id
            )
        )
    ).scalar_one()

    version = DripSequenceVersion(
        tenant_id=tenant_id,
        sequence_id=sequence_id,
        version=int(next_version) + 1,
        nodes=sequence.nodes or [],
        edges=sequence.edges or [],
        trigger_type=sequence.trigger_type,
        trigger_config=sequence.trigger_config or {},
        entry_node_id=index.entry_node_id,
        published_by_user_id=getattr(req.state, "user_id", None),
    )
    db.add(version)
    await db.flush()

    sequence.active_version_id = version.id
    sequence.status = DripStatus.ACTIVE.value
    await db.commit()

    logger.info(
        "drip_sequence_activated",
        tenant_id=tenant_id,
        sequence_id=sequence_id,
        version=version.version,
    )

    return APIResponse(
        success=True,
        data={
            "id": sequence_id,
            "status": "active",
            "version": version.version,
            "version_id": version.id,
        },
        message=f"Sequence activated as version {version.version}",
    )


@router.post("/{sequence_id}/pause", response_model=APIResponse[dict])
async def pause_sequence(
    sequence_id: str,
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Pause a sequence — no new entries, existing continue."""
    tenant_id = _require_tenant(req)

    sequence = await _get_sequence(db, tenant_id, sequence_id)
    if not sequence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sequence not found"
        )

    sequence.status = DripStatus.PAUSED.value
    await db.commit()

    return APIResponse(
        success=True,
        data={"id": sequence_id, "status": "paused"},
        message="Sequence paused",
    )


@router.delete("/{sequence_id}", response_model=APIResponse[dict])
async def delete_sequence(
    sequence_id: str,
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Archive a sequence (soft delete)."""
    tenant_id = _require_tenant(req)

    sequence = await _get_sequence(db, tenant_id, sequence_id)
    if not sequence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sequence not found"
        )

    sequence.status = DripStatus.ARCHIVED.value

    # Archiving must stop the mail. Without this, every recipient already in
    # flight keeps receiving the sequence from a worker that has no reason to
    # look at the parent's status until their next step comes due.
    cancelled = await cancel_sequence_enrollments_async(
        db, tenant_id, sequence_id, CANCEL_SEQUENCE_ARCHIVED
    )
    await db.commit()

    return APIResponse(
        success=True,
        data={
            "id": sequence_id,
            "deleted": True,
            "cancelled_enrollments": cancelled,
        },
        message=(
            f"Sequence archived; {cancelled} in-flight recipients cancelled."
            if cancelled
            else "Sequence archived"
        ),
    )


@router.post("/{sequence_id}/trigger", response_model=APIResponse[dict])
async def manual_trigger(
    sequence_id: str,
    recipient_email: str,
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Enroll one recipient into a sequence by hand.

    This used to write a ``DripExecutionRecord`` marked *simulated* and return
    success, which read as a working trigger and sent nothing. It now creates a
    real enrollment; the sweep picks it up on the next tick.
    """
    tenant_id = _require_tenant(req)

    sequence = await _get_sequence(db, tenant_id, sequence_id)
    if not sequence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sequence not found"
        )

    try:
        enrollment = await enroll_async(
            db,
            EnrollmentRequest(
                tenant_id=tenant_id,
                sequence_id=sequence_id,
                recipient_email=recipient_email,
                entry_trigger=TriggerType.MANUAL.value,
                entry_context={
                    "source": "manual_trigger",
                    "user_id": getattr(req.state, "user_id", None),
                },
            ),
        )
    except EnrollmentBlocked as blocked:
        # 409, not 400: the request is well-formed and the caller may well be
        # allowed to make it — the recipient's own state is what refuses.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"reason": blocked.reason, "message": blocked.detail},
        ) from blocked

    if enrollment is None:
        return APIResponse(
            success=True,
            data={
                "sequence_id": sequence_id,
                "status": "already_enrolled",
                "enrollment_id": None,
            },
            message="Recipient is already moving through this sequence.",
        )

    await db.commit()

    logger.info(
        "drip_manual_enrollment",
        tenant_id=tenant_id,
        sequence_id=sequence_id,
        enrollment_id=enrollment.id,
    )

    return APIResponse(
        success=True,
        data={
            "sequence_id": sequence_id,
            "enrollment_id": enrollment.id,
            "status": "enrolled",
        },
        message="Recipient enrolled; the first step runs on the next sweep.",
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
    tenant_id = _require_tenant(req)

    result = await db.execute(
        select(DripExecutionRecord)
        .where(
            DripExecutionRecord.sequence_id == sequence_id,
            DripExecutionRecord.tenant_id == tenant_id,
        )
        .order_by(DripExecutionRecord.sent_at.desc().nullslast())
    )
    rows = result.scalars().all()

    start = (page - 1) * page_size
    paginated = [_serialize_log(log) for log in rows[start : start + page_size]]

    return APIResponse(
        success=True, data=paginated, message=f"Found {len(rows)} log entries"
    )


@router.get("/{sequence_id}/analytics", response_model=APIResponse[DripAnalytics])
async def get_drip_analytics(
    sequence_id: str,
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Get aggregated analytics for a drip sequence."""
    tenant_id = _require_tenant(req)

    sequence = await _get_sequence(db, tenant_id, sequence_id)
    if not sequence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sequence not found"
        )

    result = await db.execute(
        select(DripExecutionRecord).where(
            DripExecutionRecord.sequence_id == sequence_id,
            DripExecutionRecord.tenant_id == tenant_id,
        )
    )
    logs = result.scalars().all()

    total_sent = len(
        [log for log in logs if log.status in ("sent", "opened", "clicked")]
    )
    total_opened = len([log for log in logs if log.opened_at])
    total_clicked = len([log for log in logs if log.clicked_at])

    open_rate = (total_opened / total_sent * 100) if total_sent > 0 else 0
    click_rate = (total_clicked / total_sent * 100) if total_sent > 0 else 0

    # Step performance
    step_stats: dict[int, dict[str, int]] = {}
    for log in logs:
        sn = log.step_number
        if sn not in step_stats:
            step_stats[sn] = {"sent": 0, "opened": 0, "clicked": 0}
        step_stats[sn]["sent"] += 1
        if log.opened_at:
            step_stats[sn]["opened"] += 1
        if log.clicked_at:
            step_stats[sn]["clicked"] += 1

    step_performance = [
        {
            "step": step,
            "sent": stats["sent"],
            "opened": stats["opened"],
            "clicked": stats["clicked"],
            "open_rate": (
                round(stats["opened"] / stats["sent"] * 100, 1)
                if stats["sent"] > 0
                else 0
            ),
        }
        for step, stats in sorted(step_stats.items())
    ]

    analytics = DripAnalytics(
        sequence_id=sequence_id,
        total_entries=sequence.entry_count,
        emails_sent=total_sent,
        emails_opened=total_opened,
        emails_clicked=total_clicked,
        open_rate=round(open_rate, 2),
        click_rate=round(click_rate, 2),
        conversion_rate=round(click_rate * 0.3, 2),  # estimated
        revenue_cents=sequence.revenue_attributed_cents,
        step_performance=step_performance,
    )

    return APIResponse(success=True, data=analytics, message="Analytics retrieved")


@router.get("/templates/prebuilt", response_model=APIResponse[list[dict]])
async def get_prebuilt_templates(
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Get pre-built drip sequence templates users can clone."""
    _require_tenant(req)

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
# Public tracking and unsubscribe
# =============================================================================
#
# Registered on ``public_router``, which carries neither the feature gate nor
# authentication. These URLs are baked into emails that have already been
# delivered; a recipient clicking unsubscribe six months from now must be
# honoured whatever the flag says today.

#: 1x1 transparent GIF, returned by the open pixel whatever happens. An open
#: pixel must never render as a broken image or leak whether the id was real.
_PIXEL = bytes.fromhex(
    "47494638396101000100800000000000ffffff21f90401000000002c00000000"
    "010001000002024401003b"
)


async def _record_engagement(
    db: AsyncSession, execution_id: str, field: str
) -> Optional[DripExecutionRecord]:
    """Stamp ``opened_at`` or ``clicked_at`` once, and return the record."""
    record = (
        await db.execute(
            select(DripExecutionRecord).where(DripExecutionRecord.id == execution_id)
        )
    ).scalar_one_or_none()

    if record is None:
        return None

    # First touch wins: re-opens are common (many clients prefetch), and
    # overwriting would make "opened_at" mean "last opened", which the
    # email_opened condition would then read differently on every step.
    if getattr(record, field) is None:
        setattr(record, field, datetime.now(UTC))
        if field == "clicked_at" and record.opened_at is None:
            # A click implies an open the pixel may never have recorded.
            record.opened_at = datetime.now(UTC)
        if record.status == "sent":
            record.status = "opened" if field == "opened_at" else "clicked"
        await db.commit()

    return record


@public_router.get("/track/open/{execution_id}", include_in_schema=False)
async def track_open(
    execution_id: str,
    db: AsyncSession = Depends(get_async_session),
) -> Response:
    """Open-tracking pixel."""
    await _record_engagement(db, execution_id, "opened_at")
    return Response(
        content=_PIXEL,
        media_type="image/gif",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, private"},
    )


@public_router.get("/track/click/{execution_id}", include_in_schema=False)
async def track_click(
    execution_id: str,
    url: str = Query(..., description="Destination the recipient clicked"),
    db: AsyncSession = Depends(get_async_session),
) -> Response:
    """Click tracking, then redirect to the original destination."""
    # Only ever redirect to http(s). Without this the tracker would happily
    # bounce a recipient to javascript: or data:, turning every drip email into
    # an open redirect signed by our own domain.
    if not url.lower().startswith(("http://", "https://")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported link target"
        )

    await _record_engagement(db, execution_id, "clicked_at")
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


@public_router.api_route(
    "/unsubscribe", methods=["GET", "POST"], include_in_schema=False
)
async def drip_unsubscribe(
    token: str = Query(..., description="Signed unsubscribe token"),
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[dict]:
    """Honour an unsubscribe from a drip email.

    POST as well as GET so RFC 8058 one-click unsubscribe works from the
    ``List-Unsubscribe-Post`` header the send path sets.

    The token is HMAC-signed and carries the recipient *hash*, so it cannot be
    forged, cannot be walked to unsubscribe a stranger, and never puts an email
    address in a URL.
    """
    verified = verify_unsubscribe_token(token)
    if verified is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This unsubscribe link is not valid.",
        )
    tenant_id, recipient_hash = verified

    now = datetime.now(UTC)
    result = await db.execute(
        select(DripEnrollment).where(
            DripEnrollment.tenant_id == tenant_id,
            DripEnrollment.recipient_hash == recipient_hash,
            DripEnrollment.status.in_(ENROLLMENT_IN_FLIGHT),
        )
    )
    enrollments = result.scalars().all()

    for enrollment in enrollments:
        enrollment.status = ENROLLMENT_CANCELLED
        enrollment.cancel_reason = CANCEL_UNSUBSCRIBED
        enrollment.cancelled_at = now
        enrollment.next_due_at = None

    # Record the refusal against the CDP profile too, when there is one, so the
    # opt-out is visible to the rest of the product and not only to drip.
    profile_id = next(
        (e.profile_id for e in enrollments if e.profile_id is not None), None
    )
    if profile_id is not None:
        from app.models.cdp import CDPConsent

        consent = (
            await db.execute(
                select(CDPConsent).where(
                    CDPConsent.tenant_id == tenant_id,
                    CDPConsent.profile_id == profile_id,
                    CDPConsent.consent_type == "email",
                )
            )
        ).scalar_one_or_none()
        if consent is None:
            db.add(
                CDPConsent(
                    tenant_id=tenant_id,
                    profile_id=profile_id,
                    consent_type="email",
                    granted=False,
                    revoked_at=now,
                    source="drip_unsubscribe",
                )
            )
        else:
            consent.granted = False
            consent.revoked_at = now

    await db.commit()

    logger.info(
        "drip_unsubscribed",
        tenant_id=tenant_id,
        cancelled_enrollments=len(enrollments),
    )

    # Always the same answer, whether or not anything was live. Reporting "you
    # were not subscribed" would turn this into a membership oracle for anyone
    # holding a token.
    return APIResponse(
        success=True,
        data={"unsubscribed": True, "cancelled_enrollments": len(enrollments)},
        message="You have been unsubscribed and will receive no further emails.",
    )
