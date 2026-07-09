# =============================================================================
# Stratum AI - Meta Audience Connector Deep Integration Tests (#342 Batch 5+6)
# =============================================================================
"""HTTP-level integration tests for ``MetaAudienceConnector``.

The unit suite (``tests/unit/test_audience_sync.py``) covers constructor
prefixing, payload preparation helpers, and create/delete with hand-mocked
``httpx.AsyncClient`` objects. This file exercises the real httpx transport
via respx against Meta Graph API URLs, covering the paths the unit tests
leave untouched:

- ``add_users``: multi-batch upload, num_invalid accounting, mid-batch
  HTTPStatusError (partial accounting), empty error body, network error,
  and SHA-256 hashed multi-key payload correctness.
- ``remove_users``: happy path, default num_received fallback, network error.
- ``replace_audience``: session-based replace with batch_seq/last_batch_flag,
  fallback to add_users when no session id, network error.
- ``delete_audience`` / ``get_audience_info``: success + error branches.
- ``create_audience``: full create-then-add flow with hashed payloads.

Behavior quirks pinned here (NOT fixed — source untouched):
- ``replace_audience`` fallback returns a result labeled operation="add".
- ``delete_audience`` with platform response ``{"success": false}`` yields
  ``success=False`` with ``error_message=None``.
- ``add_users`` reports ``success=True`` even if every entry is invalid.
"""

import hashlib
import json
from urllib.parse import parse_qs

import httpx
import pytest
import respx

from app.services.cdp.audience_sync.base import (
    AudienceConfig,
    AudienceUser,
    IdentifierType,
    UserIdentifier,
)
from app.services.cdp.audience_sync.meta_connector import MetaAudienceConnector

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

GRAPH = "https://graph.facebook.com/v18.0"


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _conn(**kwargs) -> MetaAudienceConnector:
    return MetaAudienceConnector(
        access_token="tok-secret", ad_account_id="123", **kwargs
    )


def _user(pid: str, email=None, phone=None, madid=None) -> AudienceUser:
    identifiers = []
    if email:
        identifiers.append(
            UserIdentifier(identifier_type=IdentifierType.EMAIL, raw_value=email)
        )
    if phone:
        identifiers.append(
            UserIdentifier(identifier_type=IdentifierType.PHONE, raw_value=phone)
        )
    if madid:
        identifiers.append(
            UserIdentifier(
                identifier_type=IdentifierType.MOBILE_ADVERTISER_ID,
                hashed_value=madid,
            )
        )
    return AudienceUser(profile_id=pid, identifiers=identifiers)


def _payload(route_call) -> dict:
    return json.loads(route_call.request.content)


# =============================================================================
# add_users
# =============================================================================


class TestAddUsers:
    async def test_single_batch_hashed_payload_and_accounting(self):
        conn = _conn()
        users = [
            _user("p1", email="User1@Example.COM ", phone="+1 (555) 123-4567"),
            _user("p2", madid="madid-hash-raw"),
        ]

        with respx.mock:
            users_route = respx.post(f"{GRAPH}/aud1/users").mock(
                return_value=httpx.Response(
                    200, json={"num_received": 2, "num_invalid_entries": 1}
                )
            )
            respx.get(f"{GRAPH}/aud1").mock(
                return_value=httpx.Response(200, json={"approximate_count": 555})
            )

            result = await conn.add_users("aud1", users)

        assert result.success is True
        assert result.operation == "add"
        assert result.platform_audience_id == "aud1"
        assert result.users_sent == 2
        assert result.users_added == 1
        assert result.users_failed == 1
        assert result.audience_size == 555
        assert result.duration_ms >= 0

        payload = _payload(users_route.calls[0])
        assert payload["access_token"] == "tok-secret"
        assert payload["payload"]["schema"] == ["EMAIL", "PHONE", "MADID"]
        rows = payload["payload"]["data"]
        # Raw PII is normalized then SHA-256 hashed before leaving the process.
        assert rows[0] == [
            _sha("user1@example.com"),
            _sha("+15551234567"),
            "",
        ]
        assert rows[1] == ["", "", "madid-hash-raw"]

    async def test_multi_batch_upload_accumulates_totals(self):
        conn = _conn()
        conn.BATCH_SIZE = 2  # instance attr shadows class constant
        users = [_user(f"p{i}", email=f"u{i}@x.com") for i in range(5)]

        with respx.mock:
            users_route = respx.post(f"{GRAPH}/aud2/users").mock(
                side_effect=[
                    httpx.Response(200, json={"num_received": 2}),
                    httpx.Response(
                        200, json={"num_received": 2, "num_invalid_entries": 1}
                    ),
                    httpx.Response(200, json={"num_received": 1}),
                ]
            )
            respx.get(f"{GRAPH}/aud2").mock(
                return_value=httpx.Response(200, json={"approximate_count": 9})
            )

            result = await conn.add_users("aud2", users)

        assert users_route.call_count == 3
        assert result.users_sent == 5
        assert result.users_added == 4
        assert result.users_failed == 1
        # Batch boundaries: 2 + 2 + 1
        assert len(_payload(users_route.calls[0])["payload"]["data"]) == 2
        assert len(_payload(users_route.calls[2])["payload"]["data"]) == 1

    async def test_all_entries_invalid_still_reports_success(self):
        """Pins behavior: HTTP 200 with every entry invalid => success=True.

        The connector treats transport success as operation success even when
        num_invalid_entries == num_received (users_added == 0).
        """
        conn = _conn()

        with respx.mock:
            respx.post(f"{GRAPH}/aud3/users").mock(
                return_value=httpx.Response(
                    200, json={"num_received": 1, "num_invalid_entries": 1}
                )
            )
            respx.get(f"{GRAPH}/aud3").mock(return_value=httpx.Response(200, json={}))

            result = await conn.add_users("aud3", [_user("p1", email="a@b.com")])

        assert result.success is True
        assert result.users_added == 0
        assert result.users_failed == 1
        assert result.audience_size is None

    async def test_mid_batch_http_error_keeps_partial_totals(self):
        conn = _conn()
        conn.BATCH_SIZE = 2
        users = [_user(f"p{i}", email=f"e{i}@x.com") for i in range(4)]

        with respx.mock:
            respx.post(f"{GRAPH}/aud4/users").mock(
                side_effect=[
                    httpx.Response(
                        200, json={"num_received": 2, "num_invalid_entries": 1}
                    ),
                    httpx.Response(
                        400,
                        json={
                            "error": {"message": "User limit reached", "code": 80003}
                        },
                    ),
                ]
            )

            result = await conn.add_users("aud4", users)

        assert result.success is False
        assert result.users_sent == 2
        assert result.users_added == 1
        assert result.users_failed == 1
        assert result.error_message == "User limit reached"
        assert result.error_details["error"]["code"] == 80003

    async def test_http_error_with_empty_body(self):
        conn = _conn()

        with respx.mock:
            respx.post(f"{GRAPH}/aud5/users").mock(return_value=httpx.Response(500))

            result = await conn.add_users("aud5", [_user("p1", email="a@b.com")])

        assert result.success is False
        assert "500" in result.error_message

    async def test_network_error(self):
        conn = _conn()

        with respx.mock:
            respx.post(f"{GRAPH}/aud6/users").mock(
                side_effect=httpx.ConnectError("dns down")
            )

            result = await conn.add_users("aud6", [_user("p1", email="a@b.com")])

        assert result.success is False
        assert "dns down" in result.error_message

    async def test_user_without_hashable_identifier_dropped_from_payload(self):
        conn = _conn()
        users = [
            _user("p1", email="keep@x.com"),
            # Identifier with neither raw nor hashed value -> get_hashed() None
            AudienceUser(
                profile_id="p2",
                identifiers=[UserIdentifier(identifier_type=IdentifierType.EMAIL)],
            ),
            # External-ID-only user does not map to any Meta schema column
            AudienceUser(
                profile_id="p3",
                identifiers=[
                    UserIdentifier(
                        identifier_type=IdentifierType.EXTERNAL_ID,
                        hashed_value="ext-hash",
                    )
                ],
            ),
        ]

        with respx.mock:
            users_route = respx.post(f"{GRAPH}/aud7/users").mock(
                return_value=httpx.Response(200, json={"num_received": 1})
            )
            respx.get(f"{GRAPH}/aud7").mock(return_value=httpx.Response(200, json={}))

            result = await conn.add_users("aud7", users)

        rows = _payload(users_route.calls[0])["payload"]["data"]
        assert rows == [[_sha("keep@x.com"), "", ""]]
        assert result.users_sent == 1


# =============================================================================
# remove_users
# =============================================================================


class TestRemoveUsers:
    async def test_remove_success_with_num_received_fallback(self):
        conn = _conn()
        users = [
            _user("p1", email="gone1@x.com"),
            _user("p2", email="gone2@x.com"),
        ]

        with respx.mock:
            # Response without num_received -> falls back to len(batch)
            del_route = respx.delete(f"{GRAPH}/aud8/users").mock(
                return_value=httpx.Response(200, json={"session_id": "ignored"})
            )

            result = await conn.remove_users("aud8", users)

        assert result.success is True
        assert result.operation == "remove"
        assert result.users_sent == 2
        assert result.users_removed == 2
        payload = _payload(del_route.calls[0])
        assert payload["payload"]["schema"] == ["EMAIL", "PHONE", "MADID"]
        assert payload["payload"]["data"][0][0] == _sha("gone1@x.com")

    async def test_remove_uses_platform_reported_count(self):
        conn = _conn()

        with respx.mock:
            respx.delete(f"{GRAPH}/aud9/users").mock(
                return_value=httpx.Response(200, json={"num_received": 1})
            )

            result = await conn.remove_users(
                "aud9", [_user("p1", email="a@b.com"), _user("p2", email="b@b.com")]
            )

        assert result.users_sent == 1
        assert result.users_removed == 1

    async def test_remove_http_error(self):
        conn = _conn()

        with respx.mock:
            respx.delete(f"{GRAPH}/aud10/users").mock(
                return_value=httpx.Response(400, json={"error": {"message": "nope"}})
            )

            result = await conn.remove_users("aud10", [_user("p1", email="a@b.com")])

        assert result.success is False
        assert result.error_message

    async def test_remove_network_error(self):
        conn = _conn()

        with respx.mock:
            respx.delete(f"{GRAPH}/aud11/users").mock(
                side_effect=httpx.ConnectError("reset")
            )

            result = await conn.remove_users("aud11", [_user("p1", email="a@b.com")])

        assert result.success is False
        assert "reset" in result.error_message


# =============================================================================
# replace_audience
# =============================================================================


class TestReplaceAudience:
    async def test_session_replace_batches_with_sequence_flags(self):
        conn = _conn()
        conn.BATCH_SIZE = 2
        users = [_user(f"p{i}", email=f"r{i}@x.com") for i in range(3)]

        with respx.mock:
            session_route = respx.post(f"{GRAPH}/aud12/usersreplace").mock(
                return_value=httpx.Response(200, json={"session_id": "sess-9"})
            )
            users_route = respx.post(f"{GRAPH}/aud12/users").mock(
                return_value=httpx.Response(200, json={})
            )

            result = await conn.replace_audience("aud12", users)

        assert result.success is True
        assert result.operation == "replace"
        assert result.users_sent == 3
        assert result.users_added == 3

        # Session creation posts the token as form data
        session_body = parse_qs(session_route.calls[0].request.content.decode())
        assert session_body["access_token"] == ["tok-secret"]

        assert users_route.call_count == 2
        first = _payload(users_route.calls[0])
        second = _payload(users_route.calls[1])
        assert first["session"] == {
            "session_id": "sess-9",
            "batch_seq": 1,
            "last_batch_flag": False,
        }
        assert second["session"]["batch_seq"] == 2
        assert second["session"]["last_batch_flag"] is True
        assert second["payload"]["data"] == [[_sha("r2@x.com"), "", ""]]

    async def test_replace_without_session_falls_back_to_add(self):
        """Pins behavior: fallback result is labeled operation="add".

        When Meta returns no session_id, replace_audience delegates to
        add_users and returns its result unchanged — callers asking for a
        replace get back operation="add".
        """
        conn = _conn()

        with respx.mock:
            respx.post(f"{GRAPH}/aud13/usersreplace").mock(
                return_value=httpx.Response(200, json={})
            )
            respx.post(f"{GRAPH}/aud13/users").mock(
                return_value=httpx.Response(200, json={"num_received": 1})
            )
            respx.get(f"{GRAPH}/aud13").mock(
                return_value=httpx.Response(200, json={"approximate_count": 1})
            )

            result = await conn.replace_audience(
                "aud13", [_user("p1", email="a@b.com")]
            )

        assert result.success is True
        assert result.operation == "add"  # quirk pinned; see docstring
        assert result.users_sent == 1

    async def test_replace_session_http_error(self):
        conn = _conn()

        with respx.mock:
            respx.post(f"{GRAPH}/aud14/usersreplace").mock(
                return_value=httpx.Response(500)
            )

            result = await conn.replace_audience(
                "aud14", [_user("p1", email="a@b.com")]
            )

        assert result.success is False
        assert result.operation == "replace"

    async def test_replace_network_error(self):
        conn = _conn()

        with respx.mock:
            respx.post(f"{GRAPH}/aud15/usersreplace").mock(
                side_effect=httpx.ConnectError("boom")
            )

            result = await conn.replace_audience(
                "aud15", [_user("p1", email="a@b.com")]
            )

        assert result.success is False
        assert "boom" in result.error_message


# =============================================================================
# delete_audience / get_audience_info
# =============================================================================


class TestDeleteAndInfo:
    async def test_delete_success(self):
        conn = _conn()

        with respx.mock:
            del_route = respx.delete(f"{GRAPH}/aud16").mock(
                return_value=httpx.Response(200, json={"success": True})
            )

            result = await conn.delete_audience("aud16")

        assert result.success is True
        assert result.operation == "delete"
        assert result.platform_response == {"success": True}
        assert "access_token=tok-secret" in str(del_route.calls[0].request.url)

    async def test_delete_platform_reports_failure_without_message(self):
        """Pins behavior: {"success": false} => success=False, error_message=None."""
        conn = _conn()

        with respx.mock:
            respx.delete(f"{GRAPH}/aud17").mock(
                return_value=httpx.Response(200, json={"success": False})
            )

            result = await conn.delete_audience("aud17")

        assert result.success is False
        assert result.error_message is None

    async def test_delete_network_error(self):
        conn = _conn()

        with respx.mock:
            respx.delete(f"{GRAPH}/aud18").mock(side_effect=httpx.ConnectError("gone"))

            result = await conn.delete_audience("aud18")

        assert result.success is False
        assert "gone" in result.error_message

    async def test_get_audience_info_success(self):
        conn = _conn()

        with respx.mock:
            info_route = respx.get(f"{GRAPH}/aud19").mock(
                return_value=httpx.Response(
                    200, json={"id": "aud19", "approximate_count": 42}
                )
            )

            info = await conn.get_audience_info("aud19")

        assert info["approximate_count"] == 42
        url = str(info_route.calls[0].request.url)
        assert "approximate_count" in url  # fields param requested

    async def test_get_audience_info_error_returns_error_dict(self):
        conn = _conn()

        with respx.mock:
            respx.get(f"{GRAPH}/aud20").mock(return_value=httpx.Response(500))

            info = await conn.get_audience_info("aud20")

        assert "error" in info


# =============================================================================
# create_audience
# =============================================================================


class TestCreateAudience:
    async def test_create_with_users_full_flow(self):
        conn = _conn(app_secret="shh")
        users = [_user("p1", email="new@x.com")]

        with respx.mock:
            create_route = respx.post(f"{GRAPH}/act_123/customaudiences").mock(
                return_value=httpx.Response(200, json={"id": "aud_new"})
            )
            respx.post(f"{GRAPH}/aud_new/users").mock(
                return_value=httpx.Response(200, json={"num_received": 1})
            )
            respx.get(f"{GRAPH}/aud_new").mock(
                return_value=httpx.Response(200, json={"approximate_count": 1})
            )

            config = AudienceConfig(name="VIPs", description="Top spenders")
            result = await conn.create_audience(config, users)

        assert result.success is True
        assert result.operation == "create"
        assert result.platform_audience_id == "aud_new"
        assert result.platform_audience_name == "VIPs"
        assert result.users_sent == 1

        body = parse_qs(create_route.calls[0].request.content.decode())
        assert body["name"] == ["VIPs"]
        assert body["subtype"] == ["CUSTOM"]
        assert body["description"] == ["Top spenders"]
        assert body["customer_file_source"] == ["USER_PROVIDED_ONLY"]

    async def test_create_without_users(self):
        conn = _conn()

        with respx.mock:
            respx.post(f"{GRAPH}/act_123/customaudiences").mock(
                return_value=httpx.Response(200, json={"id": "aud_empty"})
            )

            result = await conn.create_audience(AudienceConfig(name="Empty"), [])

        assert result.success is True
        assert result.users_sent == 0
        assert result.platform_audience_id == "aud_empty"

    async def test_create_no_id_returned(self):
        conn = _conn()

        with respx.mock:
            respx.post(f"{GRAPH}/act_123/customaudiences").mock(
                return_value=httpx.Response(200, json={"name": "no-id"})
            )

            result = await conn.create_audience(AudienceConfig(name="X"), [])

        assert result.success is False
        assert "No audience ID" in result.error_message

    async def test_create_http_error_with_body(self):
        conn = _conn()

        with respx.mock:
            respx.post(f"{GRAPH}/act_123/customaudiences").mock(
                return_value=httpx.Response(
                    400,
                    json={"error": {"message": "Invalid token", "code": 190}},
                )
            )

            result = await conn.create_audience(AudienceConfig(name="X"), [])

        assert result.success is False
        assert result.error_message == "Invalid token"
        assert result.error_code == "190"

    async def test_create_http_error_empty_body(self):
        conn = _conn()

        with respx.mock:
            respx.post(f"{GRAPH}/act_123/customaudiences").mock(
                return_value=httpx.Response(503)
            )

            result = await conn.create_audience(AudienceConfig(name="X"), [])

        assert result.success is False
        assert "503" in result.error_message

    async def test_create_network_error(self):
        conn = _conn()

        with respx.mock:
            respx.post(f"{GRAPH}/act_123/customaudiences").mock(
                side_effect=httpx.ConnectError("refused")
            )

            result = await conn.create_audience(AudienceConfig(name="X"), [])

        assert result.success is False
        assert "refused" in result.error_message
