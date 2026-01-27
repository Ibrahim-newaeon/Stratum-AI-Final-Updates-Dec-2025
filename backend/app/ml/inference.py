# =============================================================================
# Stratum AI - Model Inference Strategy
# =============================================================================
"""
Implements the ModelInferenceStrategy pattern for hybrid ML deployment.

Based on ML_PROVIDER environment variable:
- local: Load .pkl models and run inference with scikit-learn
- vertex: Send payloads to Google Vertex AI Endpoint
"""

import json
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

import numpy as np

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Exceptions
# =============================================================================
class ModelUnavailableError(Exception):
    """
    Raised when a ML model is unavailable for inference.

    This replaces silent mock fallbacks that corrupt downstream analytics.
    Callers should handle this error appropriately.
    """

    def __init__(
        self,
        model_name: str,
        message: str = None,
        retry_after: int = 300,
    ):
        self.model_name = model_name
        self.message = message or f"Model '{model_name}' is unavailable"
        self.retry_after = retry_after  # Suggested retry in seconds
        super().__init__(self.message)

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "error": "model_unavailable",
            "model_name": self.model_name,
            "message": self.message,
            "retry_after": self.retry_after,
        }


# =============================================================================
# Strategy Interface
# =============================================================================
class InferenceStrategy(ABC):
    """Abstract base class for ML inference strategies."""

    @abstractmethod
    async def predict(self, model_name: str, features: dict[str, Any]) -> dict[str, Any]:
        """
        Run inference with the specified model.

        Args:
            model_name: Name of the model to use
            features: Input features dictionary

        Returns:
            Prediction results with value and metadata
        """
        pass

    @abstractmethod
    def get_model_info(self) -> dict[str, Any]:
        """Get information about loaded models."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the inference service is healthy."""
        pass


# =============================================================================
# Local Inference Strategy (scikit-learn)
# =============================================================================
class LocalInferenceStrategy(InferenceStrategy):
    """
    Local inference using scikit-learn models loaded from disk.

    Models are loaded lazily and cached in memory.
    Supports .pkl files created with joblib.
    """

    def __init__(self, models_path: str = None):
        self.models_path = Path(models_path or settings.ml_models_path)
        self._models: dict[str, Any] = {}
        self._model_metadata: dict[str, dict] = {}

    def _load_model(self, model_name: str) -> Any:
        """Load a model from disk if not already cached."""
        if model_name in self._models:
            return self._models[model_name]

        model_file = self.models_path / f"{model_name}.pkl"

        if not model_file.exists():
            logger.warning("model_not_found", model_name=model_name, path=str(model_file))
            return None

        try:
            import joblib

            model = joblib.load(model_file)
            self._models[model_name] = model

            # Load metadata if exists
            metadata_file = self.models_path / f"{model_name}_metadata.json"
            if metadata_file.exists():
                with open(metadata_file) as f:
                    self._model_metadata[model_name] = json.load(f)
            else:
                self._model_metadata[model_name] = {
                    "version": "1.0.0",
                    "created_at": datetime.now(UTC).isoformat(),
                    "features": [],
                }

            logger.info("model_loaded", model_name=model_name)
            return model

        except Exception as e:
            logger.error("model_load_failed", model_name=model_name, error=str(e))
            return None

    async def predict(self, model_name: str, features: dict[str, Any]) -> dict[str, Any]:
        """Run inference with a local scikit-learn model."""
        model = self._load_model(model_name)

        if model is None:
            # Return mock prediction if model not available
            return self._mock_prediction(model_name, features)

        try:
            # Prepare features array
            metadata = self._model_metadata.get(model_name, {})
            feature_names = metadata.get("features", list(features.keys()))

            X = np.array([[features.get(f, 0) for f in feature_names]])

            # Run prediction
            prediction = model.predict(X)[0]

            # Get prediction probabilities if available
            confidence = None
            if hasattr(model, "predict_proba"):
                proba = model.predict_proba(X)[0]
                confidence = float(max(proba))

            # Get feature importances if available
            feature_importances = None
            if hasattr(model, "feature_importances_"):
                importances = model.feature_importances_
                feature_importances = {
                    name: float(imp) for name, imp in zip(feature_names, importances, strict=False)
                }

            return {
                "value": float(prediction),
                "confidence": confidence,
                "feature_importances": feature_importances,
                "model_version": metadata.get("version", "1.0.0"),
                "inference_strategy": "local",
            }

        except ModelUnavailableError:
            raise  # Re-raise model unavailable errors
        except Exception as e:
            logger.error("local_inference_failed", model_name=model_name, error=str(e))
            raise ModelUnavailableError(
                model_name=model_name,
                message=f"Inference failed for model '{model_name}': {e!s}",
                retry_after=60,
            )

    def _mock_prediction(self, model_name: str, features: dict[str, Any]) -> dict[str, Any]:
        """
        Handle unavailable model - raises error instead of returning fake data.

        Mock predictions were removed as they corrupt downstream analytics
        and mask model failures. Callers should handle ModelUnavailableError.
        """
        raise ModelUnavailableError(
            model_name=model_name,
            message=f"Model '{model_name}' is unavailable. No fallback data will be provided.",
            retry_after=300,  # Suggest retry in 5 minutes
        )

    def get_model_info(self) -> dict[str, Any]:
        """Get information about available models."""
        models_info = {}

        # List available model files
        if self.models_path.exists():
            for model_file in self.models_path.glob("*.pkl"):
                model_name = model_file.stem
                metadata = self._model_metadata.get(model_name, {})
                models_info[model_name] = {
                    "status": "loaded" if model_name in self._models else "available",
                    "version": metadata.get("version", "unknown"),
                    "path": str(model_file),
                }

        return {
            "strategy": "local",
            "models_path": str(self.models_path),
            "models": models_info,
        }

    def health_check(self) -> bool:
        """Check if local inference is available."""
        return self.models_path.exists()


# =============================================================================
# Vertex AI Inference Strategy
# =============================================================================
class VertexAIStrategy(InferenceStrategy):
    """
    Cloud inference using Google Vertex AI Endpoints.

    Requires:
    - GOOGLE_CLOUD_PROJECT
    - VERTEX_AI_ENDPOINT
    - GOOGLE_APPLICATION_CREDENTIALS
    """

    def __init__(self):
        self.project = settings.google_cloud_project
        self.endpoint = settings.vertex_ai_endpoint
        self._client = None

    def _get_client(self):
        """Get or create the Vertex AI prediction client."""
        if self._client is None:
            try:
                from google.cloud import aiplatform
                from google.cloud.aiplatform.gapic import PredictionServiceClient

                aiplatform.init(project=self.project)
                self._client = PredictionServiceClient()

                logger.info("vertex_ai_client_initialized", project=self.project)

            except Exception as e:
                logger.error("vertex_ai_init_failed", error=str(e))
                return None

        return self._client

    async def predict(self, model_name: str, features: dict[str, Any]) -> dict[str, Any]:
        """Run inference with Vertex AI endpoint."""
        client = self._get_client()

        if client is None:
            logger.warning("vertex_ai_unavailable_using_fallback")
            # Fall back to local strategy
            local = LocalInferenceStrategy()
            return await local.predict(model_name, features)

        try:
            from google.protobuf import json_format
            from google.protobuf.struct_pb2 import Value

            # Prepare the instance
            instance = json_format.ParseDict(features, Value())
            instances = [instance]

            # Build endpoint path
            endpoint_path = self.endpoint.format(
                project=self.project,
                location="us-central1",  # Default location
                endpoint_id=model_name,
            )

            # Make prediction request
            response = client.predict(endpoint=endpoint_path, instances=instances)

            # Parse response
            predictions = response.predictions
            if predictions:
                prediction = json_format.MessageToDict(predictions[0])

                return {
                    "value": prediction.get("value", prediction),
                    "confidence": prediction.get("confidence"),
                    "feature_importances": prediction.get("feature_importances"),
                    "model_version": response.deployed_model_id,
                    "inference_strategy": "vertex",
                }

            return {
                "value": 0,
                "confidence": None,
                "model_version": "unknown",
                "inference_strategy": "vertex",
                "error": "No predictions returned",
            }

        except Exception as e:
            logger.error("vertex_ai_prediction_failed", model_name=model_name, error=str(e))

            # Fall back to local
            local = LocalInferenceStrategy()
            return await local.predict(model_name, features)

    def get_model_info(self) -> dict[str, Any]:
        """Get information about Vertex AI configuration."""
        return {
            "strategy": "vertex",
            "project": self.project,
            "endpoint": self.endpoint,
            "status": "configured" if self.project and self.endpoint else "not_configured",
        }

    def health_check(self) -> bool:
        """Check if Vertex AI is accessible."""
        try:
            client = self._get_client()
            return client is not None
        except Exception:
            return False


# =============================================================================
# Model Registry (Strategy Selector)
# =============================================================================
class ModelRegistry:
    """
    Registry that selects and manages ML inference strategies.

    Based on ML_PROVIDER environment variable:
    - 'local': Use LocalInferenceStrategy
    - 'vertex': Use VertexAIStrategy
    """

    _instance: Optional["ModelRegistry"] = None

    def __new__(cls):
        """Singleton pattern for registry."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._strategy: Optional[InferenceStrategy] = None
        self._initialize_strategy()

    def _initialize_strategy(self):
        """Initialize the appropriate inference strategy."""
        provider = settings.ml_provider

        if provider == "vertex":
            logger.info("initializing_vertex_ai_strategy")
            self._strategy = VertexAIStrategy()
        else:
            logger.info("initializing_local_strategy")
            self._strategy = LocalInferenceStrategy()

    @property
    def strategy(self) -> InferenceStrategy:
        """Get the current inference strategy."""
        return self._strategy

    async def predict(self, model_name: str, features: dict[str, Any]) -> dict[str, Any]:
        """
        Run prediction using the configured strategy.

        Args:
            model_name: Name of the model
            features: Input features

        Returns:
            Prediction results
        """
        return await self._strategy.predict(model_name, features)

    def get_model_info(self) -> dict[str, Any]:
        """Get information about the current ML setup."""
        return {
            "provider": settings.ml_provider,
            **self._strategy.get_model_info(),
        }

    # Platform-specific model support
    SUPPORTED_PLATFORMS = ["meta", "google", "tiktok", "snapchat", "linkedin"]

    async def predict_roas(
        self,
        features: dict[str, Any],
        platform: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Run ROAS prediction with platform-specific model support.

        Tries platform-specific model first, falls back to ensemble if unavailable.

        Args:
            features: Input features for prediction
            platform: Ad platform (meta, google, tiktok, snapchat, linkedin)

        Returns:
            Prediction results with model metadata
        """
        platform = (platform or features.get("platform", "")).lower()

        # Try platform-specific model first
        if platform in self.SUPPORTED_PLATFORMS:
            platform_model = f"roas_predictor_{platform}"
            try:
                result = await self._strategy.predict(platform_model, features)
                if not result.get("error"):
                    result["model_type"] = "platform_specific"
                    result["platform"] = platform
                    logger.info("roas_prediction_platform_model", platform=platform)
                    return result
            except ModelUnavailableError:
                logger.info("platform_model_unavailable_using_ensemble", platform=platform)
            except Exception as e:
                logger.warning(
                    "platform_model_error_using_ensemble", platform=platform, error=str(e)
                )

        # Fall back to ensemble model
        try:
            result = await self._strategy.predict("roas_predictor", features)
            result["model_type"] = "ensemble"
            result["platform"] = platform or "unknown"
            result["fallback_used"] = platform in self.SUPPORTED_PLATFORMS
            return result
        except ModelUnavailableError:
            raise
        except Exception as e:
            raise ModelUnavailableError(
                model_name="roas_predictor",
                message=f"ROAS prediction failed: {e!s}",
                retry_after=60,
            )

    async def predict_with_platform(
        self,
        base_model: str,
        features: dict[str, Any],
        platform: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Generic platform-aware prediction with fallback.

        Args:
            base_model: Base model name (e.g., "roas_predictor", "conversion_predictor")
            features: Input features
            platform: Platform for model selection

        Returns:
            Prediction with platform metadata
        """
        platform = (platform or features.get("platform", "")).lower()

        # Try platform-specific model
        if platform in self.SUPPORTED_PLATFORMS:
            platform_model = f"{base_model}_{platform}"
            try:
                result = await self._strategy.predict(platform_model, features)
                if not result.get("error"):
                    result["model_type"] = "platform_specific"
                    result["platform"] = platform
                    return result
            except (ModelUnavailableError, Exception):
                pass  # Fall through to ensemble

        # Use base model
        result = await self._strategy.predict(base_model, features)
        result["model_type"] = "ensemble"
        result["platform"] = platform or "unknown"
        return result

    def get_available_platform_models(self) -> dict[str, list[str]]:
        """
        Get list of available platform-specific models.

        Returns:
            Dict mapping base models to available platform variants
        """
        info = self._strategy.get_model_info()
        models = info.get("models", {})

        platform_models = {}
        for model_name in models:
            for platform in self.SUPPORTED_PLATFORMS:
                suffix = f"_{platform}"
                if model_name.endswith(suffix):
                    base = model_name[: -len(suffix)]
                    if base not in platform_models:
                        platform_models[base] = []
                    platform_models[base].append(platform)

        return platform_models

    def health_check(self) -> bool:
        """Check if ML inference is healthy."""
        return self._strategy.health_check()
