# =============================================================================
# Stratum AI - Training Data Loader
# =============================================================================
"""
Data loader for importing training datasets from various sources.
Supports CSV files from Kaggle and other public datasets.
"""

import csv
import hashlib
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import (
    AdPlatform,
    Campaign,
    CampaignMetric,
    CampaignStatus,
    Tenant,
)

logger = get_logger(__name__)


class TrainingDataLoader:
    """
    Loads and transforms training data from various sources.

    Supported formats:
    - Facebook/Meta Ads CSV (Kaggle)
    - Google Ads CSV (Kaggle)
    - Generic marketing CSV
    """

    # Column mappings for different dataset formats
    COLUMN_MAPPINGS = {
        "facebook_kaggle": {
            "spent": "spend",
            "total_conversion": "conversions",
            "approved_conversion": "conversions",
            "impressions": "impressions",
            "clicks": "clicks",
            "revenue": "revenue",
            "campaign_id": "external_id",
            "ad_id": "ad_id",
            "age": "targeting_age",
            "gender": "targeting_gender",
            "interest": "targeting_interest",
        },
        "google_kaggle": {
            "Cost": "spend",
            "Conversions": "conversions",
            "Impressions": "impressions",
            "Clicks": "clicks",
            "ConversionValue": "revenue",
            "CampaignId": "external_id",
            "CampaignName": "name",
            "Date": "date",
        },
        "synthetic_roas_meta": {
            # Rich dataset with 40 columns
            "spend": "spend",
            "impressions": "impressions",
            "reach": "reach",
            "frequency": "frequency",
            "clicks": "clicks",
            "link_clicks": "link_clicks",
            "ctr": "ctr",
            "cpc": "cpc",
            "cpm": "cpm",
            "conversions": "conversions",
            "leads": "leads",
            "purchases": "purchases",
            "add_to_cart": "add_to_cart",
            "initiate_checkout": "initiate_checkout",
            "revenue": "revenue",
            "roas": "roas",
            "aov": "aov",
            "cvr": "cvr",
            "atc_rate": "atc_rate",
            "fatigue_score": "fatigue_score",
            "seasonality_index": "seasonality_index",
            "emq_score": "emq_score",
            "pixel_events_received": "pixel_events",
            "target_roas_7d": "target_roas",
            "campaign_id": "external_id",
            "adset_id": "adset_id",
            "ad_id": "ad_id",
            "date": "date",
            "platform": "platform",
            "account_id": "account_id",
            "objective": "objective",
            "optimization_goal": "optimization_goal",
            "placement_group": "placement_group",
            "geo": "geo",
            "age_min": "age_min",
            "age_max": "age_max",
            "gender": "gender",
            "audience_type": "audience_type",
            "creative_type": "creative_type",
            "format": "format",
        },
        "generic": {
            "spend": "spend",
            "cost": "spend",
            "conversions": "conversions",
            "impressions": "impressions",
            "clicks": "clicks",
            "revenue": "revenue",
            "campaign_id": "external_id",
            "campaign_name": "name",
            "date": "date",
            "platform": "platform",
        },
    }

    def __init__(self, db: AsyncSession = None):
        self.db = db

    async def load_csv(
        self,
        file_path: str,
        tenant_id: int,
        platform: AdPlatform = AdPlatform.META,
        dataset_format: str = "generic",
        create_daily_metrics: bool = True,
    ) -> Dict[str, Any]:
        """
        Load training data from a CSV file.

        Args:
            file_path: Path to CSV file
            tenant_id: Tenant ID to associate data with
            platform: Ad platform (meta, google, etc.)
            dataset_format: Format hint (facebook_kaggle, google_kaggle, generic)
            create_daily_metrics: Whether to create daily metric records

        Returns:
            Summary of loaded data
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        # Read CSV
        df = pd.read_csv(file_path)
        logger.info("csv_loaded", rows=len(df), columns=list(df.columns))

        # Detect and apply column mapping
        mapping = self._detect_format(df, dataset_format)
        df = self._apply_mapping(df, mapping)

        # Transform data
        df = self._transform_data(df, platform)

        # Load into database
        stats = await self._load_to_database(
            df, tenant_id, platform, create_daily_metrics
        )

        return {
            "status": "success",
            "file": str(file_path),
            "rows_processed": len(df),
            **stats,
        }

    def _detect_format(self, df: pd.DataFrame, hint: str) -> Dict[str, str]:
        """Detect dataset format based on columns."""
        columns_lower = [c.lower() for c in df.columns]

        # Check for synthetic ROAS Meta format (has rich columns like fatigue_score, emq_score)
        if "fatigue_score" in columns_lower or "emq_score" in columns_lower or "target_roas_7d" in columns_lower:
            return self.COLUMN_MAPPINGS["synthetic_roas_meta"]

        # Check for Facebook/Meta format
        if "spent" in columns_lower or "total_conversion" in columns_lower:
            return self.COLUMN_MAPPINGS["facebook_kaggle"]

        # Check for Google format
        if "cost" in columns_lower and "campaignid" in [c.lower() for c in df.columns]:
            return self.COLUMN_MAPPINGS["google_kaggle"]

        # Use hint or generic
        return self.COLUMN_MAPPINGS.get(hint, self.COLUMN_MAPPINGS["generic"])

    def _apply_mapping(self, df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
        """Apply column mapping to standardize column names."""
        # Create case-insensitive mapping
        column_renames = {}
        for col in df.columns:
            col_lower = col.lower()
            if col_lower in mapping:
                column_renames[col] = mapping[col_lower]
            elif col in mapping:
                column_renames[col] = mapping[col]

        df = df.rename(columns=column_renames)
        return df

    def _transform_data(self, df: pd.DataFrame, platform: AdPlatform) -> pd.DataFrame:
        """Transform and clean data."""
        # Ensure required columns exist
        required = ["spend", "impressions", "clicks"]
        for col in required:
            if col not in df.columns:
                df[col] = 0

        # Convert spend to cents if it looks like dollars
        if "spend" in df.columns:
            if df["spend"].mean() < 1000:  # Likely dollars
                df["spend_cents"] = (df["spend"] * 100).astype(int)
            else:
                df["spend_cents"] = df["spend"].astype(int)

        # Convert revenue to cents
        if "revenue" in df.columns:
            if df["revenue"].mean() < 1000:  # Likely dollars
                df["revenue_cents"] = (df["revenue"] * 100).astype(int)
            else:
                df["revenue_cents"] = df["revenue"].astype(int)
        else:
            # Estimate revenue from conversions if not available
            if "conversions" in df.columns:
                avg_conversion_value = 50  # $50 default
                df["revenue_cents"] = (df["conversions"] * avg_conversion_value * 100).astype(int)
            else:
                df["revenue_cents"] = 0

        # Ensure conversions column
        if "conversions" not in df.columns:
            # Estimate from clicks with 3% conversion rate
            df["conversions"] = (df["clicks"] * 0.03).astype(int)

        # Calculate CTR
        df["ctr"] = df.apply(
            lambda r: (r["clicks"] / r["impressions"] * 100) if r["impressions"] > 0 else 0,
            axis=1
        )

        # Calculate ROAS
        df["roas"] = df.apply(
            lambda r: (r["revenue_cents"] / r["spend_cents"]) if r["spend_cents"] > 0 else 0,
            axis=1
        )

        # Generate campaign IDs if not present
        if "external_id" not in df.columns:
            df["external_id"] = df.index.map(lambda x: f"campaign_{x}")

        # Generate campaign names if not present
        if "name" not in df.columns:
            df["name"] = df["external_id"].map(lambda x: f"Campaign {x}")

        # Parse dates if present
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
        else:
            # Generate dates for time series
            base_date = date.today() - timedelta(days=len(df))
            df["date"] = [base_date + timedelta(days=i) for i in range(len(df))]

        # Add platform
        df["platform"] = platform.value

        return df

    async def _load_to_database(
        self,
        df: pd.DataFrame,
        tenant_id: int,
        platform: AdPlatform,
        create_daily_metrics: bool,
    ) -> Dict[str, int]:
        """Load transformed data into database."""
        if self.db is None:
            logger.warning("no_database_session_skipping_db_load")
            return {"campaigns_created": 0, "metrics_created": 0}

        campaigns_created = 0
        metrics_created = 0

        # Group by campaign if there are multiple rows per campaign
        if "external_id" in df.columns:
            campaign_groups = df.groupby("external_id")
        else:
            campaign_groups = [(i, df.iloc[[i]]) for i in range(len(df))]

        for external_id, group in campaign_groups:
            # Aggregate campaign-level metrics
            campaign_data = {
                "tenant_id": tenant_id,
                "platform": platform,
                "external_id": str(external_id),
                "account_id": f"training_account_{tenant_id}",
                "name": group["name"].iloc[0] if "name" in group.columns else f"Campaign {external_id}",
                "status": CampaignStatus.COMPLETED,
                "total_spend_cents": int(group["spend_cents"].sum()),
                "impressions": int(group["impressions"].sum()),
                "clicks": int(group["clicks"].sum()),
                "conversions": int(group["conversions"].sum()),
                "revenue_cents": int(group["revenue_cents"].sum()),
            }

            # Calculate aggregate metrics
            if campaign_data["impressions"] > 0:
                campaign_data["ctr"] = campaign_data["clicks"] / campaign_data["impressions"] * 100
            if campaign_data["clicks"] > 0:
                campaign_data["cpc_cents"] = int(campaign_data["total_spend_cents"] / campaign_data["clicks"])
            if campaign_data["impressions"] > 0:
                campaign_data["cpm_cents"] = int(campaign_data["total_spend_cents"] / campaign_data["impressions"] * 1000)
            if campaign_data["conversions"] > 0:
                campaign_data["cpa_cents"] = int(campaign_data["total_spend_cents"] / campaign_data["conversions"])
            if campaign_data["total_spend_cents"] > 0:
                campaign_data["roas"] = campaign_data["revenue_cents"] / campaign_data["total_spend_cents"]

            # Check if campaign exists
            result = await self.db.execute(
                select(Campaign).where(
                    Campaign.tenant_id == tenant_id,
                    Campaign.platform == platform,
                    Campaign.external_id == str(external_id),
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing campaign
                for key, value in campaign_data.items():
                    if key not in ["tenant_id", "platform", "external_id"]:
                        setattr(existing, key, value)
                campaign = existing
            else:
                # Create new campaign
                campaign = Campaign(**campaign_data)
                self.db.add(campaign)
                campaigns_created += 1

            await self.db.flush()

            # Create daily metrics if requested
            if create_daily_metrics and "date" in group.columns:
                for _, row in group.iterrows():
                    metric_date = row["date"]
                    if isinstance(metric_date, pd.Timestamp):
                        metric_date = metric_date.date()

                    metric = CampaignMetric(
                        tenant_id=tenant_id,
                        campaign_id=campaign.id,
                        date=metric_date,
                        spend_cents=int(row.get("spend_cents", 0)),
                        revenue_cents=int(row.get("revenue_cents", 0)),
                        impressions=int(row.get("impressions", 0)),
                        clicks=int(row.get("clicks", 0)),
                        conversions=int(row.get("conversions", 0)),
                    )
                    self.db.add(metric)
                    metrics_created += 1

        await self.db.commit()

        return {
            "campaigns_created": campaigns_created,
            "metrics_created": metrics_created,
        }

    def load_csv_to_dataframe(self, file_path: str, dataset_format: str = "generic") -> pd.DataFrame:
        """
        Load and transform CSV to DataFrame without database.
        Useful for training directly from files.
        """
        file_path = Path(file_path)
        df = pd.read_csv(file_path)

        mapping = self._detect_format(df, dataset_format)
        df = self._apply_mapping(df, mapping)
        df = self._transform_data(df, AdPlatform.META)

        return df

    @staticmethod
    def generate_sample_data(
        num_campaigns: int = 50,
        days_per_campaign: int = 30,
        platforms: List[str] = None,
    ) -> pd.DataFrame:
        """
        Generate synthetic training data.
        Useful for testing and initial model training.
        """
        import numpy as np

        if platforms is None:
            platforms = ["meta", "google", "tiktok", "snapchat", "linkedin"]

        data = []
        base_date = date.today() - timedelta(days=days_per_campaign)

        for campaign_idx in range(num_campaigns):
            platform = platforms[campaign_idx % len(platforms)]

            # Platform-specific baselines
            baselines = {
                "meta": {"ctr": 1.5, "cvr": 0.025, "cpm": 8},
                "google": {"ctr": 3.0, "cvr": 0.035, "cpm": 5},
                "tiktok": {"ctr": 1.0, "cvr": 0.015, "cpm": 6},
                "snapchat": {"ctr": 0.8, "cvr": 0.012, "cpm": 7},
                "linkedin": {"ctr": 0.5, "cvr": 0.020, "cpm": 12},
            }

            base = baselines.get(platform, baselines["meta"])

            # Daily budget varies by campaign
            daily_budget = np.random.uniform(100, 1000)

            for day_idx in range(days_per_campaign):
                current_date = base_date + timedelta(days=day_idx)

                # Add some daily variance
                day_factor = 1 + np.random.normal(0, 0.1)
                weekend_factor = 0.85 if current_date.weekday() >= 5 else 1.0

                spend = daily_budget * day_factor * weekend_factor
                impressions = int(spend / base["cpm"] * 1000 * day_factor)
                clicks = int(impressions * base["ctr"] / 100 * (1 + np.random.normal(0, 0.2)))
                conversions = int(clicks * base["cvr"] * (1 + np.random.normal(0, 0.3)))

                # Revenue with variance
                avg_order_value = np.random.uniform(30, 150)
                revenue = conversions * avg_order_value * (1 + np.random.normal(0, 0.1))

                data.append({
                    "date": current_date,
                    "campaign_id": f"campaign_{campaign_idx}",
                    "campaign_name": f"{platform.title()} Campaign {campaign_idx}",
                    "platform": platform,
                    "spend": round(spend, 2),
                    "impressions": max(0, impressions),
                    "clicks": max(0, clicks),
                    "conversions": max(0, conversions),
                    "revenue": round(max(0, revenue), 2),
                })

        return pd.DataFrame(data)


# CLI interface for standalone usage
if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="Load training data")
    parser.add_argument("--generate", action="store_true", help="Generate sample data")
    parser.add_argument("--output", type=str, default="sample_training_data.csv", help="Output file")
    parser.add_argument("--campaigns", type=int, default=50, help="Number of campaigns")
    parser.add_argument("--days", type=int, default=30, help="Days per campaign")

    args = parser.parse_args()

    if args.generate:
        print(f"Generating sample data: {args.campaigns} campaigns, {args.days} days each...")
        df = TrainingDataLoader.generate_sample_data(
            num_campaigns=args.campaigns,
            days_per_campaign=args.days,
        )
        df.to_csv(args.output, index=False)
        print(f"Saved to {args.output}")
        print(f"Total rows: {len(df)}")
        print(f"Columns: {list(df.columns)}")
