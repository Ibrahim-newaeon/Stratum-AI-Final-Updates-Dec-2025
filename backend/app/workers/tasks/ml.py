# =============================================================================
# Stratum AI - ML Prediction Tasks
# =============================================================================
"""
Background tasks for ML predictions and ROAS alerts.
"""

from datetime import datetime, timezone
from typing import Dict, List

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import select

from app.db.session import SyncSessionLocal
from app.models import Campaign, MLPrediction, Tenant
from app.workers.tasks.helpers import calculate_task_confidence, publish_event

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2,
)
def run_live_predictions(self, tenant_id: int):
    """
    Run live ML predictions for a tenant's campaigns.

    Generates predictions for:
    - ROAS trajectory
    - Conversion probability
    - Budget optimization recommendations
    """
    logger.info(f"Running live predictions for tenant {tenant_id}")

    with SyncSessionLocal() as db:
        campaigns = (
            db.execute(
                select(Campaign).where(
                    Campaign.tenant_id == tenant_id,
                    Campaign.is_deleted == False,
                    Campaign.status == "active",
                )
            )
            .scalars()
            .all()
        )

        if not campaigns:
            return {"status": "no_campaigns"}

        # Prepare campaign data for confidence calculation
        campaign_data = [
            {
                "id": c.id,
                "spend": c.total_spend_cents or 0,
                "roas": c.roas or 0,
            }
            for c in campaigns
        ]
        confidence = calculate_task_confidence(campaign_data, "portfolio")

        predictions = []
        for campaign in campaigns:
            try:
                # Use ROAS optimizer for predictions
                from app.ml.roas_optimizer import ROASOptimizer

                optimizer = ROASOptimizer(tenant_id)
                prediction = optimizer.predict_campaign(campaign.id)

                # Store prediction
                ml_pred = MLPrediction(
                    tenant_id=tenant_id,
                    campaign_id=campaign.id,
                    prediction_type="roas_trajectory",
                    predicted_value=prediction.get("predicted_roas"),
                    confidence=prediction.get("confidence", confidence),
                    features=prediction.get("features"),
                    created_at=datetime.now(timezone.utc),
                )
                db.add(ml_pred)
                predictions.append(prediction)

            except Exception as e:
                logger.error(f"Prediction failed for campaign {campaign.id}: {e}")

        db.commit()

        # Publish update event
        publish_event(
            tenant_id,
            "predictions_updated",
            {
                "count": len(predictions),
                "confidence": confidence,
            },
        )

    logger.info(f"Generated {len(predictions)} predictions for tenant {tenant_id}")
    return {"predictions": len(predictions), "confidence": confidence}


@shared_task
def run_all_tenant_predictions():
    """
    Run predictions for all active tenants.
    Scheduled every 6 hours by Celery beat.
    """
    logger.info("Starting predictions for all tenants")

    with SyncSessionLocal() as db:
        tenants = (
            db.execute(select(Tenant).where(Tenant.is_deleted == False))
            .scalars()
            .all()
        )

        task_count = 0
        for tenant in tenants:
            run_live_predictions.delay(tenant.id)
            task_count += 1

    logger.info(f"Queued {task_count} prediction tasks")
    return {"tasks_queued": task_count}


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2,
)
def generate_roas_alerts(self, tenant_id: int):
    """
    Generate ROAS performance alerts for campaigns.

    Triggers alerts when:
    - ROAS drops below threshold
    - ROAS significantly improves
    - Anomalies detected
    """
    logger.info(f"Generating ROAS alerts for tenant {tenant_id}")

    with SyncSessionLocal() as db:
        campaigns = (
            db.execute(
                select(Campaign).where(
                    Campaign.tenant_id == tenant_id,
                    Campaign.is_deleted == False,
                    Campaign.status == "active",
                )
            )
            .scalars()
            .all()
        )

        alerts = []
        for campaign in campaigns:
            try:
                # Check ROAS against thresholds
                from app.analytics.logic.anomalies import detect_anomalies

                anomalies = detect_anomalies(
                    campaign_id=campaign.id,
                    tenant_id=tenant_id,
                    metrics=["roas", "cpa", "spend"],
                )

                for anomaly in anomalies:
                    if anomaly["severity"] in ("HIGH", "CRITICAL"):
                        alert = {
                            "campaign_id": campaign.id,
                            "campaign_name": campaign.name,
                            "metric": anomaly["metric"],
                            "severity": anomaly["severity"],
                            "z_score": anomaly["z_score"],
                            "current_value": anomaly["current_value"],
                            "baseline": anomaly["baseline"],
                        }
                        alerts.append(alert)

                        # Publish real-time alert
                        publish_event(
                            tenant_id,
                            "roas_alert",
                            alert,
                        )

            except Exception as e:
                logger.error(f"Alert generation failed for campaign {campaign.id}: {e}")

    logger.info(f"Generated {len(alerts)} ROAS alerts for tenant {tenant_id}")
    return {"alerts": len(alerts)}
