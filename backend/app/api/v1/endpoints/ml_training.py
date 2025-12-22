# =============================================================================
# Stratum AI - ML Training API Endpoints
# =============================================================================
"""
API endpoints for uploading training data and managing ML models.
"""

import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import get_async_session
from app.ml.data_loader import TrainingDataLoader
from app.ml.train import ModelTrainer

logger = get_logger(__name__)
router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================
class TrainingResponse(BaseModel):
    """Response for training operations."""
    success: bool
    message: str
    models_trained: List[str]
    metrics: dict
    training_time_seconds: float


class DataUploadResponse(BaseModel):
    """Response for data upload operations."""
    success: bool
    message: str
    rows_processed: int
    columns_detected: List[str]
    campaigns_created: int
    metrics_created: int


class ModelInfo(BaseModel):
    """Information about a trained model."""
    name: str
    version: str
    created_at: str
    metrics: dict
    features: List[str]


class ModelsListResponse(BaseModel):
    """Response listing all available models."""
    models: List[ModelInfo]
    models_path: str


class GenerateSampleRequest(BaseModel):
    """Request to generate sample training data."""
    num_campaigns: int = 50
    days_per_campaign: int = 30
    platforms: Optional[List[str]] = None


# =============================================================================
# Endpoints
# =============================================================================
@router.post("/upload", response_model=DataUploadResponse)
async def upload_training_data(
    file: UploadFile = File(...),
    platform: str = Query("meta", description="Ad platform (meta, google, tiktok, snapchat, linkedin)"),
    dataset_format: str = Query("generic", description="Dataset format hint (generic, facebook_kaggle, google_kaggle)"),
    train_after_upload: bool = Query(False, description="Automatically train models after upload"),
):
    """
    Upload CSV training data.

    Supported formats:
    - Facebook/Meta Ads CSV (Kaggle)
    - Google Ads CSV (Kaggle)
    - Generic CSV with spend/impressions/clicks/conversions/revenue columns

    The system auto-detects column mappings based on column names.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported",
        )

    # Save uploaded file temporarily
    try:
        with NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        # Load and process data
        loader = TrainingDataLoader()
        df = loader.load_csv_to_dataframe(tmp_path, dataset_format)

        # Save processed data for training
        data_dir = Path(settings.ml_models_path).parent / "training_data"
        data_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = data_dir / f"training_data_{timestamp}.csv"
        df.to_csv(output_path, index=False)

        result = {
            "success": True,
            "message": f"Data uploaded and processed successfully. Saved to {output_path}",
            "rows_processed": len(df),
            "columns_detected": list(df.columns),
            "campaigns_created": df["external_id"].nunique() if "external_id" in df.columns else 0,
            "metrics_created": len(df),
        }

        # Train models if requested
        if train_after_upload:
            trainer = ModelTrainer(settings.ml_models_path)
            trainer.train_all(df)
            result["message"] += " Models trained successfully."

        return DataUploadResponse(**result)

    except Exception as e:
        logger.error("upload_training_data_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process uploaded file: {str(e)}",
        )

    finally:
        # Cleanup temp file
        if "tmp_path" in locals():
            os.unlink(tmp_path)


@router.post("/train", response_model=TrainingResponse)
async def train_models(
    data_file: Optional[str] = Query(None, description="Path to training data CSV (uses latest if not specified)"),
    use_sample_data: bool = Query(False, description="Use generated sample data instead of uploaded data"),
    num_campaigns: int = Query(100, description="Number of campaigns for sample data"),
    days: int = Query(30, description="Days per campaign for sample data"),
):
    """
    Train ML models from uploaded data or sample data.

    Models trained:
    - roas_predictor: Predicts ROAS from campaign features
    - conversion_predictor: Predicts conversions
    - budget_impact: Predicts revenue changes from budget changes
    """
    import time
    start_time = time.time()

    try:
        if use_sample_data:
            # Generate sample data
            df = TrainingDataLoader.generate_sample_data(
                num_campaigns=num_campaigns,
                days_per_campaign=days,
            )
            logger.info("using_sample_data", rows=len(df))
        elif data_file:
            # Use specified file
            loader = TrainingDataLoader()
            df = loader.load_csv_to_dataframe(data_file)
        else:
            # Find latest uploaded data
            data_dir = Path(settings.ml_models_path).parent / "training_data"
            if not data_dir.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No training data found. Upload data first or use sample data.",
                )

            csv_files = sorted(data_dir.glob("*.csv"), key=os.path.getmtime, reverse=True)
            if not csv_files:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No training data found. Upload data first or use sample data.",
                )

            loader = TrainingDataLoader()
            df = loader.load_csv_to_dataframe(str(csv_files[0]))
            logger.info("using_latest_data", file=str(csv_files[0]), rows=len(df))

        # Train models
        trainer = ModelTrainer(settings.ml_models_path)
        results = trainer.train_all(df)

        elapsed = time.time() - start_time

        return TrainingResponse(
            success=True,
            message=f"Successfully trained {len(results)} models",
            models_trained=list(results.keys()),
            metrics=results,
            training_time_seconds=round(elapsed, 2),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("train_models_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Training failed: {str(e)}",
        )


@router.get("/models", response_model=ModelsListResponse)
async def list_models():
    """
    List all trained ML models and their metadata.
    """
    import json

    models_path = Path(settings.ml_models_path)
    models = []

    if models_path.exists():
        for metadata_file in models_path.glob("*_metadata.json"):
            try:
                with open(metadata_file) as f:
                    metadata = json.load(f)
                    models.append(ModelInfo(
                        name=metadata.get("name", metadata_file.stem.replace("_metadata", "")),
                        version=metadata.get("version", "unknown"),
                        created_at=metadata.get("created_at", "unknown"),
                        metrics=metadata.get("metrics", {}),
                        features=metadata.get("features", []),
                    ))
            except Exception as e:
                logger.warning("failed_to_read_model_metadata", file=str(metadata_file), error=str(e))

    return ModelsListResponse(
        models=models,
        models_path=str(models_path),
    )


@router.delete("/models/{model_name}")
async def delete_model(model_name: str):
    """
    Delete a trained model.
    """
    models_path = Path(settings.ml_models_path)

    files_to_delete = [
        models_path / f"{model_name}.pkl",
        models_path / f"{model_name}_scaler.pkl",
        models_path / f"{model_name}_metadata.json",
    ]

    deleted = []
    for file_path in files_to_delete:
        if file_path.exists():
            file_path.unlink()
            deleted.append(str(file_path))

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_name}' not found",
        )

    return {"success": True, "deleted_files": deleted}


@router.post("/generate-sample")
async def generate_sample_data(request: GenerateSampleRequest):
    """
    Generate sample training data for testing.

    Returns the generated data as a downloadable CSV.
    """
    df = TrainingDataLoader.generate_sample_data(
        num_campaigns=request.num_campaigns,
        days_per_campaign=request.days_per_campaign,
        platforms=request.platforms,
    )

    # Save to training data directory
    data_dir = Path(settings.ml_models_path).parent / "training_data"
    data_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = data_dir / f"sample_data_{timestamp}.csv"
    df.to_csv(output_path, index=False)

    return {
        "success": True,
        "message": f"Generated {len(df)} rows of sample data",
        "rows": len(df),
        "campaigns": request.num_campaigns,
        "days_per_campaign": request.days_per_campaign,
        "file_path": str(output_path),
        "columns": list(df.columns),
    }


@router.get("/training-data")
async def list_training_data():
    """
    List available training data files.
    """
    data_dir = Path(settings.ml_models_path).parent / "training_data"

    if not data_dir.exists():
        return {"files": [], "directory": str(data_dir)}

    files = []
    for csv_file in sorted(data_dir.glob("*.csv"), key=os.path.getmtime, reverse=True):
        stat = csv_file.stat()
        files.append({
            "name": csv_file.name,
            "path": str(csv_file),
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })

    return {"files": files, "directory": str(data_dir)}


@router.post("/load-campaigns-from-dataset")
async def load_campaigns_from_dataset(
    num_campaigns: int = Query(100, description="Number of campaigns to load"),
    dataset_path: Optional[str] = Query(None, description="Path to dataset CSV"),
    train_after_load: bool = Query(True, description="Train ML models after loading campaigns"),
):
    """
    Load campaigns from the synthetic ROAS Meta dataset into the database.

    This creates real campaign records with:
    - Targeting information (age, gender, geo, audience type)
    - Daily metrics
    - Creative assets with fatigue scores
    - ROAS, conversions, and other performance metrics

    The default dataset is synthetic_roas_meta_10k.csv from the Datasets folder.
    """
    import time
    from app.db.session import AsyncSessionLocal
    from app.models import Campaign, CampaignMetric, CreativeAsset, Tenant, AdPlatform, AssetType, CampaignStatus
    import pandas as pd
    import random

    start_time = time.time()

    # Find dataset
    if dataset_path:
        dataset_file = Path(dataset_path)
    else:
        # Look for synthetic_roas_meta_10k.csv in common locations
        possible_paths = [
            Path("/app/Datasets/synthetic_roas_meta_10k.csv"),  # Docker mount path
            Path(__file__).parent.parent.parent.parent.parent.parent / "Datasets" / "synthetic_roas_meta_10k.csv",
            Path("C:/Users/Vip/OneDrive/Desktop/Stratum-AI-Final-Updates-Dec-2025-main/Datasets/synthetic_roas_meta_10k.csv"),
            Path("./Datasets/synthetic_roas_meta_10k.csv"),
        ]
        dataset_file = None
        for p in possible_paths:
            if p.exists():
                dataset_file = p
                break

        if not dataset_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset not found. Tried: {[str(p) for p in possible_paths]}",
            )

    logger.info("loading_dataset", path=str(dataset_file))
    df = pd.read_csv(dataset_file)

    # Objective to status mapping
    objective_status = {
        "OUTCOME_SALES": CampaignStatus.ACTIVE,
        "OUTCOME_LEADS": CampaignStatus.ACTIVE,
        "OUTCOME_TRAFFIC": CampaignStatus.ACTIVE,
        "OUTCOME_ENGAGEMENT": CampaignStatus.ACTIVE,
    }

    # Creative to asset type mapping
    creative_asset = {
        "UGC": AssetType.VIDEO,
        "Product": AssetType.IMAGE,
        "Lifestyle": AssetType.IMAGE,
        "Testimonial": AssetType.VIDEO,
        "Offer/Discount": AssetType.IMAGE,
    }

    async with AsyncSessionLocal() as db:
        # Get or create tenant
        from sqlalchemy import select
        result = await db.execute(select(Tenant).limit(1))
        tenant = result.scalar_one_or_none()
        if not tenant:
            tenant = Tenant(name="Stratum Demo", slug="stratum-demo", settings={})
            db.add(tenant)
            await db.flush()
        tenant_id = tenant.id

        # Group by campaign_id
        campaign_groups = df.groupby("campaign_id")
        campaign_ids = list(campaign_groups.groups.keys())
        selected = random.sample(campaign_ids, min(num_campaigns, len(campaign_ids)))

        campaigns_created = 0
        metrics_created = 0
        assets_created = 0

        for campaign_id in selected:
            group = campaign_groups.get_group(campaign_id)
            first_row = group.iloc[0]

            # Check if exists
            existing = await db.execute(
                select(Campaign).where(
                    Campaign.tenant_id == tenant_id,
                    Campaign.external_id == campaign_id,
                )
            )
            if existing.scalar_one_or_none():
                continue

            # Aggregate metrics
            total_spend = int(group["spend"].sum() * 100)
            total_revenue = int(group["revenue"].sum() * 100)
            total_impressions = int(group["impressions"].sum())
            total_clicks = int(group["clicks"].sum())
            total_conversions = int(group["conversions"].sum())

            # Derived metrics
            ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
            cpc = int(total_spend / total_clicks) if total_clicks > 0 else 0
            cpm = int(total_spend / total_impressions * 1000) if total_impressions > 0 else 0
            cpa = int(total_spend / total_conversions) if total_conversions > 0 else 0
            roas = (total_revenue / total_spend) if total_spend > 0 else 0

            # Extract targeting
            objective = first_row.get("objective", "OUTCOME_SALES")
            geo = first_row.get("geo", "US")
            creative_type = first_row.get("creative_type", "Product")

            campaign = Campaign(
                tenant_id=tenant_id,
                platform=AdPlatform.META,
                external_id=campaign_id,
                account_id=str(first_row.get("account_id", "10000000001")),
                name=f"Meta {objective.replace('OUTCOME_', '')} - {geo} - {creative_type}",
                status=objective_status.get(objective, CampaignStatus.ACTIVE),
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
                targeting_age_min=int(first_row.get("age_min", 18)),
                targeting_age_max=int(first_row.get("age_max", 65)),
                targeting_genders=[first_row.get("gender", "all")] if first_row.get("gender") != "all" else [],
                targeting_locations=[{"name": geo, "type": "country"}],
                targeting_interests=[first_row.get("audience_type", "Broad")],
                labels=[objective, geo, creative_type],
            )
            db.add(campaign)
            await db.flush()
            campaigns_created += 1

            # Create metrics - check for existing to avoid duplicates
            seen_dates = set()
            for _, row in group.iterrows():
                try:
                    metric_date = pd.to_datetime(row.get("date")).date()
                except:
                    metric_date = datetime.now(timezone.utc).date() - timedelta(days=random.randint(1, 30))

                # Skip duplicate dates within the same campaign
                if metric_date in seen_dates:
                    continue
                seen_dates.add(metric_date)

                # Check if metric already exists
                existing_metric = await db.execute(
                    select(CampaignMetric).where(
                        CampaignMetric.campaign_id == campaign.id,
                        CampaignMetric.date == metric_date,
                    )
                )
                if existing_metric.scalar_one_or_none():
                    continue

                metric = CampaignMetric(
                    tenant_id=tenant_id,
                    campaign_id=campaign.id,
                    date=metric_date,
                    spend_cents=int(row.get("spend", 0) * 100),
                    revenue_cents=int(row.get("revenue", 0) * 100),
                    impressions=int(row.get("impressions", 0)),
                    clicks=int(row.get("clicks", 0)),
                    conversions=int(row.get("conversions", 0)),
                )
                db.add(metric)
                metrics_created += 1

            # Create asset - check if already exists for this campaign
            existing_asset = await db.execute(
                select(CreativeAsset).where(CreativeAsset.campaign_id == campaign.id).limit(1)
            )
            if not existing_asset.scalar_one_or_none():
                asset_type = creative_asset.get(creative_type, AssetType.IMAGE)
                fatigue = float(first_row.get("fatigue_score", 0)) * 100

                asset = CreativeAsset(
                    tenant_id=tenant_id,
                    campaign_id=campaign.id,
                    name=f"{creative_type}_{first_row.get('format', 'Image')}_{campaign_id[:8]}",
                    asset_type=asset_type,
                    file_url=f"https://storage.stratum.ai/assets/{campaign_id}/creative.{'mp4' if asset_type == AssetType.VIDEO else 'jpg'}",
                    thumbnail_url=f"https://storage.stratum.ai/assets/{campaign_id}/thumb.jpg",
                    fatigue_score=min(100, fatigue),
                    impressions=total_impressions,
                    clicks=total_clicks,
                    ctr=round(ctr, 4),
                    times_used=random.randint(1, 15),
                    first_used_at=datetime.now(timezone.utc) - timedelta(days=random.randint(7, 60)),
                    tags=[creative_type, first_row.get("format", "Image"), geo],
                )
                db.add(asset)
                assets_created += 1

        await db.commit()

    elapsed = time.time() - start_time

    result = {
        "success": True,
        "message": f"Loaded {campaigns_created} campaigns from dataset",
        "dataset": str(dataset_file),
        "campaigns_created": campaigns_created,
        "metrics_created": metrics_created,
        "assets_created": assets_created,
        "tenant_id": tenant_id,
        "elapsed_seconds": round(elapsed, 2),
    }

    # Train models if requested
    if train_after_load:
        logger.info("training_models_after_load")
        trainer = ModelTrainer(settings.ml_models_path)
        loader = TrainingDataLoader()
        training_df = loader.load_csv_to_dataframe(str(dataset_file))
        train_results = trainer.train_all(training_df)
        result["training_results"] = train_results
        result["message"] += " ML models trained successfully."

    return result
