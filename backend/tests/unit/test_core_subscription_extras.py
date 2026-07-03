# =============================================================================
# Stratum AI - Subscription (DB & dependency paths) Unit Tests
# =============================================================================
"""Unit tests for the DB-backed and FastAPI-dependency paths of
``app.core.subscription``.

Complements ``test_subscription_logic.py`` (pure status math). Covers:

- ``SubscriptionInfo.to_dict`` serialization (datetimes, trial fields)
- ``get_expiry_warning_message`` for every status branch
- ``get_subscription_info`` (mocked session): tenant-not-found, active,
  naive datetimes, trial detection, grace period, fully expired
- ``check_subscription_valid`` raise / no-raise paths
- ``SubscriptionRequired`` / ``SubscriptionWarning`` /
  ``get_subscription_dependency``
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.core import subscription as sub
from app.core.subscription import (
    SubscriptionInfo,
    SubscriptionRequired,
    SubscriptionStatus,
    SubscriptionWarning,
    check_subscription_valid,
    get_expiry_warning_message,
    get_subscription_dependency,
    get_subscription_info,
)
from app.core.tiers import SubscriptionTier

pytestmark = pytest.mark.unit


# =============================================================================
# Helpers
# =============================================================================


def _info(
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
    restricted: bool = False,
    **overrides,
) -> SubscriptionInfo:
    """Build a SubscriptionInfo with sensible defaults."""
    defaults = dict(
        tenant_id=1,
        plan="professional",
        tier=SubscriptionTier.PROFESSIONAL,
        status=status,
        expires_at=None,
        days_until_expiry=None,
        days_in_grace=None,
        is_access_restricted=restricted,
        restriction_reason="restricted" if restricted else None,
    )
    defaults.update(overrides)
    return SubscriptionInfo(**defaults)


def _request(tenant_id: Optional[int] = 5) -> SimpleNamespace:
    """Fake request with a mutable state namespace."""
    state = SimpleNamespace()
    if tenant_id is not None:
        state.tenant_id = tenant_id
    return SimpleNamespace(state=state)


def _patch_db_row(
    monkeypatch: pytest.MonkeyPatch,
    row: Optional[tuple],
    tier: SubscriptionTier = SubscriptionTier.PROFESSIONAL,
) -> None:
    """Patch the session generator and tier lookup used by get_subscription_info."""
    session = AsyncMock()
    result = MagicMock()
    result.one_or_none.return_value = row
    session.execute = AsyncMock(return_value=result)

    async def _gen():
        yield session

    monkeypatch.setattr("app.db.session.get_async_session", _gen)
    monkeypatch.setattr(
        "app.core.feature_gate.get_tenant_tier", AsyncMock(return_value=tier)
    )


def _patch_sub_info(monkeypatch: pytest.MonkeyPatch, info: SubscriptionInfo) -> None:
    """Patch the module-level get_subscription_info used by the dependencies."""
    monkeypatch.setattr(sub, "get_subscription_info", AsyncMock(return_value=info))


# =============================================================================
# SubscriptionInfo.to_dict
# =============================================================================


class TestToDict:
    def test_serializes_datetimes_to_isoformat(self) -> None:
        """Datetime fields serialize to ISO strings; enums to their values."""
        expires = datetime(2026, 8, 1, tzinfo=UTC)
        trial = datetime(2026, 7, 15, tzinfo=UTC)
        info = _info(
            expires_at=expires,
            trial_ends_at=trial,
            is_trial=True,
            days_until_expiry=29,
        )

        data = info.to_dict()

        assert data["tenant_id"] == 1
        assert data["plan"] == "professional"
        assert data["tier"] == "professional"
        assert data["status"] == "active"
        assert data["expires_at"] == expires.isoformat()
        assert data["trial_ends_at"] == trial.isoformat()
        assert data["is_trial"] is True
        assert data["days_until_expiry"] == 29

    def test_none_datetimes_serialize_to_none(self) -> None:
        """Absent datetimes stay None; trial defaults are falsy."""
        data = _info().to_dict()

        assert data["expires_at"] is None
        assert data["trial_ends_at"] is None
        assert data["is_trial"] is False
        assert data["is_access_restricted"] is False
        assert data["restriction_reason"] is None


# =============================================================================
# get_expiry_warning_message
# =============================================================================


class TestExpiryWarningMessage:
    def test_expiring_soon_mentions_days_left(self) -> None:
        """Expiring-soon warnings state the days until expiry."""
        msg = get_expiry_warning_message(
            _info(SubscriptionStatus.EXPIRING_SOON, days_until_expiry=5)
        )
        assert msg is not None
        assert "5 days" in msg

    def test_grace_period_mentions_remaining_days(self) -> None:
        """Grace-period warnings state the remaining renewal window."""
        msg = get_expiry_warning_message(
            _info(SubscriptionStatus.GRACE_PERIOD, days_in_grace=2)
        )
        assert msg is not None
        assert "5 days" in msg  # GRACE_PERIOD_DAYS(7) - 2

    def test_grace_period_handles_missing_days(self) -> None:
        """A None days_in_grace is treated as zero days consumed."""
        msg = get_expiry_warning_message(
            _info(SubscriptionStatus.GRACE_PERIOD, days_in_grace=None)
        )
        assert msg is not None
        assert "7 days" in msg

    def test_expired_message(self) -> None:
        """Expired subscriptions get a renewal prompt."""
        msg = get_expiry_warning_message(_info(SubscriptionStatus.EXPIRED))
        assert msg is not None
        assert "expired" in msg.lower()

    @pytest.mark.parametrize(
        "status", [SubscriptionStatus.ACTIVE, SubscriptionStatus.FREE]
    )
    def test_healthy_statuses_have_no_warning(self, status: SubscriptionStatus) -> None:
        """Healthy statuses produce no warning."""
        assert get_expiry_warning_message(_info(status)) is None


# =============================================================================
# get_subscription_info (mocked DB)
# =============================================================================


class TestGetSubscriptionInfo:
    async def test_tenant_not_found_returns_restricted_expired(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A missing tenant yields an EXPIRED, access-restricted info."""
        _patch_db_row(monkeypatch, None)

        info = await get_subscription_info(999)

        assert info.status == SubscriptionStatus.EXPIRED
        assert info.is_access_restricted is True
        assert info.restriction_reason == "Tenant not found"
        assert info.tier == SubscriptionTier.STARTER

    async def test_active_paid_plan(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A far-future expiry yields ACTIVE with no restriction or trial."""
        expires = datetime.now(UTC) + timedelta(days=60)
        _patch_db_row(monkeypatch, ("professional", expires, None))

        info = await get_subscription_info(1)

        assert info.status == SubscriptionStatus.ACTIVE
        assert info.is_access_restricted is False
        assert info.restriction_reason is None
        assert info.is_trial is False
        assert info.tier == SubscriptionTier.PROFESSIONAL
        assert info.days_until_expiry in (59, 60)

    async def test_naive_expiry_is_coerced_to_utc(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A timezone-naive expiry datetime is treated as UTC, not an error."""
        naive_expires = (datetime.now(UTC) + timedelta(days=60)).replace(tzinfo=None)
        _patch_db_row(monkeypatch, ("professional", naive_expires, None))

        info = await get_subscription_info(1)
        assert info.status == SubscriptionStatus.ACTIVE

    async def test_future_trial_sets_is_trial(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An aware, future trial_ends_at marks the tenant as trialing."""
        trial_ends = datetime.now(UTC) + timedelta(days=10)
        _patch_db_row(monkeypatch, ("professional", None, trial_ends))

        info = await get_subscription_info(1)
        assert info.is_trial is True
        assert info.trial_ends_at == trial_ends

    async def test_naive_future_trial_sets_is_trial(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A naive future trial_ends_at is coerced to UTC and still counts."""
        naive_trial = (datetime.now(UTC) + timedelta(days=10)).replace(tzinfo=None)
        _patch_db_row(monkeypatch, ("professional", None, naive_trial))

        info = await get_subscription_info(1)
        assert info.is_trial is True

    async def test_past_trial_is_not_a_trial(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An elapsed trial_ends_at does not mark the tenant as trialing."""
        past_trial = datetime.now(UTC) - timedelta(days=3)
        _patch_db_row(monkeypatch, ("professional", None, past_trial))

        info = await get_subscription_info(1)
        assert info.is_trial is False

    async def test_grace_period_allows_access_with_reason(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Within the 7-day grace window, access stays open with a warning."""
        expires = datetime.now(UTC) - timedelta(days=2, hours=23)
        _patch_db_row(monkeypatch, ("professional", expires, None))

        info = await get_subscription_info(1)

        assert info.status == SubscriptionStatus.GRACE_PERIOD
        assert info.is_access_restricted is False
        assert info.restriction_reason is not None
        assert "grace" in info.restriction_reason.lower()

    async def test_fully_expired_restricts_access(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Past the grace window, access is restricted with a renewal reason."""
        expires = datetime.now(UTC) - timedelta(days=30)
        _patch_db_row(monkeypatch, ("professional", expires, None))

        info = await get_subscription_info(1)

        assert info.status == SubscriptionStatus.EXPIRED
        assert info.is_access_restricted is True
        assert info.restriction_reason is not None
        assert "expired" in info.restriction_reason.lower()

    async def test_empty_session_returns_restricted_fallback(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A session generator that yields nothing produces the safe fallback."""

        async def _empty_gen():
            if False:  # pragma: no cover - generator intentionally yields nothing
                yield None

        monkeypatch.setattr("app.db.session.get_async_session", _empty_gen)

        info = await get_subscription_info(1)

        assert info.status == SubscriptionStatus.EXPIRED
        assert info.is_access_restricted is True
        assert info.restriction_reason == "Could not retrieve subscription info"


# =============================================================================
# check_subscription_valid
# =============================================================================


class TestCheckSubscriptionValid:
    async def test_restricted_raises_402(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A restricted subscription raises a structured 402."""
        _patch_sub_info(monkeypatch, _info(SubscriptionStatus.EXPIRED, restricted=True))

        with pytest.raises(HTTPException) as exc:
            await check_subscription_valid(1)

        assert exc.value.status_code == 402
        assert exc.value.detail["error"] == "subscription_expired"
        assert exc.value.detail["renew_url"] == "/settings/billing"

    async def test_restricted_without_raise_returns_info(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """raise_on_invalid=False returns the info instead of raising."""
        info = _info(SubscriptionStatus.EXPIRED, restricted=True)
        _patch_sub_info(monkeypatch, info)

        assert await check_subscription_valid(1, raise_on_invalid=False) is info

    async def test_valid_subscription_passes_through(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A valid subscription is returned untouched."""
        info = _info(SubscriptionStatus.ACTIVE)
        _patch_sub_info(monkeypatch, info)

        assert await check_subscription_valid(1) is info


# =============================================================================
# FastAPI dependencies
# =============================================================================


class TestSubscriptionRequired:
    async def test_missing_tenant_raises_401(self) -> None:
        """No tenant in request state means the caller is unauthenticated."""
        dep = SubscriptionRequired()
        with pytest.raises(HTTPException) as exc:
            await dep(_request(tenant_id=None))
        assert exc.value.status_code == 401

    async def test_expired_raises_402(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """An expired subscription is rejected with a structured 402."""
        _patch_sub_info(monkeypatch, _info(SubscriptionStatus.EXPIRED))

        dep = SubscriptionRequired()
        with pytest.raises(HTTPException) as exc:
            await dep(_request())
        assert exc.value.status_code == 402
        assert exc.value.detail["error"] == "subscription_expired"

    async def test_grace_period_blocked_when_grace_disallowed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """allow_grace=False rejects grace-period tenants."""
        _patch_sub_info(monkeypatch, _info(SubscriptionStatus.GRACE_PERIOD))

        dep = SubscriptionRequired(allow_grace=False)
        with pytest.raises(HTTPException) as exc:
            await dep(_request())
        assert exc.value.status_code == 402

    async def test_grace_period_allowed_by_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The default allows grace-period access and stores state."""
        info = _info(SubscriptionStatus.GRACE_PERIOD)
        _patch_sub_info(monkeypatch, info)
        request = _request()

        result = await SubscriptionRequired()(request)
        assert result is info
        assert request.state.subscription_info is info

    async def test_active_returns_info(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """An active subscription passes and is stored on the request."""
        info = _info(SubscriptionStatus.ACTIVE)
        _patch_sub_info(monkeypatch, info)
        request = _request()

        assert await SubscriptionRequired()(request) is info
        assert request.state.subscription_info is info


class TestSubscriptionWarning:
    async def test_missing_tenant_returns_none(self) -> None:
        """Warning dependency never blocks anonymous requests."""
        assert await SubscriptionWarning()(_request(tenant_id=None)) is None

    async def test_returns_info_and_stores_state(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Warning dependency returns info without blocking expired tenants."""
        info = _info(SubscriptionStatus.EXPIRED, restricted=True)
        _patch_sub_info(monkeypatch, info)
        request = _request()

        assert await SubscriptionWarning()(request) is info
        assert request.state.subscription_info is info


class TestGetSubscriptionDependency:
    async def test_missing_tenant_returns_none(self) -> None:
        """No tenant means no subscription info."""
        assert await get_subscription_dependency(_request(tenant_id=None)) is None

    async def test_returns_info_for_tenant(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A tenant's info is returned without side effects."""
        info = _info(SubscriptionStatus.ACTIVE)
        _patch_sub_info(monkeypatch, info)

        assert await get_subscription_dependency(_request()) is info
