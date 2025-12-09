# =============================================================================
# Stratum AI - ML Training Pipeline
# =============================================================================
"""
Training pipeline for ML models.
Trains ROAS predictor, conversion predictor, and saves as .pkl files.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler

from app.core.logging import get_logger

logger = get_logger(__name__)


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

    def train_all(self, df: pd.DataFrame) -> Dict[str, Any]:
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

        Returns:
            Training results summary
        """
        results = {}

        # Prepare data
        df = self._prepare_data(df)

        # Train ROAS predictor
        print("Training ROAS predictor...")
        results["roas_predictor"] = self.train_roas_predictor(df)

        # Train conversion predictor
        print("Training conversion predictor...")
        results["conversion_predictor"] = self.train_conversion_predictor(df)

        # Train budget impact predictor
        print("Training budget impact predictor...")
        results["budget_impact"] = self.train_budget_impact_predictor(df)

        return results

    def _prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare and clean data for training."""
        df = df.copy()

        # Convert cents to dollars if needed
        if "spend_cents" in df.columns and "spend" not in df.columns:
            df["spend"] = df["spend_cents"] / 100
        if "revenue_cents" in df.columns and "revenue" not in df.columns:
            df["revenue"] = df["revenue_cents"] / 100

        # Calculate derived metrics
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

        # Log transforms for skewed features
        df["log_spend"] = np.log1p(df["spend"])
        df["log_impressions"] = np.log1p(df["impressions"])
        df["log_clicks"] = np.log1p(df["clicks"])

        # Platform encoding (if present)
        if "platform" in df.columns:
            platform_dummies = pd.get_dummies(df["platform"], prefix="platform")
            df = pd.concat([df, platform_dummies], axis=1)

        # Remove rows with invalid data
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.dropna(subset=["spend", "impressions", "clicks", "revenue"])

        return df

    def train_roas_predictor(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Train ROAS prediction model.

        Features: spend, impressions, clicks, ctr, platform
        Target: roas
        """
        # Select features
        feature_cols = ["log_spend", "log_impressions", "log_clicks", "ctr", "cpm"]

        # Add platform columns if present
        platform_cols = [c for c in df.columns if c.startswith("platform_")]
        feature_cols.extend(platform_cols)

        # Filter available columns
        feature_cols = [c for c in feature_cols if c in df.columns]

        X = df[feature_cols].values
        y = df["roas"].values

        # Remove outliers (ROAS > 10 is unrealistic)
        mask = (y > 0) & (y < 10)
        X, y = X[mask], y[mask]

        # Train-test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # Train model
        model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42,
        )
        model.fit(X_train_scaled, y_train)

        # Evaluate
        y_pred = model.predict(X_test_scaled)
        metrics = self._evaluate_model(y_test, y_pred)

        # Cross-validation
        cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring="r2")
        metrics["cv_r2_mean"] = float(np.mean(cv_scores))
        metrics["cv_r2_std"] = float(np.std(cv_scores))

        # Save model and metadata
        self._save_model(
            model=model,
            scaler=scaler,
            name="roas_predictor",
            features=feature_cols,
            metrics=metrics,
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
    ) -> None:
        """Save model and metadata to disk."""
        # Save model
        model_path = self.models_path / f"{name}.pkl"
        joblib.dump(model, model_path)

        # Save scaler if present
        if scaler is not None:
            scaler_path = self.models_path / f"{name}_scaler.pkl"
            joblib.dump(scaler, scaler_path)

        # Save metadata
        metadata = {
            "name": name,
            "version": "1.0.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "features": features,
            "metrics": metrics,
            "model_type": type(model).__name__,
        }

        metadata_path = self.models_path / f"{name}_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        print(f"  Saved: {model_path}")
        print(f"  R² Score: {metrics.get('r2', 'N/A'):.4f}")


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
    print(f"Generating sample data: {num_campaigns} campaigns, {days} days...")
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
        print(f"Training from CSV: {args.csv}")
        results = train_from_csv(args.csv, args.output)
    elif args.sample:
        print("Training from sample data...")
        results = train_from_sample_data(args.campaigns, args.days, args.output)
    else:
        print("Specify --csv <file> or --sample")
        exit(1)

    print("\n" + "=" * 50)
    print("Training Complete!")
    print("=" * 50)
    for model_name, metrics in results.items():
        print(f"\n{model_name}:")
        if isinstance(metrics, dict):
            for key, value in metrics.items():
                if key != "feature_importances":
                    print(f"  {key}: {value}")
