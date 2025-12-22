"""
Stratum AI - Email Service
Handles sending transactional emails including password reset, notifications, and alerts.
Supports both SendGrid Web API and SMTP fallback.
"""

import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmailService:
    """
    Async email service for sending transactional emails.
    Supports SendGrid Web API (preferred) and SMTP fallback.
    """

    def __init__(self):
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
        self.smtp_tls = settings.smtp_tls
        self.from_email = settings.from_email
        self.from_name = settings.from_name
        self._use_sendgrid_api = (
            self.smtp_host == "smtp.sendgrid.net" and self.smtp_password
        )

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> bool:
        """
        Send an email asynchronously.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML body content
            text_content: Plain text fallback (optional)
            cc: CC recipients (optional)
            bcc: BCC recipients (optional)

        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self.smtp_password:
            logger.warning("Email not configured, skipping send", to=to_email, subject=subject)
            return False

        # Use SendGrid Web API if configured (more reliable than SMTP)
        if self._use_sendgrid_api:
            return await self._send_via_sendgrid_api(
                to_email, subject, html_content, text_content, cc, bcc
            )

        # Fallback to SMTP
        return await self._send_via_smtp(
            to_email, subject, html_content, text_content, cc, bcc
        )

    async def _send_via_sendgrid_api(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> bool:
        """Send email using SendGrid Web API."""
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Cc, Bcc

            message = Mail(
                from_email=(self.from_email, self.from_name),
                to_emails=to_email,
                subject=subject,
                html_content=html_content,
            )

            if text_content:
                message.plain_text_content = text_content

            if cc:
                for cc_email in cc:
                    message.add_cc(Cc(cc_email))

            if bcc:
                for bcc_email in bcc:
                    message.add_bcc(Bcc(bcc_email))

            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            sg = SendGridAPIClient(self.smtp_password)
            response = await loop.run_in_executor(None, sg.send, message)

            if response.status_code in (200, 201, 202):
                logger.info("email_sent_sendgrid", to=to_email, subject=subject, status=response.status_code)
                return True
            else:
                logger.error("email_send_failed_sendgrid", to=to_email, status=response.status_code)
                return False

        except Exception as e:
            logger.error("email_send_failed_sendgrid", to=to_email, subject=subject, error=str(e))
            return False

    async def _send_via_smtp(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> bool:
        """Send email using SMTP."""
        try:
            import aiosmtplib

            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email

            if cc:
                message["Cc"] = ", ".join(cc)

            if text_content:
                part1 = MIMEText(text_content, "plain")
                message.attach(part1)

            part2 = MIMEText(html_content, "html")
            message.attach(part2)

            recipients = [to_email]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)

            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                start_tls=self.smtp_tls,
            )

            logger.info("email_sent_smtp", to=to_email, subject=subject)
            return True

        except Exception as e:
            logger.error("email_send_failed_smtp", to=to_email, subject=subject, error=str(e))
            return False

    async def send_password_reset_email(
        self,
        to_email: str,
        reset_token: str,
        user_name: Optional[str] = None,
    ) -> bool:
        """
        Send a password reset email.

        Args:
            to_email: User's email address
            reset_token: Password reset token
            user_name: User's display name (optional)

        Returns:
            True if email was sent successfully
        """
        reset_url = f"{settings.frontend_url}/reset-password?token={reset_token}"

        subject = "Reset Your Stratum AI Password"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reset Your Password</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); padding: 30px; border-radius: 12px 12px 0 0; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 28px;">Stratum AI</h1>
    </div>

    <div style="background: #ffffff; padding: 40px 30px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 12px 12px;">
        <h2 style="color: #1f2937; margin-top: 0;">Reset Your Password</h2>

        <p style="color: #4b5563;">Hi{' ' + user_name if user_name else ''},</p>

        <p style="color: #4b5563;">
            We received a request to reset your password for your Stratum AI account.
            Click the button below to create a new password:
        </p>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}"
               style="display: inline-block; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-weight: 600; font-size: 16px;">
                Reset Password
            </a>
        </div>

        <p style="color: #6b7280; font-size: 14px;">
            This link will expire in 1 hour for security reasons.
        </p>

        <p style="color: #6b7280; font-size: 14px;">
            If you didn't request a password reset, you can safely ignore this email.
            Your password will remain unchanged.
        </p>

        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">

        <p style="color: #9ca3af; font-size: 12px; margin-bottom: 0;">
            If the button doesn't work, copy and paste this link into your browser:
            <br>
            <a href="{reset_url}" style="color: #6366f1; word-break: break-all;">{reset_url}</a>
        </p>
    </div>

    <div style="text-align: center; padding: 20px; color: #9ca3af; font-size: 12px;">
        <p style="margin: 0;">
            &copy; 2024 Stratum AI. All rights reserved.
            <br>
            Unified Ad Intelligence Platform
        </p>
    </div>
</body>
</html>
"""

        text_content = f"""
Reset Your Stratum AI Password

Hi{' ' + user_name if user_name else ''},

We received a request to reset your password for your Stratum AI account.

Click the link below to create a new password:
{reset_url}

This link will expire in 1 hour for security reasons.

If you didn't request a password reset, you can safely ignore this email.
Your password will remain unchanged.

---
Stratum AI - Unified Ad Intelligence Platform
"""

        return await self.send_email(to_email, subject, html_content, text_content)

    async def send_welcome_email(
        self,
        to_email: str,
        user_name: Optional[str] = None,
    ) -> bool:
        """
        Send a welcome email to new users.

        Args:
            to_email: User's email address
            user_name: User's display name (optional)

        Returns:
            True if email was sent successfully
        """
        subject = "Welcome to Stratum AI!"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); padding: 30px; border-radius: 12px 12px 0 0; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 28px;">Welcome to Stratum AI</h1>
    </div>

    <div style="background: #ffffff; padding: 40px 30px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 12px 12px;">
        <h2 style="color: #1f2937; margin-top: 0;">You're all set!</h2>

        <p style="color: #4b5563;">Hi{' ' + user_name if user_name else ''},</p>

        <p style="color: #4b5563;">
            Welcome to Stratum AI, your unified ad intelligence platform.
            You now have access to powerful features including:
        </p>

        <ul style="color: #4b5563; padding-left: 20px;">
            <li>Cross-platform campaign analytics (Meta, Google, TikTok, Snapchat, LinkedIn)</li>
            <li>AI-powered ROAS optimization</li>
            <li>Automated rules and alerts</li>
            <li>Competitor intelligence</li>
            <li>What-If simulator</li>
        </ul>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{settings.frontend_url}/overview"
               style="display: inline-block; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-weight: 600; font-size: 16px;">
                Go to Dashboard
            </a>
        </div>

        <p style="color: #6b7280; font-size: 14px;">
            Need help getting started? Check out our documentation or contact support.
        </p>
    </div>

    <div style="text-align: center; padding: 20px; color: #9ca3af; font-size: 12px;">
        <p style="margin: 0;">
            &copy; 2024 Stratum AI. All rights reserved.
        </p>
    </div>
</body>
</html>
"""

        text_content = f"""
Welcome to Stratum AI!

Hi{' ' + user_name if user_name else ''},

Welcome to Stratum AI, your unified ad intelligence platform.

You now have access to powerful features including:
- Cross-platform campaign analytics (Meta, Google, TikTok, Snapchat, LinkedIn)
- AI-powered ROAS optimization
- Automated rules and alerts
- Competitor intelligence
- What-If simulator

Get started at: {settings.frontend_url}/overview

---
Stratum AI - Unified Ad Intelligence Platform
"""

        return await self.send_email(to_email, subject, html_content, text_content)

    async def send_alert_email(
        self,
        to_email: str,
        alert_title: str,
        alert_message: str,
        severity: str = "info",
        campaign_name: Optional[str] = None,
    ) -> bool:
        """
        Send an alert notification email.

        Args:
            to_email: User's email address
            alert_title: Alert title
            alert_message: Alert details
            severity: Alert severity (info, warning, critical)
            campaign_name: Related campaign name (optional)

        Returns:
            True if email was sent successfully
        """
        severity_colors = {
            "info": "#3b82f6",
            "warning": "#f59e0b",
            "critical": "#ef4444",
        }
        color = severity_colors.get(severity, "#3b82f6")

        subject = f"[{severity.upper()}] {alert_title} - Stratum AI"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: {color}; padding: 20px; border-radius: 12px 12px 0 0;">
        <h1 style="color: white; margin: 0; font-size: 20px;">{severity.upper()} Alert</h1>
    </div>

    <div style="background: #ffffff; padding: 30px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 12px 12px;">
        <h2 style="color: #1f2937; margin-top: 0;">{alert_title}</h2>

        {f'<p style="color: #6b7280; font-size: 14px; margin-bottom: 20px;"><strong>Campaign:</strong> {campaign_name}</p>' if campaign_name else ''}

        <p style="color: #4b5563;">{alert_message}</p>

        <div style="text-align: center; margin-top: 30px;">
            <a href="{settings.frontend_url}/overview"
               style="display: inline-block; background: {color}; color: white; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: 600;">
                View in Dashboard
            </a>
        </div>
    </div>
</body>
</html>
"""

        text_content = f"""
[{severity.upper()}] {alert_title}

{f'Campaign: {campaign_name}' if campaign_name else ''}

{alert_message}

View in Dashboard: {settings.frontend_url}/overview
"""

        return await self.send_email(to_email, subject, html_content, text_content)


# Singleton instance
email_service = EmailService()


# Convenience functions
async def send_password_reset_email(
    to_email: str, reset_token: str, user_name: Optional[str] = None
) -> bool:
    """Send password reset email."""
    return await email_service.send_password_reset_email(to_email, reset_token, user_name)


async def send_welcome_email(to_email: str, user_name: Optional[str] = None) -> bool:
    """Send welcome email."""
    return await email_service.send_welcome_email(to_email, user_name)


async def send_alert_email(
    to_email: str,
    alert_title: str,
    alert_message: str,
    severity: str = "info",
    campaign_name: Optional[str] = None,
) -> bool:
    """Send alert email."""
    return await email_service.send_alert_email(
        to_email, alert_title, alert_message, severity, campaign_name
    )
