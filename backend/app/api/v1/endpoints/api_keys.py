# =============================================================================
# Stratum AI - API Keys Management Endpoints
# =============================================================================
"""
CRUD operations for API keys:
- Create new API keys
- List API keys (masked)
- Regenerate API keys
- Delete API keys
"""

import hashlib
import secrets
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models import APIKey, User
from app.schemas.response import APIResponse

router = APIRouter(prefix="/api-keys", tags=["API Keys"])
logger = get_logger(__name__)


# =============================================================================
# Pydantic Schemas
# =============================================================================

class APIKeyCreateRequest(BaseModel):
    """Request to create a new API key."""
    name: str = Field(..., min_length=1, max_length=255, description="Friendly name for the key")
    scopes: List[str] = Field(default=["read"], description="Permission scopes")
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=365, description="Days until expiration")


class APIKeyResponse(BaseModel):
    """API key response (masked key)."""
    id: int
    name: str
    key_prefix: str
    masked_key: str
    scopes: List[str]
    is_active: bool
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime


class APIKeyCreatedResponse(BaseModel):
    """Response when creating a new API key (includes full key)."""
    id: int
    name: str
    key: str  # Full key - only shown once!
    key_prefix: str
    scopes: List[str]
    expires_at: Optional[datetime]
    created_at: datetime


class APIKeyRegenerateResponse(BaseModel):
    """Response when regenerating an API key."""
    id: int
    name: str
    key: str  # New full key - only shown once!
    key_prefix: str
    message: str


# =============================================================================
# Helper Functions
# =============================================================================

def generate_api_key(key_type: str = "live") -> tuple[str, str, str]:
    """
    Generate a new API key.
    Returns: (full_key, key_hash, key_prefix)
    """
    # Generate random key
    random_part = secrets.token_urlsafe(32)
    prefix = f"strat_{key_type}_"
    full_key = f"{prefix}{random_part}"

    # Hash for storage
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()

    return full_key, key_hash, prefix


def mask_key(prefix: str) -> str:
    """Create a masked version of the key for display."""
    return f"{prefix}{'•' * 28}..."


# =============================================================================
# Endpoints
# =============================================================================

@router.get("", response_model=APIResponse[List[APIKeyResponse]])
async def list_api_keys(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[List[APIKeyResponse]]:
    """
    List all API keys for the current user (masked).
    """
    user_id = getattr(request.state, "user_id", None)
    tenant_id = getattr(request.state, "tenant_id", None)

    if not user_id or not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    result = await db.execute(
        select(APIKey).where(
            and_(
                APIKey.user_id == user_id,
                APIKey.tenant_id == tenant_id,
            )
        ).order_by(APIKey.created_at.desc())
    )
    keys = result.scalars().all()

    return APIResponse(
        success=True,
        data=[
            APIKeyResponse(
                id=key.id,
                name=key.name,
                key_prefix=key.key_prefix,
                masked_key=mask_key(key.key_prefix),
                scopes=key.scopes or [],
                is_active=key.is_active,
                last_used_at=key.last_used_at,
                expires_at=key.expires_at,
                created_at=key.created_at,
            )
            for key in keys
        ],
    )


@router.post("", response_model=APIResponse[APIKeyCreatedResponse], status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: Request,
    body: APIKeyCreateRequest,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[APIKeyCreatedResponse]:
    """
    Create a new API key.

    IMPORTANT: The full key is only returned once. Store it securely.
    """
    user_id = getattr(request.state, "user_id", None)
    tenant_id = getattr(request.state, "tenant_id", None)

    if not user_id or not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    # Check existing key count (limit to 10 per user)
    result = await db.execute(
        select(APIKey).where(
            and_(
                APIKey.user_id == user_id,
                APIKey.tenant_id == tenant_id,
                APIKey.is_active == True,
            )
        )
    )
    existing_count = len(result.scalars().all())
    if existing_count >= 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum of 10 active API keys allowed per user",
        )

    # Generate key
    full_key, key_hash, key_prefix = generate_api_key("live")

    # Calculate expiration
    expires_at = None
    if body.expires_in_days:
        from datetime import timedelta
        expires_at = datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)

    # Create database record
    api_key = APIKey(
        user_id=user_id,
        tenant_id=tenant_id,
        name=body.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        scopes=body.scopes,
        expires_at=expires_at,
        is_active=True,
    )

    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    logger.info(f"API key created: {api_key.id} for user {user_id}")

    return APIResponse(
        success=True,
        data=APIKeyCreatedResponse(
            id=api_key.id,
            name=api_key.name,
            key=full_key,
            key_prefix=key_prefix,
            scopes=api_key.scopes or [],
            expires_at=api_key.expires_at,
            created_at=api_key.created_at,
        ),
        message="API key created. Store this key securely - it won't be shown again.",
    )


@router.post("/{key_id}/regenerate", response_model=APIResponse[APIKeyRegenerateResponse])
async def regenerate_api_key(
    request: Request,
    key_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[APIKeyRegenerateResponse]:
    """
    Regenerate an API key. The old key will be invalidated immediately.
    """
    user_id = getattr(request.state, "user_id", None)
    tenant_id = getattr(request.state, "tenant_id", None)

    if not user_id or not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    # Find the key
    result = await db.execute(
        select(APIKey).where(
            and_(
                APIKey.id == key_id,
                APIKey.user_id == user_id,
                APIKey.tenant_id == tenant_id,
            )
        )
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    # Generate new key
    full_key, key_hash, key_prefix = generate_api_key("live")

    # Update the record
    api_key.key_hash = key_hash
    api_key.key_prefix = key_prefix
    api_key.is_active = True

    await db.commit()
    await db.refresh(api_key)

    logger.info(f"API key regenerated: {api_key.id}")

    return APIResponse(
        success=True,
        data=APIKeyRegenerateResponse(
            id=api_key.id,
            name=api_key.name,
            key=full_key,
            key_prefix=key_prefix,
            message="API key regenerated. Update your integrations with the new key.",
        ),
    )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    request: Request,
    key_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """
    Delete (revoke) an API key.
    """
    user_id = getattr(request.state, "user_id", None)
    tenant_id = getattr(request.state, "tenant_id", None)

    if not user_id or not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    # Find the key
    result = await db.execute(
        select(APIKey).where(
            and_(
                APIKey.id == key_id,
                APIKey.user_id == user_id,
                APIKey.tenant_id == tenant_id,
            )
        )
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    await db.delete(api_key)
    await db.commit()

    logger.info(f"API key deleted: {key_id}")


@router.patch("/{key_id}/deactivate", response_model=APIResponse[APIKeyResponse])
async def deactivate_api_key(
    request: Request,
    key_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[APIKeyResponse]:
    """
    Deactivate an API key without deleting it.
    """
    user_id = getattr(request.state, "user_id", None)
    tenant_id = getattr(request.state, "tenant_id", None)

    if not user_id or not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    result = await db.execute(
        select(APIKey).where(
            and_(
                APIKey.id == key_id,
                APIKey.user_id == user_id,
                APIKey.tenant_id == tenant_id,
            )
        )
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    api_key.is_active = False
    await db.commit()
    await db.refresh(api_key)

    return APIResponse(
        success=True,
        data=APIKeyResponse(
            id=api_key.id,
            name=api_key.name,
            key_prefix=api_key.key_prefix,
            masked_key=mask_key(api_key.key_prefix),
            scopes=api_key.scopes or [],
            is_active=api_key.is_active,
            last_used_at=api_key.last_used_at,
            expires_at=api_key.expires_at,
            created_at=api_key.created_at,
        ),
        message="API key deactivated",
    )
