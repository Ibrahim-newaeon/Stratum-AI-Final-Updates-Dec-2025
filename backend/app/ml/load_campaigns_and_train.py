# =============================================================================
# Stratum AI - Load Campaigns from Dataset & Train ML Models
# =============================================================================
"""
Script to:
1. Load 100 campaigns from synthetic_roas_meta_10k.csv
2. Create campaign records with targeting, creatives, and metrics
3. Train ML models on the dataset
"""

import asyncio
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

import pandas as pd
from sqlalchemy import select

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.core.logging import get_logger
from app.db.session import async_session_factory
from app.models import (
    AdPlatform,
    AssetType,
    Campaign,
    CampaignMetric,
    CampaignStatus,
    CreativeAsset,
    Tenant,
)

logger = get_logger(__name__)

# Dataset path
DATASET_PATH = Path(__file__).parent.parent.parent.parent.parent.parent / "Datasets" / "synthetic_roas_meta_10k.csv"

# Objective to status mapping
OBJECTIVE_TO_STATUS = {
    "OUTCOME_SALES": CampaignStatus.ACTIVE,
    "OUTCOME_LEADS": CampaignStatus.ACTIVE,
    "OUTCOME_TRAFFIC": CampaignStatus.ACTIVE,
    "OUTCOME_ENGAGEMENT": CampaignStatus.ACTIVE,
}

# Creative types to asset types
CREATIVE_TO_ASSET = {
    "UGC": AssetType.VIDEO,
    "Product": AssetType.IMAGE,
    "Lifestyle": AssetType.IMAGE,
    "Testimonial": AssetType.VIDEO,
    "Offer/Discount": AssetType.IMAGE,
}


async def load_campaigns_from_dataset(
    num_campaigns: int = 100,
    tenant_id: int = None,
) -> Dict:
    """
    Load campaigns from the synthetic ROAS Meta dataset.

    Args:
        num_campaigns: Number of campaigns to create
        tenant_id: Tenant ID to associate campaigns with

    Returns:
        Summary of loaded data
    """
    # Check if dataset exists
    if not DATASET_PATH.exists():
        print(f"Dataset not found at: {DATASET_PATH}")
        print("Looking for alternative paths...")
        alt_paths = [
            Path("C:/Users/Vip/OneDrive/Desktop/Stratum-AI-Final-Updates-Dec-2025-main/Datasets/synthetic_roas_meta_10k.csv"),
            Path("./Datasets/synthetic_roas_meta_10k.csv"),
        ]
        for alt in alt_paths:
            if alt.exists():
                global DATASET_PATH
                DATASET_PATH = alt
                break
        else:
            raise FileNotFoundError(f"Dataset not found. Tried: {DATASET_PATH}")

    print(f"Loading dataset from: {DATASET_PATH}")
    df = pd.read_csv(DATASET_PATH)
    print(f"Dataset loaded: {len(df)} rows, {len(df.columns)} columns")

    async with async_session_factory() as db:
        # Get or create tenant
        if tenant_id is None:
            result = await db.execute(select(Tenant).limit(1))
            tenant = result.scalar_one_or_none()
            if not tenant:
                tenant = Tenant(
                    name="Stratum Demo",
                    slug="stratum-demo",
                    settings={},
                )
                db.add(tenant)
                await db.flush()
            tenant_id = tenant.id
            print(f"Using tenant: {tenant_id}")

        # Group by campaign_id to aggregate
        campaign_groups = df.groupby("campaign_id")
        campaign_ids = list(campaign_groups.groups.keys())

        # Select random campaigns
        selected_campaigns = random.sample(campaign_ids, min(num_campaigns, len(campaign_ids)))
        print(f"Selected {len(selected_campaigns)} campaigns to create")

        campaigns_created = 0
        metrics_created = 0
        assets_created = 0

        for campaign_id in selected_campaigns:
            group = campaign_groups.get_group(campaign_id)
            first_row = group.iloc[0]

            # Parse objective
            objective = first_row.get("objective", "OUTCOME_SALES")
            status = OBJECTIVE_TO_STATUS.get(objective, CampaignStatus.ACTIVE)

            # Calculate aggregated metrics
            total_spend = int(group["spend"].sum() * 100)  # Convert to cents
            total_revenue = int(group["revenue"].sum() * 100)
            total_impressions = int(group["impressions"].sum())
            total_clicks = int(group["clicks"].sum())
            total_conversions = int(group["conversions"].sum())
            total_leads = int(group["leads"].sum())
            total_purchases = int(group["purchases"].sum())

            # Calculate derived metrics
            ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
            cpc = int(total_spend / total_clicks) if total_clicks > 0 else 0
            cpm = int(total_spend / total_impressions * 1000) if total_impressions > 0 else 0
            cpa = int(total_spend / total_conversions) if total_conversions > 0 else 0
            roas = (total_revenue / total_spend) if total_spend > 0 else 0

            # Targeting info
            geo = first_row.get("geo", "US")
            age_min = int(first_row.get("age_min", 18))
            age_max = int(first_row.get("age_max", 65))
            gender = first_row.get("gender", "all")
            audience_type = first_row.get("audience_type", "Broad")

            # Generate campaign name
            platform = first_row.get("platform", "Meta")
            creative_type = first_row.get("creative_type", "Product")
            campaign_name = f"{platform} {objective.replace('OUTCOME_', '')} - {geo} - {creative_type}"

            # Check if campaign exists
            existing = await db.execute(
                select(Campaign).where(
                    Campaign.tenant_id == tenant_id,
                    Campaign.external_id == campaign_id,
                )
            )
            if existing.scalar_one_or_none():
                continue

            # Create campaign
            campaign = Campaign(
                tenant_id=tenant_id,
                platform=AdPlatform.META,
                external_id=campaign_id,
                account_id=str(first_row.get("account_id", "10000000001")),
                name=campaign_name,
                status=status,
                objective=objective,
                total_spend_cents=total_spend,
                revenue_cents=total_revenue,
                impressions=total_impressions,
                clicks=total_clicks,
                conversions=total_conversions,
                ctr=round(ctr, 4),
                cpc_cents=cpc,
                cpm_cents=cpm,
                cpa_cents=cpa,
                roas=round(roas, 4),
                currency="USD",
                targeting_age_min=age_min,
                targeting_age_max=age_max,
                targeting_genders=[gender] if gender != "all" else [],
                targeting_locations=[{"name": geo, "type": "country"}],
                targeting_interests=[audience_type],
                start_date=datetime.now(timezone.utc).date() - timedelta(days=30),
                labels=[objective, geo, creative_type, audience_type],
            )
            db.add(campaign)
            await db.flush()
            campaigns_created += 1

            # Create daily metrics
            for _, row in group.iterrows():
                date_str = row.get("date")
                if pd.isna(date_str):
                    metric_date = datetime.now(timezone.utc).date() - timedelta(days=random.randint(1, 30))
                else:
                    try:
                        metric_date = pd.to_datetime(date_str).date()
                    except:
                        metric_date = datetime.now(timezone.utc).date()

                metric = CampaignMetric(
                    tenant_id=tenant_id,
                    campaign_id=campaign.id,
                    date=metric_date,
                    spend_cents=int(row.get("spend", 0) * 100),
                    revenue_cents=int(row.get("revenue", 0) * 100),
                    impressions=int(row.get("impressions", 0)),
                    clicks=int(row.get("clicks", 0)),
                    conversions=int(row.get("conversions", 0)),
                    leads=int(row.get("leads", 0)),
                    purchases=int(row.get("purchases", 0)),
                )
                db.add(metric)
                metrics_created += 1

            # Create creative asset for the campaign
            asset_type = CREATIVE_TO_ASSET.get(creative_type, AssetType.IMAGE)
            format_type = first_row.get("format", "Image")
            fatigue_score = float(first_row.get("fatigue_score", 0)) * 100  # Convert to 0-100

            asset = CreativeAsset(
                tenant_id=tenant_id,
                campaign_id=campaign.id,
                name=f"{creative_type}_{format_type}_{campaign_id[:8]}",
                asset_type=asset_type,
                file_url=f"https://storage.stratum.ai/assets/{campaign_id}/{format_type.lower()}.{'mp4' if asset_type == AssetType.VIDEO else 'jpg'}",
                thumbnail_url=f"https://storage.stratum.ai/assets/{campaign_id}/thumb.jpg",
                fatigue_score=min(100, fatigue_score),
                impressions=total_impressions,
                clicks=total_clicks,
                ctr=round(ctr, 4),
                times_used=random.randint(1, 15),
                first_used_at=datetime.now(timezone.utc) - timedelta(days=random.randint(7, 60)),
                tags=[creative_type, format_type, geo],
                folder=f"campaigns/{geo.lower()}",
            )
            db.add(asset)
            assets_created += 1

        await db.commit()

        print(f"\n{'='*50}")
        print("Campaign Loading Complete!")
        print(f"{'='*50}")
        print(f"Campaigns created: {campaigns_created}")
        print(f"Metrics created: {metrics_created}")
        print(f"Assets created: {assets_created}")

        return {
            "campaigns_created": campaigns_created,
            "metrics_created": metrics_created,
            "assets_created": assets_created,
            "tenant_id": tenant_id,
        }


async def train_ml_models():
    """Train ML models using the dataset."""
    from app.ml.train import train_from_csv

    print("\n" + "=" * 50)
    print("Training ML Models")
    print("=" * 50)

    # Check paths
    if not DATASET_PATH.exists():
        print(f"Dataset not found: {DATASET_PATH}")
        return None

    models_path = Path(__file__).parent.parent / "models"
    models_path.mkdir(parents=True, exist_ok=True)

    print(f"Training from: {DATASET_PATH}")
    print(f"Saving models to: {models_path}")

    results = train_from_csv(str(DATASET_PATH), str(models_path))

    print("\nTraining Results:")
    for model_name, metrics in results.items():
        print(f"\n{model_name}:")
        if isinstance(metrics, dict):
            for key, value in metrics.items():
                if key != "feature_importances":
                    if isinstance(value, float):
                        print(f"  {key}: {value:.4f}")
                    else:
                        print(f"  {key}: {value}")

    return results


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Load campaigns and train ML models")
    parser.add_argument("--campaigns", type=int, default=100, help="Number of campaigns to load")
    parser.add_argument("--train", action="store_true", help="Also train ML models")
    parser.add_argument("--only-train", action="store_true", help="Only train models, don't load campaigns")

    args = parser.parse_args()

    if not args.only_train:
        print("Loading campaigns from dataset...")
        result = await load_campaigns_from_dataset(num_campaigns=args.campaigns)
        print(f"\nLoaded {result['campaigns_created']} campaigns")

    if args.train or args.only_train:
        await train_ml_models()


if __name__ == "__main__":
    asyncio.run(main())
