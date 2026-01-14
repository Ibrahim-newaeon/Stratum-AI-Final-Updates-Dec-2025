# =============================================================================
# Stratum AI - Model A/B Testing Framework
# =============================================================================
"""
Framework for A/B testing ML models to enable continuous improvement.

Features:
- Traffic splitting between champion and challenger models
- Statistical significance testing
- Automatic promotion based on performance
- Rollback capabilities
- Detailed experiment tracking
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import hashlib
import numpy as np
from scipy import stats

from app.core.logging import get_logger

logger = get_logger(__name__)


class ExperimentStatus(str, Enum):
    """Status of an A/B test experiment."""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    PROMOTED = "promoted"  # Challenger won and was promoted
    REJECTED = "rejected"  # Challenger lost


class ModelVariant(str, Enum):
    """Model variant in an experiment."""
    CHAMPION = "champion"
    CHALLENGER = "challenger"


@dataclass
class ExperimentMetrics:
    """Metrics collected during an experiment."""
    variant: ModelVariant
    predictions_count: int = 0
    total_error: float = 0.0
    total_squared_error: float = 0.0
    total_absolute_error: float = 0.0
    actuals_collected: int = 0

    # Computed metrics
    mae: float = 0.0
    rmse: float = 0.0
    mape: float = 0.0

    # Raw data for statistical tests
    errors: List[float] = field(default_factory=list)
    predictions: List[float] = field(default_factory=list)
    actuals: List[float] = field(default_factory=list)

    def add_prediction(self, predicted: float, actual: Optional[float] = None):
        """Record a prediction and optionally its actual value."""
        self.predictions_count += 1
        self.predictions.append(predicted)

        if actual is not None:
            self.actuals_collected += 1
            self.actuals.append(actual)

            error = predicted - actual
            abs_error = abs(error)

            self.errors.append(error)
            self.total_error += error
            self.total_squared_error += error ** 2
            self.total_absolute_error += abs_error

            # Update computed metrics
            self._update_metrics()

    def _update_metrics(self):
        """Update computed metrics."""
        if self.actuals_collected > 0:
            self.mae = self.total_absolute_error / self.actuals_collected
            self.rmse = np.sqrt(self.total_squared_error / self.actuals_collected)

            # MAPE with safeguard
            mape_sum = sum(
                abs(e / a) if a != 0 else 0
                for e, a in zip(self.errors, self.actuals)
            )
            self.mape = (mape_sum / self.actuals_collected) * 100 if self.actuals_collected > 0 else 0


@dataclass
class ModelExperiment:
    """Represents an A/B test experiment between two models."""
    experiment_id: str
    name: str
    model_name: str  # e.g., "roas_predictor"

    champion_version: str
    challenger_version: str

    # Configuration
    traffic_split: float = 0.1  # Percentage to challenger (0.0-1.0)
    min_samples: int = 1000
    max_duration_days: int = 14
    significance_level: float = 0.05

    # Metadata
    status: ExperimentStatus = ExperimentStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Metrics
    champion_metrics: ExperimentMetrics = field(
        default_factory=lambda: ExperimentMetrics(variant=ModelVariant.CHAMPION)
    )
    challenger_metrics: ExperimentMetrics = field(
        default_factory=lambda: ExperimentMetrics(variant=ModelVariant.CHALLENGER)
    )

    # Results
    winner: Optional[ModelVariant] = None
    p_value: Optional[float] = None
    improvement_percent: Optional[float] = None


class ModelABTestingService:
    """
    Service for managing model A/B tests.

    Usage:
        service = ModelABTestingService()

        # Create experiment
        exp = service.create_experiment(
            name="ROAS Model v2.1 Test",
            model_name="roas_predictor",
            champion_version="2.0.0",
            challenger_version="2.1.0",
            traffic_split=0.1,
        )

        # Start experiment
        service.start_experiment(exp.experiment_id)

        # Get model variant for a prediction
        variant = service.get_variant(exp.experiment_id, user_id="campaign_123")

        # Record prediction
        service.record_prediction(
            exp.experiment_id,
            variant,
            predicted=2.5,
            actual=2.3
        )

        # Check if experiment is conclusive
        result = service.evaluate_experiment(exp.experiment_id)
    """

    def __init__(self):
        self._experiments: Dict[str, ModelExperiment] = {}
        self._active_experiments: Dict[str, str] = {}  # model_name -> experiment_id

    def create_experiment(
        self,
        name: str,
        model_name: str,
        champion_version: str,
        challenger_version: str,
        traffic_split: float = 0.1,
        min_samples: int = 1000,
        max_duration_days: int = 14,
        significance_level: float = 0.05,
    ) -> ModelExperiment:
        """
        Create a new A/B test experiment.

        Args:
            name: Human-readable experiment name
            model_name: Name of the model being tested (e.g., "roas_predictor")
            champion_version: Current production model version
            challenger_version: New model version to test
            traffic_split: Percentage of traffic to send to challenger (0.0-1.0)
            min_samples: Minimum samples before drawing conclusions
            max_duration_days: Maximum experiment duration
            significance_level: P-value threshold for significance

        Returns:
            Created experiment
        """
        experiment_id = f"exp_{model_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        experiment = ModelExperiment(
            experiment_id=experiment_id,
            name=name,
            model_name=model_name,
            champion_version=champion_version,
            challenger_version=challenger_version,
            traffic_split=traffic_split,
            min_samples=min_samples,
            max_duration_days=max_duration_days,
            significance_level=significance_level,
        )

        self._experiments[experiment_id] = experiment
        logger.info(f"Created experiment: {experiment_id} ({name})")

        return experiment

    def start_experiment(self, experiment_id: str) -> bool:
        """Start an experiment."""
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            logger.error(f"Experiment not found: {experiment_id}")
            return False

        if experiment.status != ExperimentStatus.DRAFT:
            logger.error(f"Experiment {experiment_id} is not in DRAFT status")
            return False

        # Check for existing active experiment on same model
        if experiment.model_name in self._active_experiments:
            existing_id = self._active_experiments[experiment.model_name]
            logger.warning(f"Stopping existing experiment {existing_id} for {experiment.model_name}")
            self.stop_experiment(existing_id)

        experiment.status = ExperimentStatus.RUNNING
        experiment.started_at = datetime.now(timezone.utc)
        self._active_experiments[experiment.model_name] = experiment_id

        logger.info(f"Started experiment: {experiment_id}")
        return True

    def stop_experiment(self, experiment_id: str, status: ExperimentStatus = ExperimentStatus.PAUSED) -> bool:
        """Stop an experiment."""
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return False

        experiment.status = status
        experiment.completed_at = datetime.now(timezone.utc)

        if experiment.model_name in self._active_experiments:
            if self._active_experiments[experiment.model_name] == experiment_id:
                del self._active_experiments[experiment.model_name]

        logger.info(f"Stopped experiment: {experiment_id} with status {status}")
        return True

    def get_variant(self, experiment_id: str, entity_id: str) -> ModelVariant:
        """
        Get the model variant for a specific entity (user, campaign, etc.).

        Uses deterministic hashing for consistent assignment.

        Args:
            experiment_id: The experiment ID
            entity_id: Unique identifier for traffic splitting

        Returns:
            The assigned model variant
        """
        experiment = self._experiments.get(experiment_id)
        if not experiment or experiment.status != ExperimentStatus.RUNNING:
            return ModelVariant.CHAMPION

        # Deterministic hash-based assignment
        hash_input = f"{experiment_id}:{entity_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        bucket = (hash_value % 1000) / 1000.0

        if bucket < experiment.traffic_split:
            return ModelVariant.CHALLENGER
        return ModelVariant.CHAMPION

    def get_active_variant(self, model_name: str, entity_id: str) -> Tuple[ModelVariant, Optional[str]]:
        """
        Get the active variant for a model if there's a running experiment.

        Args:
            model_name: The model name (e.g., "roas_predictor")
            entity_id: Entity for traffic splitting

        Returns:
            Tuple of (variant, experiment_id or None)
        """
        experiment_id = self._active_experiments.get(model_name)
        if not experiment_id:
            return ModelVariant.CHAMPION, None

        variant = self.get_variant(experiment_id, entity_id)
        return variant, experiment_id

    def record_prediction(
        self,
        experiment_id: str,
        variant: ModelVariant,
        predicted: float,
        actual: Optional[float] = None,
    ):
        """
        Record a prediction and optionally its actual value.

        Args:
            experiment_id: The experiment ID
            variant: Which variant made the prediction
            predicted: The predicted value
            actual: The actual/observed value (if known)
        """
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return

        if variant == ModelVariant.CHAMPION:
            experiment.champion_metrics.add_prediction(predicted, actual)
        else:
            experiment.challenger_metrics.add_prediction(predicted, actual)

    def update_actual(
        self,
        experiment_id: str,
        variant: ModelVariant,
        prediction_index: int,
        actual: float,
    ):
        """
        Update the actual value for a previous prediction.

        Useful when actual values arrive later than predictions.
        """
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return

        metrics = (experiment.champion_metrics if variant == ModelVariant.CHAMPION
                   else experiment.challenger_metrics)

        if prediction_index < len(metrics.predictions):
            predicted = metrics.predictions[prediction_index]

            # Add to actuals tracking
            metrics.actuals_collected += 1
            metrics.actuals.append(actual)

            error = predicted - actual
            metrics.errors.append(error)
            metrics.total_error += error
            metrics.total_squared_error += error ** 2
            metrics.total_absolute_error += abs(error)
            metrics._update_metrics()

    def evaluate_experiment(self, experiment_id: str) -> Dict[str, Any]:
        """
        Evaluate an experiment for statistical significance.

        Uses a two-sample t-test to compare error distributions.

        Returns:
            Dict with evaluation results
        """
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return {"error": "Experiment not found"}

        champion = experiment.champion_metrics
        challenger = experiment.challenger_metrics

        result = {
            "experiment_id": experiment_id,
            "name": experiment.name,
            "status": experiment.status.value,
            "champion": {
                "version": experiment.champion_version,
                "predictions": champion.predictions_count,
                "actuals_collected": champion.actuals_collected,
                "mae": round(champion.mae, 4),
                "rmse": round(champion.rmse, 4),
                "mape": round(champion.mape, 2),
            },
            "challenger": {
                "version": experiment.challenger_version,
                "predictions": challenger.predictions_count,
                "actuals_collected": challenger.actuals_collected,
                "mae": round(challenger.mae, 4),
                "rmse": round(challenger.rmse, 4),
                "mape": round(challenger.mape, 2),
            },
        }

        # Check if we have enough data
        min_samples = experiment.min_samples
        total_actuals = champion.actuals_collected + challenger.actuals_collected

        result["total_samples"] = total_actuals
        result["min_samples_required"] = min_samples
        result["has_enough_samples"] = total_actuals >= min_samples

        # Check duration
        if experiment.started_at:
            duration = datetime.now(timezone.utc) - experiment.started_at
            result["duration_days"] = duration.days
            result["max_duration_days"] = experiment.max_duration_days
            result["exceeded_duration"] = duration.days >= experiment.max_duration_days

        # Statistical test if enough data
        if champion.actuals_collected >= 30 and challenger.actuals_collected >= 30:
            # Use absolute errors for comparison (lower is better)
            champion_errors = [abs(e) for e in champion.errors]
            challenger_errors = [abs(e) for e in challenger.errors]

            # Two-sample t-test
            t_stat, p_value = stats.ttest_ind(champion_errors, challenger_errors)

            result["statistical_test"] = {
                "test": "two_sample_t_test",
                "t_statistic": round(t_stat, 4),
                "p_value": round(p_value, 4),
                "significance_level": experiment.significance_level,
                "is_significant": p_value < experiment.significance_level,
            }

            experiment.p_value = p_value

            # Determine winner based on MAE (lower is better)
            if p_value < experiment.significance_level:
                if challenger.mae < champion.mae:
                    experiment.winner = ModelVariant.CHALLENGER
                    improvement = ((champion.mae - challenger.mae) / champion.mae) * 100
                    experiment.improvement_percent = improvement
                    result["recommendation"] = "PROMOTE_CHALLENGER"
                    result["improvement_percent"] = round(improvement, 2)
                else:
                    experiment.winner = ModelVariant.CHAMPION
                    result["recommendation"] = "KEEP_CHAMPION"
            else:
                result["recommendation"] = "CONTINUE_TESTING"
        else:
            result["recommendation"] = "INSUFFICIENT_DATA"

        return result

    def promote_challenger(self, experiment_id: str) -> bool:
        """
        Promote the challenger to production.

        This should trigger the actual model swap in your model registry.
        """
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return False

        if experiment.winner != ModelVariant.CHALLENGER:
            logger.warning(f"Cannot promote: challenger is not the winner for {experiment_id}")
            return False

        experiment.status = ExperimentStatus.PROMOTED
        experiment.completed_at = datetime.now(timezone.utc)

        # Remove from active experiments
        if experiment.model_name in self._active_experiments:
            del self._active_experiments[experiment.model_name]

        logger.info(f"Promoted challenger for experiment: {experiment_id}")
        logger.info(f"  Model: {experiment.model_name}")
        logger.info(f"  New version: {experiment.challenger_version}")
        logger.info(f"  Improvement: {experiment.improvement_percent:.2f}%")

        return True

    def reject_challenger(self, experiment_id: str) -> bool:
        """Reject the challenger and keep champion."""
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return False

        experiment.status = ExperimentStatus.REJECTED
        experiment.completed_at = datetime.now(timezone.utc)

        if experiment.model_name in self._active_experiments:
            del self._active_experiments[experiment.model_name]

        logger.info(f"Rejected challenger for experiment: {experiment_id}")
        return True

    def get_experiment(self, experiment_id: str) -> Optional[ModelExperiment]:
        """Get an experiment by ID."""
        return self._experiments.get(experiment_id)

    def list_experiments(
        self,
        model_name: Optional[str] = None,
        status: Optional[ExperimentStatus] = None,
    ) -> List[ModelExperiment]:
        """List experiments with optional filtering."""
        experiments = list(self._experiments.values())

        if model_name:
            experiments = [e for e in experiments if e.model_name == model_name]

        if status:
            experiments = [e for e in experiments if e.status == status]

        return sorted(experiments, key=lambda e: e.created_at, reverse=True)

    def get_experiment_summary(self) -> Dict[str, Any]:
        """Get summary of all experiments."""
        experiments = list(self._experiments.values())

        by_status = {}
        for status in ExperimentStatus:
            by_status[status.value] = len([e for e in experiments if e.status == status])

        active = [
            {
                "experiment_id": e.experiment_id,
                "name": e.name,
                "model_name": e.model_name,
                "champion": e.champion_version,
                "challenger": e.challenger_version,
                "traffic_split": e.traffic_split,
                "samples": e.champion_metrics.actuals_collected + e.challenger_metrics.actuals_collected,
            }
            for e in experiments
            if e.status == ExperimentStatus.RUNNING
        ]

        return {
            "total_experiments": len(experiments),
            "by_status": by_status,
            "active_experiments": active,
        }


# Singleton instance
ab_testing_service = ModelABTestingService()


# =============================================================================
# Convenience Functions
# =============================================================================

def get_model_variant(model_name: str, entity_id: str) -> Tuple[str, Optional[str]]:
    """
    Get which model version to use for a prediction.

    Args:
        model_name: The model name (e.g., "roas_predictor")
        entity_id: Unique identifier for consistent bucketing

    Returns:
        Tuple of (model_version_suffix, experiment_id or None)

    Usage:
        suffix, exp_id = get_model_variant("roas_predictor", campaign_id)
        if suffix == "challenger":
            model_path = f"models/roas_predictor_{challenger_version}.pkl"
        else:
            model_path = f"models/roas_predictor.pkl"
    """
    variant, experiment_id = ab_testing_service.get_active_variant(model_name, entity_id)

    if experiment_id and variant == ModelVariant.CHALLENGER:
        return "challenger", experiment_id
    return "champion", experiment_id


def record_model_prediction(
    model_name: str,
    entity_id: str,
    predicted: float,
    actual: Optional[float] = None,
):
    """
    Record a prediction for experiment tracking.

    Args:
        model_name: The model name
        entity_id: Entity identifier used for variant assignment
        predicted: The predicted value
        actual: The actual value (if known)
    """
    variant, experiment_id = ab_testing_service.get_active_variant(model_name, entity_id)

    if experiment_id:
        ab_testing_service.record_prediction(experiment_id, variant, predicted, actual)
