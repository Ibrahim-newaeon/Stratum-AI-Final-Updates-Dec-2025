"""
Signal Health Classification Model Training Script

Trains a multi-class classification model to predict signal health status:
- healthy: Signal is reliable for automation
- risk: Signal showing early degradation signs
- degraded: Signal quality issues, review required
- critical: Signal unreliable, automation blocked

Based on:
- EMQ (Event Match Quality) scores
- Event volume and patterns
- Data freshness metrics
- Source reliability indicators

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
from sklearn.preprocessing import LabelEncoder

from ml_utils import (
    load_dataset, save_model, save_report,
    get_feature_columns, create_preprocessor,
    evaluate_classification, print_classification_metrics,
    get_feature_importance
)


# Health status order for interpretation
HEALTH_STATUS_ORDER = ['critical', 'degraded', 'risk', 'healthy']


def prepare_data(df: pd.DataFrame):
    """Prepare features and target for signal health classification."""
    # Define target and columns to exclude
    exclude_cols = ['date', 'health_status', 'health_score']

    # Get feature columns
    numeric_cols, categorical_cols = get_feature_columns(df, exclude_cols)

    print(f"Numeric features ({len(numeric_cols)}): {numeric_cols}")
    print(f"Categorical features ({len(categorical_cols)}): {categorical_cols}")

    # Prepare features
    X = df[numeric_cols + categorical_cols]
    y = df['health_status']

    # Print class distribution
    print(f"\nHealth Status Distribution:")
    for status in HEALTH_STATUS_ORDER:
        count = (y == status).sum()
        pct = count / len(y) * 100
        print(f"  {status:<10}: {count:>5} ({pct:>5.1f}%)")

    return X, y, numeric_cols, categorical_cols


def train_models(X_train, X_test, y_train, y_test, numeric_cols, categorical_cols):
    """Train multiple classification models and compare performance."""
    preprocessor = create_preprocessor(numeric_cols, categorical_cols)
    results = {}

    # 1. Random Forest (Primary)
    print("\nTraining Random Forest...")
    rf_pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', RandomForestClassifier(
            n_estimators=200,
            max_depth=12,
            min_samples_split=10,
            min_samples_leaf=5,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        ))
    ])
    rf_pipeline.fit(X_train, y_train)

    y_pred = rf_pipeline.predict(X_test)
    y_prob = rf_pipeline.predict_proba(X_test)

    results['random_forest'] = {
        'model': rf_pipeline,
        'predictions': y_pred,
        'probabilities': y_prob,
        'metrics': evaluate_classification(y_test, y_pred, y_prob)
    }
    print_classification_metrics(results['random_forest']['metrics'], "Random Forest")

    # 2. Gradient Boosting
    print("Training Gradient Boosting...")
    gb_pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', GradientBoostingClassifier(
            n_estimators=150,
            max_depth=5,
            learning_rate=0.1,
            min_samples_split=10,
            random_state=42
        ))
    ])
    gb_pipeline.fit(X_train, y_train)

    y_pred = gb_pipeline.predict(X_test)
    y_prob = gb_pipeline.predict_proba(X_test)

    results['gradient_boosting'] = {
        'model': gb_pipeline,
        'predictions': y_pred,
        'probabilities': y_prob,
        'metrics': evaluate_classification(y_test, y_pred, y_prob)
    }
    print_classification_metrics(results['gradient_boosting']['metrics'], "Gradient Boosting")

    # 3. Logistic Regression (Baseline)
    print("Training Logistic Regression (Baseline)...")
    lr_pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', LogisticRegression(
            max_iter=1000,
            multi_class='multinomial',
            class_weight='balanced',
            random_state=42
        ))
    ])
    lr_pipeline.fit(X_train, y_train)

    y_pred = lr_pipeline.predict(X_test)
    y_prob = lr_pipeline.predict_proba(X_test)

    results['logistic_regression'] = {
        'model': lr_pipeline,
        'predictions': y_pred,
        'probabilities': y_prob,
        'metrics': evaluate_classification(y_test, y_pred, y_prob)
    }
    print_classification_metrics(results['logistic_regression']['metrics'], "Logistic Regression")

    return results


def cross_validate_best_model(model, X, y, cv=5):
    """Perform cross-validation on the best model."""
    print(f"\nPerforming {cv}-fold cross-validation...")

    cv_strategy = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)

    accuracy_scores = cross_val_score(model, X, y, cv=cv_strategy, scoring='accuracy', n_jobs=-1)
    f1_scores = cross_val_score(model, X, y, cv=cv_strategy, scoring='f1_weighted', n_jobs=-1)

    print(f"  CV Accuracy: {accuracy_scores.mean():.4f} (+/- {accuracy_scores.std() * 2:.4f})")
    print(f"  CV F1 (weighted): {f1_scores.mean():.4f} (+/- {f1_scores.std() * 2:.4f})")

    return {
        'accuracy_scores': accuracy_scores,
        'f1_scores': f1_scores
    }


def analyze_health_factors(model, feature_names):
    """Analyze factors affecting signal health."""
    print("\n" + "="*60)
    print("  Top Signal Health Factors")
    print("="*60)

    importance_df = get_feature_importance(
        model.named_steps['classifier'],
        feature_names,
        top_n=15
    )

    if not importance_df.empty:
        for idx, row in importance_df.iterrows():
            bar = "█" * int(row['importance'] * 50)
            print(f"  {row['feature'][:30]:<30} {row['importance']:.4f} {bar}")

    return importance_df


def analyze_source_performance(df, model, X, y):
    """Analyze model performance by data source."""
    print("\n" + "="*60)
    print("  Source-Specific Performance")
    print("="*60)

    sources = df['source'].unique()
    source_results = []

    for source in sources:
        mask = df['source'] == source
        if mask.sum() > 0:
            X_source = X[mask]
            y_source = y[mask]

            y_pred = model.predict(X_source)
            accuracy = (y_pred == y_source).mean()

            # Get distribution
            dist = y_source.value_counts().to_dict()

            source_results.append({
                'source': source,
                'count': mask.sum(),
                'accuracy': accuracy,
                'distribution': dist
            })

            print(f"  {source:<20} | Records: {mask.sum():>4} | Accuracy: {accuracy:.3f}")

    return source_results


def analyze_confusion_by_class(y_test, y_pred, classes):
    """Detailed confusion matrix analysis."""
    print("\n" + "="*60)
    print("  Per-Class Performance")
    print("="*60)

    from sklearn.metrics import precision_recall_fscore_support

    precision, recall, f1, support = precision_recall_fscore_support(
        y_test, y_pred, labels=classes
    )

    for i, cls in enumerate(classes):
        print(f"  {cls:<10} | Precision: {precision[i]:.3f} | Recall: {recall[i]:.3f} | F1: {f1[i]:.3f} | Support: {support[i]}")

    return {
        cls: {'precision': precision[i], 'recall': recall[i], 'f1': f1[i], 'support': int(support[i])}
        for i, cls in enumerate(classes)
    }


def main():
    """Main training pipeline."""
    print("="*60)
    print("  SIGNAL HEALTH CLASSIFICATION MODEL TRAINING")
    print("="*60)

    # Load data
    print("\nLoading dataset...")
    df = load_dataset('signal_health_dataset.csv')
    print(f"Dataset shape: {df.shape}")
    print(f"Sources: {df['source'].unique().tolist()}")

    # Prepare data
    X, y, numeric_cols, categorical_cols = prepare_data(df)

    # Split data with stratification
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\nTrain set: {len(X_train)} samples")
    print(f"Test set: {len(X_test)} samples")

    # Train models
    results = train_models(X_train, X_test, y_train, y_test, numeric_cols, categorical_cols)

    # Select best model based on weighted F1
    best_model_name = max(results, key=lambda k: results[k]['metrics']['f1_weighted'])
    best_model = results[best_model_name]['model']
    best_metrics = results[best_model_name]['metrics']
    best_predictions = results[best_model_name]['predictions']

    print(f"\n*** Best Model: {best_model_name} (F1: {best_metrics['f1_weighted']:.4f}) ***")

    # Cross-validation
    cv_results = cross_validate_best_model(best_model, X, y)

    # Feature importance
    preprocessor = best_model.named_steps['preprocessor']
    feature_names = numeric_cols.copy()

    if categorical_cols:
        cat_encoder = preprocessor.named_transformers_['cat']
        cat_features = cat_encoder.get_feature_names_out(categorical_cols).tolist()
        feature_names.extend(cat_features)

    importance_df = analyze_health_factors(best_model, feature_names)

    # Source-specific analysis
    source_results = analyze_source_performance(df, best_model, X, y)

    # Per-class metrics
    classes = HEALTH_STATUS_ORDER
    per_class_metrics = analyze_confusion_by_class(y_test, best_predictions, classes)

    # Save model
    metadata = {
        'model_type': best_model_name,
        'classes': classes,
        'features': {
            'numeric': numeric_cols,
            'categorical': categorical_cols
        },
        'training_samples': len(X_train),
        'test_samples': len(X_test),
        'metrics': {
            'accuracy': best_metrics['accuracy'],
            'f1_weighted': best_metrics['f1_weighted'],
            'precision_weighted': best_metrics['precision_weighted'],
            'recall_weighted': best_metrics['recall_weighted']
        },
        'cv_accuracy_mean': float(cv_results['accuracy_scores'].mean()),
        'cv_f1_mean': float(cv_results['f1_scores'].mean()),
        'sources': df['source'].unique().tolist()
    }

    save_model(best_model, 'signal_health_classification', metadata)

    # Save report
    report = {
        'model_comparison': {
            name: {
                'accuracy': res['metrics']['accuracy'],
                'f1_weighted': res['metrics']['f1_weighted'],
                'precision_weighted': res['metrics']['precision_weighted'],
                'recall_weighted': res['metrics']['recall_weighted']
            }
            for name, res in results.items()
        },
        'best_model': best_model_name,
        'best_metrics': {
            'accuracy': best_metrics['accuracy'],
            'f1_weighted': best_metrics['f1_weighted'],
            'confusion_matrix': best_metrics['confusion_matrix']
        },
        'cross_validation': {
            'folds': 5,
            'accuracy_mean': float(cv_results['accuracy_scores'].mean()),
            'accuracy_std': float(cv_results['accuracy_scores'].std()),
            'f1_mean': float(cv_results['f1_scores'].mean()),
            'f1_std': float(cv_results['f1_scores'].std())
        },
        'per_class_metrics': per_class_metrics,
        'source_analysis': source_results,
        'feature_importance': importance_df.to_dict('records') if not importance_df.empty else [],
        'dataset_info': {
            'total_samples': len(df),
            'features': len(numeric_cols) + len(categorical_cols),
            'sources': df['source'].unique().tolist(),
            'class_distribution': y.value_counts().to_dict()
        }
    }

    save_report(report, 'signal_health')

    print("\n" + "="*60)
    print("  Training Complete!")
    print("="*60)
    print(f"  Model: models/signal_health_classification.joblib")
    print(f"  Report: reports/signal_health_report.json")
    print("="*60)


if __name__ == "__main__":
    main()
