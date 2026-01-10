# =============================================================================
# Stratum AI - Trust Layer Database Models
# =============================================================================
"""
Database models for the Trust Layer:
- FactSignalHealthDaily: Daily signal health metrics
- FactAttributionVarianceDaily: Daily attribution variance metrics
"""

from datetime import datetime, date
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Column, String, Integer, Date, DateTime, Float, Text, ForeignKey,
    Index, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

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
    status = Column(SQLEnum(SignalHealthStatus), nullable=False, default=SignalHealthStatus.OK)

    # Additional context
    notes = Column(Text, nullable=True)
    issues = Column(Text, nullable=True)  # JSON array of issue strings
    actions = Column(Text, nullable=True)  # JSON array of recommended actions

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships - use foreign_keys to resolve ambiguity
    tenant = relationship("Tenant", foreign_keys=[tenant_id], back_populates="signal_health_records")

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
    status = Column(SQLEnum(AttributionVarianceStatus), nullable=False, default=AttributionVarianceStatus.HEALTHY)

    # Additional context
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships - use foreign_keys to resolve ambiguity
    tenant = relationship("Tenant", foreign_keys=[tenant_id], back_populates="attribution_variance_records")

    __table_args__ = (
        Index("ix_fact_attribution_variance_daily_tenant_date", "tenant_id", "date"),
        Index("ix_fact_attribution_variance_daily_tenant_platform", "tenant_id", "platform"),
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
    action_type = Column(String(100), nullable=False)  # budget_increase, budget_decrease, pause, etc.
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
    status = Column(String(50), nullable=False, default="queued")  # queued, approved, applied, failed, dismissed

    # Actors
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
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
