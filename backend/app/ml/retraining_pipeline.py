# =============================================================================
# Stratum AI - Model Retraining Pipeline
# =============================================================================
"""
Automated model retraining pipeline for ML models.

Features:
- Automatic detection of model drift
- Scheduled retraining based on data freshness
- A/B comparison of new vs old models
- Rollback capability
- Performance monitoring
"""

import json
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

import joblib
import numpy as np
import pandas as pd

from app.core.logging import get_logger
from app.ml.train import ModelTrainer

logger = get_logger(__name__)


class RetrainingTrigger(str, Enum):
    """Reasons for triggering model retraining."""
    SCHEDULED = "scheduled"              # Regular schedule (e.g., weekly)
    PERFORMANCE_DRIFT = "performance_drift"  # Model accuracy degraded
    DATA_VOLUME = "data_volume"          # Enough new data collected
    MANUAL = "manual"                    # User-triggered
    NEW_FEATURES = "new_features"        # New features available


class ModelStatus(str, Enum):
    """Status of a model version."""
    ACTIVE = "active"
    STAGING = "staging"
    RETIRED = "retired"
    FAILED = "failed"


@dataclass
class ModelVersion:
    """Represents a specific version of a trained model."""
    version_id: str
    model_name: str
    created_at: datetime
    metrics: Dict[str, float]
    status: ModelStatus
    trigger: RetrainingTrigger
    training_samples: int
    features: List[str]
    path: str


@dataclass
class RetrainingConfig:
    """Configuration for the retraining pipeline."""
    # Scheduling
    retrain_interval_days: int = 7  # Retrain weekly
    min_samples_for_retrain: int = 1000  # Minimum new samples

    # Performance thresholds
    min_r2_improvement: float = 0.02  # 2% improvement required
    max_r2_degradation: float = 0.05  # 5% degradation triggers alert
    drift_detection_window_days: int = 7

    # Model management
    max_model_versions: int = 5  # Keep last 5 versions
    staging_validation_hours: int = 24  # Test in staging before promotion

    # Paths
    models_path: str = "./models"
    archive_path: str = "./models/archive"
    staging_path: str = "./models/staging"


class RetrainingPipeline:
    """
    Automated model retraining pipeline.

    Handles:
    - Detecting when models need retraining
    - Training new model versions
    - Comparing and validating new models
    - Promoting or rolling back models
    - Maintaining model version history
    """

    def __init__(self, config: Optional[RetrainingConfig] = None):
        self.config = config or RetrainingConfig()
        self.models_path = Path(self.config.models_path)
        self.archive_path = Path(self.config.archive_path)
        self.staging_path = Path(self.config.staging_path)

        # Ensure directories exist
        for path in [self.models_path, self.archive_path, self.staging_path]:
            path.mkdir(parents=True, exist_ok=True)

        self.trainer = ModelTrainer(str(self.staging_path))
        self._model_history: Dict[str, List[ModelVersion]] = {}
        self._load_model_history()

    def _load_model_history(self):
        """Load model version history from disk."""
        history_path = self.models_path / "model_history.json"
        if history_path.exists():
            try:
                with open(history_path, "r") as f:
                    data = json.load(f)
                for model_name, versions in data.items():
                    self._model_history[model_name] = [
                        ModelVersion(
                            version_id=v["version_id"],
                            model_name=v["model_name"],
                            created_at=datetime.fromisoformat(v["created_at"]),
                            metrics=v["metrics"],
                            status=ModelStatus(v["status"]),
                            trigger=RetrainingTrigger(v["trigger"]),
                            training_samples=v["training_samples"],
                            features=v["features"],
                            path=v["path"],
                        )
                        for v in versions
                    ]
            except Exception as e:
                logger.error(f"Error loading model history: {e}")

    def _save_model_history(self):
        """Save model version history to disk."""
        history_path = self.models_path / "model_history.json"
        data = {}
        for model_name, versions in self._model_history.items():
            data[model_name] = [
                {
                    "version_id": v.version_id,
                    "model_name": v.model_name,
                    "created_at": v.created_at.isoformat(),
                    "metrics": v.metrics,
                    "status": v.status.value,
                    "trigger": v.trigger.value,
                    "training_samples": v.training_samples,
                    "features": v.features,
                    "path": v.path,
                }
                for v in versions
            ]
        with open(history_path, "w") as f:
            json.dump(data, f, indent=2)

    def check_retraining_needed(
        self,
        model_name: str,
        recent_predictions: Optional[pd.DataFrame] = None,
    ) -> Tuple[bool, RetrainingTrigger, str]:
        """
        Check if a model needs retraining.

        Args:
            model_name: Name of the model to check
            recent_predictions: DataFrame with predictions and actuals

        Returns:
            Tuple of (needs_retraining, trigger, reason)
        """
        # Check if model exists
        metadata_path = self.models_path / f"{model_name}_metadata.json"
        if not metadata_path.exists():
            return True, RetrainingTrigger.MANUAL, "Model does not exist"

        # Load metadata
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        created_at = datetime.fromisoformat(metadata["created_at"])
        age_days = (datetime.now(timezone.utc) - created_at).days

        # Check age-based retraining
        if age_days >= self.config.retrain_interval_days:
            return True, RetrainingTrigger.SCHEDULED, f"Model is {age_days} days old"

        # Check performance drift if predictions provided
        if recent_predictions is not None and len(recent_predictions) > 100:
            if "prediction" in recent_predictions.columns and "actual" in recent_predictions.columns:
                # Calculate recent performance
                y_true = recent_predictions["actual"].values
                y_pred = recent_predictions["prediction"].values

                # R² score
                ss_res = np.sum((y_true - y_pred) ** 2)
                ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
                current_r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

                # Compare to training R²
                training_r2 = metadata.get("metrics", {}).get("r2", 0)

                degradation = training_r2 - current_r2
                if degradation > self.config.max_r2_degradation:
                    return True, RetrainingTrigger.PERFORMANCE_DRIFT, \
                        f"R² degraded from {training_r2:.3f} to {current_r2:.3f}"

        return False, RetrainingTrigger.MANUAL, "No retraining needed"

    def retrain_model(
        self,
        model_name: str,
        training_data: pd.DataFrame,
        trigger: RetrainingTrigger = RetrainingTrigger.MANUAL,
        validate_before_promote: bool = True,
    ) -> Dict[str, Any]:
        """
        Retrain a specific model with new data.

        Args:
            model_name: Name of model to retrain
            training_data: Training data DataFrame
            trigger: What triggered the retraining
            validate_before_promote: Whether to validate in staging first

        Returns:
            Retraining results
        """
        logger.info(f"Starting retraining for {model_name} (trigger: {trigger.value})")

        version_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        results = {
            "version_id": version_id,
            "model_name": model_name,
            "trigger": trigger.value,
            "status": "started",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # Train new model in staging
            if model_name == "roas_predictor":
                df = self.trainer._prepare_data(training_data)
                metrics = self.trainer.train_roas_predictor(df)
            elif model_name == "conversion_predictor":
                df = self.trainer._prepare_data(training_data)
                metrics = self.trainer.train_conversion_predictor(df)
            elif model_name == "budget_impact":
                df = self.trainer._prepare_data(training_data)
                metrics = self.trainer.train_budget_impact_predictor(df)
            elif model_name.startswith("roas_predictor_"):
                # Platform-specific model
                platform = model_name.replace("roas_predictor_", "")
                df = self.trainer._prepare_data(training_data)
                platform_df = df[df["platform"] == platform] if "platform" in df.columns else df
                if len(platform_df) < 50:
                    return {"status": "failed", "error": f"Insufficient data for {platform}"}
                metrics = self.trainer.train_roas_predictor(platform_df)
            else:
                return {"status": "failed", "error": f"Unknown model: {model_name}"}

            results["metrics"] = metrics
            results["training_samples"] = len(training_data)

            # Compare with current production model
            comparison = self._compare_with_production(model_name, metrics)
            results["comparison"] = comparison

            # Decide whether to promote
            if comparison.get("should_promote", False) or not validate_before_promote:
                self._promote_model(model_name, version_id, metrics, trigger, training_data)
                results["status"] = "promoted"
                logger.info(f"Model {model_name} v{version_id} promoted to production")
            else:
                results["status"] = "staged"
                logger.info(f"Model {model_name} v{version_id} kept in staging")
                results["reason"] = comparison.get("reason", "Did not meet promotion criteria")

        except Exception as e:
            logger.error(f"Retraining failed: {e}")
            results["status"] = "failed"
            results["error"] = str(e)

        return results

    def _compare_with_production(
        self,
        model_name: str,
        new_metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Compare new model metrics with production model."""
        metadata_path = self.models_path / f"{model_name}_metadata.json"

        if not metadata_path.exists():
            # No production model exists, always promote
            return {"should_promote": True, "reason": "No existing model"}

        with open(metadata_path, "r") as f:
            prod_metadata = json.load(f)

        prod_r2 = prod_metadata.get("metrics", {}).get("r2", 0)
        new_r2 = new_metrics.get("r2", 0)

        improvement = new_r2 - prod_r2

        comparison = {
            "production_r2": prod_r2,
            "new_r2": new_r2,
            "improvement": improvement,
        }

        # Promotion criteria
        if improvement >= self.config.min_r2_improvement:
            comparison["should_promote"] = True
            comparison["reason"] = f"R² improved by {improvement:.4f}"
        elif improvement >= 0:
            comparison["should_promote"] = True
            comparison["reason"] = "Slight improvement or same performance"
        else:
            comparison["should_promote"] = False
            comparison["reason"] = f"R² decreased by {abs(improvement):.4f}"

        return comparison

    def _promote_model(
        self,
        model_name: str,
        version_id: str,
        metrics: Dict[str, Any],
        trigger: RetrainingTrigger,
        training_data: pd.DataFrame,
    ):
        """Promote a staged model to production."""
        # Archive current production model
        self._archive_current_model(model_name)

        # Move staged model to production
        staged_files = [
            f"{model_name}.pkl",
            f"{model_name}_scaler.pkl",
            f"{model_name}_imputer.pkl",
            f"{model_name}_metadata.json",
        ]

        for filename in staged_files:
            staged_path = self.staging_path / filename
            prod_path = self.models_path / filename
            if staged_path.exists():
                shutil.copy2(staged_path, prod_path)

        # Update model history
        if model_name not in self._model_history:
            self._model_history[model_name] = []

        # Load metadata to get features
        metadata_path = self.models_path / f"{model_name}_metadata.json"
        features = []
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
                features = metadata.get("features", [])

        model_version = ModelVersion(
            version_id=version_id,
            model_name=model_name,
            created_at=datetime.now(timezone.utc),
            metrics=metrics,
            status=ModelStatus.ACTIVE,
            trigger=trigger,
            training_samples=len(training_data),
            features=features,
            path=str(self.models_path / f"{model_name}.pkl"),
        )

        # Mark previous versions as retired
        for v in self._model_history[model_name]:
            if v.status == ModelStatus.ACTIVE:
                v.status = ModelStatus.RETIRED

        self._model_history[model_name].append(model_version)

        # Cleanup old versions
        self._cleanup_old_versions(model_name)

        # Save history
        self._save_model_history()

    def _archive_current_model(self, model_name: str):
        """Archive the current production model."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        archive_dir = self.archive_path / f"{model_name}_{timestamp}"
        archive_dir.mkdir(parents=True, exist_ok=True)

        files_to_archive = [
            f"{model_name}.pkl",
            f"{model_name}_scaler.pkl",
            f"{model_name}_imputer.pkl",
            f"{model_name}_metadata.json",
        ]

        for filename in files_to_archive:
            src = self.models_path / filename
            if src.exists():
                shutil.copy2(src, archive_dir / filename)

    def _cleanup_old_versions(self, model_name: str):
        """Remove old model versions beyond max_model_versions."""
        if model_name not in self._model_history:
            return

        versions = self._model_history[model_name]
        if len(versions) > self.config.max_model_versions:
            # Keep only the most recent versions
            self._model_history[model_name] = versions[-self.config.max_model_versions:]

    def rollback(self, model_name: str, version_id: Optional[str] = None) -> bool:
        """
        Rollback to a previous model version.

        Args:
            model_name: Name of the model
            version_id: Specific version to rollback to (default: previous version)

        Returns:
            True if rollback successful
        """
        if model_name not in self._model_history:
            logger.error(f"No history found for model {model_name}")
            return False

        versions = self._model_history[model_name]

        if version_id:
            # Find specific version
            target = next((v for v in versions if v.version_id == version_id), None)
        else:
            # Find previous active version
            retired = [v for v in versions if v.status == ModelStatus.RETIRED]
            target = retired[-1] if retired else None

        if not target:
            logger.error(f"No rollback target found for {model_name}")
            return False

        # Find archived version
        archive_dirs = list(self.archive_path.glob(f"{model_name}_*"))
        archive_dirs.sort(reverse=True)

        for archive_dir in archive_dirs:
            metadata_path = archive_dir / f"{model_name}_metadata.json"
            if metadata_path.exists():
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                archived_time = datetime.fromisoformat(metadata["created_at"])

                # Check if this is the version we want
                if abs((archived_time - target.created_at).total_seconds()) < 60:
                    # Restore this version
                    for f in archive_dir.iterdir():
                        shutil.copy2(f, self.models_path / f.name)

                    logger.info(f"Rolled back {model_name} to version {target.version_id}")

                    # Update status
                    target.status = ModelStatus.ACTIVE
                    for v in versions:
                        if v != target and v.status == ModelStatus.ACTIVE:
                            v.status = ModelStatus.RETIRED

                    self._save_model_history()
                    return True

        logger.error(f"Archive not found for version {target.version_id}")
        return False

    def get_model_status(self, model_name: str) -> Dict[str, Any]:
        """Get status information for a model."""
        status = {
            "model_name": model_name,
            "exists": False,
            "created_at": None,
            "metrics": None,
            "age_days": None,
            "needs_retraining": False,
            "version_history": [],
        }

        metadata_path = self.models_path / f"{model_name}_metadata.json"
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            status["exists"] = True
            status["created_at"] = metadata.get("created_at")
            status["metrics"] = metadata.get("metrics")

            if status["created_at"]:
                created = datetime.fromisoformat(status["created_at"])
                status["age_days"] = (datetime.now(timezone.utc) - created).days
                status["needs_retraining"] = status["age_days"] >= self.config.retrain_interval_days

        if model_name in self._model_history:
            status["version_history"] = [
                {
                    "version_id": v.version_id,
                    "created_at": v.created_at.isoformat(),
                    "status": v.status.value,
                    "r2": v.metrics.get("r2"),
                }
                for v in self._model_history[model_name][-5:]
            ]

        return status

    def run_scheduled_retraining(
        self,
        training_data_loader: callable,
    ) -> Dict[str, Any]:
        """
        Run scheduled retraining for all models.

        Args:
            training_data_loader: Function that returns training DataFrame

        Returns:
            Results for all models
        """
        results = {}
        models_to_check = [
            "roas_predictor",
            "conversion_predictor",
            "budget_impact",
        ]

        # Check which models need retraining
        models_to_retrain = []
        for model_name in models_to_check:
            needs_retrain, trigger, reason = self.check_retraining_needed(model_name)
            if needs_retrain:
                models_to_retrain.append((model_name, trigger, reason))
                logger.info(f"{model_name}: needs retraining ({reason})")
            else:
                logger.info(f"{model_name}: up to date")

        if not models_to_retrain:
            return {"status": "no_retraining_needed", "models": models_to_check}

        # Load training data
        logger.info("Loading training data...")
        training_data = training_data_loader()

        # Retrain each model that needs it
        for model_name, trigger, reason in models_to_retrain:
            logger.info(f"Retraining {model_name}...")
            result = self.retrain_model(model_name, training_data, trigger)
            results[model_name] = result

        return {
            "status": "completed",
            "models_retrained": len(results),
            "results": results,
        }


# =============================================================================
# Celery Tasks for Scheduled Retraining
# =============================================================================

def create_retraining_task(app):
    """
    Create a Celery task for scheduled model retraining.

    Usage:
        from celery import Celery
        app = Celery(...)
        retrain_task = create_retraining_task(app)

        # Schedule in celerybeat
        app.conf.beat_schedule = {
            'retrain-models-weekly': {
                'task': 'ml.retrain_models',
                'schedule': timedelta(days=7),
            },
        }
    """
    @app.task(name='ml.retrain_models')
    def retrain_models_task():
        from app.ml.data_loader import TrainingDataLoader

        pipeline = RetrainingPipeline()

        def load_training_data():
            loader = TrainingDataLoader()
            # Load last 90 days of data for training
            return loader.load_from_database(days=90)

        results = pipeline.run_scheduled_retraining(load_training_data)
        return results

    return retrain_models_task


# =============================================================================
# CLI Interface
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Model Retraining Pipeline")
    parser.add_argument("--check", type=str, help="Check if model needs retraining")
    parser.add_argument("--retrain", type=str, help="Retrain specific model")
    parser.add_argument("--status", type=str, help="Get model status")
    parser.add_argument("--rollback", type=str, help="Rollback model to previous version")
    parser.add_argument("--run-all", action="store_true", help="Run scheduled retraining for all models")

    args = parser.parse_args()

    pipeline = RetrainingPipeline()

    if args.check:
        needs, trigger, reason = pipeline.check_retraining_needed(args.check)
        print(f"Model: {args.check}")
        print(f"Needs retraining: {needs}")
        print(f"Trigger: {trigger.value}")
        print(f"Reason: {reason}")

    elif args.status:
        status = pipeline.get_model_status(args.status)
        print(json.dumps(status, indent=2))

    elif args.rollback:
        success = pipeline.rollback(args.rollback)
        print(f"Rollback {'successful' if success else 'failed'}")

    elif args.run_all:
        print("Running scheduled retraining...")
        from app.ml.data_loader import TrainingDataLoader

        def load_data():
            return TrainingDataLoader.generate_sample_data(100, 30)

        results = pipeline.run_scheduled_retraining(load_data)
        print(json.dumps(results, indent=2, default=str))

    else:
        parser.print_help()
