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
- Training Pipeline
- Data Loader
"""

from app.ml.conversion_predictor import ConversionPredictor
from app.ml.data_loader import TrainingDataLoader
from app.ml.forecaster import ROASForecaster
from app.ml.inference import InferenceStrategy, ModelRegistry
from app.ml.roas_optimizer import LivePredictionEngine, ROASOptimizer
from app.ml.simulator import WhatIfSimulator
from app.ml.train import ModelTrainer, train_from_csv, train_from_sample_data

__all__ = [
    "WhatIfSimulator",
    "ROASForecaster",
    "ConversionPredictor",
    "ModelRegistry",
    "InferenceStrategy",
    "TrainingDataLoader",
    "ModelTrainer",
    "train_from_csv",
    "train_from_sample_data",
    "ROASOptimizer",
    "LivePredictionEngine",
]
