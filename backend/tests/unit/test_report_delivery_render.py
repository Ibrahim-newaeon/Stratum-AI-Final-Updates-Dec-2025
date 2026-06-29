# =============================================================================
# Stratum AI - Report Delivery Rendering Unit Tests
# =============================================================================
"""Unit tests for the pure rendering helpers of the report-delivery channel
handlers in ``app.services.reporting.delivery``:

- ``EmailDelivery._render_subject`` / ``_render_body`` template substitution
- ``EmailDelivery._get_content_type`` format -> MIME mapping
- ``WhatsAppDelivery._build_summary`` text summary building

These handlers have no constructor state and the rendering helpers never
do I/O, so they're exercised with duck-typed execution objects. The async
``deliver`` paths (SMTP / HTTP) are out of scope here.
"""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.services.reporting.delivery import EmailDelivery, WhatsAppDelivery

pytestmark = pytest.mark.unit


def _execution(**overrides) -> SimpleNamespace:
    base = dict(
        report_type=SimpleNamespace(value="campaign_performance"),
        format=SimpleNamespace(value="pdf"),
        date_range_start="2026-06-01",
        date_range_end="2026-06-30",
        completed_at=datetime(2026, 6, 30, 12, 0, tzinfo=timezone.utc),
        file_url="https://reports.example.com/r.pdf",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


# =============================================================================
# EmailDelivery._render_subject
# =============================================================================
class TestRenderSubject:
    @pytest.fixture
    def email(self) -> EmailDelivery:
        return EmailDelivery()

    def test_default_template(self, email):
        subject = email._render_subject(_execution(), {})
        # report_type is title-cased with underscores -> spaces.
        assert subject == "Campaign Performance Report - 2026-06-01 to 2026-06-30"

    def test_custom_template(self, email):
        subject = email._render_subject(
            _execution(), {"subject_template": "[{{report_type}}]"}
        )
        assert subject == "[Campaign Performance]"


# =============================================================================
# EmailDelivery._render_body
# =============================================================================
class TestRenderBody:
    @pytest.fixture
    def email(self) -> EmailDelivery:
        return EmailDelivery()

    def test_default_body_substitutes_placeholders(self, email):
        body = email._render_body(_execution(), {})
        assert "Campaign Performance" in body
        assert "2026-06-01 to 2026-06-30" in body
        assert "2026-06-30 12:00 UTC" in body
        # No unreplaced placeholders remain.
        assert "{{" not in body

    def test_missing_completed_at_renders_na(self, email):
        body = email._render_body(_execution(completed_at=None), {})
        assert "N/A" in body

    def test_custom_template(self, email):
        body = email._render_body(
            _execution(), {"body_template": "Range: {{date_range}}"}
        )
        assert body == "Range: 2026-06-01 to 2026-06-30"


# =============================================================================
# EmailDelivery._get_content_type
# =============================================================================
class TestContentType:
    @pytest.fixture
    def email(self) -> EmailDelivery:
        return EmailDelivery()

    @pytest.mark.parametrize(
        "fmt,mime",
        [
            ("pdf", "application/pdf"),
            ("csv", "text/csv"),
            ("json", "application/json"),
            ("html", "text/html"),
            (
                "excel",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
        ],
    )
    def test_known_formats(self, email, fmt, mime):
        assert email._get_content_type(fmt) == mime

    def test_unknown_format_is_octet_stream(self, email):
        assert email._get_content_type("xyz") == "application/octet-stream"


# =============================================================================
# WhatsAppDelivery._build_summary
# =============================================================================
class TestWhatsAppSummary:
    @pytest.fixture
    def whatsapp(self) -> WhatsAppDelivery:
        return WhatsAppDelivery()

    def test_summary_contains_key_fields(self, whatsapp):
        summary = whatsapp._build_summary(_execution())
        assert "Stratum AI Report Ready" in summary
        assert "Campaign Performance" in summary
        assert "2026-06-01 to 2026-06-30" in summary
        assert "PDF" in summary
        # file_url present -> a download line is appended.
        assert "https://reports.example.com/r.pdf" in summary

    def test_summary_without_completed_at(self, whatsapp):
        summary = whatsapp._build_summary(_execution(completed_at=None, file_url=None))
        assert "N/A" in summary
        # No file_url -> no download link.
        assert "Download:" not in summary
