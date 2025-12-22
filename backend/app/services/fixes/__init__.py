"""EMQ One-Click Fix System Services"""

from app.services.fixes.catalog import FIX_CATALOG
from app.services.fixes.metrics import compute_platform_metrics

__all__ = ["FIX_CATALOG", "compute_platform_metrics"]
