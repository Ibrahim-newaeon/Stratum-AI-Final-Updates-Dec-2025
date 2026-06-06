# =============================================================================
# Stratum AI - MFA-at-Login Tests
# =============================================================================
"""
Tests for the MFA-at-login enforcement (P0-1).

Before this, ``/auth/login`` issued full tokens with no second-factor step.
Now an MFA-enabled user receives a short-lived ``mfa_challenge`` token that
must be exchanged at ``/auth/login/mfa``. These tests pin the stateless
contract the gate relies on.
"""

from datetime import timedelta

from app.base_schemas import LoginResponse, MFALoginRequest
from app.core.security import create_access_token, decode_token


def test_mfa_challenge_token_is_distinct_from_access_token():
    """The /login/mfa gate keys off token ``type`` — the two must differ."""
    challenge = create_access_token(
        subject=42,
        expires_delta=timedelta(minutes=5),
        additional_claims={"type": "mfa_challenge"},
    )
    access = create_access_token(subject=42)

    challenge_payload = decode_token(challenge)
    access_payload = decode_token(access)

    assert challenge_payload is not None and access_payload is not None
    assert challenge_payload["type"] == "mfa_challenge"
    assert access_payload["type"] == "access"
    # An access token must NOT be accepted as a challenge (and vice-versa).
    assert challenge_payload["type"] != access_payload["type"]
    assert challenge_payload["sub"] == "42"


def test_login_response_supports_mfa_challenge_shape():
    resp = LoginResponse(mfa_required=True, mfa_token="challenge-token")
    assert resp.mfa_required is True
    assert resp.mfa_token == "challenge-token"
    assert resp.access_token is None  # no tokens until second factor verified


def test_login_response_supports_token_shape():
    resp = LoginResponse(
        access_token="a", refresh_token="r", expires_in=1800, available_tenants=[]
    )
    assert resp.mfa_required is False
    assert resp.access_token == "a"
    assert resp.refresh_token == "r"


def test_mfa_login_request_validates_code_length():
    ok = MFALoginRequest(mfa_token="t", code="123456")
    assert ok.code == "123456"

    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        MFALoginRequest(mfa_token="t", code="123")  # too short
