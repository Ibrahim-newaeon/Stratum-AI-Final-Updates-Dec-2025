# Stratum AI - ML Training Datasets & Scripts

This directory contains training datasets and scripts for Stratum AI's predictive models.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Train all models
python train_churn_prediction.py
python train_ltv_prediction.py
python train_campaign_performance.py
python train_signal_health.py
python train_anomaly_detection.py
```

## Datasets

| Dataset | Records | Target | Use Case |
|---------|---------|--------|----------|
| `churn_prediction_dataset.csv` | 10,000 | churned (0/1) | Predict customer churn |
| `ltv_prediction_dataset.csv` | 10,000 | ltv_12_months | Predict 12-month LTV |
| `campaign_performance_dataset.csv` | 15,000 | roas, cpa | Predict campaign ROAS/CPA |
| `signal_health_dataset.csv` | 1,825 | health_status | Classify signal health |
| `anomaly_detection_dataset.csv` | 365 | is_anomaly | Detect metric anomalies |

See `data_dictionary.csv` for detailed field definitions.

## Training Scripts

### 1. Churn Prediction (`train_churn_prediction.py`)
Predicts which customers are likely to churn based on engagement, transactions, and support metrics.

**Models:** Random Forest, Gradient Boosting, Logistic Regression

**Output:**
- `models/churn_prediction.joblib`
- `reports/churn_prediction_report.json`

### 2. LTV Prediction (`train_ltv_prediction.py`)
Predicts 12-month customer lifetime value using RFM analysis and behavioral data.

**Models:** Gradient Boosting, Random Forest, Ridge Regression

**Output:**
- `models/ltv_prediction.joblib`
- `reports/ltv_prediction_report.json`

### 3. Campaign Performance (`train_campaign_performance.py`)
Predicts ROAS and CPA for ad campaigns across Meta, Google, TikTok, and Snapchat.

**Models:** Gradient Boosting, Random Forest

**Output:**
- `models/campaign_roas_prediction.joblib`
- `models/campaign_cpa_prediction.joblib`
- `reports/campaign_performance_report.json`

### 4. Signal Health (`train_signal_health.py`)
Classifies data signal health status (healthy, risk, degraded, critical).

**Models:** Random Forest, Gradient Boosting, Logistic Regression

**Output:**
- `models/signal_health_classification.joblib`
- `reports/signal_health_report.json`

### 5. Anomaly Detection (`train_anomaly_detection.py`)
Detects anomalies in time-series marketing metrics (spikes, drops, trend breaks).

**Models:** Isolation Forest (unsupervised), Random Forest (supervised), One-Class SVM

**Output:**
- `models/anomaly_isolation_forest.joblib`
- `models/anomaly_supervised.joblib`
- `reports/anomaly_detection_report.json`

## Shared Utilities (`ml_utils.py`)

Common functions for all training scripts:
- `load_dataset()` - Load CSV datasets
- `save_model()` / `load_model()` - Model persistence with metadata
- `create_preprocessor()` - Feature preprocessing pipeline
- `evaluate_classification()` / `evaluate_regression()` - Metrics calculation
- `get_feature_importance()` - Extract feature importance from models

## Directory Structure

```
ml_datasets/
├── README.md                           # This file
├── requirements.txt                    # Python dependencies
├── ml_utils.py                         # Shared utilities
├── generate_ml_datasets.py             # Dataset generation script
├── data_dictionary.csv                 # Field definitions
│
├── train_churn_prediction.py           # Churn model training
├── train_ltv_prediction.py             # LTV model training
├── train_campaign_performance.py       # Campaign model training
├── train_signal_health.py              # Signal health training
├── train_anomaly_detection.py          # Anomaly detection training
│
├── churn_prediction_dataset.csv        # Training data
├── ltv_prediction_dataset.csv
├── campaign_performance_dataset.csv
├── signal_health_dataset.csv
├── anomaly_detection_dataset.csv
│
├── models/                             # Trained models (after training)
│   ├── churn_prediction.joblib
│   ├── ltv_prediction.joblib
│   └── ...
│
└── reports/                            # Training reports (after training)
    ├── churn_prediction_report.json
    └── ...
```

## Model Integration

To use trained models in the Stratum backend:

```python
import joblib

# Load model with metadata
model, metadata = load_model('churn_prediction')

# Make predictions
predictions = model.predict(new_data)
probabilities = model.predict_proba(new_data)

# Check model info
print(f"Model type: {metadata['model_type']}")
print(f"Features: {metadata['features']}")
print(f"ROC-AUC: {metadata['metrics']['roc_auc']}")
```

## Regenerating Datasets

To regenerate synthetic training data:

```bash
python generate_ml_datasets.py
```

This will overwrite existing datasets with fresh synthetic data.

## Performance Benchmarks

| Model | Primary Metric | Value |
|-------|---------------|-------|
| Churn Prediction | ROC-AUC | ~0.85-0.90 |
| LTV Prediction | R² | ~0.75-0.85 |
| Campaign ROAS | R² | ~0.70-0.80 |
| Signal Health | F1 (weighted) | ~0.90-0.95 |
| Anomaly Detection | F1 | ~0.70-0.80 |

*Actual metrics depend on random seed and data characteristics.*
