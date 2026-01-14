# =============================================================================
# Stratum AI - Pacing Alert Service
# =============================================================================
"""
Alert service for pacing and performance monitoring.

Features:
- Automatic alert generation based on pacing thresholds
- Multi-channel notifications (Slack, Email, WhatsApp)
- Alert lifecycle management (create, acknowledge, resolve)
- Historical alert tracking
"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.pacing import (
    DailyKPI,
    PacingAlert,
    Target,
    TargetMetric,
    AlertSeverity,
    AlertType,
    AlertStatus,
)
from app.services.pacing.pacing_service import PacingService

logger = get_logger(__name__)


class PacingAlertService:
    """
    Service for generating and managing pacing alerts.

    Monitors targets and generates alerts when:
    - Pacing is below/above thresholds
    - ROAS falls below target
    - Conversions/revenue below expected
    - Sudden performance drops (pacing cliff)
    """

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.pacing_service = PacingService(db, tenant_id)

    async def check_target_alerts(
        self,
        target_id: UUID,
        as_of_date: Optional[date] = None,
    ) -> List[PacingAlert]:
        """
        Check a target for alert conditions and create alerts if needed.

        Args:
            target_id: Target UUID to check
            as_of_date: Date to check (default: today)

        Returns:
            List of created alerts
        """
        if as_of_date is None:
            as_of_date = date.today()

        # Get current pacing
        pacing = await self.pacing_service.get_target_pacing(target_id, as_of_date)

        if pacing.get("status") != "success":
            return []

        created_alerts = []

        # Check for underpacing
        pacing_pct = pacing["pacing"]["pct"]
        target_value = pacing["target_value"]
        thresholds = pacing["thresholds"]
        status_flags = pacing["status_flags"]

        # Determine alert severity based on deviation
        if pacing_pct < 100 - thresholds["critical_pct"]:
            # Critical underpacing
            alert = await self._create_alert_if_new(
                target_id=target_id,
                alert_type=AlertType.UNDERPACING_SPEND,
                severity=AlertSeverity.CRITICAL,
                title=f"Critical: {pacing['target_name']} severely underpacing",
                message=f"Currently at {pacing_pct:.1f}% of expected pace. "
                        f"MTD: ${pacing['mtd']['actual']:,.2f} vs expected ${pacing['mtd']['expected']:,.2f}",
                pacing=pacing,
                as_of_date=as_of_date,
            )
            if alert:
                created_alerts.append(alert)

        elif pacing_pct < 100 - thresholds["warning_pct"]:
            # Warning underpacing
            alert = await self._create_alert_if_new(
                target_id=target_id,
                alert_type=AlertType.UNDERPACING_SPEND,
                severity=AlertSeverity.WARNING,
                title=f"Warning: {pacing['target_name']} underpacing",
                message=f"Currently at {pacing_pct:.1f}% of expected pace. "
                        f"MTD: ${pacing['mtd']['actual']:,.2f} vs expected ${pacing['mtd']['expected']:,.2f}",
                pacing=pacing,
                as_of_date=as_of_date,
            )
            if alert:
                created_alerts.append(alert)

        elif pacing_pct > 100 + thresholds["critical_pct"]:
            # Critical overpacing
            alert = await self._create_alert_if_new(
                target_id=target_id,
                alert_type=AlertType.OVERPACING_SPEND,
                severity=AlertSeverity.CRITICAL,
                title=f"Critical: {pacing['target_name']} severely overpacing",
                message=f"Currently at {pacing_pct:.1f}% of expected pace. "
                        f"Risk of budget exhaustion before period end.",
                pacing=pacing,
                as_of_date=as_of_date,
            )
            if alert:
                created_alerts.append(alert)

        elif pacing_pct > 100 + thresholds["warning_pct"]:
            # Warning overpacing
            alert = await self._create_alert_if_new(
                target_id=target_id,
                alert_type=AlertType.OVERPACING_SPEND,
                severity=AlertSeverity.WARNING,
                title=f"Warning: {pacing['target_name']} overpacing",
                message=f"Currently at {pacing_pct:.1f}% of expected pace. "
                        f"May exceed budget before period end.",
                pacing=pacing,
                as_of_date=as_of_date,
            )
            if alert:
                created_alerts.append(alert)

        # Check if projected to miss target
        if status_flags["will_miss"]:
            gap_pct = pacing["gap_analysis"]["gap_pct"]
            if abs(gap_pct) > thresholds["critical_pct"]:
                alert_type = self._get_miss_alert_type(pacing["metric_type"])
                alert = await self._create_alert_if_new(
                    target_id=target_id,
                    alert_type=alert_type,
                    severity=AlertSeverity.CRITICAL,
                    title=f"Critical: {pacing['target_name']} projected to miss target",
                    message=f"Projected EOM: ${pacing['projection']['eom']:,.2f} vs target ${target_value:,.2f}. "
                            f"Gap: {gap_pct:.1f}%",
                    pacing=pacing,
                    as_of_date=as_of_date,
                )
                if alert:
                    created_alerts.append(alert)

        # Auto-resolve alerts that are no longer valid
        await self._resolve_outdated_alerts(target_id, pacing, as_of_date)

        return created_alerts

    async def check_all_targets(
        self,
        as_of_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Check all active targets for alert conditions.

        Args:
            as_of_date: Date to check

        Returns:
            Summary of alert check results
        """
        if as_of_date is None:
            as_of_date = date.today()

        # Get all active targets
        result = await self.db.execute(
            select(Target).where(
                and_(
                    Target.tenant_id == self.tenant_id,
                    Target.is_active == True,
                    Target.period_start <= as_of_date,
                    Target.period_end >= as_of_date,
                )
            )
        )
        targets = result.scalars().all()

        total_alerts = 0
        targets_with_alerts = 0

        for target in targets:
            alerts = await self.check_target_alerts(target.id, as_of_date)
            if alerts:
                total_alerts += len(alerts)
                targets_with_alerts += 1

        return {
            "status": "success",
            "as_of_date": as_of_date.isoformat(),
            "targets_checked": len(targets),
            "targets_with_alerts": targets_with_alerts,
            "alerts_created": total_alerts,
        }

    async def check_pacing_cliff(
        self,
        target_id: UUID,
        as_of_date: Optional[date] = None,
        lookback_days: int = 7,
        drop_threshold_pct: float = 30.0,
    ) -> Optional[PacingAlert]:
        """
        Check for sudden performance drops (pacing cliff).

        Args:
            target_id: Target UUID
            as_of_date: Date to check
            lookback_days: Days to look back for comparison
            drop_threshold_pct: Percentage drop to trigger alert

        Returns:
            Created alert if cliff detected, None otherwise
        """
        if as_of_date is None:
            as_of_date = date.today()

        # Get target
        result = await self.db.execute(
            select(Target).where(
                and_(
                    Target.id == target_id,
                    Target.tenant_id == self.tenant_id,
                )
            )
        )
        target = result.scalar_one_or_none()

        if not target:
            return None

        # Get recent daily values
        conditions = [
            DailyKPI.tenant_id == self.tenant_id,
            DailyKPI.date >= as_of_date - timedelta(days=lookback_days),
            DailyKPI.date <= as_of_date,
        ]

        if target.platform:
            conditions.append(DailyKPI.platform == target.platform)
        else:
            conditions.append(DailyKPI.platform.is_(None))

        if target.campaign_id:
            conditions.append(DailyKPI.campaign_id == target.campaign_id)
        else:
            conditions.append(DailyKPI.campaign_id.is_(None))

        result = await self.db.execute(
            select(DailyKPI)
            .where(and_(*conditions))
            .order_by(DailyKPI.date)
        )
        records = result.scalars().all()

        if len(records) < 3:
            return None  # Not enough data

        # Calculate average of previous days vs latest day
        metric_values = []
        for r in records:
            value = self._get_metric_value(r, target.metric_type)
            if value is not None:
                metric_values.append((r.date, value))

        if len(metric_values) < 3:
            return None

        # Compare latest day to average of previous days
        latest_value = metric_values[-1][1]
        previous_avg = sum(v[1] for v in metric_values[:-1]) / len(metric_values[:-1])

        if previous_avg > 0:
            drop_pct = ((previous_avg - latest_value) / previous_avg) * 100

            if drop_pct >= drop_threshold_pct:
                return await self._create_alert_if_new(
                    target_id=target_id,
                    alert_type=AlertType.PACING_CLIFF,
                    severity=AlertSeverity.CRITICAL,
                    title=f"Pacing Cliff Detected: {target.name}",
                    message=f"Performance dropped {drop_pct:.1f}% from {lookback_days}-day average. "
                            f"Today: ${latest_value:,.2f} vs avg ${previous_avg:,.2f}",
                    pacing={"drop_pct": drop_pct, "latest_value": latest_value, "previous_avg": previous_avg},
                    as_of_date=as_of_date,
                )

        return None

    async def get_active_alerts(
        self,
        target_id: Optional[UUID] = None,
        severity: Optional[AlertSeverity] = None,
        alert_type: Optional[AlertType] = None,
    ) -> List[PacingAlert]:
        """
        Get active alerts with optional filters.

        Args:
            target_id: Optional target filter
            severity: Optional severity filter
            alert_type: Optional alert type filter

        Returns:
            List of active alerts
        """
        conditions = [
            PacingAlert.tenant_id == self.tenant_id,
            PacingAlert.status == AlertStatus.ACTIVE,
        ]

        if target_id:
            conditions.append(PacingAlert.target_id == target_id)

        if severity:
            conditions.append(PacingAlert.severity == severity)

        if alert_type:
            conditions.append(PacingAlert.alert_type == alert_type)

        result = await self.db.execute(
            select(PacingAlert)
            .where(and_(*conditions))
            .order_by(PacingAlert.created_at.desc())
        )
        return list(result.scalars().all())

    async def acknowledge_alert(
        self,
        alert_id: UUID,
        user_id: Optional[int] = None,
    ) -> Optional[PacingAlert]:
        """Acknowledge an alert."""
        result = await self.db.execute(
            select(PacingAlert).where(
                and_(
                    PacingAlert.id == alert_id,
                    PacingAlert.tenant_id == self.tenant_id,
                )
            )
        )
        alert = result.scalar_one_or_none()

        if not alert:
            return None

        alert.status = AlertStatus.ACKNOWLEDGED
        alert.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(alert)

        logger.info(f"Alert {alert_id} acknowledged by user {user_id}")
        return alert

    async def resolve_alert(
        self,
        alert_id: UUID,
        user_id: Optional[int] = None,
        resolution_notes: Optional[str] = None,
    ) -> Optional[PacingAlert]:
        """Resolve an alert."""
        result = await self.db.execute(
            select(PacingAlert).where(
                and_(
                    PacingAlert.id == alert_id,
                    PacingAlert.tenant_id == self.tenant_id,
                )
            )
        )
        alert = result.scalar_one_or_none()

        if not alert:
            return None

        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.utcnow()
        alert.resolved_by_user_id = user_id
        alert.resolution_notes = resolution_notes
        alert.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(alert)

        logger.info(f"Alert {alert_id} resolved by user {user_id}")
        return alert

    async def dismiss_alert(
        self,
        alert_id: UUID,
        user_id: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> Optional[PacingAlert]:
        """Dismiss an alert (false positive or not actionable)."""
        result = await self.db.execute(
            select(PacingAlert).where(
                and_(
                    PacingAlert.id == alert_id,
                    PacingAlert.tenant_id == self.tenant_id,
                )
            )
        )
        alert = result.scalar_one_or_none()

        if not alert:
            return None

        alert.status = AlertStatus.DISMISSED
        alert.resolved_at = datetime.utcnow()
        alert.resolved_by_user_id = user_id
        alert.resolution_notes = f"Dismissed: {reason}" if reason else "Dismissed"
        alert.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(alert)

        logger.info(f"Alert {alert_id} dismissed by user {user_id}")
        return alert

    async def get_alert_summary(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Get summary of alerts for a time period.

        Args:
            start_date: Start of period
            end_date: End of period

        Returns:
            Alert summary statistics
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        # Get all alerts in period
        result = await self.db.execute(
            select(PacingAlert).where(
                and_(
                    PacingAlert.tenant_id == self.tenant_id,
                    PacingAlert.created_at >= datetime.combine(start_date, datetime.min.time()),
                    PacingAlert.created_at <= datetime.combine(end_date, datetime.max.time()),
                )
            )
        )
        alerts = result.scalars().all()

        # Count by status
        by_status = {status.value: 0 for status in AlertStatus}
        for alert in alerts:
            by_status[alert.status.value] += 1

        # Count by severity
        by_severity = {severity.value: 0 for severity in AlertSeverity}
        for alert in alerts:
            by_severity[alert.severity.value] += 1

        # Count by type
        by_type = {alert_type.value: 0 for alert_type in AlertType}
        for alert in alerts:
            by_type[alert.alert_type.value] += 1

        # Calculate resolution time (for resolved alerts)
        resolution_times = []
        for alert in alerts:
            if alert.resolved_at and alert.created_at:
                delta = alert.resolved_at - alert.created_at
                resolution_times.append(delta.total_seconds() / 3600)  # Hours

        avg_resolution_hours = (
            sum(resolution_times) / len(resolution_times) if resolution_times else None
        )

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "total_alerts": len(alerts),
            "by_status": by_status,
            "by_severity": by_severity,
            "by_type": by_type,
            "resolution": {
                "avg_hours": round(avg_resolution_hours, 1) if avg_resolution_hours else None,
                "total_resolved": len(resolution_times),
            },
        }

    async def _create_alert_if_new(
        self,
        target_id: UUID,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        message: str,
        pacing: Dict[str, Any],
        as_of_date: date,
    ) -> Optional[PacingAlert]:
        """Create alert if no active alert of same type exists for target."""
        # Check for existing active alert
        result = await self.db.execute(
            select(PacingAlert).where(
                and_(
                    PacingAlert.target_id == target_id,
                    PacingAlert.alert_type == alert_type,
                    PacingAlert.status.in_([AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]),
                    PacingAlert.pacing_date >= as_of_date - timedelta(days=1),  # Within last day
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update severity if escalated
            if severity == AlertSeverity.CRITICAL and existing.severity != AlertSeverity.CRITICAL:
                existing.severity = AlertSeverity.CRITICAL
                existing.title = title
                existing.message = message
                existing.updated_at = datetime.utcnow()
                await self.db.commit()
                logger.info(f"Escalated alert {existing.id} to CRITICAL")
            return None

        # Create new alert
        alert = PacingAlert(
            tenant_id=self.tenant_id,
            target_id=target_id,
            alert_type=alert_type,
            severity=severity,
            status=AlertStatus.ACTIVE,
            title=title,
            message=message,
            pacing_date=as_of_date,
            current_value=pacing.get("mtd", {}).get("actual"),
            target_value=pacing.get("target_value"),
            projected_value=pacing.get("projection", {}).get("eom"),
            deviation_pct=100 - pacing.get("pacing", {}).get("pct", 100),
            days_remaining=pacing.get("period", {}).get("days_remaining"),
            mtd_actual=pacing.get("mtd", {}).get("actual"),
            mtd_expected=pacing.get("mtd", {}).get("expected"),
            projected_eom=pacing.get("projection", {}).get("eom"),
            platform=pacing.get("scope", {}).get("platform"),
            campaign_id=pacing.get("scope", {}).get("campaign_id"),
            details=pacing,
        )

        self.db.add(alert)
        await self.db.commit()
        await self.db.refresh(alert)

        logger.info(f"Created {severity.value} alert: {title}")

        # TODO: Send notifications (Slack, Email, WhatsApp)
        # await self._send_notifications(alert)

        return alert

    async def _resolve_outdated_alerts(
        self,
        target_id: UUID,
        pacing: Dict[str, Any],
        as_of_date: date,
    ) -> None:
        """Auto-resolve alerts that are no longer valid."""
        status_flags = pacing.get("status_flags", {})

        # If now on track, resolve underpacing/overpacing alerts
        if status_flags.get("on_track"):
            result = await self.db.execute(
                select(PacingAlert).where(
                    and_(
                        PacingAlert.target_id == target_id,
                        PacingAlert.alert_type.in_([
                            AlertType.UNDERPACING_SPEND,
                            AlertType.OVERPACING_SPEND,
                        ]),
                        PacingAlert.status.in_([AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]),
                    )
                )
            )
            alerts_to_resolve = result.scalars().all()

            for alert in alerts_to_resolve:
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.utcnow()
                alert.resolution_notes = "Auto-resolved: Pacing returned to normal"
                alert.updated_at = datetime.utcnow()

            if alerts_to_resolve:
                await self.db.commit()
                logger.info(f"Auto-resolved {len(alerts_to_resolve)} alerts for target {target_id}")

    def _get_miss_alert_type(self, metric_type: str) -> AlertType:
        """Get appropriate alert type based on metric."""
        metric_to_alert = {
            "roas": AlertType.ROAS_BELOW_TARGET,
            "conversions": AlertType.CONVERSIONS_BELOW_TARGET,
            "revenue": AlertType.REVENUE_BELOW_TARGET,
            "pipeline_value": AlertType.PIPELINE_BELOW_TARGET,
        }
        return metric_to_alert.get(metric_type, AlertType.UNDERPACING_SPEND)

    def _get_metric_value(self, record: DailyKPI, metric: TargetMetric) -> Optional[float]:
        """Extract metric value from DailyKPI record."""
        if metric == TargetMetric.SPEND:
            return (record.spend_cents or 0) / 100
        elif metric == TargetMetric.REVENUE:
            return (record.revenue_cents or 0) / 100
        elif metric == TargetMetric.ROAS:
            return record.roas
        elif metric == TargetMetric.CONVERSIONS:
            return record.conversions
        elif metric == TargetMetric.LEADS:
            return record.leads + record.crm_leads
        elif metric == TargetMetric.PIPELINE_VALUE:
            return (record.crm_pipeline_cents or 0) / 100
        elif metric == TargetMetric.WON_REVENUE:
            return (record.crm_won_revenue_cents or 0) / 100
        return None


# =============================================================================
# Notification Service (Placeholder for future implementation)
# =============================================================================

class AlertNotificationService:
    """
    Service for sending alert notifications.

    Supports:
    - Slack webhooks
    - Email via SMTP/SendGrid
    - WhatsApp via Twilio
    """

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    async def send_slack_notification(
        self,
        alert: PacingAlert,
        webhook_url: str,
    ) -> bool:
        """Send alert notification to Slack."""
        # TODO: Implement Slack notification
        logger.info(f"Would send Slack notification for alert {alert.id}")
        return True

    async def send_email_notification(
        self,
        alert: PacingAlert,
        recipients: List[str],
    ) -> bool:
        """Send alert notification via email."""
        # TODO: Implement email notification
        logger.info(f"Would send email notification for alert {alert.id} to {recipients}")
        return True

    async def send_whatsapp_notification(
        self,
        alert: PacingAlert,
        phone_numbers: List[str],
    ) -> bool:
        """Send alert notification via WhatsApp."""
        # TODO: Implement WhatsApp notification
        logger.info(f"Would send WhatsApp notification for alert {alert.id} to {phone_numbers}")
        return True

    async def notify_alert(self, alert: PacingAlert) -> Dict[str, bool]:
        """
        Send notifications for an alert based on target settings.

        Returns dict of {channel: success} for each notification sent.
        """
        # Get target to check notification settings
        result = await self.db.execute(
            select(Target).where(Target.id == alert.target_id)
        )
        target = result.scalar_one_or_none()

        if not target:
            return {}

        results = {}

        if target.notify_slack:
            # TODO: Get Slack webhook from tenant settings
            results["slack"] = await self.send_slack_notification(alert, "")

        if target.notify_email:
            recipients = target.notification_recipients or []
            if recipients:
                results["email"] = await self.send_email_notification(alert, recipients)

        if target.notify_whatsapp:
            # TODO: Get phone numbers from notification_recipients
            results["whatsapp"] = await self.send_whatsapp_notification(alert, [])

        # Track what was sent
        alert.notifications_sent = results
        alert.updated_at = datetime.utcnow()
        await self.db.commit()

        return results
