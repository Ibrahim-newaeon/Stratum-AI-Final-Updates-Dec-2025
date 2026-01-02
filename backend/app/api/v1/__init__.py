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
    campaign_builder,
    feature_flags,
    insights,
    trust_layer,
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
