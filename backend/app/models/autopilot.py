# =============================================================================
# Stratum AI - Autopilot Database Models
# =============================================================================
"""
Database models for Autopilot Enforcement settings and audit logging.

Models:
- TenantEnforcementSettings: Per-tenant enforcement configuration
- TenantEnforcementRule: Custom enforcement rules
- EnforcementAuditLog: Intervention audit log
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4
import enum

from sqlalchemy import (
    Column, String, Integer, DateTime, Float, Text, ForeignKey,
    Index, Enum as SQLEnum, Boolean, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base_class import Base, TimestampMixin


# =============================================================================
# Enums
# =============================================================================

class EnforcementMode(str, enum.Enum):
    """Autopilot enforcement modes."""
    ADVISORY = "advisory"      # Warn only, no blocking
    SOFT_BLOCK = "soft_block"  # Warn + require confirmation to proceed
    HARD_BLOCK = "hard_block"  # Prevent action via API, log override attempts


class ViolationType(str, enum.Enum):
    """Types of enforcement rule violations."""
    BUDGET_EXCEEDED = "budget_exceeded"
    ROAS_BELOW_THRESHOLD = "roas_below_threshold"
    DAILY_SPEND_LIMIT = "daily_spend_limit"
    CAMPAIGN_PAUSE_REQUIRED = "campaign_pause_required"
    FREQUENCY_CAP_EXCEEDED = "frequency_cap_exceeded"


class InterventionAction(str, enum.Enum):
    """Actions taken by enforcer."""
    WARNED = "warned"
    BLOCKED = "blocked"
    AUTO_PAUSED = "auto_paused"
    OVERRIDE_LOGGED = "override_logged"
    NOTIFICATION_SENT = "notification_sent"
    KILL_SWITCH_CHANGED = "kill_switch_changed"


# =============================================================================
# Tenant Enforcement Settings Model
# =============================================================================

class TenantEnforcementSettings(Base, TimestampMixin):
    """
    Per-tenant enforcement configuration.
    One row per tenant storing all enforcement settings.
    """
    __tablename__ = "tenant_enforcement_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Kill switch
    enforcement_enabled = Column(Boolean, nullable=False, default=True)

    # Default mode
    default_mode = Column(
        SQLEnum(
            EnforcementMode,
            name='enforcement_mode',
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=EnforcementMode.ADVISORY,
    )

    # Budget thresholds
    max_daily_budget = Column(Float, nullable=True)
    max_campaign_budget = Column(Float, nullable=True)
    budget_increase_limit_pct = Column(Float, nullable=False, default=30.0)

    # ROAS thresholds
    min_roas_threshold = Column(Float, nullable=False, default=1.0)
    roas_lookback_days = Column(Integer, nullable=False, default=7)

    # Frequency settings
    max_budget_changes_per_day = Column(Integer, nullable=False, default=5)
    min_hours_between_changes = Column(Integer, nullable=False, default=4)

    # Relationships
    tenant = relationship("Tenant", backref="enforcement_settings")
    rules = relationship(
        "TenantEnforcementRule",
        back_populates="settings",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_tenant_enforcement_settings_tenant_id", "tenant_id"),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "tenant_id": self.tenant_id,
            "enforcement_enabled": self.enforcement_enabled,
            "default_mode": self.default_mode.value if isinstance(self.default_mode, EnforcementMode) else self.default_mode,
            "max_daily_budget": self.max_daily_budget,
            "max_campaign_budget": self.max_campaign_budget,
            "budget_increase_limit_pct": self.budget_increase_limit_pct,
            "min_roas_threshold": self.min_roas_threshold,
            "roas_lookback_days": self.roas_lookback_days,
            "max_budget_changes_per_day": self.max_budget_changes_per_day,
            "min_hours_between_changes": self.min_hours_between_changes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# =============================================================================
# Custom Enforcement Rules Model
# =============================================================================

class TenantEnforcementRule(Base, TimestampMixin):
    """
    Custom enforcement rules per tenant.
    Allows fine-grained control over specific thresholds.
    """
    __tablename__ = "tenant_enforcement_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    settings_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenant_enforcement_settings.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Rule configuration
    rule_id = Column(String(100), nullable=False)
    rule_type = Column(
        SQLEnum(
            ViolationType,
            name='violation_type',
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    threshold_value = Column(Float, nullable=False)
    enforcement_mode = Column(
        SQLEnum(
            EnforcementMode,
            name='enforcement_mode',
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=EnforcementMode.ADVISORY,
    )
    enabled = Column(Boolean, nullable=False, default=True)
    description = Column(Text, nullable=True)

    # Relationships
    settings = relationship("TenantEnforcementSettings", back_populates="rules")

    __table_args__ = (
        UniqueConstraint("tenant_id", "rule_id", name="uq_tenant_rule_id"),
        Index("ix_tenant_enforcement_rules_tenant_id", "tenant_id"),
        Index("ix_tenant_enforcement_rules_settings_id", "settings_id"),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "rule_id": self.rule_id,
            "rule_type": self.rule_type.value if isinstance(self.rule_type, ViolationType) else self.rule_type,
            "threshold_value": self.threshold_value,
            "enforcement_mode": self.enforcement_mode.value if isinstance(self.enforcement_mode, EnforcementMode) else self.enforcement_mode,
            "enabled": self.enabled,
            "description": self.description,
        }


# =============================================================================
# Enforcement Audit Log Model
# =============================================================================

class EnforcementAuditLog(Base):
    """
    Audit log for all enforcement interventions.
    Tracks blocks, warnings, overrides, and auto-pause events.
    """
    __tablename__ = "enforcement_audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Timestamp
    timestamp = Column(DateTime(timezone=True), nullable=False)

    # Action context
    action_type = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(255), nullable=False)

    # Violation details
    violation_type = Column(
        SQLEnum(
            ViolationType,
            name='violation_type',
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )

    # Intervention details
    intervention_action = Column(
        SQLEnum(
            InterventionAction,
            name='intervention_action',
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    enforcement_mode = Column(
        SQLEnum(
            EnforcementMode,
            name='enforcement_mode',
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )

    # Additional context
    details = Column(JSONB, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    override_reason = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_enforcement_audit_logs_tenant_id", "tenant_id"),
        Index("ix_enforcement_audit_logs_timestamp", "timestamp"),
        Index("ix_enforcement_audit_logs_action_type", "action_type"),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "tenant_id": self.tenant_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "action_type": self.action_type,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "violation_type": self.violation_type.value if isinstance(self.violation_type, ViolationType) else self.violation_type,
            "intervention_action": self.intervention_action.value if isinstance(self.intervention_action, InterventionAction) else self.intervention_action,
            "enforcement_mode": self.enforcement_mode.value if isinstance(self.enforcement_mode, EnforcementMode) else self.enforcement_mode,
            "details": self.details,
            "user_id": self.user_id,
            "override_reason": self.override_reason,
        }


# =============================================================================
# Pending Confirmation Tokens Model
# =============================================================================

class PendingConfirmationToken(Base):
    """
    Stores pending soft-block confirmation tokens.
    Tokens expire after a configured time period.
    """
    __tablename__ = "pending_confirmation_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token = Column(String(64), nullable=False, unique=True, index=True)

    # Context
    action_type = Column(String(100), nullable=False)
    entity_id = Column(String(255), nullable=False)
    violations = Column(JSONB, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_pending_confirmation_tokens_token", "token"),
        Index("ix_pending_confirmation_tokens_tenant_id", "tenant_id"),
        Index("ix_pending_confirmation_tokens_expires_at", "expires_at"),
    )
