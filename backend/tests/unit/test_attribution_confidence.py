# =============================================================================
# Stratum AI - Attribution Confidence unit tests
# =============================================================================
"""Unit tests for app.analytics.logic.attribution_confidence.

Pure attribution-confidence scoring, no I/O. Covers the confidence/data-quality
labels, per-channel confidence scoring, model-attribution simulation, model
agreement, and the build_attribution_confidence entry point (incl. recommended
model selection).
"""

import pytest

from app.analytics.logic import attribution_confidence as ac
from app.analytics.logic.attribution_confidence import (
    AttributionConfidenceResponse,
    build_attribution_confidence,
)

pytestmark = pytest.mark.unit


def _campaign(platform, spend, revenue, conversions):
    return {
        "platform": platform,
        "spend": spend,
        "revenue": revenue,
        "conversions": conversions,
    }


# =============================================================================
# Labels
# =============================================================================
class TestLabels:
    @pytest.mark.parametrize(
        "score,label",
        [(75, "high"), (50, "medium"), (25, "low"), (10, "insufficient")],
    )
    def test_confidence_label(self, score, label):
        assert ac._confidence_label(score) == label

    @pytest.mark.parametrize(
        "score,status",
        [(75, "good"), (50, "warning"), (20, "poor")],
    )
    def test_data_quality_status(self, score, status):
        assert ac._data_quality_status(score) == status


# =============================================================================
# Channel confidence
# =============================================================================
class TestChannelConfidence:
    def test_strong_channel_high_score(self):
        score = ac._calculate_channel_confidence(
            conversions=200, revenue=10000, total_revenue=10000, spend=1000
        )
        # 35 (vol) + 25 (materiality) + 20 (roas) + 18 (freshness) = 98
        assert score == pytest.approx(98.0, abs=0.1)

    def test_weak_channel_low_score(self):
        score = ac._calculate_channel_confidence(
            conversions=2, revenue=10, total_revenue=10000, spend=0
        )
        # 1 (vol) + 5 (materiality) + 3 (no spend) + 18 (freshness) = 27
        assert score == pytest.approx(27.0, abs=0.1)

    def test_score_capped_at_100(self):
        score = ac._calculate_channel_confidence(
            conversions=10000, revenue=1_000_000, total_revenue=1_000_000, spend=100000
        )
        assert score <= 100


# =============================================================================
# Model attribution simulation
# =============================================================================
class TestModelSimulation:
    def test_zero_channels_all_zero(self):
        out = ac._simulate_model_attribution(1000, 50, 0)
        assert out == {"last_touch": 0, "first_touch": 0, "linear": 0, "data_driven": 0}

    def test_relative_model_weights(self):
        out = ac._simulate_model_attribution(1000, 50, 4)
        assert out["last_touch"] == 1000.0  # full credit
        assert out["first_touch"] == pytest.approx(700.0)  # top-funnel discount
        assert out["data_driven"] == pytest.approx(900.0)  # ML-adjusted
        assert out["linear"] == pytest.approx(850.0)  # 1000 * 0.85


# =============================================================================
# Model agreement
# =============================================================================
class TestModelAgreement:
    def test_single_value_full_agreement(self):
        assert ac._calculate_model_agreement({"a": 50}) == 100.0

    def test_identical_values_full_agreement(self):
        assert ac._calculate_model_agreement({"a": 100, "b": 100}) == 100.0

    def test_spread_reduces_agreement(self):
        # avg 75, std 25, cv 0.333 -> ~66.7
        agreement = ac._calculate_model_agreement({"a": 100, "b": 50})
        assert agreement == pytest.approx(66.7, abs=0.3)
        assert agreement < 100


# =============================================================================
# build_attribution_confidence
# =============================================================================
class TestBuild:
    def test_empty_is_insufficient(self):
        resp = build_attribution_confidence([])
        assert isinstance(resp, AttributionConfidenceResponse)
        assert resp.overall_confidence == 0
        assert resp.confidence_label == "insufficient"
        assert "No campaign data" in resp.summary

    def test_full_recommends_data_driven(self):
        campaigns = [
            _campaign("meta", 1000, 10000, 250),
            _campaign("google", 2000, 8000, 220),
            _campaign("tiktok", 500, 5000, 210),
        ]
        resp = build_attribution_confidence(campaigns)
        # 680 conversions, 3 channels -> data_driven
        assert resp.recommended_model == "data_driven"
        assert len(resp.channels) == 3
        # channels sorted by revenue desc
        assert resp.channels[0].channel == "Meta"
        assert resp.model_comparisons
        assert resp.overall_confidence > 0
        assert resp.confidence_label in {"high", "medium", "low", "insufficient"}

    def test_two_channels_recommend_linear(self):
        campaigns = [
            _campaign("meta", 1000, 5000, 50),
            _campaign("google", 1000, 3000, 30),
        ]
        resp = build_attribution_confidence(campaigns)
        assert resp.recommended_model == "linear"

    def test_single_channel_recommend_last_touch(self):
        resp = build_attribution_confidence([_campaign("meta", 1000, 5000, 100)])
        assert resp.recommended_model == "last_touch"
