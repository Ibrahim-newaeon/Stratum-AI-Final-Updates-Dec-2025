# =============================================================================
# Stratum AI - Client Entity Models
# =============================================================================
"""
Client (brand) entity for agency model.

Each tenant (agency) manages multiple clients (brands). Campaigns, analytics,
and portal access are scoped to clients.

Models:
- Client: Brand/customer entity owned by a tenant (agency)
- ClientAssignment: Junction table linking agency users to clients
- ClientRequest: Portal request workflow (v2 placeholder)
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TenantMixin, TimestampMixin

if TYPE_CHECKING:
    from app.base_models import Campaign, User


# =============================================================================
# Enums
# =============================================================================
class ClientRequestStatus(str, PyEnum):
    """Status for client portal requests."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    CANCELLED = "cancelled"


class ClientRequestType(str, PyEnum):
    """Types of actions a client can request via portal."""

    PAUSE_CAMPAIGN = "pause_campaign"
    RESUME_CAMPAIGN = "resume_campaign"
    ADJUST_BUDGET = "adjust_budget"
    CHANGE_TARGETING = "change_targeting"
    NEW_CAMPAIGN = "new_campaign"
    OTHER = "other"


# =============================================================================
# Client Model (Agency → Brand relationship)
# =============================================================================
class Client(TimestampMixin, SoftDeleteMixin, TenantMixin, Base):
    """
    Represents a brand/customer managed by an agency tenant.

    This is the AGENCY MODEL: each tenant (agency) manages multiple clients
    (brands). Campaigns, users, and analytics can be scoped to a client.
    """

    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Locale
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)

    # Budget (cents to avoid floating point issues)
    monthly_budget_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # KPI targets
    target_roas: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_cpa_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    target_ctr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Alert thresholds
    budget_alert_threshold: Mapped[float] = mapped_column(
        Float, default=0.9, nullable=False
    )
    roas_alert_threshold: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Contact info
    contact_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Metadata
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    assignments: Mapped[list["ClientAssignment"]] = relationship(
        "ClientAssignment", back_populates="client", cascade="all, delete-orphan"
    )
    campaigns: Mapped[list["Campaign"]] = relationship(
        "Campaign", back_populates="client", foreign_keys="[Campaign.client_id]"
    )
    portal_users: Mapped[list["User"]] = relationship(
        "User", back_populates="client", foreign_keys="[User.client_id]"
    )
    requests: Mapped[list["ClientRequest"]] = relationship(
        "ClientRequest", back_populates="client", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_client_tenant_slug"),
        Index("ix_clients_tenant_active", "tenant_id", "is_active"),
        Index("ix_clients_tenant_name", "tenant_id", "name"),
    )


# =============================================================================
# Client Assignment (Agency User ↔ Client junction)
# =============================================================================
class ClientAssignment(TimestampMixin, Base):
    """
    Junction table: which agency users (MANAGER/ANALYST roles)
    are assigned to which clients.

    SUPERADMIN and ADMIN see all clients implicitly.
    VIEWER users are linked via User.client_id instead.
    """

    __tablename__ = "client_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    assigned_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User", foreign_keys=[user_id], backref="client_assignments"
    )
    client: Mapped["Client"] = relationship(
        "Client", back_populates="assignments"
    )
    assigned_by_user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[assigned_by]
    )

    __table_args__ = (
        UniqueConstraint("user_id", "client_id", name="uq_user_client_assignment"),
        Index("ix_client_assignments_user", "user_id"),
        Index("ix_client_assignments_client", "client_id"),
    )


# =============================================================================
# Client Request (Portal workflow — v2 placeholder)
# =============================================================================
class ClientRequest(TimestampMixin, TenantMixin, Base):
    """
    Portal request workflow: client portal users can submit requests
    that agency users review and execute.

    Status flow: pending -> approved -> executed
                 pending -> rejected
                 pending -> cancelled
    """

    __tablename__ = "client_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    requested_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Request details
    request_type: Mapped[ClientRequestType] = mapped_column(
        Enum(ClientRequestType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Target entity (what the request is about)
    target_entity_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    target_entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    requested_changes: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Review
    status: Mapped[ClientRequestStatus] = mapped_column(
        Enum(ClientRequestStatus, values_callable=lambda x: [e.value for e in x]),
        default=ClientRequestStatus.PENDING,
        nullable=False,
    )
    reviewed_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    executed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    client: Mapped["Client"] = relationship("Client", back_populates="requests")
    requester: Mapped["User"] = relationship("User", foreign_keys=[requested_by])
    reviewer: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[reviewed_by]
    )

    __table_args__ = (
        Index("ix_client_requests_client_status", "client_id", "status"),
        Index("ix_client_requests_status", "status", "created_at"),
        Index("ix_client_requests_tenant", "tenant_id"),
    )
