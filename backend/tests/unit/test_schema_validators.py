# =============================================================================
# Stratum AI - Schema Validators unit tests
# =============================================================================
"""Unit tests for Pydantic validators in app.schemas.client and
app.schemas.embed_widgets.

Pure validation logic, no I/O. Covers slug normalization, URL-format
validation, IANA timezone validation, domain-pattern allow-listing
(security-relevant for embed CORS), and the widget custom-dimension
model validator.
"""

import pytest
from pydantic import ValidationError

from app.schemas.client import ClientCreate
from app.schemas.embed_widgets import (
    DomainWhitelistCreate,
    TokenCreate,
    WidgetCreate,
    WidgetSize,
    WidgetType,
)

pytestmark = pytest.mark.unit


def _client(**overrides):
    data = {"name": "Acme Corp", "slug": "acme"}
    data.update(overrides)
    return ClientCreate(**data)


# =============================================================================
# ClientCreate validators
# =============================================================================
class TestClientValidators:
    def test_minimal_valid(self):
        client = _client()
        assert client.slug == "acme"
        assert client.currency == "USD"
        assert client.timezone == "UTC"

    def test_slug_validator_lowercases(self):
        # exercised directly (field pattern already constrains to lowercase)
        assert ClientCreate.validate_slug("  ACME-1 ") == "acme-1"

    def test_slug_pattern_rejects_invalid(self):
        with pytest.raises(ValidationError):
            _client(slug="Has Spaces")

    @pytest.mark.parametrize("url", ["https://example.com", "http://a.b/c", "", None])
    def test_url_validator_accepts_valid(self, url):
        client = _client(website=url)
        assert client.website == url

    @pytest.mark.parametrize("url", ["not-a-url", "ftp://example.com", "example.com"])
    def test_url_validator_rejects_invalid(self, url):
        with pytest.raises(ValidationError):
            _client(website=url)

    def test_logo_url_also_validated(self):
        with pytest.raises(ValidationError):
            _client(logo_url="javascript:alert(1)")

    def test_timezone_accepts_iana(self):
        assert _client(timezone="America/New_York").timezone == "America/New_York"

    def test_timezone_rejects_unknown(self):
        with pytest.raises(ValidationError):
            _client(timezone="Mars/Phobos")


# =============================================================================
# Domain pattern validators (embed CORS security)
# =============================================================================
class TestDomainPattern:
    @pytest.mark.parametrize(
        "domain", ["example.com", "dashboard.client.com", "*.client.com", "a-b.co.uk"]
    )
    def test_valid_domains_lowercased(self, domain):
        entry = DomainWhitelistCreate(domain_pattern=domain.upper())
        assert entry.domain_pattern == domain.lower()

    @pytest.mark.parametrize(
        "domain",
        ["has spaces.com", "*.*.com", "-bad.com", "http://example.com", "a..b.com"],
    )
    def test_invalid_domains_rejected(self, domain):
        with pytest.raises(ValidationError):
            DomainWhitelistCreate(domain_pattern=domain)

    def test_token_allowed_domains_validated_and_lowered(self):
        token = TokenCreate(allowed_domains=["Example.COM", "*.client.com"])
        assert token.allowed_domains == ["example.com", "*.client.com"]

    def test_token_rejects_bad_domain_in_list(self):
        with pytest.raises(ValidationError):
            TokenCreate(allowed_domains=["good.com", "bad domain"])

    def test_token_requires_at_least_one_domain(self):
        with pytest.raises(ValidationError):
            TokenCreate(allowed_domains=[])


# =============================================================================
# Widget custom-dimension model validator
# =============================================================================
class TestWidgetDimensions:
    def test_standard_size_no_dimensions_required(self):
        widget = WidgetCreate(
            name="My Widget",
            widget_type=WidgetType.ROAS_DISPLAY,
            widget_size=WidgetSize.STANDARD,
        )
        assert widget.custom_width is None

    def test_custom_size_requires_both_dimensions(self):
        widget = WidgetCreate(
            name="Custom",
            widget_type=WidgetType.SIGNAL_HEALTH,
            widget_size=WidgetSize.CUSTOM,
            custom_width=400,
            custom_height=300,
        )
        assert widget.custom_width == 400

    def test_custom_size_missing_width_rejected(self):
        with pytest.raises(ValidationError, match="Custom dimensions required"):
            WidgetCreate(
                name="Custom",
                widget_type=WidgetType.SIGNAL_HEALTH,
                widget_size=WidgetSize.CUSTOM,
                custom_height=300,
            )

    def test_custom_size_missing_height_rejected(self):
        with pytest.raises(ValidationError, match="Custom dimensions required"):
            WidgetCreate(
                name="Custom",
                widget_type=WidgetType.SIGNAL_HEALTH,
                widget_size=WidgetSize.CUSTOM,
                custom_width=400,
            )

    def test_dimension_bounds_enforced(self):
        with pytest.raises(ValidationError):
            WidgetCreate(
                name="Too big",
                widget_type=WidgetType.SIGNAL_HEALTH,
                widget_size=WidgetSize.CUSTOM,
                custom_width=5000,  # > 1200
                custom_height=300,
            )
