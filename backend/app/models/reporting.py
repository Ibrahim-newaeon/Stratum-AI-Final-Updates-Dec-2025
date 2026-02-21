# =============================================================================
# Stratum AI - Automated Reporting Database Models
# =============================================================================
"""
Database models for automated reporting system.

Models:
- ReportTemplate: Configurable report definitions
- ScheduledReport: Report scheduling configuration
- ReportExecution: History of report runs
- ReportDelivery: Delivery tracking for each channel
"""

from datetime import datetime, date, timezone
from typing import Optional
from uuid import uuid4
import enum

import sqlalchemy as sa
from sqlalchemy import (
    Column, String, Integer, Date, DateTime, Float, Text, ForeignKey,
    Index, Enum as SQLEnum, Boolean, BigInteger, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship

from app.db.base_class import Base


# =============================================================================
# Enums
# =============================================================================

class ReportType(str, enum.Enum):
    """Types of reports available."""
    CAMPAIGN_PERFORMANCE = "campaign_performance"
    ATTRIBUTION_SUMMARY = "attribution_summary"
    PACING_STATUS = "pacing_status"
    PROFIT_ROAS = "profit_roas"
    PIPELINE_METRICS = "pipeline_metrics"
    EXECUTIVE_SUMMARY = "executive_summary"
    CUSTOM = "custom"


class ReportFormat(str, enum.Enum):
    """Output formats for reports."""
    PDF = "pdf"
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"
    HTML = "html"


class ScheduleFrequency(str, enum.Enum):
    """How often to run scheduled reports."""
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    CUSTOM = "custom"  # Uses cron expression


class DeliveryChannel(str, enum.Enum):
    """Delivery channels for reports."""
    EMAIL = "email"
    SLACK = "slack"
    TEAMS = "teams"
    WEBHOOK = "webhook"
    S3 = "s3"


class ExecutionStatus(str, enum.Enum):
    """Status of report execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DeliveryStatus(str, enum.Enum):
    """Status of report delivery."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"


# =============================================================================
# Report Template
# =============================================================================

class ReportTemplate(Base):
    """
    Configurable report template defining what data to include.
    """
    __tablename__ = "report_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Template identification
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    report_type = Column(SQLEnum(ReportType), nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)  # Built-in templates

    # Configuration
    config = Column(JSONB, nullable=False, default={})
    """
    Config structure varies by report_type:
    {
        "metrics": ["spend", "revenue", "roas", "conversions"],
        "dimensions": ["campaign", "platform", "date"],
        "filters": {"platforms": ["meta", "google"], "min_spend": 100},
        "date_range": {"type": "last_30_days"} or {"start": "2026-01-01", "end": "2026-01-31"},
        "comparison": {"enabled": true, "period": "previous_period"},
        "sections": ["summary", "charts", "detailed_table"],
        "branding": {"logo_url": "...", "primary_color": "#..."}
    }
    """

    # Output settings
    default_format = Column(SQLEnum(ReportFormat), default=ReportFormat.PDF, nullable=False)
    available_formats = Column(ARRAY(String), default=["pdf", "csv"], nullable=False)

    # Styling
    template_html = Column(Text, nullable=True)  # Custom HTML template
    chart_config = Column(JSONB, nullable=True)  # Chart configurations

    # Metadata
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    last_modified_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    last_modified_by = relationship("User", foreign_keys=[last_modified_by_user_id])
    schedules = relationship("ScheduledReport", back_populates="template", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_report_template_tenant", "tenant_id"),
        Index("ix_report_template_type", "tenant_id", "report_type"),
        UniqueConstraint("tenant_id", "name", name="uq_report_template_name"),
    )


# =============================================================================
# Scheduled Report
# =============================================================================

class ScheduledReport(Base):
    """
    Configuration for scheduled report generation.
    """
    __tablename__ = "scheduled_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey("report_templates.id", ondelete="CASCADE"), nullable=False)

    # Schedule identification
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_paused = Column(Boolean, default=False, nullable=False)

    # Schedule configuration
    frequency = Column(SQLEnum(ScheduleFrequency), nullable=False)
    cron_expression = Column(String(100), nullable=True)  # For custom frequency
    timezone = Column(String(50), default="UTC", nullable=False)

    # For weekly: which day (0=Monday, 6=Sunday)
    day_of_week = Column(Integer, nullable=True)
    # For monthly: which day (1-31, or -1 for last day)
    day_of_month = Column(Integer, nullable=True)
    # Time to run (hour in 24h format)
    hour = Column(Integer, default=8, nullable=False)
    minute = Column(Integer, default=0, nullable=False)

    # Report configuration overrides
    format_override = Column(SQLEnum(ReportFormat), nullable=True)
    config_override = Column(JSONB, nullable=True)  # Overrides template config

    # Date range for report (relative)
    date_range_type = Column(String(50), default="last_30_days", nullable=False)
    """
    Options: yesterday, last_7_days, last_30_days, last_month,
             month_to_date, quarter_to_date, year_to_date, custom
    """

    # Delivery configuration
    delivery_channels = Column(ARRAY(String), default=["email"], nullable=False)
    delivery_config = Column(JSONB, nullable=False, default={})
    """
    {
        "email": {
            "recipients": ["user@example.com"],
            "cc": [],
            "subject_template": "{{report_name}} - {{date_range}}",
            "body_template": "Please find attached..."
        },
        "slack": {
            "channel": "#reports",
            "webhook_url": "https://hooks.slack.com/..."
        },
        "teams": {
            "webhook_url": "https://outlook.office.com/webhook/..."
        }
    }
    """

    # Execution tracking
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    last_run_status = Column(SQLEnum(ExecutionStatus), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    run_count = Column(Integer, default=0, nullable=False)
    failure_count = Column(Integer, default=0, nullable=False)

    # Metadata
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    template = relationship("ReportTemplate", back_populates="schedules")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    executions = relationship("ReportExecution", back_populates="schedule", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_scheduled_report_tenant", "tenant_id"),
        Index("ix_scheduled_report_next_run", "next_run_at", postgresql_where=sa.text("is_active = true AND is_paused = false")),
        Index("ix_scheduled_report_template", "template_id"),
    )


# =============================================================================
# Report Execution
# =============================================================================

class ReportExecution(Base):
    """
    History of report generation runs.
    """
    __tablename__ = "report_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey("report_templates.id", ondelete="SET NULL"), nullable=True)
    schedule_id = Column(UUID(as_uuid=True), ForeignKey("scheduled_reports.id", ondelete="SET NULL"), nullable=True)

    # Execution details
    execution_type = Column(String(50), nullable=False)  # scheduled, manual, api
    status = Column(SQLEnum(ExecutionStatus), nullable=False, default=ExecutionStatus.PENDING)

    # Timing
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Report parameters
    report_type = Column(SQLEnum(ReportType), nullable=False)
    format = Column(SQLEnum(ReportFormat), nullable=False)
    date_range_start = Column(Date, nullable=False)
    date_range_end = Column(Date, nullable=False)
    config_used = Column(JSONB, nullable=True)  # Snapshot of config at execution time

    # Output
    file_path = Column(String(500), nullable=True)  # Path to generated file
    file_size_bytes = Column(BigInteger, nullable=True)
    file_url = Column(Text, nullable=True)  # Signed URL for download
    file_url_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Report data summary
    row_count = Column(Integer, nullable=True)
    metrics_summary = Column(JSONB, nullable=True)  # Quick summary of key metrics

    # Error tracking
    error_message = Column(Text, nullable=True)
    error_details = Column(JSONB, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)

    # Triggered by
    triggered_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    template = relationship("ReportTemplate", foreign_keys=[template_id])
    schedule = relationship("ScheduledReport", back_populates="executions")
    triggered_by = relationship("User", foreign_keys=[triggered_by_user_id])
    deliveries = relationship("ReportDelivery", back_populates="execution", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_report_execution_tenant", "tenant_id", "started_at"),
        Index("ix_report_execution_status", "tenant_id", "status"),
        Index("ix_report_execution_schedule", "schedule_id"),
    )


# =============================================================================
# Report Delivery
# =============================================================================

class ReportDelivery(Base):
    """
    Tracks delivery of reports to each channel.
    """
    __tablename__ = "report_deliveries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    execution_id = Column(UUID(as_uuid=True), ForeignKey("report_executions.id", ondelete="CASCADE"), nullable=False)

    # Delivery details
    channel = Column(SQLEnum(DeliveryChannel), nullable=False)
    status = Column(SQLEnum(DeliveryStatus), nullable=False, default=DeliveryStatus.PENDING)

    # Recipient info
    recipient = Column(String(500), nullable=False)  # Email, channel name, webhook URL
    recipient_type = Column(String(50), nullable=True)  # user, group, webhook

    # Timing
    queued_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)

    # Delivery metadata
    message_id = Column(String(255), nullable=True)  # External message ID (email, Slack ts)
    delivery_response = Column(JSONB, nullable=True)  # Response from delivery service

    # Error tracking
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    last_retry_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    execution = relationship("ReportExecution", back_populates="deliveries")

    __table_args__ = (
        Index("ix_report_delivery_execution", "execution_id"),
        Index("ix_report_delivery_status", "tenant_id", "status"),
        Index("ix_report_delivery_channel", "tenant_id", "channel"),
    )


# =============================================================================
# Delivery Channel Configuration
# =============================================================================

class DeliveryChannelConfig(Base):
    """
    Tenant-level configuration for delivery channels.
    """
    __tablename__ = "delivery_channel_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Channel
    channel = Column(SQLEnum(DeliveryChannel), nullable=False)
    name = Column(String(255), nullable=False)  # Friendly name

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Configuration (encrypted sensitive data)
    config = Column(JSONB, nullable=False)
    """
    Email:
    {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "...",
        "smtp_password_enc": "...",
        "from_email": "reports@company.com",
        "from_name": "Stratum Reports"
    }

    Slack:
    {
        "webhook_url_enc": "...",
        "bot_token_enc": "...",
        "default_channel": "#reports"
    }

    Teams:
    {
        "webhook_url_enc": "..."
    }

    S3:
    {
        "bucket": "my-reports",
        "prefix": "stratum/",
        "aws_access_key_enc": "...",
        "aws_secret_key_enc": "...",
        "region": "us-east-1"
    }
    """

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    __table_args__ = (
        Index("ix_delivery_config_tenant", "tenant_id"),
        UniqueConstraint("tenant_id", "channel", "name", name="uq_delivery_config"),
    )


