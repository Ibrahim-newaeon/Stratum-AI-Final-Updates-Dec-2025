# =============================================================================
# Stratum AI - Audit Services Database Models
# =============================================================================
"""
Database models for audit-recommended services:
- EMQ Measurements
- Offline Conversions
- Model A/B Testing
- Conversion Latency
- Creative Performance
- Competitor Benchmarks
- Budget Reallocation
- Audience Insights
- LTV Predictions
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


# =============================================================================
# Enums
# =============================================================================

class EMQStatus(str, enum.Enum):
    """EMQ calculation status."""
    PENDING = "pending"
    CALCULATED = "calculated"
    FAILED = "failed"


class ConversionUploadStatus(str, enum.Enum):
    """Offline conversion upload status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class ExperimentStatus(str, enum.Enum):
    """Model experiment status."""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ReallocationStatus(str, enum.Enum):
    """Budget reallocation status."""
    PROPOSED = "proposed"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"
    REJECTED = "rejected"


class CustomerSegment(str, enum.Enum):
    """Customer LTV segment."""
    VIP = "vip"
    HIGH_VALUE = "high_value"
    MEDIUM_VALUE = "medium_value"
    LOW_VALUE = "low_value"
    AT_RISK = "at_risk"


# =============================================================================
# EMQ Measurements
# =============================================================================

class EMQMeasurement(Base):
    """
    Stores EMQ (Event Match Quality) measurements from platforms.
    """
    __tablename__ = "emq_measurements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Measurement details
    platform = Column(String(50), nullable=False)  # meta, google, tiktok, etc.
    pixel_id = Column(String(255), nullable=False)
    measurement_date = Column(Date, nullable=False)
    event_type = Column(String(100), nullable=False)  # Purchase, Lead, AddToCart, etc.

    # EMQ scores (0-10 scale)
    overall_score = Column(Float, nullable=True)
    parameter_quality = Column(Float, nullable=True)
    deduplication_quality = Column(Float, nullable=True)
    event_coverage = Column(Float, nullable=True)

    # Event counts
    events_received = Column(Integer, default=0, nullable=False)
    events_matched = Column(Integer, default=0, nullable=False)
    events_attributed = Column(Integer, default=0, nullable=False)

    # Match rates
    email_match_rate = Column(Float, nullable=True)
    phone_match_rate = Column(Float, nullable=True)
    combined_match_rate = Column(Float, nullable=True)

    # Status
    status = Column(SQLEnum(EMQStatus), default=EMQStatus.PENDING, nullable=False)
    error_message = Column(Text, nullable=True)

    # Raw response
    raw_response = Column(JSONB, nullable=True)

    # Recommendations
    recommendations = Column(JSONB, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    __table_args__ = (
        Index("ix_emq_tenant_date", "tenant_id", "measurement_date"),
        Index("ix_emq_platform", "tenant_id", "platform", "pixel_id"),
        UniqueConstraint(
            "tenant_id", "platform", "pixel_id", "measurement_date", "event_type",
            name="uq_emq_measurement"
        ),
    )


# =============================================================================
# Offline Conversions
# =============================================================================

class OfflineConversionBatch(Base):
    """
    Tracks batches of offline conversions uploaded to platforms.
    """
    __tablename__ = "offline_conversion_batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Batch details
    batch_name = Column(String(255), nullable=True)
    platform = Column(String(50), nullable=False)
    upload_type = Column(String(50), nullable=False)  # crm_sync, manual, scheduled

    # Counts
    total_records = Column(Integer, default=0, nullable=False)
    successful_records = Column(Integer, default=0, nullable=False)
    failed_records = Column(Integer, default=0, nullable=False)
    duplicate_records = Column(Integer, default=0, nullable=False)

    # Status
    status = Column(SQLEnum(ConversionUploadStatus), default=ConversionUploadStatus.PENDING, nullable=False)
    error_message = Column(Text, nullable=True)
    error_details = Column(JSONB, nullable=True)

    # Platform response
    platform_batch_id = Column(String(255), nullable=True)
    platform_response = Column(JSONB, nullable=True)

    # File info
    source_file = Column(String(500), nullable=True)
    file_hash = Column(String(64), nullable=True)

    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Created by
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])

    __table_args__ = (
        Index("ix_offline_batch_tenant", "tenant_id", "created_at"),
        Index("ix_offline_batch_status", "tenant_id", "status"),
    )


class OfflineConversion(Base):
    """
    Individual offline conversion records.
    """
    __tablename__ = "offline_conversions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("offline_conversion_batches.id", ondelete="CASCADE"), nullable=True)

    # Conversion details
    event_name = Column(String(100), nullable=False)
    event_time = Column(DateTime(timezone=True), nullable=False)
    value_cents = Column(BigInteger, nullable=True)
    currency = Column(String(3), default="USD", nullable=False)

    # Identifiers (hashed)
    email_hash = Column(String(64), nullable=True)
    phone_hash = Column(String(64), nullable=True)
    external_id = Column(String(255), nullable=True)
    click_id = Column(String(255), nullable=True)  # fbclid, gclid, etc.

    # Platform info
    platform = Column(String(50), nullable=False)
    platform_event_id = Column(String(255), nullable=True)

    # Upload status
    uploaded = Column(Boolean, default=False, nullable=False)
    upload_attempts = Column(Integer, default=0, nullable=False)
    last_upload_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    batch = relationship("OfflineConversionBatch", foreign_keys=[batch_id])

    __table_args__ = (
        Index("ix_offline_conv_tenant", "tenant_id", "event_time"),
        Index("ix_offline_conv_batch", "batch_id"),
        Index("ix_offline_conv_uploaded", "tenant_id", "uploaded"),
    )


# =============================================================================
# Model A/B Testing
# =============================================================================

class ModelExperiment(Base):
    """
    ML model A/B testing experiments.
    """
    __tablename__ = "model_experiments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Experiment details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    model_name = Column(String(100), nullable=False)  # roas_model, ltv_model, etc.

    # Variants
    champion_version = Column(String(50), nullable=False)
    challenger_version = Column(String(50), nullable=False)

    # Traffic split (0-1, percentage going to challenger)
    traffic_split = Column(Float, default=0.1, nullable=False)

    # Status
    status = Column(SQLEnum(ExperimentStatus), default=ExperimentStatus.DRAFT, nullable=False)

    # Configuration
    min_samples = Column(Integer, default=1000, nullable=False)
    significance_threshold = Column(Float, default=0.05, nullable=False)
    primary_metric = Column(String(50), default="mae", nullable=False)

    # Results
    champion_predictions = Column(Integer, default=0, nullable=False)
    challenger_predictions = Column(Integer, default=0, nullable=False)
    champion_metrics = Column(JSONB, nullable=True)
    challenger_metrics = Column(JSONB, nullable=True)
    winner = Column(String(20), nullable=True)  # champion, challenger, inconclusive

    # Statistical results
    p_value = Column(Float, nullable=True)
    effect_size = Column(Float, nullable=True)
    confidence_interval = Column(JSONB, nullable=True)

    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Created by
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])

    __table_args__ = (
        Index("ix_model_exp_tenant", "tenant_id"),
        Index("ix_model_exp_status", "tenant_id", "status"),
        Index("ix_model_exp_model", "tenant_id", "model_name"),
    )


class ExperimentPrediction(Base):
    """
    Individual predictions made during an experiment.
    """
    __tablename__ = "experiment_predictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    experiment_id = Column(UUID(as_uuid=True), ForeignKey("model_experiments.id", ondelete="CASCADE"), nullable=False)

    # Prediction details
    entity_id = Column(String(255), nullable=False)  # campaign_id, customer_id, etc.
    variant = Column(String(20), nullable=False)  # champion, challenger
    predicted_value = Column(Float, nullable=False)
    actual_value = Column(Float, nullable=True)

    # Features used
    features = Column(JSONB, nullable=True)

    # Timestamps
    predicted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    actual_recorded_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_exp_pred_experiment", "experiment_id"),
        Index("ix_exp_pred_variant", "experiment_id", "variant"),
    )


# =============================================================================
# Conversion Latency
# =============================================================================

class ConversionLatency(Base):
    """
    Tracks latency between ad click and conversion.
    """
    __tablename__ = "conversion_latencies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Event details
    platform = Column(String(50), nullable=False)
    event_type = Column(String(100), nullable=False)
    event_id = Column(String(255), nullable=True)

    # Latency measurement (milliseconds)
    latency_ms = Column(Integer, nullable=False)

    # Context
    campaign_id = Column(String(255), nullable=True)
    source = Column(String(50), nullable=True)  # browser, server, mobile

    # Timestamps
    event_time = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    __table_args__ = (
        Index("ix_conv_latency_tenant", "tenant_id", "event_time"),
        Index("ix_conv_latency_platform", "tenant_id", "platform", "event_type"),
    )


class ConversionLatencyStats(Base):
    """
    Aggregated conversion latency statistics by period.
    """
    __tablename__ = "conversion_latency_stats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Aggregation period
    period_date = Column(Date, nullable=False)
    platform = Column(String(50), nullable=False)
    event_type = Column(String(100), nullable=False)

    # Statistics (milliseconds)
    event_count = Column(Integer, default=0, nullable=False)
    avg_latency_ms = Column(Float, nullable=True)
    median_latency_ms = Column(Float, nullable=True)
    p95_latency_ms = Column(Float, nullable=True)
    p99_latency_ms = Column(Float, nullable=True)
    min_latency_ms = Column(Integer, nullable=True)
    max_latency_ms = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    __table_args__ = (
        Index("ix_latency_stats_tenant", "tenant_id", "period_date"),
        UniqueConstraint(
            "tenant_id", "period_date", "platform", "event_type",
            name="uq_latency_stats"
        ),
    )


# =============================================================================
# Creative Performance
# =============================================================================

class Creative(Base):
    """
    Creative assets being tracked.
    """
    __tablename__ = "creatives"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Creative details
    external_id = Column(String(255), nullable=False)  # Platform's creative ID
    platform = Column(String(50), nullable=False)
    name = Column(String(500), nullable=True)
    creative_type = Column(String(50), nullable=True)  # image, video, carousel, etc.

    # Asset info
    asset_url = Column(Text, nullable=True)
    thumbnail_url = Column(Text, nullable=True)

    # Metadata (named 'creative_metadata' to avoid conflict with SQLAlchemy reserved 'metadata')
    creative_metadata = Column("metadata", JSONB, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    first_seen_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    __table_args__ = (
        Index("ix_creative_tenant", "tenant_id"),
        Index("ix_creative_external", "tenant_id", "platform", "external_id"),
        UniqueConstraint("tenant_id", "platform", "external_id", name="uq_creative"),
    )


class CreativePerformance(Base):
    """
    Daily creative performance metrics.
    """
    __tablename__ = "creative_performance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    creative_id = Column(UUID(as_uuid=True), ForeignKey("creatives.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Period
    date = Column(Date, nullable=False)
    campaign_id = Column(String(255), nullable=True)

    # Metrics
    impressions = Column(Integer, default=0, nullable=False)
    clicks = Column(Integer, default=0, nullable=False)
    conversions = Column(Integer, default=0, nullable=False)
    spend_cents = Column(BigInteger, default=0, nullable=False)
    revenue_cents = Column(BigInteger, default=0, nullable=False)

    # Calculated metrics
    ctr = Column(Float, nullable=True)
    cvr = Column(Float, nullable=True)
    cpc_cents = Column(Integer, nullable=True)
    cpm_cents = Column(Integer, nullable=True)
    roas = Column(Float, nullable=True)

    # Engagement metrics
    video_views = Column(Integer, default=0, nullable=False)
    video_completions = Column(Integer, default=0, nullable=False)
    engagements = Column(Integer, default=0, nullable=False)
    shares = Column(Integer, default=0, nullable=False)

    # Fatigue indicators
    frequency = Column(Float, nullable=True)  # avg impressions per user
    reach = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    creative = relationship("Creative", foreign_keys=[creative_id])
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    __table_args__ = (
        Index("ix_creative_perf_tenant", "tenant_id", "date"),
        Index("ix_creative_perf_creative", "creative_id", "date"),
        UniqueConstraint("creative_id", "date", "campaign_id", name="uq_creative_perf"),
    )


class CreativeFatigueAlert(Base):
    """
    Alerts when creative fatigue is detected.
    """
    __tablename__ = "creative_fatigue_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    creative_id = Column(UUID(as_uuid=True), ForeignKey("creatives.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Alert details
    alert_type = Column(String(50), nullable=False)  # declining_ctr, high_frequency, etc.
    severity = Column(String(20), nullable=False)  # info, warning, critical

    # Metrics at alert time
    current_ctr = Column(Float, nullable=True)
    baseline_ctr = Column(Float, nullable=True)
    ctr_decline_percent = Column(Float, nullable=True)
    current_frequency = Column(Float, nullable=True)
    days_active = Column(Integer, nullable=True)

    # Recommendations
    recommendation = Column(Text, nullable=True)

    # Status
    is_acknowledged = Column(Boolean, default=False, nullable=False)
    acknowledged_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    creative = relationship("Creative", foreign_keys=[creative_id])
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    acknowledged_by = relationship("User", foreign_keys=[acknowledged_by_user_id])

    __table_args__ = (
        Index("ix_fatigue_alert_tenant", "tenant_id", "created_at"),
        Index("ix_fatigue_alert_creative", "creative_id"),
    )


# =============================================================================
# Competitor Benchmarking
# =============================================================================

class CompetitorBenchmarkAudit(Base):
    """
    Stores detailed competitor benchmark audit comparisons.
    Extended version with percentile rankings and recommendations.
    """
    __tablename__ = "competitor_benchmark_audits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Benchmark context
    date = Column(Date, nullable=False)
    industry = Column(String(100), nullable=False)
    region = Column(String(50), nullable=False)
    platform = Column(String(50), nullable=False)

    # Your metrics
    your_metrics = Column(JSONB, nullable=False)

    # Industry benchmarks
    industry_metrics = Column(JSONB, nullable=False)  # {metric: {p25, p50, p75, p90, avg}}

    # Percentile rankings
    percentile_rankings = Column(JSONB, nullable=False)  # {metric: percentile}

    # Performance summary
    overall_score = Column(Float, nullable=True)  # 0-100
    metrics_above_median = Column(Integer, default=0, nullable=False)
    metrics_below_median = Column(Integer, default=0, nullable=False)

    # Recommendations
    recommendations = Column(JSONB, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    __table_args__ = (
        Index("ix_benchmark_tenant", "tenant_id", "date"),
        Index("ix_benchmark_industry", "tenant_id", "industry", "platform"),
    )


# =============================================================================
# Budget Reallocation
# =============================================================================

class BudgetReallocationPlan(Base):
    """
    Budget reallocation plans.
    """
    __tablename__ = "budget_reallocation_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Plan details
    name = Column(String(255), nullable=True)
    strategy = Column(String(50), nullable=False)  # roas_maximization, volume_maximization, etc.

    # Configuration
    config = Column(JSONB, nullable=False)

    # Budget summary
    total_current_budget_cents = Column(BigInteger, nullable=False)
    total_new_budget_cents = Column(BigInteger, nullable=False)
    campaigns_affected = Column(Integer, default=0, nullable=False)

    # Expected impact
    projected_roas_change = Column(Float, nullable=True)
    projected_spend_change = Column(Float, nullable=True)
    projected_revenue_change = Column(Float, nullable=True)

    # Status
    status = Column(SQLEnum(ReallocationStatus), default=ReallocationStatus.PROPOSED, nullable=False)

    # Approval
    approved_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Execution
    executed_at = Column(DateTime(timezone=True), nullable=True)
    rolled_back_at = Column(DateTime(timezone=True), nullable=True)
    rollback_reason = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Created by
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    approved_by = relationship("User", foreign_keys=[approved_by_user_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])

    __table_args__ = (
        Index("ix_realloc_plan_tenant", "tenant_id", "created_at"),
        Index("ix_realloc_plan_status", "tenant_id", "status"),
    )


class BudgetReallocationChange(Base):
    """
    Individual campaign budget changes in a reallocation plan.
    """
    __tablename__ = "budget_reallocation_changes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("budget_reallocation_plans.id", ondelete="CASCADE"), nullable=False)

    # Campaign details
    campaign_id = Column(String(255), nullable=False)
    campaign_name = Column(String(500), nullable=True)
    platform = Column(String(50), nullable=False)

    # Budget change
    current_budget_cents = Column(BigInteger, nullable=False)
    new_budget_cents = Column(BigInteger, nullable=False)
    change_percent = Column(Float, nullable=False)

    # Rationale
    reason = Column(Text, nullable=True)
    performance_metrics = Column(JSONB, nullable=True)

    # Execution status
    executed = Column(Boolean, default=False, nullable=False)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    execution_error = Column(Text, nullable=True)

    # Relationships
    plan = relationship("BudgetReallocationPlan", foreign_keys=[plan_id])

    __table_args__ = (
        Index("ix_realloc_change_plan", "plan_id"),
    )


# =============================================================================
# Audience Insights
# =============================================================================

class AudienceRecord(Base):
    """
    Audience records for analysis.
    """
    __tablename__ = "audience_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Audience details
    external_id = Column(String(255), nullable=False)
    platform = Column(String(50), nullable=False)
    name = Column(String(500), nullable=False)
    audience_type = Column(String(50), nullable=False)  # custom, lookalike, interest, etc.
    size = Column(Integer, nullable=True)

    # Configuration
    lookalike_percent = Column(Float, nullable=True)
    source_audience_id = Column(String(255), nullable=True)

    # Quality scores
    quality_score = Column(Float, nullable=True)  # 0-100
    expansion_potential = Column(String(20), nullable=True)  # high, medium, low, saturated

    # Performance
    current_metrics = Column(JSONB, nullable=True)
    historical_metrics = Column(JSONB, nullable=True)

    # LTV data
    avg_ltv = Column(Float, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    __table_args__ = (
        Index("ix_audience_tenant", "tenant_id"),
        Index("ix_audience_external", "tenant_id", "platform", "external_id"),
        UniqueConstraint("tenant_id", "platform", "external_id", name="uq_audience"),
    )


class AudienceOverlapRecord(Base):
    """
    Records of overlap between audiences.
    """
    __tablename__ = "audience_overlaps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    audience_id_1 = Column(UUID(as_uuid=True), ForeignKey("audience_records.id", ondelete="CASCADE"), nullable=False)
    audience_id_2 = Column(UUID(as_uuid=True), ForeignKey("audience_records.id", ondelete="CASCADE"), nullable=False)

    # Overlap metrics
    overlap_percent = Column(Float, nullable=False)
    overlap_size = Column(Integer, nullable=True)

    # Analysis date
    analyzed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    audience_1 = relationship("AudienceRecord", foreign_keys=[audience_id_1])
    audience_2 = relationship("AudienceRecord", foreign_keys=[audience_id_2])

    __table_args__ = (
        Index("ix_overlap_tenant", "tenant_id"),
        Index("ix_overlap_audiences", "audience_id_1", "audience_id_2"),
    )


# =============================================================================
# LTV Predictions
# =============================================================================

class CustomerLTVPrediction(Base):
    """
    Customer lifetime value predictions.
    """
    __tablename__ = "customer_ltv_predictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Customer identifier
    customer_id = Column(String(255), nullable=False)
    external_id = Column(String(255), nullable=True)

    # Acquisition info
    acquisition_date = Column(Date, nullable=True)
    acquisition_channel = Column(String(100), nullable=True)

    # Behavior metrics (at prediction time)
    total_orders = Column(Integer, default=0, nullable=False)
    total_revenue_cents = Column(BigInteger, default=0, nullable=False)
    avg_order_value_cents = Column(Integer, nullable=True)
    days_since_last_order = Column(Integer, nullable=True)

    # Predictions
    predicted_ltv_30d_cents = Column(BigInteger, nullable=True)
    predicted_ltv_90d_cents = Column(BigInteger, nullable=True)
    predicted_ltv_365d_cents = Column(BigInteger, nullable=True)
    predicted_ltv_lifetime_cents = Column(BigInteger, nullable=True)

    # Segment
    segment = Column(SQLEnum(CustomerSegment), nullable=True)

    # Risk
    churn_probability = Column(Float, nullable=True)

    # Confidence
    confidence = Column(Float, nullable=True)

    # Recommendation
    max_cac_cents = Column(Integer, nullable=True)

    # Model info
    model_version = Column(String(50), nullable=True)

    # Timestamps
    predicted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    __table_args__ = (
        Index("ix_ltv_pred_tenant", "tenant_id", "predicted_at"),
        Index("ix_ltv_pred_customer", "tenant_id", "customer_id"),
        Index("ix_ltv_pred_segment", "tenant_id", "segment"),
    )


class LTVCohortAnalysis(Base):
    """
    Cohort-based LTV analysis.
    """
    __tablename__ = "ltv_cohort_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Cohort identifier
    cohort_month = Column(String(7), nullable=False)  # YYYY-MM

    # Cohort metrics
    customer_count = Column(Integer, default=0, nullable=False)
    total_revenue_cents = Column(BigInteger, default=0, nullable=False)
    avg_ltv_cents = Column(BigInteger, nullable=True)
    median_ltv_cents = Column(BigInteger, nullable=True)
    ltv_p90_cents = Column(BigInteger, nullable=True)

    # Purchase metrics
    avg_orders = Column(Float, nullable=True)
    avg_retention_days = Column(Float, nullable=True)

    # Segment distribution
    segment_distribution = Column(JSONB, nullable=True)

    # Analysis date
    analyzed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    __table_args__ = (
        Index("ix_ltv_cohort_tenant", "tenant_id"),
        UniqueConstraint("tenant_id", "cohort_month", name="uq_ltv_cohort"),
    )


# =============================================================================
# Model Retraining
# =============================================================================

class ModelRetrainingJob(Base):
    """
    Model retraining job records.
    """
    __tablename__ = "model_retraining_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)  # Null for global models

    # Job details
    model_name = Column(String(100), nullable=False)
    job_type = Column(String(50), nullable=False)  # scheduled, manual, triggered
    trigger_reason = Column(Text, nullable=True)

    # Status
    status = Column(String(50), nullable=False)  # pending, running, completed, failed
    error_message = Column(Text, nullable=True)

    # Training data
    training_start_date = Column(Date, nullable=True)
    training_end_date = Column(Date, nullable=True)
    sample_count = Column(Integer, nullable=True)

    # Model info
    old_version = Column(String(50), nullable=True)
    new_version = Column(String(50), nullable=True)

    # Metrics
    old_metrics = Column(JSONB, nullable=True)
    new_metrics = Column(JSONB, nullable=True)
    improvement = Column(JSONB, nullable=True)

    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    __table_args__ = (
        Index("ix_retrain_job_tenant", "tenant_id", "created_at"),
        Index("ix_retrain_job_model", "model_name", "created_at"),
        Index("ix_retrain_job_status", "status"),
    )
