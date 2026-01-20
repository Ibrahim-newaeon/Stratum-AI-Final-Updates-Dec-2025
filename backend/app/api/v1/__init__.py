# =============================================================================
# Stratum AI - API v1 Router Configuration
# =============================================================================
"""
Main API router that aggregates all endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    oauth,
    onboarding,
    dashboard,
    campaigns,
    assets,
    rules,
    competitors,
    simulator,
    analytics,
    gdpr,
    users,
    whatsapp,
    tenants,
    tenant_dashboard,
    ml_training,
    predictions,
    capi,
    meta_capi,
    landing_cms,
    qa_fixes,
    analytics_ai,
    superadmin,
    superadmin_analytics,
    autopilot,
    autopilot_enforcement,
    campaign_builder,
    feature_flags,
    insights,
    trust_layer,
    emq_v2,
    integrations,
    pacing,
    profit,
    attribution,
    data_driven_attribution,
    reporting,
    audit_services,
    cdp,
    audience_sync,
    tier,
    subscription,
    payments,
    stripe_webhook,
    mfa,
)

api_router = APIRouter()

# Authentication
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)

# OAuth (Ad Platform Connections)
api_router.include_router(
    oauth.router,
    tags=["OAuth"],
)

# Onboarding Wizard
api_router.include_router(
    onboarding.router,
    tags=["Onboarding"],
)

# Main Dashboard (Unified dashboard for frontend)
api_router.include_router(
    dashboard.router,
    tags=["Dashboard"],
)

# User management
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Users"],
)

# Tenant management
api_router.include_router(
    tenants.router,
    prefix="/tenants",
    tags=["Tenants"],
)

# Campaigns (Module B)
api_router.include_router(
    campaigns.router,
    prefix="/campaigns",
    tags=["Campaigns"],
)

# Creative Assets / DAM (Module B)
api_router.include_router(
    assets.router,
    prefix="/assets",
    tags=["Digital Assets"],
)

# Automation Rules (Module C)
api_router.include_router(
    rules.router,
    prefix="/rules",
    tags=["Automation Rules"],
)

# Competitor Intelligence (Module D)
api_router.include_router(
    competitors.router,
    prefix="/competitors",
    tags=["Competitor Intelligence"],
)

# ML Simulator (Module A)
api_router.include_router(
    simulator.router,
    prefix="/simulate",
    tags=["ML Simulator"],
)

# Analytics & Dashboard
api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["Analytics"],
)

# GDPR Compliance (Module F)
api_router.include_router(
    gdpr.router,
    prefix="/gdpr",
    tags=["GDPR Compliance"],
)

# WhatsApp Integration (Module G)
api_router.include_router(
    whatsapp.router,
    prefix="/whatsapp",
    tags=["WhatsApp"],
)

# ML Training & Data Upload
api_router.include_router(
    ml_training.router,
    prefix="/ml",
    tags=["ML Training"],
)

# Live Predictions & ROAS Optimization
api_router.include_router(
    predictions.router,
    prefix="/predictions",
    tags=["Live Predictions"],
)

# Conversion API (CAPI) Integration
api_router.include_router(
    capi.router,
    prefix="/capi",
    tags=["Conversion API"],
)

# Meta CAPI QA (Event collection with quality tracking)
api_router.include_router(
    meta_capi.router,
    tags=["Meta CAPI QA"],
)

# Landing Page CMS (Multi-language content management)
api_router.include_router(
    landing_cms.router,
    tags=["Landing CMS"],
)

# EMQ One-Click Fix System
api_router.include_router(
    qa_fixes.router,
    tags=["QA Fixes"],
)

# AI-Powered Analytics (Scaling scores, fatigue, anomalies, recommendations)
api_router.include_router(
    analytics_ai.router,
    prefix="/analytics/ai",
    tags=["AI Analytics"],
)

# Super Admin Dashboard (Platform-level management)
api_router.include_router(
    superadmin.router,
    prefix="/superadmin",
    tags=["Super Admin"],
)

# Tenant Dashboard (Tenant-scoped analytics and settings)
api_router.include_router(
    tenant_dashboard.router,
    prefix="/tenant",
    tags=["Tenant Dashboard"],
)

# Superadmin Analytics (Platform-wide analytics)
api_router.include_router(
    superadmin_analytics.router,
    prefix="/superadmin/analytics",
    tags=["Superadmin Analytics"],
)

# Autopilot (Automated campaign optimization)
api_router.include_router(
    autopilot.router,
    prefix="/autopilot",
    tags=["Autopilot"],
)

# Autopilot Enforcement (Budget/ROAS restrictions)
api_router.include_router(
    autopilot_enforcement.router,
    tags=["Autopilot Enforcement"],
)

# Campaign Builder (Multi-platform campaign creation)
api_router.include_router(
    campaign_builder.router,
    prefix="/campaign-builder",
    tags=["Campaign Builder"],
)

# Feature Flags (Feature toggles and rollouts)
api_router.include_router(
    feature_flags.router,
    prefix="/features",
    tags=["Feature Flags"],
)

# AI Insights (Intelligent recommendations)
api_router.include_router(
    insights.router,
    prefix="/insights",
    tags=["AI Insights"],
)

# Trust Layer (Data quality and signal health)
api_router.include_router(
    trust_layer.router,
    prefix="/trust",
    tags=["Trust Layer"],
)

# EMQ v2 (Event Measurement Quality - Enhanced)
api_router.include_router(
    emq_v2.router,
    tags=["EMQ v2"],
)

# Integrations (HubSpot, CRM, Attribution)
api_router.include_router(
    integrations.router,
    tags=["Integrations"],
)

# Pacing & Forecasting (Targets, Pacing Alerts, EOM Projections)
api_router.include_router(
    pacing.router,
    prefix="/pacing",
    tags=["Pacing & Forecasting"],
)

# Profit ROAS (Products, COGS, Profit Calculations)
api_router.include_router(
    profit.router,
    prefix="/profit",
    tags=["Profit ROAS"],
)

# Multi-Touch Attribution (MTA)
api_router.include_router(
    attribution.router,
    tags=["Attribution"],
)

# Data-Driven Attribution (ML-based)
api_router.include_router(
    data_driven_attribution.router,
    tags=["Data-Driven Attribution"],
)

# Automated Reporting (Scheduled reports, PDF generation, multi-channel delivery)
api_router.include_router(
    reporting.router,
    prefix="/reporting",
    tags=["Automated Reporting"],
)

# Audit Services (EMQ, Offline Conversions, A/B Testing, LTV, etc.)
api_router.include_router(
    audit_services.router,
    prefix="/audit",
    tags=["Audit Services"],
)

# CDP (Customer Data Platform - Event ingestion, profiles, identity resolution)
api_router.include_router(
    cdp.router,
    tags=["CDP"],
)

# CDP Audience Sync (Push segments to ad platforms)
api_router.include_router(
    audience_sync.router,
    tags=["CDP Audience Sync"],
)

# Subscription Tier (Feature access and limits)
api_router.include_router(
    tier.router,
    tags=["Subscription Tier"],
)

# Subscription Status (Expiry, billing, warnings)
api_router.include_router(
    subscription.router,
    tags=["Subscription"],
)

# Payment Processing (Stripe integration)
api_router.include_router(
    payments.router,
    tags=["Payments"],
)

# Stripe Webhooks (public endpoint for Stripe events)
api_router.include_router(
    stripe_webhook.router,
    tags=["Stripe Webhooks"],
)

# MFA (Two-Factor Authentication)
api_router.include_router(
    mfa.router,
    tags=["MFA"],
)
