# =============================================================================
# Stratum AI - EMQ Playbook Models
# =============================================================================
"""
Persistence for EMQ fix-playbook progress.

The playbook items themselves are generated deterministically from a tenant's
EMQ driver scores (see ``app.api.v1.endpoints.emq_v2.get_playbook``) and are
identified by a stable ``item_key`` (e.g. ``enhanced_conversions``). This model
stores only the user-driven *state* for an item — its workflow status and the
owner assigned to it — so progress survives across requests.

Rows are created lazily on first update; an item with no row is treated as
``pending`` with no owner.
"""

from typing import Optional

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, TimestampMixin


class EmqPlaybookItemState(Base, TimestampMixin):
    """Per-tenant workflow state for a generated EMQ playbook item."""

    __tablename__ = "emq_playbook_item_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Stable identifier for the generated fix (not an ephemeral UUID), so a
    # given recommendation maps to the same row across requests.
    item_key: Mapped[str] = mapped_column(String(100), nullable=False)
    # Workflow status: pending | in_progress | completed.
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="pending"
    )
    owner: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "item_key", name="uq_emq_playbook_item"),
        Index("ix_emq_playbook_state_tenant", "tenant_id"),
    )
