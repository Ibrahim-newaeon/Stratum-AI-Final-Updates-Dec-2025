# =============================================================================
# Stratum AI - TikTok Custom Audience Connector Deep Tests
# =============================================================================
"""Deep integration tests for the TikTok DMP Custom Audience connector.

The connector talks to the TikTok Marketing API with plain ``httpx``, so all
HTTP is intercepted with respx. TikTok is quirky: HTTP status is always 200
and errors ride in the body ``code`` field (0 = success). Tests assert:

- request payload shapes (create, APPEND/DELETE/OVERRIDE update actions,
  per-identifier-type ``id_list`` uploads with SHA-256 hashes),
- Access-Token header auth (not Bearer),
- batching across uploads and partial-failure accounting,
- error taxonomy: body-code errors, HTTP 4xx/5xx, network/timeout errors,
- known quirks pinned (not fixed) with explanatory docstrings.
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
from app.services.cdp.audience_sync.tiktok_connector import TikTokAudienceConnector

pytestmark = pytest.mark.integration

BASE = "https://business-api.tiktok.com/open_api/v1.3"
ADVERTISER_ID = "adv-77"
AUDIENCE_ID = "aud-99"
CREATE_URL = f"{BASE}/dmp/custom_audience/create/"
UPDATE_URL = f"{BASE}/dmp/custom_audience/update/"
DELETE_URL = f"{BASE}/dmp/custom_audience/delete/"
GET_URL = f"{BASE}/dmp/custom_audience/get/"

EMAIL_RAW = "  User@Example.COM "
EMAIL_SHA = hashlib.sha256(b"user@example.com").hexdigest()
PHONE_RAW = "+1 (555) 123-4567"
PHONE_SHA = hashlib.sha256(b"+15551234567").hexdigest()
MOBILE_RAW = "ABCDEF-123"
MOBILE_SHA = hashlib.sha256(b"abcdef-123").hexdigest()

OK = {"code": 0, "message": "OK"}


def _connector() -> TikTokAudienceConnector:
    return TikTokAudienceConnector(
        access_token="tt-tok",
        ad_account_id=ADVERTISER_ID,
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
        identifiers=[
            # Valueless identifier exercises the `if not hashed: continue`
            # guard in the add/remove/replace collection loops.
            UserIdentifier(IdentifierType.PHONE),
            UserIdentifier(IdentifierType.EMAIL, raw_value=EMAIL_RAW),
        ],
    )


def _req_json(route, call_index: int = -1) -> dict:
    return json.loads(route.calls[call_index].request.content)


def _ok(data: dict | None = None) -> httpx.Response:
    return httpx.Response(200, json={**OK, "data": data or {}})


# =============================================================================
# Headers / construction
# =============================================================================
class TestHeaders:
    def test_access_token_header_not_bearer(self):
        assert _connector()._get_headers() == {
            "Access-Token": "tt-tok",
            "Content-Type": "application/json",
        }

    def test_advertiser_id_aliases_ad_account(self):
        assert _connector().advertiser_id == ADVERTISER_ID


# =============================================================================
# create_audience
# =============================================================================
class TestCreateAudience:
    @respx.mock
    async def test_create_success_no_users(self):
        route = respx.post(CREATE_URL).mock(
            return_value=_ok({"custom_audience_id": AUDIENCE_ID})
        )

        result = await _connector().create_audience(
            AudienceConfig(name="VIP Buyers"), users=[]
        )

        assert result.success is True
        assert result.operation == "create"
        assert result.platform_audience_id == AUDIENCE_ID
        assert result.platform_audience_name == "VIP Buyers"
        assert result.users_sent == 0

        payload = _req_json(route)
        assert payload == {
            "advertiser_id": ADVERTISER_ID,
            "custom_audience_name": "VIP Buyers",
            "calculate_type": "MULTIPLE_TYPES",
            "file_paths": [],
        }
        assert route.calls.last.request.headers["Access-Token"] == "tt-tok"

    @respx.mock
    async def test_create_body_code_error(self):
        respx.post(CREATE_URL).mock(
            return_value=httpx.Response(
                200, json={"code": 40001, "message": "invalid advertiser"}
            )
        )

        result = await _connector().create_audience(AudienceConfig(name="A"), [])

        assert result.success is False
        assert result.error_message == "invalid advertiser"
        assert result.error_code == "40001"

    @respx.mock
    async def test_create_missing_audience_id_is_failure(self):
        respx.post(CREATE_URL).mock(return_value=_ok({}))

        result = await _connector().create_audience(AudienceConfig(name="A"), [])

        assert result.success is False
        assert result.error_message == "No audience ID returned"

    @respx.mock
    async def test_create_with_users_chains_add_users(self):
        respx.post(CREATE_URL).mock(
            return_value=_ok({"custom_audience_id": AUDIENCE_ID})
        )
        update = respx.post(UPDATE_URL).mock(return_value=_ok())

        result = await _connector().create_audience(
            AudienceConfig(name="Seed"), users=[_email_user()]
        )

        assert result.success is True
        assert result.operation == "create"  # rewritten from "add"
        assert result.platform_audience_id == AUDIENCE_ID
        assert result.platform_audience_name == "Seed"
        assert result.users_sent == 1

        payload = _req_json(update)
        assert payload["action"] == "APPEND"
        assert payload["id_type"] == "EMAIL_SHA256"
        assert payload["id_list"] == [EMAIL_SHA]

    @respx.mock
    async def test_create_http_error_extracts_message(self):
        respx.post(CREATE_URL).mock(
            return_value=httpx.Response(403, json={"message": "forbidden"})
        )

        result = await _connector().create_audience(AudienceConfig(name="A"), [])

        assert result.success is False
        assert result.error_message == "forbidden"
        assert result.error_details == {"message": "forbidden"}

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
    async def test_add_uploads_each_identifier_type(self):
        update = respx.post(UPDATE_URL).mock(return_value=_ok())

        result = await _connector().add_users(AUDIENCE_ID, [_full_user()])

        assert result.success is True
        assert result.operation == "add"
        assert result.platform_audience_id == AUDIENCE_ID
        assert result.users_sent == 3  # one entry per identifier type
        assert result.users_added == 3
        assert result.users_failed == 0

        assert update.call_count == 3
        payloads = [_req_json(update, i) for i in range(3)]
        by_type = {p["id_type"]: p for p in payloads}
        assert set(by_type) == {"EMAIL_SHA256", "PHONE_SHA256", "IDFA_SHA256"}
        assert by_type["EMAIL_SHA256"]["id_list"] == [EMAIL_SHA]
        assert by_type["PHONE_SHA256"]["id_list"] == [PHONE_SHA]
        assert by_type["IDFA_SHA256"]["id_list"] == [MOBILE_SHA]
        for p in payloads:
            assert p["advertiser_id"] == ADVERTISER_ID
            assert p["custom_audience_id"] == AUDIENCE_ID
            assert p["action"] == "APPEND"

    @respx.mock
    async def test_add_batches_by_batch_size(self):
        update = respx.post(UPDATE_URL).mock(return_value=_ok())

        connector = _connector()
        connector.BATCH_SIZE = 1  # force chunking
        users = [_email_user(f"p{i}") for i in range(3)]

        result = await connector.add_users(AUDIENCE_ID, users)

        assert result.success is True
        assert update.call_count == 3
        assert result.users_sent == 3

    @respx.mock
    async def test_add_partial_failure_counts_failed_batch(self):
        respx.post(UPDATE_URL).mock(
            side_effect=[
                _ok(),
                httpx.Response(200, json={"code": 40100, "message": "quota"}),
            ]
        )

        user = AudienceUser(
            profile_id="p1",
            identifiers=[
                UserIdentifier(IdentifierType.EMAIL, raw_value=EMAIL_RAW),
                UserIdentifier(IdentifierType.PHONE, raw_value=PHONE_RAW),
            ],
        )
        result = await _connector().add_users(AUDIENCE_ID, [user])

        assert result.success is False  # any failed batch flips success
        assert result.users_sent == 1
        assert result.users_added == 1
        assert result.users_failed == 1

    @respx.mock
    async def test_add_no_identifiers_succeeds_without_http(self):
        result = await _connector().add_users(
            AUDIENCE_ID, [AudienceUser(profile_id="empty")]
        )

        assert result.success is True
        assert result.users_sent == 0

    @respx.mock
    async def test_add_network_error(self):
        respx.post(UPDATE_URL).mock(side_effect=httpx.ConnectError("down"))

        result = await _connector().add_users(AUDIENCE_ID, [_email_user()])

        assert result.success is False
        assert result.operation == "add"
        assert "down" in result.error_message

    @respx.mock
    async def test_add_http_status_error_treated_as_network_error(self):
        """TikTok connector has no HTTPStatusError branch in add_users; a
        4xx/5xx raise_for_status falls into the generic httpx.HTTPError
        handler and returns the exception string."""
        respx.post(UPDATE_URL).mock(return_value=httpx.Response(500))

        result = await _connector().add_users(AUDIENCE_ID, [_email_user()])

        assert result.success is False
        assert "500" in result.error_message


# =============================================================================
# remove_users
# =============================================================================
class TestRemoveUsers:
    @respx.mock
    async def test_remove_uses_delete_action(self):
        update = respx.post(UPDATE_URL).mock(return_value=_ok())

        result = await _connector().remove_users(AUDIENCE_ID, [_full_user()])

        assert result.success is True
        assert result.operation == "remove"
        assert result.users_sent == 3
        assert result.users_removed == 3

        assert update.call_count == 3
        for i in range(3):
            assert _req_json(update, i)["action"] == "DELETE"

    @respx.mock
    async def test_remove_body_code_error_reports_failure(self):
        """A non-zero body code means the removal was rejected: the result now
        reports success=False and surfaces the platform message, instead of
        silently claiming success with users_removed=0
        (tiktok_connector.py remove_users). A failed GDPR-driven removal must
        not look successful to the sync service."""
        respx.post(UPDATE_URL).mock(
            return_value=httpx.Response(200, json={"code": 40100, "message": "quota"})
        )

        result = await _connector().remove_users(AUDIENCE_ID, [_email_user()])

        assert result.success is False
        assert result.users_sent == 0
        assert result.users_removed == 0
        assert result.error_message == "quota"
        assert result.error_code == "40100"

    @respx.mock
    async def test_remove_network_error(self):
        respx.post(UPDATE_URL).mock(side_effect=httpx.ConnectError("down"))

        result = await _connector().remove_users(AUDIENCE_ID, [_email_user()])

        assert result.success is False
        assert result.operation == "remove"


# =============================================================================
# replace_audience
# =============================================================================
class TestReplaceAudience:
    @respx.mock
    async def test_replace_uses_override_action_includes_mobile_ids(self):
        """replace_audience now collects EMAIL, PHONE and MOBILE_ADVERTISER_ID
        identifiers — mobile advertiser IDs are uploaded as IDFA_SHA256 in the
        OVERRIDE payload, matching add/remove so replace syncs keep device-id
        matching (tiktok_connector.py replace_audience)."""
        update = respx.post(UPDATE_URL).mock(return_value=_ok())

        result = await _connector().replace_audience(AUDIENCE_ID, [_full_user()])

        assert result.success is True
        assert result.operation == "replace"
        assert result.users_sent == 3  # email + phone + mobile advertiser id

        assert update.call_count == 3
        payloads = [_req_json(update, i) for i in range(3)]
        assert {p["id_type"] for p in payloads} == {
            "EMAIL_SHA256",
            "PHONE_SHA256",
            "IDFA_SHA256",
        }
        by_type = {p["id_type"]: p for p in payloads}
        assert by_type["IDFA_SHA256"]["id_list"] == [MOBILE_SHA]
        for p in payloads:
            assert p["action"] == "OVERRIDE"

    @respx.mock
    async def test_replace_body_code_error_reports_failure(self):
        """Same fix as remove_users: a non-zero body code now surfaces as a
        failure with the platform message instead of a silent success."""
        respx.post(UPDATE_URL).mock(
            return_value=httpx.Response(200, json={"code": 40100, "message": "quota"})
        )

        result = await _connector().replace_audience(AUDIENCE_ID, [_email_user()])

        assert result.success is False
        assert result.users_sent == 0
        assert result.error_message == "quota"
        assert result.error_code == "40100"

    @respx.mock
    async def test_replace_skips_unmapped_identifier_types(self):
        """A replace user carrying only a phone plus an unmapped identifier
        type (EXTERNAL_ID) uploads just the phone list — email/mobile stay
        empty, so only PHONE_SHA256 is sent and the unmapped id is dropped."""
        update = respx.post(UPDATE_URL).mock(return_value=_ok())

        user = AudienceUser(
            profile_id="p1",
            identifiers=[
                UserIdentifier(IdentifierType.PHONE, raw_value=PHONE_RAW),
                UserIdentifier(IdentifierType.EXTERNAL_ID, raw_value="crm-1"),
            ],
        )
        result = await _connector().replace_audience(AUDIENCE_ID, [user])

        assert result.success is True
        assert result.users_sent == 1
        assert update.call_count == 1
        payload = _req_json(update)
        assert payload["id_type"] == "PHONE_SHA256"
        assert payload["id_list"] == [PHONE_SHA]

    @respx.mock
    async def test_replace_network_error(self):
        respx.post(UPDATE_URL).mock(side_effect=httpx.ConnectError("down"))

        result = await _connector().replace_audience(AUDIENCE_ID, [_email_user()])

        assert result.success is False
        assert result.operation == "replace"


# =============================================================================
# delete_audience
# =============================================================================
class TestDeleteAudience:
    @respx.mock
    async def test_delete_success(self):
        route = respx.post(DELETE_URL).mock(return_value=_ok())

        result = await _connector().delete_audience(AUDIENCE_ID)

        assert result.success is True
        assert result.operation == "delete"
        assert result.platform_audience_id == AUDIENCE_ID
        assert result.error_message is None

        payload = _req_json(route)
        assert payload == {
            "advertiser_id": ADVERTISER_ID,
            "custom_audience_ids": [AUDIENCE_ID],
        }

    @respx.mock
    async def test_delete_body_code_error(self):
        respx.post(DELETE_URL).mock(
            return_value=httpx.Response(
                200, json={"code": 40002, "message": "audience not found"}
            )
        )

        result = await _connector().delete_audience(AUDIENCE_ID)

        assert result.success is False
        assert result.error_message == "audience not found"

    @respx.mock
    async def test_delete_network_error(self):
        respx.post(DELETE_URL).mock(side_effect=httpx.ConnectError("down"))

        result = await _connector().delete_audience(AUDIENCE_ID)

        assert result.success is False
        assert result.operation == "delete"


# =============================================================================
# get_audience_info
# =============================================================================
class TestGetAudienceInfo:
    @respx.mock
    async def test_info_success_parses_audience(self):
        route = respx.get(GET_URL).mock(
            return_value=_ok(
                {
                    "list": [
                        {
                            "custom_audience_id": AUDIENCE_ID,
                            "custom_audience_name": "VIP",
                            "audience_size": 5000,
                            "is_valid": True,
                            "create_time": "2026-01-01 00:00:00",
                        }
                    ]
                }
            )
        )

        info = await _connector().get_audience_info(AUDIENCE_ID)

        assert info == {
            "id": AUDIENCE_ID,
            "name": "VIP",
            "size": 5000,
            "status": True,
            "create_time": "2026-01-01 00:00:00",
        }

        params = dict(route.calls.last.request.url.params)
        assert params["advertiser_id"] == ADVERTISER_ID
        assert json.loads(params["custom_audience_ids"]) == [AUDIENCE_ID]

    @respx.mock
    async def test_info_code_ok_but_empty_list_returns_error_dict(self):
        respx.get(GET_URL).mock(return_value=_ok({"list": []}))

        info = await _connector().get_audience_info(AUDIENCE_ID)

        # Falls through to the error return, echoing the body message
        assert info == {"error": "OK"}

    @respx.mock
    async def test_info_body_code_error(self):
        respx.get(GET_URL).mock(
            return_value=httpx.Response(
                200, json={"code": 40002, "message": "not found"}
            )
        )

        info = await _connector().get_audience_info(AUDIENCE_ID)

        assert info == {"error": "not found"}

    @respx.mock
    async def test_info_network_error_returns_error_dict(self):
        respx.get(GET_URL).mock(side_effect=httpx.ConnectError("down"))

        info = await _connector().get_audience_info(AUDIENCE_ID)

        assert info == {"error": "down"}
