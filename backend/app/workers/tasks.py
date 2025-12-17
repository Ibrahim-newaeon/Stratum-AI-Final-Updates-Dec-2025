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
