# =============================================================================
# Stratum AI - Auth Signup-OTP Endpoint Integration Tests
# =============================================================================
"""Integration tests for the signup verification OTP endpoints:

- ``POST /auth/whatsapp/send-otp`` / ``POST /auth/whatsapp/verify-otp``
- ``POST /auth/email/send-otp`` / ``POST /auth/email/verify-otp``

OTPs are stored in the real Redis instance; the WhatsApp client and email
service delivery seams are stubbed (following the existing email-stub
pattern in test_auth_accept_invite_api.py). The verify half reads the
generated OTP straight out of Redis, and the returned verification token
is driven through ``POST /auth/register`` for the full signup round trip.
"""

import uuid

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_SEND_WA = "/api/v1/auth/whatsapp/send-otp"
_VERIFY_WA = "/api/v1/auth/whatsapp/verify-otp"
_SEND_EMAIL = "/api/v1/auth/email/send-otp"
_VERIFY_EMAIL = "/api/v1/auth/email/verify-otp"
_REGISTER = "/api/v1/auth/register"


def _unique_phone() -> str:
    """E.164 phone unique per test (Redis is shared across runs)."""
    return "+1555" + str(uuid.uuid4().int)[:7]


def _unique_email() -> str:
    return f"otp-{uuid.uuid4().hex[:10]}@example.com"


async def _redis_get(key: str):
    from app.api.v1.endpoints.auth import get_redis_client

    rc = await get_redis_client()
    try:
        return await rc.get(key)
    finally:
        await rc.close()


async def _redis_setex(key: str, value: str, ttl: int = 600) -> None:
    from app.api.v1.endpoints.auth import get_redis_client

    rc = await get_redis_client()
    try:
        await rc.setex(key, ttl, value)
    finally:
        await rc.close()


@pytest.fixture
def redis_down(monkeypatch):
    """Make the auth module's Redis factory raise ConnectionError."""
    import app.api.v1.endpoints.auth as auth_module

    async def _boom():
        raise ConnectionError("redis down (test)")

    monkeypatch.setattr(auth_module, "get_redis_client", _boom)


class _StubWhatsAppClient:
    """Captures template/text sends; optionally raises on send."""

    def __init__(self, fail_with: Exception | None = None):
        self.calls: list = []
        self._fail_with = fail_with

    async def send_template_message(self, **kwargs):
        if self._fail_with:
            raise self._fail_with
        self.calls.append(("template", kwargs))

    async def send_text_message(self, **kwargs):
        if self._fail_with:
            raise self._fail_with
        self.calls.append(("text", kwargs))


@pytest.fixture
def whatsapp_ready(monkeypatch) -> _StubWhatsAppClient:
    """Pretend WhatsApp is configured and stub the delivery client."""
    import app.api.v1.endpoints.auth as auth_module

    stub = _StubWhatsAppClient()
    monkeypatch.setattr(auth_module, "is_whatsapp_configured", lambda: True)
    monkeypatch.setattr(auth_module, "get_whatsapp_client", lambda: stub)
    return stub


class _StubEmailService:
    def __init__(self):
        self.otp_emails: list = []
        self.otp_result = True
        self.raise_exc: Exception | None = None

    def send_otp_email(self, to_email: str, otp_code: str) -> bool:
        if self.raise_exc:
            raise self.raise_exc
        self.otp_emails.append((to_email, otp_code))
        return self.otp_result

    def send_welcome_email(self, **kwargs):  # register round trips send this
        return True


@pytest.fixture
def email_stub(monkeypatch) -> _StubEmailService:
    import app.api.v1.endpoints.auth as auth_module

    stub = _StubEmailService()
    monkeypatch.setattr(auth_module, "get_email_service", lambda: stub)
    return stub


# =============================================================================
# WhatsApp OTP
# =============================================================================


class TestWhatsAppSendOtp:
    async def test_not_configured_503(self, client, monkeypatch):
        import app.api.v1.endpoints.auth as auth_module

        monkeypatch.setattr(auth_module, "is_whatsapp_configured", lambda: False)
        resp = await client.post(_SEND_WA, json={"phone_number": _unique_phone()})
        assert resp.status_code == 503

    async def test_invalid_phone_400(self, client, whatsapp_ready):
        resp = await client.post(_SEND_WA, json={"phone_number": "abc"})
        assert resp.status_code == 400

    async def test_send_stores_otp_and_delivers(self, client, whatsapp_ready):
        from app.api.v1.endpoints.auth import OTP_PREFIX

        phone = _unique_phone()
        resp = await client.post(_SEND_WA, json={"phone_number": phone})
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["expires_in"] > 0

        stored = await _redis_get(f"{OTP_PREFIX}{phone}")
        assert stored is not None and len(stored) == 6 and stored.isdigit()

        # Background task delivered the auth template with the same code
        assert len(whatsapp_ready.calls) == 1
        kind, kwargs = whatsapp_ready.calls[0]
        assert kind == "template"
        assert kwargs["template_name"] == "stratum_verify_code"

    async def test_phone_is_normalized(self, client, whatsapp_ready):
        from app.api.v1.endpoints.auth import OTP_PREFIX

        raw = _unique_phone()  # e.g. +15551234567
        digits = raw[1:]
        messy = f"{digits[0]} ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        resp = await client.post(_SEND_WA, json={"phone_number": messy})
        assert resp.status_code == 200, resp.text
        # Stored under the normalized E.164 key
        assert await _redis_get(f"{OTP_PREFIX}{raw}") is not None

    async def test_whatsapp_api_error_does_not_fail_request(self, client, monkeypatch):
        import app.api.v1.endpoints.auth as auth_module
        from app.services.whatsapp_client import WhatsAppAPIError

        stub = _StubWhatsAppClient(fail_with=WhatsAppAPIError("boom", "131026"))
        monkeypatch.setattr(auth_module, "is_whatsapp_configured", lambda: True)
        monkeypatch.setattr(auth_module, "get_whatsapp_client", lambda: stub)

        resp = await client.post(_SEND_WA, json={"phone_number": _unique_phone()})
        assert resp.status_code == 200

    async def test_whatsapp_unconfigured_at_send_time_does_not_fail_request(
        self, client, monkeypatch
    ):
        import app.api.v1.endpoints.auth as auth_module
        from app.services.whatsapp_client import WhatsAppNotConfiguredError

        def _raise():
            raise WhatsAppNotConfiguredError("gone")

        monkeypatch.setattr(auth_module, "is_whatsapp_configured", lambda: True)
        monkeypatch.setattr(auth_module, "get_whatsapp_client", _raise)

        resp = await client.post(_SEND_WA, json={"phone_number": _unique_phone()})
        assert resp.status_code == 200

    async def test_whatsapp_connection_error_does_not_fail_request(
        self, client, monkeypatch
    ):
        import app.api.v1.endpoints.auth as auth_module

        stub = _StubWhatsAppClient(fail_with=ConnectionError("network down"))
        monkeypatch.setattr(auth_module, "is_whatsapp_configured", lambda: True)
        monkeypatch.setattr(auth_module, "get_whatsapp_client", lambda: stub)

        resp = await client.post(_SEND_WA, json={"phone_number": _unique_phone()})
        assert resp.status_code == 200

    async def test_redis_down_500(self, client, whatsapp_ready, redis_down):
        resp = await client.post(_SEND_WA, json={"phone_number": _unique_phone()})
        assert resp.status_code == 500


class TestWhatsAppVerifyOtp:
    async def test_invalid_phone_400(self, client):
        resp = await client.post(
            _VERIFY_WA, json={"phone_number": "abc", "otp_code": "123456"}
        )
        assert resp.status_code == 400

    async def test_no_otp_stored_400(self, client):
        resp = await client.post(
            _VERIFY_WA,
            json={"phone_number": _unique_phone(), "otp_code": "123456"},
        )
        assert resp.status_code == 400
        assert "expired or not found" in resp.json()["detail"].lower()

    async def test_wrong_code_400(self, client):
        from app.api.v1.endpoints.auth import OTP_PREFIX

        phone = _unique_phone()
        await _redis_setex(f"{OTP_PREFIX}{phone}", "123456")
        resp = await client.post(
            _VERIFY_WA, json={"phone_number": phone, "otp_code": "654321"}
        )
        assert resp.status_code == 400
        assert "invalid otp" in resp.json()["detail"].lower()

    async def test_correct_code_returns_token_then_registers(self, client, email_stub):
        from app.api.v1.endpoints.auth import OTP_PREFIX

        phone = _unique_phone()
        await _redis_setex(f"{OTP_PREFIX}{phone}", "123456")

        resp = await client.post(
            _VERIFY_WA, json={"phone_number": phone, "otp_code": "123456"}
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["verified"] is True
        assert data["verification_token"]

        # The OTP is one-time use
        again = await client.post(
            _VERIFY_WA, json={"phone_number": phone, "otp_code": "123456"}
        )
        assert again.status_code == 400

        # Full signup round trip with the issued verification token
        register = await client.post(
            _REGISTER,
            json={
                "email": _unique_email(),
                "password": "Testpassword123",
                "full_name": "WhatsApp Signup",
                "verification_token": data["verification_token"],
            },
        )
        assert register.status_code == 200, register.text

    async def test_redis_down_500(self, client, redis_down):
        resp = await client.post(
            _VERIFY_WA,
            json={"phone_number": _unique_phone(), "otp_code": "123456"},
        )
        assert resp.status_code == 500


# =============================================================================
# Email OTP
# =============================================================================


class TestEmailSendOtp:
    async def test_invalid_email_400(self, client, email_stub):
        resp = await client.post(_SEND_EMAIL, json={"email": "not-an-email"})
        assert resp.status_code == 400

    async def test_send_stores_otp_and_delivers(self, client, email_stub):
        from app.api.v1.endpoints.auth import EMAIL_OTP_PREFIX

        email = _unique_email()
        resp = await client.post(_SEND_EMAIL, json={"email": email})
        assert resp.status_code == 200, resp.text

        stored = await _redis_get(f"{EMAIL_OTP_PREFIX}{email}")
        assert stored is not None and len(stored) == 6 and stored.isdigit()

        assert len(email_stub.otp_emails) == 1
        to_email, otp_code = email_stub.otp_emails[0]
        assert to_email == email
        assert otp_code == stored

    async def test_provider_returning_false_does_not_fail_request(
        self, client, email_stub
    ):
        email_stub.otp_result = False
        resp = await client.post(_SEND_EMAIL, json={"email": _unique_email()})
        assert resp.status_code == 200

    async def test_provider_error_does_not_fail_request(self, client, email_stub):
        email_stub.raise_exc = ConnectionError("smtp down")
        resp = await client.post(_SEND_EMAIL, json={"email": _unique_email()})
        assert resp.status_code == 200

    async def test_redis_down_500(self, client, email_stub, redis_down):
        resp = await client.post(_SEND_EMAIL, json={"email": _unique_email()})
        assert resp.status_code == 500


class TestEmailVerifyOtp:
    async def test_no_otp_stored_400(self, client):
        resp = await client.post(
            _VERIFY_EMAIL, json={"email": _unique_email(), "otp_code": "123456"}
        )
        assert resp.status_code == 400

    async def test_wrong_code_400(self, client):
        from app.api.v1.endpoints.auth import EMAIL_OTP_PREFIX

        email = _unique_email()
        await _redis_setex(f"{EMAIL_OTP_PREFIX}{email}", "123456")
        resp = await client.post(
            _VERIFY_EMAIL, json={"email": email, "otp_code": "654321"}
        )
        assert resp.status_code == 400

    async def test_correct_code_returns_token_then_registers(self, client, email_stub):
        from app.api.v1.endpoints.auth import EMAIL_OTP_PREFIX

        email = _unique_email()
        await _redis_setex(f"{EMAIL_OTP_PREFIX}{email}", "123456")

        resp = await client.post(
            _VERIFY_EMAIL, json={"email": email, "otp_code": "123456"}
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["verified"] is True
        assert data["verification_token"]

        register = await client.post(
            _REGISTER,
            json={
                "email": email,
                "password": "Testpassword123",
                "full_name": "Email Signup",
                "verification_token": data["verification_token"],
            },
        )
        assert register.status_code == 200, register.text

    async def test_redis_down_500(self, client, redis_down):
        resp = await client.post(
            _VERIFY_EMAIL, json={"email": _unique_email(), "otp_code": "123456"}
        )
        assert resp.status_code == 500
