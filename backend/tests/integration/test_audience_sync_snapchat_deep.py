# =============================================================================
# Stratum AI - Snapchat Audience Match Connector Deep Tests
# =============================================================================
"""Deep integration tests for the Snapchat SAM (Snap Audience Match) connector.

The connector talks to the Snapchat Marketing API with plain ``httpx``, so
all HTTP is intercepted with respx. Tests assert:

- request payload shapes (segment create, schema-based user uploads with
  ``[EMAIL_SHA256, PHONE_SHA256, MOBILE_AD_ID_SHA256]`` rows),
- SHA-256 hashing / normalization of identifiers,
- batching across uploads, DELETE-with-body removal,
- error taxonomy: HTTP 4xx/5xx (Snapchat error envelope), network/timeout
  errors, and malformed responses.
"""

import hashlib
import json

import httpx
import pytest
import respx

from app.services.cdp.audience_sync.base import (
    AudienceConfig,
    AudienceUser,
    IdentifierType,
    UserIdentifier,
)
from app.services.cdp.audience_sync.snapchat_connector import (
    SnapchatAudienceConnector,
)

pytestmark = pytest.mark.integration

BASE = "https://adsapi.snapchat.com/v1"
AD_ACCOUNT = "ad-acct-1"
SEGMENT_ID = "seg-42"
CREATE_URL = f"{BASE}/adaccounts/{AD_ACCOUNT}/segments"
USERS_URL = f"{BASE}/segments/{SEGMENT_ID}/users"
SEGMENT_URL = f"{BASE}/segments/{SEGMENT_ID}"

EMAIL_RAW = "  User@Example.COM "
EMAIL_SHA = hashlib.sha256(b"user@example.com").hexdigest()
PHONE_RAW = "+1 (555) 123-4567"
PHONE_SHA = hashlib.sha256(b"+15551234567").hexdigest()
MOBILE_RAW = "ABCDEF-123"
MOBILE_SHA = hashlib.sha256(b"abcdef-123").hexdigest()

SCHEMA = ["EMAIL_SHA256", "PHONE_SHA256", "MOBILE_AD_ID_SHA256"]


def _connector(**kwargs) -> SnapchatAudienceConnector:
    return SnapchatAudienceConnector(
        access_token="snap-tok",
        ad_account_id=AD_ACCOUNT,
        **kwargs,
    )


def _full_user(profile_id: str = "p1") -> AudienceUser:
    return AudienceUser(
        profile_id=profile_id,
        identifiers=[
            UserIdentifier(IdentifierType.EMAIL, raw_value=EMAIL_RAW),
            UserIdentifier(IdentifierType.PHONE, raw_value=PHONE_RAW),
            UserIdentifier(IdentifierType.MOBILE_ADVERTISER_ID, raw_value=MOBILE_RAW),
        ],
    )


def _email_user(profile_id: str = "p1") -> AudienceUser:
    return AudienceUser(
        profile_id=profile_id,
        identifiers=[UserIdentifier(IdentifierType.EMAIL, raw_value=EMAIL_RAW)],
    )


def _req_json(route, call_index: int = -1) -> dict:
    return json.loads(route.calls[call_index].request.content)


def _segment_response(**overrides) -> dict:
    segment = {
        "id": SEGMENT_ID,
        "name": "VIP",
        "description": "d",
        "status": "ACTIVE",
        "source_type": "FIRST_PARTY",
        "approximate_number_users": 1200,
        "targetable_status": "READY",
        "upload_status": "COMPLETE",
        "retention_in_days": 180,
    }
    segment.update(overrides)
    return {"segments": [{"segment": segment}]}


def _mock_get_info() -> respx.Route:
    return respx.get(SEGMENT_URL).mock(
        return_value=httpx.Response(200, json=_segment_response())
    )


# =============================================================================
# Headers
# =============================================================================
class TestHeaders:
    def test_bearer_auth_headers(self):
        assert _connector()._get_headers() == {
            "Authorization": "Bearer snap-tok",
            "Content-Type": "application/json",
        }

    def test_organization_id_stored(self):
        assert _connector(organization_id="org-9").organization_id == "org-9"


# =============================================================================
# create_audience
# =============================================================================
class TestCreateAudience:
    @respx.mock
    async def test_create_success_no_users(self):
        route = respx.post(CREATE_URL).mock(
            return_value=httpx.Response(200, json=_segment_response())
        )

        result = await _connector().create_audience(
            AudienceConfig(name="VIP Buyers"), users=[]
        )

        assert result.success is True
        assert result.operation == "create"
        assert result.platform_audience_id == SEGMENT_ID
        assert result.platform_audience_name == "VIP Buyers"
        assert result.users_sent == 0

        seg = _req_json(route)["segments"][0]
        assert seg["name"] == "VIP Buyers"
        assert seg["description"] == "CDP Segment: VIP Buyers"
        assert seg["source_type"] == "FIRST_PARTY"
        assert seg["ad_account_id"] == AD_ACCOUNT
        assert seg["retention_in_days"] == 180  # default
        assert route.calls.last.request.headers["Authorization"] == "Bearer snap-tok"

    @respx.mock
    async def test_create_custom_retention(self):
        route = respx.post(CREATE_URL).mock(
            return_value=httpx.Response(200, json=_segment_response())
        )

        await _connector().create_audience(
            AudienceConfig(name="A", retention_days=30), users=[]
        )

        assert _req_json(route)["segments"][0]["retention_in_days"] == 30

    @respx.mock
    async def test_create_empty_segments_is_failure(self):
        respx.post(CREATE_URL).mock(
            return_value=httpx.Response(200, json={"segments": []})
        )

        result = await _connector().create_audience(AudienceConfig(name="A"), [])

        assert result.success is False
        assert result.error_message == "No segment returned from Snapchat"

    @respx.mock
    async def test_create_segment_without_id_is_failure(self):
        respx.post(CREATE_URL).mock(
            return_value=httpx.Response(
                200, json={"segments": [{"segment": {"name": "no-id"}}]}
            )
        )

        result = await _connector().create_audience(AudienceConfig(name="A"), [])

        assert result.success is False
        assert result.error_message == "No segment ID in response"

    @respx.mock
    async def test_create_with_users_chains_add_users(self):
        respx.post(CREATE_URL).mock(
            return_value=httpx.Response(200, json=_segment_response())
        )
        upload = respx.post(USERS_URL).mock(
            return_value=httpx.Response(
                200, json={"users": [{"number_uploaded_users": 1}]}
            )
        )
        _mock_get_info()

        result = await _connector().create_audience(
            AudienceConfig(name="Seed"), users=[_email_user()]
        )

        assert result.success is True
        assert result.operation == "create"  # rewritten from "add"
        assert result.platform_audience_id == SEGMENT_ID
        assert result.platform_audience_name == "Seed"
        assert result.users_sent == 1
        assert upload.called

    @respx.mock
    async def test_create_http_error_extracts_error_message(self):
        respx.post(CREATE_URL).mock(
            return_value=httpx.Response(400, json={"error_message": "bad segment name"})
        )

        result = await _connector().create_audience(AudienceConfig(name="A"), [])

        assert result.success is False
        assert result.error_message == "bad segment name"
        assert result.error_details == {"error_message": "bad segment name"}

    @respx.mock
    async def test_create_http_error_with_empty_body(self):
        respx.post(CREATE_URL).mock(return_value=httpx.Response(500))

        result = await _connector().create_audience(AudienceConfig(name="A"), [])

        assert result.success is False
        assert "500" in result.error_message

    @respx.mock
    async def test_create_network_error(self):
        respx.post(CREATE_URL).mock(side_effect=httpx.ConnectError("boom"))

        result = await _connector().create_audience(AudienceConfig(name="A"), [])

        assert result.success is False
        assert "boom" in result.error_message


# =============================================================================
# add_users
# =============================================================================
class TestAddUsers:
    @respx.mock
    async def test_add_success_schema_payload_and_size(self):
        upload = respx.post(USERS_URL).mock(
            return_value=httpx.Response(
                200, json={"users": [{"number_uploaded_users": 1}]}
            )
        )
        _mock_get_info()

        result = await _connector().add_users(SEGMENT_ID, [_full_user()])

        assert result.success is True
        assert result.operation == "add"
        assert result.platform_audience_id == SEGMENT_ID
        assert result.users_sent == 1
        assert result.users_added == 1
        assert result.users_failed == 0
        assert result.audience_size == 1200  # from get_audience_info

        payload = _req_json(upload)["users"][0]
        assert payload["schema"] == SCHEMA
        assert payload["data"] == [[EMAIL_SHA, PHONE_SHA, MOBILE_SHA]]

    async def test_add_no_identifiers_short_circuits_without_http(self):
        # No respx mock active: any HTTP call would raise.
        result = await _connector().add_users(
            SEGMENT_ID, [AudienceUser(profile_id="empty")]
        )

        assert result.success is True
        assert result.users_sent == 0
        assert result.users_added == 0

    @respx.mock
    async def test_add_batches_by_batch_size(self):
        upload = respx.post(USERS_URL).mock(
            return_value=httpx.Response(
                200, json={"users": [{"number_uploaded_users": 1}]}
            )
        )
        _mock_get_info()

        connector = _connector()
        connector.BATCH_SIZE = 1  # force chunking
        users = [_email_user(f"p{i}") for i in range(3)]

        result = await connector.add_users(SEGMENT_ID, users)

        assert result.success is True
        assert upload.call_count == 3
        assert result.users_sent == 3
        assert result.users_added == 3

    @respx.mock
    async def test_add_defaults_uploaded_count_to_batch_size(self):
        respx.post(USERS_URL).mock(
            return_value=httpx.Response(200, json={"users": [{}]})
        )
        _mock_get_info()

        result = await _connector().add_users(SEGMENT_ID, [_email_user()])

        assert result.users_added == 1  # falls back to len(batch)

    @respx.mock
    async def test_add_http_error_extracts_error_message(self):
        respx.post(USERS_URL).mock(
            return_value=httpx.Response(429, json={"error_message": "rate limited"})
        )

        result = await _connector().add_users(SEGMENT_ID, [_email_user()])

        assert result.success is False
        assert result.operation == "add"
        assert result.error_message == "rate limited"
        assert result.users_sent == 0

    @respx.mock
    async def test_add_timeout_is_failure(self):
        respx.post(USERS_URL).mock(side_effect=httpx.ReadTimeout("timed out"))

        result = await _connector().add_users(SEGMENT_ID, [_email_user()])

        assert result.success is False
        assert "timed out" in result.error_message


# =============================================================================
# remove_users
# =============================================================================
class TestRemoveUsers:
    @respx.mock
    async def test_remove_success_delete_with_body(self):
        route = respx.delete(USERS_URL).mock(
            return_value=httpx.Response(
                200, json={"users": [{"number_uploaded_users": 1}]}
            )
        )

        result = await _connector().remove_users(SEGMENT_ID, [_full_user()])

        assert result.success is True
        assert result.operation == "remove"
        assert result.users_sent == 1
        assert result.users_removed == 1

        assert route.calls.last.request.method == "DELETE"
        payload = _req_json(route)["users"][0]
        assert payload["schema"] == SCHEMA
        assert payload["data"] == [[EMAIL_SHA, PHONE_SHA, MOBILE_SHA]]

    async def test_remove_no_identifiers_short_circuits(self):
        result = await _connector().remove_users(
            SEGMENT_ID, [AudienceUser(profile_id="empty")]
        )

        assert result.success is True
        assert result.users_sent == 0

    @respx.mock
    async def test_remove_network_error(self):
        respx.delete(USERS_URL).mock(side_effect=httpx.ConnectError("down"))

        result = await _connector().remove_users(SEGMENT_ID, [_email_user()])

        assert result.success is False
        assert result.operation == "remove"
        assert "down" in result.error_message


# =============================================================================
# replace_audience
# =============================================================================
class TestReplaceAudience:
    @respx.mock
    async def test_replace_delegates_to_add_users(self):
        """Snapchat has no native replace; connector re-uploads the list."""
        respx.post(USERS_URL).mock(
            return_value=httpx.Response(
                200, json={"users": [{"number_uploaded_users": 1}]}
            )
        )
        _mock_get_info()

        result = await _connector().replace_audience(SEGMENT_ID, [_email_user()])

        assert result.success is True
        assert result.operation == "replace"
        assert result.users_sent == 1

    @respx.mock
    async def test_replace_failure_relabelled(self):
        """add_users swallows httpx errors itself, so replace's own except
        branch is unreachable via HTTP failures; the failed add result is
        relabelled operation="replace"."""
        respx.post(USERS_URL).mock(side_effect=httpx.ConnectError("down"))

        result = await _connector().replace_audience(SEGMENT_ID, [_email_user()])

        assert result.success is False
        assert result.operation == "replace"


# =============================================================================
# delete_audience
# =============================================================================
class TestDeleteAudience:
    @respx.mock
    async def test_delete_success(self):
        route = respx.delete(SEGMENT_URL).mock(
            return_value=httpx.Response(200, json={"request_status": "SUCCESS"})
        )

        result = await _connector().delete_audience(SEGMENT_ID)

        assert result.success is True
        assert result.operation == "delete"
        assert result.platform_audience_id == SEGMENT_ID
        assert result.platform_response == {"request_status": "SUCCESS"}
        assert route.called

    @respx.mock
    async def test_delete_http_error(self):
        respx.delete(SEGMENT_URL).mock(return_value=httpx.Response(404))

        result = await _connector().delete_audience(SEGMENT_ID)

        assert result.success is False
        assert result.operation == "delete"


# =============================================================================
# get_audience_info
# =============================================================================
class TestGetAudienceInfo:
    @respx.mock
    async def test_info_success_full_field_map(self):
        _mock_get_info()

        info = await _connector().get_audience_info(SEGMENT_ID)

        assert info == {
            "id": SEGMENT_ID,
            "name": "VIP",
            "description": "d",
            "status": "ACTIVE",
            "source_type": "FIRST_PARTY",
            "approximate_number_users": 1200,
            "targetable_status": "READY",
            "upload_status": "COMPLETE",
            "retention_in_days": 180,
        }

    @respx.mock
    async def test_info_empty_segments_returns_empty_dict(self):
        respx.get(SEGMENT_URL).mock(
            return_value=httpx.Response(200, json={"segments": []})
        )

        info = await _connector().get_audience_info(SEGMENT_ID)

        assert info == {}

    @respx.mock
    async def test_info_network_error_returns_error_dict(self):
        respx.get(SEGMENT_URL).mock(side_effect=httpx.ConnectError("down"))

        info = await _connector().get_audience_info(SEGMENT_ID)

        assert info == {"error": "down"}


# =============================================================================
# _prepare_snapchat_user_data
# =============================================================================
class TestPrepareSnapchatUserData:
    def test_partial_identifiers_use_empty_placeholders(self):
        user = AudienceUser(
            profile_id="p1",
            identifiers=[UserIdentifier(IdentifierType.PHONE, raw_value=PHONE_RAW)],
        )
        data = _connector()._prepare_snapchat_user_data([user])
        assert data == [["", PHONE_SHA, ""]]

    def test_skips_users_without_any_identifier(self):
        users = [
            AudienceUser(profile_id="empty"),
            AudienceUser(
                profile_id="valueless",
                identifiers=[UserIdentifier(IdentifierType.EMAIL)],
            ),
        ]
        assert _connector()._prepare_snapchat_user_data(users) == []

    def test_external_id_ignored(self):
        user = AudienceUser(
            profile_id="p1",
            identifiers=[
                UserIdentifier(IdentifierType.EXTERNAL_ID, raw_value="crm-1"),
                UserIdentifier(IdentifierType.EMAIL, raw_value=EMAIL_RAW),
            ],
        )
        data = _connector()._prepare_snapchat_user_data([user])
        assert data == [[EMAIL_SHA, "", ""]]
