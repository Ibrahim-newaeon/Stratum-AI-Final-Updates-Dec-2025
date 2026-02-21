# =============================================================================
# Stratum AI - Attribution Database Models
# =============================================================================
"""
Database models for Multi-Touch Attribution (MTA).

Models:
- DailyAttributedRevenue: Pre-calculated attributed revenue by model
- ConversionPath: Aggregated conversion path statistics
- AttributionSnapshot: Point-in-time attribution snapshots for comparison
- ChannelInteraction: Channel transition matrix for Sankey visualization
- TrainedAttributionModel: Stored data-driven models (Markov/Shapley)
"""

from datetime import datetime, date, timezone
from typing import Optional
from uuid import uuid4
import enum

from sqlalchemy import (
    Column, String, Integer, Date, DateTime, Float, Text, ForeignKey,
    Index, Enum as SQLEnum, Boolean, BigInteger, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.crm import AttributionModel


# =============================================================================
# Daily Attributed Revenue (Pre-calculated)
# =============================================================================

class DailyAttributedRevenue(Base):
    """
    Pre-calculated daily attributed revenue by model and dimension.

    Enables fast reporting without recalculating attribution on every request.
    Updated daily via scheduled job.
    """
    __tablename__ = "daily_attributed_revenue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)

    # Attribution model used
    attribution_model = Column(SQLEnum(AttributionModel), nullable=False)

    # Dimension (what we're attributing to)
    dimension_type = Column(String(50), nullable=False)  # platform, campaign, adset, ad
    dimension_id = Column(String(255), nullable=False)
    dimension_name = Column(String(500), nullable=True)

    # Attribution metrics
    attributed_revenue_cents = Column(BigInteger, default=0, nullable=False)
    attributed_deals = Column(Float, default=0, nullable=False)  # Fractional for multi-touch
    attributed_pipeline_cents = Column(BigInteger, default=0, nullable=False)

    # Touchpoint metrics
    touchpoint_count = Column(Integer, default=0, nullable=False)
    first_touch_count = Column(Integer, default=0, nullable=False)
    last_touch_count = Column(Integer, default=0, nullable=False)
    assisted_count = Column(Integer, default=0, nullable=False)

    # Spend (for ROAS calculations)
    spend_cents = Column(BigInteger, default=0, nullable=False)

    # Calculated ROAS
    attributed_roas = Column(Float, nullable=True)

    # Unique contacts reached
    unique_contacts = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    __table_args__ = (
        Index("ix_daily_attributed_rev_tenant_date", "tenant_id", "date"),
        Index("ix_daily_attributed_rev_model", "tenant_id", "attribution_model", "date"),
        Index("ix_daily_attributed_rev_dimension", "tenant_id", "dimension_type", "dimension_id", "date"),
        UniqueConstraint(
            "tenant_id", "date", "attribution_model", "dimension_type", "dimension_id",
            name="uq_daily_attributed_rev"
        ),
    )


# =============================================================================
# Conversion Path Statistics
# =============================================================================

class ConversionPath(Base):
    """
    Aggregated statistics for conversion paths.

    Tracks which sequences of touchpoints lead to conversions.
    """
    __tablename__ = "conversion_paths"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Path identifier
    path_hash = Column(String(64), nullable=False)  # SHA256 of path string
    path_string = Column(Text, nullable=False)  # e.g., "google → meta → google"
    path_type = Column(String(50), nullable=False)  # platform, campaign

    # Path structure
    path_length = Column(Integer, nullable=False)
    unique_channels = Column(Integer, nullable=False)
    first_channel = Column(String(100), nullable=True)
    last_channel = Column(String(100), nullable=True)

    # Period
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # Conversion metrics
    conversions = Column(Integer, default=0, nullable=False)
    total_revenue_cents = Column(BigInteger, default=0, nullable=False)
    avg_deal_size_cents = Column(BigInteger, default=0, nullable=False)

    # Time metrics (in hours)
    avg_time_to_conversion = Column(Float, nullable=True)
    min_time_to_conversion = Column(Float, nullable=True)
    max_time_to_conversion = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    __table_args__ = (
        Index("ix_conversion_paths_tenant_period", "tenant_id", "period_start", "period_end"),
        Index("ix_conversion_paths_hash", "tenant_id", "path_hash"),
        Index("ix_conversion_paths_conversions", "tenant_id", "conversions"),
        UniqueConstraint(
            "tenant_id", "path_hash", "path_type", "period_start", "period_end",
            name="uq_conversion_path"
        ),
    )


# =============================================================================
# Attribution Snapshot (Historical Comparison)
# =============================================================================

class AttributionSnapshot(Base):
    """
    Point-in-time snapshot of attribution for historical comparison.

    Allows comparing how attribution has changed over time.
    """
    __tablename__ = "attribution_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Snapshot metadata
    snapshot_date = Column(Date, nullable=False)
    snapshot_type = Column(String(50), nullable=False)  # daily, weekly, monthly
    attribution_model = Column(SQLEnum(AttributionModel), nullable=False)

    # Period covered
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # Summary metrics
    total_revenue_cents = Column(BigInteger, default=0, nullable=False)
    total_deals = Column(Integer, default=0, nullable=False)
    total_touchpoints = Column(Integer, default=0, nullable=False)
    unique_contacts = Column(Integer, default=0, nullable=False)

    # Journey metrics
    avg_touches_per_conversion = Column(Float, nullable=True)
    avg_time_to_conversion_hours = Column(Float, nullable=True)
    avg_unique_channels = Column(Float, nullable=True)

    # Top performers (JSON for flexibility)
    top_campaigns = Column(JSONB, nullable=True)  # [{campaign_id, revenue, deals}, ...]
    top_platforms = Column(JSONB, nullable=True)  # [{platform, revenue, deals}, ...]
    top_paths = Column(JSONB, nullable=True)  # [{path, conversions, revenue}, ...]

    # Channel contribution
    channel_mix = Column(JSONB, nullable=True)  # {platform: percentage, ...}

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    __table_args__ = (
        Index("ix_attribution_snapshot_tenant_date", "tenant_id", "snapshot_date"),
        Index("ix_attribution_snapshot_model", "tenant_id", "attribution_model", "snapshot_date"),
        UniqueConstraint(
            "tenant_id", "snapshot_date", "snapshot_type", "attribution_model",
            name="uq_attribution_snapshot"
        ),
    )


# =============================================================================
# Channel Interaction Matrix
# =============================================================================

class ChannelInteraction(Base):
    """
    Tracks channel-to-channel transitions for Sankey visualization.

    Pre-aggregated for performance.
    """
    __tablename__ = "channel_interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Period
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # Transition
    from_channel = Column(String(100), nullable=False)
    to_channel = Column(String(100), nullable=False)
    transition_type = Column(String(50), nullable=False)  # platform, campaign

    # Metrics
    transition_count = Column(Integer, default=0, nullable=False)
    unique_journeys = Column(Integer, default=0, nullable=False)

    # Revenue attributed to this transition
    attributed_revenue_cents = Column(BigInteger, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    __table_args__ = (
        Index("ix_channel_interaction_tenant_period", "tenant_id", "period_start", "period_end"),
        Index("ix_channel_interaction_from", "tenant_id", "from_channel"),
        UniqueConstraint(
            "tenant_id", "period_start", "period_end", "from_channel", "to_channel", "transition_type",
            name="uq_channel_interaction"
        ),
    )


# =============================================================================
# Data-Driven Model Type Enum
# =============================================================================

class DataDrivenModelType(str, enum.Enum):
    """Types of data-driven attribution models."""
    MARKOV_CHAIN = "markov_chain"
    SHAPLEY_VALUE = "shapley_value"


class ModelStatus(str, enum.Enum):
    """Status of trained models."""
    TRAINING = "training"
    ACTIVE = "active"
    ARCHIVED = "archived"
    FAILED = "failed"


# =============================================================================
# Trained Attribution Model Storage
# =============================================================================

class TrainedAttributionModel(Base):
    """
    Stores trained data-driven attribution models.

    Models can be trained periodically and stored for fast attribution
    without recomputing from scratch.
    """
    __tablename__ = "trained_attribution_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Model identification
    model_name = Column(String(255), nullable=False)
    model_type = Column(SQLEnum(DataDrivenModelType), nullable=False)
    channel_type = Column(String(50), nullable=False)  # platform, campaign

    # Status
    status = Column(SQLEnum(ModelStatus), nullable=False, default=ModelStatus.TRAINING)
    is_active = Column(Boolean, default=False, nullable=False)  # Currently used for attribution

    # Training period
    training_start = Column(Date, nullable=False)
    training_end = Column(Date, nullable=False)

    # Training statistics
    journey_count = Column(Integer, nullable=True)
    converting_journeys = Column(Integer, nullable=True)
    unique_channels = Column(Integer, nullable=True)

    # Model results
    attribution_weights = Column(JSONB, nullable=True)  # {channel: weight, ...}
    model_data = Column(JSONB, nullable=True)  # Full serialized model

    # For Markov Chain
    removal_effects = Column(JSONB, nullable=True)  # {channel: effect, ...}
    baseline_conversion_rate = Column(Float, nullable=True)

    # For Shapley Value
    shapley_values = Column(JSONB, nullable=True)  # {channel: value, ...}

    # Validation metrics
    validation_accuracy = Column(Float, nullable=True)
    validation_period_start = Column(Date, nullable=True)
    validation_period_end = Column(Date, nullable=True)

    # Metadata
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])

    __table_args__ = (
        Index("ix_trained_model_tenant", "tenant_id"),
        Index("ix_trained_model_active", "tenant_id", "is_active"),
        Index("ix_trained_model_type", "tenant_id", "model_type"),
    )


# =============================================================================
# Model Training History
# =============================================================================

class ModelTrainingRun(Base):
    """
    History of model training runs for auditing and debugging.
    """
    __tablename__ = "model_training_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    model_id = Column(UUID(as_uuid=True), ForeignKey("trained_attribution_models.id", ondelete="CASCADE"), nullable=True)

    # Run details
    model_type = Column(SQLEnum(DataDrivenModelType), nullable=False)
    channel_type = Column(String(50), nullable=False)
    status = Column(SQLEnum(ModelStatus), nullable=False, default=ModelStatus.TRAINING)

    # Training period
    training_start = Column(Date, nullable=False)
    training_end = Column(Date, nullable=False)

    # Configuration
    include_non_converting = Column(Boolean, default=True)
    min_journeys = Column(Integer, default=100)

    # Timing
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Results
    journey_count = Column(Integer, nullable=True)
    converting_journeys = Column(Integer, nullable=True)
    unique_channels = Column(Integer, nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)
    error_details = Column(JSONB, nullable=True)

    # Triggered by
    triggered_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    model = relationship("TrainedAttributionModel", foreign_keys=[model_id])
    triggered_by = relationship("User", foreign_keys=[triggered_by_user_id])

    __table_args__ = (
        Index("ix_training_run_tenant", "tenant_id", "started_at"),
        Index("ix_training_run_status", "tenant_id", "status"),
    )
