# =============================================================================
# Stratum AI - Drip Tracking, Unsubscribe and Feature Gating
# =============================================================================
"""The open-pixel, click and unsubscribe routes must survive the feature flag.

Those three URLs are baked into emails that have already been delivered. An
inbox is forever: turning ``FEATURE_DRIP_CAMPAIGNS`` off later must not turn a
recipient's unsubscribe link into a 503, and no configuration change may make
refusing an opt-out the default behaviour.

Two things are load-bearing and easy to break by accident:

1. ``public_router`` carries no feature-gate dependency.
2. It is registered **before** the gated router. ``/drip-campaigns/unsubscribe``
   and ``/drip-campaigns/{sequence_id}`` are the same shape, and routes match in
   registration order — the wrong order sends every unsubscribe click to the
   sequence handler.
"""

import pytest

from app.services.drip.render import (
    build_unsubscribe_url,
    sign_unsubscribe_token,
    verify_unsubscribe_token,
)


def _match_order(router) -> list[str]:
    """Every route path in the order the router will try to match it.

    This FastAPI wraps ``include_router`` results in ``_IncludedRouter``, which
    nests rather than flattening, so the walk has to recurse to see the real
    ordering.
    """
    paths: list[str] = []

    def walk(node) -> None:
        for route in getattr(node, "routes", []):
            nested = getattr(route, "original_router", None)
            if nested is not None:
                walk(nested)
            elif hasattr(route, "path"):
                paths.append(route.path)

    walk(router)
    return paths


# ---------------------------------------------------------------------------
# Route wiring
# ---------------------------------------------------------------------------


class TestRouterWiring:
    async def test_public_router_has_no_feature_gate(self):
        from app.api.v1.endpoints import drip_campaigns

        assert drip_campaigns.public_router.dependencies == []
        # ... while the product surface does have one.
        assert drip_campaigns.router.dependencies

    async def test_unsubscribe_is_registered_before_the_sequence_route(self):
        """The literal path must win over ``/{sequence_id}``."""
        from app.api.v1 import api_router

        unsubscribe = _match_order(api_router).index("/drip-campaigns/unsubscribe")
        wildcard = _match_order(api_router).index("/drip-campaigns/{sequence_id}")
        assert unsubscribe < wildcard, (
            "public_router must be included before the gated router, or "
            "/drip-campaigns/unsubscribe binds to /{sequence_id}"
        )

    async def test_unsubscribe_accepts_get_and_post(self):
        """POST is required for RFC 8058 one-click unsubscribe."""
        from app.api.v1.endpoints import drip_campaigns

        route = next(
            r
            for r in drip_campaigns.public_router.routes
            if r.path == "/drip-campaigns/unsubscribe"
        )
        assert {"GET", "POST"} <= set(route.methods)


class TestFeatureGateReachesTheProductSurface:
    async def test_listing_sequences_is_503_when_disabled(
        self, api_client, admin_headers, monkeypatch
    ):
        from app.core.config import settings

        monkeypatch.setattr(settings, "feature_drip_campaigns", False)
        response = await api_client.get("/api/v1/drip-campaigns", headers=admin_headers)
        assert response.status_code == 503

    async def test_unsubscribe_still_answers_when_disabled(
        self, api_client, monkeypatch
    ):
        """The point of the whole split: opting out works with the flag off."""
        from app.core.config import settings

        monkeypatch.setattr(settings, "feature_drip_campaigns", False)
        token = sign_unsubscribe_token(1, "a" * 64)
        response = await api_client.get(
            f"/api/v1/drip-campaigns/unsubscribe?token={token}"
        )
        assert response.status_code != 503
        assert response.status_code == 200
        assert response.json()["data"]["unsubscribed"] is True

    async def test_open_pixel_still_answers_when_disabled(
        self, api_client, monkeypatch
    ):
        from app.core.config import settings

        monkeypatch.setattr(settings, "feature_drip_campaigns", False)
        response = await api_client.get(
            "/api/v1/drip-campaigns/track/open/exec_missing"
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/gif"


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------


class TestUnsubscribeToken:
    """The newsletter's equivalent base64-encodes ``campaign_id:subscriber_id``
    and calls it signed — decrementing an integer unsubscribes a stranger. This
    one is HMAC-signed, so none of that works."""

    def test_round_trips(self):
        token = sign_unsubscribe_token(42, "f" * 64)
        assert verify_unsubscribe_token(token) == (42, "f" * 64)

    def test_rejects_a_tampered_payload(self):
        token = sign_unsubscribe_token(42, "f" * 64)
        _, _, signature = token.partition(".")
        forged = sign_unsubscribe_token(43, "f" * 64).partition(".")[0]
        assert verify_unsubscribe_token(f"{forged}.{signature}") is None

    def test_rejects_a_tampered_signature(self):
        token = sign_unsubscribe_token(42, "f" * 64)
        payload, _, signature = token.partition(".")
        assert verify_unsubscribe_token(f"{payload}.{signature[:-2]}xy") is None

    @pytest.mark.parametrize(
        "bad", ["", "garbage", "no-separator", ".", "a.b", "!!!.???"]
    )
    def test_rejects_malformed_tokens(self, bad):
        assert verify_unsubscribe_token(bad) is None

    def test_never_contains_the_address(self):
        # The hash goes in the URL, never the email — URLs end up in logs,
        # referrers and support tickets.
        url = build_unsubscribe_url(7, "c" * 64, "https://api.example.com")
        assert "@" not in url
        assert "/api/v1/drip-campaigns/unsubscribe?token=" in url

    def test_different_tenants_get_different_tokens(self):
        assert sign_unsubscribe_token(1, "a" * 64) != sign_unsubscribe_token(
            2, "a" * 64
        )


# ---------------------------------------------------------------------------
# Click tracking
# ---------------------------------------------------------------------------


class TestClickTracking:
    async def test_redirects_to_the_original_destination(self, api_client):
        response = await api_client.get(
            "/api/v1/drip-campaigns/track/click/exec_1?url=https%3A%2F%2Fexample.com%2Fa",
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["location"] == "https://example.com/a"

    @pytest.mark.parametrize(
        "scheme",
        [
            "javascript:alert(1)",
            "data:text/html;base64,PHNjcmlwdD4=",
            "file:///etc/passwd",
            "//evil.example.com",
        ],
    )
    async def test_refuses_non_http_targets(self, api_client, scheme):
        """Without this the tracker is an open redirect signed by our domain."""
        from urllib.parse import quote

        response = await api_client.get(
            f"/api/v1/drip-campaigns/track/click/exec_1?url={quote(scheme, safe='')}",
            follow_redirects=False,
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Link rewriting
# ---------------------------------------------------------------------------


class TestTrackingInjection:
    def test_pixel_is_added_before_body_close(self):
        from app.services.drip.render import inject_tracking

        out = inject_tracking("<html><body>Hi</body></html>", "exec_1", "https://a.io")
        assert "track/open/exec_1" in out
        assert out.index("track/open/exec_1") < out.index("</body>")

    def test_links_are_rewritten(self):
        from app.services.drip.render import inject_tracking

        out = inject_tracking(
            '<a href="https://x.io/p">go</a>', "exec_1", "https://a.io"
        )
        assert "track/click/exec_1" in out
        assert "https%3A%2F%2Fx.io%2Fp" in out

    def test_unsubscribe_link_is_left_alone(self):
        """Routing an opt-out through click tracking would record refusing to
        be mailed as engagement."""
        from app.services.drip.render import inject_tracking

        href = "https://a.io/api/v1/drip-campaigns/unsubscribe?token=t"
        out = inject_tracking(f'<a href="{href}">out</a>', "exec_1", "https://a.io")
        assert f'href="{href}"' in out
        assert "track/click" not in out

    def test_mailto_and_anchors_are_left_alone(self):
        from app.services.drip.render import inject_tracking

        html = '<a href="mailto:a@b.io">m</a><a href="#top">t</a>'
        assert inject_tracking(html, "exec_1", "https://a.io").count("track/click") == 0

    def test_footer_is_appended_when_the_template_forgot_one(self):
        from app.services.drip.render import append_unsubscribe_footer

        out = append_unsubscribe_footer("<html><body>x</body></html>", "https://u/1")
        assert "https://u/1" in out

    def test_footer_is_not_duplicated(self):
        from app.services.drip.render import append_unsubscribe_footer

        html = '<body><a href="https://u/1">Unsubscribe</a></body>'
        assert append_unsubscribe_footer(html, "https://u/1") == html


class TestPersonalisation:
    def test_replaces_known_placeholders(self):
        from app.services.drip.render import personalization_context, personalize

        context = personalization_context("Person@Example.com", "Ada Lovelace")
        out = personalize("Hi {{first_name}} <{{email}}>", context)
        assert out == "Hi Ada <Person@Example.com>"

    def test_missing_name_falls_back(self):
        from app.services.drip.render import personalization_context, personalize

        context = personalization_context("a@b.io")
        assert personalize("Hi {{first_name}}", context) == "Hi there"

    def test_unknown_placeholder_is_left_visible(self):
        # Blanking it would hide the typo; leaving it shows up in a test send.
        from app.services.drip.render import personalization_context, personalize

        context = personalization_context("a@b.io")
        assert personalize("Hi {{nickname}}", context) == "Hi {{nickname}}"
