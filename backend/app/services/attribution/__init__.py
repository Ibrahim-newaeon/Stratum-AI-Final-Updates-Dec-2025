# =============================================================================
# Stratum AI - Attribution Services Package
# =============================================================================
"""
Multi-Touch Attribution (MTA) services for marketing analytics.

Includes:
- Rule-based attribution (first touch, last touch, linear, etc.)
- Data-driven attribution (Markov Chain, Shapley Values)
- Journey analysis and visualization
"""

from app.services.attribution.attribution_service import (
    AttributionService,
    AttributionCalculator,
)
from app.services.attribution.journey_service import (
    JourneyService,
    JourneyAggregator,
)
from app.services.attribution.markov_attribution import (
    MarkovChainModel,
    MarkovAttributionService,
)
from app.services.attribution.shapley_attribution import (
    ShapleyValueModel,
    ShapleyAttributionService,
)
from app.services.attribution.model_training import (
    DataDrivenModelType,
    ModelTrainingService,
)

__all__ = [
    "AttributionCalculator",
    # Rule-based attribution
    "AttributionService",
    "DataDrivenModelType",
    "JourneyAggregator",
    # Journey analysis
    "JourneyService",
    "MarkovAttributionService",
    # Data-driven attribution
    "MarkovChainModel",
    "ModelTrainingService",
    "ShapleyAttributionService",
    "ShapleyValueModel",
]
