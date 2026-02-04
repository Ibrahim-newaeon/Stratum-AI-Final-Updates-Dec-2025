"""
Slack Notification Service - Trust Gate Alerts & Reports

Sends real-time notifications to Slack channels for:
- Trust Gate decisions (PASS/HOLD/BLOCK)
- Signal health changes
- Anomaly detection alerts
- Daily/weekly summary reports
"""

import logging
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    SUCCESS = "success"


class TrustGateStatus(str, Enum):
    PASS = "pass"
    HOLD = "hold"
    BLOCK = "block"


class SlackNotificationService:
    """
    Sends structured notifications to Slack via webhooks.
    Supports rich formatting with blocks, attachments, and emojis.
    """

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url
        self.client = httpx.AsyncClient(timeout=10.0)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    def set_webhook_url(self, url: str) -> None:
        """Update the webhook URL."""
        self.webhook_url = url

    def _get_severity_emoji(self, severity: AlertSeverity) -> str:
        """Get emoji for alert severity."""
        return {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.CRITICAL: "🚨",
            AlertSeverity.SUCCESS: "✅",
        }.get(severity, "📢")

    def _get_trust_gate_color(self, status: TrustGateStatus) -> str:
        """Get color hex for trust gate status."""
        return {
            TrustGateStatus.PASS: "#22c55e",  # Green
            TrustGateStatus.HOLD: "#eab308",  # Yellow
            TrustGateStatus.BLOCK: "#ef4444",  # Red
        }.get(status, "#6b7280")

    def _get_trust_gate_emoji(self, status: TrustGateStatus) -> str:
        """Get emoji for trust gate status."""
        return {
            TrustGateStatus.PASS: "🟢",
            TrustGateStatus.HOLD: "🟡",
            TrustGateStatus.BLOCK: "🔴",
        }.get(status, "⚪")

    async def send_message(
        self,
        text: str,
        blocks: Optional[list[dict[str, Any]]] = None,
        attachments: Optional[list[dict[str, Any]]] = None,
        webhook_url: Optional[str] = None,
    ) -> bool:
        """
        Send a message to Slack.

        Args:
            text: Fallback text for notifications
            blocks: Rich layout blocks
            attachments: Legacy attachments
            webhook_url: Override default webhook URL

        Returns:
            True if sent successfully
        """
        url = webhook_url or self.webhook_url
        if not url:
            logger.warning("No Slack webhook URL configured")
            return False

        payload: dict[str, Any] = {"text": text}
        if blocks:
            payload["blocks"] = blocks
        if attachments:
            payload["attachments"] = attachments

        try:
            response = await self.client.post(url, json=payload)
            if response.status_code == 200:
                logger.info("Slack notification sent successfully")
                return True
            else:
                logger.error(f"Slack API error: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False

    async def send_trust_gate_alert(
        self,
        tenant_name: str,
        automation_name: str,
        status: TrustGateStatus,
        signal_health: float,
        threshold: float = 70.0,
        details: Optional[dict[str, Any]] = None,
        webhook_url: Optional[str] = None,
    ) -> bool:
        """
        Send a Trust Gate decision alert.

        Args:
            tenant_name: Name of the tenant
            automation_name: Name of the automation rule
            status: Trust gate decision (PASS/HOLD/BLOCK)
            signal_health: Current signal health score
            threshold: Health threshold for the gate
            details: Additional context
            webhook_url: Override webhook URL
        """
        emoji = self._get_trust_gate_emoji(status)
        color = self._get_trust_gate_color(status)
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

        # Determine action text
        action_text = {
            TrustGateStatus.PASS: "Automation executed successfully",
            TrustGateStatus.HOLD: "Automation on hold - monitoring",
            TrustGateStatus.BLOCK: "Automation blocked - manual review required",
        }.get(status, "Status unknown")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} Trust Gate: {status.value.upper()}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Tenant:*\n{tenant_name}"},
                    {"type": "mrkdwn", "text": f"*Automation:*\n{automation_name}"},
                    {"type": "mrkdwn", "text": f"*Signal Health:*\n{signal_health:.1f}/100"},
                    {"type": "mrkdwn", "text": f"*Threshold:*\n{threshold:.1f}"},
                ],
            },
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Action:* {action_text}"}},
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"🕐 {timestamp} | Stratum AI Trust Engine"}
                ],
            },
        ]

        # Add details if provided
        if details:
            detail_text = "\n".join([f"• *{k}:* {v}" for k, v in details.items()])
            blocks.insert(
                3,
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Details:*\n{detail_text}"},
                },
            )

        attachments = [{"color": color, "blocks": blocks}]

        return await self.send_message(
            text=f"Trust Gate {status.value.upper()} for {automation_name}",
            attachments=attachments,
            webhook_url=webhook_url,
        )

    async def send_signal_health_alert(
        self,
        tenant_name: str,
        signal_name: str,
        current_health: float,
        previous_health: float,
        severity: AlertSeverity = AlertSeverity.WARNING,
        webhook_url: Optional[str] = None,
    ) -> bool:
        """
        Send a signal health change alert.
        """
        emoji = self._get_severity_emoji(severity)
        change = current_health - previous_health
        direction = "📈" if change > 0 else "📉"
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

        # Determine health status text
        if current_health >= 70:
            status_text = "🟢 Healthy"
        elif current_health >= 40:
            status_text = "🟡 Degraded"
        else:
            status_text = "🔴 Unhealthy"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} Signal Health Alert",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Tenant:*\n{tenant_name}"},
                    {"type": "mrkdwn", "text": f"*Signal:*\n{signal_name}"},
                    {
                        "type": "mrkdwn",
                        "text": f"*Current Health:*\n{status_text} ({current_health:.1f})",
                    },
                    {"type": "mrkdwn", "text": f"*Change:*\n{direction} {change:+.1f}"},
                ],
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"🕐 {timestamp} | Previous: {previous_health:.1f}"}
                ],
            },
        ]

        color = (
            "#ef4444" if current_health < 40 else "#eab308" if current_health < 70 else "#22c55e"
        )

        return await self.send_message(
            text=f"Signal Health Alert: {signal_name} at {current_health:.1f}",
            attachments=[{"color": color, "blocks": blocks}],
            webhook_url=webhook_url,
        )

    async def send_anomaly_alert(
        self,
        tenant_name: str,
        metric_name: str,
        current_value: float,
        expected_value: float,
        z_score: float,
        webhook_url: Optional[str] = None,
    ) -> bool:
        """
        Send an anomaly detection alert.
        """
        severity = AlertSeverity.CRITICAL if abs(z_score) > 3 else AlertSeverity.WARNING
        emoji = self._get_severity_emoji(severity)
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

        deviation_pct = (
            ((current_value - expected_value) / expected_value * 100) if expected_value != 0 else 0
        )

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} Anomaly Detected",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Tenant:*\n{tenant_name}"},
                    {"type": "mrkdwn", "text": f"*Metric:*\n{metric_name}"},
                    {"type": "mrkdwn", "text": f"*Current Value:*\n{current_value:,.2f}"},
                    {"type": "mrkdwn", "text": f"*Expected:*\n{expected_value:,.2f}"},
                    {"type": "mrkdwn", "text": f"*Z-Score:*\n{z_score:.2f}σ"},
                    {"type": "mrkdwn", "text": f"*Deviation:*\n{deviation_pct:+.1f}%"},
                ],
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"🕐 {timestamp} | Stratum AI Anomaly Detection"}
                ],
            },
        ]

        color = "#ef4444" if abs(z_score) > 3 else "#eab308"

        return await self.send_message(
            text=f"Anomaly: {metric_name} deviation of {deviation_pct:+.1f}%",
            attachments=[{"color": color, "blocks": blocks}],
            webhook_url=webhook_url,
        )

    async def send_daily_summary(
        self,
        tenant_name: str,
        stats: dict[str, Any],
        webhook_url: Optional[str] = None,
    ) -> bool:
        """
        Send a daily summary report.

        Args:
            tenant_name: Tenant name
            stats: Dictionary with summary statistics
            webhook_url: Override webhook URL
        """
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d")

        # Extract stats with defaults
        total_automations = stats.get("total_automations", 0)
        passed = stats.get("passed", 0)
        held = stats.get("held", 0)
        blocked = stats.get("blocked", 0)
        avg_signal_health = stats.get("avg_signal_health", 0)
        anomalies_detected = stats.get("anomalies", 0)

        pass_rate = (passed / total_automations * 100) if total_automations > 0 else 0

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📊 Daily Trust Report - {tenant_name}",
                    "emoji": True,
                },
            },
            {"type": "divider"},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Summary for {timestamp}*"}},
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Total Automations:*\n{total_automations}"},
                    {"type": "mrkdwn", "text": f"*Pass Rate:*\n{pass_rate:.1f}%"},
                    {"type": "mrkdwn", "text": f"🟢 *Passed:*\n{passed}"},
                    {"type": "mrkdwn", "text": f"🟡 *Held:*\n{held}"},
                    {"type": "mrkdwn", "text": f"🔴 *Blocked:*\n{blocked}"},
                    {
                        "type": "mrkdwn",
                        "text": f"*Avg Signal Health:*\n{avg_signal_health:.1f}/100",
                    },
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Anomalies Detected:* {anomalies_detected}"},
            },
            {"type": "divider"},
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": "📈 Stratum AI - Trust-Gated Revenue Operations"}
                ],
            },
        ]

        # Determine overall status color
        color = "#22c55e" if pass_rate > 90 else "#eab308" if pass_rate > 70 else "#ef4444"

        return await self.send_message(
            text=f"Daily Summary: {pass_rate:.1f}% pass rate",
            attachments=[{"color": color, "blocks": blocks}],
            webhook_url=webhook_url,
        )

    async def test_connection(self, webhook_url: Optional[str] = None) -> bool:
        """
        Test the Slack webhook connection.
        """
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "✅ *Stratum AI Connected!*\n\nYour Slack integration is working. You'll receive Trust Gate alerts and reports in this channel.",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"🔗 Connection verified at {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
                    }
                ],
            },
        ]

        return await self.send_message(
            text="Stratum AI Slack Integration Test",
            blocks=blocks,
            webhook_url=webhook_url,
        )


# Singleton instance
slack_service = SlackNotificationService()
