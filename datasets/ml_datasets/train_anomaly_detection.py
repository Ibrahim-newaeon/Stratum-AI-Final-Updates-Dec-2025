"""
Anomaly Detection Model Training Script

Trains models to detect anomalies in time-series marketing metrics:
- Spend anomalies (sudden spikes or drops)
- Performance anomalies (unusual ROAS, CTR, conversion patterns)
- Trend breaks (significant changes in metric direction)

Anomaly types:
- spike: Sudden increase above normal range
- drop: Sudden decrease below normal range
- trend_break: Change in underlying trend direction

Models trained:
- Isolation Forest (primary - unsupervised)
- Random Forest Classifier (supervised comparison)
- One-Class SVM (unsupervised comparison)
"""

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.svm import OneClassSVM
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml_utils import (
    load_dataset, save_model, save_report,
    get_feature_columns, create_preprocessor,
    evaluate_classification, print_classification_metrics,
    get_feature_importance
)


def prepare_data(df: pd.DataFrame):
    """Prepare features and target for anomaly detection."""
    # Sort by date
    df = df.sort_values('date').reset_index(drop=True)

    # Define target and columns to exclude
    exclude_cols = ['date', 'is_anomaly', 'anomaly_type']

    # Get feature columns
    numeric_cols, categorical_cols = get_feature_columns(df, exclude_cols)

    print(f"Numeric features ({len(numeric_cols)}): {numeric_cols}")
    print(f"Categorical features ({len(categorical_cols)}): {categorical_cols}")

    # Prepare features
    X = df[numeric_cols + categorical_cols]
    y = df['is_anomaly']
    anomaly_types = df['anomaly_type']

    # Print statistics
    anomaly_rate = y.mean()
    print(f"\nAnomaly rate: {anomaly_rate:.2%}")

    print(f"\nAnomaly Type Distribution:")
    type_dist = anomaly_types[y == 1].value_counts()
    for atype, count in type_dist.items():
        print(f"  {atype:<15}: {count:>3} ({count/y.sum()*100:.1f}%)")

    return X, y, anomaly_types, numeric_cols, categorical_cols


def train_isolation_forest(X_train, X_test, y_test, numeric_cols):
    """Train Isolation Forest (unsupervised anomaly detection)."""
    print("\nTraining Isolation Forest (Unsupervised)...")

    # Isolation Forest works with numeric features
    scaler = StandardScaler()
    X_train_numeric = X_train[numeric_cols]
    X_test_numeric = X_test[numeric_cols]

    X_train_scaled = scaler.fit_transform(X_train_numeric)
    X_test_scaled = scaler.transform(X_test_numeric)

    # Contamination is the expected proportion of anomalies
    # We estimate this from training data
    iso_forest = IsolationForest(
        n_estimators=200,
        contamination=0.05,  # Expect ~5% anomalies
        max_samples='auto',
        random_state=42,
        n_jobs=-1
    )

    iso_forest.fit(X_train_scaled)

    # Predict: -1 for anomaly, 1 for normal
    y_pred_raw = iso_forest.predict(X_test_scaled)
    y_pred = (y_pred_raw == -1).astype(int)  # Convert to 0/1

    # Get anomaly scores (lower = more anomalous)
    anomaly_scores = iso_forest.decision_function(X_test_scaled)

    metrics = evaluate_classification(y_test, y_pred)
    print_classification_metrics(metrics, "Isolation Forest")

    return {
        'model': iso_forest,
        'scaler': scaler,
        'predictions': y_pred,
        'anomaly_scores': anomaly_scores,
        'metrics': metrics,
        'features': numeric_cols
    }


def train_supervised_classifier(X_train, X_test, y_train, y_test, numeric_cols, categorical_cols):
    """Train supervised Random Forest for anomaly classification."""
    print("\nTraining Random Forest Classifier (Supervised)...")

    preprocessor = create_preprocessor(numeric_cols, categorical_cols)

    rf_pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_split=5,
            class_weight='balanced',  # Handle imbalanced classes
            random_state=42,
            n_jobs=-1
        ))
    ])

    rf_pipeline.fit(X_train, y_train)

    y_pred = rf_pipeline.predict(X_test)
    y_prob = rf_pipeline.predict_proba(X_test)

    metrics = evaluate_classification(y_test, y_pred, y_prob)
    print_classification_metrics(metrics, "Random Forest Classifier")

    return {
        'model': rf_pipeline,
        'predictions': y_pred,
        'probabilities': y_prob,
        'metrics': metrics
    }


def train_one_class_svm(X_train, X_test, y_train, y_test, numeric_cols):
    """Train One-Class SVM (unsupervised, trained on normal data only)."""
    print("\nTraining One-Class SVM (Unsupervised)...")

    scaler = StandardScaler()
    X_train_numeric = X_train[numeric_cols]
    X_test_numeric = X_test[numeric_cols]

    # Train only on normal samples
    X_train_normal = X_train_numeric[y_train == 0]
    X_train_scaled = scaler.fit_transform(X_train_normal)
    X_test_scaled = scaler.transform(X_test_numeric)

    oc_svm = OneClassSVM(
        kernel='rbf',
        gamma='auto',
        nu=0.05  # Expected proportion of anomalies
    )

    oc_svm.fit(X_train_scaled)

    # Predict: -1 for anomaly, 1 for normal
    y_pred_raw = oc_svm.predict(X_test_scaled)
    y_pred = (y_pred_raw == -1).astype(int)

    metrics = evaluate_classification(y_test, y_pred)
    print_classification_metrics(metrics, "One-Class SVM")

    return {
        'model': oc_svm,
        'scaler': scaler,
        'predictions': y_pred,
        'metrics': metrics,
        'features': numeric_cols
    }


def analyze_anomaly_patterns(df, y_test, y_pred, anomaly_types_test):
    """Analyze detected anomalies by type and pattern."""
    print("\n" + "="*60)
    print("  Anomaly Detection Analysis")
    print("="*60)

    # True positives - correctly detected anomalies
    true_positives = (y_test == 1) & (y_pred == 1)
    false_negatives = (y_test == 1) & (y_pred == 0)
    false_positives = (y_test == 0) & (y_pred == 1)

    print(f"\n  Detection Summary:")
    print(f"    True Positives:  {true_positives.sum():>3} (correctly detected anomalies)")
    print(f"    False Negatives: {false_negatives.sum():>3} (missed anomalies)")
    print(f"    False Positives: {false_positives.sum():>3} (false alarms)")

    # Detection rate by anomaly type
    print(f"\n  Detection Rate by Anomaly Type:")
    anomaly_mask = y_test == 1

    if anomaly_mask.sum() > 0:
        types_actual = anomaly_types_test[anomaly_mask]
        types_detected = anomaly_types_test[true_positives]

        for atype in ['spike', 'drop', 'trend_break']:
            actual_count = (types_actual == atype).sum()
            detected_count = (types_detected == atype).sum()
            if actual_count > 0:
                rate = detected_count / actual_count
                print(f"    {atype:<15}: {detected_count:>2}/{actual_count:<2} ({rate:.1%})")

    return {
        'true_positives': int(true_positives.sum()),
        'false_negatives': int(false_negatives.sum()),
        'false_positives': int(false_positives.sum())
    }


def analyze_feature_importance(model, feature_names):
    """Analyze feature importance for supervised model."""
    print("\n" + "="*60)
    print("  Top Anomaly Detection Features")
    print("="*60)

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
    print("  ANOMALY DETECTION MODEL TRAINING")
    print("="*60)

    # Load data
    print("\nLoading dataset...")
    df = load_dataset('anomaly_detection_dataset.csv')
    print(f"Dataset shape: {df.shape}")

    # Prepare data
    X, y, anomaly_types, numeric_cols, categorical_cols = prepare_data(df)

    # Split data with stratification
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Also split anomaly types for analysis
    _, anomaly_types_test = train_test_split(
        anomaly_types, test_size=0.2, random_state=42, stratify=y
    )

    print(f"\nTrain set: {len(X_train)} samples ({y_train.mean():.2%} anomalies)")
    print(f"Test set: {len(X_test)} samples ({y_test.mean():.2%} anomalies)")

    # Train models
    results = {}

    # 1. Isolation Forest (Unsupervised)
    results['isolation_forest'] = train_isolation_forest(
        X_train, X_test, y_test, numeric_cols
    )

    # 2. Random Forest Classifier (Supervised)
    results['random_forest'] = train_supervised_classifier(
        X_train, X_test, y_train, y_test, numeric_cols, categorical_cols
    )

    # 3. One-Class SVM (Unsupervised)
    results['one_class_svm'] = train_one_class_svm(
        X_train, X_test, y_train, y_test, numeric_cols
    )

    # Compare models
    print("\n" + "="*60)
    print("  Model Comparison (on test set)")
    print("="*60)
    print(f"  {'Model':<25} | {'Precision':>10} | {'Recall':>10} | {'F1':>10}")
    print(f"  {'-'*25}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}")

    for name, res in results.items():
        m = res['metrics']
        precision = m.get('precision_binary', m['precision_weighted'])
        recall = m.get('recall_binary', m['recall_weighted'])
        f1 = m.get('f1_binary', m['f1_weighted'])
        print(f"  {name:<25} | {precision:>10.4f} | {recall:>10.4f} | {f1:>10.4f}")

    # Select best model based on F1 score (balance precision/recall for anomaly detection)
    best_model_name = max(results, key=lambda k: results[k]['metrics'].get('f1_binary', results[k]['metrics']['f1_weighted']))
    best_result = results[best_model_name]
    best_metrics = best_result['metrics']

    print(f"\n*** Best Model: {best_model_name} ***")

    # Analyze anomaly patterns with best model
    detection_analysis = analyze_anomaly_patterns(
        df, y_test.values, best_result['predictions'], anomaly_types_test.values
    )

    # Feature importance (for supervised model)
    preprocessor = results['random_forest']['model'].named_steps['preprocessor']
    feature_names = numeric_cols.copy()

    if categorical_cols:
        cat_encoder = preprocessor.named_transformers_['cat']
        cat_features = cat_encoder.get_feature_names_out(categorical_cols).tolist()
        feature_names.extend(cat_features)

    importance_df = analyze_feature_importance(results['random_forest']['model'], feature_names)

    # Save Isolation Forest (primary unsupervised model)
    iso_metadata = {
        'model_type': 'isolation_forest',
        'approach': 'unsupervised',
        'features': numeric_cols,
        'contamination': 0.05,
        'training_samples': len(X_train),
        'test_samples': len(X_test),
        'metrics': {
            'precision': results['isolation_forest']['metrics'].get('precision_binary', 0),
            'recall': results['isolation_forest']['metrics'].get('recall_binary', 0),
            'f1': results['isolation_forest']['metrics'].get('f1_binary', 0)
        }
    }

    # Save model with scaler
    import joblib
    from ml_utils import MODELS_DIR, setup_directories
    setup_directories()

    joblib.dump({
        'model': results['isolation_forest']['model'],
        'scaler': results['isolation_forest']['scaler'],
        'features': numeric_cols
    }, MODELS_DIR / 'anomaly_isolation_forest.joblib')

    save_model(
        results['random_forest']['model'],
        'anomaly_supervised',
        {
            'model_type': 'random_forest',
            'approach': 'supervised',
            'features': {'numeric': numeric_cols, 'categorical': categorical_cols},
            'metrics': {
                'precision': results['random_forest']['metrics'].get('precision_binary', 0),
                'recall': results['random_forest']['metrics'].get('recall_binary', 0),
                'f1': results['random_forest']['metrics'].get('f1_binary', 0),
                'roc_auc': results['random_forest']['metrics'].get('roc_auc', 0)
            }
        }
    )

    # Save comprehensive report
    report = {
        'model_comparison': {
            name: {
                'precision': res['metrics'].get('precision_binary', res['metrics']['precision_weighted']),
                'recall': res['metrics'].get('recall_binary', res['metrics']['recall_weighted']),
                'f1': res['metrics'].get('f1_binary', res['metrics']['f1_weighted']),
                'accuracy': res['metrics']['accuracy']
            }
            for name, res in results.items()
        },
        'best_model': best_model_name,
        'detection_analysis': detection_analysis,
        'feature_importance': importance_df.to_dict('records') if not importance_df.empty else [],
        'anomaly_types': ['spike', 'drop', 'trend_break'],
        'dataset_info': {
            'total_samples': len(df),
            'features': len(numeric_cols) + len(categorical_cols),
            'anomaly_rate': float(y.mean()),
            'anomaly_distribution': anomaly_types[y == 1].value_counts().to_dict()
        },
        'recommendations': {
            'unsupervised': 'Use Isolation Forest for real-time anomaly detection without labels',
            'supervised': 'Use Random Forest when historical anomaly labels are available',
            'threshold': 'Adjust contamination/nu parameter based on acceptable false positive rate'
        }
    }

    save_report(report, 'anomaly_detection')

    print("\n" + "="*60)
    print("  Training Complete!")
    print("="*60)
    print(f"  Isolation Forest: models/anomaly_isolation_forest.joblib")
    print(f"  Supervised Model: models/anomaly_supervised.joblib")
    print(f"  Report: reports/anomaly_detection_report.json")
    print("="*60)


if __name__ == "__main__":
    main()
