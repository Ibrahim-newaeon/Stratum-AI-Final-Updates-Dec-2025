# =============================================================================
# Stratum AI - API Key Authentication
# =============================================================================
"""
Inbound API-key authentication.

The platform mints API keys (CRUD in ``endpoints/api_keys.py``) but, prior to
this module, nothing ever *validated* an inbound key — `verify_api_key` had no
production callers, so keys authenticated nothing (audit P0-4).

`get_api_key_principal` is the missing validator: it reads the ``X-API-Key``
header, looks the SHA-256 hash up against active, non-expired keys, records
``last_used_at``, and populates tenant context for downstream middleware.
Apply it (or ``require_api_key_scope``) to any programmatic endpoint.
"""

from datetime import datetime, timezone
from typing import Annotated, Awaitable, Callable, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import hash_api_key
from app.db.session import get_async_session
from app.models import APIKey

logger = get_logger(__name__)

# Declared as a security scheme so it surfaces in the OpenAPI docs.
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class APIKeyPrincipal:
    """The authenticated identity behind a valid API key."""

    def __init__(self, api_key: APIKey):
        self.api_key = api_key
        self.id = api_key.id
        self.tenant_id = api_key.tenant_id
        self.user_id = api_key.user_id
        self.scopes = list(api_key.scopes or [])


async def get_api_key_principal(
    request: Request,
    presented_key: Annotated[Optional[str], Depends(api_key_header)],
    db: AsyncSession = Depends(get_async_session),
) -> APIKeyPrincipal:
    """
    Resolve the ``X-API-Key`` header to an authenticated principal.

    Raises 401 when the key is missing, unknown, inactive, or expired.
    """
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API key",
        headers={"WWW-Authenticate": "ApiKey"},
    )
    if not presented_key:
        raise invalid

    key_hash = hash_api_key(presented_key)
    result = await db.execute(select(APIKey).where(APIKey.key_hash == key_hash))
    record = result.scalar_one_or_none()

    if record is None or not record.is_active:
        raise invalid

    if record.expires_at is not None:
        expires_at = record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key has expired",
                headers={"WWW-Authenticate": "ApiKey"},
            )

    # Best-effort usage stamp — never fail auth on a write hiccup.
    try:
        record.last_used_at = datetime.now(timezone.utc)
        await db.commit()
    except Exception as exc:  # noqa: BLE001 - usage stamping must not block auth
        await db.rollback()
        logger.warning("api_key_last_used_update_failed", error=str(exc))

    # Populate request state for downstream middleware / audit logging.
    # /programmatic/* bypasses TenantMiddleware (it authenticates by API key, not
    # JWT), so this dependency is the single place tenant/role context is set for
    # those requests — mirror the fields TenantMiddleware would otherwise set so
    # shared services reading request.state.role / is_superadmin don't trip.
    request.state.tenant_id = record.tenant_id
    request.state.user_id = record.user_id
    request.state.role = "api_key"
    request.state.is_superadmin = False

    # Bind structured-logging context for parity with JWT-authenticated requests.
    import structlog

    structlog.contextvars.bind_contextvars(
        tenant_id=record.tenant_id,
        user_id=record.user_id,
        role="api_key",
    )

    return APIKeyPrincipal(record)


def require_api_key_scope(
    *required_scopes: str,
) -> Callable[..., Awaitable["APIKeyPrincipal"]]:
    """
    Dependency factory enforcing that the API key carries the given scope(s).

    An ``admin`` scope satisfies any requirement.
    """

    async def scope_checker(
        principal: Annotated[APIKeyPrincipal, Depends(get_api_key_principal)],
    ) -> APIKeyPrincipal:
        held = set(principal.scopes)
        if "admin" not in held and not set(required_scopes).issubset(held):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"API key missing required scope(s): {', '.join(required_scopes)}",
            )
        return principal

    return scope_checker


APIKeyPrincipalDep = Annotated[APIKeyPrincipal, Depends(get_api_key_principal)]
