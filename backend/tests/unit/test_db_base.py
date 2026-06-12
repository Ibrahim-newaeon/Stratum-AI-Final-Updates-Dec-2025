# =============================================================================
# Stratum AI - DB Base / Mixins unit tests
# =============================================================================
"""Unit tests for app.db.base.

Pure SQLAlchemy helper logic, no database. Covers the StrEnumType
TypeDecorator (the asyncpg enum-casing bridge: bind/result conversion +
PG enum-name derivation), the auto snake_case __tablename__, to_dict
serialization, and the soft-delete mixin.
"""

import enum

import pytest
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, StrEnumType

pytestmark = pytest.mark.unit


class Color(str, enum.Enum):
    RED = "red"
    BLUE = "blue"


class CRMProvider(str, enum.Enum):
    HUBSPOT = "hubspot"


# =============================================================================
# StrEnumType - bind / result conversion
# =============================================================================
class TestStrEnumBind:
    def test_enum_binds_to_value(self):
        t = StrEnumType(Color)
        assert t.process_bind_param(Color.RED, None) == "red"

    def test_none_passthrough(self):
        t = StrEnumType(Color)
        assert t.process_bind_param(None, None) is None
        assert t.process_result_value(None, None) is None

    def test_foreign_enum_uses_value(self):
        class Other(str, enum.Enum):
            X = "x"

        t = StrEnumType(Color)
        assert t.process_bind_param(Other.X, None) == "x"

    def test_raw_string_stringified(self):
        t = StrEnumType(Color)
        assert t.process_bind_param("green", None) == "green"

    def test_result_parses_back_to_enum(self):
        t = StrEnumType(Color)
        assert t.process_result_value("blue", None) is Color.BLUE

    def test_result_unknown_value_passthrough(self):
        t = StrEnumType(Color)
        # value not in enum -> returned as-is rather than raising
        assert t.process_result_value("purple", None) == "purple"


# =============================================================================
# StrEnumType - PG enum name derivation
# =============================================================================
class TestPgEnumName:
    def test_simple_camelcase(self):
        assert StrEnumType(Color)._pg_enum_name == "color"

    def test_acronym_prefix(self):
        # CRMProvider -> crm_provider (two-step regex handles the acronym)
        assert StrEnumType(CRMProvider)._pg_enum_name == "crm_provider"

    def test_explicit_name_override(self):
        t = StrEnumType(Color, pg_type_name="custom_color_enum")
        assert t._pg_enum_name == "custom_color_enum"


# =============================================================================
# Base.__tablename__ + to_dict
# =============================================================================
class WidgetThing(Base):
    __tablename__ = "widget_thing_test"
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(default="")


class AutoNamed(Base):
    id: Mapped[int] = mapped_column(primary_key=True)


class TestBaseHelpers:
    def test_tablename_snake_case(self):
        # CamelCase class name -> snake_case table name
        assert AutoNamed.__tablename__ == "auto_named"

    def test_to_dict_returns_columns(self):
        row = WidgetThing(id=7, label="hello")
        assert row.to_dict() == {"id": 7, "label": "hello"}


# =============================================================================
# SoftDeleteMixin
# =============================================================================
class SoftRow(Base, SoftDeleteMixin):
    __tablename__ = "soft_row_test"
    id: Mapped[int] = mapped_column(primary_key=True)


class TestSoftDelete:
    def test_soft_delete_sets_flags(self):
        row = SoftRow(id=1)
        row.is_deleted = False
        row.deleted_at = None
        row.soft_delete()
        assert row.is_deleted is True
        assert row.deleted_at is not None
