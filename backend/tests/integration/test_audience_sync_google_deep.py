# =============================================================================
# Stratum AI - Google Customer Match Connector Deep Tests
# =============================================================================
"""Deep integration tests for the Google Ads Customer Match connector.

The connector talks to the Google Ads REST API with plain ``httpx``, so all
HTTP is intercepted with respx. Tests assert:

- request payload shapes (user-list mutate ops, offline-user-data-job ops,
  SHA-256 hashed identifiers per Google Customer Match spec),
- batching / chunking across the OfflineUserDataJob addOperations calls,
- error taxonomy: HTTP 4xx/5xx (Google error envelope), network/timeout
  errors, and malformed responses,
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
from app.services.cdp.audience_sync.google_connector import GoogleAudienceConnector

pytestmark = pytest.mark.integration

BASE = "https://googleads.googleapis.com/v15"
CUSTOMER_ID = "1234567890"
MUTATE_URL = f"{BASE}/customers/{CUSTOMER_ID}/userLists:mutate"
JOB_CREATE_URL = f"{BASE}/customers/{CUSTOMER_ID}/offlineUserDataJobs:create"
JOB_RESOURCE = f"customers/{CUSTOMER_ID}/offlineUserDataJobs/777"
ADD_OPS_URL = f"{BASE}/{JOB_RESOURCE}:addOperations"
RUN_URL = f"{BASE}/{JOB_RESOURCE}:run"
SEARCH_URL = f"{BASE}/customers/{CUSTOMER_ID}/googleAds:searchStream"

EMAIL_RAW = "  User@Example.COM "
EMAIL_SHA = hashlib.sha256(b"user@example.com").hexdigest()
PHONE_RAW = "+1 (555) 123-4567"
PHONE_SHA = hashlib.sha256(b"+15551234567").hexdigest()
MOBILE_RAW = "ABCDEF-123"
MOBILE_SHA = hashlib.sha256(b"abcdef-123").hexdigest()
PREHASHED = "ab" * 32


def _connector(**kwargs) -> GoogleAudienceConnector:
    return GoogleAudienceConnector(
        access_token="tok-123",
        ad_account_id="123-456-7890",
        **kwargs,
    )


def _user(profile_id: str = "p1", **extra) -> AudienceUser:
    return AudienceUser(
        profile_id=profile_id,
        identifiers=[
            UserIdentifier(IdentifierType.EMAIL, raw_value=EMAIL_RAW),
            UserIdentifier(IdentifierType.PHONE, raw_value=PHONE_RAW),
            UserIdentifier(IdentifierType.MOBILE_ADVERTISER_ID, raw_value=MOBILE_RAW),
        ],
        **extra,
    )


def _email_user(profile_id: str = "p1") -> AudienceUser:
    return AudienceUser(
        profile_id=profile_id,
        identifiers=[UserIdentifier(IdentifierType.EMAIL, raw_value=EMAIL_RAW)],
    )


def _req_json(route, call_index: int = -1) -> dict:
    return json.loads(route.calls[call_index].request.content)


def _mock_job_chain() -> tuple[respx.Route, respx.Route, respx.Route]:
    """Mock the 3-step offline user data job flow (create/addOps/run)."""
    job = respx.post(JOB_CREATE_URL).mock(
        return_value=httpx.Response(200, json={"resourceName": JOB_RESOURCE})
    )
    add = respx.post(ADD_OPS_URL).mock(return_value=httpx.Response(200, json={}))
    run = respx.post(RUN_URL).mock(return_value=httpx.Response(200, json={}))
    return job, add, run


# =============================================================================
# Construction + headers
# =============================================================================
class TestInitAndHeaders:
    def test_customer_id_dashes_stripped(self):
        assert _connector().customer_id == CUSTOMER_ID

    def test_headers_minimal(self):
        headers = _connector()._get_headers()
        assert headers == {
            "Authorization": "Bearer tok-123",
            "Content-Type": "application/json",
        }

    def test_headers_with_developer_and_login_customer(self):
        headers = _connector(
            developer_token="dev-tok",
            login_customer_id="987-654-3210",
        )._get_headers()
        assert headers["developer-token"] == "dev-tok"
        assert headers["login-customer-id"] == "9876543210"


# =============================================================================
# create_audience
# =============================================================================
class TestCreateAudience:
    @respx.mock
    async def test_create_success_no_users(self):
        route = respx.post(MUTATE_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {"resourceName": f"customers/{CUSTOMER_ID}/userLists/456"}
                    ]
                },
            )
        )

        result = await _connector().create_audience(
            AudienceConfig(name="VIP Buyers"), users=[]
        )

        assert result.success is True
        assert result.operation == "create"
        assert result.platform_audience_id == "456"
        assert result.platform_audience_name == "VIP Buyers"
        assert result.users_sent == 0

        payload = _req_json(route)
        op = payload["operations"][0]["create"]
        assert op["name"] == "VIP Buyers"
        assert op["description"] == "CDP Segment: VIP Buyers"
        assert op["membershipStatus"] == "OPEN"
        assert op["membershipLifeSpan"] == 540  # default retention
        assert op["crmBasedUserList"] == {
            "uploadKeyType": "CONTACT_INFO",
            "dataSourceType": "FIRST_PARTY",
        }
        assert route.calls.last.request.headers["Authorization"] == "Bearer tok-123"

    @respx.mock
    async def test_create_custom_retention_and_description(self):
        route = respx.post(MUTATE_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {"resourceName": f"customers/{CUSTOMER_ID}/userLists/9"}
                    ]
                },
            )
        )

        await _connector().create_audience(
            AudienceConfig(name="A", description="custom", retention_days=120),
            users=[],
        )

        op = _req_json(route)["operations"][0]["create"]
        assert op["membershipLifeSpan"] == 120
        assert op["description"] == "custom"

    @respx.mock
    async def test_create_empty_results_is_failure(self):
        respx.post(MUTATE_URL).mock(
            return_value=httpx.Response(200, json={"results": []})
        )

        result = await _connector().create_audience(AudienceConfig(name="A"), [])

        assert result.success is False
        assert result.error_message == "No user list created in response"

    @respx.mock
    async def test_create_with_users_chains_add_users(self):
        respx.post(MUTATE_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {"resourceName": f"customers/{CUSTOMER_ID}/userLists/456"}
                    ]
                },
            )
        )
        _job, add, _run = _mock_job_chain()

        result = await _connector().create_audience(
            AudienceConfig(name="Seed"), users=[_email_user()]
        )

        assert result.success is True
        assert result.operation == "create"  # rewritten from "add"
        assert result.platform_audience_id == "456"
        assert result.platform_audience_name == "Seed"
        assert result.users_sent == 1

        ops = _req_json(add)["operations"]
        assert ops[0]["create"]["userIdentifiers"] == [{"hashedEmail": EMAIL_SHA}]

    @respx.mock
    async def test_create_http_error_extracts_google_error_message(self):
        respx.post(MUTATE_URL).mock(
            return_value=httpx.Response(
                403, json={"error": {"message": "permission denied"}}
            )
        )

        result = await _connector().create_audience(AudienceConfig(name="A"), [])

        assert result.success is False
        assert result.error_message == "permission denied"
        assert result.error_details["error"]["message"] == "permission denied"
        assert result.duration_ms >= 0

    @respx.mock
    async def test_create_http_error_with_empty_body(self):
        respx.post(MUTATE_URL).mock(return_value=httpx.Response(500))

        result = await _connector().create_audience(AudienceConfig(name="A"), [])

        assert result.success is False
        assert "500" in result.error_message

    @respx.mock
    async def test_create_network_error(self):
        respx.post(MUTATE_URL).mock(side_effect=httpx.ConnectError("boom"))

        result = await _connector().create_audience(AudienceConfig(name="A"), [])

        assert result.success is False
        assert result.operation == "create"
        assert "boom" in result.error_message


# =============================================================================
# add_users
# =============================================================================
class TestAddUsers:
    @respx.mock
    async def test_add_success_hashed_payload_and_job_flow(self):
        job, add, run = _mock_job_chain()

        user = _user(
            first_name="Jane",
            last_name="Doe",
            country="US",
            zip_code="94105",
        )
        result = await _connector().add_users("456", [user])

        assert result.success is True
        assert result.operation == "add"
        assert result.platform_audience_id == "456"
        assert result.users_sent == 1
        assert result.users_added == 1
        assert result.users_failed == 0

        # Job targets the right user list
        job_payload = _req_json(job)
        assert job_payload["job"]["type"] == "CUSTOMER_MATCH_USER_LIST"
        assert (
            job_payload["job"]["customerMatchUserListMetadata"]["userList"]
            == f"customers/{CUSTOMER_ID}/userLists/456"
        )

        # Identifiers hashed per Google Customer Match spec
        add_payload = _req_json(add)
        assert add_payload["enablePartialFailure"] is True
        identifiers = add_payload["operations"][0]["create"]["userIdentifiers"]
        assert {"hashedEmail": EMAIL_SHA} in identifiers
        assert {"hashedPhoneNumber": PHONE_SHA} in identifiers
        assert {"mobileId": MOBILE_SHA} in identifiers

        address = next(i for i in identifiers if "addressInfo" in i)["addressInfo"]
        assert address["hashedFirstName"] == hashlib.sha256(b"jane").hexdigest()
        assert address["hashedLastName"] == hashlib.sha256(b"doe").hexdigest()
        assert address["countryCode"] == "US"
        assert address["postalCode"] == "94105"

        assert run.called

    @respx.mock
    async def test_add_batches_by_batch_size(self):
        _job, add, run = _mock_job_chain()

        connector = _connector()
        connector.BATCH_SIZE = 1  # force chunking
        users = [_email_user(f"p{i}") for i in range(3)]

        result = await connector.add_users("456", users)

        assert result.success is True
        assert result.users_sent == 3
        assert add.call_count == 3  # one addOperations per chunk
        assert run.call_count == 1  # job run exactly once

    @respx.mock
    async def test_add_missing_job_resource_name_is_failure(self):
        respx.post(JOB_CREATE_URL).mock(return_value=httpx.Response(200, json={}))

        result = await _connector().add_users("456", [_email_user()])

        assert result.success is False
        assert result.error_message == "Failed to create offline data job"

    @respx.mock
    async def test_add_http_error_on_job_create(self):
        respx.post(JOB_CREATE_URL).mock(
            return_value=httpx.Response(
                401, json={"error": {"message": "invalid credentials"}}
            )
        )

        result = await _connector().add_users("456", [_email_user()])

        assert result.success is False
        assert result.operation == "add"
        assert result.error_message == "invalid credentials"
        assert result.users_sent == 0

    @respx.mock
    async def test_add_http_error_on_add_operations(self):
        respx.post(JOB_CREATE_URL).mock(
            return_value=httpx.Response(200, json={"resourceName": JOB_RESOURCE})
        )
        respx.post(ADD_OPS_URL).mock(
            return_value=httpx.Response(500, json={"error": {"message": "backend"}})
        )

        result = await _connector().add_users("456", [_email_user()])

        assert result.success is False
        assert result.error_message == "backend"

    @respx.mock
    async def test_add_timeout_is_failure(self):
        respx.post(JOB_CREATE_URL).mock(side_effect=httpx.ReadTimeout("timed out"))

        result = await _connector().add_users("456", [_email_user()])

        assert result.success is False
        assert "timed out" in result.error_message


# =============================================================================
# remove_users
# =============================================================================
class TestRemoveUsers:
    @respx.mock
    async def test_remove_success_uses_remove_operations(self):
        _job, add, run = _mock_job_chain()

        result = await _connector().remove_users("456", [_email_user()])

        assert result.success is True
        assert result.operation == "remove"
        assert result.users_sent == 1
        assert result.users_removed == 1

        ops = _req_json(add)["operations"]
        assert ops[0] == {"remove": {"userIdentifiers": [{"hashedEmail": EMAIL_SHA}]}}
        assert run.called

    @respx.mock
    async def test_remove_network_error(self):
        respx.post(JOB_CREATE_URL).mock(side_effect=httpx.ConnectError("down"))

        result = await _connector().remove_users("456", [_email_user()])

        assert result.success is False
        assert result.operation == "remove"
        assert "down" in result.error_message


# =============================================================================
# replace_audience
# =============================================================================
class TestReplaceAudience:
    @respx.mock
    async def test_replace_delegates_to_add_users(self):
        """Google has no native replace; connector re-adds the full list."""
        _mock_job_chain()

        result = await _connector().replace_audience("456", [_email_user()])

        assert result.success is True
        assert result.operation == "replace"
        assert result.users_sent == 1

    @respx.mock
    async def test_replace_network_error_surfaces_as_add_failure(self):
        """add_users swallows httpx errors itself, so replace's own except
        branch is unreachable via HTTP failures; the failed add result is
        relabelled operation="replace"."""
        respx.post(JOB_CREATE_URL).mock(side_effect=httpx.ConnectError("down"))

        result = await _connector().replace_audience("456", [_email_user()])

        assert result.success is False
        assert result.operation == "replace"


# =============================================================================
# delete_audience
# =============================================================================
class TestDeleteAudience:
    @respx.mock
    async def test_delete_closes_membership(self):
        route = respx.post(MUTATE_URL).mock(
            return_value=httpx.Response(200, json={"results": [{}]})
        )

        result = await _connector().delete_audience("456")

        assert result.success is True
        assert result.operation == "delete"
        assert result.platform_audience_id == "456"

        op = _req_json(route)["operations"][0]
        assert op["update"]["membershipStatus"] == "CLOSED"
        assert op["update"]["resourceName"] == f"customers/{CUSTOMER_ID}/userLists/456"
        assert op["updateMask"] == "membershipStatus"

    @respx.mock
    async def test_delete_http_error(self):
        respx.post(MUTATE_URL).mock(return_value=httpx.Response(404))

        result = await _connector().delete_audience("456")

        assert result.success is False
        assert result.operation == "delete"


# =============================================================================
# get_audience_info
# =============================================================================
class TestGetAudienceInfo:
    @respx.mock
    async def test_info_success_parses_user_list(self):
        route = respx.post(SEARCH_URL).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {
                        "results": [
                            {
                                "userList": {
                                    "id": "456",
                                    "name": "VIP",
                                    "description": "d",
                                    "membershipStatus": "OPEN",
                                    "sizeForDisplay": "1000",
                                    "sizeForSearch": "900",
                                }
                            }
                        ]
                    }
                ],
            )
        )

        info = await _connector().get_audience_info("456")

        assert info == {
            "id": "456",
            "name": "VIP",
            "description": "d",
            "status": "OPEN",
            "size_display": "1000",
            "size_search": "900",
        }
        # GAQL query embeds the validated integer id
        query = _req_json(route)["query"]
        assert "WHERE user_list.id = 456" in query

    @respx.mock
    async def test_info_empty_stream_returns_empty_dict(self):
        respx.post(SEARCH_URL).mock(return_value=httpx.Response(200, json=[]))

        info = await _connector().get_audience_info("456")

        assert info == {}

    @respx.mock
    async def test_info_network_error_returns_error_dict(self):
        respx.post(SEARCH_URL).mock(side_effect=httpx.ConnectError("down"))

        info = await _connector().get_audience_info("456")

        assert info == {"error": "down"}

    async def test_info_non_numeric_id_returns_error_dict(self):
        """A non-numeric audience id fails the ``int(audience_id)`` GAQL-
        injection guard, and the resulting ValueError is now caught alongside
        the transport errors — the sync job fails soft with an ``{"error": ...}``
        dict rather than crashing (google_connector.py get_audience_info)."""
        info = await _connector().get_audience_info("not-a-number")

        assert "error" in info


# =============================================================================
# _prepare_google_user_data
# =============================================================================
class TestPrepareGoogleUserData:
    def test_skips_users_without_identifiers(self):
        data = _connector()._prepare_google_user_data(
            [AudienceUser(profile_id="empty")]
        )
        assert data == []

    def test_prehashed_value_used_verbatim(self):
        user = AudienceUser(
            profile_id="p1",
            identifiers=[UserIdentifier(IdentifierType.EMAIL, hashed_value=PREHASHED)],
        )
        data = _connector()._prepare_google_user_data([user])
        assert data == [[{"hashedEmail": PREHASHED}]]

    def test_identifier_without_value_skipped(self):
        user = AudienceUser(
            profile_id="p1",
            identifiers=[
                UserIdentifier(IdentifierType.EMAIL),  # no raw/hashed value
                UserIdentifier(IdentifierType.PHONE, raw_value=PHONE_RAW),
            ],
        )
        data = _connector()._prepare_google_user_data([user])
        assert data == [[{"hashedPhoneNumber": PHONE_SHA}]]

    def test_address_only_user_included(self):
        user = AudienceUser(profile_id="p1", last_name="Doe", country="US")
        data = _connector()._prepare_google_user_data([user])
        assert len(data) == 1
        address = data[0][0]["addressInfo"]
        assert address["hashedLastName"] == hashlib.sha256(b"doe").hexdigest()
        assert address["countryCode"] == "US"
        assert "hashedFirstName" not in address
        assert "postalCode" not in address

    def test_first_name_only_with_zip_but_no_country(self):
        user = AudienceUser(profile_id="p1", first_name="Jane", zip_code="94105")
        data = _connector()._prepare_google_user_data([user])
        address = data[0][0]["addressInfo"]
        assert address["hashedFirstName"] == hashlib.sha256(b"jane").hexdigest()
        assert "hashedLastName" not in address
        assert "countryCode" not in address
        assert address["postalCode"] == "94105"

    def test_external_id_identifier_ignored(self):
        user = AudienceUser(
            profile_id="p1",
            identifiers=[
                UserIdentifier(IdentifierType.EXTERNAL_ID, raw_value="crm-1"),
                UserIdentifier(
                    IdentifierType.MOBILE_ADVERTISER_ID, raw_value=MOBILE_RAW
                ),
            ],
        )
        data = _connector()._prepare_google_user_data([user])
        assert data == [[{"mobileId": MOBILE_SHA}]]
