# =============================================================================
# Stratum AI - Embed Widget Tier Resolution
# =============================================================================
"""embed_widgets must read the caller's tier, not a process-wide default.

Every tier decision in embed_widgets.py went through `get_current_tier()`,
whose own docstring marks it DEPRECATED and which resolves:

    tier_value = getattr(settings, "subscription_tier", "starter")

`subscription_tier` is not defined on Settings anywhere in the codebase, so
the fallback was the only path and every tenant resolved to STARTER. Confirmed
against the running production container before the fix:

    get_current_tier() -> starter

That is wrong in both directions. STARTER *has* EMBED_WIDGETS_BASIC, so the
feature check in create_widget passed for tenants who had not paid for it;
STARTER *lacks* EMBED_WIDGETS_WHITELABEL, so Enterprise customers were handed
starter branding and starter limits on the white-label feature they bought.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.feature_gate import get_tenant_tier
from app.core.tiers import SubscriptionTier

pytestmark = pytest.mark.asyncio


def _db_returning_plan(plan):
    """AsyncSession double whose single scalar result is `plan`."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = plan
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result)
    return db


class TestTierFollowsTheTenantRow:
    @pytest.mark.parametrize(
        "plan,expected",
        [
            ("enterprise", SubscriptionTier.ENTERPRISE),
            ("professional", SubscriptionTier.PROFESSIONAL),
            ("starter", SubscriptionTier.STARTER),
            ("free", SubscriptionTier.STARTER),
            ("ENTERPRISE", SubscriptionTier.ENTERPRISE),
        ],
    )
    async def test_plan_maps_to_tier(self, plan, expected):
        tier = await get_tenant_tier(1, db=_db_returning_plan(plan))
        assert tier is expected

    async def test_unknown_plan_falls_back_to_starter(self):
        tier = await get_tenant_tier(1, db=_db_returning_plan("platinum"))
        assert tier is SubscriptionTier.STARTER

    async def test_missing_tenant_falls_back_to_starter(self):
        """A soft-deleted or absent tenant is excluded by the query."""
        tier = await get_tenant_tier(1, db=_db_returning_plan(None))
        assert tier is SubscriptionTier.STARTER

    async def test_two_tenants_get_different_answers(self):
        """The regression this suite exists for.

        With the deprecated global fallback these two calls returned the same
        tier regardless of the tenants' plans.
        """
        enterprise = await get_tenant_tier(1, db=_db_returning_plan("enterprise"))
        free = await get_tenant_tier(2, db=_db_returning_plan("free"))
        assert enterprise is SubscriptionTier.ENTERPRISE
        assert free is SubscriptionTier.STARTER
        assert enterprise is not free


class TestEndpointsAskForTheCallersTier:
    """The endpoint must resolve tier from the authenticated tenant."""

    async def test_tier_info_uses_the_callers_tenant(
        self, api_client, admin_headers, monkeypatch
    ):
        seen = {}

        async def fake_get_tenant_tier(tenant_id, db=None):
            seen["tenant_id"] = tenant_id
            return SubscriptionTier.ENTERPRISE

        monkeypatch.setattr(
            "app.api.v1.endpoints.embed_widgets.get_tenant_tier",
            fake_get_tenant_tier,
        )

        resp = await api_client.get(
            "/api/v1/embed-widgets/tier-info", headers=admin_headers
        )

        assert resp.status_code == 200, resp.text
        # admin_headers is minted for tenant_id=1.
        assert seen.get("tenant_id") == 1
        body = resp.json()
        assert body["tier"] == SubscriptionTier.ENTERPRISE.value
        # Enterprise is the white-label tier; starter would report "full".
        assert body["branding_level"] == "none"
        assert body["features"]["white_label"] is True


class TestDeprecatedGlobalIsGone:
    """embed_widgets must not reach for the settings fallback again.

    Pinned as an import-level assertion rather than a behavioural one because
    the failure mode is silent: `get_current_tier()` returns a valid tier, so
    nothing errors — every tenant simply gets the same one.
    """

    def test_module_does_not_import_get_current_tier(self):
        import app.api.v1.endpoints.embed_widgets as mod

        assert not hasattr(mod, "get_current_tier"), (
            "embed_widgets imported get_current_tier again; it resolves a "
            "setting that does not exist and answers STARTER for everyone"
        )
        assert hasattr(mod, "get_tenant_tier")


class TestSettingIsStillUndefined:
    """The root cause, asserted so it is not mistaken for configuration.

    get_current_tier() reads `settings.subscription_tier` via getattr with a
    "starter" default. No such field exists on Settings, so the default is the
    only path it ever takes. If someone later adds the field, this test fails
    and the fallback's behaviour should be re-examined.
    """

    def test_settings_has_no_subscription_tier(self):
        from app.core.config import settings

        assert not hasattr(settings, "subscription_tier")
