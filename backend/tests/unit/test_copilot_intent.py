# =============================================================================
# Stratum AI - Copilot Intent Classification Unit Tests
# =============================================================================
"""Unit tests for the pure NL helpers in
``app.services.agents.copilot_agent``: keyword-scored ``classify_intent``
and the static greeting / help / unknown response builders. The
LLM/DB-backed message pipeline is out of scope here.
"""

import pytest

from app.services.agents.copilot_agent import (
    CopilotIntent,
    classify_intent,
    generate_greeting_response,
    generate_help_response,
    generate_unknown_response,
)

pytestmark = pytest.mark.unit


# =============================================================================
# classify_intent
# =============================================================================
class TestClassifyIntent:
    @pytest.mark.parametrize(
        "message,intent",
        [
            ("Hello there!", CopilotIntent.GREETING),
            ("show my roas numbers", CopilotIntent.ROAS_ANALYSIS),
            ("show me any anomalies", CopilotIntent.ANOMALIES),
            ("how is signal health and emq", CopilotIntent.SIGNAL_HEALTH),
            ("how much did I spend on budget", CopilotIntent.SPEND_ANALYSIS),
            ("what do you recommend", CopilotIntent.RECOMMENDATIONS),
            ("show my campaigns", CopilotIntent.CAMPAIGNS),
            ("what can you do", CopilotIntent.HELP),
        ],
    )
    def test_keyword_classification(self, message, intent):
        assert classify_intent(message) == intent

    def test_empty_message_is_unknown(self):
        assert classify_intent("") == CopilotIntent.UNKNOWN

    def test_no_keyword_match_is_unknown(self):
        assert classify_intent("xyzzy plugh frobnicate") == CopilotIntent.UNKNOWN

    def test_highest_scoring_intent_wins(self):
        # Multiple ROAS keywords ("roas", "roi", "return") outscore a lone
        # spend keyword ("budget").
        msg = "compare roas roi and return vs budget"
        assert classify_intent(msg) == CopilotIntent.ROAS_ANALYSIS

    def test_case_insensitive(self):
        assert classify_intent("HELLO") == CopilotIntent.GREETING


# =============================================================================
# response builders
# =============================================================================
class TestResponseBuilders:
    def test_greeting_includes_name_and_intent(self):
        resp = generate_greeting_response("Sam")
        assert "Sam" in resp.message
        assert resp.intent == "greeting"
        assert resp.suggestions  # non-empty quick replies

    def test_greeting_defaults_without_name(self):
        resp = generate_greeting_response()
        assert resp.intent == "greeting"
        assert resp.message

    def test_help_response(self):
        resp = generate_help_response()
        assert resp.intent == "help"
        assert resp.suggestions

    def test_unknown_response_echoes_intent(self):
        resp = generate_unknown_response("garbled input")
        assert resp.intent == "unknown"
        assert resp.message
