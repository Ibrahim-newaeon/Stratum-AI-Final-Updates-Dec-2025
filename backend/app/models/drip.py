# =============================================================================
# Stratum AI - Drip Campaign Models
# =============================================================================
"""SQLAlchemy models for drip (email sequence) campaigns.

Persists drip sequences and their execution logs so that data survives
process restarts and is shared across API workers — replacing the former
per-process in-memory store, which lost data on restart and was invisible
across workers.

Sequences keep their flow graph (nodes + edges + trigger config) as JSONB.
Identifiers retain the legacy ``drip_<hex>`` / ``exec_<hex>`` string format
so the API contract and any persisted frontend references are unchanged.
"""

import secrets
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base_class import Base


def generate_sequence_id() -> str:
    """Generate a drip-sequence identifier (legacy ``drip_<hex>`` format)."""
    return f"drip_{secrets.token_hex(8)}"


def generate_execution_id() -> str:
    """Generate a drip-execution identifier (legacy ``exec_<hex>`` format)."""
    return f"exec_{secrets.token_hex(8)}"


class DripSequence(Base):
    """A drip (email) sequence defined by a drag-and-drop flow graph."""

    __tablename__ = "drip_sequences"

    id = Column(String(64), primary_key=True, default=generate_sequence_id)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False, default="")
    trigger_type = Column(String(50), nullable=False)
    trigger_config = Column(JSONB, nullable=False, default=dict)
    status = Column(String(20), nullable=False, default="draft")

    # Flow graph
    nodes = Column(JSONB, nullable=False, default=list)
    edges = Column(JSONB, nullable=False, default=list)

    # Aggregate counters
    entry_count = Column(Integer, nullable=False, default=0)
    active_recipient_count = Column(Integer, nullable=False, default=0)
    completion_rate = Column(Float, nullable=False, default=0.0)
    revenue_attributed_cents = Column(BigInteger, nullable=False, default=0)

    created_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    __table_args__ = (Index("ix_drip_sequence_tenant_status", "tenant_id", "status"),)


class DripExecutionRecord(Base):
    """A single send/open/click event for a drip sequence recipient."""

    __tablename__ = "drip_execution_logs"

    id = Column(String(64), primary_key=True, default=generate_execution_id)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence_id = Column(
        String(64),
        ForeignKey("drip_sequences.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    recipient_email = Column(String(320), nullable=False)
    step_number = Column(Integer, nullable=False, default=0)
    node_type = Column(String(30), nullable=False)
    status = Column(String(20), nullable=False)

    sent_at = Column(DateTime(timezone=True), nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=True)
    clicked_at = Column(DateTime(timezone=True), nullable=True)
    extra = Column(JSONB, nullable=False, default=dict)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (Index("ix_drip_exec_sequence", "sequence_id", "sent_at"),)
