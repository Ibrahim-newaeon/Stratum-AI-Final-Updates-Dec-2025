# =============================================================================
# Stratum AI - Customer journey summary
# =============================================================================
"""``CustomerJourneyResponse`` promises nine fields. The Cypher behind it
returns three -- ``profile_id``, ``lifecycle`` and a ``journey`` list -- so the
endpoint filled the other six from its own defaults and answered
``total_events: 0, total_revenue: 0.0`` for a profile that had both. Confirmed
against live AGE: a profile with one purchase and 5000 cents of revenue was
reported as having neither.

Everything the response needs is already in the ``journey`` list; nothing here
requires another query. ``stage_transitions`` is the exception -- the graph
records no stage history, so it stays empty rather than being invented.
"""

import pytest

from app.services.knowledge_graph.service import summarise_journey

pytestmark = pytest.mark.unit


def _raw(journey, lifecycle="customer", profile_id="p-1"):
    return {"profile_id": profile_id, "lifecycle": lifecycle, "journey": journey}


class TestSummariseJourney:
    def test_counts_only_real_events(self):
        """A profile with no events at all still collects one null entry.

        ``OPTIONAL MATCH`` on revenue means ``collect`` yields a row whose keys
        are all null rather than an empty list, so counting list length would
        report one event where there are none.
        """
        summary = summarise_journey(_raw([{"event_type": None, "timestamp": None, "revenue": None}]))

        assert summary["total_events"] == 0

    def test_totals_revenue_in_cents_across_events(self):
        summary = summarise_journey(
            _raw(
                [
                    {"event_type": "purchase", "timestamp": "2026-08-01T00:00:00", "revenue": 5000},
                    {"event_type": "purchase", "timestamp": "2026-08-03T00:00:00", "revenue": 1000},
                ]
            )
        )

        assert summary["total_events"] == 2
        assert summary["total_revenue"] == 6000.0

    def test_an_event_without_revenue_counts_but_adds_nothing(self):
        summary = summarise_journey(
            _raw(
                [
                    {"event_type": "page_view", "timestamp": "2026-08-01T00:00:00", "revenue": None},
                    {"event_type": "purchase", "timestamp": "2026-08-02T00:00:00", "revenue": 2500},
                ]
            )
        )

        assert summary["total_events"] == 2
        assert summary["total_revenue"] == 2500.0

    def test_first_and_last_seen_come_from_the_timestamp_range(self):
        summary = summarise_journey(
            _raw(
                [
                    {"event_type": "b", "timestamp": "2026-08-05T00:00:00", "revenue": None},
                    {"event_type": "a", "timestamp": "2026-08-01T00:00:00", "revenue": None},
                ]
            )
        )

        assert summary["first_seen_at"] == "2026-08-01T00:00:00"
        assert summary["last_seen_at"] == "2026-08-05T00:00:00"
        assert summary["journey_duration_days"] == 4.0

    def test_lifecycle_is_carried_across_under_the_name_the_response_uses(self):
        summary = summarise_journey(_raw([], lifecycle="at_risk"))

        assert summary["lifecycle_stage"] == "at_risk"

    def test_an_empty_journey_reports_zeros_not_nulls(self):
        summary = summarise_journey(_raw([]))

        assert summary["total_events"] == 0
        assert summary["total_revenue"] == 0.0
        assert summary["first_seen_at"] is None
        assert summary["journey_duration_days"] is None

    def test_stage_transitions_stay_empty_because_the_graph_has_no_history(self):
        summary = summarise_journey(
            _raw([{"event_type": "purchase", "timestamp": "2026-08-01T00:00:00", "revenue": 100}])
        )

        assert summary["stage_transitions"] == []

    def test_an_unparseable_timestamp_does_not_sink_the_whole_summary(self):
        """Timestamps arrive as whatever was written to the graph."""
        summary = summarise_journey(
            _raw([{"event_type": "purchase", "timestamp": "not-a-date", "revenue": 100}])
        )

        assert summary["total_events"] == 1
        assert summary["total_revenue"] == 100.0
        assert summary["journey_duration_days"] is None
