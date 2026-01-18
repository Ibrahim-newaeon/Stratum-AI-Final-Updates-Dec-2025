"""
Churn Prediction Model Training Script

Trains a classification model to predict customer churn based on:
- Engagement metrics (logins, feature usage, session duration)
- Transaction history (MRR, payment failures)
- Support interactions (tickets, NPS scores)
- Account characteristics (age, subscription tier)

Models trained:
- Random Forest Classifier (primary)
- Gradient Boosting Classifier (comparison)
- Logistic Regression (baseline)
"""

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.calibration import CalibratedClassifierCV

from ml_utils import (
    load_dataset, save_model, save_report,
    get_feature_columns, create_preprocessor,
    evaluate_classification, print_classification_metrics,
    get_feature_importance
)


def prepare_data(df: pd.DataFrame):
    """Prepare features and target for churn prediction."""
    # Define target and ID columns to exclude
    # Note: churn_date is excluded to prevent data leakage
    exclude_cols = ['customer_id', 'churned', 'churn_probability', 'churn_date']

    # Get feature columns
    numeric_cols, categorical_cols = get_feature_columns(df, exclude_cols)

    print(f"Numeric features ({len(numeric_cols)}): {numeric_cols[:5]}...")
    print(f"Categorical features ({len(categorical_cols)}): {categorical_cols}")

    # Prepare features and target
    X = df[numeric_cols + categorical_cols]
    y = df['churned']

    return X, y, numeric_cols, categorical_cols


def train_models(X_train, X_test, y_train, y_test, numeric_cols, categorical_cols):
    """Train multiple models and compare performance."""
    # Create preprocessor
    preprocessor = create_preprocessor(numeric_cols, categorical_cols)

    results = {}

    # 1. Random Forest (Primary Model)
    print("\nTraining Random Forest...")
    rf_pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_split=10,
            min_samples_leaf=5,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        ))
    ])
    rf_pipeline.fit(X_train, y_train)

    y_pred_rf = rf_pipeline.predict(X_test)
    y_prob_rf = rf_pipeline.predict_proba(X_test)

    results['random_forest'] = {
        'model': rf_pipeline,
        'predictions': y_pred_rf,
        'probabilities': y_prob_rf,
        'metrics': evaluate_classification(y_test, y_pred_rf, y_prob_rf)
    }
    print_classification_metrics(results['random_forest']['metrics'], "Random Forest")

    # 2. Gradient Boosting
    print("Training Gradient Boosting...")
    gb_pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', GradientBoostingClassifier(
            n_estimators=150,
            max_depth=6,
            learning_rate=0.1,
            min_samples_split=10,
            random_state=42
        ))
    ])
    gb_pipeline.fit(X_train, y_train)

    y_pred_gb = gb_pipeline.predict(X_test)
    y_prob_gb = gb_pipeline.predict_proba(X_test)

    results['gradient_boosting'] = {
        'model': gb_pipeline,
        'predictions': y_pred_gb,
        'probabilities': y_prob_gb,
        'metrics': evaluate_classification(y_test, y_pred_gb, y_prob_gb)
    }
    print_classification_metrics(results['gradient_boosting']['metrics'], "Gradient Boosting")

    # 3. Logistic Regression (Baseline)
    print("Training Logistic Regression (Baseline)...")
    lr_pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', LogisticRegression(
            max_iter=1000,
            class_weight='balanced',
            random_state=42
        ))
    ])
    lr_pipeline.fit(X_train, y_train)

    y_pred_lr = lr_pipeline.predict(X_test)
    y_prob_lr = lr_pipeline.predict_proba(X_test)

    results['logistic_regression'] = {
        'model': lr_pipeline,
        'predictions': y_pred_lr,
        'probabilities': y_prob_lr,
        'metrics': evaluate_classification(y_test, y_pred_lr, y_prob_lr)
    }
    print_classification_metrics(results['logistic_regression']['metrics'], "Logistic Regression")

    return results


def cross_validate_best_model(model, X, y, cv=5):
    """Perform cross-validation on the best model."""
    print(f"\nPerforming {cv}-fold cross-validation...")

    cv_strategy = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)
    cv_scores = cross_val_score(model, X, y, cv=cv_strategy, scoring='roc_auc', n_jobs=-1)

    print(f"  CV ROC-AUC scores: {cv_scores}")
    print(f"  Mean: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")

    return cv_scores


def analyze_churn_factors(model, X_train, feature_names):
    """Analyze top factors contributing to churn."""
    print("\n" + "="*60)
    print("  Top Churn Prediction Factors")
    print("="*60)

    # Get feature importance
    importance_df = get_feature_importance(
        model.named_steps['classifier'],
        feature_names,
        top_n=15
    )

    if not importance_df.empty:
        for idx, row in importance_df.iterrows():
            bar = "#" * int(row['importance'] * 50)
            print(f"  {row['feature'][:30]:<30} {row['importance']:.4f} {bar}")

    return importance_df


def main():
    """Main training pipeline."""
    print("="*60)
    print("  CHURN PREDICTION MODEL TRAINING")
    print("="*60)

    # Load data
    print("\nLoading dataset...")
    df = load_dataset('churn_prediction_dataset.csv')
    print(f"Dataset shape: {df.shape}")
    print(f"Churn rate: {df['churned'].mean():.2%}")

    # Prepare data
    X, y, numeric_cols, categorical_cols = prepare_data(df)

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\nTrain set: {len(X_train)} samples")
    print(f"Test set: {len(X_test)} samples")

    # Train models
    results = train_models(X_train, X_test, y_train, y_test, numeric_cols, categorical_cols)

    # Select best model based on ROC-AUC
    best_model_name = max(results, key=lambda k: results[k]['metrics'].get('roc_auc', 0))
    best_model = results[best_model_name]['model']
    best_metrics = results[best_model_name]['metrics']

    print(f"\n*** Best Model: {best_model_name} (ROC-AUC: {best_metrics['roc_auc']:.4f}) ***")

    # Cross-validation
    cv_scores = cross_validate_best_model(best_model, X, y)

    # Feature importance analysis
    preprocessor = best_model.named_steps['preprocessor']
    feature_names = numeric_cols.copy()

    # Add encoded categorical feature names
    if categorical_cols:
        cat_encoder = preprocessor.named_transformers_['cat']
        cat_features = cat_encoder.get_feature_names_out(categorical_cols).tolist()
        feature_names.extend(cat_features)

    importance_df = analyze_churn_factors(best_model, X_train, feature_names)

    # Save best model
    metadata = {
        'model_type': best_model_name,
        'features': {
            'numeric': numeric_cols,
            'categorical': categorical_cols
        },
        'training_samples': len(X_train),
        'test_samples': len(X_test),
        'churn_rate': float(y.mean()),
        'metrics': {
            'accuracy': best_metrics['accuracy'],
            'precision': best_metrics['precision_binary'],
            'recall': best_metrics['recall_binary'],
            'f1': best_metrics['f1_binary'],
            'roc_auc': best_metrics['roc_auc']
        },
        'cv_roc_auc_mean': float(cv_scores.mean()),
        'cv_roc_auc_std': float(cv_scores.std())
    }

    save_model(best_model, 'churn_prediction', metadata)

    # Save comprehensive report
    report = {
        'model_comparison': {
            name: {
                'accuracy': res['metrics']['accuracy'],
                'precision': res['metrics'].get('precision_binary', res['metrics']['precision_weighted']),
                'recall': res['metrics'].get('recall_binary', res['metrics']['recall_weighted']),
                'f1': res['metrics'].get('f1_binary', res['metrics']['f1_weighted']),
                'roc_auc': res['metrics'].get('roc_auc', 0)
            }
            for name, res in results.items()
        },
        'best_model': best_model_name,
        'best_metrics': metadata['metrics'],
        'cross_validation': {
            'folds': 5,
            'scores': cv_scores.tolist(),
            'mean': float(cv_scores.mean()),
            'std': float(cv_scores.std())
        },
        'feature_importance': importance_df.to_dict('records') if not importance_df.empty else [],
        'dataset_info': {
            'total_samples': len(df),
            'features': len(numeric_cols) + len(categorical_cols),
            'churn_rate': float(y.mean())
        }
    }

    save_report(report, 'churn_prediction')

    print("\n" + "="*60)
    print("  Training Complete!")
    print("="*60)
    print(f"  Model saved: models/churn_prediction.joblib")
    print(f"  Report saved: reports/churn_prediction_report.json")
    print("="*60)


if __name__ == "__main__":
    main()
