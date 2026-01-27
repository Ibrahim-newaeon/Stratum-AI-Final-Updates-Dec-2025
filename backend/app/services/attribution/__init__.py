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
    AttributionCalculator,
    AttributionService,
)
from app.services.attribution.journey_service import (
    JourneyAggregator,
    JourneyService,
)
from app.services.attribution.markov_attribution import (
    MarkovAttributionService,
    MarkovChainModel,
)
from app.services.attribution.model_training import (
    DataDrivenModelType,
    ModelTrainingService,
)
from app.services.attribution.shapley_attribution import (
    ShapleyAttributionService,
    ShapleyValueModel,
)

__all__ = [
    # Rule-based attribution
    "AttributionService",
    "AttributionCalculator",
    # Journey analysis
    "JourneyService",
    "JourneyAggregator",
    # Data-driven attribution
    "MarkovChainModel",
    "MarkovAttributionService",
    "ShapleyValueModel",
    "ShapleyAttributionService",
    "DataDrivenModelType",
    "ModelTrainingService",
]
