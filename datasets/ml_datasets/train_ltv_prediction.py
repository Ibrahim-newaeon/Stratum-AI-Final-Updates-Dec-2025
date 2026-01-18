"""
LTV (Lifetime Value) Prediction Model Training Script

Trains a regression model to predict 12-month customer LTV based on:
- RFM scores (Recency, Frequency, Monetary)
- Transaction history
- Customer behavior patterns
- Account characteristics

Models trained:
- Gradient Boosting Regressor (primary)
- Random Forest Regressor (comparison)
- Ridge Regression (baseline)
"""

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score, KFold
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline

from ml_utils import (
    load_dataset, save_model, save_report,
    get_feature_columns, create_preprocessor,
    evaluate_regression, print_regression_metrics,
    get_feature_importance
)


def prepare_data(df: pd.DataFrame):
    """Prepare features and target for LTV prediction."""
    # Define target and ID columns to exclude
    exclude_cols = ['customer_id', 'ltv_12_months']

    # Get feature columns
    numeric_cols, categorical_cols = get_feature_columns(df, exclude_cols)

    print(f"Numeric features ({len(numeric_cols)}): {numeric_cols[:5]}...")
    print(f"Categorical features ({len(categorical_cols)}): {categorical_cols}")

    # Prepare features and target
    X = df[numeric_cols + categorical_cols]
    y = df['ltv_12_months']

    print(f"\nTarget (LTV) statistics:")
    print(f"  Mean: ${y.mean():,.2f}")
    print(f"  Median: ${y.median():,.2f}")
    print(f"  Std: ${y.std():,.2f}")
    print(f"  Range: ${y.min():,.2f} - ${y.max():,.2f}")

    return X, y, numeric_cols, categorical_cols


def train_models(X_train, X_test, y_train, y_test, numeric_cols, categorical_cols):
    """Train multiple regression models and compare performance."""
    # Create preprocessor
    preprocessor = create_preprocessor(numeric_cols, categorical_cols)

    results = {}

    # 1. Gradient Boosting Regressor (Primary)
    print("\nTraining Gradient Boosting Regressor...")
    gb_pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('regressor', GradientBoostingRegressor(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42
        ))
    ])
    gb_pipeline.fit(X_train, y_train)

    y_pred_gb = gb_pipeline.predict(X_test)
    results['gradient_boosting'] = {
        'model': gb_pipeline,
        'predictions': y_pred_gb,
        'metrics': evaluate_regression(y_test, y_pred_gb)
    }
    print_regression_metrics(results['gradient_boosting']['metrics'], "Gradient Boosting")

    # 2. Random Forest Regressor
    print("Training Random Forest Regressor...")
    rf_pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('regressor', RandomForestRegressor(
            n_estimators=200,
            max_depth=15,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1
        ))
    ])
    rf_pipeline.fit(X_train, y_train)

    y_pred_rf = rf_pipeline.predict(X_test)
    results['random_forest'] = {
        'model': rf_pipeline,
        'predictions': y_pred_rf,
        'metrics': evaluate_regression(y_test, y_pred_rf)
    }
    print_regression_metrics(results['random_forest']['metrics'], "Random Forest")

    # 3. Ridge Regression (Baseline)
    print("Training Ridge Regression (Baseline)...")
    ridge_pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('regressor', Ridge(alpha=1.0, random_state=42))
    ])
    ridge_pipeline.fit(X_train, y_train)

    y_pred_ridge = ridge_pipeline.predict(X_test)
    results['ridge_regression'] = {
        'model': ridge_pipeline,
        'predictions': y_pred_ridge,
        'metrics': evaluate_regression(y_test, y_pred_ridge)
    }
    print_regression_metrics(results['ridge_regression']['metrics'], "Ridge Regression")

    return results


def cross_validate_best_model(model, X, y, cv=5):
    """Perform cross-validation on the best model."""
    print(f"\nPerforming {cv}-fold cross-validation...")

    cv_strategy = KFold(n_splits=cv, shuffle=True, random_state=42)

    # Multiple scoring metrics
    r2_scores = cross_val_score(model, X, y, cv=cv_strategy, scoring='r2', n_jobs=-1)
    neg_rmse_scores = cross_val_score(model, X, y, cv=cv_strategy, scoring='neg_root_mean_squared_error', n_jobs=-1)

    print(f"  CV R² scores: {r2_scores}")
    print(f"  Mean R²: {r2_scores.mean():.4f} (+/- {r2_scores.std() * 2:.4f})")
    print(f"  Mean RMSE: {-neg_rmse_scores.mean():.2f} (+/- {neg_rmse_scores.std() * 2:.2f})")

    return {
        'r2_scores': r2_scores,
        'rmse_scores': -neg_rmse_scores
    }


def analyze_ltv_drivers(model, feature_names):
    """Analyze top factors driving LTV."""
    print("\n" + "="*60)
    print("  Top LTV Prediction Drivers")
    print("="*60)

    importance_df = get_feature_importance(
        model.named_steps['regressor'],
        feature_names,
        top_n=15
    )

    if not importance_df.empty:
        for idx, row in importance_df.iterrows():
            bar = "#" * int(row['importance'] * 50)
            print(f"  {row['feature'][:30]:<30} {row['importance']:.4f} {bar}")

    return importance_df


def analyze_ltv_segments(df, y_test, y_pred):
    """Analyze prediction accuracy by LTV segment."""
    print("\n" + "="*60)
    print("  LTV Segment Analysis")
    print("="*60)

    # Create LTV segments
    segments = pd.qcut(y_test, q=4, labels=['Low', 'Medium', 'High', 'Premium'])

    results = []
    for segment in ['Low', 'Medium', 'High', 'Premium']:
        mask = segments == segment
        if mask.sum() > 0:
            segment_actual = y_test[mask]
            segment_pred = y_pred[mask]
            mae = np.mean(np.abs(segment_actual - segment_pred))
            mape = np.mean(np.abs((segment_actual - segment_pred) / (segment_actual + 1))) * 100

            results.append({
                'segment': segment,
                'count': mask.sum(),
                'avg_ltv': segment_actual.mean(),
                'mae': mae,
                'mape': mape
            })

            print(f"  {segment:<10} | Count: {mask.sum():>4} | Avg LTV: ${segment_actual.mean():>10,.2f} | MAE: ${mae:>8,.2f} | MAPE: {mape:>5.1f}%")

    return results


def main():
    """Main training pipeline."""
    print("="*60)
    print("  LTV PREDICTION MODEL TRAINING")
    print("="*60)

    # Load data
    print("\nLoading dataset...")
    df = load_dataset('ltv_prediction_dataset.csv')
    print(f"Dataset shape: {df.shape}")

    # Prepare data
    X, y, numeric_cols, categorical_cols = prepare_data(df)

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"\nTrain set: {len(X_train)} samples")
    print(f"Test set: {len(X_test)} samples")

    # Train models
    results = train_models(X_train, X_test, y_train, y_test, numeric_cols, categorical_cols)

    # Select best model based on R²
    best_model_name = max(results, key=lambda k: results[k]['metrics']['r2'])
    best_model = results[best_model_name]['model']
    best_metrics = results[best_model_name]['metrics']
    best_predictions = results[best_model_name]['predictions']

    print(f"\n*** Best Model: {best_model_name} (R²: {best_metrics['r2']:.4f}) ***")

    # Cross-validation
    cv_results = cross_validate_best_model(best_model, X, y)

    # Feature importance analysis
    preprocessor = best_model.named_steps['preprocessor']
    feature_names = numeric_cols.copy()

    if categorical_cols:
        cat_encoder = preprocessor.named_transformers_['cat']
        cat_features = cat_encoder.get_feature_names_out(categorical_cols).tolist()
        feature_names.extend(cat_features)

    importance_df = analyze_ltv_drivers(best_model, feature_names)

    # Segment analysis
    segment_results = analyze_ltv_segments(df, y_test.values, best_predictions)

    # Save best model
    metadata = {
        'model_type': best_model_name,
        'features': {
            'numeric': numeric_cols,
            'categorical': categorical_cols
        },
        'training_samples': len(X_train),
        'test_samples': len(X_test),
        'target_stats': {
            'mean': float(y.mean()),
            'median': float(y.median()),
            'std': float(y.std())
        },
        'metrics': {
            'rmse': best_metrics['rmse'],
            'mae': best_metrics['mae'],
            'r2': best_metrics['r2'],
            'mape': best_metrics['mape']
        },
        'cv_r2_mean': float(cv_results['r2_scores'].mean()),
        'cv_r2_std': float(cv_results['r2_scores'].std())
    }

    save_model(best_model, 'ltv_prediction', metadata)

    # Save comprehensive report
    report = {
        'model_comparison': {
            name: res['metrics']
            for name, res in results.items()
        },
        'best_model': best_model_name,
        'best_metrics': best_metrics,
        'cross_validation': {
            'folds': 5,
            'r2_scores': cv_results['r2_scores'].tolist(),
            'r2_mean': float(cv_results['r2_scores'].mean()),
            'r2_std': float(cv_results['r2_scores'].std()),
            'rmse_mean': float(cv_results['rmse_scores'].mean()),
            'rmse_std': float(cv_results['rmse_scores'].std())
        },
        'feature_importance': importance_df.to_dict('records') if not importance_df.empty else [],
        'segment_analysis': segment_results,
        'dataset_info': {
            'total_samples': len(df),
            'features': len(numeric_cols) + len(categorical_cols),
            'ltv_mean': float(y.mean()),
            'ltv_median': float(y.median())
        }
    }

    save_report(report, 'ltv_prediction')

    print("\n" + "="*60)
    print("  Training Complete!")
    print("="*60)
    print(f"  Model saved: models/ltv_prediction.joblib")
    print(f"  Report saved: reports/ltv_prediction_report.json")
    print("="*60)


if __name__ == "__main__":
    main()
