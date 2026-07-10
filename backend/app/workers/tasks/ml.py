# =============================================================================
# Stratum AI - ML Prediction Tasks
# =============================================================================
"""
Background tasks for ML predictions and ROAS alerts.
"""

from datetime import UTC, datetime

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import select

from app.db.session import SyncSessionLocal
from app.models import Campaign, MLPrediction, Tenant
from app.workers.locks import with_distributed_lock
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
                    created_at=datetime.now(UTC),
                )
                db.add(ml_pred)
                predictions.append(prediction)

            except (ValueError, TypeError, KeyError, RuntimeError) as e:
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


# Explicit name: this module was split out of the old app/workers/tasks.py;
# without it the auto-generated name gains the submodule segment and the
# beat schedule's task reference silently dispatches to nothing.
@shared_task(name="app.workers.tasks.run_all_tenant_predictions")
@with_distributed_lock(timeout=1800)
def run_all_tenant_predictions():
    """
    Run predictions for all active tenants.
    Scheduled every 6 hours by Celery beat.
    """
    logger.info("Starting predictions for all tenants")

    with SyncSessionLocal() as db:
        tenants = (
            db.execute(select(Tenant).where(Tenant.is_deleted == False)).scalars().all()
        )

        task_count = 0
        for tenant in tenants:
            run_live_predictions.delay(tenant.id)
            # Fan out anomaly/ROAS alerting on the same cadence so the
            # safety-signal alerts actually run (previously never dispatched).
            generate_roas_alerts.delay(tenant.id)
            task_count += 1

    logger.info(f"Queued predictions + ROAS alerts for {task_count} tenants")
    return {"tasks_queued": task_count}


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2,
)
def generate_roas_alerts(self, tenant_id: int):
    """
    Generate ROAS/CPA/spend anomaly alerts for a tenant's active campaigns.

    Builds a per-campaign daily time series from ``campaign_metrics`` and runs
    the z-score anomaly detector, emitting HIGH/CRITICAL anomalies as real-time
    alerts.
    """
    from app.analytics.logic.anomalies import detect_anomalies
    from app.analytics.logic.types import AnomalyParams
    from app.base_models import CampaignMetric

    logger.info(f"Generating ROAS alerts for tenant {tenant_id}")

    params = AnomalyParams(metrics_to_check=["roas", "cpa", "spend"])
    # Baseline window plus today's value.
    lookback = params.window_days + 1

    def _roas(m: "CampaignMetric") -> float:
        spend = (m.spend_cents or 0) / 100.0
        return ((m.revenue_cents or 0) / 100.0) / spend if spend > 0 else 0.0

    def _cpa(m: "CampaignMetric") -> float:
        conv = m.conversions or 0
        return ((m.spend_cents or 0) / 100.0) / conv if conv > 0 else 0.0

    def _spend(m: "CampaignMetric") -> float:
        return (m.spend_cents or 0) / 100.0

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
                # Most-recent `lookback` daily rows, then order oldest -> newest.
                rows = (
                    db.execute(
                        select(CampaignMetric)
                        .where(
                            CampaignMetric.campaign_id == campaign.id,
                            CampaignMetric.tenant_id == tenant_id,
                        )
                        .order_by(CampaignMetric.date.desc())
                        .limit(lookback)
                    )
                    .scalars()
                    .all()
                )
                rows = list(reversed(rows))

                # Need >=3 baseline points plus today for a meaningful z-score.
                if len(rows) < 4:
                    continue

                history, today = rows[:-1], rows[-1]
                metrics_series = {
                    "roas": [_roas(m) for m in history],
                    "cpa": [_cpa(m) for m in history],
                    "spend": [_spend(m) for m in history],
                }
                current_values = {
                    "roas": _roas(today),
                    "cpa": _cpa(today),
                    "spend": _spend(today),
                }

                for anomaly in detect_anomalies(metrics_series, current_values, params):
                    if not anomaly.is_anomaly:
                        continue
                    severity = getattr(anomaly.severity, "value", anomaly.severity)
                    if severity not in ("high", "critical"):
                        continue

                    alert = {
                        "campaign_id": campaign.id,
                        "campaign_name": campaign.name,
                        "metric": anomaly.metric,
                        "severity": severity,
                        "z_score": anomaly.zscore,
                        "current_value": anomaly.current_value,
                        "baseline": anomaly.baseline_mean,
                    }
                    alerts.append(alert)

                    # Publish real-time alert
                    publish_event(
                        tenant_id,
                        "roas_alert",
                        alert,
                    )

            # Narrow catch: data-shape issues skip one campaign. A call-signature
            # regression (TypeError) must NOT be swallowed here — that is exactly
            # what previously made this task silently emit zero alerts.
            except (ValueError, KeyError, ZeroDivisionError) as e:
                logger.error(f"Alert generation failed for campaign {campaign.id}: {e}")

    logger.info(f"Generated {len(alerts)} ROAS alerts for tenant {tenant_id}")
    return {"alerts": len(alerts)}
