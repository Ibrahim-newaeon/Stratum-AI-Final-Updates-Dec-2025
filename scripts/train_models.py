#!/usr/bin/env python3
"""
Train ML models from warehouse data.
Loads data from PostgreSQL warehouse schema and trains all ML models.
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

import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment
load_dotenv(backend_path / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL_SYNC",
    "postgresql://stratum:password@localhost:5432/stratum_ai"
)

def load_warehouse_data():
    """Load data from warehouse schema."""
    print("=" * 70)
    print("Stratum AI - ML Model Training Pipeline")
    print("=" * 70)
    print()

    print("Connecting to database...")
    engine = create_engine(DATABASE_URL)

    # Load fact_daily from warehouse
    query1 = """
    SELECT
        date,
        campaign_id,
        platform,
        spend,
        impressions,
        clicks,
        conversions_total as conversions,
        revenue,
        geo
    FROM warehouse.fact_daily
    WHERE spend > 0 AND impressions > 0
    """

    print("Loading training data from warehouse.fact_daily...")
    df1 = pd.read_sql(query1, engine)
    print(f"   Loaded {len(df1):,} rows from fact_daily")

    # Load ROAS predictor dataset if available
    query2 = """
    SELECT
        date,
        campaign_id,
        platform,
        spend_usd as spend,
        impressions,
        clicks,
        conversions_total as conversions,
        revenue_usd as revenue,
        geo,
        label_next_7d_roas
    FROM warehouse.stratumai_roas_predictor_dataset_18k_gcc
    WHERE spend_usd > 0 AND impressions > 0
    """

    try:
        print("Loading training data from warehouse.stratumai_roas_predictor_dataset_18k_gcc...")
        df2 = pd.read_sql(query2, engine)
        print(f"   Loaded {len(df2):,} rows from ROAS predictor dataset")

        # Combine datasets
        df = pd.concat([df1, df2], ignore_index=True)
        print(f"   Combined total: {len(df):,} rows")
    except Exception as e:
        print(f"   ROAS predictor table not found, using fact_daily only")
        df = df1

    # Show data summary
    print()
    print("Data Summary:")
    print(f"   Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"   Platforms: {df['platform'].unique().tolist()}")
    print(f"   Campaigns: {df['campaign_id'].nunique()}")
    if 'geo' in df.columns:
        geos = df['geo'].dropna().unique().tolist()
        if geos:
            print(f"   Geos: {geos}")

    return df

def train_models(df: pd.DataFrame, models_path: str = None):
    """Train all ML models."""
    from app.ml.train import ModelTrainer

    if models_path is None:
        models_path = backend_path / "models"

    print()
    print("-" * 70)
    print("Training ML Models")
    print("-" * 70)
    print()

    trainer = ModelTrainer(str(models_path))
    results = trainer.train_all(df)

    return results

def main():
    # Load data from warehouse
    df = load_warehouse_data()

    if len(df) == 0:
        print("ERROR: No data found in warehouse. Run load_datasets.py first.")
        return

    # Train models
    results = train_models(df)

    # Print results
    print()
    print("=" * 70)
    print("Training Complete!")
    print("=" * 70)
    print()

    for model_name, metrics in results.items():
        print(f"Model: {model_name}")
        if isinstance(metrics, dict):
            if "error" in metrics:
                print(f"   ERROR: {metrics['error']}")
            else:
                print(f"   R2 Score: {metrics.get('r2', 0):.4f}")
                print(f"   MAE: {metrics.get('mae', 0):.4f}")
                print(f"   RMSE: {metrics.get('rmse', 0):.4f}")
                if 'cv_r2_mean' in metrics:
                    print(f"   CV R2 (mean): {metrics['cv_r2_mean']:.4f} +/- {metrics.get('cv_r2_std', 0):.4f}")
                if 'spend_elasticity' in metrics:
                    print(f"   Spend Elasticity: {metrics['spend_elasticity']:.4f}")
        print()

    print("Models saved to backend/models/")
    print()
    print("Available models:")
    print("   - roas_predictor.pkl (ROAS prediction)")
    print("   - conversion_predictor.pkl (Conversion prediction)")
    print("   - budget_impact.pkl (Budget impact analysis)")

if __name__ == "__main__":
    main()
