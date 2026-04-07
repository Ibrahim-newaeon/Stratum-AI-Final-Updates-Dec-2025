# =============================================================================
# Stratum AI - SQLAlchemy Base Configuration
# =============================================================================
"""
Base model configuration with common mixins and utilities.
All models inherit from this base for consistent behavior.
"""

from datetime import datetime, timezone
from typing import Any

import enum as _enum
import re as _re

from sqlalchemy import DateTime, Integer, MetaData, String, event, func, cast as sa_cast
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Enum as _SAEnum, TypeDecorator

# Naming convention for constraints (important for Alembic)
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class StrEnumType(TypeDecorator):
    """
    TypeDecorator that stores Python str-enums using their .value (lowercase).

    asyncpg + SQLAlchemy native Enum sends .name (UPPERCASE) which doesn't
    match PostgreSQL enum values (lowercase). This type:
    1. Converts Python enum -> lowercase .value on bind
    2. Adds CAST(... AS pg_enum_type) so PostgreSQL can compare
    3. Converts DB string -> Python enum on result
    """
    impl = String(50)
    cache_ok = True

    def __init__(self, enum_class: type, pg_type_name: str | None = None, **kw):
        self.enum_class = enum_class
        if pg_type_name:
            self._pg_enum_name = pg_type_name
        else:
            # Derive PG enum type name: CamelCase -> snake_case
            # Two-step regex handles acronyms: CRMProvider -> crm_provider
            name = enum_class.__name__
            s1 = _re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
            self._pg_enum_name = _re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
        super().__init__()

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, self.enum_class):
            return value.value
        if isinstance(value, _enum.Enum):
            return value.value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return self.enum_class(value)
        except (ValueError, KeyError):
            return value

    def bind_expression(self, bindvalue):
        """Cast the VARCHAR bind value to the PG ENUM type for comparison."""
        return sa_cast(bindvalue, _SAEnum(name=self._pg_enum_name, create_type=False))


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.
    Provides common columns and behaviors.
    """

    metadata = MetaData(naming_convention=convention)

    # Type annotation map for common types
    type_annotation_map = {
        datetime: DateTime(timezone=True),
    }

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Generate table name from class name (snake_case)."""
        import re

        name = cls.__name__
        return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()

    def to_dict(self) -> dict[str, Any]:
        """Convert model instance to dictionary."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class SoftDeleteMixin:
    """Mixin that adds soft delete capability."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    is_deleted: Mapped[bool] = mapped_column(default=False, nullable=False)

    def soft_delete(self) -> None:
        """Mark the record as deleted."""
        self.deleted_at = datetime.now(timezone.utc)
        self.is_deleted = True


class TenantMixin:
    """
    Mixin that adds tenant_id for multi-tenancy.
    Every query MUST filter by tenant_id for row-level security.
    """

    @declared_attr
    def tenant_id(cls) -> Mapped[int]:
        from sqlalchemy import ForeignKey
        return mapped_column(
            Integer,
            ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )

    @declared_attr
    def tenant(cls):
        from sqlalchemy.orm import relationship
        return relationship("Tenant", foreign_keys=[cls.tenant_id])


# =============================================================================
# Import all models here to ensure they're registered with Base
# =============================================================================
# This is done in a separate file to avoid circular imports
