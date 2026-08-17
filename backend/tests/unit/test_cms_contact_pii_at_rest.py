# =============================================================================
# Stratum AI - Contact Form PII
# =============================================================================
"""The public contact form stores identifiable data encrypted, and records the
visitor's IP rather than the proxy's.

Two separate defects in `POST /cms/contact`:

1. Every field the visitor typed — name, email, company, phone, subject,
   message — was stored as plaintext `VARCHAR`/`TEXT`. The logging half of this
   was fixed earlier (the handler masks via `mask_email`), which left the at-rest
   half looking done.

2. `ip_address` came from `request.client.host`. Production sits behind
   Cloudflare and an nginx edge container, so that is the *proxy's* address —
   every submission recorded the same useless IP. Three middlewares
   (`audit.py`, `rate_limit.py`, `embed_widgets/security.py`) already each carry
   a private `_get_client_ip` that resolves this correctly; the contact form
   reimplemented it as the weakest possible version. This adds one shared
   resolver and points the contact form at it. The three middlewares are
   deliberately left alone — rate limiting and audit have both bitten us before
   and deserve their own change.

`cms_contact_submissions` is tenant-less: it is Stratum's own marketing form, not
tenant data, so there is no `tenant_id` to derive a per-tenant key from. That
makes the global-key `EncryptedString` the only structurally available option
here, contrary to its own docstring's warning against using it for PII — the
warning exists because tenant-aware call sites should use `encrypt_pii(v,
tenant_id)`, and this table has no tenant to pass.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.client_ip import get_client_ip
from app.db.types import EncryptedString, EncryptedText
from app.models.cms import CMSContactSubmission

pytestmark = pytest.mark.asyncio

# column -> the max input length the ContactSubmit schema accepts for it.
# encrypt_pii output is ~2.2x the plaintext here (255 -> 560 measured, not the
# ~1.4x a bare Fernet token costs), so the column has to be considerably wider
# than the schema's limit or the longest legitimate submission fails on insert.
# This mapping is what makes that checkable instead of assumed.
_PII_COLUMNS = {
    "name": 255,
    "email": 255,
    "company": 255,
    "phone": 50,
    "subject": 255,
    "message": 5000,
    "ip_address": 45,
}

# Technical metadata, deliberately readable: no personal identifier, and useful
# for triage exactly because you can read it straight out of the table.
_PLAINTEXT_COLUMNS = ("source_page", "user_agent")


def _column_type(name: str):
    return CMSContactSubmission.__table__.c[name].type


class TestPiiColumnsEncryptAtRest:
    @pytest.mark.parametrize("column", sorted(_PII_COLUMNS))
    async def test_column_encrypts_and_round_trips(self, column):
        column_type = _column_type(column)
        assert isinstance(
            column_type, (EncryptedString, EncryptedText)
        ), f"{column} is stored in the clear"

        plaintext = "alice@example.com"
        stored = column_type.process_bind_param(plaintext, None)

        assert stored != plaintext, "value reached the column unencrypted"
        assert column_type.process_result_value(stored, None) == plaintext

    @pytest.mark.parametrize("column,max_input", sorted(_PII_COLUMNS.items()))
    async def test_column_is_wide_enough_for_the_ciphertext(self, column, max_input):
        """A column that fits the plaintext but not its ciphertext turns the
        longest legitimate submission into a 500."""
        column_type = _column_type(column)
        declared = getattr(column_type.impl, "length", None)

        stored = column_type.process_bind_param("x" * max_input, None)

        if declared is None:
            return  # TEXT / unbounded VARCHAR
        assert (
            len(stored) <= declared
        ), f"{column}: ciphertext is {len(stored)} chars, column holds {declared}"


class TestTechnicalColumnsStayReadable:
    @pytest.mark.parametrize("column", _PLAINTEXT_COLUMNS)
    async def test_column_is_not_encrypted(self, column):
        column_type = _column_type(column)
        assert not isinstance(column_type, (EncryptedString, EncryptedText))


def _request(client_host, headers=None):
    request = MagicMock()
    request.client = MagicMock(host=client_host) if client_host else None
    request.headers = headers or {}
    return request


class TestClientIpResolution:
    async def test_direct_client_is_used_when_it_is_not_a_proxy(self):
        """A public client cannot lie about its own address via a header."""
        request = _request("203.0.113.9", {"X-Forwarded-For": "1.2.3.4"})
        assert get_client_ip(request) == "203.0.113.9"

    async def test_forwarded_client_is_used_behind_a_trusted_proxy(self):
        request = _request("172.18.0.5", {"X-Forwarded-For": "198.51.100.7"})
        assert get_client_ip(request) == "198.51.100.7"

    async def test_real_ip_header_is_the_fallback(self):
        request = _request("127.0.0.1", {"X-Real-IP": "198.51.100.8"})
        assert get_client_ip(request) == "198.51.100.8"

    async def test_missing_client_is_reported_as_unknown(self):
        assert get_client_ip(_request(None)) == "unknown"


class TestContactFormRecordsTheVisitorIp:
    async def test_stores_the_forwarded_address_not_the_proxy(self):
        from app.api.v1.endpoints.cms import submit_contact_form
        from app.schemas.cms import ContactSubmit

        captured = []
        db = AsyncMock()
        db.add = MagicMock(side_effect=captured.append)
        db.commit = AsyncMock()

        request = _request(
            "172.18.0.5",
            {"X-Forwarded-For": "198.51.100.7", "user-agent": "pytest"},
        )
        body = ContactSubmit(
            name="Alice",
            email="alice@example.com",
            message="This is a long enough message body.",
        )

        await submit_contact_form(request=request, body=body, db=db)

        assert len(captured) == 1
        assert captured[0].ip_address == "198.51.100.7"
