"""
Deep integration tests for ``app/stratum/adapters/whatsapp_adapter.py`` [#342].

The adapter talks to Meta's WhatsApp Cloud API through ``httpx.AsyncClient``,
opened per request. ``patch_http`` below stubs that boundary inside the adapter
module namespace (respx would not intercept it) and yields the AsyncMock for
the verb, so call assertions read the same as before.

PRODUCTION BUGS FIXED under #540 (assertions below pin the corrected
behavior — do not revert):

1. CRITICAL — ``WhatsAppAdapter`` was abstract and uninstantiable.
   ``BaseAdapter`` declares abstract ``upload_image``/``upload_video`` which
   the subclass never implemented, so ``WhatsAppAdapter(creds)`` raised
   ``TypeError: Can't instantiate abstract class``.  Both methods are now
   implemented against the Cloud API ``/media`` upload endpoint, so the class
   constructs directly (``TestConstruction::test_can_instantiate_directly``).

2. HIGH — ``MessageType(media_type.upper())`` in ``send_media_message``
   raised ``ValueError`` for every media type because enum values are
   lowercase.  Now uses ``.lower()`` so the method returns the ``Message``.

3. HIGH — the same uppercase-lookup pattern in ``_parse_incoming_message``
   made ``process_webhook`` raise for every *valid* incoming message type.
   Now uses ``.lower()`` so text/media/interactive messages parse and the
   content-extraction branches are reachable.

4. LOW — ``initialize()`` now catches the ``PlatformError`` that
   ``_make_request`` raises and re-wraps it as the documented
   ``AuthenticationError`` (an explicit ``AuthenticationError`` re-raises).
"""

import hashlib
import hmac
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.stratum.adapters.base import (
    AdapterError,
    AuthenticationError,
    PlatformError,
)
from app.stratum.adapters.whatsapp_adapter import (
    Contact,
    Conversation,
    ConversationType,
    Message,
    MessageStatus,
    MessageType,
    Template,
    WhatsAppAdapter,
)
from app.stratum.models import Platform

# Without this marker the CI integration run (-m "integration") silently
# deselects this entire module.
pytestmark = pytest.mark.integration

MOD = "app.stratum.adapters.whatsapp_adapter"

BASE_CREDS = {
    "phone_number_id": "111222333",
    "access_token": "EAA-test-token",
    "business_account_id": "999888777",
    "app_secret": "top-secret",
    "verify_token": "verify-me",
}


def _resp(json_data, status_code=200):
    """Build a mock successful httpx.Response."""
    m = MagicMock()
    m.status_code = status_code
    m.json.return_value = json_data
    m.raise_for_status.return_value = None
    return m


def _err_resp(error_json=None):
    """Build a mock response whose raise_for_status raises HTTPError."""
    err_response = MagicMock()
    if error_json is None:
        err_response.json.side_effect = ValueError("no json body")
    else:
        err_response.json.return_value = error_json
    # httpx.HTTPStatusError needs a real Request/Response pair; the adapter only
    # reads .response, so attach it to a plain HTTPError instead.
    http_error = httpx.HTTPError("400 Client Error")
    http_error.response = err_response
    m = MagicMock()
    m.raise_for_status.side_effect = http_error
    return m


@contextmanager
def patch_http(verb, return_value=None, side_effect=None):
    """Stub ``async with httpx.AsyncClient(...) as c: await c.<verb>(...)``.

    Yields the AsyncMock standing in for the verb so existing call assertions
    keep working. __aexit__ is pinned to False — a truthy value would swallow
    the transport errors the failure-path tests rely on.
    """
    handler = AsyncMock(return_value=return_value, side_effect=side_effect)
    with patch(f"{MOD}.httpx.AsyncClient") as mock_cls:
        setattr(mock_cls.return_value.__aenter__.return_value, verb, handler)
        mock_cls.return_value.__aexit__.return_value = False
        yield handler


@pytest.fixture
def adapter():
    """An initialized adapter (initialize() itself is tested separately)."""
    a = WhatsAppAdapter(dict(BASE_CREDS))
    a._initialized = True
    return a


@pytest.fixture
def capi_adapter():
    """Adapter with a pixel_id so mark_conversion hits the CAPI path."""
    creds = dict(BASE_CREDS)
    creds["pixel_id"] = "px-123"
    a = WhatsAppAdapter(creds)
    a._initialized = True
    return a


# ============================================================================
# Construction / credentials
# ============================================================================


class TestConstruction:
    def test_can_instantiate_directly(self):
        """BUG #1 (critical) FIXED: the adapter is now concrete.

        ``BaseAdapter``'s abstract ``upload_image``/``upload_video`` are
        implemented, so the real class constructs directly with no
        subclass workaround.
        """
        a = WhatsAppAdapter(dict(BASE_CREDS))
        assert isinstance(a, WhatsAppAdapter)
        assert a.phone_number_id == BASE_CREDS["phone_number_id"]
        # The previously-missing abstract methods are now bound coroutines.
        assert callable(a.upload_image)
        assert callable(a.upload_video)

    @pytest.mark.parametrize(
        "missing", ["phone_number_id", "access_token", "business_account_id"]
    )
    def test_missing_required_credential_raises(self, missing):
        creds = dict(BASE_CREDS)
        del creds[missing]
        with pytest.raises(ValueError, match=missing):
            WhatsAppAdapter(creds)

    def test_optional_credentials_default_to_none(self):
        creds = {
            "phone_number_id": "1",
            "access_token": "t",
            "business_account_id": "2",
        }
        a = WhatsAppAdapter(creds)
        assert a.app_secret is None
        assert a.verify_token is None
        assert a._conversations == {}
        assert a._initialized is False

    def test_platform_is_meta(self, adapter):
        assert adapter.platform == Platform.META

    def test_ensure_initialized_guard(self):
        a = WhatsAppAdapter(dict(BASE_CREDS))
        with pytest.raises(AdapterError, match="not initialized"):
            a._ensure_initialized()


# ============================================================================
# Lifecycle
# ============================================================================


class TestLifecycle:
    async def test_initialize_success(self):
        a = WhatsAppAdapter(dict(BASE_CREDS))
        info = {
            "display_phone_number": "+1 555-0100",
            "verified_name": "Stratum Test",
            "quality_rating": "GREEN",
        }
        with patch_http("get", return_value=_resp(info)) as mock_get:
            await a.initialize()

        assert a._initialized is True
        url = mock_get.call_args.args[0]
        assert url == f"{WhatsAppAdapter.BASE_URL}/{BASE_CREDS['phone_number_id']}"
        kwargs = mock_get.call_args.kwargs
        assert (
            kwargs["headers"]["Authorization"] == f"Bearer {BASE_CREDS['access_token']}"
        )
        assert "display_phone_number" in kwargs["params"]["fields"]

    async def test_initialize_success_with_missing_fields(self):
        """Defaults to 'Unknown' when the API omits phone info fields."""
        a = WhatsAppAdapter(dict(BASE_CREDS))
        with patch_http("get", return_value=_resp({})):
            await a.initialize()
        assert a._initialized is True

    async def test_initialize_requests_error_wrapped_as_authentication_error(self):
        """BUG #4 (P2) FIXED: API failures surface as AuthenticationError.

        ``_make_request`` converts ``httpx.ConnectError`` into
        ``PlatformError``; ``initialize()`` now catches that and re-wraps it
        as the documented ``AuthenticationError``, keeping the original
        message.
        """
        a = WhatsAppAdapter(dict(BASE_CREDS))
        with patch_http(
            "get",
            side_effect=httpx.ConnectError("connection refused"),
        ):
            with pytest.raises(
                AuthenticationError, match="connection refused"
            ) as exc_info:
                await a.initialize()
        assert "Failed to initialize" in str(exc_info.value)
        assert a._initialized is False

    async def test_initialize_oserror_wrapped_as_authentication_error(self):
        """Non-requests transport errors do hit the AuthenticationError wrap."""
        a = WhatsAppAdapter(dict(BASE_CREDS))
        with patch_http("get", side_effect=TimeoutError("slow")):
            with pytest.raises(AuthenticationError, match="Failed to initialize"):
                await a.initialize()

    async def test_initialize_parse_error_wrapped_as_authentication_error(self):
        a = WhatsAppAdapter(dict(BASE_CREDS))
        with patch_http("get", side_effect=ValueError("bad payload")):
            with pytest.raises(AuthenticationError, match="Failed to parse"):
                await a.initialize()

    async def test_cleanup_resets_state(self, adapter):
        adapter._conversations["123"] = Conversation(conversation_id="c1", wa_id="123")
        await adapter.cleanup()
        assert adapter._initialized is False
        assert adapter._conversations == {}


# ============================================================================
# Sending: text
# ============================================================================


class TestSendTextMessage:
    async def test_requires_initialization(self):
        a = WhatsAppAdapter(dict(BASE_CREDS))
        with pytest.raises(AdapterError, match="not initialized"):
            await a.send_text_message("+15550001111", "hi")

    async def test_send_text_success(self, adapter):
        resp = _resp({"messages": [{"id": "wamid.abc"}]})
        with patch_http("post", return_value=resp) as mock_post:
            msg = await adapter.send_text_message(
                "+1 (555) 000-1111", "hello there", preview_url=True
            )

        payload = mock_post.call_args.kwargs["json"]
        assert payload["to"] == "15550001111"  # normalized, no punctuation
        assert payload["type"] == "text"
        assert payload["text"] == {"preview_url": True, "body": "hello there"}
        assert "context" not in payload

        assert msg.message_id == "wamid.abc"
        assert msg.message_type == MessageType.TEXT
        assert msg.status == MessageStatus.SENT
        assert msg.is_outbound is True
        assert msg.text == "hello there"
        # Message was tracked into a conversation keyed by the raw wa_id
        conv = adapter.get_conversation("+1 (555) 000-1111")
        assert conv is not None
        assert conv.messages[-1] is msg

    async def test_send_text_reply_to_sets_context(self, adapter):
        resp = _resp({"messages": [{"id": "wamid.reply"}]})
        with patch_http("post", return_value=resp) as mock_post:
            msg = await adapter.send_text_message(
                "15550001111", "replying", reply_to="wamid.orig"
            )
        payload = mock_post.call_args.kwargs["json"]
        assert payload["context"] == {"message_id": "wamid.orig"}
        assert msg.context_message_id == "wamid.orig"

    async def test_send_text_empty_messages_response(self, adapter):
        """A malformed success response yields an empty message_id."""
        with patch_http("post", return_value=_resp({})):
            msg = await adapter.send_text_message("15550001111", "x")
        assert msg.message_id == ""


# ============================================================================
# Sending: template
# ============================================================================


class TestSendTemplateMessage:
    async def test_send_template_with_components(self, adapter):
        resp = _resp({"messages": [{"id": "wamid.tpl"}]})
        components = [
            {
                "type": "body",
                "parameters": [{"type": "text", "text": "John"}],
            }
        ]
        with patch_http("post", return_value=resp) as mock_post:
            msg = await adapter.send_template_message(
                "+15550001111",
                "order_confirmation",
                language="ar",
                components=components,
            )

        payload = mock_post.call_args.kwargs["json"]
        assert payload["type"] == "template"
        assert payload["template"]["name"] == "order_confirmation"
        assert payload["template"]["language"] == {"code": "ar"}
        assert payload["template"]["components"] == components

        assert msg.message_type == MessageType.TEMPLATE
        assert msg.template_name == "order_confirmation"
        assert msg.template_params == {"components": components}
        assert msg.status == MessageStatus.SENT

    async def test_send_template_without_components(self, adapter):
        resp = _resp({"messages": [{"id": "wamid.tpl2"}]})
        with patch_http("post", return_value=resp) as mock_post:
            msg = await adapter.send_template_message("15550001111", "hello_world")
        payload = mock_post.call_args.kwargs["json"]
        assert "components" not in payload["template"]
        assert payload["template"]["language"] == {"code": "en"}
        assert msg.message_id == "wamid.tpl2"

    async def test_send_template_requires_initialization(self):
        a = WhatsAppAdapter(dict(BASE_CREDS))
        with pytest.raises(AdapterError, match="not initialized"):
            await a.send_template_message("15550001111", "hello_world")


# ============================================================================
# Sending: interactive
# ============================================================================


class TestSendInteractiveMessage:
    async def test_send_interactive_full(self, adapter):
        resp = _resp({"messages": [{"id": "wamid.int"}]})
        action = {"buttons": [{"type": "reply", "reply": {"id": "b1", "title": "Yes"}}]}
        with patch_http("post", return_value=resp) as mock_post:
            msg = await adapter.send_interactive_message(
                "15550001111",
                interactive_type="button",
                body_text="Confirm?",
                action=action,
                header={"type": "text", "text": "Order"},
                footer="Stratum",
            )
        payload = mock_post.call_args.kwargs["json"]
        interactive = payload["interactive"]
        assert interactive["type"] == "button"
        assert interactive["body"] == {"text": "Confirm?"}
        assert interactive["action"] == action
        assert interactive["header"] == {"type": "text", "text": "Order"}
        assert interactive["footer"] == {"text": "Stratum"}

        assert msg.message_type == MessageType.INTERACTIVE
        assert msg.interactive_data == interactive
        assert adapter.get_conversation("15550001111") is not None

    async def test_send_interactive_minimal(self, adapter):
        resp = _resp({"messages": [{"id": "wamid.int2"}]})
        with patch_http("post", return_value=resp) as mock_post:
            await adapter.send_interactive_message(
                "15550001111",
                interactive_type="list",
                body_text="Pick one",
                action={"sections": []},
            )
        interactive = mock_post.call_args.kwargs["json"]["interactive"]
        assert "header" not in interactive
        assert "footer" not in interactive


# ============================================================================
# Sending: media
# ============================================================================


class TestSendMediaMessage:
    async def test_requires_media_id_or_url(self, adapter):
        with pytest.raises(ValueError, match="media_id or media_url"):
            await adapter.send_media_message("15550001111", "image")

    async def test_send_media_returns_message(self, adapter):
        """BUG #2 (high) FIXED: send_media_message returns the Message.

        ``MessageType(media_type.lower())`` now matches the lowercase enum
        values, so after the API POST the method returns a populated
        ``Message`` instead of raising ``ValueError``.
        """
        resp = _resp({"messages": [{"id": "wamid.media"}]})
        with patch_http("post", return_value=resp) as mock_post:
            msg = await adapter.send_media_message(
                "15550001111", "image", media_id="MEDIA-1", caption="pic"
            )
        payload = mock_post.call_args.kwargs["json"]
        assert payload["type"] == "image"
        assert payload["image"] == {"id": "MEDIA-1", "caption": "pic"}

        assert msg.message_id == "wamid.media"
        assert msg.message_type == MessageType.IMAGE
        assert msg.media_id == "MEDIA-1"
        assert msg.text == "pic"
        assert msg.status == MessageStatus.SENT
        assert msg.is_outbound is True

    async def test_send_media_by_url_document_filename(self, adapter):
        """Document payload uses link + filename; caption ignored for docs."""
        resp = _resp({"messages": [{"id": "wamid.doc"}]})
        with patch_http("post", return_value=resp) as mock_post:
            msg = await adapter.send_media_message(
                "15550001111",
                "document",
                media_url="https://cdn.example.com/inv.pdf",
                caption="ignored",
                filename="invoice.pdf",
            )
        payload = mock_post.call_args.kwargs["json"]
        assert payload["document"] == {
            "link": "https://cdn.example.com/inv.pdf",
            "filename": "invoice.pdf",
        }
        assert msg.message_type == MessageType.DOCUMENT
        assert msg.media_url == "https://cdn.example.com/inv.pdf"


# ============================================================================
# Media upload
# ============================================================================


class TestUploadMedia:
    async def test_upload_media_success(self, adapter, tmp_path):
        f = tmp_path / "photo.jpg"
        f.write_bytes(b"\xff\xd8fakejpeg")
        with patch_http("post", return_value=_resp({"id": "MEDIA-42"})
        ) as mock_post:
            media_id = await adapter.upload_media(str(f), "image")

        assert media_id == "MEDIA-42"
        args, kwargs = mock_post.call_args
        assert args[0].endswith(f"/{BASE_CREDS['phone_number_id']}/media")
        assert kwargs["data"] == {"messaging_product": "whatsapp", "type": "image/jpeg"}
        assert (
            kwargs["headers"]["Authorization"] == f"Bearer {BASE_CREDS['access_token']}"
        )
        assert kwargs["files"]["file"][2] == "image/jpeg"

    async def test_upload_media_unknown_type_falls_back(self, adapter, tmp_path):
        f = tmp_path / "blob.bin"
        f.write_bytes(b"data")
        with patch_http("post", return_value=_resp({"id": "MEDIA-43"})
        ) as mock_post:
            media_id = await adapter.upload_media(str(f), "weird")
        assert media_id == "MEDIA-43"
        kwargs = mock_post.call_args.kwargs
        assert kwargs["files"]["file"][2] == "application/octet-stream"
        assert kwargs["data"]["type"] is None  # unknown type -> None mime

    async def test_upload_media_requires_initialization(self, tmp_path):
        a = WhatsAppAdapter(dict(BASE_CREDS))
        with pytest.raises(AdapterError, match="not initialized"):
            await a.upload_media(str(tmp_path / "x.jpg"), "image")


# ============================================================================
# Creative uploads (BaseAdapter.upload_image / upload_video) — BUG #1 fix
# ============================================================================


class TestUploadCreative:
    async def test_upload_image_posts_bytes_and_returns_id(self, adapter):
        """BUG #1 FIXED: upload_image hits the Cloud API /media endpoint."""
        with patch_http("post", return_value=_resp({"id": "IMG-1"})
        ) as mock_post:
            media_id = await adapter.upload_image("acct", b"\xff\xd8jpeg", "logo.png")

        assert media_id == "IMG-1"
        args, kwargs = mock_post.call_args
        assert args[0].endswith(f"/{BASE_CREDS['phone_number_id']}/media")
        assert kwargs["data"]["messaging_product"] == "whatsapp"
        # MIME inferred from filename
        assert kwargs["data"]["type"] == "image/png"
        assert kwargs["files"]["file"] == ("logo.png", b"\xff\xd8jpeg", "image/png")
        assert (
            kwargs["headers"]["Authorization"] == f"Bearer {BASE_CREDS['access_token']}"
        )

    async def test_upload_image_unknown_extension_uses_default_mime(self, adapter):
        """Unguessable extension falls back to the image/jpeg default."""
        with patch_http("post", return_value=_resp({"id": "IMG-2"})
        ) as mock_post:
            media_id = await adapter.upload_image("acct", b"data", "blob")
        assert media_id == "IMG-2"
        assert mock_post.call_args.kwargs["data"]["type"] == "image/jpeg"

    async def test_upload_video_posts_bytes_and_returns_id(self, adapter):
        with patch_http("post", return_value=_resp({"id": "VID-1"})
        ) as mock_post:
            media_id = await adapter.upload_video("acct", b"movie", "promo.mp4")
        assert media_id == "VID-1"
        assert mock_post.call_args.kwargs["data"]["type"] == "video/mp4"
        assert mock_post.call_args.kwargs["files"]["file"][2] == "video/mp4"

    async def test_upload_video_missing_id_returns_empty(self, adapter):
        """A malformed success response yields an empty media id."""
        with patch_http("post", return_value=_resp({})):
            assert await adapter.upload_video("acct", b"x", "clip.mp4") == ""

    async def test_upload_image_requires_initialization(self):
        a = WhatsAppAdapter(dict(BASE_CREDS))
        with pytest.raises(AdapterError, match="not initialized"):
            await a.upload_image("acct", b"x", "logo.png")

    async def test_upload_video_requires_initialization(self):
        a = WhatsAppAdapter(dict(BASE_CREDS))
        with pytest.raises(AdapterError, match="not initialized"):
            await a.upload_video("acct", b"x", "clip.mp4")


# ============================================================================
# Templates
# ============================================================================


class TestTemplates:
    async def test_get_templates_full_parse(self, adapter):
        data = {
            "data": [
                {
                    "name": "order_update",
                    "language": "en_US",
                    "category": "UTILITY",
                    "status": "APPROVED",
                    "id": "tpl-1",
                    "quality_score": {"score": "GREEN"},
                    "components": [
                        {"type": "HEADER", "format": "TEXT", "text": "Hi"},
                        {"type": "BODY", "text": "Your order {{1}} shipped"},
                        {"type": "FOOTER", "text": "Stratum"},
                        {
                            "type": "BUTTONS",
                            "buttons": [{"type": "QUICK_REPLY", "text": "Track"}],
                        },
                    ],
                },
                {"name": "bare"},
            ]
        }
        with patch_http("get", return_value=_resp(data)) as mock_get:
            templates = await adapter.get_templates()

        url = mock_get.call_args.args[0]
        assert url.endswith(f"/{BASE_CREDS['business_account_id']}/message_templates")
        assert mock_get.call_args.kwargs["params"] == {"limit": 100}

        assert len(templates) == 2
        t = templates[0]
        assert isinstance(t, Template)
        assert t.name == "order_update"
        assert t.language == "en_US"
        assert t.category == "UTILITY"
        assert t.status == "APPROVED"
        assert t.id == "tpl-1"
        assert t.header == {"type": "HEADER", "format": "TEXT", "text": "Hi"}
        assert t.body == "Your order {{1}} shipped"
        assert t.footer == "Stratum"
        assert t.buttons == [{"type": "QUICK_REPLY", "text": "Track"}]
        assert t.quality_score == "GREEN"

        bare = templates[1]
        assert bare.name == "bare"
        assert bare.language == "en"
        assert bare.body == ""
        assert bare.footer is None
        assert bare.buttons == []
        assert bare.quality_score is None

    async def test_get_templates_empty(self, adapter):
        with patch_http("get", return_value=_resp({})):
            assert await adapter.get_templates() == []

    async def test_create_template(self, adapter):
        components = [{"type": "BODY", "text": "Hello {{1}}"}]
        with patch_http(
            "post",
            return_value=_resp({"id": "tpl-new", "status": "PENDING"}),
        ) as mock_post:
            result = await adapter.create_template(
                "welcome_msg", "MARKETING", "en", components
            )
        assert result == {"id": "tpl-new", "status": "PENDING"}
        payload = mock_post.call_args.kwargs["json"]
        assert payload == {
            "name": "welcome_msg",
            "category": "MARKETING",
            "language": "en",
            "components": components,
        }


# ============================================================================
# Webhook verification
# ============================================================================


class TestWebhookVerification:
    def test_verify_webhook_success(self, adapter):
        assert adapter.verify_webhook("subscribe", "verify-me", "chal-1") == "chal-1"

    def test_verify_webhook_wrong_token(self, adapter):
        assert adapter.verify_webhook("subscribe", "nope", "chal-1") is None

    def test_verify_webhook_wrong_mode(self, adapter):
        assert adapter.verify_webhook("unsubscribe", "verify-me", "chal-1") is None

    def test_verify_signature_valid(self, adapter):
        payload = b'{"entry": []}'
        digest = hmac.new(b"top-secret", payload, hashlib.sha256).hexdigest()
        assert adapter.verify_signature(payload, f"sha256={digest}") is True

    def test_verify_signature_invalid(self, adapter):
        assert adapter.verify_signature(b"payload", "sha256=deadbeef") is False

    def test_verify_signature_no_app_secret_skips(self):
        creds = {
            "phone_number_id": "1",
            "access_token": "t",
            "business_account_id": "2",
        }
        a = WhatsAppAdapter(creds)
        assert a.verify_signature(b"anything", "sha256=whatever") is True


# ============================================================================
# Webhook processing
# ============================================================================


def _webhook(value):
    return {"entry": [{"changes": [{"value": value}]}]}


class TestProcessWebhook:
    async def test_incoming_text_message_parses_and_dispatches(self, adapter):
        """BUG #3 (high) FIXED: valid incoming types now parse.

        ``MessageType(msg_type.lower())`` matches the lowercase enum values,
        so a "text" webhook parses into a ``MessageType.TEXT`` message and the
        text content-extraction branch runs.
        Location: whatsapp_adapter.py:806 / 816-817.
        """
        received = []

        async def handler(message):
            received.append(message)

        adapter.on_message(handler)

        payload = _webhook(
            {
                "messages": [
                    {
                        "id": "wamid.in1",
                        "from": "15550002222",
                        "type": "text",
                        "timestamp": "1720000000",
                        "text": {"body": "hi there"},
                    }
                ]
            }
        )
        await adapter.process_webhook(payload)

        assert len(received) == 1
        msg = received[0]
        assert msg.message_type == MessageType.TEXT
        assert msg.text == "hi there"
        assert msg.is_outbound is False
        assert msg.status == MessageStatus.DELIVERED
        assert adapter.get_conversation("15550002222") is not None

    @pytest.mark.parametrize("media_type", ["image", "video", "audio", "document"])
    async def test_incoming_media_message_extracts_media(self, adapter, media_type):
        """BUG #3 FIXED: media webhooks reach the media-extraction branch.

        The media id and caption are pulled off the type-keyed sub-object
        (whatsapp_adapter.py:818-821).
        """
        payload = _webhook(
            {
                "messages": [
                    {
                        "id": "wamid.med",
                        "from": "15550002222",
                        "type": media_type,
                        "timestamp": "1720000000",
                        media_type: {"id": "MED-9", "caption": "look"},
                    }
                ]
            }
        )
        await adapter.process_webhook(payload)
        msg = adapter.get_conversation("15550002222").messages[-1]
        assert msg.message_type == MessageType(media_type)
        assert msg.media_id == "MED-9"
        assert msg.text == "look"

    @pytest.mark.parametrize(
        ("int_type", "reply_key"),
        [("button_reply", "button_reply"), ("list_reply", "list_reply")],
    )
    async def test_incoming_interactive_message_extracts_reply(
        self, adapter, int_type, reply_key
    ):
        """BUG #3 FIXED: interactive webhooks reach the reply-extraction branch.

        (whatsapp_adapter.py:822-828).
        """
        reply = {"id": "opt-1", "title": "Yes"}
        payload = _webhook(
            {
                "messages": [
                    {
                        "id": "wamid.int",
                        "from": "15550002222",
                        "type": "interactive",
                        "timestamp": "1720000000",
                        "interactive": {"type": int_type, reply_key: reply},
                    }
                ]
            }
        )
        await adapter.process_webhook(payload)
        msg = adapter.get_conversation("15550002222").messages[-1]
        assert msg.message_type == MessageType.INTERACTIVE
        assert msg.interactive_data == reply

    async def test_unknown_type_falls_back_to_text_and_dispatches(self, adapter):
        """Unknown types survive parsing via the MessageType.TEXT fallback."""
        received = []

        async def handler(message):
            received.append(message)

        async def bad_handler(message):
            raise RuntimeError("handler exploded")

        adapter.on_message(bad_handler)  # errors must be swallowed + logged
        adapter.on_message(handler)

        payload = _webhook(
            {
                "messages": [
                    {
                        "id": "wamid.in2",
                        "from": "15550002222",
                        "type": "order",  # not a MessageType value
                        "timestamp": "1720000000",
                        "context": {"id": "wamid.parent"},
                    }
                ],
                "contacts": [{"wa_id": "15550002222", "profile": {"name": "Jane"}}],
            }
        )
        await adapter.process_webhook(payload)

        assert len(received) == 1
        msg = received[0]
        assert msg.message_type == MessageType.TEXT  # fallback
        assert msg.is_outbound is False
        assert msg.status == MessageStatus.DELIVERED
        assert msg.context_message_id == "wamid.parent"
        assert msg.wa_id == "15550002222"
        assert msg.timestamp == datetime.fromtimestamp(1720000000, tz=timezone.utc)
        # Inbound message tracked and conversation window refreshed
        conv = adapter.get_conversation("15550002222")
        assert conv is not None
        assert conv.expires_at == msg.timestamp + timedelta(hours=24)

    async def test_unknown_type_without_context_or_contacts(self, adapter):
        """No context / contacts keys: parser keeps sender wa_id untouched."""
        payload = _webhook(
            {
                "messages": [
                    {
                        "id": "wamid.in3",
                        "from": "15550008888",
                        "type": "order",
                        "timestamp": "1720000001",
                    }
                ]
            }
        )
        await adapter.process_webhook(payload)
        conv = adapter.get_conversation("15550008888")
        assert conv is not None
        msg = conv.messages[0]
        assert msg.context_message_id is None
        assert msg.wa_id == "15550008888"

    async def test_status_update_delivered_and_read(self, adapter):
        updates = []

        async def status_handler(message_id, status):
            updates.append((message_id, status))

        async def bad_status_handler(message_id, status):
            raise KeyError("boom")

        adapter.on_status_update(bad_status_handler)
        adapter.on_status_update(status_handler)

        tracked = Message(
            message_id="wamid.out1",
            wa_id="15550003333",
            message_type=MessageType.TEXT,
            timestamp=datetime.now(timezone.utc),
            status=MessageStatus.SENT,
        )
        adapter._track_message(tracked)

        await adapter.process_webhook(
            _webhook({"statuses": [{"id": "wamid.out1", "status": "read"}]})
        )
        assert tracked.status == MessageStatus.READ
        assert updates == [("wamid.out1", MessageStatus.READ)]

    async def test_status_update_failed_captures_error(self, adapter):
        tracked = Message(
            message_id="wamid.out2",
            wa_id="15550003333",
            message_type=MessageType.TEXT,
            timestamp=datetime.now(timezone.utc),
        )
        adapter._track_message(tracked)

        await adapter.process_webhook(
            _webhook(
                {
                    "statuses": [
                        {
                            "id": "wamid.out2",
                            "status": "failed",
                            "errors": [
                                {"code": 131047, "message": "Re-engagement required"}
                            ],
                        }
                    ]
                }
            )
        )
        assert tracked.status == MessageStatus.FAILED
        assert tracked.error_code == 131047
        assert tracked.error_message == "Re-engagement required"

    async def test_status_update_unknown_status_maps_to_pending(self, adapter):
        tracked = Message(
            message_id="wamid.out3",
            wa_id="15550003333",
            message_type=MessageType.TEXT,
            timestamp=datetime.now(timezone.utc),
            status=MessageStatus.SENT,
        )
        adapter._track_message(tracked)
        await adapter.process_webhook(
            _webhook({"statuses": [{"id": "wamid.out3", "status": "warped"}]})
        )
        assert tracked.status == MessageStatus.PENDING

    async def test_status_update_failed_with_empty_errors_list(self, adapter):
        tracked = Message(
            message_id="wamid.out4",
            wa_id="15550003333",
            message_type=MessageType.TEXT,
            timestamp=datetime.now(timezone.utc),
        )
        adapter._track_message(tracked)
        await adapter.process_webhook(
            _webhook(
                {"statuses": [{"id": "wamid.out4", "status": "failed", "errors": []}]}
            )
        )
        assert tracked.status == MessageStatus.FAILED
        assert tracked.error_code is None
        assert tracked.error_message is None

    async def test_status_update_unknown_message_is_noop(self, adapter):
        await adapter.process_webhook(
            _webhook({"statuses": [{"id": "wamid.ghost", "status": "read"}]})
        )
        assert adapter._conversations == {}

    async def test_status_update_no_match_in_nonempty_conversations(self, adapter):
        tracked = Message(
            message_id="wamid.other",
            wa_id="15550003333",
            message_type=MessageType.TEXT,
            timestamp=datetime.now(timezone.utc),
            status=MessageStatus.SENT,
        )
        adapter._track_message(tracked)
        await adapter.process_webhook(
            _webhook({"statuses": [{"id": "wamid.ghost", "status": "read"}]})
        )
        assert tracked.status == MessageStatus.SENT  # untouched

    async def test_empty_payload_is_noop(self, adapter):
        await adapter.process_webhook({})
        await adapter.process_webhook({"entry": [{"changes": []}]})
        assert adapter._conversations == {}


# ============================================================================
# Conversation tracking
# ============================================================================


class TestConversationTracking:
    def test_track_message_creates_conversation(self, adapter):
        ts = datetime.now(timezone.utc)
        msg = Message(
            message_id="m1",
            wa_id="15550004444",
            message_type=MessageType.TEXT,
            timestamp=ts,
        )
        adapter._track_message(msg)
        conv = adapter.get_conversation("15550004444")
        assert conv is not None
        assert conv.started_at == ts
        assert conv.expires_at == ts + timedelta(hours=24)
        assert conv.messages == [msg]
        assert conv.conversation_type == ConversationType.SERVICE

    def test_outbound_message_does_not_refresh_window(self, adapter):
        ts = datetime.now(timezone.utc)
        first = Message(
            message_id="m1",
            wa_id="w1",
            message_type=MessageType.TEXT,
            timestamp=ts,
        )
        adapter._track_message(first)
        later = Message(
            message_id="m2",
            wa_id="w1",
            message_type=MessageType.TEXT,
            timestamp=ts + timedelta(hours=5),
            is_outbound=True,
        )
        adapter._track_message(later)
        conv = adapter.get_conversation("w1")
        assert len(conv.messages) == 2
        assert conv.expires_at == ts + timedelta(hours=24)  # unchanged

    def test_inbound_message_refreshes_window(self, adapter):
        ts = datetime.now(timezone.utc)
        adapter._track_message(
            Message(
                message_id="m1",
                wa_id="w2",
                message_type=MessageType.TEXT,
                timestamp=ts,
            )
        )
        inbound_ts = ts + timedelta(hours=3)
        adapter._track_message(
            Message(
                message_id="m2",
                wa_id="w2",
                message_type=MessageType.TEXT,
                timestamp=inbound_ts,
                is_outbound=False,
            )
        )
        assert adapter.get_conversation("w2").expires_at == inbound_ts + timedelta(
            hours=24
        )

    def test_get_conversation_missing_returns_none(self, adapter):
        assert adapter.get_conversation("nobody") is None


# ============================================================================
# Conversion tracking (CAPI)
# ============================================================================


class TestMarkConversion:
    async def test_no_pixel_id_tracks_locally_only(self, adapter):
        adapter._conversations["w9"] = Conversation(conversation_id="c9", wa_id="w9")
        result = await adapter.mark_conversion("w9", 149.99, currency="EUR")
        assert result == {"tracked_locally": True, "sent_to_capi": False}
        conv = adapter._conversations["w9"]
        assert conv.is_converted is True
        assert conv.conversion_value == 149.99
        assert conv.conversion_time is not None

    async def test_capi_success(self, capi_adapter):
        with patch_http("post", return_value=_resp({"events_received": 1})
        ) as mock_post:
            result = await capi_adapter.mark_conversion("15550005555", 42.0)

        assert result == {
            "tracked_locally": True,
            "sent_to_capi": True,
            "events_received": 1,
        }
        args, kwargs = mock_post.call_args
        assert args[0].endswith("/px-123/events")
        assert kwargs["params"] == {"access_token": BASE_CREDS["access_token"]}
        event = kwargs["json"]["data"][0]
        assert event["event_name"] == "Purchase"
        assert event["action_source"] == "chat"
        assert event["messaging_channel"] == "whatsapp"
        assert event["custom_data"] == {"value": 42.0, "currency": "USD"}
        expected_ph = hashlib.sha256(b"15550005555").hexdigest()
        assert event["user_data"]["ph"] == expected_ph
        assert "fbc" not in event["user_data"]

    async def test_capi_includes_click_attribution(self, capi_adapter):
        capi_adapter._conversations["15550006666"] = Conversation(
            conversation_id="c1", wa_id="15550006666", ad_id="ad-777"
        )
        with patch_http("post", return_value=_resp({"events_received": 1})
        ) as mock_post:
            await capi_adapter.mark_conversion("15550006666", 10.0)
        event = mock_post.call_args.kwargs["json"]["data"][0]
        assert event["user_data"]["fbc"] == "fb.1.ad-777"

    async def test_capi_failure_returns_error(self, capi_adapter):
        with patch_http(
            "post",
            side_effect=httpx.ConnectError("capi down"),
        ):
            result = await capi_adapter.mark_conversion("15550007777", 5.0)
        assert result["tracked_locally"] is True
        assert result["sent_to_capi"] is False
        assert "capi down" in result["error"]


# ============================================================================
# Analytics
# ============================================================================


class TestAnalytics:
    async def test_get_analytics(self, adapter):
        start = datetime(2026, 6, 1, tzinfo=timezone.utc)
        end = datetime(2026, 6, 30, tzinfo=timezone.utc)
        with patch_http("get", return_value=_resp({"analytics": {"sent": 5}})
        ) as mock_get:
            result = await adapter.get_analytics(start, end, granularity="MONTH")
        assert result == {"analytics": {"sent": 5}}
        url = mock_get.call_args.args[0]
        assert url.endswith(f"/{BASE_CREDS['business_account_id']}/analytics")
        params = mock_get.call_args.kwargs["params"]
        assert params["start"] == int(start.timestamp())
        assert params["end"] == int(end.timestamp())
        assert params["granularity"] == "MONTH"
        assert "SENT" in params["metric_types"]

    async def test_get_conversation_analytics(self, adapter):
        start = datetime(2026, 6, 1, tzinfo=timezone.utc)
        end = datetime(2026, 6, 2, tzinfo=timezone.utc)
        with patch_http("get", return_value=_resp({"conversation_analytics": {}})
        ) as mock_get:
            result = await adapter.get_conversation_analytics(start, end)
        assert result == {"conversation_analytics": {}}
        url = mock_get.call_args.args[0]
        assert url.endswith("/conversation_analytics")
        params = mock_get.call_args.kwargs["params"]
        assert params["dimension"] == "CONVERSATION_CATEGORY"
        assert params["granularity"] == "DAILY"


# ============================================================================
# Helpers: phone normalization + HTTP plumbing
# ============================================================================


class TestHelpers:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("+15550001111", "15550001111"),
            ("+1 (555) 000-1111", "15550001111"),
            ("001-555.000.1111", "0015550001111"),
            ("15550001111", "15550001111"),
        ],
    )
    def test_normalize_phone(self, adapter, raw, expected):
        assert adapter._normalize_phone(raw) == expected

    def test_make_request_delete(self, adapter):
        with patch_http("delete", return_value=_resp({"success": True})
        ) as mock_delete:
            result = adapter._make_request("DELETE", "/thing/1")
        assert result == {"success": True}
        assert mock_delete.call_args.args[0].endswith("/thing/1")

    def test_make_request_other_method(self, adapter):
        with patch_http("request", return_value=_resp({"patched": True})
        ) as mock_req:
            result = adapter._make_request("PATCH", "/thing/2", data={"a": 1})
        assert result == {"patched": True}
        assert mock_req.call_args.args[:2] == ("PATCH",) + (
            f"{WhatsAppAdapter.BASE_URL}/thing/2",
        )
        assert mock_req.call_args.kwargs["json"] == {"a": 1}

    def test_make_request_http_error_extracts_api_message(self, adapter):
        err = _err_resp({"error": {"message": "Invalid OAuth access token"}})
        with patch_http("get", return_value=err):
            with pytest.raises(PlatformError, match="Invalid OAuth access token"):
                adapter._make_request("GET", "/me")

    def test_make_request_http_error_non_json_body(self, adapter):
        with patch_http("get", return_value=_err_resp(None)):
            with pytest.raises(PlatformError, match="400 Client Error"):
                adapter._make_request("GET", "/me")

    def test_make_request_connection_error_no_response(self, adapter):
        with patch_http(
            "post",
            side_effect=httpx.ConnectError("dns failure"),
        ):
            with pytest.raises(PlatformError, match="dns failure"):
                adapter._make_request("POST", "/messages", data={})


# ============================================================================
# BaseAdapter interface stubs
# ============================================================================


class TestBaseInterface:
    async def test_ad_entity_reads_return_empty(self, adapter):
        assert await adapter.get_accounts() == []
        assert await adapter.get_campaigns("acct") == []
        assert await adapter.get_adsets("acct", campaign_id="c1") == []
        assert await adapter.get_ads("acct", adset_id="as1") == []

    async def test_get_metrics_delegates_to_analytics(self, adapter):
        start = datetime(2026, 6, 1, tzinfo=timezone.utc)
        end = datetime(2026, 6, 7, tzinfo=timezone.utc)
        with patch_http("get", return_value=_resp({"metrics": True})
        ) as mock_get:
            result = await adapter.get_metrics("acct", "campaign", ["c1"], start, end)
        assert result == {"metrics": True}
        assert mock_get.call_args.args[0].endswith("/analytics")

    async def test_get_emq_scores_maps_template_quality(self, adapter):
        data = {
            "data": [
                {
                    "name": "tpl_a",
                    "quality_score": {"score": "GREEN"},
                    "components": [],
                },
                {"name": "tpl_b", "components": []},
            ]
        }
        with patch_http("get", return_value=_resp(data)):
            scores = await adapter.get_emq_scores("acct")
        assert scores == [
            {"template": "tpl_a", "quality": "GREEN"},
            {"template": "tpl_b", "quality": None},
        ]

    async def test_execute_action_not_supported(self, adapter):
        with pytest.raises(NotImplementedError, match="ad automation"):
            await adapter.execute_action(action=None)


# ============================================================================
# Dataclass surface (documents intended shapes)
# ============================================================================


class TestDataclasses:
    def test_contact_defaults(self):
        c = Contact(wa_id="15550001111")
        assert c.profile_name is None
        assert c.tags == []

    def test_conversation_defaults(self):
        conv = Conversation(conversation_id="c1", wa_id="w1")
        assert conv.conversation_type == ConversationType.SERVICE
        assert conv.is_converted is False
        assert conv.messages == []
        assert conv.started_at.tzinfo is not None
