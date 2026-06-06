# =============================================================================
# Stratum AI - Programmatic API (API-key authenticated)
# =============================================================================
"""
Endpoints authenticated by an inbound API key (``X-API-Key`` header) rather
than a user JWT. This is the surface third-party/server-side integrations use.

``GET /programmatic/whoami`` is the canonical "is my key valid?" check and the
first endpoint that actually authenticates an API key (closing audit P0-4).
Additional programmatic endpoints can adopt ``APIKeyPrincipalDep`` /
``require_api_key_scope(...)`` as the product surface grows.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.auth.api_key import APIKeyPrincipalDep
from app.schemas.response import APIResponse

router = APIRouter(prefix="/programmatic", tags=["Programmatic API"])


class APIKeyIdentity(BaseModel):
    """Identity resolved from a valid API key."""

    key_id: int
    tenant_id: int
    user_id: int
    scopes: list[str]


@router.get("/whoami", response_model=APIResponse[APIKeyIdentity])
async def whoami(principal: APIKeyPrincipalDep) -> APIResponse[APIKeyIdentity]:
    """Return the identity behind the presented ``X-API-Key``."""
    return APIResponse(
        success=True,
        data=APIKeyIdentity(
            key_id=principal.id,
            tenant_id=principal.tenant_id,
            user_id=principal.user_id,
            scopes=principal.scopes,
        ),
    )
