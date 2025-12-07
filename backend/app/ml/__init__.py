# =============================================================================
# Stratum AI - ML Module
# =============================================================================
"""
Machine Learning module implementing the Hybrid ML Strategy.

Module A: Intelligence Engine
- ModelInferenceStrategy pattern (local vs vertex)
- ROAS Forecaster
- Conversion Predictor
- What-If Simulator
"""

from app.ml.simulator import WhatIfSimulator
from app.ml.forecaster import ROASForecaster
from app.ml.conversion_predictor import ConversionPredictor
from app.ml.inference import ModelRegistry, InferenceStrategy

__all__ = [
    "WhatIfSimulator",
    "ROASForecaster",
    "ConversionPredictor",
    "ModelRegistry",
    "InferenceStrategy",
]
