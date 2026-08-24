# =============================================================================
# Stratum AI - Newsletter Unsubscribe Tokens
# =============================================================================
"""The unsubscribe link in a newsletter must only unsubscribe its own recipient.

The previous token was ``base64("<campaign_id>:<subscriber_id>")``. The helper
that made it was called ``_generate_unsubscribe_token`` and its docstring said
"signed"; nothing was signed. Both values are small sequential integers, and the
endpoint has no authentication — by necessity, since the caller is a person
clicking a link in an email — so any recipient could decrement the subscriber id
and unsubscribe a stranger, or walk the range and unsubscribe the whole list.

Two properties are load-bearing here:

1. A token that was not minted by this application is rejected.
2. A token that *was* minted for one subscriber cannot be edited into a token
   for another.

The legacy format is still accepted behind a flag, because links in mail that
has already been delivered cannot be reissued. That is a deliberate, reversible
trade — a broken unsubscribe link is worse than the forgery risk it closes — so
the tests pin both the acceptance and the switch that ends it.
"""

import base64

import pytest

from app.core.config import settings
from app.core.unsubscribe_tokens import (
    make_unsubscribe_token,
    parse_unsubscribe_token,
)


def legacy_token(campaign_id: int, subscriber_id: int) -> str:
    """The exact pre-fix format, reproduced so the compatibility path is tested."""
    return base64.urlsafe_b64encode(f"{campaign_id}:{subscriber_id}".encode()).decode()


class TestRoundTrip:
    def test_signed_token_round_trips(self):
        assert parse_unsubscribe_token(make_unsubscribe_token(7, 42)) == (7, 42)

    def test_token_is_url_safe(self):
        token = make_unsubscribe_token(123456, 987654)
        assert "+" not in token and "/" not in token and "=" not in token

    def test_ids_are_not_hidden_by_signing(self):
        # The payload is still just the two ids: signing adds authenticity, not
        # confidentiality, and nothing new is exposed in the URL either way.
        token = make_unsubscribe_token(7, 42)
        payload = token.partition(".")[0]
        decoded = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
        assert decoded == b"7:42"


class TestForgeryIsRejected:
    def test_cannot_walk_to_another_subscriber(self):
        """The whole point. Holding your own link must not unsubscribe anyone else."""
        mine = make_unsubscribe_token(7, 42)
        _, _, signature = mine.partition(".")
        theirs_payload = base64.urlsafe_b64encode(b"7:43").decode().rstrip("=")

        assert parse_unsubscribe_token(f"{theirs_payload}.{signature}") is None

    def test_rejects_a_tampered_signature(self):
        token = make_unsubscribe_token(7, 42)
        payload, _, signature = token.partition(".")
        assert parse_unsubscribe_token(f"{payload}.{signature[:-2]}xy") is None

    def test_rejects_an_empty_signature(self):
        payload = base64.urlsafe_b64encode(b"7:42").decode().rstrip("=")
        assert parse_unsubscribe_token(f"{payload}.") is None

    def test_signature_depends_on_both_ids(self):
        assert make_unsubscribe_token(7, 42) != make_unsubscribe_token(8, 42)
        assert make_unsubscribe_token(7, 42) != make_unsubscribe_token(7, 43)

    @pytest.mark.parametrize(
        "bad",
        ["", "garbage", ".", "a.b", "!!!.???", "....", "7:42"],
    )
    def test_rejects_malformed_tokens(self, bad):
        assert parse_unsubscribe_token(bad) is None

    def test_non_numeric_payload_is_rejected(self):
        payload = base64.urlsafe_b64encode(b"seven:forty-two").decode().rstrip("=")
        from app.core.unsubscribe_tokens import _signature

        token = f"{payload}.{_signature('seven:forty-two')}"
        assert parse_unsubscribe_token(token) is None


class TestLegacyCompatibility:
    """Links already sitting in inboxes have to keep working."""

    def test_legacy_token_is_accepted_by_default(self, monkeypatch):
        monkeypatch.setattr(
            settings, "newsletter_accept_legacy_unsubscribe_tokens", True
        )
        assert parse_unsubscribe_token(legacy_token(7, 42)) == (7, 42)

    def test_legacy_token_is_rejected_once_the_flag_is_off(self, monkeypatch):
        # The one-line change that closes the residual forgery window, once the
        # logs show no legacy tokens arriving.
        monkeypatch.setattr(
            settings, "newsletter_accept_legacy_unsubscribe_tokens", False
        )
        assert parse_unsubscribe_token(legacy_token(7, 42)) is None

    def test_signed_tokens_still_work_with_the_flag_off(self, monkeypatch):
        monkeypatch.setattr(
            settings, "newsletter_accept_legacy_unsubscribe_tokens", False
        )
        assert parse_unsubscribe_token(make_unsubscribe_token(7, 42)) == (7, 42)

    def test_legacy_acceptance_is_logged(self, monkeypatch, capsys):
        """The signal that says when the flag above can be turned off.

        Read through capsys rather than caplog: structlog renders straight to
        stdout here, so caplog sees nothing.
        """
        monkeypatch.setattr(
            settings, "newsletter_accept_legacy_unsubscribe_tokens", True
        )
        parse_unsubscribe_token(legacy_token(7, 42))
        assert "newsletter_legacy_unsubscribe_token_used" in capsys.readouterr().out

    def test_signed_tokens_are_not_logged_as_legacy(self, monkeypatch, capsys):
        monkeypatch.setattr(
            settings, "newsletter_accept_legacy_unsubscribe_tokens", True
        )
        parse_unsubscribe_token(make_unsubscribe_token(7, 42))
        assert "newsletter_legacy_unsubscribe_token_used" not in capsys.readouterr().out

    def test_a_malformed_legacy_token_is_still_rejected(self, monkeypatch):
        monkeypatch.setattr(
            settings, "newsletter_accept_legacy_unsubscribe_tokens", True
        )
        assert (
            parse_unsubscribe_token(base64.urlsafe_b64encode(b"nope").decode()) is None
        )


class TestSendPathUsesSignedTokens:
    def test_the_worker_and_the_endpoint_share_one_implementation(self):
        """They each used to carry their own copy, and neither signed anything."""
        import inspect

        from app.api.v1.endpoints import newsletter
        from app.workers import newsletter_tasks

        assert "parse_unsubscribe_token" in inspect.getsource(
            newsletter._decode_unsubscribe_token
        )
        assert "make_unsubscribe_token" in inspect.getsource(
            newsletter_tasks.send_newsletter_campaign
        )

    def test_the_endpoint_accepts_the_worker_s_token(self):
        from app.api.v1.endpoints.newsletter import _decode_unsubscribe_token

        assert _decode_unsubscribe_token(make_unsubscribe_token(3, 9)) == (3, 9)

    def test_the_endpoint_rejects_a_forged_token(self):
        from fastapi import HTTPException

        from app.api.v1.endpoints.newsletter import _decode_unsubscribe_token

        forged = base64.urlsafe_b64encode(b"3:10").decode().rstrip("=") + ".xxxx"
        with pytest.raises(HTTPException) as exc:
            _decode_unsubscribe_token(forged)
        assert exc.value.status_code == 400


class TestOneClickUnsubscribeAcceptsPost:
    def test_route_allows_get_and_post(self):
        """``send_newsletter_email`` sets List-Unsubscribe-Post, which tells
        Gmail and Yahoo to POST here. The route was GET-only, so every one-click
        unsubscribe from a major provider got a 405."""
        from app.api.v1.endpoints import newsletter

        route = next(
            r
            for r in newsletter.router.routes
            if getattr(r, "path", "") == "/newsletter/unsubscribe"
        )
        assert {"GET", "POST"} <= set(route.methods)

    def test_no_wildcard_route_shadows_unsubscribe(self):
        """`/newsletter/unsubscribe` must not be swallowed by a `/{id}` route
        registered before it — routes match in declaration order."""
        from app.api.v1.endpoints import newsletter

        paths = [getattr(r, "path", "") for r in newsletter.router.routes]
        index = paths.index("/newsletter/unsubscribe")
        earlier_wildcards = [
            p
            for p in paths[:index]
            if p.count("/") == 2 and "{" in p.rsplit("/", 1)[-1]
        ]
        assert earlier_wildcards == []

    def test_the_send_path_still_advertises_one_click(self):
        import inspect

        from app.services.email_service import EmailService

        source = inspect.getsource(EmailService.send_newsletter_email)
        assert "List-Unsubscribe-Post" in source
