# =============================================================================
# Stratum AI - Report Delivery Service Deep Integration Tests (#342 Batch 4)
# =============================================================================
"""DB-backed integration tests for ``app.services.reporting.delivery``.

Covers the async orchestration paths that the unit rendering tests
(``tests/unit/test_report_delivery_render.py``) leave out:

- Every channel handler's ``deliver()`` (email/SMTP, Slack, Teams, generic
  webhook, S3, WhatsApp) with the transport mocked at the client boundary
  (aiosmtplib.SMTP / aiohttp.ClientSession / aioboto3.Session).
- ``DeliveryService.deliver_report`` end-to-end against real Postgres rows:
  ReportDelivery persistence, per-recipient success/failure accounting,
  unknown-channel skipping.
- ``DeliveryService.retry_delivery`` including the schedule-config lookup
  branch, and ``get_delivery_status``.

respx cannot intercept aiohttp, so all HTTP is faked with hand-rolled
async-context-manager doubles (see FakeSession / FakeResponse).
"""

import sys
import tempfile
import types
import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch

import aiohttp
import aiosmtplib
import pytest

import app.services.reporting.delivery as delivery_mod
from app.models.reporting import (
    DeliveryChannel,
    DeliveryStatus,
    ExecutionStatus,
    ReportDelivery,
    ReportExecution,
    ReportFormat,
    ReportTemplate,
    ReportType,
    ScheduledReport,
    ScheduleFrequency,
)
from app.services.reporting.delivery import (
    DeliveryService,
    EmailDelivery,
    S3Delivery,
    SlackDelivery,
    TeamsDelivery,
    WebhookDelivery,
    WhatsAppDelivery,
)

pytestmark = pytest.mark.integration


# =============================================================================
# Transport doubles
# =============================================================================


class FakeResponse:
    """Async-CM double for an aiohttp response."""

    def __init__(self, status=200, text_body="ok", json_body=None):
        self.status = status
        self._text = text_body
        self._json = json_body

    async def text(self):
        return self._text

    async def json(self):
        return self._json

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class FakeSession:
    """Async-CM double for aiohttp.ClientSession recording post() calls."""

    def __init__(self, response=None, exc=None):
        self.response = response or FakeResponse()
        self.exc = exc
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def post(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        if self.exc:
            raise self.exc
        return self.response


class FakeSMTP:
    """Async-CM double for aiosmtplib.SMTP."""

    last_instance = None

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.logged_in = None
        self.sent = []
        self.send_exc = None
        FakeSMTP.last_instance = self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def login(self, user, password):
        self.logged_in = (user, password)

    async def send_message(self, msg):
        if self.send_exc:
            raise self.send_exc
        self.sent.append(msg)
        return ({}, "OK")


class FailingSMTP(FakeSMTP):
    async def send_message(self, msg):
        raise aiosmtplib.SMTPException("smtp boom")


def _patch_session(fake_session):
    """Patch aiohttp.ClientSession as seen by the delivery module."""
    return patch.object(
        delivery_mod.aiohttp, "ClientSession", lambda *a, **k: fake_session
    )


# =============================================================================
# Execution builders
# =============================================================================


def _execution(**overrides) -> ReportExecution:
    """Build an unsaved ReportExecution suitable for handler-level tests."""
    base = dict(
        id=uuid.uuid4(),
        tenant_id=1,
        execution_type="manual",
        status=ExecutionStatus.COMPLETED,
        report_type=ReportType.CAMPAIGN_PERFORMANCE,
        format=ReportFormat.PDF,
        date_range_start=date(2026, 6, 1),
        date_range_end=date(2026, 6, 30),
        completed_at=datetime(2026, 6, 30, 12, 0, tzinfo=timezone.utc),
        file_url="https://reports.example.com/r.pdf",
        metrics_summary={
            "total_spend": 1234.5,
            "total_revenue": 6789.0,
            "overall_roas": 5.5,
        },
    )
    base.update(overrides)
    return ReportExecution(**base)


def _tmp_report_file(suffix=".pdf") -> str:
    f = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    f.write(b"%PDF-1.4 fake report body")
    f.close()
    return f.name


async def _seed_execution(db_session, tenant_id, **overrides) -> ReportExecution:
    execution = _execution(tenant_id=tenant_id, **overrides)
    db_session.add(execution)
    await db_session.flush()
    return execution


async def _seed_template(db_session, tenant_id, name="Delivery Tmpl") -> ReportTemplate:
    template = ReportTemplate(
        tenant_id=tenant_id,
        name=name,
        report_type=ReportType.CAMPAIGN_PERFORMANCE,
        config={"metrics": ["spend"]},
        default_format=ReportFormat.PDF,
        available_formats=["pdf", "csv"],
    )
    db_session.add(template)
    await db_session.flush()
    return template


# =============================================================================
# EmailDelivery
# =============================================================================


class TestEmailDelivery:
    @pytest.fixture
    def config(self):
        return {
            "from_email": "reports@stratum.ai",
            "from_name": "Stratum Reports",
            "smtp_host": "smtp.example.com",
            "smtp_port": 2525,
            "smtp_user": "mailer",
            "smtp_password": "s3cret",
        }

    async def test_success_with_login_and_attachment(self, config):
        config["body_template"] = "<p>Custom body for {{report_type}}</p>"
        execution = _execution(file_path=_tmp_report_file())
        with patch.object(delivery_mod.aiosmtplib, "SMTP", FakeSMTP):
            result = await EmailDelivery().deliver(execution, config, "to@example.com")

        assert result["success"] is True
        smtp = FakeSMTP.last_instance
        assert smtp.kwargs["hostname"] == "smtp.example.com"
        assert smtp.kwargs["port"] == 2525
        assert smtp.logged_in == ("mailer", "s3cret")
        assert len(smtp.sent) == 1
        msg = smtp.sent[0]
        assert msg["To"] == "to@example.com"
        assert "Campaign Performance" in msg["Subject"]
        # Multipart: HTML body + base64 attachment.
        parts = msg.get_payload()
        assert len(parts) == 2
        assert "attachment" in parts[1].get("Content-Disposition", "")

    async def test_success_without_login_or_attachment(self, config):
        config.pop("smtp_user")
        config.pop("smtp_password")
        execution = _execution(file_path=None)
        with patch.object(delivery_mod.aiosmtplib, "SMTP", FakeSMTP):
            result = await EmailDelivery().deliver(execution, config, "to@example.com")

        assert result["success"] is True
        smtp = FakeSMTP.last_instance
        assert smtp.logged_in is None
        # Only the HTML body, no attachment.
        assert len(smtp.sent[0].get_payload()) == 1

    async def test_smtp_error_returns_failure(self, config):
        execution = _execution(file_path=None)
        with patch.object(delivery_mod.aiosmtplib, "SMTP", FailingSMTP):
            result = await EmailDelivery().deliver(execution, config, "to@example.com")

        assert result["success"] is False
        assert "smtp boom" in result["error"]


# =============================================================================
# SlackDelivery
# =============================================================================


class TestSlackDelivery:
    async def test_success_posts_block_kit_message(self):
        session = FakeSession(FakeResponse(status=200, text_body="ok"))
        config = {"webhook_url": "https://hooks.slack.com/services/T/B/X"}
        with _patch_session(session):
            result = await SlackDelivery().deliver(_execution(), config, "#reports")

        assert result == {"success": True, "response": "ok"}
        call = session.calls[0]
        assert call["url"] == "https://hooks.slack.com/services/T/B/X"
        blocks = call["json"]["blocks"]
        types_ = [b["type"] for b in blocks]
        # header + fields section + metrics section + download + context
        assert types_ == ["header", "section", "section", "section", "context"]
        assert "Campaign Performance" in blocks[0]["text"]["text"]
        metrics_text = blocks[2]["text"]["text"]
        assert "$1,234.50" in metrics_text
        assert "$6,789.00" in metrics_text
        assert "5.50x" in metrics_text
        assert "https://reports.example.com/r.pdf" in blocks[3]["text"]["text"]

    async def test_recipient_used_as_webhook_when_config_empty(self):
        session = FakeSession(FakeResponse(status=200))
        execution = _execution(metrics_summary=None, file_url=None)
        with _patch_session(session):
            result = await SlackDelivery().deliver(
                execution, {}, "https://hooks.slack.com/recipient"
            )

        assert result["success"] is True
        call = session.calls[0]
        assert call["url"] == "https://hooks.slack.com/recipient"
        # No metrics / file_url -> only header + fields + context.
        assert [b["type"] for b in call["json"]["blocks"]] == [
            "header",
            "section",
            "context",
        ]

    async def test_non_200_is_failure(self):
        session = FakeSession(FakeResponse(status=404, text_body="no_service"))
        with _patch_session(session):
            result = await SlackDelivery().deliver(
                _execution(), {"webhook_url": "https://hooks.slack.com/x"}, "#r"
            )

        assert result["success"] is False
        assert "404" in result["error"]
        assert "no_service" in result["error"]

    async def test_client_error_is_failure(self):
        session = FakeSession(exc=aiohttp.ClientError("conn reset"))
        with _patch_session(session):
            result = await SlackDelivery().deliver(
                _execution(), {"webhook_url": "https://hooks.slack.com/x"}, "#r"
            )

        assert result["success"] is False
        assert "conn reset" in result["error"]


# =============================================================================
# TeamsDelivery
# =============================================================================


class TestTeamsDelivery:
    async def test_success_202_posts_message_card(self):
        session = FakeSession(FakeResponse(status=202, text_body="1"))
        config = {"webhook_url": "https://outlook.office.com/webhook/abc"}
        with _patch_session(session):
            result = await TeamsDelivery().deliver(_execution(), config, "ignored")

        assert result == {"success": True, "response": "1"}
        card = session.calls[0]["json"]
        assert card["@type"] == "MessageCard"
        facts = {f["title"]: f["value"] for f in card["sections"][0]["facts"]}
        assert facts["Total Spend"] == "$1,234.50"
        assert facts["Total Revenue"] == "$6,789.00"
        assert facts["ROAS"] == "5.50x"
        assert card["potentialAction"][0]["targets"][0]["uri"] == (
            "https://reports.example.com/r.pdf"
        )

    async def test_card_without_metrics_or_url_has_no_action(self):
        card = TeamsDelivery()._build_card(
            _execution(metrics_summary=None, file_url=None), {}
        )
        assert "potentialAction" not in card
        titles = [f["title"] for f in card["sections"][0]["facts"]]
        assert titles == ["Report Type", "Date Range", "Generated"]

    async def test_error_status_is_failure(self):
        session = FakeSession(FakeResponse(status=500, text_body="teams down"))
        with _patch_session(session):
            result = await TeamsDelivery().deliver(
                _execution(), {}, "https://outlook.office.com/webhook/abc"
            )

        assert result["success"] is False
        assert "500" in result["error"]

    async def test_client_error_is_failure(self):
        session = FakeSession(exc=aiohttp.ClientError("teams boom"))
        with _patch_session(session):
            result = await TeamsDelivery().deliver(
                _execution(), {"webhook_url": "https://o.example/w"}, ""
            )

        assert result["success"] is False
        assert "teams boom" in result["error"]


# =============================================================================
# WebhookDelivery
# =============================================================================


class TestWebhookDelivery:
    async def test_success_with_custom_headers_and_auth(self):
        session = FakeSession(FakeResponse(status=201, text_body="created"))
        execution = _execution()
        config = {
            "webhook_url": "https://api.example.com/hooks/report",
            "headers": {"X-Custom": "yes"},
            "auth_header": "Bearer tok123",
        }
        with _patch_session(session):
            result = await WebhookDelivery().deliver(execution, config, "ignored")

        assert result == {"success": True, "response": "created"}
        call = session.calls[0]
        assert call["headers"]["Content-Type"] == "application/json"
        assert call["headers"]["X-Custom"] == "yes"
        assert call["headers"]["Authorization"] == "Bearer tok123"
        payload = call["json"]
        assert payload["event"] == "report.generated"
        assert payload["tenant_id"] == execution.tenant_id
        assert payload["report"]["execution_id"] == str(execution.id)
        assert payload["report"]["type"] == "campaign_performance"
        assert payload["report"]["date_range"] == {
            "start": "2026-06-01",
            "end": "2026-06-30",
        }
        assert payload["report"]["generated_at"] == "2026-06-30T12:00:00+00:00"

    async def test_payload_without_completed_at(self):
        payload = WebhookDelivery()._build_payload(_execution(completed_at=None), {})
        assert payload["report"]["generated_at"] is None

    async def test_http_error_is_failure(self):
        session = FakeSession(FakeResponse(status=422, text_body="bad payload"))
        with _patch_session(session):
            result = await WebhookDelivery().deliver(
                _execution(), {}, "https://api.example.com/hook"
            )

        assert result["success"] is False
        assert "422" in result["error"]

    async def test_client_error_is_failure(self):
        session = FakeSession(exc=aiohttp.ClientError("dns fail"))
        with _patch_session(session):
            result = await WebhookDelivery().deliver(
                _execution(), {"webhook_url": "https://api.example.com/hook"}, ""
            )

        assert result["success"] is False
        assert "dns fail" in result["error"]


# =============================================================================
# S3Delivery
# =============================================================================


class FakeS3Client:
    def __init__(self):
        self.put_kwargs = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def put_object(self, **kwargs):
        self.put_kwargs = kwargs

    async def generate_presigned_url(self, op, Params=None, ExpiresIn=None):
        return f"https://s3.example.com/{Params['Bucket']}/{Params['Key']}?sig=1"


class TestS3Delivery:
    async def test_success_uploads_and_signs(self):
        s3_client = FakeS3Client()

        class FakeBotoSession:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def client(self, name):
                assert name == "s3"
                return s3_client

        fake_aioboto3 = types.ModuleType("aioboto3")
        fake_aioboto3.Session = FakeBotoSession

        execution = _execution(file_path=_tmp_report_file())
        config = {
            "bucket": "stratum-reports",
            "prefix": "exports/",
            "aws_access_key": "AK",
            "aws_secret_key": "SK",
        }
        with patch.dict(sys.modules, {"aioboto3": fake_aioboto3}):
            result = await S3Delivery().deliver(execution, config, "unused")

        assert result["success"] is True
        today = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        assert result["s3_key"].startswith(f"exports/{today}/")
        assert result["presigned_url"].startswith(
            "https://s3.example.com/stratum-reports/"
        )
        assert s3_client.put_kwargs["Bucket"] == "stratum-reports"
        assert s3_client.put_kwargs["ContentType"] == "application/pdf"
        assert s3_client.put_kwargs["Body"] == b"%PDF-1.4 fake report body"

    async def test_missing_aioboto3_returns_error(self):
        # sys.modules[name] = None makes ``import aioboto3`` raise ImportError.
        with patch.dict(sys.modules, {"aioboto3": None}):
            result = await S3Delivery().deliver(
                _execution(), {"bucket": "b"}, "reports/"
            )

        assert result["success"] is False
        assert "aioboto3" in result["error"]

    async def test_missing_bucket_key_is_failure(self):
        fake_aioboto3 = types.ModuleType("aioboto3")
        fake_aioboto3.Session = lambda **kw: None
        with patch.dict(sys.modules, {"aioboto3": fake_aioboto3}):
            result = await S3Delivery().deliver(_execution(), {}, "reports/")

        assert result["success"] is False
        assert "bucket" in result["error"]


# =============================================================================
# WhatsAppDelivery
# =============================================================================


class TestWhatsAppDelivery:
    @pytest.fixture
    def config(self):
        return {
            "phone_number_id": "1234567890",
            "access_token": "EAAtoken",
        }

    async def test_template_message_success(self, config):
        session = FakeSession(
            FakeResponse(status=200, json_body={"messages": [{"id": "wamid.42"}]})
        )
        with _patch_session(session):
            result = await WhatsAppDelivery().deliver(
                _execution(), config, "+15551234567"
            )

        assert result["success"] is True
        assert result["message_id"] == "wamid.42"
        call = session.calls[0]
        assert call["url"] == "https://graph.facebook.com/v18.0/1234567890/messages"
        assert call["headers"]["Authorization"] == "Bearer EAAtoken"
        payload = call["json"]
        assert payload["type"] == "template"
        assert payload["to"] == "15551234567"  # leading + stripped
        assert payload["template"]["name"] == "report_notification"

    async def test_text_message_mode(self, config):
        config["use_text_message"] = True
        session = FakeSession(
            FakeResponse(status=200, json_body={"messages": [{"id": "wamid.7"}]})
        )
        with _patch_session(session):
            result = await WhatsAppDelivery().deliver(
                _execution(), config, "+15551234567"
            )

        assert result["success"] is True
        payload = session.calls[0]["json"]
        assert payload["type"] == "text"
        assert "Stratum AI Report Ready" in payload["text"]["body"]

    async def test_api_error_response(self, config):
        session = FakeSession(
            FakeResponse(
                status=400, json_body={"error": {"message": "invalid recipient"}}
            )
        )
        with _patch_session(session):
            result = await WhatsAppDelivery().deliver(
                _execution(), config, "+15551234567"
            )

        assert result["success"] is False
        assert result["error"] == "invalid recipient"

    async def test_status_error_without_error_body(self, config):
        session = FakeSession(FakeResponse(status=500, json_body={}))
        with _patch_session(session):
            result = await WhatsAppDelivery().deliver(
                _execution(), config, "+15551234567"
            )

        assert result["success"] is False
        assert result["error"] == "HTTP 500"

    async def test_missing_config_key_is_failure(self):
        result = await WhatsAppDelivery().deliver(
            _execution(), {"access_token": "t"}, "+15551234567"
        )
        assert result["success"] is False
        assert "phone_number_id" in result["error"]


# =============================================================================
# DeliveryService.deliver_report (DB-backed)
# =============================================================================


class TestDeliverReport:
    async def test_execution_not_found_raises(self, db_session, test_tenant):
        service = DeliveryService(db_session, test_tenant["id"])
        with pytest.raises(ValueError, match="Execution not found"):
            await service.deliver_report(uuid.uuid4(), ["email"], {})

    async def test_wrong_tenant_raises(self, db_session, test_tenant):
        execution = await _seed_execution(db_session, test_tenant["id"])
        service = DeliveryService(db_session, test_tenant["id"] + 999)
        with pytest.raises(ValueError, match="Execution not found"):
            await service.deliver_report(execution.id, ["email"], {})

    async def test_incomplete_execution_raises(self, db_session, test_tenant):
        execution = await _seed_execution(
            db_session, test_tenant["id"], status=ExecutionStatus.RUNNING
        )
        service = DeliveryService(db_session, test_tenant["id"])
        with pytest.raises(ValueError, match="Cannot deliver report"):
            await service.deliver_report(execution.id, ["email"], {})

    async def test_multi_channel_persists_delivery_rows(self, db_session, test_tenant):
        execution = await _seed_execution(db_session, test_tenant["id"])
        service = DeliveryService(db_session, test_tenant["id"])

        email_results = [
            {"success": True, "message_id": "<msg-1@stratum>", "response": "ok"},
            {"success": False, "error": "mailbox full"},
        ]
        with patch.object(
            EmailDelivery, "deliver", AsyncMock(side_effect=email_results)
        ) as email_mock, patch.object(
            SlackDelivery,
            "deliver",
            AsyncMock(return_value={"success": True, "response": "ok"}),
        ) as slack_mock:
            results = await service.deliver_report(
                execution.id,
                ["email", "slack", "carrier_pigeon"],
                {
                    "email": {
                        "recipients": ["a@example.com"],
                        "cc": ["b@example.com"],
                    },
                    "slack": {"webhook_url": "https://hooks.slack.com/x"},
                },
            )

        assert results["total_recipients"] == 3
        assert results["successful"] == 2
        assert results["failed"] == 1
        # Unknown channel skipped entirely.
        assert "carrier_pigeon" not in results["channels"]
        assert email_mock.await_count == 2
        assert slack_mock.await_count == 1

        email_channel = results["channels"]["email"]
        assert email_channel[0] == {
            "recipient": "a@example.com",
            "success": True,
            "error": None,
        }
        assert email_channel[1]["error"] == "mailbox full"

        # ReportDelivery rows persisted with correct statuses.
        status = await service.get_delivery_status(execution.id)
        assert len(status) == 3
        by_recipient = {d["recipient"]: d for d in status}
        assert by_recipient["a@example.com"]["status"] == "sent"
        assert by_recipient["a@example.com"]["sent_at"] is not None
        assert by_recipient["b@example.com"]["status"] == "failed"
        assert by_recipient["b@example.com"]["error"] == "mailbox full"
        assert by_recipient["https://hooks.slack.com/x"]["channel"] == "slack"
        assert by_recipient["https://hooks.slack.com/x"]["status"] == "sent"

    async def test_channel_without_handler_is_skipped(self, db_session, test_tenant):
        execution = await _seed_execution(db_session, test_tenant["id"])
        service = DeliveryService(db_session, test_tenant["id"])

        with patch.dict(DeliveryService.CHANNEL_HANDLERS):
            del DeliveryService.CHANNEL_HANDLERS[DeliveryChannel.SLACK]
            results = await service.deliver_report(
                execution.id,
                ["slack"],
                {"slack": {"webhook_url": "https://hooks.slack.com/x"}},
            )

        assert results["total_recipients"] == 0
        assert results["channels"] == {}

    async def test_whatsapp_channel_delivers_to_phone_numbers(
        self, db_session, test_tenant
    ):
        # Regression for the fixed bug: _get_recipients now has a WHATSAPP
        # branch that reads phone numbers from ``phone_numbers``, so a
        # whatsapp-channel schedule resolves recipients and delivers.
        execution = await _seed_execution(db_session, test_tenant["id"])
        service = DeliveryService(db_session, test_tenant["id"])

        with patch.object(
            WhatsAppDelivery,
            "deliver",
            AsyncMock(return_value={"success": True, "message_id": "wamid.1"}),
        ) as wa_mock:
            results = await service.deliver_report(
                execution.id,
                ["whatsapp"],
                {
                    "whatsapp": {
                        "phone_number_id": "1",
                        "access_token": "t",
                        "phone_numbers": ["+15551234567", "+15559876543"],
                    }
                },
            )

        assert results["total_recipients"] == 2
        assert results["successful"] == 2
        assert wa_mock.await_count == 2
        wa_channel = results["channels"]["whatsapp"]
        assert {c["recipient"] for c in wa_channel} == {
            "+15551234567",
            "+15559876543",
        }
        assert all(c["success"] for c in wa_channel)

    async def test_get_recipients_branches(self, db_session, test_tenant):
        service = DeliveryService(db_session, test_tenant["id"])
        get = service._get_recipients

        assert get(
            DeliveryChannel.EMAIL, {"recipients": ["a@x.com"], "cc": ["b@x.com"]}
        ) == ["a@x.com", "b@x.com"]
        assert get(DeliveryChannel.SLACK, {"channel": "#reports"}) == ["#reports"]
        assert get(DeliveryChannel.SLACK, {"webhook_url": "https://h/x"}) == [
            "https://h/x"
        ]
        assert get(DeliveryChannel.SLACK, {}) == []
        assert get(DeliveryChannel.TEAMS, {"webhook_url": "https://t/x"}) == [
            "https://t/x"
        ]
        assert get(DeliveryChannel.TEAMS, {}) == []
        assert get(DeliveryChannel.WEBHOOK, {"webhook_url": "https://w/x"}) == [
            "https://w/x"
        ]
        assert get(DeliveryChannel.WEBHOOK, {}) == []
        assert get(DeliveryChannel.S3, {}) == ["reports/"]
        assert get(DeliveryChannel.S3, {"prefix": "custom/"}) == ["custom/"]
        assert get(DeliveryChannel.WHATSAPP, {}) == []
        assert get(DeliveryChannel.WHATSAPP, {"phone_numbers": ["+15551234567"]}) == [
            "+15551234567"
        ]


# =============================================================================
# DeliveryService.retry_delivery (DB-backed)
# =============================================================================


async def _seed_failed_delivery(
    db_session, tenant_id, execution, channel=DeliveryChannel.SLACK
) -> ReportDelivery:
    delivery = ReportDelivery(
        tenant_id=tenant_id,
        execution_id=execution.id,
        channel=channel,
        recipient="https://hooks.slack.com/original",
        status=DeliveryStatus.FAILED,
        error_message="first attempt failed",
    )
    db_session.add(delivery)
    await db_session.flush()
    return delivery


class TestRetryDelivery:
    async def test_not_found_raises(self, db_session, test_tenant):
        service = DeliveryService(db_session, test_tenant["id"])
        with pytest.raises(ValueError, match="Delivery not found"):
            await service.retry_delivery(uuid.uuid4())

    async def test_non_failed_status_raises(self, db_session, test_tenant):
        execution = await _seed_execution(db_session, test_tenant["id"])
        delivery = ReportDelivery(
            tenant_id=test_tenant["id"],
            execution_id=execution.id,
            channel=DeliveryChannel.SLACK,
            recipient="#r",
            status=DeliveryStatus.SENT,
        )
        db_session.add(delivery)
        await db_session.flush()

        service = DeliveryService(db_session, test_tenant["id"])
        with pytest.raises(ValueError, match="only retry failed"):
            await service.retry_delivery(delivery.id)

    async def test_successful_retry_uses_schedule_config(self, db_session, test_tenant):
        template = await _seed_template(db_session, test_tenant["id"], "Retry Tmpl")
        schedule = ScheduledReport(
            tenant_id=test_tenant["id"],
            template_id=template.id,
            name="Retry Sched",
            frequency=ScheduleFrequency.DAILY,
            hour=8,
            minute=0,
            timezone="UTC",
            delivery_channels=["slack"],
            delivery_config={"slack": {"webhook_url": "https://hooks.slack.com/cfg"}},
        )
        db_session.add(schedule)
        await db_session.flush()

        execution = await _seed_execution(
            db_session, test_tenant["id"], schedule_id=schedule.id
        )
        delivery = await _seed_failed_delivery(db_session, test_tenant["id"], execution)

        service = DeliveryService(db_session, test_tenant["id"])
        with patch.object(
            SlackDelivery,
            "deliver",
            AsyncMock(
                return_value={"success": True, "message_id": "ts.1", "response": "ok"}
            ),
        ) as slack_mock:
            result = await service.retry_delivery(delivery.id)

        assert result["success"] is True
        # Handler received the schedule's channel config + original recipient.
        args = slack_mock.await_args.args
        assert args[1] == {"webhook_url": "https://hooks.slack.com/cfg"}
        assert args[2] == "https://hooks.slack.com/original"

        assert delivery.status == DeliveryStatus.SENT
        assert delivery.retry_count == 1
        assert delivery.sent_at is not None
        assert delivery.message_id == "ts.1"
        assert delivery.error_message is None
        assert delivery.last_retry_at is not None

    async def test_failed_retry_records_error(self, db_session, test_tenant):
        execution = await _seed_execution(db_session, test_tenant["id"])
        delivery = await _seed_failed_delivery(db_session, test_tenant["id"], execution)

        service = DeliveryService(db_session, test_tenant["id"])
        with patch.object(
            SlackDelivery,
            "deliver",
            AsyncMock(return_value={"success": False, "error": "still down"}),
        ):
            result = await service.retry_delivery(delivery.id)

        assert result["success"] is False
        assert delivery.status == DeliveryStatus.FAILED
        assert delivery.retry_count == 1
        assert delivery.error_message == "still down"

    async def test_missing_handler_raises(self, db_session, test_tenant):
        execution = await _seed_execution(db_session, test_tenant["id"])
        delivery = await _seed_failed_delivery(db_session, test_tenant["id"], execution)

        service = DeliveryService(db_session, test_tenant["id"])
        with patch.dict(DeliveryService.CHANNEL_HANDLERS):
            del DeliveryService.CHANNEL_HANDLERS[DeliveryChannel.SLACK]
            with pytest.raises(ValueError, match="No handler"):
                await service.retry_delivery(delivery.id)


# =============================================================================
# DeliveryService.get_delivery_status
# =============================================================================


class TestGetDeliveryStatus:
    async def test_empty_when_no_deliveries(self, db_session, test_tenant):
        execution = await _seed_execution(db_session, test_tenant["id"])
        service = DeliveryService(db_session, test_tenant["id"])
        assert await service.get_delivery_status(execution.id) == []

    async def test_returns_serialized_rows(self, db_session, test_tenant):
        execution = await _seed_execution(db_session, test_tenant["id"])
        delivery = await _seed_failed_delivery(db_session, test_tenant["id"], execution)

        service = DeliveryService(db_session, test_tenant["id"])
        rows = await service.get_delivery_status(execution.id)

        assert len(rows) == 1
        assert rows[0]["id"] == str(delivery.id)
        assert rows[0]["channel"] == "slack"
        assert rows[0]["status"] == "failed"
        assert rows[0]["error"] == "first attempt failed"
        assert rows[0]["retry_count"] == 0
        assert rows[0]["sent_at"] is None
