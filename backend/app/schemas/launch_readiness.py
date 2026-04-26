# =============================================================================
# Stratum AI - Launch Readiness Schemas
# =============================================================================
"""
Pydantic schemas for the Launch Readiness wizard API.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import Field

from app.base_schemas import BaseSchema


class LaunchReadinessItem(BaseSchema):
    """One checklist item inside a phase."""

    key: str
    title: str
    description: Optional[str] = None
    is_checked: bool = False
    checked_by_user_id: Optional[int] = None
    checked_by_user_name: Optional[str] = None
    checked_at: Optional[datetime] = None
    note: Optional[str] = None


class LaunchReadinessPhase(BaseSchema):
    """A phase containing its items and roll-up state."""

    number: int
    slug: str
    title: str
    description: Optional[str] = None
    items: List[LaunchReadinessItem]
    completed_count: int
    total_count: int
    is_complete: bool
    is_active: bool
    is_locked: bool


class LaunchReadinessState(BaseSchema):
    """Full launch readiness state served to the UI."""

    phases: List[LaunchReadinessPhase]
    current_phase_number: int
    overall_completed: int
    overall_total: int
    is_launched: bool


class LaunchReadinessItemUpdate(BaseSchema):
    """Payload for toggling an item's checked state."""

    checked: bool
    note: Optional[str] = Field(default=None, max_length=2000)


class LaunchReadinessEventEntry(BaseSchema):
    """Audit trail entry."""

    id: int
    phase_number: int
    item_key: Optional[str] = None
    action: str
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime
