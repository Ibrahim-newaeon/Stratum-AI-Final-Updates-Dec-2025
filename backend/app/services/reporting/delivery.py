# =============================================================================
# Stratum AI - Report Delivery Service
# =============================================================================
"""
Multi-channel delivery service for generated reports.

Supported channels:
- Email (SMTP)
- Slack (Webhook/API)
- Microsoft Teams (Webhook)
- Webhook (Generic HTTP)
- S3 (AWS Storage)
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Protocol
from uuid import UUID
import logging
import os
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import aiosmtplib
import aiohttp
from abc import ABC, abstractmethod

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reporting import (
    ReportExecution,
    ReportDelivery,
    DeliveryChannelConfig,
    DeliveryChannel,
    DeliveryStatus,
    ExecutionStatus,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Delivery Channel Interface
# =============================================================================

class DeliveryChannelHandler(ABC):
    """Abstract base class for delivery channel implementations."""

    @abstractmethod
    async def deliver(
        self,
        execution: ReportExecution,
        config: Dict[str, Any],
        recipient: str,
    ) -> Dict[str, Any]:
        """
        Deliver a report through this channel.

        Returns dict with:
        - success: bool
        - message_id: Optional[str]
        - response: Any
        - error: Optional[str]
        """
        pass


# =============================================================================
# Email Delivery
# =============================================================================

class EmailDelivery(DeliveryChannelHandler):
    """SMTP-based email delivery."""

    async def deliver(
        self,
        execution: ReportExecution,
        config: Dict[str, Any],
        recipient: str,
    ) -> Dict[str, Any]:
        """Send report via email with attachment."""
        try:
            # Build email
            msg = MIMEMultipart()
            msg["From"] = f"{config.get('from_name', 'Stratum Reports')} <{config['from_email']}>"
            msg["To"] = recipient
            msg["Subject"] = self._render_subject(execution, config)

            # Email body
            body = self._render_body(execution, config)
            msg.attach(MIMEText(body, "html"))

            # Attach report file
            if execution.file_path and os.path.exists(execution.file_path):
                await self._attach_file(msg, execution)

            # Send email
            async with aiosmtplib.SMTP(
                hostname=config["smtp_host"],
                port=config.get("smtp_port", 587),
                use_tls=config.get("use_tls", True),
            ) as smtp:
                if config.get("smtp_user") and config.get("smtp_password"):
                    await smtp.login(config["smtp_user"], config["smtp_password"])

                result = await smtp.send_message(msg)

            return {
                "success": True,
                "message_id": msg.get("Message-ID"),
                "response": str(result),
            }

        except Exception as e:
            logger.error(f"Email delivery failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }

    def _render_subject(self, execution: ReportExecution, config: Dict[str, Any]) -> str:
        """Render email subject from template."""
        template = config.get("subject_template", "{{report_type}} Report - {{date_range}}")

        # Simple template replacement
        subject = template.replace("{{report_type}}", execution.report_type.value.replace("_", " ").title())
        subject = subject.replace("{{date_range}}", f"{execution.date_range_start} to {execution.date_range_end}")

        return subject

    def _render_body(self, execution: ReportExecution, config: Dict[str, Any]) -> str:
        """Render email body from template."""
        template = config.get("body_template", "")

        if not template:
            template = """
            <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2>{{report_type}} Report</h2>
                <p>Please find your scheduled report attached.</p>
                <table style="border-collapse: collapse; margin: 20px 0;">
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Report Type:</strong></td>
                        <td style="padding: 8px; border: 1px solid #ddd;">{{report_type}}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Date Range:</strong></td>
                        <td style="padding: 8px; border: 1px solid #ddd;">{{date_range}}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Generated:</strong></td>
                        <td style="padding: 8px; border: 1px solid #ddd;">{{generated_at}}</td>
                    </tr>
                </table>
                <p style="color: #666; font-size: 12px;">
                    This is an automated report from Stratum AI. Do not reply to this email.
                </p>
            </body>
            </html>
            """

        body = template.replace("{{report_type}}", execution.report_type.value.replace("_", " ").title())
        body = body.replace("{{date_range}}", f"{execution.date_range_start} to {execution.date_range_end}")
        body = body.replace("{{generated_at}}", execution.completed_at.strftime("%Y-%m-%d %H:%M UTC") if execution.completed_at else "N/A")

        return body

    async def _attach_file(self, msg: MIMEMultipart, execution: ReportExecution):
        """Attach report file to email."""
        filename = os.path.basename(execution.file_path)
        content_type = self._get_content_type(execution.format.value)

        with open(execution.file_path, "rb") as f:
            part = MIMEBase(*content_type.split("/"))
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{filename}"',
            )
            msg.attach(part)

    def _get_content_type(self, format: str) -> str:
        """Get MIME type for report format."""
        types = {
            "pdf": "application/pdf",
            "csv": "text/csv",
            "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "json": "application/json",
            "html": "text/html",
        }
        return types.get(format, "application/octet-stream")


# =============================================================================
# Slack Delivery
# =============================================================================

class SlackDelivery(DeliveryChannelHandler):
    """Slack webhook-based delivery."""

    async def deliver(
        self,
        execution: ReportExecution,
        config: Dict[str, Any],
        recipient: str,  # Channel name or webhook URL
    ) -> Dict[str, Any]:
        """Send report notification to Slack."""
        try:
            # Build Slack message
            message = self._build_message(execution, config)

            # Determine webhook URL
            webhook_url = config.get("webhook_url") or recipient

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=message,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    response_text = await response.text()

                    if response.status == 200:
                        return {
                            "success": True,
                            "response": response_text,
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Slack API error: {response.status} - {response_text}",
                        }

        except Exception as e:
            logger.error(f"Slack delivery failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }

    def _build_message(self, execution: ReportExecution, config: Dict[str, Any]) -> Dict[str, Any]:
        """Build Slack Block Kit message."""
        report_type = execution.report_type.value.replace("_", " ").title()
        date_range = f"{execution.date_range_start} to {execution.date_range_end}"

        # Summary from metrics if available
        summary_text = ""
        if execution.metrics_summary:
            metrics = execution.metrics_summary
            if "total_spend" in metrics:
                summary_text += f"• Spend: ${metrics['total_spend']:,.2f}\n"
            if "total_revenue" in metrics:
                summary_text += f"• Revenue: ${metrics['total_revenue']:,.2f}\n"
            if "overall_roas" in metrics:
                summary_text += f"• ROAS: {metrics['overall_roas']:.2f}x\n"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f":chart_with_upwards_trend: {report_type} Report",
                    "emoji": True,
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Date Range:*\n{date_range}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Generated:*\n{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
                    },
                ],
            },
        ]

        if summary_text:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Key Metrics:*\n{summary_text}",
                },
            })

        # Add download link if available
        if execution.file_url:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"<{execution.file_url}|:arrow_down: Download Report>",
                },
            })

        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Sent by Stratum AI Automated Reporting",
                }
            ],
        })

        return {"blocks": blocks}


# =============================================================================
# Microsoft Teams Delivery
# =============================================================================

class TeamsDelivery(DeliveryChannelHandler):
    """Microsoft Teams webhook-based delivery."""

    async def deliver(
        self,
        execution: ReportExecution,
        config: Dict[str, Any],
        recipient: str,  # Webhook URL
    ) -> Dict[str, Any]:
        """Send report notification to Microsoft Teams."""
        try:
            # Build Teams Adaptive Card
            card = self._build_card(execution, config)

            webhook_url = config.get("webhook_url") or recipient

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=card,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    response_text = await response.text()

                    if response.status in (200, 202):
                        return {
                            "success": True,
                            "response": response_text,
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Teams API error: {response.status} - {response_text}",
                        }

        except Exception as e:
            logger.error(f"Teams delivery failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }

    def _build_card(self, execution: ReportExecution, config: Dict[str, Any]) -> Dict[str, Any]:
        """Build Microsoft Teams Adaptive Card."""
        report_type = execution.report_type.value.replace("_", " ").title()
        date_range = f"{execution.date_range_start} to {execution.date_range_end}"

        facts = [
            {"title": "Report Type", "value": report_type},
            {"title": "Date Range", "value": date_range},
            {"title": "Generated", "value": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")},
        ]

        # Add metrics if available
        if execution.metrics_summary:
            metrics = execution.metrics_summary
            if "total_spend" in metrics:
                facts.append({"title": "Total Spend", "value": f"${metrics['total_spend']:,.2f}"})
            if "total_revenue" in metrics:
                facts.append({"title": "Total Revenue", "value": f"${metrics['total_revenue']:,.2f}"})
            if "overall_roas" in metrics:
                facts.append({"title": "ROAS", "value": f"{metrics['overall_roas']:.2f}x"})

        card = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "0076D7",
            "summary": f"{report_type} Report Generated",
            "sections": [
                {
                    "activityTitle": f"📊 {report_type} Report",
                    "activitySubtitle": "Stratum AI Automated Reporting",
                    "facts": facts,
                    "markdown": True,
                }
            ],
        }

        # Add download button if URL available
        if execution.file_url:
            card["potentialAction"] = [
                {
                    "@type": "OpenUri",
                    "name": "Download Report",
                    "targets": [
                        {"os": "default", "uri": execution.file_url}
                    ],
                }
            ]

        return card


# =============================================================================
# Webhook Delivery (Generic)
# =============================================================================

class WebhookDelivery(DeliveryChannelHandler):
    """Generic HTTP webhook delivery."""

    async def deliver(
        self,
        execution: ReportExecution,
        config: Dict[str, Any],
        recipient: str,  # Webhook URL
    ) -> Dict[str, Any]:
        """Send report data to a webhook endpoint."""
        try:
            payload = self._build_payload(execution, config)
            webhook_url = config.get("webhook_url") or recipient

            headers = {"Content-Type": "application/json"}

            # Add custom headers if configured
            if config.get("headers"):
                headers.update(config["headers"])

            # Add authentication if configured
            if config.get("auth_header"):
                headers["Authorization"] = config["auth_header"]

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    response_text = await response.text()

                    if response.status < 400:
                        return {
                            "success": True,
                            "response": response_text,
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Webhook error: {response.status} - {response_text}",
                        }

        except Exception as e:
            logger.error(f"Webhook delivery failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }

    def _build_payload(self, execution: ReportExecution, config: Dict[str, Any]) -> Dict[str, Any]:
        """Build webhook payload."""
        return {
            "event": "report.generated",
            "report": {
                "execution_id": str(execution.id),
                "type": execution.report_type.value,
                "format": execution.format.value,
                "date_range": {
                    "start": str(execution.date_range_start),
                    "end": str(execution.date_range_end),
                },
                "generated_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "file_url": execution.file_url,
                "metrics_summary": execution.metrics_summary,
            },
            "tenant_id": execution.tenant_id,
        }


# =============================================================================
# S3 Delivery
# =============================================================================

class S3Delivery(DeliveryChannelHandler):
    """AWS S3 storage delivery."""

    async def deliver(
        self,
        execution: ReportExecution,
        config: Dict[str, Any],
        recipient: str,  # S3 path prefix
    ) -> Dict[str, Any]:
        """Upload report to S3."""
        try:
            import aioboto3

            bucket = config["bucket"]
            prefix = config.get("prefix", recipient or "reports/")

            # Build S3 key
            timestamp = datetime.now(timezone.utc).strftime("%Y/%m/%d")
            filename = os.path.basename(execution.file_path)
            s3_key = f"{prefix.rstrip('/')}/{timestamp}/{filename}"

            session = aioboto3.Session(
                aws_access_key_id=config.get("aws_access_key"),
                aws_secret_access_key=config.get("aws_secret_key"),
                region_name=config.get("region", "us-east-1"),
            )

            async with session.client("s3") as s3:
                with open(execution.file_path, "rb") as f:
                    await s3.put_object(
                        Bucket=bucket,
                        Key=s3_key,
                        Body=f.read(),
                        ContentType=self._get_content_type(execution.format.value),
                    )

                # Generate presigned URL
                presigned_url = await s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": bucket, "Key": s3_key},
                    ExpiresIn=86400 * 7,  # 7 days
                )

            return {
                "success": True,
                "s3_key": s3_key,
                "presigned_url": presigned_url,
            }

        except ImportError:
            return {
                "success": False,
                "error": "aioboto3 package not installed for S3 delivery",
            }
        except Exception as e:
            logger.error(f"S3 delivery failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }

    def _get_content_type(self, format: str) -> str:
        """Get MIME type for report format."""
        types = {
            "pdf": "application/pdf",
            "csv": "text/csv",
            "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "json": "application/json",
            "html": "text/html",
        }
        return types.get(format, "application/octet-stream")


# =============================================================================
# Delivery Service (Orchestrator)
# =============================================================================

class DeliveryService:
    """
    Orchestrates report delivery across multiple channels.
    """

    CHANNEL_HANDLERS = {
        DeliveryChannel.EMAIL: EmailDelivery,
        DeliveryChannel.SLACK: SlackDelivery,
        DeliveryChannel.TEAMS: TeamsDelivery,
        DeliveryChannel.WEBHOOK: WebhookDelivery,
        DeliveryChannel.S3: S3Delivery,
    }

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    async def deliver_report(
        self,
        execution_id: UUID,
        channels: List[str],
        delivery_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Deliver a report to multiple channels.

        Args:
            execution_id: The report execution to deliver
            channels: List of channel names (email, slack, teams, webhook, s3)
            delivery_config: Channel-specific configuration

        Returns:
            Dict with delivery results per channel
        """
        execution = await self.db.get(ReportExecution, execution_id)
        if not execution or execution.tenant_id != self.tenant_id:
            raise ValueError(f"Execution not found: {execution_id}")

        if execution.status != ExecutionStatus.COMPLETED:
            raise ValueError(f"Cannot deliver report with status: {execution.status}")

        results = {
            "execution_id": str(execution_id),
            "channels": {},
            "total_recipients": 0,
            "successful": 0,
            "failed": 0,
        }

        for channel_name in channels:
            try:
                channel = DeliveryChannel(channel_name)
            except ValueError:
                logger.warning(f"Unknown delivery channel: {channel_name}")
                continue

            channel_config = delivery_config.get(channel_name, {})
            handler_class = self.CHANNEL_HANDLERS.get(channel)

            if not handler_class:
                logger.warning(f"No handler for channel: {channel_name}")
                continue

            handler = handler_class()

            # Get recipients for this channel
            recipients = self._get_recipients(channel, channel_config)

            channel_results = []

            for recipient in recipients:
                # Create delivery record
                delivery = ReportDelivery(
                    tenant_id=self.tenant_id,
                    execution_id=execution_id,
                    channel=channel,
                    recipient=recipient,
                    status=DeliveryStatus.PENDING,
                )
                self.db.add(delivery)
                await self.db.flush()

                # Attempt delivery
                result = await handler.deliver(execution, channel_config, recipient)

                results["total_recipients"] += 1

                if result.get("success"):
                    delivery.status = DeliveryStatus.SENT
                    delivery.sent_at = datetime.now(timezone.utc)
                    delivery.message_id = result.get("message_id")
                    delivery.delivery_response = result
                    results["successful"] += 1
                else:
                    delivery.status = DeliveryStatus.FAILED
                    delivery.error_message = result.get("error")
                    delivery.delivery_response = result
                    results["failed"] += 1

                channel_results.append({
                    "recipient": recipient,
                    "success": result.get("success"),
                    "error": result.get("error"),
                })

            results["channels"][channel_name] = channel_results

        await self.db.commit()

        return results

    def _get_recipients(
        self,
        channel: DeliveryChannel,
        config: Dict[str, Any],
    ) -> List[str]:
        """Extract recipients from channel config."""
        if channel == DeliveryChannel.EMAIL:
            recipients = config.get("recipients", [])
            cc = config.get("cc", [])
            return recipients + cc

        elif channel == DeliveryChannel.SLACK:
            # Could be channel name or webhook URL
            if config.get("channel"):
                return [config["channel"]]
            elif config.get("webhook_url"):
                return [config["webhook_url"]]
            return []

        elif channel == DeliveryChannel.TEAMS:
            if config.get("webhook_url"):
                return [config["webhook_url"]]
            return []

        elif channel == DeliveryChannel.WEBHOOK:
            if config.get("webhook_url"):
                return [config["webhook_url"]]
            return []

        elif channel == DeliveryChannel.S3:
            return [config.get("prefix", "reports/")]

        return []

    async def retry_delivery(
        self,
        delivery_id: UUID,
    ) -> Dict[str, Any]:
        """Retry a failed delivery."""
        delivery = await self.db.get(ReportDelivery, delivery_id)
        if not delivery or delivery.tenant_id != self.tenant_id:
            raise ValueError(f"Delivery not found: {delivery_id}")

        if delivery.status != DeliveryStatus.FAILED:
            raise ValueError(f"Can only retry failed deliveries")

        execution = await self.db.get(ReportExecution, delivery.execution_id)

        # Get channel config from schedule or use empty dict
        channel_config = {}
        if execution.schedule_id:
            from app.models.reporting import ScheduledReport
            schedule = await self.db.get(ScheduledReport, execution.schedule_id)
            if schedule:
                channel_config = schedule.delivery_config.get(delivery.channel.value, {})

        handler_class = self.CHANNEL_HANDLERS.get(delivery.channel)
        if not handler_class:
            raise ValueError(f"No handler for channel: {delivery.channel}")

        handler = handler_class()
        result = await handler.deliver(execution, channel_config, delivery.recipient)

        delivery.retry_count += 1
        delivery.last_retry_at = datetime.now(timezone.utc)

        if result.get("success"):
            delivery.status = DeliveryStatus.SENT
            delivery.sent_at = datetime.now(timezone.utc)
            delivery.message_id = result.get("message_id")
            delivery.error_message = None
        else:
            delivery.error_message = result.get("error")

        delivery.delivery_response = result
        await self.db.commit()

        return result

    async def get_delivery_status(
        self,
        execution_id: UUID,
    ) -> List[Dict[str, Any]]:
        """Get delivery status for an execution."""
        query = (
            select(ReportDelivery)
            .where(
                and_(
                    ReportDelivery.tenant_id == self.tenant_id,
                    ReportDelivery.execution_id == execution_id,
                )
            )
            .order_by(ReportDelivery.queued_at)
        )

        result = await self.db.execute(query)
        deliveries = result.scalars().all()

        return [
            {
                "id": str(d.id),
                "channel": d.channel.value,
                "recipient": d.recipient,
                "status": d.status.value,
                "sent_at": d.sent_at.isoformat() if d.sent_at else None,
                "error": d.error_message,
                "retry_count": d.retry_count,
            }
            for d in deliveries
        ]
