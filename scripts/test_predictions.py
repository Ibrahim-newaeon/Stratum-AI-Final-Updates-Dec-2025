#!/usr/bin/env python3
"""
Test ML model predictions with sample data.
"""

import os
import sys
from pathlib import Path

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import json
import numpy as np
import joblib

MODELS_PATH = backend_path / "models"

def load_model_and_scaler(model_name):
    """Load model and its scaler."""
    model = joblib.load(MODELS_PATH / f"{model_name}.pkl")

    scaler_path = MODELS_PATH / f"{model_name}_scaler.pkl"
    scaler = joblib.load(scaler_path) if scaler_path.exists() else None

    with open(MODELS_PATH / f"{model_name}_metadata.json") as f:
        metadata = json.load(f)

    return model, scaler, metadata

def predict_roas(spend, impressions, clicks, platform="Meta"):
    """Predict ROAS for a campaign."""
    model, scaler, metadata = load_model_and_scaler("roas_predictor")

    # Calculate derived features
    log_spend = np.log1p(spend)
    log_impressions = np.log1p(impressions)
    log_clicks = np.log1p(clicks)
    ctr = (clicks / impressions * 100) if impressions > 0 else 0
    cpm = (spend / impressions * 1000) if impressions > 0 else 0

    # Platform one-hot encoding
    platforms = ["Google Ads", "Meta", "Snapchat", "TikTok"]
    platform_features = [1 if p == platform else 0 for p in platforms]

    # Build feature vector (order must match training)
    features = [log_spend, log_impressions, log_clicks, ctr, cpm] + platform_features
    X = np.array([features])

    # Scale and predict
    if scaler:
        X = scaler.transform(X)

    prediction = model.predict(X)[0]
    return max(0, prediction)  # ROAS can't be negative

def predict_conversions(spend, impressions, clicks, platform="Meta"):
    """Predict conversions for a campaign."""
    model, scaler, metadata = load_model_and_scaler("conversion_predictor")

    # Calculate derived features
    log_spend = np.log1p(spend)
    log_impressions = np.log1p(impressions)
    log_clicks = np.log1p(clicks)
    ctr = (clicks / impressions * 100) if impressions > 0 else 0
    cpc = (spend / clicks) if clicks > 0 else 0

    # Platform one-hot encoding
    platforms = ["Google Ads", "Meta", "Snapchat", "TikTok"]
    platform_features = [1 if p == platform else 0 for p in platforms]

    # Build feature vector
    features = [log_spend, log_impressions, log_clicks, ctr, cpc] + platform_features
    X = np.array([features])

    # Scale and predict
    if scaler:
        X = scaler.transform(X)

    prediction = model.predict(X)[0]
    return max(0, int(round(prediction)))  # Conversions must be non-negative integer

def predict_budget_impact(current_spend, new_spend):
    """Predict revenue change from budget change."""
    model, scaler, metadata = load_model_and_scaler("budget_impact")

    # Predict log revenue for both spend levels
    log_current = np.log1p(current_spend)
    log_new = np.log1p(new_spend)

    current_revenue = np.expm1(model.predict([[log_current]])[0])
    new_revenue = np.expm1(model.predict([[log_new]])[0])

    return {
        "current_revenue": max(0, current_revenue),
        "new_revenue": max(0, new_revenue),
        "revenue_change": new_revenue - current_revenue,
        "revenue_change_pct": ((new_revenue - current_revenue) / current_revenue * 100) if current_revenue > 0 else 0
    }

def main():
    print("=" * 70)
    print("Stratum AI - ML Model Prediction Tests")
    print("=" * 70)
    print()

    # Test scenarios
    test_campaigns = [
        {"name": "Meta - Small Budget", "spend": 500, "impressions": 50000, "clicks": 750, "platform": "Meta"},
        {"name": "Meta - Medium Budget", "spend": 2000, "impressions": 200000, "clicks": 3000, "platform": "Meta"},
        {"name": "Google - High Intent", "spend": 1500, "impressions": 30000, "clicks": 1500, "platform": "Google Ads"},
        {"name": "TikTok - Awareness", "spend": 1000, "impressions": 150000, "clicks": 1200, "platform": "TikTok"},
        {"name": "Snapchat - Youth", "spend": 800, "impressions": 100000, "clicks": 800, "platform": "Snapchat"},
    ]

    print("-" * 70)
    print("1. ROAS Predictions")
    print("-" * 70)
    print()
    print(f"{'Campaign':<25} {'Spend':>10} {'Impressions':>12} {'Clicks':>8} {'Pred ROAS':>10}")
    print("-" * 70)

    for camp in test_campaigns:
        roas = predict_roas(camp["spend"], camp["impressions"], camp["clicks"], camp["platform"])
        print(f"{camp['name']:<25} ${camp['spend']:>9,} {camp['impressions']:>12,} {camp['clicks']:>8,} {roas:>10.2f}x")

    print()
    print("-" * 70)
    print("2. Conversion Predictions")
    print("-" * 70)
    print()
    print(f"{'Campaign':<25} {'Spend':>10} {'Clicks':>8} {'CTR':>8} {'Pred Conv':>10}")
    print("-" * 70)

    for camp in test_campaigns:
        conversions = predict_conversions(camp["spend"], camp["impressions"], camp["clicks"], camp["platform"])
        ctr = camp["clicks"] / camp["impressions"] * 100
        print(f"{camp['name']:<25} ${camp['spend']:>9,} {camp['clicks']:>8,} {ctr:>7.2f}% {conversions:>10,}")

    print()
    print("-" * 70)
    print("3. Budget Impact Analysis")
    print("-" * 70)
    print()

    budget_scenarios = [
        {"current": 1000, "new": 1500, "label": "50% increase"},
        {"current": 1000, "new": 2000, "label": "100% increase"},
        {"current": 2000, "new": 1500, "label": "25% decrease"},
        {"current": 5000, "new": 7500, "label": "50% increase (high budget)"},
    ]

    print(f"{'Scenario':<25} {'Current $':>12} {'New $':>12} {'Rev Change':>15} {'Change %':>10}")
    print("-" * 70)

    for scenario in budget_scenarios:
        impact = predict_budget_impact(scenario["current"], scenario["new"])
        print(f"{scenario['label']:<25} ${scenario['current']:>11,} ${scenario['new']:>11,} ${impact['revenue_change']:>14,.2f} {impact['revenue_change_pct']:>9.1f}%")

    print()
    print("=" * 70)
    print("All predictions completed successfully!")
    print("=" * 70)

if __name__ == "__main__":
    main()
