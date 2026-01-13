# =============================================================================
# Stratum AI - CDP API Endpoints
# =============================================================================
"""
CDP (Customer Data Platform) API endpoints.

Endpoints:
- POST /events - Ingest events (single or batch)
- GET /profiles/{profile_id} - Get profile by ID
- GET /profiles - Lookup profile by identifier
- GET /sources - List data sources
- POST /sources - Create data source

Security features:
- Rate limiting on all endpoints
- Source key authentication for event ingestion
- Tenant isolation on all operations
"""

import hashlib
import secrets
import time
import threading
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.deps import get_current_user
from app.db.session import get_async_session
from app.models.cdp import (
    CDPSource,
    CDPProfile,
    CDPProfileIdentifier,
    CDPEvent,
    CDPConsent,
    CDPWebhook,
    IdentifierType,
    LifecycleStage,
)
from app.schemas.cdp import (
    EventBatchInput,
    EventBatchResponse,
    EventIngestResult,
    ProfileResponse,
    ProfileListResponse,
    SourceCreate,
    SourceResponse,
    SourceListResponse,
    ConsentUpdate,
    ConsentResponse,
    IdentifierResponse,
    WebhookCreate,
    WebhookUpdate,
    WebhookResponse,
    WebhookListResponse,
    WebhookTestResult,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/cdp", tags=["CDP"])


# =============================================================================
# Rate Limiting
# =============================================================================

class RateLimiter:
    """Simple in-memory rate limiter for API protection."""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed under rate limit."""
        now = time.time()
        window_start = now - 60  # 1 minute window

        with self._lock:
            # Clean old entries
            self.requests[key] = [t for t in self.requests[key] if t > window_start]

            if len(self.requests[key]) >= self.requests_per_minute:
                return False

            self.requests[key].append(now)
            return True


# Rate limiters for different operation types
_event_limiter = RateLimiter(requests_per_minute=100)   # Events: 100/min (batch allowed)
_profile_limiter = RateLimiter(requests_per_minute=300)  # Profile reads: 300/min
_source_limiter = RateLimiter(requests_per_minute=30)    # Source ops: 30/min
_webhook_limiter = RateLimiter(requests_per_minute=30)   # Webhook ops: 30/min


# =============================================================================
# Profile Caching
# =============================================================================

class ProfileCache:
    """
    Simple in-memory cache for CDP profiles with TTL.

    Caches profile responses to reduce database load for repeated lookups.
    Cache is automatically cleared when profiles are updated through events.
    """

    DEFAULT_TTL = 60  # 60 seconds
    MAX_SIZE = 10000  # Maximum cache entries per tenant

    def __init__(self, ttl_seconds: int = DEFAULT_TTL):
        self.ttl = ttl_seconds
        self.cache: Dict[str, tuple[float, Any]] = {}  # key -> (expiry_time, value)
        self._lock = threading.Lock()

    def _make_key(self, tenant_id: int, profile_id: str) -> str:
        """Create cache key from tenant_id and profile_id."""
        return f"profile:{tenant_id}:{profile_id}"

    def _make_lookup_key(self, tenant_id: int, ident_type: str, ident_hash: str) -> str:
        """Create cache key for identifier lookups."""
        return f"lookup:{tenant_id}:{ident_type}:{ident_hash}"

    def get(self, tenant_id: int, profile_id: str) -> Optional[Any]:
        """Get cached profile if not expired."""
        key = self._make_key(tenant_id, profile_id)
        with self._lock:
            if key in self.cache:
                expiry, value = self.cache[key]
                if time.time() < expiry:
                    return value
                # Expired, remove it
                del self.cache[key]
        return None

    def get_by_lookup(self, tenant_id: int, ident_type: str, ident_hash: str) -> Optional[Any]:
        """Get cached profile by identifier lookup."""
        key = self._make_lookup_key(tenant_id, ident_type, ident_hash)
        with self._lock:
            if key in self.cache:
                expiry, value = self.cache[key]
                if time.time() < expiry:
                    return value
                del self.cache[key]
        return None

    def set(self, tenant_id: int, profile_id: str, value: Any) -> None:
        """Cache a profile response."""
        key = self._make_key(tenant_id, profile_id)
        with self._lock:
            # Clean expired entries if cache is getting large
            if len(self.cache) > self.MAX_SIZE:
                self._cleanup_expired()
            self.cache[key] = (time.time() + self.ttl, value)

    def set_by_lookup(self, tenant_id: int, ident_type: str, ident_hash: str, value: Any) -> None:
        """Cache a profile for identifier lookup."""
        key = self._make_lookup_key(tenant_id, ident_type, ident_hash)
        with self._lock:
            if len(self.cache) > self.MAX_SIZE:
                self._cleanup_expired()
            self.cache[key] = (time.time() + self.ttl, value)

    def invalidate(self, tenant_id: int, profile_id: str) -> None:
        """Invalidate cache for a specific profile."""
        key = self._make_key(tenant_id, profile_id)
        with self._lock:
            self.cache.pop(key, None)
            # Also clear any lookup keys pointing to this profile
            # This is approximate - we can't track all lookup keys for a profile
            # without additional overhead, so we rely on TTL for those

    def invalidate_tenant(self, tenant_id: int) -> None:
        """Invalidate all cached profiles for a tenant."""
        prefix = f"profile:{tenant_id}:"
        lookup_prefix = f"lookup:{tenant_id}:"
        with self._lock:
            keys_to_delete = [
                k for k in self.cache
                if k.startswith(prefix) or k.startswith(lookup_prefix)
            ]
            for k in keys_to_delete:
                del self.cache[k]

    def _cleanup_expired(self) -> None:
        """Remove expired entries. Must be called with lock held."""
        now = time.time()
        expired = [k for k, (exp, _) in self.cache.items() if now >= exp]
        for k in expired:
            del self.cache[k]


# Global profile cache instance
_profile_cache = ProfileCache(ttl_seconds=60)


async def check_event_rate_limit(
    current_user = Depends(get_current_user),
):
    """Rate limit for event ingestion."""
    key = f"{current_user.tenant_id}:events"
    if not _event_limiter.is_allowed(key):
        logger.warning(
            "cdp_rate_limit_exceeded",
            operation="events",
            tenant_id=current_user.tenant_id,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for event ingestion. Max 100 requests/minute.",
            headers={"Retry-After": "60"},
        )


async def check_profile_rate_limit(
    current_user = Depends(get_current_user),
):
    """Rate limit for profile lookups."""
    key = f"{current_user.tenant_id}:profiles"
    if not _profile_limiter.is_allowed(key):
        logger.warning(
            "cdp_rate_limit_exceeded",
            operation="profiles",
            tenant_id=current_user.tenant_id,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for profile lookups. Max 300 requests/minute.",
            headers={"Retry-After": "60"},
        )


async def check_source_rate_limit(
    current_user = Depends(get_current_user),
):
    """Rate limit for source operations."""
    key = f"{current_user.tenant_id}:sources"
    if not _source_limiter.is_allowed(key):
        logger.warning(
            "cdp_rate_limit_exceeded",
            operation="sources",
            tenant_id=current_user.tenant_id,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for source operations. Max 30 requests/minute.",
            headers={"Retry-After": "60"},
        )


async def check_webhook_rate_limit(
    current_user = Depends(get_current_user),
):
    """Rate limit for webhook operations."""
    key = f"{current_user.tenant_id}:webhooks"
    if not _webhook_limiter.is_allowed(key):
        logger.warning(
            "cdp_rate_limit_exceeded",
            operation="webhooks",
            tenant_id=current_user.tenant_id,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for webhook operations. Max 30 requests/minute.",
            headers={"Retry-After": "60"},
        )


# =============================================================================
# Helper Functions
# =============================================================================

def normalize_identifier(identifier_type: str, value: str) -> str:
    """Normalize identifier value before hashing."""
    if identifier_type == "email":
        # Lowercase, strip whitespace
        return value.lower().strip()
    elif identifier_type == "phone":
        # Remove non-digit characters, keep + prefix if present
        import re
        cleaned = re.sub(r"[^\d+]", "", value)
        # Ensure E.164 format (starts with +)
        if not cleaned.startswith("+"):
            cleaned = "+" + cleaned
        return cleaned
    else:
        # Other identifiers: strip whitespace only
        return value.strip()


def hash_identifier(value: str) -> str:
    """Hash identifier value using SHA256."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _get_identifier_type(identifier) -> str:
    """Get identifier type from dict or object."""
    if isinstance(identifier, dict):
        return identifier.get("type", "")
    return getattr(identifier, "type", "")


def _get_context_attr(context, attr: str):
    """Get attribute from context dict or object."""
    if context is None:
        return None
    if isinstance(context, dict):
        return context.get(attr)
    return getattr(context, attr, None)


def calculate_emq_score(event_data: dict, has_pii: bool, latency_seconds: float) -> float:
    """Calculate Event Match Quality score (0-100)."""
    score = 0.0

    # Identifier quality (40%)
    identifiers = event_data.get("identifiers", [])
    has_email = any(_get_identifier_type(i) == "email" for i in identifiers)
    has_phone = any(_get_identifier_type(i) == "phone" for i in identifiers)
    if has_email or has_phone:
        score += 40
    elif identifiers:
        score += 20

    # Data completeness (25%)
    properties = event_data.get("properties", {})
    if properties:
        score += 25

    # Timeliness (20%)
    if latency_seconds < 300:  # Within 5 minutes
        score += 20
    elif latency_seconds < 3600:  # Within 1 hour
        score += 10

    # Context richness (15%)
    context = event_data.get("context")
    if context:
        if _get_context_attr(context, "campaign"):
            score += 5
        if _get_context_attr(context, "user_agent"):
            score += 5
        if _get_context_attr(context, "ip"):
            score += 5

    return min(score, 100.0)


async def find_or_create_profile(
    db: AsyncSession,
    tenant_id: int,
    identifiers: list,
) -> tuple[CDPProfile, bool]:
    """
    Find existing profile by any identifier, or create new one.
    Returns (profile, is_new).
    """
    # Try to find existing profile by any identifier
    for ident in identifiers:
        normalized = normalize_identifier(ident.type, ident.value)
        ident_hash = hash_identifier(normalized)

        result = await db.execute(
            select(CDPProfileIdentifier)
            .where(
                CDPProfileIdentifier.tenant_id == tenant_id,
                CDPProfileIdentifier.identifier_type == ident.type,
                CDPProfileIdentifier.identifier_hash == ident_hash,
            )
            .options(selectinload(CDPProfileIdentifier.profile))
        )
        existing = result.scalar_one_or_none()

        if existing and existing.profile:
            return existing.profile, False

    # No existing profile found, create new one
    profile = CDPProfile(
        tenant_id=tenant_id,
        lifecycle_stage=LifecycleStage.ANONYMOUS.value,
    )
    db.add(profile)
    await db.flush()

    return profile, True


async def link_identifiers_to_profile(
    db: AsyncSession,
    tenant_id: int,
    profile: CDPProfile,
    identifiers: list,
) -> None:
    """Link identifiers to profile, creating new ones if needed."""
    for ident in identifiers:
        normalized = normalize_identifier(ident.type, ident.value)
        ident_hash = hash_identifier(normalized)

        # Check if identifier already exists
        result = await db.execute(
            select(CDPProfileIdentifier)
            .where(
                CDPProfileIdentifier.tenant_id == tenant_id,
                CDPProfileIdentifier.identifier_type == ident.type,
                CDPProfileIdentifier.identifier_hash == ident_hash,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update last_seen_at
            existing.last_seen_at = datetime.now(timezone.utc)
        else:
            # Create new identifier
            new_ident = CDPProfileIdentifier(
                tenant_id=tenant_id,
                profile_id=profile.id,
                identifier_type=ident.type,
                identifier_value=ident.value,  # Store original (can be redacted later)
                identifier_hash=ident_hash,
                is_primary=(ident.type in ["email", "phone"]),
            )
            db.add(new_ident)

    # Update profile lifecycle if we now have PII
    has_pii = any(i.type in ["email", "phone"] for i in identifiers)
    if has_pii and profile.lifecycle_stage == LifecycleStage.ANONYMOUS.value:
        profile.lifecycle_stage = LifecycleStage.KNOWN.value


# =============================================================================
# Event Endpoints
# =============================================================================

async def validate_source_key(
    db: AsyncSession,
    tenant_id: int,
    source_key: Optional[str],
) -> Optional[CDPSource]:
    """
    Validate source_key and return the source if valid.
    Returns None if source_key is not provided (backward compatibility).
    Raises HTTPException if source_key is invalid.
    """
    if not source_key:
        return None

    result = await db.execute(
        select(CDPSource)
        .where(
            CDPSource.tenant_id == tenant_id,
            CDPSource.source_key == source_key,
            CDPSource.is_active == True,
        )
    )
    source = result.scalar_one_or_none()

    if not source:
        logger.warning(
            "cdp_invalid_source_key",
            tenant_id=tenant_id,
            source_key_prefix=source_key[:8] + "..." if source_key else None,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive source_key",
        )

    return source


@router.post(
    "/events",
    response_model=EventBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest events",
    description="Ingest one or more events. Events are linked to profiles based on identifiers.",
)
async def ingest_events(
    request: Request,
    batch: EventBatchInput,
    source_key: Optional[str] = Query(None, description="Source API key for authentication"),
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_event_rate_limit),
):
    """
    Ingest events into CDP.

    - Validates source_key (if provided) for source-level authentication
    - Validates event schema
    - Hashes PII identifiers
    - Finds or creates profile
    - Links identifiers to profile
    - Stores event with source_id
    - Calculates EMQ score
    """
    tenant_id = current_user.tenant_id
    results = []
    accepted = 0
    rejected = 0
    duplicates = 0

    # Validate source authentication
    source = await validate_source_key(db, tenant_id, source_key)
    source_id = source.id if source else None

    logger.info(
        "cdp_event_ingestion_started",
        tenant_id=tenant_id,
        event_count=len(batch.events),
        source_id=str(source_id) if source_id else None,
    )

    for event in batch.events:
        try:
            # Check for duplicate (idempotency)
            if event.idempotency_key:
                cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
                result = await db.execute(
                    select(CDPEvent.id)
                    .where(
                        CDPEvent.tenant_id == tenant_id,
                        CDPEvent.idempotency_key == event.idempotency_key,
                        CDPEvent.received_at >= cutoff,
                    )
                )
                if result.scalar_one_or_none():
                    duplicates += 1
                    results.append(EventIngestResult(
                        status="duplicate",
                        error="Event with same idempotency_key already exists",
                    ))
                    continue

            # Find or create profile
            profile, is_new = await find_or_create_profile(
                db, tenant_id, event.identifiers
            )

            # Link identifiers to profile
            await link_identifiers_to_profile(
                db, tenant_id, profile, event.identifiers
            )

            # Calculate EMQ score
            received_at = datetime.now(timezone.utc)
            latency = (received_at - event.event_time).total_seconds()
            has_pii = any(i.type in ["email", "phone"] for i in event.identifiers)
            emq_score = calculate_emq_score(
                {"identifiers": event.identifiers, "properties": event.properties, "context": event.context},
                has_pii,
                latency,
            )

            # Create event
            db_event = CDPEvent(
                tenant_id=tenant_id,
                profile_id=profile.id,
                source_id=source_id,
                event_name=event.event_name,
                event_time=event.event_time,
                received_at=received_at,
                idempotency_key=event.idempotency_key,
                properties=event.properties or {},
                context=event.context.model_dump() if event.context else {},
                identifiers=[i.model_dump() for i in event.identifiers],
                emq_score=emq_score,
            )
            db.add(db_event)

            # Update source metrics if source is provided
            if source:
                source.event_count += 1
                source.last_event_at = received_at

            # Update profile counters
            profile.total_events += 1
            profile.last_seen_at = received_at

            # Invalidate cache for this profile
            _profile_cache.invalidate(tenant_id, str(profile.id))

            # Handle consent if provided
            if event.consent:
                for consent_type, granted in event.consent.model_dump(exclude_none=True).items():
                    if granted is not None:
                        # Upsert consent
                        result = await db.execute(
                            select(CDPConsent)
                            .where(
                                CDPConsent.tenant_id == tenant_id,
                                CDPConsent.profile_id == profile.id,
                                CDPConsent.consent_type == consent_type,
                            )
                        )
                        existing_consent = result.scalar_one_or_none()

                        if existing_consent:
                            existing_consent.granted = granted
                            if granted:
                                existing_consent.granted_at = received_at
                                existing_consent.revoked_at = None
                            else:
                                existing_consent.revoked_at = received_at
                        else:
                            new_consent = CDPConsent(
                                tenant_id=tenant_id,
                                profile_id=profile.id,
                                consent_type=consent_type,
                                granted=granted,
                                granted_at=received_at if granted else None,
                                source="event_ingestion",
                            )
                            db.add(new_consent)

            await db.flush()

            accepted += 1
            results.append(EventIngestResult(
                event_id=db_event.id,
                status="accepted",
                profile_id=profile.id,
            ))

        except Exception as e:
            logger.error(
                "cdp_event_processing_error",
                tenant_id=tenant_id,
                event_name=event.event_name,
                error=str(e),
            )
            rejected += 1
            results.append(EventIngestResult(
                status="rejected",
                error=str(e),
            ))

    await db.commit()

    logger.info(
        "cdp_event_ingestion_completed",
        tenant_id=tenant_id,
        accepted=accepted,
        rejected=rejected,
        duplicates=duplicates,
    )

    return EventBatchResponse(
        accepted=accepted,
        rejected=rejected,
        duplicates=duplicates,
        results=results,
    )


# =============================================================================
# Profile Endpoints
# =============================================================================

def _build_profile_response(profile: CDPProfile) -> ProfileResponse:
    """Build ProfileResponse from a CDPProfile ORM object."""
    return ProfileResponse(
        id=profile.id,
        tenant_id=profile.tenant_id,
        external_id=profile.external_id,
        first_seen_at=profile.first_seen_at,
        last_seen_at=profile.last_seen_at,
        profile_data=profile.profile_data,
        computed_traits=profile.computed_traits,
        lifecycle_stage=profile.lifecycle_stage,
        total_events=profile.total_events,
        total_sessions=profile.total_sessions,
        total_purchases=profile.total_purchases,
        total_revenue=profile.total_revenue,
        identifiers=[
            IdentifierResponse(
                id=i.id,
                identifier_type=i.identifier_type,
                identifier_value=i.identifier_value,
                identifier_hash=i.identifier_hash,
                is_primary=i.is_primary,
                confidence_score=i.confidence_score,
                verified_at=i.verified_at,
                first_seen_at=i.first_seen_at,
                last_seen_at=i.last_seen_at,
            )
            for i in profile.identifiers
        ],
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.get(
    "/profiles/{profile_id}",
    response_model=ProfileResponse,
    summary="Get profile by ID",
    description="Retrieve a profile by its UUID, including identifiers and metadata.",
)
async def get_profile(
    profile_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_profile_rate_limit),
):
    """Get profile by ID with caching."""
    tenant_id = current_user.tenant_id
    profile_id_str = str(profile_id)

    # Check cache first
    cached = _profile_cache.get(tenant_id, profile_id_str)
    if cached is not None:
        logger.debug("cdp_profile_cache_hit", profile_id=profile_id_str)
        return cached

    # Cache miss - fetch from database
    result = await db.execute(
        select(CDPProfile)
        .where(
            CDPProfile.id == profile_id,
            CDPProfile.tenant_id == tenant_id,
        )
        .options(selectinload(CDPProfile.identifiers))
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    response = _build_profile_response(profile)

    # Cache the response
    _profile_cache.set(tenant_id, profile_id_str, response)

    return response


@router.get(
    "/profiles",
    response_model=ProfileResponse,
    summary="Lookup profile by identifier",
    description="Find a profile by identifier type and value. Value is hashed before lookup.",
)
async def lookup_profile(
    identifier_type: str = Query(..., description="Identifier type (email, phone, etc.)"),
    identifier_value: str = Query(..., description="Identifier value to look up"),
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_profile_rate_limit),
):
    """Lookup profile by identifier with caching."""
    tenant_id = current_user.tenant_id

    # Normalize and hash the identifier
    normalized = normalize_identifier(identifier_type, identifier_value)
    ident_hash = hash_identifier(normalized)

    # Check cache first
    cached = _profile_cache.get_by_lookup(tenant_id, identifier_type.lower(), ident_hash)
    if cached is not None:
        logger.debug(
            "cdp_profile_lookup_cache_hit",
            identifier_type=identifier_type,
        )
        return cached

    # Cache miss - fetch from database
    result = await db.execute(
        select(CDPProfileIdentifier)
        .where(
            CDPProfileIdentifier.tenant_id == tenant_id,
            CDPProfileIdentifier.identifier_type == identifier_type.lower(),
            CDPProfileIdentifier.identifier_hash == ident_hash,
        )
        .options(
            selectinload(CDPProfileIdentifier.profile)
            .selectinload(CDPProfile.identifiers)
        )
    )
    ident = result.scalar_one_or_none()

    if not ident or not ident.profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found for given identifier",
        )

    response = _build_profile_response(ident.profile)

    # Cache the response for both lookup key and profile ID
    _profile_cache.set_by_lookup(tenant_id, identifier_type.lower(), ident_hash, response)
    _profile_cache.set(tenant_id, str(ident.profile.id), response)

    return response


# =============================================================================
# Source Endpoints
# =============================================================================

@router.get(
    "/sources",
    response_model=SourceListResponse,
    summary="List data sources",
    description="List all data sources configured for the tenant.",
)
async def list_sources(
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_source_rate_limit),
):
    """List all data sources for tenant."""
    tenant_id = current_user.tenant_id

    result = await db.execute(
        select(CDPSource)
        .where(CDPSource.tenant_id == tenant_id)
        .order_by(CDPSource.created_at.desc())
    )
    sources = result.scalars().all()

    return SourceListResponse(
        sources=[
            SourceResponse(
                id=s.id,
                name=s.name,
                source_type=s.source_type,
                source_key=s.source_key,
                config=s.config,
                is_active=s.is_active,
                event_count=s.event_count,
                last_event_at=s.last_event_at,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in sources
        ],
        total=len(sources),
    )


@router.post(
    "/sources",
    response_model=SourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create data source",
    description="Create a new data source. Returns source_key for API authentication.",
)
async def create_source(
    source: SourceCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_source_rate_limit),
):
    """Create a new data source."""
    tenant_id = current_user.tenant_id

    # Generate unique source key
    source_key = f"cdp_{secrets.token_urlsafe(32)}"

    db_source = CDPSource(
        tenant_id=tenant_id,
        name=source.name,
        source_type=source.source_type,
        source_key=source_key,
        config=source.config or {},
    )
    db.add(db_source)
    await db.commit()
    await db.refresh(db_source)

    logger.info(
        "cdp_source_created",
        tenant_id=tenant_id,
        source_id=str(db_source.id),
        source_type=source.source_type,
    )

    return SourceResponse(
        id=db_source.id,
        name=db_source.name,
        source_type=db_source.source_type,
        source_key=db_source.source_key,
        config=db_source.config,
        is_active=db_source.is_active,
        event_count=db_source.event_count,
        last_event_at=db_source.last_event_at,
        created_at=db_source.created_at,
        updated_at=db_source.updated_at,
    )


# =============================================================================
# Health Check Endpoint
# =============================================================================

@router.get(
    "/health",
    summary="CDP health check",
    description="Check CDP module health status.",
)
async def cdp_health():
    """CDP health check endpoint."""
    return {
        "status": "healthy",
        "module": "cdp",
        "version": "1.1.0",
    }


# =============================================================================
# Data Export Endpoints
# =============================================================================

@router.get(
    "/export/profiles",
    summary="Export profiles",
    description="Export profiles in JSON or CSV format.",
)
async def export_profiles(
    format: str = Query("json", description="Export format: json or csv"),
    limit: int = Query(1000, ge=1, le=10000, description="Max profiles to export"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_source_rate_limit),
):
    """
    Export profiles for data portability.

    Supports JSON and CSV formats with pagination.
    Maximum 10,000 profiles per request.
    """
    from fastapi.responses import StreamingResponse
    import csv
    import io
    import json

    tenant_id = current_user.tenant_id

    # Fetch profiles
    result = await db.execute(
        select(CDPProfile)
        .where(CDPProfile.tenant_id == tenant_id)
        .order_by(CDPProfile.created_at.desc())
        .offset(offset)
        .limit(limit)
        .options(selectinload(CDPProfile.identifiers))
    )
    profiles = result.scalars().all()

    if format.lower() == "csv":
        # Generate CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "id", "external_id", "lifecycle_stage", "first_seen_at", "last_seen_at",
            "total_events", "total_sessions", "total_purchases", "total_revenue",
            "identifier_count", "created_at", "updated_at"
        ])
        writer.writeheader()

        for profile in profiles:
            writer.writerow({
                "id": str(profile.id),
                "external_id": profile.external_id or "",
                "lifecycle_stage": profile.lifecycle_stage,
                "first_seen_at": profile.first_seen_at.isoformat() if profile.first_seen_at else "",
                "last_seen_at": profile.last_seen_at.isoformat() if profile.last_seen_at else "",
                "total_events": profile.total_events,
                "total_sessions": profile.total_sessions,
                "total_purchases": profile.total_purchases,
                "total_revenue": float(profile.total_revenue),
                "identifier_count": len(profile.identifiers),
                "created_at": profile.created_at.isoformat(),
                "updated_at": profile.updated_at.isoformat(),
            })

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=cdp_profiles_{tenant_id}.csv"}
        )

    else:
        # Generate JSON
        data = [
            {
                "id": str(p.id),
                "external_id": p.external_id,
                "lifecycle_stage": p.lifecycle_stage,
                "first_seen_at": p.first_seen_at.isoformat() if p.first_seen_at else None,
                "last_seen_at": p.last_seen_at.isoformat() if p.last_seen_at else None,
                "profile_data": p.profile_data,
                "computed_traits": p.computed_traits,
                "total_events": p.total_events,
                "total_sessions": p.total_sessions,
                "total_purchases": p.total_purchases,
                "total_revenue": float(p.total_revenue),
                "identifiers": [
                    {
                        "type": i.identifier_type,
                        "hash": i.identifier_hash,
                        "is_primary": i.is_primary,
                    }
                    for i in p.identifiers
                ],
                "created_at": p.created_at.isoformat(),
                "updated_at": p.updated_at.isoformat(),
            }
            for p in profiles
        ]

        return {
            "format": "json",
            "count": len(data),
            "offset": offset,
            "limit": limit,
            "data": data,
        }


@router.get(
    "/export/events",
    summary="Export events",
    description="Export events in JSON or CSV format.",
)
async def export_events(
    format: str = Query("json", description="Export format: json or csv"),
    limit: int = Query(1000, ge=1, le=10000, description="Max events to export"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    start_date: Optional[datetime] = Query(None, description="Filter events from this date"),
    end_date: Optional[datetime] = Query(None, description="Filter events until this date"),
    event_name: Optional[str] = Query(None, description="Filter by event name"),
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_source_rate_limit),
):
    """
    Export events for data analysis.

    Supports JSON and CSV formats with filtering and pagination.
    Maximum 10,000 events per request.
    """
    from fastapi.responses import StreamingResponse
    import csv
    import io

    tenant_id = current_user.tenant_id

    # Build query with filters
    query = select(CDPEvent).where(CDPEvent.tenant_id == tenant_id)

    if start_date:
        query = query.where(CDPEvent.event_time >= start_date)
    if end_date:
        query = query.where(CDPEvent.event_time <= end_date)
    if event_name:
        query = query.where(CDPEvent.event_name == event_name)

    query = query.order_by(CDPEvent.event_time.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    events = result.scalars().all()

    if format.lower() == "csv":
        # Generate CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "id", "profile_id", "event_name", "event_time", "received_at",
            "emq_score", "processed", "source_id"
        ])
        writer.writeheader()

        for event in events:
            writer.writerow({
                "id": str(event.id),
                "profile_id": str(event.profile_id),
                "event_name": event.event_name,
                "event_time": event.event_time.isoformat(),
                "received_at": event.received_at.isoformat(),
                "emq_score": float(event.emq_score) if event.emq_score else "",
                "processed": event.processed,
                "source_id": str(event.source_id) if event.source_id else "",
            })

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=cdp_events_{tenant_id}.csv"}
        )

    else:
        # Generate JSON
        data = [
            {
                "id": str(e.id),
                "profile_id": str(e.profile_id),
                "event_name": e.event_name,
                "event_time": e.event_time.isoformat(),
                "received_at": e.received_at.isoformat(),
                "properties": e.properties,
                "context": e.context,
                "emq_score": float(e.emq_score) if e.emq_score else None,
                "processed": e.processed,
                "source_id": str(e.source_id) if e.source_id else None,
            }
            for e in events
        ]

        return {
            "format": "json",
            "count": len(data),
            "offset": offset,
            "limit": limit,
            "filters": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "event_name": event_name,
            },
            "data": data,
        }


# =============================================================================
# Webhook Endpoints
# =============================================================================

def _build_webhook_response(webhook: CDPWebhook, include_secret: bool = False) -> WebhookResponse:
    """Build WebhookResponse from a CDPWebhook ORM object."""
    return WebhookResponse(
        id=webhook.id,
        name=webhook.name,
        url=webhook.url,
        event_types=webhook.event_types or [],
        secret_key=webhook.secret_key if include_secret else None,
        is_active=webhook.is_active,
        last_triggered_at=webhook.last_triggered_at,
        last_success_at=webhook.last_success_at,
        last_failure_at=webhook.last_failure_at,
        failure_count=webhook.failure_count,
        max_retries=webhook.max_retries,
        timeout_seconds=webhook.timeout_seconds,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at,
    )


@router.get(
    "/webhooks",
    response_model=WebhookListResponse,
    summary="List webhooks",
    description="List all webhook destinations configured for the tenant.",
)
async def list_webhooks(
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_webhook_rate_limit),
):
    """List all webhooks for tenant."""
    tenant_id = current_user.tenant_id

    result = await db.execute(
        select(CDPWebhook)
        .where(CDPWebhook.tenant_id == tenant_id)
        .order_by(CDPWebhook.created_at.desc())
    )
    webhooks = result.scalars().all()

    return WebhookListResponse(
        webhooks=[_build_webhook_response(w) for w in webhooks],
        total=len(webhooks),
    )


@router.post(
    "/webhooks",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create webhook",
    description="Create a new webhook destination. Returns secret_key for HMAC validation.",
)
async def create_webhook(
    webhook: WebhookCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_webhook_rate_limit),
):
    """Create a new webhook destination."""
    tenant_id = current_user.tenant_id

    # Generate secret key for HMAC signature
    secret_key = secrets.token_urlsafe(32)

    db_webhook = CDPWebhook(
        tenant_id=tenant_id,
        name=webhook.name,
        url=webhook.url,
        event_types=webhook.event_types,
        secret_key=secret_key,
        max_retries=webhook.max_retries,
        timeout_seconds=webhook.timeout_seconds,
    )
    db.add(db_webhook)
    await db.commit()
    await db.refresh(db_webhook)

    logger.info(
        "cdp_webhook_created",
        tenant_id=tenant_id,
        webhook_id=str(db_webhook.id),
        event_types=webhook.event_types,
    )

    # Include secret_key in response for initial creation
    return _build_webhook_response(db_webhook, include_secret=True)


@router.get(
    "/webhooks/{webhook_id}",
    response_model=WebhookResponse,
    summary="Get webhook",
    description="Get webhook details by ID.",
)
async def get_webhook(
    webhook_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_webhook_rate_limit),
):
    """Get webhook by ID."""
    tenant_id = current_user.tenant_id

    result = await db.execute(
        select(CDPWebhook)
        .where(
            CDPWebhook.id == webhook_id,
            CDPWebhook.tenant_id == tenant_id,
        )
    )
    webhook = result.scalar_one_or_none()

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    return _build_webhook_response(webhook)


@router.patch(
    "/webhooks/{webhook_id}",
    response_model=WebhookResponse,
    summary="Update webhook",
    description="Update webhook configuration.",
)
async def update_webhook(
    webhook_id: UUID,
    webhook_update: WebhookUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_webhook_rate_limit),
):
    """Update webhook configuration."""
    tenant_id = current_user.tenant_id

    result = await db.execute(
        select(CDPWebhook)
        .where(
            CDPWebhook.id == webhook_id,
            CDPWebhook.tenant_id == tenant_id,
        )
    )
    webhook = result.scalar_one_or_none()

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    # Apply updates
    update_data = webhook_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(webhook, field, value)

    # Reset failure count if re-activating
    if webhook_update.is_active is True and webhook.failure_count > 0:
        webhook.failure_count = 0

    await db.commit()
    await db.refresh(webhook)

    logger.info(
        "cdp_webhook_updated",
        tenant_id=tenant_id,
        webhook_id=str(webhook_id),
        updates=list(update_data.keys()),
    )

    return _build_webhook_response(webhook)


@router.delete(
    "/webhooks/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete webhook",
    description="Delete a webhook destination.",
)
async def delete_webhook(
    webhook_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_webhook_rate_limit),
):
    """Delete a webhook."""
    tenant_id = current_user.tenant_id

    result = await db.execute(
        select(CDPWebhook)
        .where(
            CDPWebhook.id == webhook_id,
            CDPWebhook.tenant_id == tenant_id,
        )
    )
    webhook = result.scalar_one_or_none()

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    await db.delete(webhook)
    await db.commit()

    logger.info(
        "cdp_webhook_deleted",
        tenant_id=tenant_id,
        webhook_id=str(webhook_id),
    )


@router.post(
    "/webhooks/{webhook_id}/test",
    response_model=WebhookTestResult,
    summary="Test webhook",
    description="Send a test request to the webhook endpoint.",
)
async def test_webhook(
    webhook_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_webhook_rate_limit),
):
    """Send a test request to webhook endpoint."""
    import httpx
    import hmac
    import json

    tenant_id = current_user.tenant_id

    result = await db.execute(
        select(CDPWebhook)
        .where(
            CDPWebhook.id == webhook_id,
            CDPWebhook.tenant_id == tenant_id,
        )
    )
    webhook = result.scalar_one_or_none()

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    # Prepare test payload
    test_payload = {
        "event_type": "test",
        "tenant_id": tenant_id,
        "webhook_id": str(webhook_id),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "message": "This is a test webhook request from Stratum CDP",
        },
    }

    payload_json = json.dumps(test_payload)

    # Create HMAC signature
    if webhook.secret_key:
        signature = hmac.new(
            webhook.secret_key.encode(),
            payload_json.encode(),
            hashlib.sha256,
        ).hexdigest()
    else:
        signature = None

    headers = {
        "Content-Type": "application/json",
        "X-Stratum-Webhook-Event": "test",
        "X-Stratum-Webhook-ID": str(webhook_id),
    }
    if signature:
        headers["X-Stratum-Signature"] = f"sha256={signature}"

    # Send test request
    start_time = time.time()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook.url,
                content=payload_json,
                headers=headers,
                timeout=webhook.timeout_seconds,
            )

        elapsed_ms = (time.time() - start_time) * 1000

        success = 200 <= response.status_code < 300

        logger.info(
            "cdp_webhook_test",
            tenant_id=tenant_id,
            webhook_id=str(webhook_id),
            success=success,
            status_code=response.status_code,
            elapsed_ms=elapsed_ms,
        )

        return WebhookTestResult(
            success=success,
            status_code=response.status_code,
            response_time_ms=round(elapsed_ms, 2),
            error=None if success else f"HTTP {response.status_code}",
        )

    except httpx.TimeoutException:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.warning(
            "cdp_webhook_test_timeout",
            tenant_id=tenant_id,
            webhook_id=str(webhook_id),
        )
        return WebhookTestResult(
            success=False,
            status_code=None,
            response_time_ms=round(elapsed_ms, 2),
            error=f"Request timed out after {webhook.timeout_seconds} seconds",
        )

    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error(
            "cdp_webhook_test_error",
            tenant_id=tenant_id,
            webhook_id=str(webhook_id),
            error=str(e),
        )
        return WebhookTestResult(
            success=False,
            status_code=None,
            response_time_ms=round(elapsed_ms, 2),
            error=str(e),
        )


@router.post(
    "/webhooks/{webhook_id}/rotate-secret",
    response_model=WebhookResponse,
    summary="Rotate webhook secret",
    description="Generate a new secret key for webhook HMAC signatures.",
)
async def rotate_webhook_secret(
    webhook_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_webhook_rate_limit),
):
    """Rotate the webhook secret key."""
    tenant_id = current_user.tenant_id

    result = await db.execute(
        select(CDPWebhook)
        .where(
            CDPWebhook.id == webhook_id,
            CDPWebhook.tenant_id == tenant_id,
        )
    )
    webhook = result.scalar_one_or_none()

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    # Generate new secret
    webhook.secret_key = secrets.token_urlsafe(32)
    await db.commit()
    await db.refresh(webhook)

    logger.info(
        "cdp_webhook_secret_rotated",
        tenant_id=tenant_id,
        webhook_id=str(webhook_id),
    )

    # Include new secret in response
    return _build_webhook_response(webhook, include_secret=True)


# =============================================================================
# Anomaly Detection Endpoints
# =============================================================================

def calculate_zscore(values: List[float], current: float, window: int = 14) -> float:
    """Calculate Z-score for anomaly detection."""
    import statistics

    if len(values) < 3:
        return 0.0

    series = values[-window:] if len(values) > window else values

    try:
        mu = statistics.mean(series)
        sd = statistics.stdev(series) if len(series) > 1 else 0.0

        if sd <= 1e-9:
            return 0.0

        return (current - mu) / sd
    except (statistics.StatisticsError, ZeroDivisionError):
        return 0.0


def get_anomaly_severity(zscore: float) -> str:
    """Map Z-score to severity level."""
    abs_z = abs(zscore)
    if abs_z >= 4.0:
        return "critical"
    elif abs_z >= 3.0:
        return "high"
    elif abs_z >= 2.5:
        return "medium"
    else:
        return "low"


@router.get(
    "/anomalies/events",
    summary="Detect event volume anomalies",
    description="Analyze event volume patterns and detect anomalies per source.",
)
async def detect_event_anomalies(
    window_days: int = Query(14, ge=3, le=30, description="Days for baseline calculation"),
    zscore_threshold: float = Query(2.5, ge=1.5, le=5.0, description="Z-score threshold for anomaly"),
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_profile_rate_limit),
):
    """
    Detect anomalies in event volume per source.

    Analyzes the last N days of event counts per source and detects
    significant deviations from the baseline using Z-scores.
    """
    import statistics
    from sqlalchemy import cast, Date

    tenant_id = current_user.tenant_id

    # Get daily event counts per source for the last N+1 days
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days + 1)

    result = await db.execute(
        select(
            CDPEvent.source_id,
            cast(CDPEvent.received_at, Date).label("date"),
            func.count(CDPEvent.id).label("event_count"),
        )
        .where(
            CDPEvent.tenant_id == tenant_id,
            CDPEvent.received_at >= cutoff,
        )
        .group_by(CDPEvent.source_id, cast(CDPEvent.received_at, Date))
        .order_by(cast(CDPEvent.received_at, Date))
    )
    daily_counts = result.all()

    # Also get total events per day (across all sources)
    total_result = await db.execute(
        select(
            cast(CDPEvent.received_at, Date).label("date"),
            func.count(CDPEvent.id).label("event_count"),
        )
        .where(
            CDPEvent.tenant_id == tenant_id,
            CDPEvent.received_at >= cutoff,
        )
        .group_by(cast(CDPEvent.received_at, Date))
        .order_by(cast(CDPEvent.received_at, Date))
    )
    total_daily = total_result.all()

    # Get source names for display
    sources_result = await db.execute(
        select(CDPSource.id, CDPSource.name)
        .where(CDPSource.tenant_id == tenant_id)
    )
    source_names = {row.id: row.name for row in sources_result.all()}

    # Group by source and analyze
    source_data: Dict[str, List[int]] = defaultdict(list)
    for row in daily_counts:
        source_key = str(row.source_id) if row.source_id else "unknown"
        source_data[source_key].append(row.event_count)

    # Analyze total events
    total_counts = [row.event_count for row in total_daily]

    anomalies = []

    # Check for anomalies per source
    for source_id, counts in source_data.items():
        if len(counts) < 3:
            continue

        historical = counts[:-1]
        current = counts[-1]

        z = calculate_zscore(historical, current, window_days)

        if abs(z) >= zscore_threshold:
            try:
                baseline_mean = statistics.mean(historical)
                baseline_std = statistics.stdev(historical) if len(historical) > 1 else 0.0
            except statistics.StatisticsError:
                baseline_mean = 0.0
                baseline_std = 0.0

            pct_change = ((current - baseline_mean) / baseline_mean * 100) if baseline_mean > 0 else 0

            source_name = source_names.get(source_id, source_id) if source_id != "unknown" else "Unknown Source"

            anomalies.append({
                "source_id": source_id if source_id != "unknown" else None,
                "source_name": source_name,
                "metric": "event_count",
                "zscore": round(z, 2),
                "severity": get_anomaly_severity(z),
                "current_value": current,
                "baseline_mean": round(baseline_mean, 2),
                "baseline_std": round(baseline_std, 2),
                "direction": "high" if z > 0 else "low",
                "pct_change": round(pct_change, 1),
            })

    # Check total events anomaly
    if len(total_counts) >= 3:
        historical_total = total_counts[:-1]
        current_total = total_counts[-1]

        z_total = calculate_zscore(historical_total, current_total, window_days)

        if abs(z_total) >= zscore_threshold:
            try:
                baseline_mean_total = statistics.mean(historical_total)
                baseline_std_total = statistics.stdev(historical_total) if len(historical_total) > 1 else 0.0
            except statistics.StatisticsError:
                baseline_mean_total = 0.0
                baseline_std_total = 0.0

            pct_change_total = ((current_total - baseline_mean_total) / baseline_mean_total * 100) if baseline_mean_total > 0 else 0

            anomalies.append({
                "source_id": None,
                "source_name": "All Sources (Total)",
                "metric": "total_event_count",
                "zscore": round(z_total, 2),
                "severity": get_anomaly_severity(z_total),
                "current_value": current_total,
                "baseline_mean": round(baseline_mean_total, 2),
                "baseline_std": round(baseline_std_total, 2),
                "direction": "high" if z_total > 0 else "low",
                "pct_change": round(pct_change_total, 1),
            })

    # Sort by absolute Z-score (most significant first)
    anomalies.sort(key=lambda x: abs(x["zscore"]), reverse=True)

    # Summary stats
    has_critical = any(a["severity"] == "critical" for a in anomalies)
    has_high = any(a["severity"] == "high" for a in anomalies)

    logger.info(
        "cdp_anomaly_detection_completed",
        tenant_id=tenant_id,
        anomaly_count=len(anomalies),
        has_critical=has_critical,
        has_high=has_high,
    )

    return {
        "anomalies": anomalies,
        "anomaly_count": len(anomalies),
        "has_critical": has_critical,
        "has_high": has_high,
        "analysis_period_days": window_days,
        "zscore_threshold": zscore_threshold,
        "total_sources_analyzed": len(source_data),
    }


@router.get(
    "/anomalies/summary",
    summary="Get anomaly detection summary",
    description="Get a summary of event volume patterns and health status.",
)
async def get_anomaly_summary(
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_profile_rate_limit),
):
    """
    Get a summary of CDP data health including volume trends and anomalies.
    """
    from sqlalchemy import cast, Date

    tenant_id = current_user.tenant_id

    # Get event counts for the last 7 days
    cutoff_7d = datetime.now(timezone.utc) - timedelta(days=7)
    cutoff_14d = datetime.now(timezone.utc) - timedelta(days=14)

    # Last 7 days total
    result_7d = await db.execute(
        select(func.count(CDPEvent.id))
        .where(
            CDPEvent.tenant_id == tenant_id,
            CDPEvent.received_at >= cutoff_7d,
        )
    )
    events_7d = result_7d.scalar() or 0

    # Previous 7 days (days 8-14)
    result_prev_7d = await db.execute(
        select(func.count(CDPEvent.id))
        .where(
            CDPEvent.tenant_id == tenant_id,
            CDPEvent.received_at >= cutoff_14d,
            CDPEvent.received_at < cutoff_7d,
        )
    )
    events_prev_7d = result_prev_7d.scalar() or 0

    # Today's events
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    result_today = await db.execute(
        select(func.count(CDPEvent.id))
        .where(
            CDPEvent.tenant_id == tenant_id,
            CDPEvent.received_at >= today_start,
        )
    )
    events_today = result_today.scalar() or 0

    # Average EMQ score (last 7 days)
    result_emq = await db.execute(
        select(func.avg(CDPEvent.emq_score))
        .where(
            CDPEvent.tenant_id == tenant_id,
            CDPEvent.received_at >= cutoff_7d,
            CDPEvent.emq_score.isnot(None),
        )
    )
    avg_emq = result_emq.scalar()

    # Calculate week-over-week change
    if events_prev_7d > 0:
        wow_change = ((events_7d - events_prev_7d) / events_prev_7d) * 100
    else:
        wow_change = 100.0 if events_7d > 0 else 0.0

    # Determine health status
    if avg_emq is None:
        health_status = "unknown"
    elif avg_emq >= 80:
        health_status = "healthy"
    elif avg_emq >= 60:
        health_status = "fair"
    elif avg_emq >= 40:
        health_status = "degraded"
    else:
        health_status = "critical"

    # Volume trend
    if wow_change > 20:
        volume_trend = "increasing"
    elif wow_change < -20:
        volume_trend = "decreasing"
    else:
        volume_trend = "stable"

    return {
        "health_status": health_status,
        "events_today": events_today,
        "events_7d": events_7d,
        "events_prev_7d": events_prev_7d,
        "wow_change_pct": round(wow_change, 1),
        "volume_trend": volume_trend,
        "avg_emq_score": round(float(avg_emq), 1) if avg_emq else None,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }
