# =============================================================================
# Stratum AI - Email Service
# =============================================================================
"""
Email service for sending transactional emails.
Handles verification emails, password reset, and notifications.
"""

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmailService:
    """Service for sending transactional emails."""

    def __init__(self) -> None:
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.user = settings.smtp_user
        self.password = settings.smtp_password
        self.use_tls = settings.smtp_tls
        self.use_ssl = settings.smtp_ssl
        self.from_name = settings.email_from_name
        self.from_address = settings.email_from_address
        self.frontend_url = settings.frontend_url

    def _create_message(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> MIMEMultipart:
        """Create a MIME message with HTML and optional text content."""
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{self.from_name} <{self.from_address}>"
        message["To"] = to_email

        # Add plain text version (fallback)
        if text_content:
            message.attach(MIMEText(text_content, "plain"))

        # Add HTML version
        message.attach(MIMEText(html_content, "html"))

        return message

    def _send_email(self, to_email: str, message: MIMEMultipart) -> bool:
        """Send an email using SMTP."""
        if not self.user or not self.password:
            logger.warning(
                "SMTP credentials not configured, email not sent",
                to_email=to_email[:20] + "...",
            )
            if settings.is_development:
                logger.info(
                    "Development mode: Email would be sent",
                    subject=message["Subject"],
                    to=to_email,
                )
                return True
            return False

        try:
            if self.use_ssl:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.host, self.port, context=context) as server:
                    server.login(self.user, self.password)
                    server.sendmail(self.from_address, to_email, message.as_string())
            else:
                with smtplib.SMTP(self.host, self.port) as server:
                    if self.use_tls:
                        context = ssl.create_default_context()
                        server.starttls(context=context)
                    server.login(self.user, self.password)
                    server.sendmail(self.from_address, to_email, message.as_string())

            logger.info("Email sent successfully", to_email=to_email[:20] + "...")
            return True

        except smtplib.SMTPException as e:
            logger.error("SMTP error sending email", error=str(e))
            return False
        except Exception as e:
            logger.error("Unexpected error sending email", error=str(e))
            return False

    def send_verification_email(self, to_email: str, token: str, user_name: str) -> bool:
        """Send email verification link to new user."""
        verification_url = f"{self.frontend_url}/verify-email?token={token}"

        subject = "Verify your Stratum AI account"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #2563eb; margin: 0;">Stratum AI</h1>
    </div>

    <div style="background: #f8fafc; border-radius: 8px; padding: 30px; margin-bottom: 20px;">
        <h2 style="margin-top: 0;">Hi {user_name or 'there'},</h2>

        <p>Welcome to Stratum AI! Please verify your email address to activate your account and start automating your ad campaigns.</p>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{verification_url}"
               style="background: #2563eb; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: 600; display: inline-block;">
                Verify Email Address
            </a>
        </div>

        <p style="color: #64748b; font-size: 14px;">
            This link expires in {settings.email_verification_expire_hours} hours.
        </p>

        <p style="color: #64748b; font-size: 14px;">
            If you didn't create an account with Stratum AI, you can safely ignore this email.
        </p>
    </div>

    <div style="text-align: center; color: #94a3b8; font-size: 12px;">
        <p>
            If the button doesn't work, copy and paste this link into your browser:<br>
            <a href="{verification_url}" style="color: #2563eb; word-break: break-all;">{verification_url}</a>
        </p>
        <p style="margin-top: 20px;">
            &copy; 2024 Stratum AI. All rights reserved.
        </p>
    </div>
</body>
</html>
"""

        text_content = f"""
Hi {user_name or 'there'},

Welcome to Stratum AI! Please verify your email address to activate your account.

Click here to verify: {verification_url}

This link expires in {settings.email_verification_expire_hours} hours.

If you didn't create an account with Stratum AI, you can safely ignore this email.

- The Stratum AI Team
"""

        message = self._create_message(to_email, subject, html_content, text_content)
        return self._send_email(to_email, message)

    def send_password_reset_email(self, to_email: str, token: str, user_name: str) -> bool:
        """Send password reset link to user."""
        reset_url = f"{self.frontend_url}/reset-password?token={token}"

        subject = "Reset your Stratum AI password"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #2563eb; margin: 0;">Stratum AI</h1>
    </div>

    <div style="background: #f8fafc; border-radius: 8px; padding: 30px; margin-bottom: 20px;">
        <h2 style="margin-top: 0;">Password Reset Request</h2>

        <p>Hi {user_name or 'there'},</p>

        <p>We received a request to reset your password. Click the button below to create a new password:</p>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}"
               style="background: #2563eb; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: 600; display: inline-block;">
                Reset Password
            </a>
        </div>

        <p style="color: #64748b; font-size: 14px;">
            This link expires in {settings.password_reset_expire_hours} hour(s).
        </p>

        <p style="color: #dc2626; font-size: 14px;">
            If you didn't request a password reset, please ignore this email or contact support if you're concerned about your account security.
        </p>
    </div>

    <div style="text-align: center; color: #94a3b8; font-size: 12px;">
        <p>
            If the button doesn't work, copy and paste this link into your browser:<br>
            <a href="{reset_url}" style="color: #2563eb; word-break: break-all;">{reset_url}</a>
        </p>
        <p style="margin-top: 20px;">
            &copy; 2024 Stratum AI. All rights reserved.
        </p>
    </div>
</body>
</html>
"""

        text_content = f"""
Password Reset Request

Hi {user_name or 'there'},

We received a request to reset your password. Click the link below to create a new password:

{reset_url}

This link expires in {settings.password_reset_expire_hours} hour(s).

If you didn't request a password reset, please ignore this email.

- The Stratum AI Team
"""

        message = self._create_message(to_email, subject, html_content, text_content)
        return self._send_email(to_email, message)

    def send_welcome_email(self, to_email: str, user_name: str) -> bool:
        """Send welcome email after verification."""
        dashboard_url = f"{self.frontend_url}/dashboard"

        subject = "Welcome to Stratum AI - Let's get started!"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #2563eb; margin: 0;">Stratum AI</h1>
    </div>

    <div style="background: #f8fafc; border-radius: 8px; padding: 30px; margin-bottom: 20px;">
        <h2 style="margin-top: 0; color: #16a34a;">Your account is verified!</h2>

        <p>Hi {user_name or 'there'},</p>

        <p>Your email has been verified and your Stratum AI account is now active. Here's what you can do next:</p>

        <ul style="padding-left: 20px;">
            <li><strong>Connect your ad accounts</strong> - Link Meta, Google, TikTok, or Snapchat</li>
            <li><strong>Set up automation rules</strong> - Let AI optimize your campaigns</li>
            <li><strong>Monitor signal health</strong> - Track your data quality in real-time</li>
        </ul>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{dashboard_url}"
               style="background: #16a34a; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: 600; display: inline-block;">
                Go to Dashboard
            </a>
        </div>

        <p style="color: #64748b; font-size: 14px;">
            Need help getting started? Check out our <a href="{self.frontend_url}/docs" style="color: #2563eb;">documentation</a> or reply to this email.
        </p>
    </div>

    <div style="text-align: center; color: #94a3b8; font-size: 12px;">
        <p style="margin-top: 20px;">
            &copy; 2024 Stratum AI. All rights reserved.
        </p>
    </div>
</body>
</html>
"""

        text_content = f"""
Your account is verified!

Hi {user_name or 'there'},

Your email has been verified and your Stratum AI account is now active.

Here's what you can do next:
- Connect your ad accounts (Meta, Google, TikTok, Snapchat)
- Set up automation rules
- Monitor signal health

Go to Dashboard: {dashboard_url}

Need help? Check out our documentation at {self.frontend_url}/docs

- The Stratum AI Team
"""

        message = self._create_message(to_email, subject, html_content, text_content)
        return self._send_email(to_email, message)

    def send_payment_failed_email(
        self,
        to_email: str,
        user_name: str,
        attempt_count: int = 1,
        amount_due: Optional[str] = None,
    ) -> bool:
        """Send payment failure notification email."""
        billing_url = f"{self.frontend_url}/dashboard/settings/billing"

        # Adjust messaging based on attempt count
        if attempt_count == 1:
            urgency = "We were unable to process your payment"
            action_text = "Please update your payment method to ensure uninterrupted service."
        elif attempt_count == 2:
            urgency = "Second payment attempt failed"
            action_text = "Your subscription may be suspended soon. Please update your payment method immediately."
        else:
            urgency = "Final payment notice"
            action_text = "Your subscription will be suspended if payment is not received. Please update your payment method now."

        subject = f"Action Required: Payment failed for your Stratum AI subscription"

        amount_section = ""
        if amount_due:
            amount_section = f'<p style="font-size: 18px; font-weight: 600;">Amount Due: {amount_due}</p>'

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #2563eb; margin: 0;">Stratum AI</h1>
    </div>

    <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 30px; margin-bottom: 20px;">
        <h2 style="margin-top: 0; color: #dc2626;">{urgency}</h2>

        <p>Hi {user_name or 'there'},</p>

        <p>{action_text}</p>

        {amount_section}

        <div style="text-align: center; margin: 30px 0;">
            <a href="{billing_url}"
               style="background: #dc2626; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: 600; display: inline-block;">
                Update Payment Method
            </a>
        </div>

        <p style="color: #64748b; font-size: 14px;">
            If you believe this is an error or need assistance, please contact our support team.
        </p>
    </div>

    <div style="background: #f8fafc; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
        <h3 style="margin-top: 0; font-size: 14px; color: #64748b;">Common reasons for payment failure:</h3>
        <ul style="color: #64748b; font-size: 14px; padding-left: 20px; margin-bottom: 0;">
            <li>Expired credit card</li>
            <li>Insufficient funds</li>
            <li>Card declined by bank</li>
            <li>Incorrect billing information</li>
        </ul>
    </div>

    <div style="text-align: center; color: #94a3b8; font-size: 12px;">
        <p style="margin-top: 20px;">
            &copy; 2024 Stratum AI. All rights reserved.
        </p>
    </div>
</body>
</html>
"""

        text_content = f"""
{urgency}

Hi {user_name or 'there'},

{action_text}

{"Amount Due: " + amount_due if amount_due else ""}

Update your payment method here: {billing_url}

Common reasons for payment failure:
- Expired credit card
- Insufficient funds
- Card declined by bank
- Incorrect billing information

If you believe this is an error, please contact support.

- The Stratum AI Team
"""

        message = self._create_message(to_email, subject, html_content, text_content)
        return self._send_email(to_email, message)

    def send_user_invite_email(
        self,
        to_email: str,
        inviter_name: str,
        tenant_name: str,
        invite_token: str,
        role: str = "member",
    ) -> bool:
        """Send invitation email to new team member."""
        invite_url = f"{self.frontend_url}/accept-invite?token={invite_token}"

        subject = f"You've been invited to join {tenant_name} on Stratum AI"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #2563eb; margin: 0;">Stratum AI</h1>
    </div>

    <div style="background: #f8fafc; border-radius: 8px; padding: 30px; margin-bottom: 20px;">
        <h2 style="margin-top: 0;">You're invited!</h2>

        <p><strong>{inviter_name}</strong> has invited you to join <strong>{tenant_name}</strong> on Stratum AI as a <strong>{role}</strong>.</p>

        <p>Stratum AI is a Revenue Operating System that helps teams automate and optimize their ad campaigns with trust-gated automation.</p>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{invite_url}"
               style="background: #2563eb; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: 600; display: inline-block;">
                Accept Invitation
            </a>
        </div>

        <p style="color: #64748b; font-size: 14px;">
            This invitation expires in 7 days. If you didn't expect this invitation, you can safely ignore this email.
        </p>
    </div>

    <div style="text-align: center; color: #94a3b8; font-size: 12px;">
        <p>
            If the button doesn't work, copy and paste this link into your browser:<br>
            <a href="{invite_url}" style="color: #2563eb; word-break: break-all;">{invite_url}</a>
        </p>
        <p style="margin-top: 20px;">
            &copy; 2024 Stratum AI. All rights reserved.
        </p>
    </div>
</body>
</html>
"""

        text_content = f"""
You're invited!

{inviter_name} has invited you to join {tenant_name} on Stratum AI as a {role}.

Stratum AI is a Revenue Operating System that helps teams automate and optimize their ad campaigns.

Accept your invitation: {invite_url}

This invitation expires in 7 days.

If you didn't expect this invitation, you can safely ignore this email.

- The Stratum AI Team
"""

        message = self._create_message(to_email, subject, html_content, text_content)
        return self._send_email(to_email, message)


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create email service instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
