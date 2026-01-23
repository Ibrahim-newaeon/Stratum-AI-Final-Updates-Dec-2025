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
from sqlalchemy import select
from sqlalchemy.orm import Session

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

def _calculate_task_confidence(campaign_data: list, analysis_type: str = "portfolio") -> float:
    """
    Calculate model-derived confidence for background task predictions.
    
    Args:
        campaign_data: List of campaign dicts with metrics
        analysis_type: Type of analysis (portfolio, campaign, alerts)
    
    Returns:
        Confidence score between 0.0 and 0.95
    """
    if not campaign_data:
        return 0.3  # Minimum confidence for empty data
    
    n = len(campaign_data)
    
    # Base confidence from sample size
    sample_conf = min(0.5, 0.25 + (n / 40))
    
    # Data completeness
    complete = sum(1 for c in campaign_data if c.get("roas", 0) > 0 and c.get("spend", 0) > 0)
    completeness_conf = (complete / n) * 0.25 if n > 0 else 0
    
    # Analysis type adjustments
    type_bonus = {"portfolio": 0.1, "campaign": 0.15, "alerts": 0.2}.get(analysis_type, 0.1)
    
    return round(min(0.95, sample_conf + completeness_conf + type_bonus), 2)




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
    from app.ml.roas_optimizer import ROASOptimizer
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
            confidence_score=_calculate_task_confidence(campaign_data, "portfolio"),
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
                confidence_score=_calculate_task_confidence([camp_analysis.get("current_metrics", {})], "campaign"),
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
                confidence_score=_calculate_task_confidence([{"roas": c.roas, "spend": c.total_spend_cents} for c in campaigns], "alerts"),
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


# =============================================================================
# CDP (Customer Data Platform) Tasks
# =============================================================================

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=3,
)
def compute_cdp_segment(self, tenant_id: int, segment_id: str):
    """
    Compute membership for a specific CDP segment.

    Evaluates all profiles against segment rules and updates membership.
    Idempotent: Safe to retry without side effects.
    """
    from uuid import UUID
    from app.models.cdp import CDPSegment, CDPProfile, CDPSegmentMembership, SegmentStatus

    logger.info(f"Computing CDP segment {segment_id} for tenant {tenant_id}")

    with SyncSessionLocal() as db:
        segment = db.execute(
            select(CDPSegment).where(
                CDPSegment.id == UUID(segment_id),
                CDPSegment.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()

        if not segment:
            logger.warning(f"Segment {segment_id} not found")
            return {"status": "not_found", "segment_id": segment_id}

        try:
            # Update status to computing
            segment.status = SegmentStatus.COMPUTING
            db.commit()

            start_time = datetime.now(timezone.utc)

            # Clear existing memberships for fresh computation
            db.execute(
                select(CDPSegmentMembership).where(
                    CDPSegmentMembership.segment_id == segment.id
                )
            )
            from sqlalchemy import delete
            db.execute(
                delete(CDPSegmentMembership).where(
                    CDPSegmentMembership.segment_id == segment.id
                )
            )

            # Get all profiles for this tenant
            profiles = db.execute(
                select(CDPProfile).where(CDPProfile.tenant_id == tenant_id)
            ).scalars().all()

            # Evaluate each profile against segment rules
            matched_count = 0
            rules = segment.rules or {}

            for profile in profiles:
                match_result = _evaluate_segment_rules(profile, rules)

                if match_result["matched"]:
                    membership = CDPSegmentMembership(
                        tenant_id=tenant_id,
                        segment_id=segment.id,
                        profile_id=profile.id,
                        match_score=match_result.get("score", 1.0),
                    )
                    db.add(membership)
                    matched_count += 1

            # Update segment stats
            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            segment.profile_count = matched_count
            segment.status = SegmentStatus.ACTIVE
            segment.last_computed_at = end_time
            segment.computation_duration_ms = duration_ms

            # Set next refresh time
            if segment.auto_refresh:
                segment.next_refresh_at = end_time + timedelta(hours=segment.refresh_interval_hours)

            db.commit()

            # Publish event
            _publish_event(tenant_id, "segment_computed", {
                "segment_id": segment_id,
                "segment_name": segment.name,
                "profile_count": matched_count,
                "duration_ms": duration_ms,
            })

            logger.info(f"Segment {segment_id} computed: {matched_count} profiles matched in {duration_ms}ms")
            return {
                "status": "success",
                "segment_id": segment_id,
                "profile_count": matched_count,
                "duration_ms": duration_ms,
            }

        except Exception as e:
            segment.status = SegmentStatus.STALE
            db.commit()
            logger.error(f"Failed to compute segment {segment_id}: {e}")
            raise


def _evaluate_segment_rules(profile, rules: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate a profile against segment rules."""
    try:
        logic = rules.get("logic", "and")
        conditions = rules.get("conditions", [])
        groups = rules.get("groups", [])

        if not conditions and not groups:
            return {"matched": False, "score": 0.0}

        condition_results = []

        # Evaluate conditions
        for condition in conditions:
            result = _evaluate_condition_single(profile, condition)
            condition_results.append(result)

        # Evaluate nested groups recursively
        for group in groups:
            group_result = _evaluate_segment_rules(profile, group)
            condition_results.append(group_result["matched"])

        # Apply logic
        if not condition_results:
            matched = False
        elif logic == "and":
            matched = all(condition_results)
        else:  # or
            matched = any(condition_results)

        # Calculate match score (percentage of conditions met)
        score = sum(1 for r in condition_results if r) / len(condition_results) if condition_results else 0.0

        return {"matched": matched, "score": score}

    except Exception as e:
        logger.warning(f"Error evaluating segment rules: {e}")
        return {"matched": False, "score": 0.0}


def _evaluate_condition_single(profile, condition: Dict[str, Any]) -> bool:
    """Evaluate a single condition against a profile."""
    field = condition.get("field", "")
    operator = condition.get("operator", "equals")
    value = condition.get("value")

    # Get field value from profile
    if field.startswith("profile_data."):
        data_field = field[13:]  # Remove "profile_data." prefix
        field_value = (profile.profile_data or {}).get(data_field)
    elif field.startswith("computed_traits."):
        trait_field = field[16:]  # Remove "computed_traits." prefix
        field_value = (profile.computed_traits or {}).get(trait_field)
    else:
        field_value = getattr(profile, field, None)

    if field_value is None and operator not in ("is_null", "is_not_null", "not_exists"):
        return False

    try:
        # Operators
        if operator == "equals":
            return field_value == value
        elif operator == "not_equals":
            return field_value != value
        elif operator == "greater_than":
            return float(field_value) > float(value)
        elif operator == "less_than":
            return float(field_value) < float(value)
        elif operator == "gte":
            return float(field_value) >= float(value)
        elif operator == "lte":
            return float(field_value) <= float(value)
        elif operator == "contains":
            return str(value).lower() in str(field_value).lower()
        elif operator == "not_contains":
            return str(value).lower() not in str(field_value).lower()
        elif operator == "starts_with":
            return str(field_value).lower().startswith(str(value).lower())
        elif operator == "ends_with":
            return str(field_value).lower().endswith(str(value).lower())
        elif operator == "in":
            return field_value in (value if isinstance(value, list) else [value])
        elif operator == "not_in":
            return field_value not in (value if isinstance(value, list) else [value])
        elif operator == "is_null":
            return field_value is None
        elif operator == "is_not_null":
            return field_value is not None
        elif operator == "exists":
            return field_value is not None
        elif operator == "not_exists":
            return field_value is None
        elif operator == "within_last":
            # value is number of days
            if isinstance(field_value, datetime):
                return field_value >= datetime.now(timezone.utc) - timedelta(days=int(value))
            return False
        elif operator == "not_within_last":
            if isinstance(field_value, datetime):
                return field_value < datetime.now(timezone.utc) - timedelta(days=int(value))
            return False
        elif operator == "between":
            if isinstance(value, list) and len(value) == 2:
                return float(value[0]) <= float(field_value) <= float(value[1])
            return False
        else:
            return False

    except (ValueError, TypeError):
        return False


@shared_task
def compute_all_cdp_segments(tenant_id: int = None):
    """
    Compute all CDP segments that need refresh.

    If tenant_id is provided, only compute for that tenant.
    Otherwise, compute for all tenants.
    """
    from app.models.cdp import CDPSegment, SegmentStatus

    logger.info("Computing all CDP segments" + (f" for tenant {tenant_id}" if tenant_id else ""))

    with SyncSessionLocal() as db:
        now = datetime.now(timezone.utc)

        # Build query for segments needing refresh
        query = select(CDPSegment).where(
            CDPSegment.auto_refresh == True,
            CDPSegment.status.in_([SegmentStatus.ACTIVE, SegmentStatus.STALE, SegmentStatus.DRAFT]),
        )

        if tenant_id:
            query = query.where(CDPSegment.tenant_id == tenant_id)

        # Get segments where next_refresh_at is in the past or null
        segments = db.execute(query).scalars().all()

        task_count = 0
        for segment in segments:
            # Check if refresh is due
            if segment.next_refresh_at is None or segment.next_refresh_at <= now:
                compute_cdp_segment.delay(segment.tenant_id, str(segment.id))
                task_count += 1

    logger.info(f"Queued {task_count} CDP segment computation tasks")
    return {"tasks_queued": task_count}


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=3,
)
def compute_cdp_rfm(self, tenant_id: int, config: Optional[Dict] = None):
    """
    Compute RFM scores for all profiles of a tenant.

    Uses purchase events to calculate Recency, Frequency, and Monetary values.
    Assigns RFM segment based on score thresholds.
    """
    from app.models.cdp import CDPProfile, CDPEvent
    from decimal import Decimal

    logger.info(f"Computing RFM scores for tenant {tenant_id}")

    config = config or {}
    purchase_event = config.get("purchase_event_name", "purchase")
    revenue_property = config.get("revenue_property", "revenue")
    analysis_window_days = config.get("analysis_window_days", 365)

    with SyncSessionLocal() as db:
        start_time = datetime.now(timezone.utc)
        window_start = start_time - timedelta(days=analysis_window_days)

        # Get all profiles for this tenant
        profiles = db.execute(
            select(CDPProfile).where(CDPProfile.tenant_id == tenant_id)
        ).scalars().all()

        segment_counts = {}
        profiles_processed = 0

        for profile in profiles:
            # Get purchase events for this profile
            purchase_events = db.execute(
                select(CDPEvent).where(
                    CDPEvent.profile_id == profile.id,
                    CDPEvent.event_name == purchase_event,
                    CDPEvent.event_time >= window_start,
                )
            ).scalars().all()

            if not purchase_events:
                # No purchases - skip or assign 'lost'/'hibernating'
                rfm_data = {
                    "recency_days": analysis_window_days,
                    "frequency": 0,
                    "monetary": 0,
                    "recency_score": 1,
                    "frequency_score": 1,
                    "monetary_score": 1,
                    "rfm_score": 1.0,
                    "rfm_segment": "lost",
                    "calculated_at": start_time.isoformat(),
                }
            else:
                # Calculate R, F, M values
                most_recent = max(e.event_time for e in purchase_events)
                recency_days = (start_time - most_recent).days
                frequency = len(purchase_events)

                total_revenue = 0.0
                for e in purchase_events:
                    props = e.properties or {}
                    rev = props.get(revenue_property, 0)
                    if isinstance(rev, (int, float, Decimal)):
                        total_revenue += float(rev)

                # Calculate scores (1-5)
                r_score = _calculate_rfm_score(recency_days, [7, 30, 90, 180], reverse=True)
                f_score = _calculate_rfm_score(frequency, [1, 2, 5, 10])
                m_score = _calculate_rfm_score(total_revenue, [50, 100, 500, 1000])

                # Calculate composite RFM score
                rfm_composite = (r_score + f_score + m_score) / 3.0

                # Determine segment
                segment = _determine_rfm_segment(r_score, f_score, m_score)

                rfm_data = {
                    "recency_days": recency_days,
                    "frequency": frequency,
                    "monetary": total_revenue,
                    "recency_score": r_score,
                    "frequency_score": f_score,
                    "monetary_score": m_score,
                    "rfm_score": round(rfm_composite, 2),
                    "rfm_segment": segment,
                    "calculated_at": start_time.isoformat(),
                }

            # Update profile computed traits with RFM data
            computed_traits = profile.computed_traits or {}
            computed_traits["rfm"] = rfm_data
            profile.computed_traits = computed_traits

            # Count segments
            seg = rfm_data["rfm_segment"]
            segment_counts[seg] = segment_counts.get(seg, 0) + 1
            profiles_processed += 1

        db.commit()

        duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

        # Publish event
        _publish_event(tenant_id, "rfm_computed", {
            "profiles_processed": profiles_processed,
            "segment_distribution": segment_counts,
            "duration_ms": duration_ms,
        })

        logger.info(f"RFM computed for {profiles_processed} profiles in {duration_ms}ms")
        return {
            "status": "success",
            "profiles_processed": profiles_processed,
            "segment_distribution": segment_counts,
            "duration_ms": duration_ms,
        }


def _calculate_rfm_score(value: float, thresholds: List[float], reverse: bool = False) -> int:
    """Calculate RFM score (1-5) based on value and thresholds."""
    score = 1
    for i, threshold in enumerate(thresholds, start=2):
        if reverse:
            if value <= threshold:
                score = 6 - i + 1  # Higher score for lower values (recency)
        else:
            if value >= threshold:
                score = i
    return score


def _determine_rfm_segment(r: int, f: int, m: int) -> str:
    """Determine RFM segment based on R, F, M scores."""
    # Champions: High R, F, M
    if r >= 4 and f >= 4 and m >= 4:
        return "champions"
    # Loyal Customers: High F & M
    elif f >= 4 and m >= 4:
        return "loyal_customers"
    # Potential Loyalists: High R, medium F
    elif r >= 4 and f >= 2 and f < 4:
        return "potential_loyalists"
    # New Customers: High R, low F
    elif r >= 4 and f == 1:
        return "new_customers"
    # Promising: High R, low F & M
    elif r >= 4 and f < 2:
        return "promising"
    # Need Attention: Medium R, F, M
    elif r >= 3 and r < 4 and f >= 3 and m >= 3:
        return "need_attention"
    # About to Sleep: Low R, moderate F
    elif r >= 2 and r < 3 and f >= 2:
        return "about_to_sleep"
    # At Risk: Low R, high F
    elif r < 3 and f >= 4:
        return "at_risk"
    # Cannot Lose: Very low R, very high F & M
    elif r == 1 and f >= 4 and m >= 4:
        return "cannot_lose"
    # Hibernating: Very low R, low F
    elif r < 2 and f < 2:
        return "hibernating"
    # Lost: Lowest scores
    elif r == 1 and f == 1:
        return "lost"
    else:
        return "other"


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=3,
)
def compute_cdp_traits(self, tenant_id: int, trait_id: Optional[str] = None):
    """
    Compute computed traits for all profiles of a tenant.

    If trait_id is provided, only compute that specific trait.
    Otherwise, compute all active traits.
    """
    from uuid import UUID
    from app.models.cdp import CDPProfile, CDPComputedTrait

    logger.info(f"Computing CDP traits for tenant {tenant_id}" + (f" (trait: {trait_id})" if trait_id else ""))

    with SyncSessionLocal() as db:
        start_time = datetime.now(timezone.utc)

        # Get traits to compute
        trait_query = select(CDPComputedTrait).where(
            CDPComputedTrait.tenant_id == tenant_id,
            CDPComputedTrait.is_active == True,
        )
        if trait_id:
            trait_query = trait_query.where(CDPComputedTrait.id == UUID(trait_id))

        traits = db.execute(trait_query).scalars().all()

        if not traits:
            return {"status": "no_traits", "computed": 0}

        # Get all profiles
        profiles = db.execute(
            select(CDPProfile).where(CDPProfile.tenant_id == tenant_id)
        ).scalars().all()

        profiles_updated = 0
        errors = 0

        for profile in profiles:
            computed = profile.computed_traits or {}

            for trait in traits:
                try:
                    value = _compute_trait_value(db, profile, trait)
                    computed[trait.name] = value
                except Exception as e:
                    logger.warning(f"Error computing trait {trait.name} for profile {profile.id}: {e}")
                    errors += 1

            profile.computed_traits = computed
            profiles_updated += 1

        # Update trait metadata
        for trait in traits:
            trait.last_computed_at = datetime.now(timezone.utc)

        db.commit()

        duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

        logger.info(f"Traits computed for {profiles_updated} profiles in {duration_ms}ms")
        return {
            "status": "success",
            "profiles_processed": profiles_updated,
            "traits_computed": len(traits),
            "errors": errors,
            "duration_ms": duration_ms,
        }


def _compute_trait_value(db, profile, trait) -> Any:
    """Compute a single trait value for a profile."""
    from app.models.cdp import CDPEvent

    source_config = trait.source_config or {}
    event_name = source_config.get("event_name")
    property_name = source_config.get("property")
    time_window_days = source_config.get("time_window_days")

    # Build event query
    query = select(CDPEvent).where(CDPEvent.profile_id == profile.id)

    if event_name:
        query = query.where(CDPEvent.event_name == event_name)

    if time_window_days:
        window_start = datetime.now(timezone.utc) - timedelta(days=time_window_days)
        query = query.where(CDPEvent.event_time >= window_start)

    events = db.execute(query).scalars().all()

    trait_type = trait.trait_type
    default_value = trait.default_value

    if not events:
        return default_value

    values = []
    if property_name:
        for e in events:
            props = e.properties or {}
            if property_name in props:
                values.append(props[property_name])

    # Calculate based on trait type
    if trait_type == "count":
        return len(events)
    elif trait_type == "sum":
        return sum(float(v) for v in values if isinstance(v, (int, float)))
    elif trait_type == "average":
        numeric = [float(v) for v in values if isinstance(v, (int, float))]
        return sum(numeric) / len(numeric) if numeric else default_value
    elif trait_type == "min":
        numeric = [float(v) for v in values if isinstance(v, (int, float))]
        return min(numeric) if numeric else default_value
    elif trait_type == "max":
        numeric = [float(v) for v in values if isinstance(v, (int, float))]
        return max(numeric) if numeric else default_value
    elif trait_type == "first":
        sorted_events = sorted(events, key=lambda e: e.event_time)
        if sorted_events and property_name:
            return (sorted_events[0].properties or {}).get(property_name, default_value)
        return events[0].event_time.isoformat() if events else default_value
    elif trait_type == "last":
        sorted_events = sorted(events, key=lambda e: e.event_time, reverse=True)
        if sorted_events and property_name:
            return (sorted_events[0].properties or {}).get(property_name, default_value)
        return events[-1].event_time.isoformat() if events else default_value
    elif trait_type == "unique_count":
        return len(set(values))
    elif trait_type == "exists":
        return len(events) > 0
    else:
        return default_value


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=3,
)
def compute_cdp_funnel(self, tenant_id: int, funnel_id: str):
    """
    Compute metrics for a specific CDP funnel.

    Evaluates all profiles through funnel steps and updates conversion metrics.
    """
    from uuid import UUID
    from app.models.cdp import CDPFunnel, CDPFunnelEntry, CDPProfile, CDPEvent, FunnelStatus

    logger.info(f"Computing CDP funnel {funnel_id} for tenant {tenant_id}")

    with SyncSessionLocal() as db:
        funnel = db.execute(
            select(CDPFunnel).where(
                CDPFunnel.id == UUID(funnel_id),
                CDPFunnel.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()

        if not funnel:
            logger.warning(f"Funnel {funnel_id} not found")
            return {"status": "not_found", "funnel_id": funnel_id}

        try:
            # Update status
            funnel.status = FunnelStatus.COMPUTING
            db.commit()

            start_time = datetime.now(timezone.utc)
            steps = funnel.steps or []

            if len(steps) < 2:
                funnel.status = FunnelStatus.STALE
                db.commit()
                return {"status": "error", "message": "Funnel needs at least 2 steps"}

            # Clear existing entries
            from sqlalchemy import delete
            db.execute(
                delete(CDPFunnelEntry).where(CDPFunnelEntry.funnel_id == funnel.id)
            )

            # Get conversion window
            conversion_window = timedelta(days=funnel.conversion_window_days)
            step_timeout = timedelta(hours=funnel.step_timeout_hours) if funnel.step_timeout_hours else None

            # Get all profiles
            profiles = db.execute(
                select(CDPProfile).where(CDPProfile.tenant_id == tenant_id)
            ).scalars().all()

            total_entered = 0
            total_converted = 0
            step_counts = [0] * len(steps)
            step_metrics = []

            for profile in profiles:
                # Get all events for this profile
                events = db.execute(
                    select(CDPEvent).where(CDPEvent.profile_id == profile.id)
                    .order_by(CDPEvent.event_time)
                ).scalars().all()

                if not events:
                    continue

                # Track progress through funnel
                entry_result = _track_funnel_progress(events, steps, conversion_window, step_timeout)

                if entry_result["entered"]:
                    total_entered += 1
                    step_counts[0] += 1

                    # Create funnel entry
                    entry = CDPFunnelEntry(
                        tenant_id=tenant_id,
                        funnel_id=funnel.id,
                        profile_id=profile.id,
                        entered_at=entry_result["entered_at"],
                        current_step=entry_result["current_step"],
                        completed_steps=entry_result["completed_steps"],
                        is_converted=entry_result["is_converted"],
                        converted_at=entry_result.get("converted_at"),
                        step_timestamps=entry_result["step_timestamps"],
                        total_duration_seconds=entry_result.get("total_duration_seconds"),
                    )
                    db.add(entry)

                    # Update step counts
                    for i in range(1, entry_result["completed_steps"]):
                        if i < len(step_counts):
                            step_counts[i] += 1

                    if entry_result["is_converted"]:
                        total_converted += 1

            # Calculate step metrics
            for i, step in enumerate(steps):
                count = step_counts[i] if i < len(step_counts) else 0
                prev_count = step_counts[i - 1] if i > 0 else total_entered

                conversion_rate = (count / total_entered * 100) if total_entered > 0 else 0
                drop_off = prev_count - count if i > 0 else 0
                drop_off_rate = (drop_off / prev_count * 100) if prev_count > 0 else 0

                step_metrics.append({
                    "step": i + 1,
                    "name": step.get("step_name", f"Step {i + 1}"),
                    "event_name": step.get("event_name", ""),
                    "count": count,
                    "conversion_rate": round(conversion_rate, 2),
                    "drop_off_rate": round(drop_off_rate, 2),
                    "drop_off_count": drop_off,
                })

            # Update funnel metrics
            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

            funnel.total_entered = total_entered
            funnel.total_converted = total_converted
            funnel.overall_conversion_rate = (total_converted / total_entered * 100) if total_entered > 0 else 0
            funnel.step_metrics = step_metrics
            funnel.status = FunnelStatus.ACTIVE
            funnel.last_computed_at = datetime.now(timezone.utc)
            funnel.computation_duration_ms = duration_ms

            if funnel.auto_refresh:
                funnel.next_refresh_at = datetime.now(timezone.utc) + timedelta(hours=funnel.refresh_interval_hours)

            db.commit()

            # Publish event
            _publish_event(tenant_id, "funnel_computed", {
                "funnel_id": funnel_id,
                "funnel_name": funnel.name,
                "total_entered": total_entered,
                "total_converted": total_converted,
                "conversion_rate": funnel.overall_conversion_rate,
            })

            logger.info(f"Funnel {funnel_id} computed: {total_entered} entered, {total_converted} converted")
            return {
                "status": "success",
                "funnel_id": funnel_id,
                "total_entered": total_entered,
                "total_converted": total_converted,
                "conversion_rate": funnel.overall_conversion_rate,
                "duration_ms": duration_ms,
            }

        except Exception as e:
            funnel.status = FunnelStatus.STALE
            db.commit()
            logger.error(f"Failed to compute funnel {funnel_id}: {e}")
            raise


def _track_funnel_progress(events, steps, conversion_window, step_timeout) -> Dict[str, Any]:
    """Track a profile's progress through funnel steps."""
    if not events or not steps:
        return {"entered": False}

    first_step = steps[0]
    first_step_event = first_step.get("event_name")

    # Find first matching event for step 1
    entered_at = None
    for event in events:
        if event.event_name == first_step_event:
            if _check_step_conditions(event, first_step.get("conditions", [])):
                entered_at = event.event_time
                break

    if not entered_at:
        return {"entered": False}

    # Track progress through remaining steps
    step_timestamps = {"1": entered_at.isoformat()}
    current_step = 1
    completed_steps = 1
    last_step_time = entered_at

    for i, step in enumerate(steps[1:], start=2):
        step_event = step.get("event_name")
        step_conditions = step.get("conditions", [])

        # Find matching event after previous step
        found = False
        for event in events:
            if event.event_time <= last_step_time:
                continue

            # Check conversion window
            if event.event_time > entered_at + conversion_window:
                break

            # Check step timeout
            if step_timeout and event.event_time > last_step_time + step_timeout:
                break

            if event.event_name == step_event:
                if _check_step_conditions(event, step_conditions):
                    step_timestamps[str(i)] = event.event_time.isoformat()
                    current_step = i
                    completed_steps = i
                    last_step_time = event.event_time
                    found = True
                    break

        if not found:
            break

    is_converted = completed_steps == len(steps)
    converted_at = None
    total_duration_seconds = None

    if is_converted:
        last_step_str = str(len(steps))
        if last_step_str in step_timestamps:
            from dateutil.parser import parse
            converted_at = parse(step_timestamps[last_step_str])
            total_duration_seconds = int((converted_at - entered_at).total_seconds())

    return {
        "entered": True,
        "entered_at": entered_at,
        "current_step": current_step,
        "completed_steps": completed_steps,
        "is_converted": is_converted,
        "converted_at": converted_at,
        "step_timestamps": step_timestamps,
        "total_duration_seconds": total_duration_seconds,
    }


def _check_step_conditions(event, conditions) -> bool:
    """Check if an event matches step conditions."""
    if not conditions:
        return True

    props = event.properties or {}

    for condition in conditions:
        field = condition.get("field", "")
        operator = condition.get("operator", "equals")
        value = condition.get("value")

        field_value = props.get(field)

        if operator == "equals" and field_value != value:
            return False
        elif operator == "not_equals" and field_value == value:
            return False
        elif operator == "greater_than" and not (field_value and float(field_value) > float(value)):
            return False
        elif operator == "less_than" and not (field_value and float(field_value) < float(value)):
            return False
        elif operator == "contains" and not (field_value and str(value) in str(field_value)):
            return False
        elif operator == "exists" and field_value is None:
            return False

    return True


@shared_task
def compute_all_cdp_funnels(tenant_id: int = None):
    """
    Compute all CDP funnels that need refresh.

    If tenant_id is provided, only compute for that tenant.
    """
    from app.models.cdp import CDPFunnel, FunnelStatus

    logger.info("Computing all CDP funnels" + (f" for tenant {tenant_id}" if tenant_id else ""))

    with SyncSessionLocal() as db:
        now = datetime.now(timezone.utc)

        query = select(CDPFunnel).where(
            CDPFunnel.auto_refresh == True,
            CDPFunnel.status.in_([FunnelStatus.ACTIVE, FunnelStatus.STALE, FunnelStatus.DRAFT]),
        )

        if tenant_id:
            query = query.where(CDPFunnel.tenant_id == tenant_id)

        funnels = db.execute(query).scalars().all()

        task_count = 0
        for funnel in funnels:
            if funnel.next_refresh_at is None or funnel.next_refresh_at <= now:
                compute_cdp_funnel.delay(funnel.tenant_id, str(funnel.id))
                task_count += 1

    logger.info(f"Queued {task_count} CDP funnel computation tasks")
    return {"tasks_queued": task_count}


# =============================================================================
# CMS (Content Management System) Tasks - 2026 Workflow
# =============================================================================

@shared_task
def publish_scheduled_cms_posts():
    """
    Process scheduled CMS posts and publish them when their scheduled_at time arrives.

    2026 Standard: Automated scheduled publishing with audit trail.
    This task runs every minute via Celery Beat.
    """
    from uuid import UUID
    from app.models.cms import CMSPost, CMSPostStatus, CMSWorkflowAction, CMSWorkflowLog

    logger.info("Processing scheduled CMS posts")

    with SyncSessionLocal() as db:
        now = datetime.now(timezone.utc)

        # Find all posts that are scheduled and ready to publish
        posts_to_publish = db.execute(
            select(CMSPost).where(
                CMSPost.status == CMSPostStatus.SCHEDULED.value,
                CMSPost.scheduled_at <= now,
                CMSPost.is_deleted == False,
            )
        ).scalars().all()

        published_count = 0
        failed_count = 0

        for post in posts_to_publish:
            try:
                # Store previous status for audit
                previous_status = post.status

                # Update post status to published
                post.status = CMSPostStatus.PUBLISHED.value
                post.published_at = now

                # Create workflow log entry
                workflow_log = CMSWorkflowLog(
                    post_id=post.id,
                    action=CMSWorkflowAction.PUBLISHED.value,
                    from_status=previous_status,
                    to_status=CMSPostStatus.PUBLISHED.value,
                    performed_by_id=post.approved_by_id,  # Use the approver as the publisher
                    comment=f"Auto-published via scheduled publishing (scheduled_at: {post.scheduled_at.isoformat()})",
                    version_number=post.version,
                    metadata={
                        "scheduled_at": post.scheduled_at.isoformat(),
                        "published_at": now.isoformat(),
                        "auto_published": True,
                    },
                )
                db.add(workflow_log)

                db.commit()
                published_count += 1

                logger.info(f"Published scheduled CMS post: {post.id} - {post.title}")

            except Exception as e:
                db.rollback()
                failed_count += 1
                logger.error(f"Failed to publish scheduled CMS post {post.id}: {e}")

        logger.info(f"Scheduled CMS publishing complete: {published_count} published, {failed_count} failed")
        return {
            "status": "success",
            "published_count": published_count,
            "failed_count": failed_count,
            "timestamp": now.isoformat(),
        }


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=3,
)
def publish_cms_post(self, post_id: str, published_by_id: int = None):
    """
    Publish a single CMS post immediately.

    Args:
        post_id: UUID of the post to publish
        published_by_id: User ID who triggered the publish (optional)
    """
    from uuid import UUID
    from app.models.cms import CMSPost, CMSPostStatus, CMSWorkflowAction, CMSWorkflowLog

    logger.info(f"Publishing CMS post {post_id}")

    with SyncSessionLocal() as db:
        post = db.execute(
            select(CMSPost).where(
                CMSPost.id == UUID(post_id),
                CMSPost.is_deleted == False,
            )
        ).scalar_one_or_none()

        if not post:
            logger.warning(f"CMS post {post_id} not found")
            return {"status": "not_found", "post_id": post_id}

        # Check if post is in a publishable state
        publishable_states = [
            CMSPostStatus.APPROVED.value,
            CMSPostStatus.SCHEDULED.value,
        ]
        if post.status not in publishable_states:
            logger.warning(f"CMS post {post_id} cannot be published (status: {post.status})")
            return {
                "status": "error",
                "message": f"Post cannot be published from status: {post.status}",
                "post_id": post_id,
            }

        try:
            now = datetime.now(timezone.utc)
            previous_status = post.status

            # Update post
            post.status = CMSPostStatus.PUBLISHED.value
            post.published_at = now

            # Create workflow log
            workflow_log = CMSWorkflowLog(
                post_id=post.id,
                action=CMSWorkflowAction.PUBLISHED.value,
                from_status=previous_status,
                to_status=CMSPostStatus.PUBLISHED.value,
                performed_by_id=published_by_id or post.approved_by_id,
                comment="Published via async task",
                version_number=post.version,
                metadata={
                    "published_at": now.isoformat(),
                    "triggered_by": published_by_id,
                },
            )
            db.add(workflow_log)

            db.commit()

            logger.info(f"Published CMS post: {post_id} - {post.title}")
            return {
                "status": "success",
                "post_id": post_id,
                "title": post.title,
                "published_at": now.isoformat(),
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to publish CMS post {post_id}: {e}")
            raise


@shared_task
def create_cms_post_version(post_id: str, created_by_id: int, change_summary: str = None):
    """
    Create a version snapshot of a CMS post.

    Called automatically when content is updated.
    """
    from uuid import UUID
    from app.models.cms import CMSPost, CMSPostVersion

    logger.info(f"Creating version snapshot for CMS post {post_id}")

    with SyncSessionLocal() as db:
        post = db.execute(
            select(CMSPost).where(CMSPost.id == UUID(post_id))
        ).scalar_one_or_none()

        if not post:
            logger.warning(f"CMS post {post_id} not found")
            return {"status": "not_found", "post_id": post_id}

        try:
            # Create version snapshot
            version = CMSPostVersion(
                post_id=post.id,
                version=post.version,
                title=post.title,
                slug=post.slug,
                excerpt=post.excerpt,
                content=post.content,
                content_json=post.content_json,
                meta_title=post.meta_title,
                meta_description=post.meta_description,
                featured_image_url=post.featured_image_url,
                created_by_id=created_by_id,
                change_summary=change_summary,
                word_count=post.word_count,
                reading_time_minutes=post.reading_time_minutes,
            )
            db.add(version)

            # Increment post version
            post.version += 1
            post.current_version_id = version.id

            db.commit()

            logger.info(f"Created version {version.version} for CMS post {post_id}")
            return {
                "status": "success",
                "post_id": post_id,
                "version": version.version,
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create version for CMS post {post_id}: {e}")
            raise
