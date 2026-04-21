# =============================================================================
# Stratum AI - Launch Readiness Models
# =============================================================================
"""
Persistence for the Launch Readiness go-live wizard (superadmin-only).

Phase / item metadata lives in ``app.core.launch_readiness_phases`` as a
static catalog. This module only stores user-driven state:

- ``LaunchReadinessItemState`` — one row per catalog item, tracks whether
  the item is checked, who checked it, and when.
- ``LaunchReadinessEvent`` — append-only audit trail of check / uncheck /
  phase-completed / phase-reopened events.

No tenant_id: this is platform-level, scoped to the Stratum team.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin


class LaunchReadinessItemState(Base, TimestampMixin):
    """
    Per-item check state for the Launch Readiness wizard.

    Rows are created lazily on first check. An item with no row is treated
    as unchecked. The uniqueness constraint guarantees a single row per
    (phase, item).
    """

    __tablename__ = "launch_readiness_item_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phase_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    item_key: Mapped[str] = mapped_column(String(100), nullable=False)

    is_checked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    checked_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    checked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    checked_by: Mapped[Optional["User"]] = relationship(  # type: ignore[name-defined] # noqa: F821
        "User", foreign_keys=[checked_by_user_id], lazy="joined"
    )

    __table_args__ = (
        UniqueConstraint("phase_number", "item_key", name="uq_launch_readiness_item"),
        Index("ix_launch_readiness_state_phase", "phase_number"),
    )


class LaunchReadinessEvent(Base):
    """
    Append-only audit trail for Launch Readiness actions.

    Action is one of: ``checked``, ``unchecked``, ``phase_completed``,
    ``phase_reopened``. Phase-level events have a null ``item_key``.
    """

    __tablename__ = "launch_readiness_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phase_number: Mapped[int] = mapped_column(Integer, nullable=False)
    item_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped[Optional["User"]] = relationship(  # type: ignore[name-defined] # noqa: F821
        "User", foreign_keys=[user_id], lazy="joined"
    )

    __table_args__ = (
        Index(
            "ix_launch_readiness_event_phase_created",
            "phase_number",
            "created_at",
        ),
        Index("ix_launch_readiness_event_created", "created_at"),
    )
