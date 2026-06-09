# =============================================================================
# Stratum AI - Natural-Language Filters unit tests
# =============================================================================
"""Unit tests for app.analytics.logic.nl_filters.

Pure NL query parsing, no I/O. Covers intent classification, platform / metric /
time-range extraction, suggestion generation, and the build_nl_filter entry
point.
"""

import pytest

from app.analytics.logic import nl_filters as nlf
from app.analytics.logic.nl_filters import NLFilterResponse, build_nl_filter

pytestmark = pytest.mark.unit


# =============================================================================
# Intent classification
# =============================================================================
class TestIntent:
    def test_compare_intent(self):
        intent, conf = nlf._classify_intent("compare google versus meta")
        assert intent == "compare"
        assert 0 < conf <= 95

    def test_summarize_intent(self):
        intent, _ = nlf._classify_intent("give me an overall summary aggregate")
        assert intent == "summarize"

    def test_analyze_intent(self):
        intent, _ = nlf._classify_intent("analyze the breakdown in detail")
        assert intent == "analyze"

    def test_empty_defaults_to_filter(self):
        intent, conf = nlf._classify_intent("")
        assert intent == "filter"
        assert conf == 50.0

    def test_confidence_capped_at_95(self):
        _, conf = nlf._classify_intent("compare versus vs against difference")
        assert conf <= 95


# =============================================================================
# Platform extraction
# =============================================================================
class TestPlatforms:
    def test_meta_alias(self):
        filters = nlf._extract_platforms("show facebook campaigns")
        assert filters
        assert filters[0].value == "meta"
        assert filters[0].filter_type == "platform"

    def test_google_alias(self):
        filters = nlf._extract_platforms("google adwords performance")
        assert filters[0].value == "google"

    def test_no_platform(self):
        # NB: short aliases (ig/li/tt/fb/x) match as substrings in the source,
        # so the query must avoid those letter sequences (e.g. "campaigns"
        # contains "ig" -> instagram). Documented as a latent bug.
        assert nlf._extract_platforms("show data last week") == []


# =============================================================================
# Metric threshold extraction
# =============================================================================
class TestMetrics:
    def test_roas_above(self):
        filters = nlf._extract_metrics("roas above 3x")
        assert filters[0].field == "roas"
        assert filters[0].operator == "gt"
        assert filters[0].value == "3"

    def test_spend_over_dollars(self):
        filters = nlf._extract_metrics("spend over $1000")
        assert filters[0].field == "spend"
        assert filters[0].operator == "gt"
        assert filters[0].value == "1000"

    def test_cpa_below(self):
        filters = nlf._extract_metrics("cpa below $15")
        assert filters[0].field == "cpa"
        assert filters[0].operator == "lt"
        assert filters[0].value == "15"

    def test_no_threshold(self):
        assert nlf._extract_metrics("show all campaigns") == []


# =============================================================================
# Time range extraction
# =============================================================================
class TestTimeRange:
    def test_last_30_days(self):
        filters = nlf._extract_time_range("revenue last 30 days")
        assert filters
        assert filters[0].filter_type == "date_range"
        assert filters[0].operator == "between"
        assert "," in filters[0].value  # "start,end"

    def test_this_week(self):
        filters = nlf._extract_time_range("spend this week")
        assert filters[0].display_label == "This Week"

    def test_no_time(self):
        assert nlf._extract_time_range("show meta campaigns") == []


# =============================================================================
# Suggestions
# =============================================================================
class TestSuggestions:
    def test_platform_specific_first(self):
        suggestions = nlf._generate_suggestions("", ["meta", "google"])
        assert len(suggestions) <= 6
        # platform-specific suggestions are prepended
        assert any("Meta" in s.query for s in suggestions)

    def test_no_platforms_still_returns_base(self):
        suggestions = nlf._generate_suggestions("", [])
        assert suggestions  # base suggestions present


# =============================================================================
# build_nl_filter (entry point)
# =============================================================================
class TestBuild:
    def test_empty_query(self):
        resp = build_nl_filter("", [{"platform": "meta"}])
        assert isinstance(resp, NLFilterResponse)
        assert resp.interpretation.intent == "filter"
        assert resp.interpretation.confidence == 0
        assert "Enter a natural language query" in resp.interpretation.explanation
        assert resp.suggestions

    def test_full_parse(self):
        campaigns = [
            {"platform": "meta", "roas": 5},
            {"platform": "meta", "roas": 2},
            {"platform": "google", "roas": 4},
        ]
        resp = build_nl_filter("show meta campaigns with roas above 3x", campaigns)
        assert resp.interpretation.intent == "filter"
        assert resp.interpretation.applied is True
        fields = {f.field for f in resp.interpretation.parsed_filters}
        assert "platform" in fields
        assert "roas" in fields
        roas_filter = next(
            f for f in resp.interpretation.parsed_filters if f.field == "roas"
        )
        assert roas_filter.operator == "gt"
        assert roas_filter.value == "3"

    def test_no_filters_matches_query_text(self):
        resp = build_nl_filter("tell me something interesting", [])
        # no structured filters extracted -> explanation references the raw query
        assert resp.interpretation.applied is False
        assert "interesting" in resp.interpretation.explanation
