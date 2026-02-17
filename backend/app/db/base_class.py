# =============================================================================
# Stratum AI - Base Class Compatibility Layer
# =============================================================================
# Re-exports from base.py for backwards compatibility

from app.db.base import Base, TimestampMixin, SoftDeleteMixin, TenantMixin

__all__ = ["Base", "TimestampMixin", "SoftDeleteMixin", "TenantMixin"]
