# =============================================================================
# Stratum AI - Report Date-Range Parsing Unit Tests
# =============================================================================
"""Unit tests for ``ReportGenerator.parse_date_range`` in
``app.services.reporting.report_generator`` — the pure relative-to-absolute
date-range resolver shared by exports and scheduled reports. It is a
staticmethod, so no DB session is needed.
"""

from datetime import date

import pytest

from app.services.reporting.report_generator import ReportGenerator

pytestmark = pytest.mark.unit

# A mid-quarter, mid-month reference so every branch is unambiguous.
REF = date(2026, 5, 20)  # Wednesday, Q2


def _range(kind: str):
    return ReportGenerator.parse_date_range(kind, reference_date=REF)


class TestDayRanges:
    def test_today(self):
        assert _range("today") == (REF, REF)

    def test_yesterday(self):
        assert _range("yesterday") == (date(2026, 5, 19), date(2026, 5, 19))


class TestRollingWindows:
    @pytest.mark.parametrize(
        "kind,start",
        [
            ("last_7_days", date(2026, 5, 14)),  # 7 inclusive
            ("last_30_days", date(2026, 4, 21)),  # 30 inclusive
            ("last_90_days", date(2026, 2, 20)),  # 90 inclusive
        ],
    )
    def test_inclusive_rolling_window_ends_today(self, kind, start):
        assert _range(kind) == (start, REF)


class TestCalendarRanges:
    def test_this_month(self):
        assert _range("this_month") == (date(2026, 5, 1), REF)

    def test_month_to_date_alias(self):
        assert _range("month_to_date") == _range("this_month")

    def test_last_month(self):
        assert _range("last_month") == (date(2026, 4, 1), date(2026, 4, 30))

    def test_quarter_to_date(self):
        # Q2 starts in April.
        assert _range("quarter_to_date") == (date(2026, 4, 1), REF)

    def test_year_to_date(self):
        assert _range("year_to_date") == (date(2026, 1, 1), REF)


class TestEdgeCases:
    def test_unknown_kind_defaults_to_last_7_days(self):
        assert _range("garbage") == (date(2026, 5, 14), REF)

    def test_last_month_handles_january_to_december_rollover(self):
        start, end = ReportGenerator.parse_date_range(
            "last_month", reference_date=date(2026, 1, 15)
        )
        assert start == date(2025, 12, 1)
        assert end == date(2025, 12, 31)

    def test_quarter_to_date_q1(self):
        start, _ = ReportGenerator.parse_date_range(
            "quarter_to_date", reference_date=date(2026, 2, 10)
        )
        assert start == date(2026, 1, 1)

    def test_defaults_reference_to_today_when_omitted(self):
        # Smoke check: with no reference_date it still returns a valid ordered pair.
        start, end = ReportGenerator.parse_date_range("today")
        assert start == end
