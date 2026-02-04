# =============================================================================
# Stratum AI - Profit ROAS Services Package
# =============================================================================
"""
Services for Profit ROAS calculations and COGS management.
"""

from app.services.profit.cogs_service import COGSIngestionService, COGSService
from app.services.profit.product_service import ProductCatalogService
from app.services.profit.profit_service import ProfitCalculationService

__all__ = [
    "ProfitCalculationService",
    "COGSService",
    "COGSIngestionService",
    "ProductCatalogService",
]
