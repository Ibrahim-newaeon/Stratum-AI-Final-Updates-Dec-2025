# =============================================================================
# Stratum AI - Attribution Model Training Service
# =============================================================================
"""
Service for training, storing, and managing data-driven attribution models.

Supports:
- Markov Chain models
- Shapley Value models
- Model comparison and selection
- Scheduled retraining
"""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.services.attribution.markov_attribution import (
    MarkovAttributionService,
    MarkovChainModel,
)
from app.services.attribution.shapley_attribution import (
    ShapleyAttributionService,
    ShapleyValueModel,
)

logger = get_logger(__name__)


class DataDrivenModelType:
    """Available data-driven model types."""

    MARKOV_CHAIN = "markov_chain"
    SHAPLEY_VALUE = "shapley_value"


class ModelTrainingService:
    """
    Service for training and managing data-driven attribution models.
    """

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    async def train_model(
        self,
        model_type: str,
        start_date: datetime,
        end_date: datetime,
        channel_type: str = "platform",
        include_non_converting: bool = True,
        min_journeys: int = 100,
        model_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Train a data-driven attribution model.

        Args:
            model_type: 'markov_chain' or 'shapley_value'
            start_date: Start of training period
            end_date: End of training period
            channel_type: 'platform' or 'campaign'
            include_non_converting: Include non-converting journeys
            min_journeys: Minimum journeys required
            model_name: Optional name for the model

        Returns:
            Training results with model data
        """
        if model_type == DataDrivenModelType.MARKOV_CHAIN:
            service = MarkovAttributionService(self.db, self.tenant_id)
        elif model_type == DataDrivenModelType.SHAPLEY_VALUE:
            service = ShapleyAttributionService(self.db, self.tenant_id)
        else:
            return {
                "success": False,
                "error": f"Unknown model type: {model_type}",
            }

        result = await service.train_model(
            start_date=start_date,
            end_date=end_date,
            channel_type=channel_type,
            include_non_converting=include_non_converting,
            min_journeys=min_journeys,
        )

        if result.get("success"):
            result["model_name"] = model_name or f"{model_type}_{channel_type}_{end_date.date()}"

        return result

    async def train_all_models(
        self,
        start_date: datetime,
        end_date: datetime,
        channel_type: str = "platform",
        include_non_converting: bool = True,
        min_journeys: int = 100,
    ) -> dict[str, Any]:
        """
        Train all available model types and compare results.

        Returns comparison of attribution weights across models.
        """
        models = {}
        weights_comparison = {}

        # Train Markov Chain
        markov_result = await self.train_model(
            model_type=DataDrivenModelType.MARKOV_CHAIN,
            start_date=start_date,
            end_date=end_date,
            channel_type=channel_type,
            include_non_converting=include_non_converting,
            min_journeys=min_journeys,
        )

        if markov_result.get("success"):
            models["markov_chain"] = markov_result
            weights_comparison["markov_chain"] = markov_result.get("attribution_weights", {})

        # Train Shapley Value
        shapley_result = await self.train_model(
            model_type=DataDrivenModelType.SHAPLEY_VALUE,
            start_date=start_date,
            end_date=end_date,
            channel_type=channel_type,
            include_non_converting=include_non_converting,
            min_journeys=min_journeys,
        )

        if shapley_result.get("success"):
            models["shapley_value"] = shapley_result
            weights_comparison["shapley_value"] = shapley_result.get("attribution_weights", {})

        # Calculate consensus weights (average across models)
        consensus_weights = self._calculate_consensus_weights(weights_comparison)

        return {
            "success": len(models) > 0,
            "training_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "channel_type": channel_type,
            "models": models,
            "weights_comparison": weights_comparison,
            "consensus_weights": consensus_weights,
        }

    def _calculate_consensus_weights(
        self,
        weights_by_model: dict[str, dict[str, float]],
    ) -> dict[str, float]:
        """
        Calculate consensus weights by averaging across models.
        """
        if not weights_by_model:
            return {}

        # Get all channels
        all_channels = set()
        for weights in weights_by_model.values():
            all_channels.update(weights.keys())

        # Average weights
        consensus = {}
        for channel in all_channels:
            values = [weights.get(channel, 0.0) for weights in weights_by_model.values()]
            consensus[channel] = sum(values) / len(values) if values else 0.0

        # Normalize
        total = sum(consensus.values())
        if total > 0:
            consensus = {k: v / total for k, v in consensus.items()}

        return consensus

    async def compare_with_rule_based(
        self,
        data_driven_weights: dict[str, float],
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, Any]:
        """
        Compare data-driven weights with rule-based attribution models.
        """
        from app.models.crm import AttributionModel
        from app.services.attribution.attribution_service import (
            AttributionService,
        )

        attribution_service = AttributionService(self.db, self.tenant_id)

        # Get rule-based attribution summaries
        rule_based = {}

        for model in [
            AttributionModel.FIRST_TOUCH,
            AttributionModel.LAST_TOUCH,
            AttributionModel.LINEAR,
            AttributionModel.POSITION_BASED,
            AttributionModel.TIME_DECAY,
        ]:
            summary = await attribution_service.get_attribution_summary(
                start_date=start_date,
                end_date=end_date,
                model=model,
                group_by="platform",
            )

            # Convert to weights
            total_revenue = sum(item["attributed_revenue"] for item in summary)
            if total_revenue > 0:
                rule_based[model.value] = {
                    item["key"]: item["attributed_revenue"] / total_revenue for item in summary
                }
            else:
                rule_based[model.value] = {}

        # Calculate correlation with data-driven
        correlations = {}
        for model_name, weights in rule_based.items():
            correlation = self._calculate_weight_correlation(data_driven_weights, weights)
            correlations[model_name] = correlation

        # Find closest rule-based model
        closest_model = max(correlations.items(), key=lambda x: x[1]) if correlations else None

        return {
            "data_driven_weights": data_driven_weights,
            "rule_based_weights": rule_based,
            "correlations": correlations,
            "closest_rule_based_model": closest_model[0] if closest_model else None,
            "closest_correlation": closest_model[1] if closest_model else None,
        }

    def _calculate_weight_correlation(
        self,
        weights1: dict[str, float],
        weights2: dict[str, float],
    ) -> float:
        """
        Calculate correlation between two weight distributions.

        Uses cosine similarity for comparison.
        """
        all_channels = set(weights1.keys()) | set(weights2.keys())

        if not all_channels:
            return 0.0

        # Build vectors
        vec1 = [weights1.get(c, 0.0) for c in all_channels]
        vec2 = [weights2.get(c, 0.0) for c in all_channels]

        # Cosine similarity
        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))
        norm1 = sum(a**2 for a in vec1) ** 0.5
        norm2 = sum(b**2 for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    async def get_recommended_model(
        self,
        start_date: datetime,
        end_date: datetime,
        channel_type: str = "platform",
    ) -> dict[str, Any]:
        """
        Get model recommendation based on data characteristics.

        Considers:
        - Journey length distribution
        - Channel diversity
        - Conversion rate
        - Data volume
        """
        from app.models.crm import CRMContact, CRMDeal

        # Get journey statistics
        deal_result = await self.db.execute(
            select(CRMDeal).where(
                and_(
                    CRMDeal.tenant_id == self.tenant_id,
                    CRMDeal.is_won == True,
                    CRMDeal.won_at >= start_date,
                    CRMDeal.won_at <= end_date,
                    CRMDeal.contact_id.isnot(None),
                )
            )
        )
        deals = deal_result.scalars().all()

        total_deals = len(deals)

        if total_deals < 50:
            return {
                "recommendation": "rule_based",
                "recommended_model": "last_touch",
                "reason": "Insufficient conversion data for data-driven models",
                "deals_analyzed": total_deals,
                "minimum_required": 50,
            }

        # Analyze journey characteristics
        journey_lengths = []
        channel_counts = []

        for deal in deals[:500]:  # Sample for efficiency
            contact_result = await self.db.execute(
                select(CRMContact).where(CRMContact.id == deal.contact_id)
            )
            contact = contact_result.scalar_one_or_none()
            if contact:
                journey_lengths.append(contact.touch_count or 1)

        avg_journey_length = sum(journey_lengths) / len(journey_lengths) if journey_lengths else 1

        # Recommendations based on data characteristics
        if avg_journey_length < 2:
            return {
                "recommendation": "rule_based",
                "recommended_model": "last_touch",
                "reason": "Short journeys (avg < 2 touches) - simple attribution sufficient",
                "deals_analyzed": total_deals,
                "avg_journey_length": round(avg_journey_length, 2),
            }

        if avg_journey_length >= 2 and avg_journey_length < 4:
            return {
                "recommendation": "data_driven",
                "recommended_model": "shapley_value",
                "reason": "Medium-length journeys - Shapley values provide fair credit distribution",
                "deals_analyzed": total_deals,
                "avg_journey_length": round(avg_journey_length, 2),
            }

        if avg_journey_length >= 4:
            return {
                "recommendation": "data_driven",
                "recommended_model": "markov_chain",
                "reason": "Long journeys - Markov chains capture sequential patterns",
                "deals_analyzed": total_deals,
                "avg_journey_length": round(avg_journey_length, 2),
            }

        return {
            "recommendation": "data_driven",
            "recommended_model": "consensus",
            "reason": "Use consensus of multiple models for best accuracy",
            "deals_analyzed": total_deals,
            "avg_journey_length": round(avg_journey_length, 2),
        }

    async def validate_model(
        self,
        model_data: dict[str, Any],
        model_type: str,
        validation_start: datetime,
        validation_end: datetime,
    ) -> dict[str, Any]:
        """
        Validate a trained model on holdout data.

        Compares predicted conversion probabilities with actual outcomes.
        """
        from app.models.crm import CRMDeal

        # Get validation deals
        deal_result = await self.db.execute(
            select(CRMDeal).where(
                and_(
                    CRMDeal.tenant_id == self.tenant_id,
                    CRMDeal.is_won == True,
                    CRMDeal.won_at >= validation_start,
                    CRMDeal.won_at <= validation_end,
                    CRMDeal.contact_id.isnot(None),
                )
            )
        )
        deals = deal_result.scalars().all()

        if len(deals) < 10:
            return {
                "success": False,
                "error": "Insufficient validation data",
                "deals_count": len(deals),
            }

        # Load model
        if model_type == DataDrivenModelType.MARKOV_CHAIN:
            model = MarkovChainModel.from_dict(model_data)
            service = MarkovAttributionService(self.db, self.tenant_id)
        else:
            model = ShapleyValueModel.from_dict(model_data)
            service = ShapleyAttributionService(self.db, self.tenant_id)

        # Calculate accuracy metrics
        correct_attributions = 0
        total_attributions = 0

        for deal in deals[:100]:  # Sample for efficiency
            result = await service.attribute_with_model(model_data, deal.id)
            if result.get("success"):
                total_attributions += 1
                # Consider attribution "correct" if it matches the actual converting channel
                if deal.attributed_platform:
                    top_channel = max(
                        result.get("breakdown", [{}]),
                        key=lambda x: x.get("weight", 0),
                        default={},
                    ).get("channel")
                    if top_channel == deal.attributed_platform:
                        correct_attributions += 1

        accuracy = correct_attributions / total_attributions if total_attributions > 0 else 0

        return {
            "success": True,
            "model_type": model_type,
            "validation_period": {
                "start_date": validation_start.isoformat(),
                "end_date": validation_end.isoformat(),
            },
            "deals_validated": total_attributions,
            "accuracy": round(accuracy, 4),
            "metrics": {
                "correct_attributions": correct_attributions,
                "total_attributions": total_attributions,
            },
        }
