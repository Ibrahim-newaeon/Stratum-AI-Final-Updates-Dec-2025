"""
Shared utilities for ML model training scripts.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# Paths
BASE_DIR = Path(__file__).parent
MODELS_DIR = BASE_DIR / "models"
REPORTS_DIR = BASE_DIR / "reports"


def setup_directories():
    """Create necessary directories for models and reports."""
    MODELS_DIR.mkdir(exist_ok=True)
    REPORTS_DIR.mkdir(exist_ok=True)


def load_dataset(filename: str) -> pd.DataFrame:
    """Load a CSV dataset from the ml_datasets directory."""
    filepath = BASE_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Dataset not found: {filepath}")
    return pd.read_csv(filepath)


def save_model(model: Any, name: str, metadata: Optional[dict] = None):
    """Save a trained model with metadata."""
    setup_directories()

    # Save model
    model_path = MODELS_DIR / f"{name}.joblib"
    joblib.dump(model, model_path)

    # Save metadata
    if metadata:
        metadata["saved_at"] = datetime.now().isoformat()
        metadata["model_path"] = str(model_path)
        metadata_path = MODELS_DIR / f"{name}_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)

    print(f"Model saved: {model_path}")
    return model_path


def load_model(name: str) -> tuple[Any, Optional[dict]]:
    """Load a trained model with its metadata."""
    model_path = MODELS_DIR / f"{name}.joblib"
    metadata_path = MODELS_DIR / f"{name}_metadata.json"

    model = joblib.load(model_path)
    metadata = None

    if metadata_path.exists():
        with open(metadata_path) as f:
            metadata = json.load(f)

    return model, metadata


def get_feature_columns(df: pd.DataFrame, exclude: list[str]) -> tuple[list[str], list[str]]:
    """
    Identify numeric and categorical columns, excluding specified columns.

    Returns:
        Tuple of (numeric_columns, categorical_columns)
    """
    numeric_cols = []
    categorical_cols = []

    for col in df.columns:
        if col in exclude:
            continue
        if df[col].dtype in ["int64", "float64"]:
            numeric_cols.append(col)
        elif df[col].dtype == "object" or df[col].dtype.name == "category":
            categorical_cols.append(col)

    return numeric_cols, categorical_cols


def create_preprocessor(
    numeric_features: list[str], categorical_features: list[str], scale_numeric: bool = True
) -> ColumnTransformer:
    """
    Create a preprocessing pipeline for numeric and categorical features.
    """
    transformers = []

    if numeric_features:
        if scale_numeric:
            transformers.append(("num", StandardScaler(), numeric_features))
        else:
            transformers.append(("num", "passthrough", numeric_features))

    if categorical_features:
        transformers.append(
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                categorical_features,
            )
        )

    return ColumnTransformer(transformers=transformers)


def evaluate_classification(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: Optional[np.ndarray] = None,
    labels: Optional[list] = None,
) -> dict[str, Any]:
    """
    Comprehensive evaluation metrics for classification models.
    """
    metrics = {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision_weighted": precision_score(y_true, y_pred, average="weighted", zero_division=0),
        "recall_weighted": recall_score(y_true, y_pred, average="weighted", zero_division=0),
        "f1_weighted": f1_score(y_true, y_pred, average="weighted", zero_division=0),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
        "classification_report": classification_report(y_true, y_pred, output_dict=True),
    }

    # Binary classification metrics
    unique_classes = np.unique(y_true)
    if len(unique_classes) == 2 and y_prob is not None:
        if y_prob.ndim == 2:
            y_prob_positive = y_prob[:, 1]
        else:
            y_prob_positive = y_prob
        metrics["roc_auc"] = roc_auc_score(y_true, y_prob_positive)
        metrics["precision_binary"] = precision_score(y_true, y_pred, zero_division=0)
        metrics["recall_binary"] = recall_score(y_true, y_pred, zero_division=0)
        metrics["f1_binary"] = f1_score(y_true, y_pred, zero_division=0)
    elif len(unique_classes) > 2 and y_prob is not None:
        try:
            metrics["roc_auc_ovr"] = roc_auc_score(y_true, y_prob, multi_class="ovr")
        except ValueError:
            pass

    return metrics


def evaluate_regression(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """
    Comprehensive evaluation metrics for regression models.
    """
    return {
        "mse": mean_squared_error(y_true, y_pred),
        "rmse": np.sqrt(mean_squared_error(y_true, y_pred)),
        "mae": mean_absolute_error(y_true, y_pred),
        "r2": r2_score(y_true, y_pred),
        "mape": np.mean(np.abs((y_true - y_pred) / (y_true + 1e-8))) * 100,
    }


def save_report(report: dict, name: str):
    """Save evaluation report as JSON."""
    setup_directories()

    report["generated_at"] = datetime.now().isoformat()
    report_path = REPORTS_DIR / f"{name}_report.json"

    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"Report saved: {report_path}")
    return report_path


def print_classification_metrics(metrics: dict[str, Any], model_name: str):
    """Pretty print classification metrics."""
    print(f"\n{'='*60}")
    print(f"  {model_name} - Classification Metrics")
    print(f"{'='*60}")
    print(f"  Accuracy:  {metrics['accuracy']:.4f}")
    print(f"  Precision: {metrics['precision_weighted']:.4f} (weighted)")
    print(f"  Recall:    {metrics['recall_weighted']:.4f} (weighted)")
    print(f"  F1 Score:  {metrics['f1_weighted']:.4f} (weighted)")
    if "roc_auc" in metrics:
        print(f"  ROC-AUC:   {metrics['roc_auc']:.4f}")
    elif "roc_auc_ovr" in metrics:
        print(f"  ROC-AUC:   {metrics['roc_auc_ovr']:.4f} (OvR)")
    print(f"{'='*60}\n")


def print_regression_metrics(metrics: dict[str, float], model_name: str):
    """Pretty print regression metrics."""
    print(f"\n{'='*60}")
    print(f"  {model_name} - Regression Metrics")
    print(f"{'='*60}")
    print(f"  RMSE:  {metrics['rmse']:.4f}")
    print(f"  MAE:   {metrics['mae']:.4f}")
    print(f"  R²:    {metrics['r2']:.4f}")
    print(f"  MAPE:  {metrics['mape']:.2f}%")
    print(f"{'='*60}\n")


def get_feature_importance(model: Any, feature_names: list[str], top_n: int = 20) -> pd.DataFrame:
    """
    Extract feature importance from tree-based models.
    """
    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
    elif hasattr(model, "named_steps") and hasattr(
        model.named_steps.get("classifier", model), "feature_importances_"
    ):
        importances = model.named_steps["classifier"].feature_importances_
    elif hasattr(model, "named_steps") and hasattr(
        model.named_steps.get("regressor", model), "feature_importances_"
    ):
        importances = model.named_steps["regressor"].feature_importances_
    else:
        return pd.DataFrame()

    # Handle case where feature_names length doesn't match
    if len(importances) != len(feature_names):
        feature_names = [f"feature_{i}" for i in range(len(importances))]

    importance_df = pd.DataFrame({"feature": feature_names, "importance": importances}).sort_values(
        "importance", ascending=False
    )

    return importance_df.head(top_n)
