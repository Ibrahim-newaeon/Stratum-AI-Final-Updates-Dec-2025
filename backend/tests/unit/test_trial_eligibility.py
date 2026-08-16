# =============================================================================
# Stratum AI - Trial Eligibility
# =============================================================================
"""One trial per tenant, fixed at 14 days.

trial_days was a request field:

    trial_days: int = Field(default=14, ge=0, le=30)

so the caller chose its own trial length, and nothing anywhere recorded that a
tenant had already had one. Cancel, resubscribe, take another 30 days —
indefinitely.

It was worse than repeatable. Registration already grants a trial
(auth.py sets trial_ends_at = now + 14 days on signup), so checkout was
handing every signed-up tenant a *second* trial on top of the one they had.

trial_ends_at is the record that a trial was granted. It is never cleared, so
it stays truthy once the trial ends — which is exactly what makes
cancel-and-resubscribe stop working.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.api.v1.endpoints.payments import (
    TRIAL_PERIOD_DAYS,
    CreateCheckoutRequest,
    _trial_days_for_tenant,
)


class _Tenant:
    def __init__(self, trial_ends_at=None):
        self.trial_ends_at = trial_ends_at


class TestEligibility:
    def test_tenant_that_never_trialled_gets_the_fixed_period(self):
        assert _trial_days_for_tenant(_Tenant(None)) == TRIAL_PERIOD_DAYS
        assert TRIAL_PERIOD_DAYS == 14

    def test_tenant_from_signup_gets_none(self):
        """Signup already set trial_ends_at, so checkout adds nothing."""
        future = datetime.now(UTC) + timedelta(days=14)
        assert _trial_days_for_tenant(_Tenant(future)) == 0

    def test_expired_trial_still_counts_as_used(self):
        """The regression this exists for.

        An expired trial is still a used trial — otherwise cancelling and
        resubscribing after it lapsed would hand out a fresh one.
        """
        past = datetime.now(UTC) - timedelta(days=365)
        assert _trial_days_for_tenant(_Tenant(past)) == 0

    def test_eligibility_does_not_depend_on_when_the_trial_ended(self):
        for offset in (-3650, -30, -1, 0, 1, 30, 3650):
            when = datetime.now(UTC) + timedelta(days=offset)
            assert _trial_days_for_tenant(_Tenant(when)) == 0, offset


class TestTrialLengthIsNotCallerControlled:
    def test_request_model_rejects_trial_days(self):
        """A client sending the old field must not silently get its way."""
        body = CreateCheckoutRequest(
            tier="starter",
            success_url="https://app.stratumai.app/ok",
            cancel_url="https://app.stratumai.app/no",
            trial_days=30,
        )
        assert not hasattr(body, "trial_days"), (
            "trial_days is back on the request model; trial length is a "
            "server decision, not a caller's"
        )

    def test_valid_request_still_builds(self):
        body = CreateCheckoutRequest(
            tier="professional",
            success_url="https://app.stratumai.app/ok",
            cancel_url="https://app.stratumai.app/no",
        )
        assert body.tier == "professional"
