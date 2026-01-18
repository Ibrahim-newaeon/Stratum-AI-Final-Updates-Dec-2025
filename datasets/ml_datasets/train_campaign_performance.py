"""
Campaign Performance Prediction Model Training Script

Trains regression models to predict campaign performance metrics:
- ROAS (Return on Ad Spend) - primary target
- CPA (Cost per Acquisition) - secondary target

Based on:
- Campaign configuration (platform, objective, audience)
- Spend and budget metrics
- Creative performance (CTR, frequency)
- Historical performance patterns

Models trained:
- Gradient Boosting Regressor (primary)
- Random Forest Regressor (comparison)
- Platform-specific models
"""

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score, KFold
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.pipeline import Pipeline

from ml_utils import (
    load_dataset, save_model, save_report,
    get_feature_columns, create_preprocessor,
    evaluate_regression, print_regression_metrics,
    get_feature_importance
)


def prepare_data(df: pd.DataFrame):
    """Prepare features and targets for campaign performance prediction."""
    # Define target and ID columns to exclude
    exclude_cols = ['campaign_id', 'date', 'roas', 'cpa', 'conversions', 'revenue']

    # Get feature columns
    numeric_cols, categorical_cols = get_feature_columns(df, exclude_cols)

    print(f"Numeric features ({len(numeric_cols)}): {numeric_cols[:5]}...")
    print(f"Categorical features ({len(categorical_cols)}): {categorical_cols}")

    # Prepare features
    X = df[numeric_cols + categorical_cols]

    # Multiple targets
    y_roas = df['roas']
    y_cpa = df['cpa']

    print(f"\nTarget (ROAS) statistics:")
    print(f"  Mean: {y_roas.mean():.2f}x")
    print(f"  Median: {y_roas.median():.2f}x")
    print(f"  Range: {y_roas.min():.2f}x - {y_roas.max():.2f}x")

    print(f"\nTarget (CPA) statistics:")
    print(f"  Mean: ${y_cpa.mean():.2f}")
    print(f"  Median: ${y_cpa.median():.2f}")
    print(f"  Range: ${y_cpa.min():.2f} - ${y_cpa.max():.2f}")

    return X, y_roas, y_cpa, numeric_cols, categorical_cols


def train_roas_models(X_train, X_test, y_train, y_test, numeric_cols, categorical_cols):
    """Train models for ROAS prediction."""
    preprocessor = create_preprocessor(numeric_cols, categorical_cols)
    results = {}

    # 1. Gradient Boosting
    print("\nTraining Gradient Boosting for ROAS...")
    gb_pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('regressor', GradientBoostingRegressor(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            min_samples_split=15,
            random_state=42
        ))
    ])
    gb_pipeline.fit(X_train, y_train)

    y_pred = gb_pipeline.predict(X_test)
    results['gradient_boosting'] = {
        'model': gb_pipeline,
        'predictions': y_pred,
        'metrics': evaluate_regression(y_test, y_pred)
    }
    print_regression_metrics(results['gradient_boosting']['metrics'], "Gradient Boosting (ROAS)")

    # 2. Random Forest
    print("Training Random Forest for ROAS...")
    rf_pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('regressor', RandomForestRegressor(
            n_estimators=200,
            max_depth=12,
            min_samples_split=15,
            random_state=42,
            n_jobs=-1
        ))
    ])
    rf_pipeline.fit(X_train, y_train)

    y_pred = rf_pipeline.predict(X_test)
    results['random_forest'] = {
        'model': rf_pipeline,
        'predictions': y_pred,
        'metrics': evaluate_regression(y_test, y_pred)
    }
    print_regression_metrics(results['random_forest']['metrics'], "Random Forest (ROAS)")

    return results


def train_cpa_models(X_train, X_test, y_train, y_test, numeric_cols, categorical_cols):
    """Train models for CPA prediction."""
    preprocessor = create_preprocessor(numeric_cols, categorical_cols)
    results = {}

    # 1. Gradient Boosting
    print("\nTraining Gradient Boosting for CPA...")
    gb_pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('regressor', GradientBoostingRegressor(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            min_samples_split=15,
            random_state=42
        ))
    ])
    gb_pipeline.fit(X_train, y_train)

    y_pred = gb_pipeline.predict(X_test)
    results['gradient_boosting'] = {
        'model': gb_pipeline,
        'predictions': y_pred,
        'metrics': evaluate_regression(y_test, y_pred)
    }
    print_regression_metrics(results['gradient_boosting']['metrics'], "Gradient Boosting (CPA)")

    # 2. Random Forest
    print("Training Random Forest for CPA...")
    rf_pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('regressor', RandomForestRegressor(
            n_estimators=200,
            max_depth=12,
            min_samples_split=15,
            random_state=42,
            n_jobs=-1
        ))
    ])
    rf_pipeline.fit(X_train, y_train)

    y_pred = rf_pipeline.predict(X_test)
    results['random_forest'] = {
        'model': rf_pipeline,
        'predictions': y_pred,
        'metrics': evaluate_regression(y_test, y_pred)
    }
    print_regression_metrics(results['random_forest']['metrics'], "Random Forest (CPA)")

    return results


def analyze_platform_performance(df, model, X, y_roas, feature_names):
    """Analyze model performance by platform."""
    print("\n" + "="*60)
    print("  Platform-Specific Performance Analysis")
    print("="*60)

    platforms = df['platform'].unique()
    platform_results = []

    for platform in platforms:
        mask = df['platform'] == platform
        if mask.sum() > 0:
            X_platform = X[mask]
            y_platform = y_roas[mask]

            y_pred = model.predict(X_platform)
            metrics = evaluate_regression(y_platform.values, y_pred)

            platform_results.append({
                'platform': platform,
                'count': mask.sum(),
                'avg_roas': y_platform.mean(),
                'r2': metrics['r2'],
                'rmse': metrics['rmse']
            })

            print(f"  {platform:<12} | Records: {mask.sum():>5} | Avg ROAS: {y_platform.mean():>6.2f}x | R²: {metrics['r2']:.3f} | RMSE: {metrics['rmse']:.3f}")

    return platform_results


def analyze_performance_drivers(model, feature_names, target_name):
    """Analyze top factors affecting campaign performance."""
    print(f"\n" + "="*60)
    print(f"  Top {target_name} Prediction Drivers")
    print("="*60)

    importance_df = get_feature_importance(
        model.named_steps['regressor'],
        feature_names,
        top_n=15
    )

    if not importance_df.empty:
        for idx, row in importance_df.iterrows():
            bar = "█" * int(row['importance'] * 50)
            print(f"  {row['feature'][:30]:<30} {row['importance']:.4f} {bar}")

    return importance_df


def main():
    """Main training pipeline."""
    print("="*60)
    print("  CAMPAIGN PERFORMANCE PREDICTION MODEL TRAINING")
    print("="*60)

    # Load data
    print("\nLoading dataset...")
    df = load_dataset('campaign_performance_dataset.csv')
    print(f"Dataset shape: {df.shape}")
    print(f"Platforms: {df['platform'].unique().tolist()}")

    # Prepare data
    X, y_roas, y_cpa, numeric_cols, categorical_cols = prepare_data(df)

    # Split data
    X_train, X_test, y_roas_train, y_roas_test, y_cpa_train, y_cpa_test = train_test_split(
        X, y_roas, y_cpa, test_size=0.2, random_state=42
    )
    print(f"\nTrain set: {len(X_train)} samples")
    print(f"Test set: {len(X_test)} samples")

    # Train ROAS models
    print("\n" + "-"*60)
    print("  ROAS Prediction Models")
    print("-"*60)
    roas_results = train_roas_models(
        X_train, X_test, y_roas_train, y_roas_test,
        numeric_cols, categorical_cols
    )

    # Train CPA models
    print("\n" + "-"*60)
    print("  CPA Prediction Models")
    print("-"*60)
    cpa_results = train_cpa_models(
        X_train, X_test, y_cpa_train, y_cpa_test,
        numeric_cols, categorical_cols
    )

    # Select best models
    best_roas_name = max(roas_results, key=lambda k: roas_results[k]['metrics']['r2'])
    best_roas_model = roas_results[best_roas_name]['model']
    best_roas_metrics = roas_results[best_roas_name]['metrics']

    best_cpa_name = max(cpa_results, key=lambda k: cpa_results[k]['metrics']['r2'])
    best_cpa_model = cpa_results[best_cpa_name]['model']
    best_cpa_metrics = cpa_results[best_cpa_name]['metrics']

    print(f"\n*** Best ROAS Model: {best_roas_name} (R²: {best_roas_metrics['r2']:.4f}) ***")
    print(f"*** Best CPA Model: {best_cpa_name} (R²: {best_cpa_metrics['r2']:.4f}) ***")

    # Platform analysis
    platform_results = analyze_platform_performance(
        df, best_roas_model, X, y_roas,
        numeric_cols + categorical_cols
    )

    # Feature importance analysis
    preprocessor = best_roas_model.named_steps['preprocessor']
    feature_names = numeric_cols.copy()

    if categorical_cols:
        cat_encoder = preprocessor.named_transformers_['cat']
        cat_features = cat_encoder.get_feature_names_out(categorical_cols).tolist()
        feature_names.extend(cat_features)

    roas_importance = analyze_performance_drivers(best_roas_model, feature_names, "ROAS")
    cpa_importance = analyze_performance_drivers(best_cpa_model, feature_names, "CPA")

    # Save ROAS model
    roas_metadata = {
        'model_type': best_roas_name,
        'target': 'roas',
        'features': {
            'numeric': numeric_cols,
            'categorical': categorical_cols
        },
        'training_samples': len(X_train),
        'test_samples': len(X_test),
        'metrics': best_roas_metrics,
        'platforms': df['platform'].unique().tolist()
    }
    save_model(best_roas_model, 'campaign_roas_prediction', roas_metadata)

    # Save CPA model
    cpa_metadata = {
        'model_type': best_cpa_name,
        'target': 'cpa',
        'features': {
            'numeric': numeric_cols,
            'categorical': categorical_cols
        },
        'training_samples': len(X_train),
        'test_samples': len(X_test),
        'metrics': best_cpa_metrics
    }
    save_model(best_cpa_model, 'campaign_cpa_prediction', cpa_metadata)

    # Save comprehensive report
    report = {
        'roas_models': {
            name: res['metrics']
            for name, res in roas_results.items()
        },
        'cpa_models': {
            name: res['metrics']
            for name, res in cpa_results.items()
        },
        'best_roas_model': {
            'name': best_roas_name,
            'metrics': best_roas_metrics
        },
        'best_cpa_model': {
            'name': best_cpa_name,
            'metrics': best_cpa_metrics
        },
        'platform_analysis': platform_results,
        'roas_feature_importance': roas_importance.to_dict('records') if not roas_importance.empty else [],
        'cpa_feature_importance': cpa_importance.to_dict('records') if not cpa_importance.empty else [],
        'dataset_info': {
            'total_samples': len(df),
            'features': len(numeric_cols) + len(categorical_cols),
            'platforms': df['platform'].unique().tolist(),
            'objectives': df['objective'].unique().tolist() if 'objective' in df.columns else [],
            'roas_mean': float(y_roas.mean()),
            'cpa_mean': float(y_cpa.mean())
        }
    }

    save_report(report, 'campaign_performance')

    print("\n" + "="*60)
    print("  Training Complete!")
    print("="*60)
    print(f"  ROAS Model: models/campaign_roas_prediction.joblib")
    print(f"  CPA Model: models/campaign_cpa_prediction.joblib")
    print(f"  Report: reports/campaign_performance_report.json")
    print("="*60)


if __name__ == "__main__":
    main()
