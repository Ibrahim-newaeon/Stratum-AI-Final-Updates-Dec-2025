# =============================================================================
# Stratum AI - API v1 Router Configuration
# =============================================================================
"""
Main API router that aggregates all endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    campaigns,
    assets,
    dashboard,
    rules,
    competitors,
    simulator,
    analytics,
    gdpr,
    users,
    whatsapp,
    tenants,
    tenant_dashboard,
    linkedin,
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
    newsletter,
    mfa,
    onboarding,
    oauth,
    notifications,
    api_keys,
    cdp,
    changelog,
    clients,
    # Previously unregistered endpoints
    cms,
    knowledge_graph,
    tier,
    webhooks,
    payments,
    stripe_webhook,
    subscription,
    slack,
    onboarding_agent,
    embed_widgets,
    audience_sync,
)

api_router = APIRouter()

# Authentication
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
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

# LinkedIn Ads Integration
api_router.include_router(
    linkedin.router,
    prefix="/linkedin",
    tags=["LinkedIn Ads"],
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

# Dashboard (Overview metrics, signal health, campaigns, settings)
# Note: dashboard.router already has prefix="/dashboard"
api_router.include_router(
    dashboard.router,
    tags=["Dashboard"],
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
    prefix="/autopilot/enforcement",
    tags=["Autopilot Enforcement"],
)

# Campaign Builder (Multi-platform campaign creation)
api_router.include_router(
    campaign_builder.router,
    prefix="/campaign-builder",
    tags=["Campaign Builder"],
)

# Feature Flags (Feature toggles and rollouts)
# Note: feature_flags.router already has /tenant/{tenant_id} and /superadmin prefixes
api_router.include_router(
    feature_flags.router,
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

# Newsletter & Email Campaigns
# Note: newsletter.router already has prefix="/newsletter"
api_router.include_router(
    newsletter.router,
    tags=["Newsletter"],
)

# Multi-Factor Authentication (2FA/MFA)
# Note: mfa.router already has prefix="/mfa"
api_router.include_router(
    mfa.router,
    tags=["MFA"],
)

# Onboarding (Guided setup wizard)
# Note: onboarding.router already has prefix="/onboarding"
api_router.include_router(
    onboarding.router,
    tags=["Onboarding"],
)

# OAuth (Platform authorization flows)
# Note: oauth.router already has prefix="/oauth"
api_router.include_router(
    oauth.router,
    tags=["OAuth"],
)

# Notifications (In-app notifications)
# Note: notifications.router already has prefix="/notifications"
api_router.include_router(
    notifications.router,
    tags=["Notifications"],
)

# API Keys Management
# Note: api_keys.router already has prefix="/api-keys"
api_router.include_router(
    api_keys.router,
    tags=["API Keys"],
)

# CDP (Customer Data Platform)
# Note: cdp.router already has prefix="/cdp"
api_router.include_router(
    cdp.router,
    tags=["CDP"],
)

# Changelog
# Note: changelog.router already has prefix="/changelog"
api_router.include_router(
    changelog.router,
    tags=["Changelog"],
)

# Client Management
api_router.include_router(
    clients.router,
    prefix="/clients",
    tags=["Clients"],
)

# =============================================================================
# Previously Unregistered Endpoints
# =============================================================================

# CMS (Content Management System - Blog, Pages, Contact)
# Note: cms.router already has prefix="/cms"
api_router.include_router(
    cms.router,
    tags=["CMS"],
)

# Knowledge Graph (Insights, Analytics, Problem Detection)
api_router.include_router(
    knowledge_graph.router,
    prefix="/knowledge-graph",
    tags=["Knowledge Graph"],
)

# Tier Management (Subscription tiers and feature gates)
# Note: tier.router already has prefix="/tier"
api_router.include_router(
    tier.router,
    tags=["Tier"],
)

# Webhooks (Inbound webhook processing)
# Note: webhooks.router already has prefix="/webhooks"
api_router.include_router(
    webhooks.router,
    tags=["Webhooks"],
)

# Payments (Stripe payment processing)
# Note: payments.router already has prefix="/payments"
api_router.include_router(
    payments.router,
    tags=["Payments"],
)

# Stripe Webhooks (Stripe event processing)
api_router.include_router(
    stripe_webhook.router,
    tags=["Stripe Webhooks"],
)

# Subscription Management
# Note: subscription.router already has prefix="/subscription"
api_router.include_router(
    subscription.router,
    tags=["Subscription"],
)

# Slack Integration
# Note: slack.router already has prefix="/slack"
api_router.include_router(
    slack.router,
    tags=["Slack"],
)

# Onboarding Agent (AI-powered onboarding assistant)
# Note: onboarding_agent.router already has prefix="/onboarding-agent"
api_router.include_router(
    onboarding_agent.router,
    tags=["Onboarding Agent"],
)

# Embeddable Widgets (External dashboard widgets)
# Note: embed_widgets.router already has prefix="/embed-widgets"
api_router.include_router(
    embed_widgets.router,
    tags=["Embed Widgets"],
)

# CDP Audience Sync (Push segments to ad platforms)
# Note: audience_sync.router already has prefix="/cdp/audience-sync"
api_router.include_router(
    audience_sync.router,
    tags=["CDP Audience Sync"],
)
