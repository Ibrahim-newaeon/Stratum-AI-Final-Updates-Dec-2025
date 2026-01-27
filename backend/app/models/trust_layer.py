# =============================================================================
# Stratum AI - Trust Layer Database Models
# =============================================================================
"""
Database models for the Trust Layer:
- FactSignalHealthDaily: Daily signal health metrics
- FactAttributionVarianceDaily: Daily attribution variance metrics
"""

import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base_class import Base

# =============================================================================
# Enums
# =============================================================================


class SignalHealthStatus(str, enum.Enum):
    """Signal health status levels."""

    OK = "ok"
    RISK = "risk"
    DEGRADED = "degraded"
    CRITICAL = "critical"


class AttributionVarianceStatus(str, enum.Enum):
    """Attribution variance status levels."""

    HEALTHY = "healthy"
    MINOR_VARIANCE = "minor_variance"
    MODERATE_VARIANCE = "moderate_variance"
    HIGH_VARIANCE = "high_variance"


# =============================================================================
# Models
# =============================================================================


class FactSignalHealthDaily(Base):
    """
    Daily signal health metrics per tenant/platform.
    Tracks EMQ scores, event loss, freshness, and API health.
    """

    __tablename__ = "fact_signal_health_daily"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    platform = Column(String(50), nullable=False)  # meta, google, tiktok, snapchat
    account_id = Column(String(255), nullable=True)  # Optional, for account-level tracking

    # Signal health metrics
    emq_score = Column(Float, nullable=True)  # Event Match Quality (0-100)
    event_loss_pct = Column(Float, nullable=True)  # Percentage of lost events (0-100)
    freshness_minutes = Column(Integer, nullable=True)  # Data freshness in minutes
    api_error_rate = Column(Float, nullable=True)  # API error rate percentage (0-100)

    # Computed status
    status = Column(
        SQLEnum(
            SignalHealthStatus,
            name="signal_health_status",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=SignalHealthStatus.OK,
    )

    # Additional context
    notes = Column(Text, nullable=True)
    issues = Column(Text, nullable=True)  # JSON array of issue strings
    actions = Column(Text, nullable=True)  # JSON array of recommended actions

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships - use foreign_keys to resolve ambiguity
    tenant = relationship(
        "Tenant", foreign_keys=[tenant_id], back_populates="signal_health_records"
    )

    __table_args__ = (
        Index("ix_fact_signal_health_daily_tenant_date", "tenant_id", "date"),
        Index("ix_fact_signal_health_daily_tenant_platform", "tenant_id", "platform"),
        Index("ix_fact_signal_health_daily_status", "tenant_id", "status"),
    )


class FactAttributionVarianceDaily(Base):
    """
    Daily attribution variance metrics (Platform vs GA4).
    Tracks divergence between platform-reported and GA4 data.
    """

    __tablename__ = "fact_attribution_variance_daily"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    platform = Column(String(50), nullable=False)

    # Revenue comparison
    ga4_revenue = Column(Float, nullable=False, default=0.0)
    platform_revenue = Column(Float, nullable=False, default=0.0)
    revenue_delta_abs = Column(Float, nullable=False, default=0.0)
    revenue_delta_pct = Column(Float, nullable=False, default=0.0)

    # Conversion comparison
    ga4_conversions = Column(Integer, nullable=False, default=0)
    platform_conversions = Column(Integer, nullable=False, default=0)
    conversion_delta_abs = Column(Integer, nullable=False, default=0)
    conversion_delta_pct = Column(Float, nullable=False, default=0.0)

    # Confidence and status
    confidence = Column(Float, nullable=False, default=0.0)  # 0-1
    status = Column(
        SQLEnum(
            AttributionVarianceStatus,
            name="attribution_variance_status",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=AttributionVarianceStatus.HEALTHY,
    )

    # Additional context
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships - use foreign_keys to resolve ambiguity
    tenant = relationship(
        "Tenant", foreign_keys=[tenant_id], back_populates="attribution_variance_records"
    )

    __table_args__ = (
        Index("ix_fact_attribution_variance_daily_tenant_date", "tenant_id", "date"),
        Index("ix_fact_attribution_variance_daily_tenant_platform", "tenant_id", "platform"),
    )


class SignalHealthHistory(Base):
    """
    Aggregated signal health history for trend analysis.
    Stores daily rollups of signal health metrics.
    """

    __tablename__ = "signal_health_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)

    # Aggregated scores
    overall_score = Column(Float, nullable=False)  # 0-100
    emq_score_avg = Column(Float, nullable=True)
    event_loss_pct_avg = Column(Float, nullable=True)
    freshness_minutes_avg = Column(Integer, nullable=True)
    api_error_rate_avg = Column(Float, nullable=True)

    # Status counts
    platforms_ok = Column(Integer, default=0)
    platforms_risk = Column(Integer, default=0)
    platforms_degraded = Column(Integer, default=0)
    platforms_critical = Column(Integer, default=0)

    # Computed overall status
    status = Column(
        SQLEnum(
            SignalHealthStatus,
            name="signal_health_status",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=SignalHealthStatus.OK,
    )

    # Automation state
    automation_blocked = Column(
        Integer, default=0
    )  # Boolean stored as int for SQLite compatibility

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_signal_health_history_tenant_date", "tenant_id", "date", unique=True),
    )


class TrustGateAuditLog(Base):
    """
    Audit log for trust gate decisions.
    Tracks every automation decision made by the trust gate.
    """

    __tablename__ = "trust_gate_audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Decision context
    decision_type = Column(String(50), nullable=False)  # execute, hold, block
    action_type = Column(String(100), nullable=False)  # budget_increase, pause, etc.
    entity_type = Column(String(50), nullable=False)  # campaign, adset, creative
    entity_id = Column(String(255), nullable=False)
    entity_name = Column(String(255), nullable=True)
    platform = Column(String(50), nullable=True)

    # Signal health at decision time
    signal_health_score = Column(Float, nullable=True)
    signal_health_status = Column(String(20), nullable=True)

    # Trust gate evaluation
    gate_passed = Column(Integer, default=0)  # Boolean as int
    gate_reason = Column(Text, nullable=True)  # JSON with reasons

    # Thresholds used
    healthy_threshold = Column(Float, nullable=True)
    degraded_threshold = Column(Float, nullable=True)

    # Dry run indicator
    is_dry_run = Column(Integer, default=0)  # Boolean as int

    # Action details
    action_payload = Column(Text, nullable=True)  # JSON
    action_result = Column(Text, nullable=True)  # JSON

    # User context
    triggered_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    triggered_by_system = Column(Integer, default=0)  # Boolean as int

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    triggered_by = relationship("User", foreign_keys=[triggered_by_user_id])

    __table_args__ = (
        Index("ix_trust_gate_audit_tenant_date", "tenant_id", "created_at"),
        Index("ix_trust_gate_audit_decision", "tenant_id", "decision_type"),
        Index("ix_trust_gate_audit_entity", "tenant_id", "entity_type", "entity_id"),
    )


class FactActionsQueue(Base):
    """
    Queue for autopilot actions requiring approval or execution.
    Tracks action lifecycle from creation to application.
    """

    __tablename__ = "fact_actions_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)

    # Action details
    action_type = Column(
        String(100), nullable=False
    )  # budget_increase, budget_decrease, pause, etc.
    entity_type = Column(String(50), nullable=False)  # campaign, adset, creative
    entity_id = Column(String(255), nullable=False)
    entity_name = Column(String(255), nullable=True)
    platform = Column(String(50), nullable=False)

    # Action payload
    action_json = Column(Text, nullable=False)  # Full action details as JSON

    # Before/after values for audit
    before_value = Column(Text, nullable=True)  # JSON
    after_value = Column(Text, nullable=True)  # JSON

    # Workflow status
    status = Column(
        String(50), nullable=False, default="queued"
    )  # queued, approved, applied, failed, dismissed

    # Actors
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    applied_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    applied_at = Column(DateTime(timezone=True), nullable=True)

    # Result
    error = Column(Text, nullable=True)
    platform_response = Column(Text, nullable=True)  # JSON

    # Relationships - use foreign_keys to resolve ambiguity
    tenant = relationship("Tenant", foreign_keys=[tenant_id], back_populates="actions_queue")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    approved_by = relationship("User", foreign_keys=[approved_by_user_id])
    applied_by = relationship("User", foreign_keys=[applied_by_user_id])

    __table_args__ = (
        Index("ix_fact_actions_queue_tenant_date", "tenant_id", "date"),
        Index("ix_fact_actions_queue_status", "tenant_id", "status"),
    )
