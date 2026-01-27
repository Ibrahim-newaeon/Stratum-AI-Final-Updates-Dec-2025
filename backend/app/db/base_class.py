# =============================================================================
# Stratum AI - Base Class Compatibility Layer
# =============================================================================
# Re-exports from base.py for backwards compatibility

from app.db.base import Base, SoftDeleteMixin, TenantMixin, TimestampMixin

__all__ = ["Base", "TimestampMixin", "SoftDeleteMixin", "TenantMixin"]
