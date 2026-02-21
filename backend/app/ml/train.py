# =============================================================================
# Stratum AI - ML Training Pipeline (Enhanced)
# =============================================================================
"""
Training pipeline for ML models.
Trains ROAS predictor, conversion predictor, and saves as .pkl files.

Enhanced with:
- Creative features (type, format, engagement indicators)
- Audience features (targeting type, size, demographics)
- Campaign features (objective, bid strategy, timing)
- Historical features (trends, volatility)
- Platform-specific models for better accuracy
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
import structlog
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.linear_model import Ridge, ElasticNet
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import cross_val_score, train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.impute import SimpleImputer

from app.core.logging import get_logger

logger = structlog.get_logger(__name__)


# =============================================================================
# Feature Engineering Constants
# =============================================================================

CREATIVE_TYPES = ["image", "video", "carousel", "collection", "stories", "reels", "unknown"]
AUDIENCE_TYPES = ["broad", "lookalike", "custom", "interest", "retargeting", "unknown"]
OBJECTIVES = ["conversions", "traffic", "awareness", "engagement", "leads", "sales", "app_installs", "unknown"]
BID_STRATEGIES = ["lowest_cost", "cost_cap", "bid_cap", "target_roas", "manual", "unknown"]
PLATFORMS = ["meta", "google", "tiktok", "snapchat", "linkedin"]


class ModelTrainer:
    """
    Trains and saves ML models for the Stratum AI platform.

    Models:
    - roas_predictor: Predicts ROAS based on campaign features
    - conversion_predictor: Predicts conversions based on spend/impressions
    - budget_impact: Predicts revenue change from budget changes
    """

    def __init__(self, models_path: str = None):
        self.models_path = Path(models_path or os.getenv("ML_MODELS_PATH", "./models"))
        self.models_path.mkdir(parents=True, exist_ok=True)

        self.scalers: Dict[str, StandardScaler] = {}
        self.feature_names: Dict[str, List[str]] = {}

    def train_all(self, df: pd.DataFrame, include_platform_models: bool = True) -> Dict[str, Any]:
        """
        Train all models from a dataset.

        Args:
            df: DataFrame with columns:
                - spend (or spend_cents)
                - impressions
                - clicks
                - conversions
                - revenue (or revenue_cents)
                - platform (optional)
                - creative_type (optional)
                - audience_type (optional)
                - objective (optional)
                - bid_strategy (optional)
                - campaign_id (optional)
                - date (optional)
            include_platform_models: Whether to train platform-specific models

        Returns:
            Training results summary
        """
        results = {}

        # Prepare data with enhanced feature engineering
        logger.info("preparing_data")
        df = self._prepare_data(df)
        logger.info("data_prepared", rows=len(df), columns=len(df.columns))

        # Train ROAS predictor (enhanced with creative/audience features)
        logger.info("training_roas_predictor")
        results["roas_predictor"] = self.train_roas_predictor(df)

        # Train platform-specific models if enabled
        if include_platform_models and "platform" in df.columns:
            logger.info("training_platform_specific_models")
            platform_results = self.train_platform_specific_models(df)
            results["platform_models"] = platform_results

        # Train conversion predictor
        logger.info("training_conversion_predictor")
        results["conversion_predictor"] = self.train_conversion_predictor(df)

        # Train budget impact predictor
        logger.info("training_budget_impact_predictor")
        results["budget_impact"] = self.train_budget_impact_predictor(df)

        return results

    def _prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare and clean data for training with enhanced feature engineering."""
        df = df.copy()

        # Convert cents to dollars if needed
        if "spend_cents" in df.columns and "spend" not in df.columns:
            df["spend"] = df["spend_cents"] / 100
        if "revenue_cents" in df.columns and "revenue" not in df.columns:
            df["revenue"] = df["revenue_cents"] / 100

        # =====================================================================
        # Core Performance Metrics
        # =====================================================================
        df["ctr"] = np.where(
            df["impressions"] > 0,
            df["clicks"] / df["impressions"] * 100,
            0
        )
        df["cvr"] = np.where(
            df["clicks"] > 0,
            df["conversions"] / df["clicks"] * 100,
            0
        )
        df["roas"] = np.where(
            df["spend"] > 0,
            df["revenue"] / df["spend"],
            0
        )
        df["cpc"] = np.where(
            df["clicks"] > 0,
            df["spend"] / df["clicks"],
            0
        )
        df["cpm"] = np.where(
            df["impressions"] > 0,
            df["spend"] / df["impressions"] * 1000,
            0
        )
        df["cpa"] = np.where(
            df["conversions"] > 0,
            df["spend"] / df["conversions"],
            0
        )
        df["revenue_per_conversion"] = np.where(
            df["conversions"] > 0,
            df["revenue"] / df["conversions"],
            0
        )

        # Log transforms for skewed features
        df["log_spend"] = np.log1p(df["spend"])
        df["log_impressions"] = np.log1p(df["impressions"])
        df["log_clicks"] = np.log1p(df["clicks"])
        df["log_conversions"] = np.log1p(df["conversions"])
        df["log_revenue"] = np.log1p(df["revenue"])

        # =====================================================================
        # Creative Features
        # =====================================================================
        if "creative_type" in df.columns:
            df["creative_type"] = df["creative_type"].fillna("unknown").str.lower()
            for ct in CREATIVE_TYPES:
                df[f"creative_{ct}"] = (df["creative_type"] == ct).astype(int)
        else:
            # Default creative features
            for ct in CREATIVE_TYPES:
                df[f"creative_{ct}"] = 0
            df["creative_unknown"] = 1

        # Video-specific features
        if "video_length_seconds" in df.columns:
            df["video_length_seconds"] = df["video_length_seconds"].fillna(0)
            df["is_short_video"] = (df["video_length_seconds"] > 0) & (df["video_length_seconds"] <= 15)
            df["is_medium_video"] = (df["video_length_seconds"] > 15) & (df["video_length_seconds"] <= 60)
            df["is_long_video"] = df["video_length_seconds"] > 60
        else:
            df["video_length_seconds"] = 0
            df["is_short_video"] = 0
            df["is_medium_video"] = 0
            df["is_long_video"] = 0

        # Creative engagement indicators
        if "has_cta" in df.columns:
            df["has_cta"] = df["has_cta"].fillna(0).astype(int)
        else:
            df["has_cta"] = 0

        if "headline_length" in df.columns:
            df["headline_length"] = df["headline_length"].fillna(0)
        else:
            df["headline_length"] = 0

        # =====================================================================
        # Audience Features
        # =====================================================================
        if "audience_type" in df.columns:
            df["audience_type"] = df["audience_type"].fillna("unknown").str.lower()
            for at in AUDIENCE_TYPES:
                df[f"audience_{at}"] = (df["audience_type"] == at).astype(int)
        else:
            for at in AUDIENCE_TYPES:
                df[f"audience_{at}"] = 0
            df["audience_unknown"] = 1

        # Audience size (log transform)
        if "audience_size" in df.columns:
            df["log_audience_size"] = np.log1p(df["audience_size"].fillna(0))
        else:
            df["log_audience_size"] = 0

        # Lookalike percentage (quality indicator)
        if "lookalike_percent" in df.columns:
            df["lookalike_percent"] = df["lookalike_percent"].fillna(0)
        else:
            df["lookalike_percent"] = 0

        # =====================================================================
        # Campaign Features
        # =====================================================================
        if "objective" in df.columns:
            df["objective"] = df["objective"].fillna("unknown").str.lower()
            for obj in OBJECTIVES:
                df[f"objective_{obj}"] = (df["objective"] == obj).astype(int)
        else:
            for obj in OBJECTIVES:
                df[f"objective_{obj}"] = 0
            df["objective_unknown"] = 1

        if "bid_strategy" in df.columns:
            df["bid_strategy"] = df["bid_strategy"].fillna("unknown").str.lower()
            for bs in BID_STRATEGIES:
                df[f"bid_{bs}"] = (df["bid_strategy"] == bs).astype(int)
        else:
            for bs in BID_STRATEGIES:
                df[f"bid_{bs}"] = 0
            df["bid_unknown"] = 1

        # Campaign age (days since launch)
        if "campaign_start_date" in df.columns and "date" in df.columns:
            df["campaign_start_date"] = pd.to_datetime(df["campaign_start_date"], errors="coerce")
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df["campaign_age_days"] = (df["date"] - df["campaign_start_date"]).dt.days.fillna(0)
            df["log_campaign_age"] = np.log1p(df["campaign_age_days"].clip(lower=0))
        else:
            df["campaign_age_days"] = 0
            df["log_campaign_age"] = 0

        # =====================================================================
        # Temporal Features
        # =====================================================================
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df["day_of_week"] = df["date"].dt.dayofweek.fillna(0)
            df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
            df["month"] = df["date"].dt.month.fillna(1)
            df["quarter"] = df["date"].dt.quarter.fillna(1)
        else:
            df["day_of_week"] = 0
            df["is_weekend"] = 0
            df["month"] = 1
            df["quarter"] = 1

        # =====================================================================
        # Historical Performance Features (rolling averages)
        # =====================================================================
        if "campaign_id" in df.columns and "date" in df.columns:
            df = df.sort_values(["campaign_id", "date"])

            # 7-day rolling averages
            for col in ["roas", "ctr", "cvr", "cpc"]:
                if col in df.columns:
                    df[f"{col}_7d_avg"] = df.groupby("campaign_id")[col].transform(
                        lambda x: x.rolling(7, min_periods=1).mean()
                    )
                    df[f"{col}_7d_std"] = df.groupby("campaign_id")[col].transform(
                        lambda x: x.rolling(7, min_periods=1).std()
                    ).fillna(0)

            # Trend direction (positive if improving)
            df["roas_trend"] = df.groupby("campaign_id")["roas"].transform(
                lambda x: x.diff().fillna(0)
            )
            df["is_improving"] = (df["roas_trend"] > 0).astype(int)
        else:
            # Default rolling features
            for col in ["roas", "ctr", "cvr", "cpc"]:
                df[f"{col}_7d_avg"] = df.get(col, 0)
                df[f"{col}_7d_std"] = 0
            df["roas_trend"] = 0
            df["is_improving"] = 0

        # =====================================================================
        # Platform Encoding
        # =====================================================================
        if "platform" in df.columns:
            df["platform"] = df["platform"].fillna("unknown").str.lower()
            for platform in PLATFORMS:
                df[f"platform_{platform}"] = (df["platform"] == platform).astype(int)
        else:
            for platform in PLATFORMS:
                df[f"platform_{platform}"] = 0

        # =====================================================================
        # Interaction Features
        # =====================================================================
        # Creative x Platform interactions
        if "creative_video" in df.columns and "platform_tiktok" in df.columns:
            df["video_on_tiktok"] = df["creative_video"] * df["platform_tiktok"]
        else:
            df["video_on_tiktok"] = 0

        # Audience x Objective interactions
        if "audience_retargeting" in df.columns and "objective_conversions" in df.columns:
            df["retargeting_conversions"] = df["audience_retargeting"] * df["objective_conversions"]
        else:
            df["retargeting_conversions"] = 0

        # Efficiency interaction
        df["ctr_cvr_product"] = df["ctr"] * df["cvr"]

        # =====================================================================
        # Clean up
        # =====================================================================
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.dropna(subset=["spend", "impressions", "clicks", "revenue"])

        return df

    def train_roas_predictor(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Train enhanced ROAS prediction model.

        Features include:
        - Core metrics: spend, impressions, clicks, ctr, cpm, cvr
        - Creative: type, video length, CTA presence
        - Audience: type, size, lookalike quality
        - Campaign: objective, bid strategy, age
        - Temporal: day of week, seasonality
        - Historical: 7-day averages, trends
        - Platform: one-hot encoded
        - Interactions: creative x platform, audience x objective

        Target: roas
        """
        # =====================================================================
        # Build comprehensive feature list
        # =====================================================================
        feature_cols = []

        # Core performance metrics
        core_metrics = [
            "log_spend", "log_impressions", "log_clicks", "log_conversions",
            "ctr", "cvr", "cpm", "cpc", "cpa", "revenue_per_conversion",
            "ctr_cvr_product"
        ]
        feature_cols.extend([c for c in core_metrics if c in df.columns])

        # Creative features
        creative_cols = [c for c in df.columns if c.startswith("creative_")]
        feature_cols.extend(creative_cols)
        video_features = ["video_length_seconds", "is_short_video", "is_medium_video", "is_long_video"]
        feature_cols.extend([c for c in video_features if c in df.columns])
        if "has_cta" in df.columns:
            feature_cols.append("has_cta")
        if "headline_length" in df.columns:
            feature_cols.append("headline_length")

        # Audience features
        audience_cols = [c for c in df.columns if c.startswith("audience_")]
        feature_cols.extend(audience_cols)
        if "log_audience_size" in df.columns:
            feature_cols.append("log_audience_size")
        if "lookalike_percent" in df.columns:
            feature_cols.append("lookalike_percent")

        # Campaign features
        objective_cols = [c for c in df.columns if c.startswith("objective_")]
        feature_cols.extend(objective_cols)
        bid_cols = [c for c in df.columns if c.startswith("bid_")]
        feature_cols.extend(bid_cols)
        if "log_campaign_age" in df.columns:
            feature_cols.append("log_campaign_age")

        # Temporal features
        temporal_features = ["day_of_week", "is_weekend", "month", "quarter"]
        feature_cols.extend([c for c in temporal_features if c in df.columns])

        # Historical features
        historical_features = [
            "roas_7d_avg", "roas_7d_std", "ctr_7d_avg", "ctr_7d_std",
            "cvr_7d_avg", "cvr_7d_std", "roas_trend", "is_improving"
        ]
        feature_cols.extend([c for c in historical_features if c in df.columns])

        # Platform features
        platform_cols = [c for c in df.columns if c.startswith("platform_")]
        feature_cols.extend(platform_cols)

        # Interaction features
        interaction_features = ["video_on_tiktok", "retargeting_conversions"]
        feature_cols.extend([c for c in interaction_features if c in df.columns])

        # Remove duplicates and filter available
        feature_cols = list(dict.fromkeys(feature_cols))
        feature_cols = [c for c in feature_cols if c in df.columns]

        # Ensure only numeric columns are used
        numeric_cols = df[feature_cols].select_dtypes(include=[np.number]).columns.tolist()
        feature_cols = numeric_cols

        logger.info("roas_predictor_features", num_features=len(feature_cols))

        # =====================================================================
        # Prepare data
        # =====================================================================
        X = df[feature_cols].values
        y = df["roas"].values

        # Remove outliers (ROAS > 10 is unrealistic for most campaigns)
        mask = (y > 0) & (y < 10)
        X, y = X[mask], y[mask]

        if len(X) < 100:
            logger.warning("limited_training_data", num_samples=len(X))

        # Train-test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Handle missing values
        imputer = SimpleImputer(strategy="median")
        X_train = imputer.fit_transform(X_train)
        X_test = imputer.transform(X_test)

        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # =====================================================================
        # Train model with hyperparameter tuning
        # =====================================================================
        base_model = HistGradientBoostingRegressor(
            random_state=42,
            early_stopping=True,
            validation_fraction=0.1,
        )

        # Grid search for best parameters
        param_grid = {
            "max_depth": [5, 8, 12],
            "learning_rate": [0.05, 0.1, 0.15],
            "max_iter": [100, 200],
            "l2_regularization": [0.0, 0.1, 1.0],
        }

        # Use smaller grid if limited data
        if len(X_train) < 500:
            param_grid = {
                "max_depth": [5, 8],
                "learning_rate": [0.1],
                "max_iter": [100],
                "l2_regularization": [0.1],
            }

        grid_search = GridSearchCV(
            base_model,
            param_grid,
            cv=3,
            scoring="r2",
            n_jobs=-1,
            verbose=0,
        )
        grid_search.fit(X_train_scaled, y_train)

        model = grid_search.best_estimator_
        logger.info("best_params_found", params=grid_search.best_params_)

        # =====================================================================
        # Evaluate
        # =====================================================================
        y_pred = model.predict(X_test_scaled)
        metrics = self._evaluate_model(y_test, y_pred)

        # Cross-validation on best model
        cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring="r2")
        metrics["cv_r2_mean"] = float(np.mean(cv_scores))
        metrics["cv_r2_std"] = float(np.std(cv_scores))
        metrics["best_params"] = grid_search.best_params_
        metrics["num_features"] = len(feature_cols)
        metrics["num_samples"] = len(X)

        # =====================================================================
        # Save model and metadata
        # =====================================================================
        self._save_model(
            model=model,
            scaler=scaler,
            name="roas_predictor",
            features=feature_cols,
            metrics=metrics,
            imputer=imputer,
        )

        return metrics

    def train_conversion_predictor(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Train conversion prediction model.

        Features: spend, impressions, clicks, ctr, cpc
        Target: conversions
        """
        feature_cols = ["log_spend", "log_impressions", "log_clicks", "ctr", "cpc"]

        # Add platform columns if present
        platform_cols = [c for c in df.columns if c.startswith("platform_")]
        feature_cols.extend(platform_cols)

        # Filter available columns
        feature_cols = [c for c in feature_cols if c in df.columns]

        X = df[feature_cols].values
        y = df["conversions"].values

        # Remove outliers
        mask = y >= 0
        X, y = X[mask], y[mask]

        # Train-test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # Train model (Random Forest works well for count data)
        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1,
        )
        model.fit(X_train_scaled, y_train)

        # Evaluate
        y_pred = model.predict(X_test_scaled)
        metrics = self._evaluate_model(y_test, y_pred)

        # Feature importances
        metrics["feature_importances"] = {
            name: float(imp)
            for name, imp in zip(feature_cols, model.feature_importances_)
        }

        # Save
        self._save_model(
            model=model,
            scaler=scaler,
            name="conversion_predictor",
            features=feature_cols,
            metrics=metrics,
        )

        return metrics

    def train_budget_impact_predictor(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Train budget impact prediction model.

        Predicts how revenue changes with budget changes.
        Uses aggregated campaign data to learn spend-revenue relationship.
        """
        # Aggregate by campaign if there are multiple rows
        if "campaign_id" in df.columns:
            agg_df = df.groupby("campaign_id").agg({
                "spend": "sum",
                "revenue": "sum",
                "impressions": "sum",
                "clicks": "sum",
                "conversions": "sum",
            }).reset_index()
        else:
            agg_df = df.copy()

        # Calculate efficiency metrics
        agg_df["roas"] = np.where(
            agg_df["spend"] > 0,
            agg_df["revenue"] / agg_df["spend"],
            0
        )
        agg_df["log_spend"] = np.log1p(agg_df["spend"])
        agg_df["log_revenue"] = np.log1p(agg_df["revenue"])

        # Features: log spend, to capture diminishing returns
        feature_cols = ["log_spend"]
        X = agg_df[feature_cols].values
        y = agg_df["log_revenue"].values

        # Remove invalid
        mask = np.isfinite(X.flatten()) & np.isfinite(y)
        X, y = X[mask], y[mask]

        if len(X) < 10:
            return {"error": "Not enough data for budget impact model"}

        # Train-test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Simple Ridge regression (captures log-log relationship)
        model = Ridge(alpha=1.0)
        model.fit(X_train, y_train)

        # Evaluate
        y_pred = model.predict(X_test)
        metrics = self._evaluate_model(y_test, y_pred)

        # Elasticity coefficient (how revenue responds to spend changes)
        metrics["spend_elasticity"] = float(model.coef_[0])

        # Save
        self._save_model(
            model=model,
            scaler=None,
            name="budget_impact",
            features=feature_cols,
            metrics=metrics,
        )

        return metrics

    def _evaluate_model(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """Calculate evaluation metrics."""
        return {
            "r2": float(r2_score(y_true, y_pred)),
            "mae": float(mean_absolute_error(y_true, y_pred)),
            "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
            "mape": float(np.mean(np.abs((y_true - y_pred) / (y_true + 1e-10))) * 100),
        }

    def _save_model(
        self,
        model: Any,
        scaler: Optional[StandardScaler],
        name: str,
        features: List[str],
        metrics: Dict[str, Any],
        imputer: Optional[SimpleImputer] = None,
    ) -> None:
        """Save model, preprocessors, and metadata to disk."""
        # Save model
        model_path = self.models_path / f"{name}.pkl"
        joblib.dump(model, model_path)

        # Save scaler if present
        if scaler is not None:
            scaler_path = self.models_path / f"{name}_scaler.pkl"
            joblib.dump(scaler, scaler_path)

        # Save imputer if present
        if imputer is not None:
            imputer_path = self.models_path / f"{name}_imputer.pkl"
            joblib.dump(imputer, imputer_path)

        # Serialize best_params if present (convert numpy types)
        serializable_metrics = {}
        for key, value in metrics.items():
            if isinstance(value, dict):
                serializable_metrics[key] = {
                    k: int(v) if isinstance(v, (np.integer, np.int64)) else float(v) if isinstance(v, (np.floating, np.float64)) else v
                    for k, v in value.items()
                }
            elif isinstance(value, (np.integer, np.int64)):
                serializable_metrics[key] = int(value)
            elif isinstance(value, (np.floating, np.float64)):
                serializable_metrics[key] = float(value)
            else:
                serializable_metrics[key] = value

        # Save metadata
        metadata = {
            "name": name,
            "version": "2.0.0",  # Enhanced version with creative/audience features
            "created_at": datetime.now(timezone.utc).isoformat(),
            "features": features,
            "metrics": serializable_metrics,
            "model_type": type(model).__name__,
            "has_imputer": imputer is not None,
            "has_scaler": scaler is not None,
        }

        metadata_path = self.models_path / f"{name}_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info("model_saved", path=str(model_path), r2_score=round(metrics.get("r2", 0), 4), num_features=len(features))


    def train_platform_specific_models(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Train platform-specific ROAS models for better accuracy.
        Each platform has different characteristics and user behaviors.
        """
        results = {}

        if "platform" not in df.columns:
            logger.warning("No platform column found, skipping platform-specific models")
            return results

        platforms = df["platform"].dropna().unique()
        logger.info("training_platform_models", platforms=list(platforms))

        for platform in platforms:
            platform_df = df[df["platform"] == platform].copy()

            if len(platform_df) < 50:
                logger.warning("insufficient_platform_data", platform=platform, rows=len(platform_df))
                continue

            logger.info("training_platform_model", platform=platform, num_samples=len(platform_df))

            try:
                # Use simplified feature set for platform-specific models
                feature_cols = [
                    "log_spend", "log_impressions", "log_clicks",
                    "ctr", "cvr", "cpm", "cpc"
                ]

                # Add creative features if available
                creative_cols = [c for c in platform_df.columns if c.startswith("creative_")]
                feature_cols.extend(creative_cols[:5])  # Limit to avoid overfitting

                # Add audience features if available
                audience_cols = [c for c in platform_df.columns if c.startswith("audience_")]
                feature_cols.extend(audience_cols[:3])

                # Add historical features
                if "roas_7d_avg" in platform_df.columns:
                    feature_cols.append("roas_7d_avg")

                feature_cols = [c for c in feature_cols if c in platform_df.columns]

                X = platform_df[feature_cols].values
                y = platform_df["roas"].values

                # Remove outliers
                mask = (y > 0) & (y < 10)
                X, y = X[mask], y[mask]

                if len(X) < 30:
                    logger.warning("insufficient_valid_platform_data", platform=platform)
                    continue

                # Train-test split
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.2, random_state=42
                )

                # Impute and scale
                imputer = SimpleImputer(strategy="median")
                X_train = imputer.fit_transform(X_train)
                X_test = imputer.transform(X_test)

                scaler = StandardScaler()
                X_train_scaled = scaler.fit_transform(X_train)
                X_test_scaled = scaler.transform(X_test)

                # Train model
                model = HistGradientBoostingRegressor(
                    max_depth=6,
                    learning_rate=0.1,
                    max_iter=100,
                    random_state=42,
                    early_stopping=True,
                    validation_fraction=0.15,
                )
                model.fit(X_train_scaled, y_train)

                # Evaluate
                y_pred = model.predict(X_test_scaled)
                metrics = self._evaluate_model(y_test, y_pred)
                metrics["num_samples"] = len(X)
                metrics["num_features"] = len(feature_cols)

                # Save platform-specific model
                self._save_model(
                    model=model,
                    scaler=scaler,
                    name=f"roas_predictor_{platform}",
                    features=feature_cols,
                    metrics=metrics,
                    imputer=imputer,
                )

                results[platform] = metrics
                logger.info("platform_model_trained", platform=platform, r2=round(metrics["r2"], 4))

            except Exception as e:
                logger.error("platform_model_training_error", platform=platform, error=str(e))
                results[platform] = {"error": str(e)}

        return results


def train_from_csv(csv_path: str, models_path: str = None) -> Dict[str, Any]:
    """
    Train models from a CSV file.

    Args:
        csv_path: Path to training data CSV
        models_path: Where to save models

    Returns:
        Training results
    """
    from app.ml.data_loader import TrainingDataLoader

    # Load data
    loader = TrainingDataLoader()
    df = loader.load_csv_to_dataframe(csv_path)

    # Train models
    trainer = ModelTrainer(models_path)
    results = trainer.train_all(df)

    return results


def train_from_sample_data(
    num_campaigns: int = 100,
    days: int = 30,
    models_path: str = None,
) -> Dict[str, Any]:
    """
    Train models using generated sample data.

    Args:
        num_campaigns: Number of campaigns to generate
        days: Days of data per campaign
        models_path: Where to save models

    Returns:
        Training results
    """
    from app.ml.data_loader import TrainingDataLoader

    # Generate sample data
    logger.info("generating_sample_data", num_campaigns=num_campaigns, days=days)
    df = TrainingDataLoader.generate_sample_data(
        num_campaigns=num_campaigns,
        days_per_campaign=days,
    )

    # Train models
    trainer = ModelTrainer(models_path)
    results = trainer.train_all(df)

    return results


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train ML models")
    parser.add_argument("--csv", type=str, help="Path to training CSV")
    parser.add_argument("--sample", action="store_true", help="Use sample data")
    parser.add_argument("--campaigns", type=int, default=100, help="Sample campaigns")
    parser.add_argument("--days", type=int, default=30, help="Days per campaign")
    parser.add_argument("--output", type=str, default="./models", help="Models output path")

    args = parser.parse_args()

    if args.csv:
        logger.info("training_from_csv", csv_path=args.csv)
        results = train_from_csv(args.csv, args.output)
    elif args.sample:
        logger.info("training_from_sample_data")
        results = train_from_sample_data(args.campaigns, args.days, args.output)
    else:
        logger.error("no_training_source_specified")
        exit(1)

    logger.info("training_complete")
    for model_name, metrics in results.items():
        if isinstance(metrics, dict):
            safe_metrics = {k: v for k, v in metrics.items() if k != "feature_importances"}
            logger.info("model_results", model=model_name, **safe_metrics)
