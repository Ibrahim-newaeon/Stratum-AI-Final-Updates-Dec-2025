# =============================================================================
# Stratum AI - Recommendations Engine unit tests
# =============================================================================
"""Unit tests for app.analytics.logic.recommend.

Pure orchestration over the signal-health / anomaly / scaling / budget logic,
no I/O. Focuses on the trust-gated entry contract: a degraded signal blocks
automation; a healthy signal returns the full recommendation envelope.
"""

import pytest

from app.analytics.logic.recommend import (
    RecommendationsEngine,
    generate_recommendations,
)

pytestmark = pytest.mark.unit


class TestSignalHealthGate:
    def test_degraded_signal_blocks_automation(self):
        # very low EMQ + high event loss + API down -> suspend automation
        result = generate_recommendations(
            entities_today=[],
            baselines={},
            emq_score=0.2,
            event_loss_pct=50.0,
            api_health=False,
        )
        assert result["automation_blocked"] is True
        assert result["alerts"]  # emq_degraded alert recorded
        assert any(a.get("type") == "emq_degraded" for a in result["alerts"])

    def test_healthy_signal_returns_full_envelope(self):
        result = generate_recommendations(
            entities_today=[],
            baselines={},
            emq_score=95.0,
            event_loss_pct=1.0,
            api_health=True,
        )
        # not blocked -> standard envelope keys present
        assert result.get("automation_blocked") is not True
        for key in ("recommendations", "actions", "alerts", "insights"):
            assert key in result


class TestEngine:
    def test_engine_is_reusable(self):
        engine = RecommendationsEngine()
        r1 = engine.generate_recommendations([], {}, emq_score=90.0, api_health=True)
        r2 = engine.generate_recommendations([], {}, emq_score=90.0, api_health=True)
        assert "generated_at" in r1 and "generated_at" in r2
