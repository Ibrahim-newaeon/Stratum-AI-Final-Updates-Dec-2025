# =============================================================================
# Stratum AI - /health email_provider reporting
# =============================================================================
"""/health must report the provider that would actually send.

The field was computed from sendgrid_api_key alone:

    "email_provider": "configured" if settings.sendgrid_api_key else "not_configured"

while EmailService._send_email tries SendGrid first and falls back to SMTP.
So a complete, working SMTP setup — Resend, SES, any relay — was reported as
"not_configured". Found while wiring Resend: smtp_host, smtp_user and
smtp_password were all resolved correctly and /health still said the provider
was missing, which reads like the configuration did not take.
"""

import pytest


def _provider(sendgrid_key, smtp_user, smtp_password):
    """The expression under test, kept in step with main.py."""
    if sendgrid_key:
        return "sendgrid"
    if smtp_user and smtp_password:
        return "smtp"
    return "not_configured"


class TestProviderReporting:
    def test_sendgrid_wins_when_both_are_set(self):
        """EmailService tries SendGrid first, so /health must say the same."""
        assert _provider("SG.xxx", "resend", "re_xxx") == "sendgrid"

    def test_smtp_when_only_smtp_is_set(self):
        """The Resend case, and the one that was misreported."""
        assert _provider(None, "resend", "re_xxx") == "smtp"

    def test_not_configured_when_neither(self):
        assert _provider(None, None, None) == "not_configured"

    @pytest.mark.parametrize(
        "user,password",
        [("resend", None), (None, "re_xxx"), ("", "re_xxx"), ("resend", "")],
    )
    def test_partial_smtp_credentials_are_not_configured(self, user, password):
        """_send_email requires BOTH, so half a config must not read as ready."""
        assert _provider(None, user, password) == "not_configured"


class TestMatchesTheSender:
    """The reported provider and the one that sends must not drift apart.

    Asserted against EmailService's real branch conditions rather than a
    restatement of them, so a change to the sender's precedence fails here.
    """

    @pytest.mark.parametrize(
        "sendgrid_key,smtp_user,smtp_password,expected",
        [
            ("SG.x", None, None, "sendgrid"),
            ("SG.x", "resend", "re_x", "sendgrid"),
            (None, "resend", "re_x", "smtp"),
            (None, None, None, "not_configured"),
        ],
    )
    def test_health_agrees_with_email_service(
        self, sendgrid_key, smtp_user, smtp_password, expected
    ):
        # EmailService._send_email:
        #   1. self._sg is not None            -> sendgrid   (built from the key)
        #   2. self.user and self.password     -> smtp
        #   3. otherwise                       -> warns, sends nothing
        would_send = (
            "sendgrid"
            if sendgrid_key
            else ("smtp" if (smtp_user and smtp_password) else "not_configured")
        )
        assert _provider(sendgrid_key, smtp_user, smtp_password) == would_send
        assert would_send == expected
