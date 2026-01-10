# =============================================================================
# Stratum AI - Meta CAPI QA Endpoints
# =============================================================================
"""
Meta Conversion API (CAPI) Quality Assurance endpoints.
Handles event collection with quality tracking.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/meta-capi")


@router.get("/health")
async def meta_capi_health():
    """Health check for Meta CAPI QA module."""
    return {"status": "healthy", "module": "meta_capi"}
