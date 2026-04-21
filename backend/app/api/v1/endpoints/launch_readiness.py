# =============================================================================
# Stratum AI - Launch Readiness Endpoints
# =============================================================================
"""
Superadmin-only endpoints for the Launch Readiness wizard.

Rules:
- Phase N+1 is locked until phase N is 100 percent complete.
- Checking an item is allowed only when its phase is the current phase.
- Unchecking is always allowed. Unchecking an item in a completed phase
  re-opens that phase (and naturally relocks later phases).
- Every state change appends a row to ``launch_readiness_events`` for audit.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.launch_readiness_phases import (
    LAUNCH_READINESS_PHASES,
    find_item,
    total_item_count,
)
from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models import (
    LaunchReadinessEvent,
    LaunchReadinessItemState,
    User,
    UserRole,
)
from app.schemas import APIResponse
from app.schemas.launch_readiness import (
    LaunchReadinessEventEntry,
    LaunchReadinessItem,
    LaunchReadinessItemUpdate,
    LaunchReadinessPhase,
    LaunchReadinessState,
)

logger = get_logger(__name__)
router = APIRouter()


# =============================================================================
# Dependencies
# =============================================================================
def require_superadmin(request: Request) -> int:
    """Verify user has superadmin role. Returns the acting user id."""
    user_role = getattr(request.state, "role", None)
    user_id = getattr(request.state, "user_id", None)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    if user_role != UserRole.SUPERADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required",
        )

    return user_id


# =============================================================================
# State assembly
# =============================================================================
async def _load_states_by_key(
    db: AsyncSession,
) -> Dict[str, LaunchReadinessItemState]:
    """Return a {item_key: state_row} map for every persisted item state."""
    result = await db.execute(select(LaunchReadinessItemState))
    rows = result.scalars().all()
    return {row.item_key: row for row in rows}


async def _build_state(db: AsyncSession) -> LaunchReadinessState:
    """Merge the static phase catalog with DB state into the response shape."""
    states = await _load_states_by_key(db)

    phases: List[LaunchReadinessPhase] = []
    current_phase_number: Optional[int] = None
    overall_completed = 0

    for phase_def in LAUNCH_READINESS_PHASES:
        phase_items: List[LaunchReadinessItem] = []
        completed = 0

        for item_def in phase_def["items"]:
            state = states.get(item_def["key"])
            is_checked = bool(state and state.is_checked)
            if is_checked:
                completed += 1

            checked_by_name: Optional[str] = None
            if state and state.checked_by is not None:
                checked_by_name = state.checked_by.full_name or state.checked_by.email

            phase_items.append(
                LaunchReadinessItem(
                    key=item_def["key"],
                    title=item_def["title"],
                    description=item_def.get("description"),
                    is_checked=is_checked,
                    checked_by_user_id=state.checked_by_user_id if state else None,
                    checked_by_user_name=checked_by_name,
                    checked_at=state.checked_at if state else None,
                    note=state.note if state else None,
                )
            )

        total = len(phase_def["items"])
        is_complete = completed == total and total > 0
        if not is_complete and current_phase_number is None:
            current_phase_number = phase_def["number"]

        phases.append(
            LaunchReadinessPhase(
                number=phase_def["number"],
                slug=phase_def["slug"],
                title=phase_def["title"],
                description=phase_def.get("description"),
                items=phase_items,
                completed_count=completed,
                total_count=total,
                is_complete=is_complete,
                is_active=False,  # filled in below
                is_locked=False,  # filled in below
            )
        )
        overall_completed += completed

    # If every phase is complete, there is no "current phase"; keep the
    # active flag off all phases and signal launch via is_launched.
    is_launched = current_phase_number is None
    effective_current = current_phase_number if current_phase_number is not None else (
        LAUNCH_READINESS_PHASES[-1]["number"] + 1
    )

    for phase in phases:
        phase.is_active = phase.number == current_phase_number
        phase.is_locked = phase.number > effective_current

    return LaunchReadinessState(
        phases=phases,
        current_phase_number=effective_current,
        overall_completed=overall_completed,
        overall_total=total_item_count(),
        is_launched=is_launched,
    )


async def _current_phase_number(db: AsyncSession) -> int:
    """Return the lowest phase number that is not yet 100% complete."""
    states = await _load_states_by_key(db)
    for phase_def in LAUNCH_READINESS_PHASES:
        checked = sum(
            1
            for item in phase_def["items"]
            if item["key"] in states and states[item["key"]].is_checked
        )
        if checked < len(phase_def["items"]):
            return phase_def["number"]
    return LAUNCH_READINESS_PHASES[-1]["number"] + 1


async def _is_phase_complete(db: AsyncSession, phase_number: int) -> bool:
    """Check whether a given phase is 100% complete."""
    phase_def = next(
        (p for p in LAUNCH_READINESS_PHASES if p["number"] == phase_number),
        None,
    )
    if phase_def is None:
        return False
    states = await _load_states_by_key(db)
    for item in phase_def["items"]:
        row = states.get(item["key"])
        if row is None or not row.is_checked:
            return False
    return True


# =============================================================================
# Endpoints
# =============================================================================
@router.get("", response_model=APIResponse[LaunchReadinessState])
async def get_launch_readiness(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Return the full Launch Readiness state (phases, items, progress)."""
    require_superadmin(request)
    state = await _build_state(db)
    return APIResponse(success=True, data=state)


@router.patch(
    "/items/{item_key}",
    response_model=APIResponse[LaunchReadinessState],
)
async def toggle_item(
    item_key: str,
    payload: LaunchReadinessItemUpdate,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Check or uncheck a single item. Enforces that checking only happens in
    the current phase; unchecking is always allowed.
    """
    acting_user_id = require_superadmin(request)

    located = find_item(item_key)
    if located is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown launch readiness item: {item_key}",
        )
    phase_def, _item_def = located

    current_phase = await _current_phase_number(db)

    if payload.checked and phase_def["number"] != current_phase:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot check items in phase {phase_def['number']}: "
                f"phase {current_phase} must be completed first."
            ),
        )

    result = await db.execute(
        select(LaunchReadinessItemState).where(
            LaunchReadinessItemState.item_key == item_key
        )
    )
    state_row = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    was_checked = bool(state_row and state_row.is_checked)

    if state_row is None:
        state_row = LaunchReadinessItemState(
            phase_number=phase_def["number"],
            item_key=item_key,
            is_checked=payload.checked,
            checked_by_user_id=acting_user_id if payload.checked else None,
            checked_at=now if payload.checked else None,
            note=payload.note,
        )
        db.add(state_row)
    else:
        state_row.is_checked = payload.checked
        state_row.note = payload.note
        if payload.checked:
            state_row.checked_by_user_id = acting_user_id
            state_row.checked_at = now
        else:
            state_row.checked_by_user_id = None
            state_row.checked_at = None

    # Audit trail. Record the user-driven action; phase-level transitions
    # are recorded below after we know the post-toggle state.
    if payload.checked != was_checked:
        db.add(
            LaunchReadinessEvent(
                phase_number=phase_def["number"],
                item_key=item_key,
                action="checked" if payload.checked else "unchecked",
                user_id=acting_user_id,
                note=payload.note,
            )
        )

    await db.flush()

    phase_now_complete = await _is_phase_complete(db, phase_def["number"])
    if payload.checked and phase_now_complete and not was_checked:
        db.add(
            LaunchReadinessEvent(
                phase_number=phase_def["number"],
                item_key=None,
                action="phase_completed",
                user_id=acting_user_id,
            )
        )
        logger.info(
            "launch_readiness_phase_completed",
            phase=phase_def["number"],
            user_id=acting_user_id,
        )
    elif not payload.checked and was_checked:
        db.add(
            LaunchReadinessEvent(
                phase_number=phase_def["number"],
                item_key=None,
                action="phase_reopened",
                user_id=acting_user_id,
            )
        )
        logger.info(
            "launch_readiness_phase_reopened",
            phase=phase_def["number"],
            user_id=acting_user_id,
            item=item_key,
        )

    await db.commit()

    state = await _build_state(db)
    return APIResponse(success=True, data=state)


@router.get(
    "/events",
    response_model=APIResponse[List[LaunchReadinessEventEntry]],
)
async def list_events(
    request: Request,
    phase_number: Optional[int] = Query(default=None, ge=1, le=99),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_async_session),
):
    """Return the audit trail, most recent first."""
    require_superadmin(request)

    stmt = select(LaunchReadinessEvent).order_by(desc(LaunchReadinessEvent.created_at))
    if phase_number is not None:
        stmt = stmt.where(LaunchReadinessEvent.phase_number == phase_number)
    stmt = stmt.limit(limit)

    result = await db.execute(stmt)
    rows = result.scalars().all()

    entries: List[LaunchReadinessEventEntry] = []
    for row in rows:
        user_name: Optional[str] = None
        if row.user is not None:
            user_name = row.user.full_name or row.user.email
        entries.append(
            LaunchReadinessEventEntry(
                id=row.id,
                phase_number=row.phase_number,
                item_key=row.item_key,
                action=row.action,
                user_id=row.user_id,
                user_name=user_name,
                note=row.note,
                created_at=row.created_at,
            )
        )

    return APIResponse(success=True, data=entries)
