# =============================================================================
# Stratum AI - Feature Gate (request/DB paths) Unit Tests
# =============================================================================
"""Unit tests for the request- and DB-backed paths of ``app.core.feature_gate``.

Complements ``test_feature_gate_pure.py`` (settings-fallback helpers) and
``test_feature_gating.py`` (basic FeatureGate allow/deny). Covers:

- ``get_tier_from_request`` and the ``get_current_tier`` settings branches
- ``FeatureGate`` / ``TierGate`` subscription checks (pass and 402)
- structured 403 details (``FeatureNotAvailableError`` / ``LimitExceededError``)
- ``LimitChecker`` under/over limit
- ``require_feature`` / ``require_tier`` decorators (request in args,
  kwargs, and absent)
- DB-backed ``get_tenant_tier`` plan mapping and the ``*_for_tenant`` helpers
"""

from types import SimpleNamespace
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, Request

from app.core import feature_gate as fg
from app.core.subscription import SubscriptionInfo, SubscriptionStatus
from app.core.tiers import TIER_FEATURES, Feature, SubscriptionTier

pytestmark = pytest.mark.unit

# A feature that every Starter tenant has (picked from the real matrix).
STARTER_FEATURE = sorted(
    TIER_FEATURES[SubscriptionTier.STARTER], key=lambda f: f.value
)[0]
# GDPR tooling is pinned Enterprise-only by test_feature_gating.py.
ENTERPRISE_FEATURE = Feature.GDPR_TOOLS


# =============================================================================
# Helpers
# =============================================================================


def _request(tenant_id: Optional[int] = 5, **state) -> SimpleNamespace:
    """Fake request with a mutable state namespace."""
    ns = SimpleNamespace(**state)
    if tenant_id is not None:
        ns.tenant_id = tenant_id
    return SimpleNamespace(state=ns)


def _http_request(tenant_id: Optional[int] = None) -> Request:
    """Real starlette Request (needed for isinstance checks in decorators)."""
    req = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": b"",
        }
    )
    if tenant_id is not None:
        req.state.tenant_id = tenant_id
    return req


def _sub_info(
    status: SubscriptionStatus,
    tier: SubscriptionTier = SubscriptionTier.ENTERPRISE,
    restricted: bool = False,
) -> SubscriptionInfo:
    """Build a minimal SubscriptionInfo for gate tests."""
    return SubscriptionInfo(
        tenant_id=5,
        plan=tier.value,
        tier=tier,
        status=status,
        expires_at=None,
        days_until_expiry=None,
        days_in_grace=None,
        is_access_restricted=restricted,
        restriction_reason="restricted" if restricted else None,
    )


def _patch_tier(monkeypatch: pytest.MonkeyPatch, tier: SubscriptionTier) -> None:
    """Patch the module-level get_tenant_tier used by gates and helpers."""

    async def fake_tier(_tenant_id: int) -> SubscriptionTier:
        return tier

    monkeypatch.setattr(fg, "get_tenant_tier", fake_tier)


def _patch_sub_info(monkeypatch: pytest.MonkeyPatch, info: SubscriptionInfo) -> None:
    """Patch get_subscription_info at its lazy-import site."""
    monkeypatch.setattr(
        "app.core.subscription.get_subscription_info",
        AsyncMock(return_value=info),
    )


def _patch_db_plan(monkeypatch: pytest.MonkeyPatch, plan: Optional[str]) -> None:
    """Patch app.db.session.get_async_session with a mock session yielding `plan`."""
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = plan
    session.execute = AsyncMock(return_value=result)

    async def _gen():
        yield session

    monkeypatch.setattr("app.db.session.get_async_session", _gen)


# =============================================================================
# get_current_tier / get_tier_from_request
# =============================================================================


class TestTierResolution:
    def test_get_required_tier_unknown_feature_returns_none(self) -> None:
        """A value present in no tier's feature set has no required tier."""
        # Deliberately not a Feature member: pins the None fallback.
        assert fg.get_required_tier("not-a-real-feature") is None  # type: ignore[arg-type]

    def test_get_current_tier_reads_settings_value(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A valid settings tier string is honoured."""
        monkeypatch.setattr(
            fg, "settings", SimpleNamespace(subscription_tier="enterprise")
        )
        assert fg.get_current_tier() == SubscriptionTier.ENTERPRISE

    def test_get_current_tier_invalid_value_defaults_to_starter(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An unknown settings tier falls back to the safe STARTER default."""
        monkeypatch.setattr(fg, "settings", SimpleNamespace(subscription_tier="bogus"))
        assert fg.get_current_tier() == SubscriptionTier.STARTER

    def test_get_tier_from_request_reads_cached_tier(self) -> None:
        """A cached request.state.subscription_tier is parsed."""
        request = _request(subscription_tier="professional")
        assert fg.get_tier_from_request(request) == SubscriptionTier.PROFESSIONAL

    def test_get_tier_from_request_invalid_value_defaults_to_starter(self) -> None:
        """An unparseable cached tier falls back to STARTER."""
        request = _request(subscription_tier="BOGUS-TIER")
        assert fg.get_tier_from_request(request) == SubscriptionTier.STARTER

    def test_get_tier_from_request_missing_defaults_to_starter(self) -> None:
        """No cached tier means the STARTER default."""
        request = _request()
        assert fg.get_tier_from_request(request) == SubscriptionTier.STARTER


# =============================================================================
# FeatureGate
# =============================================================================


class TestFeatureGateSubscription:
    async def test_valid_subscription_passes_and_caches_tier(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An active subscription passes and caches info + tier on the request."""
        info = _sub_info(SubscriptionStatus.ACTIVE, SubscriptionTier.ENTERPRISE)
        _patch_sub_info(monkeypatch, info)
        request = _request()

        gate = fg.FeatureGate(ENTERPRISE_FEATURE, check_subscription=True)
        assert await gate(request) is None
        assert request.state.subscription_info is info
        assert request.state.subscription_tier == "enterprise"

    async def test_expired_subscription_raises_402(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An expired subscription is rejected with a structured 402."""
        _patch_sub_info(
            monkeypatch,
            _sub_info(SubscriptionStatus.EXPIRED, restricted=True),
        )

        gate = fg.FeatureGate(ENTERPRISE_FEATURE, check_subscription=True)
        with pytest.raises(HTTPException) as exc:
            await gate(_request())

        assert exc.value.status_code == 402
        assert exc.value.detail["error"] == "subscription_expired"
        assert exc.value.detail["feature"] == ENTERPRISE_FEATURE.value

    async def test_feature_denied_detail_is_structured(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The 403 carries the feature, tiers, and an upgrade URL."""
        _patch_tier(monkeypatch, SubscriptionTier.STARTER)

        gate = fg.FeatureGate(ENTERPRISE_FEATURE, check_subscription=False)
        with pytest.raises(fg.FeatureNotAvailableError) as exc:
            await gate(_request())

        detail = exc.value.detail
        assert exc.value.status_code == 403
        assert detail["error"] == "feature_not_available"
        assert detail["feature"] == ENTERPRISE_FEATURE.value
        assert detail["current_tier"] == "starter"
        assert detail["required_tier"] == "enterprise"
        assert detail["upgrade_url"] == "/settings/billing"

    async def test_no_tenant_uses_settings_fallback(self) -> None:
        """Without a tenant, the settings fallback (STARTER) drives the gate."""
        deny_gate = fg.FeatureGate(ENTERPRISE_FEATURE, check_subscription=True)
        with pytest.raises(HTTPException) as exc:
            await deny_gate(_request(tenant_id=None))
        assert exc.value.status_code == 403

        allow_gate = fg.FeatureGate(STARTER_FEATURE, check_subscription=True)
        assert await allow_gate(_request(tenant_id=None)) is None


# =============================================================================
# TierGate
# =============================================================================


class TestTierGate:
    async def test_sufficient_tier_passes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A tenant at or above the minimum tier passes."""
        info = _sub_info(SubscriptionStatus.ACTIVE, SubscriptionTier.PROFESSIONAL)
        _patch_sub_info(monkeypatch, info)
        request = _request()

        gate = fg.TierGate(SubscriptionTier.PROFESSIONAL)
        assert await gate(request) is None
        assert request.state.subscription_tier == "professional"

    async def test_expired_subscription_raises_402(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An expired subscription is rejected before the tier check."""
        _patch_sub_info(
            monkeypatch, _sub_info(SubscriptionStatus.EXPIRED, restricted=True)
        )

        gate = fg.TierGate(SubscriptionTier.STARTER)
        with pytest.raises(HTTPException) as exc:
            await gate(_request())
        assert exc.value.status_code == 402
        assert exc.value.detail["error"] == "subscription_expired"

    async def test_insufficient_tier_raises_403(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A tenant below the minimum tier gets a structured 403."""
        _patch_tier(monkeypatch, SubscriptionTier.STARTER)

        gate = fg.TierGate(SubscriptionTier.ENTERPRISE, check_subscription=False)
        with pytest.raises(HTTPException) as exc:
            await gate(_request())

        assert exc.value.status_code == 403
        assert exc.value.detail["error"] == "tier_required"
        assert exc.value.detail["current_tier"] == "starter"
        assert exc.value.detail["required_tier"] == "enterprise"

    async def test_no_tenant_uses_settings_fallback(self) -> None:
        """Without a tenant, the STARTER fallback fails an ENTERPRISE gate."""
        gate = fg.TierGate(SubscriptionTier.ENTERPRISE)
        with pytest.raises(HTTPException) as exc:
            await gate(_request(tenant_id=None))
        assert exc.value.status_code == 403


# =============================================================================
# LimitChecker
# =============================================================================


class TestLimitChecker:
    async def test_under_limit_returns_usage_dict(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Below the tier limit, the checker returns usage accounting."""
        _patch_tier(monkeypatch, SubscriptionTier.STARTER)  # max_users = 3

        async def count_one(_request: Request) -> int:
            return 1

        checker = fg.LimitChecker("max_users", count_one)
        result = await checker(_request())

        assert result == {"current": 1, "maximum": 3, "remaining": 2, "tier": "starter"}

    async def test_at_limit_raises_structured_403(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Hitting the limit raises LimitExceededError with structured detail."""
        _patch_tier(monkeypatch, SubscriptionTier.STARTER)

        async def count_three(_request: Request) -> int:
            return 3

        checker = fg.LimitChecker("max_users", count_three)
        with pytest.raises(fg.LimitExceededError) as exc:
            await checker(_request())

        detail = exc.value.detail
        assert exc.value.status_code == 403
        assert detail["error"] == "limit_exceeded"
        assert detail["limit"] == "max_users"
        assert detail["current"] == 3
        assert detail["maximum"] == 3
        assert detail["tier"] == "starter"

    async def test_no_tenant_uses_settings_fallback(self) -> None:
        """Without a tenant, the STARTER limits apply."""

        async def count_zero(_request: Request) -> int:
            return 0

        checker = fg.LimitChecker("max_users", count_zero)
        result = await checker(_request(tenant_id=None))
        assert result["tier"] == "starter"
        assert result["current"] == 0


# =============================================================================
# require_feature / require_tier decorators
# =============================================================================


class TestRequireFeatureDecorator:
    async def test_request_in_args_uses_tenant_tier(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A positional Request is detected and the tenant tier allows access."""
        _patch_tier(monkeypatch, SubscriptionTier.ENTERPRISE)

        @fg.require_feature(ENTERPRISE_FEATURE)
        async def endpoint(request: Request) -> str:
            return "ok"

        assert await endpoint(_http_request(tenant_id=7)) == "ok"

    async def test_request_in_kwargs_denied_for_low_tier(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A kwargs request is detected and a low tier is denied."""
        _patch_tier(monkeypatch, SubscriptionTier.STARTER)

        @fg.require_feature(ENTERPRISE_FEATURE)
        async def endpoint(*, request: Request) -> str:
            return "ok"

        with pytest.raises(fg.FeatureNotAvailableError):
            await endpoint(request=_request(tenant_id=7))

    async def test_no_request_uses_settings_fallback(self) -> None:
        """Without any request, the settings fallback (STARTER) applies."""

        @fg.require_feature(ENTERPRISE_FEATURE)
        async def gated() -> str:
            return "ok"

        with pytest.raises(fg.FeatureNotAvailableError):
            await gated()

        @fg.require_feature(STARTER_FEATURE)
        async def open_endpoint() -> str:
            return "ok"

        assert await open_endpoint() == "ok"

    async def test_request_without_tenant_uses_settings_fallback(self) -> None:
        """A request lacking a tenant drops to the settings fallback."""

        @fg.require_feature(STARTER_FEATURE)
        async def endpoint(flag: int, request: Request) -> str:
            return "ok"

        # A non-Request positional arg precedes the Request (loop must skip it).
        assert await endpoint(1, _http_request()) == "ok"


class TestRequireTierDecorator:
    async def test_request_in_args_allows_sufficient_tier(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A positional Request with a sufficient tenant tier passes."""
        _patch_tier(monkeypatch, SubscriptionTier.ENTERPRISE)

        @fg.require_tier(SubscriptionTier.PROFESSIONAL)
        async def endpoint(request: Request) -> str:
            return "ok"

        assert await endpoint(_http_request(tenant_id=7)) == "ok"

    async def test_request_in_kwargs_denied_with_structured_403(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A kwargs request below the minimum tier gets a tier_required 403."""
        _patch_tier(monkeypatch, SubscriptionTier.STARTER)

        @fg.require_tier(SubscriptionTier.ENTERPRISE)
        async def endpoint(*, request: Request) -> str:
            return "ok"

        with pytest.raises(HTTPException) as exc:
            await endpoint(request=_request(tenant_id=7))
        assert exc.value.status_code == 403
        assert exc.value.detail["error"] == "tier_required"

    async def test_no_request_uses_settings_fallback(self) -> None:
        """Without any request, the STARTER fallback drives the check."""

        @fg.require_tier(SubscriptionTier.ENTERPRISE)
        async def gated() -> str:
            return "ok"

        with pytest.raises(HTTPException):
            await gated()

        @fg.require_tier(SubscriptionTier.STARTER)
        async def open_endpoint() -> str:
            return "ok"

        assert await open_endpoint() == "ok"

    async def test_request_without_tenant_uses_settings_fallback(self) -> None:
        """A request lacking a tenant drops to the settings fallback."""

        @fg.require_tier(SubscriptionTier.STARTER)
        async def endpoint(flag: int, request: Request) -> str:
            return "ok"

        assert await endpoint(1, _http_request()) == "ok"


# =============================================================================
# DB-backed get_tenant_tier
# =============================================================================


class TestGetTenantTier:
    @pytest.mark.parametrize(
        "plan,expected",
        [
            ("professional", SubscriptionTier.PROFESSIONAL),
            ("Enterprise", SubscriptionTier.ENTERPRISE),
            ("free", SubscriptionTier.STARTER),
            ("starter", SubscriptionTier.STARTER),
            ("bespoke-plan", SubscriptionTier.STARTER),
            (None, SubscriptionTier.STARTER),
        ],
    )
    async def test_plan_maps_to_tier(
        self,
        monkeypatch: pytest.MonkeyPatch,
        plan: Optional[str],
        expected: SubscriptionTier,
    ) -> None:
        """Tenant plan names map onto subscription tiers (STARTER default)."""
        _patch_db_plan(monkeypatch, plan)
        assert await fg.get_tenant_tier(1) == expected

    async def test_empty_session_falls_back_to_starter(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A session generator that yields nothing produces the safe default."""

        async def _empty_gen():
            if False:  # pragma: no cover - generator intentionally yields nothing
                yield None

        monkeypatch.setattr("app.db.session.get_async_session", _empty_gen)
        assert await fg.get_tenant_tier(1) == SubscriptionTier.STARTER


# =============================================================================
# *_for_tenant helpers & tier dependency
# =============================================================================


class TestTenantHelpers:
    async def test_check_feature_for_tenant(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Feature check reflects the tenant's tier."""
        _patch_tier(monkeypatch, SubscriptionTier.ENTERPRISE)
        assert await fg.check_feature_for_tenant(1, ENTERPRISE_FEATURE) is True

        _patch_tier(monkeypatch, SubscriptionTier.STARTER)
        assert await fg.check_feature_for_tenant(1, ENTERPRISE_FEATURE) is False

    async def test_check_limit_for_tenant(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Limit check reflects the tenant tier's limits (STARTER max_users=3)."""
        _patch_tier(monkeypatch, SubscriptionTier.STARTER)
        assert await fg.check_limit_for_tenant(1, "max_users", 2) is True
        assert await fg.check_limit_for_tenant(1, "max_users", 3) is False

    async def test_get_tier_features_for_tenant(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Tier info for a tenant includes tier, features, limits and pricing."""
        _patch_tier(monkeypatch, SubscriptionTier.PROFESSIONAL)
        info = await fg.get_tier_features_for_tenant(1)

        assert info["tier"] == "professional"
        assert "features" in info
        assert "limits" in info
        assert "pricing" in info

    async def test_get_current_tier_dependency_with_tenant(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The dependency resolves the tenant tier and caches it on the request."""
        _patch_tier(monkeypatch, SubscriptionTier.ENTERPRISE)
        request = _request()

        tier = await fg.get_current_tier_dependency(request)
        assert tier == SubscriptionTier.ENTERPRISE
        assert request.state.subscription_tier == "enterprise"

    async def test_get_current_tier_dependency_without_tenant(self) -> None:
        """Without a tenant, the settings fallback (STARTER) is returned."""
        tier = await fg.get_current_tier_dependency(_request(tenant_id=None))
        assert tier == SubscriptionTier.STARTER
