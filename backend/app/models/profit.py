# =============================================================================
# Stratum AI - Profit ROAS Database Models
# =============================================================================
"""
Database models for Profit ROAS calculations.

Models:
- ProductCatalog: Product definitions with SKU, category
- ProductMargin: COGS and margin data per product (time-series)
- MarginRule: Default margin rules by category/platform
- DailyProfitMetrics: Daily profit calculations per campaign/product
- ProfitROASReport: Aggregated profit ROAS reports
"""

from datetime import datetime, date
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

class MarginType(str, enum.Enum):
    """How margin/COGS is specified."""
    FIXED_AMOUNT = "fixed_amount"  # Fixed dollar amount per unit
    PERCENTAGE = "percentage"  # Percentage of revenue
    TIERED = "tiered"  # Different rates at different volumes


class ProductStatus(str, enum.Enum):
    """Product status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISCONTINUED = "discontinued"


class COGSSource(str, enum.Enum):
    """Source of COGS data."""
    MANUAL = "manual"  # Manually entered
    CSV_UPLOAD = "csv_upload"  # Uploaded via CSV
    API_SYNC = "api_sync"  # Synced from external system
    ERP_INTEGRATION = "erp_integration"  # From ERP system
    SHOPIFY = "shopify"
    WOOCOMMERCE = "woocommerce"


# =============================================================================
# Product Catalog Model
# =============================================================================

class ProductCatalog(Base):
    """
    Product catalog with SKU and category information.
    Used for matching conversions to products for profit calculation.
    """
    __tablename__ = "product_catalog"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Product identification
    sku = Column(String(100), nullable=False)
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Categorization
    category = Column(String(255), nullable=True)
    subcategory = Column(String(255), nullable=True)
    brand = Column(String(255), nullable=True)
    product_type = Column(String(100), nullable=True)

    # Pricing
    base_price_cents = Column(BigInteger, nullable=True)  # List price
    currency = Column(String(3), default="USD", nullable=False)

    # Status
    status = Column(SQLEnum(ProductStatus), default=ProductStatus.ACTIVE, nullable=False)

    # External IDs (for matching with platform data)
    external_ids = Column(JSONB, nullable=True)  # {"shopify_id": "...", "meta_product_id": "..."}

    # Metadata
    attributes = Column(JSONB, nullable=True)  # Custom attributes

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    margins = relationship("ProductMargin", back_populates="product", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_product_catalog_tenant_sku", "tenant_id", "sku"),
        Index("ix_product_catalog_tenant_category", "tenant_id", "category"),
        UniqueConstraint("tenant_id", "sku", name="uq_product_sku"),
    )


# =============================================================================
# Product Margin Model (Time-Series)
# =============================================================================

class ProductMargin(Base):
    """
    COGS and margin data per product.
    Supports time-series for historical margin changes.
    """
    __tablename__ = "product_margins"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("product_catalog.id", ondelete="CASCADE"), nullable=False)

    # Effective period
    effective_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)  # Null = current/ongoing

    # COGS data
    cogs_cents = Column(BigInteger, nullable=True)  # Cost of goods sold per unit
    cogs_percentage = Column(Float, nullable=True)  # COGS as % of revenue (alternative)

    # Margin data (derived or specified)
    margin_type = Column(SQLEnum(MarginType), default=MarginType.FIXED_AMOUNT, nullable=False)
    margin_cents = Column(BigInteger, nullable=True)  # Profit per unit in cents
    margin_percentage = Column(Float, nullable=True)  # Gross margin %

    # Additional costs
    shipping_cost_cents = Column(BigInteger, default=0)
    handling_cost_cents = Column(BigInteger, default=0)
    platform_fee_cents = Column(BigInteger, default=0)  # Marketplace fees
    payment_processing_cents = Column(BigInteger, default=0)

    # Total landed cost
    total_cogs_cents = Column(BigInteger, nullable=True)  # COGS + shipping + handling + fees

    # Source tracking
    source = Column(SQLEnum(COGSSource), default=COGSSource.MANUAL, nullable=False)
    source_reference = Column(String(255), nullable=True)  # File name, API endpoint, etc.

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    product = relationship("ProductCatalog", back_populates="margins")
    created_by = relationship("User", foreign_keys=[created_by_user_id])

    __table_args__ = (
        Index("ix_product_margins_product_date", "product_id", "effective_date"),
        Index("ix_product_margins_tenant_date", "tenant_id", "effective_date"),
    )


# =============================================================================
# Margin Rule Model (Default Rules)
# =============================================================================

class MarginRule(Base):
    """
    Default margin rules by category, platform, or campaign.
    Used when specific product margin is not available.
    """
    __tablename__ = "margin_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Rule identification
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Rule scope (priority: product > campaign > platform > category > default)
    priority = Column(Integer, default=100, nullable=False)  # Lower = higher priority
    category = Column(String(255), nullable=True)  # Product category
    subcategory = Column(String(255), nullable=True)
    platform = Column(String(50), nullable=True)  # meta, google, etc.
    campaign_id = Column(String(255), nullable=True)

    # Margin specification
    margin_type = Column(SQLEnum(MarginType), default=MarginType.PERCENTAGE, nullable=False)
    default_margin_percentage = Column(Float, nullable=True)  # e.g., 30% gross margin
    default_cogs_percentage = Column(Float, nullable=True)  # e.g., 70% COGS

    # Tiered margins (for volume-based pricing)
    tiered_config = Column(JSONB, nullable=True)
    # Example: [{"min_units": 0, "max_units": 100, "margin_pct": 25}, {"min_units": 101, "margin_pct": 30}]

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    __table_args__ = (
        Index("ix_margin_rules_tenant_priority", "tenant_id", "priority"),
        Index("ix_margin_rules_tenant_category", "tenant_id", "category"),
    )


# =============================================================================
# Daily Profit Metrics Model
# =============================================================================

class DailyProfitMetrics(Base):
    """
    Daily profit calculations aggregated by campaign/product.
    Materialized table for fast profit ROAS queries.
    """
    __tablename__ = "daily_profit_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)

    # Scope
    platform = Column(String(50), nullable=True)
    campaign_id = Column(String(255), nullable=True)
    adset_id = Column(String(255), nullable=True)
    ad_id = Column(String(255), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("product_catalog.id", ondelete="SET NULL"), nullable=True)

    # Revenue metrics
    units_sold = Column(Integer, default=0, nullable=False)
    gross_revenue_cents = Column(BigInteger, default=0, nullable=False)
    net_revenue_cents = Column(BigInteger, default=0, nullable=False)  # After discounts/returns
    average_order_value_cents = Column(BigInteger, nullable=True)

    # Cost metrics
    total_cogs_cents = Column(BigInteger, default=0, nullable=False)
    product_cogs_cents = Column(BigInteger, default=0, nullable=False)
    shipping_costs_cents = Column(BigInteger, default=0, nullable=False)
    platform_fees_cents = Column(BigInteger, default=0, nullable=False)
    payment_fees_cents = Column(BigInteger, default=0, nullable=False)

    # Ad spend
    ad_spend_cents = Column(BigInteger, default=0, nullable=False)

    # Profit calculations
    gross_profit_cents = Column(BigInteger, default=0, nullable=False)  # Revenue - COGS
    contribution_margin_cents = Column(BigInteger, default=0, nullable=False)  # Gross profit - variable costs
    net_profit_cents = Column(BigInteger, default=0, nullable=False)  # After ad spend

    # ROAS metrics
    revenue_roas = Column(Float, nullable=True)  # Traditional: Revenue / Ad Spend
    gross_profit_roas = Column(Float, nullable=True)  # Gross Profit / Ad Spend
    contribution_roas = Column(Float, nullable=True)  # Contribution Margin / Ad Spend
    net_profit_roas = Column(Float, nullable=True)  # Net Profit / Ad Spend (can be negative)

    # Margin percentages
    gross_margin_pct = Column(Float, nullable=True)  # Gross Profit / Revenue
    contribution_margin_pct = Column(Float, nullable=True)
    net_margin_pct = Column(Float, nullable=True)

    # Data quality
    cogs_source = Column(SQLEnum(COGSSource), nullable=True)
    margin_rule_id = Column(UUID(as_uuid=True), ForeignKey("margin_rules.id", ondelete="SET NULL"), nullable=True)
    is_estimated = Column(Boolean, default=False, nullable=False)  # True if using default margins

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    product = relationship("ProductCatalog", foreign_keys=[product_id])
    margin_rule = relationship("MarginRule", foreign_keys=[margin_rule_id])

    __table_args__ = (
        Index("ix_daily_profit_tenant_date", "tenant_id", "date"),
        Index("ix_daily_profit_tenant_campaign", "tenant_id", "campaign_id", "date"),
        Index("ix_daily_profit_tenant_product", "tenant_id", "product_id", "date"),
        UniqueConstraint("tenant_id", "date", "platform", "campaign_id", "product_id", name="uq_daily_profit_scope"),
    )


# =============================================================================
# Profit ROAS Report Model
# =============================================================================

class ProfitROASReport(Base):
    """
    Aggregated profit ROAS reports for dashboard/export.
    Stores pre-calculated summaries for different time periods.
    """
    __tablename__ = "profit_roas_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Report period
    report_type = Column(String(50), nullable=False)  # daily, weekly, monthly, custom
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # Scope
    platform = Column(String(50), nullable=True)  # null = all platforms
    campaign_id = Column(String(255), nullable=True)
    category = Column(String(255), nullable=True)

    # Aggregated metrics
    total_units = Column(Integer, default=0, nullable=False)
    total_revenue_cents = Column(BigInteger, default=0, nullable=False)
    total_cogs_cents = Column(BigInteger, default=0, nullable=False)
    total_ad_spend_cents = Column(BigInteger, default=0, nullable=False)
    total_gross_profit_cents = Column(BigInteger, default=0, nullable=False)
    total_net_profit_cents = Column(BigInteger, default=0, nullable=False)

    # ROAS metrics
    revenue_roas = Column(Float, nullable=True)
    gross_profit_roas = Column(Float, nullable=True)
    net_profit_roas = Column(Float, nullable=True)

    # Margin metrics
    avg_gross_margin_pct = Column(Float, nullable=True)
    avg_net_margin_pct = Column(Float, nullable=True)

    # Breakeven analysis
    breakeven_roas = Column(Float, nullable=True)  # ROAS needed to break even
    above_breakeven = Column(Boolean, nullable=True)

    # Comparison to target
    target_profit_roas = Column(Float, nullable=True)
    vs_target_pct = Column(Float, nullable=True)

    # Data quality
    products_with_cogs = Column(Integer, default=0)
    products_estimated = Column(Integer, default=0)
    data_completeness_pct = Column(Float, nullable=True)

    # Report metadata
    generated_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    generated_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    generated_by = relationship("User", foreign_keys=[generated_by_user_id])

    __table_args__ = (
        Index("ix_profit_reports_tenant_period", "tenant_id", "period_start", "period_end"),
        Index("ix_profit_reports_tenant_type", "tenant_id", "report_type"),
    )


# =============================================================================
# COGS Upload History
# =============================================================================

class COGSUpload(Base):
    """
    History of COGS data uploads for audit trail.
    """
    __tablename__ = "cogs_uploads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Upload metadata
    filename = Column(String(500), nullable=True)
    file_type = Column(String(50), nullable=False)  # csv, xlsx, api
    source = Column(SQLEnum(COGSSource), nullable=False)

    # Processing results
    status = Column(String(50), nullable=False)  # pending, processing, completed, failed
    rows_processed = Column(Integer, default=0)
    rows_succeeded = Column(Integer, default=0)
    rows_failed = Column(Integer, default=0)
    error_details = Column(JSONB, nullable=True)

    # Affected date range
    effective_date = Column(Date, nullable=True)
    products_updated = Column(Integer, default=0)

    # Timestamps
    uploaded_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_user_id])

    __table_args__ = (
        Index("ix_cogs_uploads_tenant_date", "tenant_id", "uploaded_at"),
    )
