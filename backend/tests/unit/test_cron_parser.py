# =============================================================================
# Stratum AI - Cron Parser Unit Tests
# =============================================================================
"""Unit tests for the pure ``CronParser`` in
``app.services.reporting.scheduler``: field parsing (wildcards, lists,
ranges, steps), full-expression parsing, and next-run calculation. The
DB-backed ReportScheduler is out of scope here.
"""

from datetime import datetime, timezone

import pytest

from app.services.reporting.scheduler import CronParser

pytestmark = pytest.mark.unit


# =============================================================================
# parse_field
# =============================================================================
class TestParseField:
    def test_wildcard_is_full_range(self):
        assert CronParser.parse_field("*", 0, 5) == [0, 1, 2, 3, 4, 5]

    def test_single_value(self):
        assert CronParser.parse_field("5", 0, 59) == [5]

    def test_comma_list_is_sorted_and_deduped(self):
        assert CronParser.parse_field("5,1,3,3", 0, 59) == [1, 3, 5]

    def test_range(self):
        assert CronParser.parse_field("1-5", 0, 59) == [1, 2, 3, 4, 5]

    def test_wildcard_step(self):
        assert CronParser.parse_field("*/15", 0, 59) == [0, 15, 30, 45]

    def test_ranged_step(self):
        assert CronParser.parse_field("0-30/10", 0, 59) == [0, 10, 20, 30]

    def test_out_of_range_values_clamped(self):
        # 70 exceeds max (59) and is dropped.
        assert CronParser.parse_field("5,70", 0, 59) == [5]


# =============================================================================
# parse
# =============================================================================
class TestParse:
    def test_parses_five_fields(self):
        parsed = CronParser.parse("30 9 * * 1")
        assert parsed["minute"] == [30]
        assert parsed["hour"] == [9]
        assert parsed["day"] == list(range(1, 32))
        assert parsed["month"] == list(range(1, 13))
        assert parsed["weekday"] == [1]

    def test_invalid_field_count_raises(self):
        with pytest.raises(ValueError, match="Invalid cron expression"):
            CronParser.parse("* * *")


# =============================================================================
# get_next_run
# =============================================================================
class TestGetNextRun:
    def test_every_minute_returns_next_minute(self):
        after = datetime(2026, 6, 15, 10, 0, 30, tzinfo=timezone.utc)
        nxt = CronParser.get_next_run("* * * * *", after)
        assert nxt == datetime(2026, 6, 15, 10, 1, tzinfo=timezone.utc)

    def test_daily_time_same_day(self):
        after = datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc)
        nxt = CronParser.get_next_run("30 14 * * *", after)
        assert nxt == datetime(2026, 6, 15, 14, 30, tzinfo=timezone.utc)

    def test_daily_time_rolls_to_next_day(self):
        after = datetime(2026, 6, 15, 15, 0, tzinfo=timezone.utc)
        nxt = CronParser.get_next_run("30 14 * * *", after)
        assert nxt == datetime(2026, 6, 16, 14, 30, tzinfo=timezone.utc)

    def test_specific_day_of_month(self):
        after = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc)
        nxt = CronParser.get_next_run("0 0 1 * *", after)
        assert nxt == datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc)
