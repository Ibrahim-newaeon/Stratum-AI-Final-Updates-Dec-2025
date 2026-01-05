# =============================================================================
# Stratum AI - Landing Page CMS Endpoints
# =============================================================================
"""
Landing Page CMS endpoints for multi-language content management.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/landing-cms")


@router.get("/health")
async def landing_cms_health():
    """Health check for Landing CMS module."""
    return {"status": "healthy", "module": "landing_cms"}
