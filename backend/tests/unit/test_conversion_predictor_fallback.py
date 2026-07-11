# =============================================================================
# Stratum AI - ConversionPredictor heuristic fallback tests (ML-001)
# =============================================================================
"""
ModelRegistry.predict raises ModelUnavailableError when the model file is
missing/corrupt (e.g. a fresh deploy before training). ConversionPredictor
must fall back to its deterministic heuristic instead of letting the error
500 the request.
"""

from unittest.mock import AsyncMock

import pytest

from app.ml.conversion_predictor import ConversionPredictor
from app.ml.inference import ModelUnavailableError

FEATURES = {
    "impressions": 100000,
    "clicks": 2000,
    "spend": 1500.0,
    "ctr": 2.0,
    "platform": "meta",
}


@pytest.mark.asyncio
async def test_falls_back_to_heuristic_on_model_unavailable():
    predictor = ConversionPredictor()
    predictor.registry.predict = AsyncMock(
        side_effect=ModelUnavailableError(model_name="conversion_predictor")
    )

    result = await predictor.predict(FEATURES)

    # Heuristic path is used — no exception propagates.
    assert result["model_version"] == "heuristic-1.0.0"
    assert result["value"] > 0
    assert 0.3 <= result["confidence"] <= 0.75


@pytest.mark.asyncio
async def test_uses_model_prediction_when_available():
    predictor = ConversionPredictor()
    predictor.registry.predict = AsyncMock(
        return_value={
            "value": 55.0,
            "confidence": 0.91,
            "feature_importances": {"clicks_log": 0.6, "ctr": 0.4},
            "model_version": "2.0.0",
            "inference_strategy": "local",
        }
    )

    result = await predictor.predict(FEATURES)

    assert result["model_version"] == "2.0.0"
    assert result["value"] == 55.0
    assert result["confidence"] == 0.91


@pytest.mark.asyncio
async def test_mock_strategy_tag_also_falls_back():
    predictor = ConversionPredictor()
    predictor.registry.predict = AsyncMock(
        return_value={"value": 0, "inference_strategy": "remote-mock"}
    )

    result = await predictor.predict(FEATURES)

    assert result["model_version"] == "heuristic-1.0.0"
