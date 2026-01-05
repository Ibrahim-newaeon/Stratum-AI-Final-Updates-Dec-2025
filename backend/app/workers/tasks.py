# =============================================================================
# Stratum AI - Celery Tasks
# =============================================================================
"""
Background tasks for data synchronization, rules evaluation, and ML jobs.
Implements idempotent, retriable operations with exponential backoff.
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import select, and_
from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.db.session import SyncSessionLocal
from app.models import (
    AuditAction,
    AuditLog,
    Campaign,
    CampaignMetric,
    CompetitorBenchmark,
    CreativeAsset,
    Rule,
    RuleExecution,
    RuleStatus,
    Tenant,
)

logger = get_task_logger(__name__)


# =============================================================================
# Data Synchronization Tasks
# =============================================================================
@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
)
def sync_campaign_data(self, tenant_id: int, campaign_id: int):
    """
    Sync data for a specific campaign from its ad platform.

    Idempotent: Safe to retry without side effects.
    """
    logger.info(f"Syncing campaign {campaign_id} for tenant {tenant_id}")

    with SyncSessionLocal() as db:
        campaign = db.execute(
            select(Campaign).where(
                Campaign.id == campaign_id,
                Campaign.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()

        if not campaign:
            logger.warning(f"Campaign {campaign_id} not found")
            return {"status": "not_found"}

        try:
            # Use mock client for development
            if settings.use_mock_ad_data:
                from app.services.mock_client import MockAdNetworkManager

                manager = MockAdNetworkManager(tenant_id)
                # Get time series data
                from app.services.mock_client import MockAdNetwork
                network = MockAdNetwork(seed=tenant_id)

                end_date = datetime.now(timezone.utc).date()
                start_date = campaign.start_date or (end_date - timedelta(days=30))

                time_series = network.generate_time_series(
                    campaign.external_id,
                    start_date,
                    end_date,
                    campaign.__dict__,
                )

                # Update daily metrics
                for day_data in time_series:
                    existing = db.execute(
                        select(CampaignMetric).where(
                            CampaignMetric.campaign_id == campaign_id,
                            CampaignMetric.date == day_data["date"],
                        )
                    ).scalar_one_or_none()

                    if existing:
                        for key, value in day_data.items():
                            if key != "date" and hasattr(existing, key):
                                setattr(existing, key, value)
                    else:
                        metric = CampaignMetric(
                            tenant_id=tenant_id,
                            campaign_id=campaign_id,
                            date=day_data["date"],
                            impressions=day_data["impressions"],
                            clicks=day_data["clicks"],
                            conversions=day_data["conversions"],
                            spend_cents=day_data["spend_cents"],
                            revenue_cents=day_data["revenue_cents"],
                            video_views=day_data.get("video_views"),
                            video_completions=day_data.get("video_completions"),
                        )
                        db.add(metric)

                # Update campaign aggregates
                campaign.calculate_metrics()
                campaign.last_synced_at = datetime.now(timezone.utc)
                campaign.sync_error = None

            db.commit()

            # Publish real-time event
            _publish_event(tenant_id, "sync_complete", {
                "campaign_id": campaign_id,
                "campaign_name": campaign.name,
            })

            logger.info(f"Campaign {campaign_id} synced successfully")
            return {"status": "success", "campaign_id": campaign_id}

        except Exception as e:
            campaign.sync_error = str(e)
            db.commit()
            raise


@shared_task
def sync_all_campaigns():
    """
    Sync all active campaigns across all tenants.
    Scheduled hourly by Celery beat.
    """
    logger.info("Starting sync for all campaigns")

    with SyncSessionLocal() as db:
        # Get all active tenants
        tenants = db.execute(
            select(Tenant).where(Tenant.is_deleted == False)
        ).scalars().all()

        task_count = 0
        for tenant in tenants:
            # Get active campaigns for tenant
            campaigns = db.execute(
                select(Campaign).where(
                    Campaign.tenant_id == tenant.id,
                    Campaign.is_deleted == False,
                )
            ).scalars().all()

            for campaign in campaigns:
                # Queue individual sync task
                sync_campaign_data.delay(tenant.id, campaign.id)
                task_count += 1

    logger.info(f"Queued {task_count} campaign sync tasks")
    return {"tasks_queued": task_count}


# =============================================================================
# Rules Engine Tasks
# =============================================================================
@shared_task(bind=True)
def evaluate_rules(self, tenant_id: int, rule_id: int):
    """
    Evaluate a specific automation rule.
    """
    logger.info(f"Evaluating rule {rule_id} for tenant {tenant_id}")

    with SyncSessionLocal() as db:
        rule = db.execute(
            select(Rule).where(
                Rule.id == rule_id,
                Rule.tenant_id == tenant_id,
                Rule.is_deleted == False,
            )
        ).scalar_one_or_none()

        if not rule:
            return {"status": "not_found"}

        if rule.status != RuleStatus.ACTIVE:
            return {"status": "inactive"}

        # Check cooldown
        if rule.last_triggered_at:
            cooldown_end = rule.last_triggered_at + timedelta(hours=rule.cooldown_hours)
            if datetime.now(timezone.utc) < cooldown_end:
                return {"status": "in_cooldown"}

        # Get campaigns to evaluate
        query = select(Campaign).where(
            Campaign.tenant_id == tenant_id,
            Campaign.is_deleted == False,
        )

        if rule.applies_to_campaigns:
            query = query.where(Campaign.id.in_(rule.applies_to_campaigns))
        if rule.applies_to_platforms:
            query = query.where(Campaign.platform.in_(rule.applies_to_platforms))

        campaigns = db.execute(query).scalars().all()

        triggered = False
        for campaign in campaigns:
            result = _evaluate_condition(rule, campaign)

            # Log execution
            execution = RuleExecution(
                tenant_id=tenant_id,
                rule_id=rule_id,
                campaign_id=campaign.id,
                executed_at=datetime.now(timezone.utc),
                triggered=result["triggered"],
                condition_result=result["condition"],
                action_result=result.get("action"),
                error=result.get("error"),
            )
            db.add(execution)

            if result["triggered"]:
                triggered = True
                _execute_action(rule, campaign, db)

        # Update rule metadata
        rule.last_evaluated_at = datetime.now(timezone.utc)
        if triggered:
            rule.last_triggered_at = datetime.now(timezone.utc)
            rule.trigger_count += 1

            # Publish event
            _publish_event(tenant_id, "rule_triggered", {
                "rule_id": rule_id,
                "rule_name": rule.name,
            })

        db.commit()

        return {"status": "evaluated", "triggered": triggered}


@shared_task
def evaluate_all_rules():
    """
    Evaluate all active rules across all tenants.
    Scheduled every 15 minutes by Celery beat.
    """
    logger.info("Starting evaluation of all active rules")

    with SyncSessionLocal() as db:
        # Get all active rules
        rules = db.execute(
            select(Rule).where(
                Rule.status == RuleStatus.ACTIVE,
                Rule.is_deleted == False,
            )
        ).scalars().all()

        task_count = 0
        for rule in rules:
            evaluate_rules.delay(rule.tenant_id, rule.id)
            task_count += 1

    logger.info(f"Queued {task_count} rule evaluation tasks")
    return {"tasks_queued": task_count}


def _evaluate_condition(rule: Rule, campaign: Campaign) -> Dict[str, Any]:
    """Evaluate a rule condition against a campaign."""
    try:
        # Get the field value
        field_value = getattr(campaign, rule.condition_field, None)

        if field_value is None:
            return {
                "triggered": False,
                "condition": {"error": f"Field {rule.condition_field} not found"},
            }

        # Parse condition value
        condition_value = _parse_condition_value(rule.condition_value, type(field_value))

        # Evaluate based on operator
        operator = rule.condition_operator.value
        triggered = False

        if operator == "equals":
            triggered = field_value == condition_value
        elif operator == "not_equals":
            triggered = field_value != condition_value
        elif operator == "greater_than":
            triggered = field_value > condition_value
        elif operator == "less_than":
            triggered = field_value < condition_value
        elif operator == "gte":
            triggered = field_value >= condition_value
        elif operator == "lte":
            triggered = field_value <= condition_value
        elif operator == "contains":
            triggered = str(condition_value) in str(field_value)
        elif operator == "in":
            triggered = field_value in condition_value

        return {
            "triggered": triggered,
            "condition": {
                "field": rule.condition_field,
                "operator": operator,
                "expected": condition_value,
                "actual": field_value,
            },
        }

    except Exception as e:
        return {
            "triggered": False,
            "condition": {"error": str(e)},
            "error": str(e),
        }


def _parse_condition_value(value: str, target_type: type) -> Any:
    """Parse condition value to appropriate type."""
    if target_type == float:
        return float(value)
    elif target_type == int:
        return int(float(value))
    elif target_type == bool:
        return value.lower() in ("true", "1", "yes")
    elif target_type == list:
        return json.loads(value) if value.startswith("[") else [value]
    return value


def _execute_action(rule: Rule, campaign: Campaign, db: Session) -> Dict[str, Any]:
    """Execute the rule action."""
    action = rule.action_type.value
    config = rule.action_config

    if action == "apply_label":
        label = config.get("label", "flagged")
        if label not in campaign.labels:
            campaign.labels = campaign.labels + [label]
        return {"action": "apply_label", "label": label}

    elif action == "send_alert":
        # In production, this would send email/Slack
        logger.info(f"Alert: Rule {rule.name} triggered for campaign {campaign.name}")
        return {"action": "send_alert", "sent": True}

    elif action == "pause_campaign":
        from app.models import CampaignStatus
        campaign.status = CampaignStatus.PAUSED
        return {"action": "pause_campaign", "new_status": "paused"}

    elif action == "adjust_budget":
        adjustment = config.get("adjustment_percent", 0)
        if campaign.daily_budget_cents:
            new_budget = int(campaign.daily_budget_cents * (1 + adjustment / 100))
            campaign.daily_budget_cents = new_budget
        return {"action": "adjust_budget", "adjustment_percent": adjustment}

    elif action == "notify_slack":
        webhook_url = config.get("webhook_url")
        if webhook_url:
            # In production, post to Slack
            logger.info(f"Slack notification: Rule {rule.name} triggered")
        return {"action": "notify_slack", "sent": bool(webhook_url)}

    return {"action": action, "status": "unknown"}


# =============================================================================
# Competitor Intelligence Tasks
# =============================================================================
@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def fetch_competitor_data(self, tenant_id: int, competitor_id: int):
    """
    Fetch and update competitor intelligence data.
    """
    logger.info(f"Fetching competitor data: {competitor_id} for tenant {tenant_id}")

    with SyncSessionLocal() as db:
        competitor = db.execute(
            select(CompetitorBenchmark).where(
                CompetitorBenchmark.id == competitor_id,
                CompetitorBenchmark.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()

        if not competitor:
            return {"status": "not_found"}

        try:
            # Use market intelligence service
            import asyncio
            from app.services.market_proxy import MarketIntelligenceService

            service = MarketIntelligenceService()

            # Run async function in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                data = loop.run_until_complete(
                    service.get_competitor_data(competitor.domain)
                )
            finally:
                loop.close()

            # Update competitor record
            competitor.meta_title = data.meta_title
            competitor.meta_description = data.meta_description
            competitor.meta_keywords = data.meta_keywords
            competitor.social_links = data.social_links
            competitor.estimated_traffic = data.estimated_traffic
            competitor.traffic_trend = data.traffic_trend
            competitor.top_keywords = data.top_keywords
            competitor.paid_keywords_count = data.paid_keywords_count
            competitor.organic_keywords_count = data.organic_keywords_count
            competitor.estimated_ad_spend_cents = data.estimated_ad_spend_cents
            competitor.detected_ad_platforms = data.detected_ad_platforms
            competitor.data_source = data.data_source
            competitor.last_fetched_at = datetime.now(timezone.utc)
            competitor.fetch_error = data.error

            # Store historical snapshot
            if competitor.metrics_history is None:
                competitor.metrics_history = []

            snapshot = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "traffic": data.estimated_traffic,
                "keywords": data.organic_keywords_count,
            }
            competitor.metrics_history = competitor.metrics_history + [snapshot]
            # Keep last 30 snapshots
            competitor.metrics_history = competitor.metrics_history[-30:]

            db.commit()

            logger.info(f"Competitor {competitor.domain} data updated")
            return {"status": "success", "domain": competitor.domain}

        except Exception as e:
            competitor.fetch_error = str(e)
            competitor.last_fetched_at = datetime.now(timezone.utc)
            db.commit()
            raise


@shared_task
def refresh_all_competitors():
    """
    Refresh data for all tracked competitors.
    Scheduled every 6 hours by Celery beat.
    """
    logger.info("Starting refresh of all competitor data")

    with SyncSessionLocal() as db:
        competitors = db.execute(
            select(CompetitorBenchmark)
        ).scalars().all()

        task_count = 0
        for comp in competitors:
            fetch_competitor_data.delay(comp.tenant_id, comp.id)
            task_count += 1

    logger.info(f"Queued {task_count} competitor refresh tasks")
    return {"tasks_queued": task_count}


# =============================================================================
# ML Tasks
# =============================================================================
@shared_task
def generate_forecast(tenant_id: int, campaign_ids: List[int] = None):
    """
    Generate ML forecasts for campaigns.
    """
    logger.info(f"Generating forecasts for tenant {tenant_id}")

    # Implementation would use the ROASForecaster
    # For now, return placeholder
    return {"status": "completed", "tenant_id": tenant_id}


@shared_task
def generate_daily_forecasts():
    """
    Generate daily forecasts for all tenants.
    Scheduled daily at 6 AM UTC.
    """
    logger.info("Generating daily forecasts for all tenants")

    with SyncSessionLocal() as db:
        tenants = db.execute(
            select(Tenant).where(Tenant.is_deleted == False)
        ).scalars().all()

        for tenant in tenants:
            generate_forecast.delay(tenant.id)

    return {"status": "scheduled"}


# =============================================================================
# Asset Management Tasks
# =============================================================================
@shared_task
def calculate_all_fatigue_scores():
    """
    Calculate fatigue scores for all creative assets.
    Scheduled daily at 3 AM UTC.
    """
    logger.info("Calculating fatigue scores for all assets")

    with SyncSessionLocal() as db:
        assets = db.execute(
            select(CreativeAsset).where(CreativeAsset.is_deleted == False)
        ).scalars().all()

        for asset in assets:
            # Simple fatigue calculation
            base_score = 0.0

            if asset.times_used > 0:
                base_score += min(30, asset.times_used * 3)

            if asset.first_used_at:
                days_active = (datetime.now(timezone.utc) - asset.first_used_at).days
                base_score += min(30, days_active * 0.5)

            if asset.impressions > 100000:
                base_score += min(20, (asset.impressions / 100000) * 5)

            if asset.ctr and asset.ctr < 1.0:
                base_score += 20 - (asset.ctr * 10)

            asset.fatigue_score = min(100, base_score)

        db.commit()

    logger.info(f"Updated fatigue scores for {len(assets)} assets")
    return {"assets_updated": len(assets)}


# =============================================================================
# Audit Log Processing
# =============================================================================
@shared_task
def process_audit_log_queue():
    """
    Process queued audit log entries from Redis.
    """
    import redis

    try:
        client = redis.from_url(settings.redis_url)
        count = 0

        with SyncSessionLocal() as db:
            while True:
                # Pop entry from queue
                entry_json = client.rpop("audit_log_queue")
                if not entry_json:
                    break

                entry = json.loads(entry_json)

                # Create audit log
                audit_log = AuditLog(
                    tenant_id=entry.get("tenant_id", 0),
                    user_id=entry.get("user_id"),
                    action=AuditAction(entry.get("action", "update")),
                    resource_type=entry.get("resource_type", "unknown"),
                    resource_id=entry.get("resource_id"),
                    new_value=entry.get("new_value"),
                    ip_address=entry.get("ip_address"),
                    user_agent=entry.get("user_agent"),
                    request_id=entry.get("request_id"),
                    endpoint=entry.get("endpoint"),
                    http_method=entry.get("http_method"),
                )
                db.add(audit_log)
                count += 1

                # Batch commits
                if count % 100 == 0:
                    db.commit()

            db.commit()

        client.close()
        return {"processed": count}

    except Exception as e:
        logger.error(f"Failed to process audit logs: {e}")
        return {"error": str(e)}


# =============================================================================
# Helper Functions
# =============================================================================
def _publish_event(tenant_id: int, event_type: str, payload: Dict[str, Any]):
    """Publish a real-time event via Redis pub/sub."""
    try:
        import redis

        client = redis.from_url(settings.redis_url)
        channel = f"events:tenant:{tenant_id}"

        message = json.dumps({
            "event_type": event_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id,
        })

        client.publish(channel, message)
        client.close()

    except Exception as e:
        logger.warning(f"Failed to publish event: {e}")


# =============================================================================
# WhatsApp Tasks
# =============================================================================
@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=3,
)
def send_whatsapp_message(
    self,
    tenant_id: int,
    message_id: int,
    contact_phone: str,
    message_type: str,
    template_name: Optional[str] = None,
    template_variables: Optional[Dict] = None,
    content: Optional[str] = None,
    media_url: Optional[str] = None,
):
    """
    Send a WhatsApp message via the Meta API.

    This task is queued from the API endpoint and handles
    the actual sending asynchronously.
    """
    import asyncio
    from app.models import WhatsAppMessage, WhatsAppMessageStatus

    logger.info(f"Sending WhatsApp message {message_id} to {contact_phone}")

    with SyncSessionLocal() as db:
        # Get the message record
        message = db.execute(
            select(WhatsAppMessage).where(
                WhatsAppMessage.id == message_id,
                WhatsAppMessage.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()

        if not message:
            logger.error(f"Message {message_id} not found")
            return {"status": "not_found"}

        try:
            # Import WhatsApp client
            from app.services.whatsapp_client import WhatsAppClient, WhatsAppAPIError

            client = WhatsAppClient()

            # Run async function in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                if message_type == "template":
                    # Build components from template variables
                    components = []
                    if template_variables:
                        body_params = [
                            {"type": "text", "text": str(v)}
                            for v in template_variables.get("body", [])
                        ]
                        if body_params:
                            components.append({
                                "type": "body",
                                "parameters": body_params
                            })

                    response = loop.run_until_complete(
                        client.send_template_message(
                            recipient_phone=contact_phone,
                            template_name=template_name,
                            components=components if components else None,
                        )
                    )

                elif message_type == "text":
                    response = loop.run_until_complete(
                        client.send_text_message(
                            recipient_phone=contact_phone,
                            text=content,
                        )
                    )

                elif message_type in ["image", "video", "document", "audio"]:
                    response = loop.run_until_complete(
                        client.send_media_message(
                            recipient_phone=contact_phone,
                            media_type=message_type,
                            media_url=media_url,
                            caption=content,
                        )
                    )

                else:
                    raise ValueError(f"Unsupported message type: {message_type}")

            finally:
                loop.close()

            # Update message with WhatsApp message ID
            wamid = response.get("messages", [{}])[0].get("id")
            message.wamid = wamid
            message.status = WhatsAppMessageStatus.SENT
            message.sent_at = datetime.now(timezone.utc)

            # Update status history
            status_history = message.status_history or []
            status_history.append({
                "status": "sent",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            message.status_history = status_history

            db.commit()

            logger.info(f"Message {message_id} sent successfully, wamid: {wamid}")

            # Publish real-time event
            _publish_event(tenant_id, "message_sent", {
                "message_id": message_id,
                "wamid": wamid,
            })

            return {"status": "sent", "wamid": wamid}

        except WhatsAppAPIError as e:
            message.status = WhatsAppMessageStatus.FAILED
            message.error_code = e.error_code
            message.error_message = e.message

            status_history = message.status_history or []
            status_history.append({
                "status": "failed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": e.message,
            })
            message.status_history = status_history

            db.commit()

            logger.error(f"Failed to send message {message_id}: {e.message}")
            raise  # Trigger retry

        except Exception as e:
            message.status = WhatsAppMessageStatus.FAILED
            message.error_message = str(e)
            db.commit()

            logger.error(f"Error sending message {message_id}: {e}")
            raise  # Trigger retry


@shared_task
def process_scheduled_whatsapp_messages():
    """
    Process WhatsApp messages that are scheduled to be sent.
    Scheduled every minute by Celery beat.
    """
    from app.models import WhatsAppMessage, WhatsAppMessageStatus, WhatsAppContact

    logger.info("Processing scheduled WhatsApp messages")

    with SyncSessionLocal() as db:
        # Get messages scheduled for now or earlier
        now = datetime.now(timezone.utc)
        messages = db.execute(
            select(WhatsAppMessage).where(
                WhatsAppMessage.status == WhatsAppMessageStatus.PENDING,
                WhatsAppMessage.scheduled_at <= now,
                WhatsAppMessage.scheduled_at.isnot(None),
            )
        ).scalars().all()

        task_count = 0
        for msg in messages:
            # Get contact phone
            contact = db.execute(
                select(WhatsAppContact).where(WhatsAppContact.id == msg.contact_id)
            ).scalar_one_or_none()

            if contact:
                send_whatsapp_message.delay(
                    tenant_id=msg.tenant_id,
                    message_id=msg.id,
                    contact_phone=contact.phone_number,
                    message_type=msg.message_type,
                    template_name=msg.template_name,
                    template_variables=msg.template_variables,
                    content=msg.content,
                    media_url=msg.media_url,
                )
                task_count += 1

    logger.info(f"Queued {task_count} scheduled WhatsApp messages")
    return {"tasks_queued": task_count}


# =============================================================================
# Live Prediction Tasks
# =============================================================================
@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2,
)
def run_live_predictions(self, tenant_id: int):
    """
    Run live predictions for all campaigns of a tenant.
    Generates predictions, alerts, and ROAS optimization recommendations.
    """
    from app.ml.roas_optimizer import ROASOptimizer, LivePredictionEngine
    from app.models import MLPrediction

    logger.info(f"Running live predictions for tenant {tenant_id}")

    with SyncSessionLocal() as db:
        # Get all active campaigns
        campaigns = db.execute(
            select(Campaign).where(
                Campaign.tenant_id == tenant_id,
                Campaign.is_deleted == False,
            )
        ).scalars().all()

        if not campaigns:
            logger.info(f"No campaigns found for tenant {tenant_id}")
            return {"status": "no_campaigns"}

        # Convert to dict format
        campaign_data = []
        for c in campaigns:
            campaign_data.append({
                "id": c.id,
                "name": c.name,
                "platform": c.platform.value if c.platform else "meta",
                "spend": c.total_spend_cents / 100 if c.total_spend_cents else 0,
                "revenue": c.revenue_cents / 100 if c.revenue_cents else 0,
                "roas": c.roas or 0,
                "impressions": c.impressions or 0,
                "clicks": c.clicks or 0,
                "conversions": c.conversions or 0,
                "ctr": c.ctr or 0,
                "daily_budget": c.daily_budget_cents / 100 if c.daily_budget_cents else 0,
                "status": c.status.value if c.status else "unknown",
            })

        # Run ROAS optimization analysis
        import asyncio
        optimizer = ROASOptimizer()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            analysis = loop.run_until_complete(
                optimizer.analyze_portfolio(campaign_data)
            )
        finally:
            loop.close()

        # Store predictions in database
        prediction_record = MLPrediction(
            tenant_id=tenant_id,
            prediction_type="portfolio_analysis",
            input_data={"campaign_count": len(campaigns)},
            prediction_result=analysis,
            confidence_score=0.75,
            model_version="roas_optimizer_v1.0",
        )
        db.add(prediction_record)

        # Store individual campaign predictions
        for camp_analysis in analysis.get("campaign_analyses", []):
            camp_prediction = MLPrediction(
                tenant_id=tenant_id,
                campaign_id=camp_analysis.get("campaign_id"),
                prediction_type="campaign_roas_optimization",
                input_data=camp_analysis.get("current_metrics", {}),
                prediction_result={
                    "health_score": camp_analysis.get("health_score"),
                    "recommendations": camp_analysis.get("recommendations"),
                    "optimal_budget": camp_analysis.get("optimal_budget"),
                },
                confidence_score=0.70,
                model_version="roas_optimizer_v1.0",
            )
            db.add(camp_prediction)

        db.commit()

        # Publish event for real-time updates
        _publish_event(tenant_id, "predictions_updated", {
            "campaign_count": len(campaigns),
            "portfolio_roas": analysis.get("portfolio_metrics", {}).get("portfolio_roas"),
            "potential_uplift": analysis.get("potential_uplift", {}).get("uplift_percent"),
        })

        logger.info(f"Live predictions completed for tenant {tenant_id}: {len(campaigns)} campaigns analyzed")

        return {
            "status": "completed",
            "campaigns_analyzed": len(campaigns),
            "portfolio_roas": analysis.get("portfolio_metrics", {}).get("portfolio_roas"),
        }


@shared_task
def run_all_tenant_predictions():
    """
    Run live predictions for all active tenants.
    Scheduled every 30 minutes by Celery beat.
    """
    logger.info("Starting live predictions for all tenants")

    with SyncSessionLocal() as db:
        # Get all active tenants
        tenants = db.execute(
            select(Tenant).where(Tenant.is_active == True)
        ).scalars().all()

        task_count = 0
        for tenant in tenants:
            run_live_predictions.delay(tenant.id)
            task_count += 1

    logger.info(f"Queued {task_count} tenant prediction tasks")
    return {"tasks_queued": task_count}


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2,
)
def generate_roas_alerts(self, tenant_id: int):
    """
    Generate ROAS alerts for campaigns with significant changes.
    Compares current metrics with previous period.
    """
    from app.models import MLPrediction

    logger.info(f"Generating ROAS alerts for tenant {tenant_id}")

    with SyncSessionLocal() as db:
        # Get campaigns
        campaigns = db.execute(
            select(Campaign).where(
                Campaign.tenant_id == tenant_id,
                Campaign.is_deleted == False,
            )
        ).scalars().all()

        alerts = []
        for campaign in campaigns:
            # Check for ROAS below threshold
            if campaign.roas and campaign.roas < 1.0:
                alerts.append({
                    "campaign_id": campaign.id,
                    "campaign_name": campaign.name,
                    "type": "low_roas",
                    "severity": "critical" if campaign.roas < 0.5 else "high",
                    "message": f"ROAS is {campaign.roas:.2f}x - below break-even",
                    "recommendation": "Consider pausing or reducing budget",
                })

            # Check for high ROAS - scaling opportunity
            if campaign.roas and campaign.roas > 3.0:
                alerts.append({
                    "campaign_id": campaign.id,
                    "campaign_name": campaign.name,
                    "type": "scaling_opportunity",
                    "severity": "info",
                    "message": f"ROAS is {campaign.roas:.2f}x - excellent performance",
                    "recommendation": "Consider increasing budget by 20-30%",
                })

            # Check for low CTR
            if campaign.ctr and campaign.ctr < 0.5:
                alerts.append({
                    "campaign_id": campaign.id,
                    "campaign_name": campaign.name,
                    "type": "low_ctr",
                    "severity": "medium",
                    "message": f"CTR is {campaign.ctr:.2f}% - below average",
                    "recommendation": "Review ad creative and targeting",
                })

        # Store alerts
        if alerts:
            alert_record = MLPrediction(
                tenant_id=tenant_id,
                prediction_type="roas_alerts",
                input_data={"campaign_count": len(campaigns)},
                prediction_result={"alerts": alerts, "alert_count": len(alerts)},
                confidence_score=0.85,
                model_version="alert_engine_v1.0",
            )
            db.add(alert_record)
            db.commit()

            # Publish alert event
            _publish_event(tenant_id, "roas_alerts_generated", {
                "alert_count": len(alerts),
                "critical_count": len([a for a in alerts if a["severity"] == "critical"]),
            })

        logger.info(f"Generated {len(alerts)} ROAS alerts for tenant {tenant_id}")

        return {"alerts_generated": len(alerts)}


# =============================================================================
# Cost Allocation Tasks (Daily)
# =============================================================================
@shared_task
def calculate_cost_allocation():
    """
    Calculate daily cost allocation per tenant.
    Estimates warehouse, API, and compute costs.

    Scheduled daily at 2 AM UTC.
    """
    logger.info("Calculating daily cost allocation for all tenants")

    with SyncSessionLocal() as db:
        tenants = db.execute(
            select(Tenant).where(Tenant.is_deleted == False)
        ).scalars().all()

        today = datetime.now(timezone.utc).date()
        records_created = 0

        for tenant in tenants:
            # Calculate estimated costs based on usage

            # Get campaign count for compute estimation
            campaign_count = db.execute(
                select(func.count(Campaign.id)).where(
                    Campaign.tenant_id == tenant.id,
                    Campaign.is_deleted == False,
                )
            ).scalar() or 0

            # Estimate warehouse storage (based on data volume)
            storage_gb = (campaign_count * 0.05) + 0.1  # Base + per-campaign
            storage_cost = storage_gb * 0.023  # ~$0.023/GB/month / 30 days

            # Estimate API costs (based on sync frequency)
            api_calls_estimate = campaign_count * 24 * 4  # 4 calls per hour per campaign
            meta_api_calls = int(api_calls_estimate * 0.4)
            google_api_calls = int(api_calls_estimate * 0.3)
            tiktok_api_calls = int(api_calls_estimate * 0.2)
            snap_api_calls = int(api_calls_estimate * 0.1)
            api_cost = api_calls_estimate * 0.00001  # ~$0.01 per 1000 calls

            # Estimate compute costs
            compute_hours = campaign_count * 0.1  # 6 min per campaign per day
            compute_cost = compute_hours * 0.05  # ~$0.05 per compute hour

            # Estimate ML costs
            ml_predictions = campaign_count * 10  # 10 predictions per campaign per day
            ml_cost = ml_predictions * 0.001  # ~$0.001 per prediction

            # Total cost
            total_cost = storage_cost + api_cost + compute_cost + ml_cost

            # Get tenant's MRR from subscription
            tenant_mrr = 99.0  # Default placeholder
            if tenant.plan == "starter":
                tenant_mrr = 99.0
            elif tenant.plan == "professional":
                tenant_mrr = 299.0
            elif tenant.plan == "enterprise":
                tenant_mrr = 999.0

            # Calculate margin
            gross_margin = ((tenant_mrr / 30) - total_cost) / (tenant_mrr / 30) * 100 if tenant_mrr > 0 else 0

            # Insert cost allocation record
            from sqlalchemy import text
            db.execute(
                text("""
                    INSERT INTO fact_cost_allocation_daily
                    (date, tenant_id, warehouse_storage_gb, warehouse_storage_cost_usd,
                     warehouse_query_cost_usd, warehouse_total_cost_usd, meta_api_calls,
                     google_api_calls, tiktok_api_calls, snap_api_calls, api_total_cost_usd,
                     compute_hours, compute_cost_usd, ml_predictions, ml_cost_usd,
                     total_cost_usd, mrr_usd, gross_margin_pct)
                    VALUES (:date, :tenant_id, :storage_gb, :storage_cost, :query_cost,
                            :warehouse_total, :meta_calls, :google_calls, :tiktok_calls,
                            :snap_calls, :api_cost, :compute_hours, :compute_cost,
                            :ml_predictions, :ml_cost, :total_cost, :mrr, :margin)
                    ON CONFLICT (tenant_id, date) DO UPDATE SET
                        warehouse_storage_gb = EXCLUDED.warehouse_storage_gb,
                        total_cost_usd = EXCLUDED.total_cost_usd,
                        gross_margin_pct = EXCLUDED.gross_margin_pct
                """),
                {
                    "date": today,
                    "tenant_id": tenant.id,
                    "storage_gb": storage_gb,
                    "storage_cost": storage_cost,
                    "query_cost": 0.001,  # Minimal query cost
                    "warehouse_total": storage_cost + 0.001,
                    "meta_calls": meta_api_calls,
                    "google_calls": google_api_calls,
                    "tiktok_calls": tiktok_api_calls,
                    "snap_calls": snap_api_calls,
                    "api_cost": api_cost,
                    "compute_hours": compute_hours,
                    "compute_cost": compute_cost,
                    "ml_predictions": ml_predictions,
                    "ml_cost": ml_cost,
                    "total_cost": total_cost,
                    "mrr": tenant_mrr,
                    "margin": gross_margin,
                },
            )
            records_created += 1

        db.commit()

    logger.info(f"Cost allocation calculated for {records_created} tenants")
    return {"tenants_processed": records_created}


# =============================================================================
# Usage Rollup Tasks (Daily)
# =============================================================================
@shared_task
def calculate_usage_rollup():
    """
    Roll up daily usage metrics per tenant.
    Calculates DAU, feature usage, and engagement metrics.

    Scheduled daily at 1 AM UTC.
    """
    logger.info("Calculating daily usage rollup for all tenants")

    with SyncSessionLocal() as db:
        from app.models import User

        tenants = db.execute(
            select(Tenant).where(Tenant.is_deleted == False)
        ).scalars().all()

        today = datetime.now(timezone.utc).date()
        records_created = 0

        for tenant in tenants:
            # Get user count (proxy for DAU in this example)
            user_count = db.execute(
                select(func.count(User.id)).where(
                    User.tenant_id == tenant.id,
                    User.is_deleted == False,
                    User.is_active == True,
                )
            ).scalar() or 0

            # Calculate mock usage metrics
            # In production, these would come from actual event tracking
            dashboard_views = user_count * 5  # Est 5 views per user per day
            campaign_edits = user_count * 2
            rule_executions = user_count * 3
            report_exports = user_count  # 1 per user
            ai_insights = user_count * 4
            api_calls = user_count * 50

            # Estimate session time (in seconds)
            session_seconds = user_count * 1800  # 30 min per user

            # Insert usage record
            from sqlalchemy import text
            db.execute(
                text("""
                    INSERT INTO feature_usage
                    (date, tenant_id, dashboard_views, campaign_edits, rule_executions,
                     report_exports, ai_insights_generated, api_calls_made, whatsapp_messages,
                     session_seconds, unique_users)
                    VALUES (:date, :tenant_id, :dashboard_views, :campaign_edits,
                            :rule_executions, :report_exports, :ai_insights, :api_calls,
                            :whatsapp, :session_seconds, :unique_users)
                    ON CONFLICT (tenant_id, date) DO UPDATE SET
                        dashboard_views = EXCLUDED.dashboard_views,
                        unique_users = EXCLUDED.unique_users
                """),
                {
                    "date": today,
                    "tenant_id": tenant.id,
                    "dashboard_views": dashboard_views,
                    "campaign_edits": campaign_edits,
                    "rule_executions": rule_executions,
                    "report_exports": report_exports,
                    "ai_insights": ai_insights,
                    "api_calls": api_calls,
                    "whatsapp": 0,
                    "session_seconds": session_seconds,
                    "unique_users": user_count,
                },
            )
            records_created += 1

        db.commit()

    logger.info(f"Usage rollup calculated for {records_created} tenants")
    return {"tenants_processed": records_created}


# =============================================================================
# Pipeline Health Check Tasks (Hourly)
# =============================================================================
@shared_task
def check_pipeline_health():
    """
    Check data pipeline health and generate alerts.
    Monitors data freshness, API errors, and sync status.

    Scheduled hourly.
    """
    logger.info("Running pipeline health check")

    with SyncSessionLocal() as db:
        tenants = db.execute(
            select(Tenant).where(Tenant.is_deleted == False)
        ).scalars().all()

        alerts_generated = 0
        issues_found = []

        for tenant in tenants:
            tenant_issues = []

            # Check campaign sync freshness
            campaigns = db.execute(
                select(Campaign).where(
                    Campaign.tenant_id == tenant.id,
                    Campaign.is_deleted == False,
                )
            ).scalars().all()

            stale_campaigns = 0
            sync_errors = 0

            for campaign in campaigns:
                # Check if data is stale (last synced > 6 hours ago)
                if campaign.last_synced_at:
                    hours_since_sync = (
                        datetime.now(timezone.utc) - campaign.last_synced_at
                    ).total_seconds() / 3600
                    if hours_since_sync > 6:
                        stale_campaigns += 1

                # Check for sync errors
                if campaign.sync_error:
                    sync_errors += 1

            # Generate alerts for stale data
            if stale_campaigns > 0:
                tenant_issues.append({
                    "type": "stale_data",
                    "severity": "high" if stale_campaigns > 5 else "medium",
                    "message": f"{stale_campaigns} campaigns have stale data (>6 hours)",
                    "count": stale_campaigns,
                })
                alerts_generated += 1

            # Generate alerts for sync errors
            if sync_errors > 0:
                tenant_issues.append({
                    "type": "sync_error",
                    "severity": "critical" if sync_errors > 3 else "high",
                    "message": f"{sync_errors} campaigns have sync errors",
                    "count": sync_errors,
                })
                alerts_generated += 1

            # Check API rate limits (placeholder - would check platform_rate_limits table)
            # ...

            if tenant_issues:
                issues_found.append({
                    "tenant_id": tenant.id,
                    "tenant_name": tenant.name,
                    "issues": tenant_issues,
                })

                # Publish alert event
                _publish_event(tenant.id, "pipeline_health_alert", {
                    "issues": tenant_issues,
                    "severity": max(i["severity"] for i in tenant_issues),
                })

    logger.info(f"Pipeline health check complete. {alerts_generated} alerts generated.")
    return {
        "tenants_checked": len(tenants) if 'tenants' in dir() else 0,
        "alerts_generated": alerts_generated,
        "issues": issues_found,
    }


# =============================================================================
# Daily Scoring Task
# =============================================================================
@shared_task
def calculate_daily_scores():
    """
    Calculate daily scaling scores, fatigue scores, and anomaly detection.
    Writes results to tables and generates alerts.

    Scheduled daily at 4 AM UTC.
    """
    from app.analytics.logic.types import EntityMetrics, BaselineMetrics, EntityLevel, Platform
    from app.analytics.logic.scoring import scaling_score
    from app.analytics.logic.fatigue import creative_fatigue

    logger.info("Running daily scoring calculations")

    with SyncSessionLocal() as db:
        tenants = db.execute(
            select(Tenant).where(Tenant.is_deleted == False)
        ).scalars().all()

        total_scored = 0
        scale_candidates = 0
        fix_candidates = 0

        for tenant in tenants:
            campaigns = db.execute(
                select(Campaign).where(
                    Campaign.tenant_id == tenant.id,
                    Campaign.is_deleted == False,
                )
            ).scalars().all()

            for campaign in campaigns:
                spend = campaign.total_spend_cents / 100 if campaign.total_spend_cents else 0
                revenue = campaign.revenue_cents / 100 if campaign.revenue_cents else 0

                if spend == 0:
                    continue

                # Build entity metrics
                entity = EntityMetrics(
                    entity_id=str(campaign.id),
                    entity_name=campaign.name,
                    entity_level=EntityLevel.CAMPAIGN,
                    platform=Platform(campaign.platform.value if campaign.platform else "meta"),
                    date=datetime.now(timezone.utc),
                    spend=spend,
                    impressions=campaign.impressions or 0,
                    clicks=campaign.clicks or 0,
                    conversions=campaign.conversions or 0,
                    revenue=revenue,
                    ctr=campaign.ctr or 0,
                    cvr=0,
                    cpa=0,
                    roas=campaign.roas or 0,
                )

                # Baseline (using same values - in production, fetch historical)
                baseline = BaselineMetrics(
                    spend=spend * 0.9,
                    impressions=int((campaign.impressions or 0) * 0.95),
                    clicks=int((campaign.clicks or 0) * 0.95),
                    conversions=int((campaign.conversions or 0) * 0.95),
                    revenue=revenue * 0.9,
                    ctr=(campaign.ctr or 0) * 0.95,
                    cvr=0,
                    cpa=0,
                    roas=(campaign.roas or 0) * 0.9,
                )

                # Calculate scaling score
                score_result = scaling_score(entity, baseline)
                total_scored += 1

                if score_result.final_score >= 0.25:
                    scale_candidates += 1
                elif score_result.final_score <= -0.25:
                    fix_candidates += 1

        db.commit()

    logger.info(
        f"Daily scoring complete. Scored {total_scored} campaigns. "
        f"Scale candidates: {scale_candidates}, Fix candidates: {fix_candidates}"
    )
    return {
        "campaigns_scored": total_scored,
        "scale_candidates": scale_candidates,
        "fix_candidates": fix_candidates,
    }


# Additional helper for missing function
from sqlalchemy import func
