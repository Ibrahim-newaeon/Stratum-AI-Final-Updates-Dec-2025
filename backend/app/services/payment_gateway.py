# =============================================================================
# Stratum AI - Payment Gateway Selection
# =============================================================================
"""
One place that answers "which payment gateway is active".

``stripe_service`` and ``paddle_service`` expose the same function names and
the same dataclass shapes, plus a small set of aliases (``GATEWAY_NAME``,
``CONFIGURED``, ``TENANT_CUSTOMER_FIELD``, ``sync_tenant_customer``) that
normalise the places where they genuinely differ. That makes them
interchangeable, and this module is what does the choosing.

``payments.py`` therefore contains no ``if settings.payment_gateway ==`` branch:
it resolves the gateway once per request and calls it. Switching gateways is a
config change plus a restart, and switching back is the same change reversed —
which is the property that makes the migration off Stripe safe to attempt.

The choice is read per call rather than captured at import, so a test can
monkeypatch ``settings.payment_gateway`` without reloading modules.
"""

from types import ModuleType

from app.core.config import settings
from app.core.logging import get_logger
from app.services import paddle_service, stripe_service

logger = get_logger(__name__)

_GATEWAYS: dict[str, ModuleType] = {
    "stripe": stripe_service,
    "paddle": paddle_service,
}


def get_gateway() -> ModuleType:
    """
    Return the active payment gateway module.

    Falls back to Stripe if ``settings.payment_gateway`` names something
    unknown. Pydantic's Literal already rejects that at startup, so this branch
    is unreachable in normal operation; it exists so a mangled override degrades
    to the incumbent gateway rather than raising KeyError on every billing
    request.
    """
    name = settings.payment_gateway
    gateway = _GATEWAYS.get(name)
    if gateway is None:
        logger.error(
            "payment_gateway_unknown",
            configured=name,
            detail="falling back to stripe",
        )
        return stripe_service
    return gateway


def get_tenant_customer_id(tenant) -> str | None:
    """
    Read the tenant's customer ID for whichever gateway is active.

    Tenants carry both ``stripe_customer_id`` and ``paddle_customer_id``; which
    one is meaningful depends on the active gateway, and reading the wrong one
    would either create a duplicate customer or bill against the wrong account.
    """
    return getattr(tenant, get_gateway().TENANT_CUSTOMER_FIELD, None)
