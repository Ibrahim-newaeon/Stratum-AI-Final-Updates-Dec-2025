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
    linkedin,
    ml_training,
    predictions,
    capi,
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
