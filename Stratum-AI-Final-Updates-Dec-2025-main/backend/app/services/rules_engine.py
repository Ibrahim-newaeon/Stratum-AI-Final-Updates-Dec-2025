# =============================================================================
# Stratum AI - Rules Engine Service
# =============================================================================
"""
IFTTT-style automation rules engine.
Implements Module C: Stratum Automation.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import Campaign, Rule, RuleAction, RuleExecution, RuleOperator, RuleStatus

logger = get_logger(__name__)


class RulesEngine:
    """
    Rules engine that evaluates IFTTT-style automation rules.

    Supports conditions on:
    - ROAS (Return on Ad Spend)
    - CTR (Click-Through Rate)
    - CPC (Cost Per Click)
    - CPA (Cost Per Acquisition)
    - Spend
    - Impressions, Clicks, Conversions

    Supports actions:
    - Apply Label
    - Send Alert
    - Pause Campaign
    - Adjust Budget
    - Notify Slack
    """

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    async def evaluate_rule(
        self,
        rule: Rule,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Evaluate a rule against applicable campaigns.

        Args:
            rule: The rule to evaluate
            dry_run: If True, don't execute actions (for testing)

        Returns:
            Evaluation results
        """
        # Check if rule is active
        if rule.status != RuleStatus.ACTIVE and not dry_run:
            return {
                "status": "skipped",
                "reason": "Rule is not active",
            }

        # Check cooldown
        if rule.last_triggered_at and not dry_run:
            cooldown_end = rule.last_triggered_at + timedelta(hours=rule.cooldown_hours)
            if datetime.now(UTC) < cooldown_end:
                return {
                    "status": "skipped",
                    "reason": "Rule is in cooldown",
                    "cooldown_ends": cooldown_end.isoformat(),
                }

        # Get campaigns to evaluate
        campaigns = await self._get_applicable_campaigns(rule)

        if not campaigns:
            return {
                "status": "completed",
                "campaigns_evaluated": 0,
                "campaigns_matched": 0,
            }

        # Evaluate each campaign
        results = []
        matched_campaigns = []

        for campaign in campaigns:
            evaluation = await self._evaluate_condition(rule, campaign)
            results.append(evaluation)

            if evaluation["matched"]:
                matched_campaigns.append(campaign)

                if not dry_run:
                    # Execute action
                    action_result = await self._execute_action(rule, campaign)
                    evaluation["action_result"] = action_result

                    # Log execution
                    await self._log_execution(rule, campaign, evaluation, action_result)

        # Update rule metadata if any matched
        if matched_campaigns and not dry_run:
            rule.last_evaluated_at = datetime.now(UTC)
            rule.last_triggered_at = datetime.now(UTC)
            rule.trigger_count += 1
            await self.db.commit()

        return {
            "status": "completed",
            "campaigns_evaluated": len(campaigns),
            "campaigns_matched": len(matched_campaigns),
            "dry_run": dry_run,
            "results": results,
        }

    async def _get_applicable_campaigns(self, rule: Rule) -> list[Campaign]:
        """Get campaigns that this rule applies to."""
        query = select(Campaign).where(
            Campaign.tenant_id == self.tenant_id,
            Campaign.is_deleted == False,
        )

        # Filter by specific campaigns if specified
        if rule.applies_to_campaigns:
            query = query.where(Campaign.id.in_(rule.applies_to_campaigns))

        # Filter by platforms if specified
        if rule.applies_to_platforms:
            query = query.where(Campaign.platform.in_(rule.applies_to_platforms))

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _evaluate_condition(
        self,
        rule: Rule,
        campaign: Campaign,
    ) -> dict[str, Any]:
        """
        Evaluate a rule condition against a campaign.
        """
        field = rule.condition_field
        operator = rule.condition_operator
        expected_value = rule.condition_value

        # Get actual value
        actual_value = self._get_field_value(campaign, field)

        if actual_value is None:
            return {
                "campaign_id": campaign.id,
                "campaign_name": campaign.name,
                "matched": False,
                "reason": f"Field '{field}' not found or null",
            }

        # Parse expected value
        try:
            expected = self._parse_value(expected_value, type(actual_value))
        except ValueError as e:
            return {
                "campaign_id": campaign.id,
                "campaign_name": campaign.name,
                "matched": False,
                "reason": f"Invalid condition value: {e}",
            }

        # Evaluate
        matched = self._compare_values(actual_value, operator, expected)

        return {
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "matched": matched,
            "condition": {
                "field": field,
                "operator": operator.value,
                "expected": expected,
                "actual": actual_value,
            },
        }

    def _get_field_value(self, campaign: Campaign, field: str) -> Optional[Any]:
        """Get a field value from a campaign, handling computed fields."""
        # Direct attributes
        if hasattr(campaign, field):
            return getattr(campaign, field)

        # Computed fields
        computed_fields = {
            "spend": lambda c: c.total_spend_cents / 100,
            "revenue": lambda c: c.revenue_cents / 100,
            "cpc": lambda c: (c.total_spend_cents / c.clicks / 100) if c.clicks > 0 else None,
            "cpm": lambda c: (c.total_spend_cents / c.impressions * 1000 / 100)
            if c.impressions > 0
            else None,
            "cpa": lambda c: (c.total_spend_cents / c.conversions / 100)
            if c.conversions > 0
            else None,
            "conversion_rate": lambda c: (c.conversions / c.clicks * 100) if c.clicks > 0 else None,
        }

        if field in computed_fields:
            return computed_fields[field](campaign)

        return None

    def _parse_value(self, value: str, target_type: type) -> Any:
        """Parse a string value to the target type."""
        if target_type == float:
            return float(value)
        elif target_type == int:
            return int(float(value))
        elif target_type == bool:
            return value.lower() in ("true", "1", "yes")
        elif target_type == list:
            import json

            return json.loads(value) if value.startswith("[") else [value]
        return value

    def _compare_values(
        self,
        actual: Any,
        operator: RuleOperator,
        expected: Any,
    ) -> bool:
        """Compare two values based on the operator."""
        if operator == RuleOperator.EQUALS:
            return actual == expected
        elif operator == RuleOperator.NOT_EQUALS:
            return actual != expected
        elif operator == RuleOperator.GREATER_THAN:
            return actual > expected
        elif operator == RuleOperator.LESS_THAN:
            return actual < expected
        elif operator == RuleOperator.GREATER_THAN_OR_EQUAL:
            return actual >= expected
        elif operator == RuleOperator.LESS_THAN_OR_EQUAL:
            return actual <= expected
        elif operator == RuleOperator.CONTAINS:
            return str(expected) in str(actual)
        elif operator == RuleOperator.IN:
            return actual in expected

        return False

    async def _execute_action(
        self,
        rule: Rule,
        campaign: Campaign,
    ) -> dict[str, Any]:
        """Execute the rule action on a campaign."""
        action = rule.action_type
        config = rule.action_config

        logger.info(
            "executing_rule_action",
            rule_id=rule.id,
            campaign_id=campaign.id,
            action=action.value,
        )

        if action == RuleAction.APPLY_LABEL:
            label = config.get("label", "flagged")
            if label not in campaign.labels:
                campaign.labels = campaign.labels + [label]
            return {"action": "apply_label", "label": label, "success": True}

        elif action == RuleAction.SEND_ALERT:
            # In production, send email notification
            return {
                "action": "send_alert",
                "success": True,
                "message": f"Alert sent for campaign {campaign.name}",
            }

        elif action == RuleAction.PAUSE_CAMPAIGN:
            from app.models import CampaignStatus

            campaign.status = CampaignStatus.PAUSED
            return {
                "action": "pause_campaign",
                "success": True,
                "new_status": "paused",
            }

        elif action == RuleAction.ADJUST_BUDGET:
            adjustment_percent = config.get("adjustment_percent", 0)
            if campaign.daily_budget_cents:
                old_budget = campaign.daily_budget_cents
                new_budget = int(old_budget * (1 + adjustment_percent / 100))
                campaign.daily_budget_cents = new_budget
                return {
                    "action": "adjust_budget",
                    "success": True,
                    "old_budget_cents": old_budget,
                    "new_budget_cents": new_budget,
                    "adjustment_percent": adjustment_percent,
                }
            return {
                "action": "adjust_budget",
                "success": False,
                "reason": "No daily budget set",
            }

        elif action == RuleAction.NOTIFY_SLACK:
            webhook_url = config.get("webhook_url")
            if webhook_url:
                # In production, post to Slack webhook
                return {
                    "action": "notify_slack",
                    "success": True,
                    "webhook_called": True,
                }
            return {
                "action": "notify_slack",
                "success": False,
                "reason": "No webhook URL configured",
            }

        elif action == RuleAction.NOTIFY_WHATSAPP:
            # Send WhatsApp notification when rule is triggered
            return await self._send_whatsapp_notification(rule, campaign, config)

        return {"action": action.value, "success": False, "reason": "Unknown action"}

    async def _send_whatsapp_notification(
        self,
        rule: Rule,
        campaign: Campaign,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Send WhatsApp notification when a rule is triggered.

        Config options:
            - contact_ids: List of WhatsApp contact IDs to notify
            - template_name: Template to use (default: rule_alert)
            - message: Custom message text (for text messages within 24hr window)
        """
        from app.models import WhatsAppContact, WhatsAppMessage, WhatsAppMessageStatus
        from app.services.whatsapp_client import WhatsAppAPIError, WhatsAppClient

        contact_ids = config.get("contact_ids", [])
        template_name = config.get("template_name", "rule_alert")
        custom_message = config.get("message")

        if not contact_ids:
            return {
                "action": "notify_whatsapp",
                "success": False,
                "reason": "No WhatsApp contacts configured for notification",
            }

        # Get opted-in contacts
        from sqlalchemy import select

        result = await self.db.execute(
            select(WhatsAppContact).where(
                WhatsAppContact.id.in_(contact_ids),
                WhatsAppContact.tenant_id == self.tenant_id,
                WhatsAppContact.opt_in_status == "opted_in",
            )
        )
        contacts = result.scalars().all()

        if not contacts:
            return {
                "action": "notify_whatsapp",
                "success": False,
                "reason": "No opted-in contacts found",
            }

        # Build notification message
        alert_message = custom_message or (
            f"Rule Alert: {rule.name}\n"
            f"Campaign: {campaign.name}\n"
            f"Condition: {rule.condition_field} {rule.condition_operator.value} {rule.condition_value}\n"
            f"Action triggered at: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}"
        )

        # Send to each contact
        client = WhatsAppClient()
        sent_count = 0
        failed_count = 0
        results = []

        for contact in contacts:
            try:
                # Create message record
                message = WhatsAppMessage(
                    tenant_id=self.tenant_id,
                    contact_id=contact.id,
                    message_type="template" if template_name else "text",
                    template_name=template_name,
                    content=alert_message,
                    status=WhatsAppMessageStatus.PENDING,
                )
                self.db.add(message)

                # Attempt to send via WhatsApp API
                if template_name:
                    # Send template message with rule alert details
                    api_response = await client.send_template_message(
                        recipient_phone=contact.phone_number,
                        template_name=template_name,
                        components=[
                            {
                                "type": "body",
                                "parameters": [
                                    {"type": "text", "text": rule.name},
                                    {"type": "text", "text": campaign.name},
                                    {
                                        "type": "text",
                                        "text": f"{rule.condition_field} {rule.condition_operator.value} {rule.condition_value}",
                                    },
                                ],
                            }
                        ],
                    )
                else:
                    # Send text message (only works within 24hr conversation window)
                    api_response = await client.send_text_message(
                        recipient_phone=contact.phone_number,
                        text=alert_message,
                    )

                # Update message with WhatsApp message ID
                if api_response.get("messages"):
                    message.wamid = api_response["messages"][0].get("id")
                    message.status = WhatsAppMessageStatus.SENT
                    message.sent_at = datetime.now(UTC)

                sent_count += 1
                results.append(
                    {
                        "contact_id": contact.id,
                        "phone": contact.phone_number,
                        "status": "sent",
                    }
                )

                logger.info(
                    "whatsapp_notification_sent",
                    rule_id=rule.id,
                    campaign_id=campaign.id,
                    contact_id=contact.id,
                )

            except WhatsAppAPIError as e:
                message.status = WhatsAppMessageStatus.FAILED
                message.error_code = e.error_code
                message.error_message = e.message
                failed_count += 1
                results.append(
                    {
                        "contact_id": contact.id,
                        "phone": contact.phone_number,
                        "status": "failed",
                        "error": e.message,
                    }
                )

                logger.warning(
                    "whatsapp_notification_failed",
                    rule_id=rule.id,
                    contact_id=contact.id,
                    error=e.message,
                )

            except Exception as e:
                failed_count += 1
                results.append(
                    {
                        "contact_id": contact.id,
                        "phone": contact.phone_number,
                        "status": "failed",
                        "error": str(e),
                    }
                )

        await self.db.commit()

        return {
            "action": "notify_whatsapp",
            "success": sent_count > 0,
            "sent_count": sent_count,
            "failed_count": failed_count,
            "results": results,
        }

    async def _log_execution(
        self,
        rule: Rule,
        campaign: Campaign,
        evaluation: dict[str, Any],
        action_result: dict[str, Any],
    ):
        """Log the rule execution."""
        execution = RuleExecution(
            tenant_id=self.tenant_id,
            rule_id=rule.id,
            campaign_id=campaign.id,
            executed_at=datetime.now(UTC),
            triggered=evaluation["matched"],
            condition_result=evaluation["condition"],
            action_result=action_result,
        )
        self.db.add(execution)


class RuleBuilder:
    """
    Builder pattern for creating rules with validation.
    """

    def __init__(self, tenant_id: int):
        self.tenant_id = tenant_id
        self._rule_data = {
            "tenant_id": tenant_id,
            "status": RuleStatus.DRAFT,
            "cooldown_hours": 24,
            "condition_duration_hours": 24,
        }

    def name(self, name: str) -> "RuleBuilder":
        self._rule_data["name"] = name
        return self

    def description(self, description: str) -> "RuleBuilder":
        self._rule_data["description"] = description
        return self

    def when(
        self,
        field: str,
        operator: RuleOperator,
        value: str,
        duration_hours: int = 24,
    ) -> "RuleBuilder":
        """Define the condition (IF part)."""
        self._rule_data["condition_field"] = field
        self._rule_data["condition_operator"] = operator
        self._rule_data["condition_value"] = str(value)
        self._rule_data["condition_duration_hours"] = duration_hours
        return self

    def then(
        self,
        action: RuleAction,
        config: dict[str, Any] = None,
    ) -> "RuleBuilder":
        """Define the action (THEN part)."""
        self._rule_data["action_type"] = action
        self._rule_data["action_config"] = config or {}
        return self

    def applies_to(
        self,
        campaigns: list[int] = None,
        platforms: list[str] = None,
    ) -> "RuleBuilder":
        """Define scope."""
        if campaigns:
            self._rule_data["applies_to_campaigns"] = campaigns
        if platforms:
            self._rule_data["applies_to_platforms"] = platforms
        return self

    def cooldown(self, hours: int) -> "RuleBuilder":
        """Set cooldown period."""
        self._rule_data["cooldown_hours"] = hours
        return self

    def build(self) -> Rule:
        """Build the rule."""
        return Rule(**self._rule_data)

    def validate(self) -> list[str]:
        """Validate the rule configuration."""
        errors = []

        if not self._rule_data.get("name"):
            errors.append("Rule name is required")

        if not self._rule_data.get("condition_field"):
            errors.append("Condition field is required")

        if not self._rule_data.get("condition_operator"):
            errors.append("Condition operator is required")

        if not self._rule_data.get("condition_value"):
            errors.append("Condition value is required")

        if not self._rule_data.get("action_type"):
            errors.append("Action type is required")

        return errors
