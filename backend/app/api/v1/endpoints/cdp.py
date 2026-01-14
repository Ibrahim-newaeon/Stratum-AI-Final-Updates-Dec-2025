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
from sqlalchemy import select, func, or_, String, delete
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
    CDPIdentityLink,
    CDPProfileMerge,
    CDPCanonicalIdentity,
    CDPSegment,
    CDPSegmentMembership,
    CDPFunnel,
    LifecycleStage,
    MergeReason,
)
from app.schemas.cdp import (
    EventBatchInput,
    EventBatchResponse,
    EventIngestResult,
    ProfileResponse,
    SourceCreate,
    SourceResponse,
    SourceListResponse,
    IdentifierResponse,
    WebhookCreate,
    WebhookUpdate,
    WebhookResponse,
    WebhookListResponse,
    WebhookTestResult,
    IdentityGraphResponse,
    IdentityGraphNode,
    IdentityGraphEdge,
    ProfileMergeRequest,
    ProfileMergeResponse,
    ProfileMergeHistoryResponse,
    CanonicalIdentityResponse,
    SegmentCreate,
    SegmentUpdate,
    SegmentResponse,
    SegmentListResponse,
    SegmentPreviewRequest,
    SegmentPreviewResponse,
    SegmentProfilesResponse,
    ProfileSegmentsResponse,
    ProfileDeletionResponse,
    ComputedTraitCreate,
    ComputedTraitResponse,
    ComputedTraitListResponse,
    ComputeTraitsResponse,
    RFMConfig,
    RFMScores,
    RFMBatchResponse,
    RFMSummaryResponse,
    FunnelCreate,
    FunnelUpdate,
    FunnelResponse,
    FunnelListResponse,
    FunnelComputeResponse,
    FunnelAnalysisRequest,
    FunnelAnalysisResponse,
    ProfileFunnelJourneysResponse,
    FunnelDropOffResponse,
)
from app.services.cdp.identity_resolution import IdentityResolutionService
from app.services.cdp.segment_service import SegmentService
from app.services.cdp.computed_traits_service import ComputedTraitsService, RFMAnalysisService
from app.services.cdp.funnel_service import FunnelService

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
            CDPSource.is_active.is_(True),
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
# Event Statistics and Analytics Endpoints
# =============================================================================

@router.get(
    "/events/statistics",
    summary="Get event statistics",
    description="Get comprehensive event statistics and trends.",
)
async def get_event_statistics(
    period_days: int = Query(30, ge=1, le=365, description="Analysis period in days"),
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_source_rate_limit),
):
    """
    Get event statistics for the tenant.

    Returns:
    - Total event counts
    - Events by type
    - Daily event volume
    - EMQ score distribution
    - Top event sources
    """
    tenant_id = current_user.tenant_id
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=period_days)

    # Total events in period
    total_result = await db.execute(
        select(func.count(CDPEvent.id))
        .where(
            CDPEvent.tenant_id == tenant_id,
            CDPEvent.event_time >= cutoff_date,
        )
    )
    total_events = total_result.scalar() or 0

    # Events by name
    events_by_name_result = await db.execute(
        select(
            CDPEvent.event_name,
            func.count(CDPEvent.id).label("count"),
        )
        .where(
            CDPEvent.tenant_id == tenant_id,
            CDPEvent.event_time >= cutoff_date,
        )
        .group_by(CDPEvent.event_name)
        .order_by(func.count(CDPEvent.id).desc())
        .limit(20)
    )
    events_by_name = [
        {"event_name": row.event_name, "count": row.count}
        for row in events_by_name_result.all()
    ]

    # Daily event volume (last 30 days or period, whichever is less)
    daily_period = min(period_days, 30)
    daily_cutoff = datetime.now(timezone.utc) - timedelta(days=daily_period)

    daily_volume_result = await db.execute(
        select(
            func.date(CDPEvent.event_time).label("date"),
            func.count(CDPEvent.id).label("count"),
        )
        .where(
            CDPEvent.tenant_id == tenant_id,
            CDPEvent.event_time >= daily_cutoff,
        )
        .group_by(func.date(CDPEvent.event_time))
        .order_by(func.date(CDPEvent.event_time).asc())
    )
    daily_volume = [
        {"date": str(row.date), "count": row.count}
        for row in daily_volume_result.all()
    ]

    # EMQ score distribution
    emq_distribution_result = await db.execute(
        select(
            func.round(CDPEvent.emq_score * 10).label("bucket"),
            func.count(CDPEvent.id).label("count"),
        )
        .where(
            CDPEvent.tenant_id == tenant_id,
            CDPEvent.event_time >= cutoff_date,
            CDPEvent.emq_score.isnot(None),
        )
        .group_by(func.round(CDPEvent.emq_score * 10))
        .order_by(func.round(CDPEvent.emq_score * 10))
    )
    emq_distribution = [
        {
            "score_range": f"{int(row.bucket * 10)}-{int(row.bucket * 10 + 9)}",
            "count": row.count,
        }
        for row in emq_distribution_result.all()
    ]

    # Average EMQ score
    avg_emq_result = await db.execute(
        select(func.avg(CDPEvent.emq_score))
        .where(
            CDPEvent.tenant_id == tenant_id,
            CDPEvent.event_time >= cutoff_date,
            CDPEvent.emq_score.isnot(None),
        )
    )
    avg_emq_score = avg_emq_result.scalar()

    # Events by source
    events_by_source_result = await db.execute(
        select(
            CDPSource.name,
            func.count(CDPEvent.id).label("count"),
        )
        .join(CDPSource, CDPEvent.source_id == CDPSource.id)
        .where(
            CDPEvent.tenant_id == tenant_id,
            CDPEvent.event_time >= cutoff_date,
        )
        .group_by(CDPSource.name)
        .order_by(func.count(CDPEvent.id).desc())
        .limit(10)
    )
    events_by_source = [
        {"source_name": row.name, "count": row.count}
        for row in events_by_source_result.all()
    ]

    # Unique profiles with events
    unique_profiles_result = await db.execute(
        select(func.count(func.distinct(CDPEvent.profile_id)))
        .where(
            CDPEvent.tenant_id == tenant_id,
            CDPEvent.event_time >= cutoff_date,
        )
    )
    unique_profiles = unique_profiles_result.scalar() or 0

    return {
        "period_days": period_days,
        "analysis_start": cutoff_date.isoformat(),
        "analysis_end": datetime.now(timezone.utc).isoformat(),
        "total_events": total_events,
        "unique_profiles": unique_profiles,
        "avg_emq_score": round(float(avg_emq_score), 2) if avg_emq_score else None,
        "events_by_name": events_by_name,
        "daily_volume": daily_volume,
        "emq_distribution": emq_distribution,
        "events_by_source": events_by_source,
    }


@router.get(
    "/events/trends",
    summary="Get event trends",
    description="Get event volume trends and comparisons.",
)
async def get_event_trends(
    period_days: int = Query(7, ge=1, le=90, description="Current period in days"),
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_source_rate_limit),
):
    """
    Get event trends comparing current period vs previous period.
    """
    tenant_id = current_user.tenant_id
    now = datetime.now(timezone.utc)

    # Current period
    current_start = now - timedelta(days=period_days)

    # Previous period (same duration, immediately before current)
    previous_start = current_start - timedelta(days=period_days)
    previous_end = current_start

    # Current period events
    current_result = await db.execute(
        select(func.count(CDPEvent.id))
        .where(
            CDPEvent.tenant_id == tenant_id,
            CDPEvent.event_time >= current_start,
        )
    )
    current_events = current_result.scalar() or 0

    # Previous period events
    previous_result = await db.execute(
        select(func.count(CDPEvent.id))
        .where(
            CDPEvent.tenant_id == tenant_id,
            CDPEvent.event_time >= previous_start,
            CDPEvent.event_time < previous_end,
        )
    )
    previous_events = previous_result.scalar() or 0

    # Calculate change
    if previous_events > 0:
        change_pct = ((current_events - previous_events) / previous_events) * 100
    else:
        change_pct = 100.0 if current_events > 0 else 0.0

    # Event name trends
    current_by_name = await db.execute(
        select(
            CDPEvent.event_name,
            func.count(CDPEvent.id).label("count"),
        )
        .where(
            CDPEvent.tenant_id == tenant_id,
            CDPEvent.event_time >= current_start,
        )
        .group_by(CDPEvent.event_name)
    )
    current_names = {row.event_name: row.count for row in current_by_name.all()}

    previous_by_name = await db.execute(
        select(
            CDPEvent.event_name,
            func.count(CDPEvent.id).label("count"),
        )
        .where(
            CDPEvent.tenant_id == tenant_id,
            CDPEvent.event_time >= previous_start,
            CDPEvent.event_time < previous_end,
        )
        .group_by(CDPEvent.event_name)
    )
    previous_names = {row.event_name: row.count for row in previous_by_name.all()}

    # Calculate trends per event
    all_names = set(current_names.keys()) | set(previous_names.keys())
    event_trends = []
    for name in all_names:
        curr = current_names.get(name, 0)
        prev = previous_names.get(name, 0)
        if prev > 0:
            trend_pct = ((curr - prev) / prev) * 100
        else:
            trend_pct = 100.0 if curr > 0 else 0.0

        event_trends.append({
            "event_name": name,
            "current_count": curr,
            "previous_count": prev,
            "change_pct": round(trend_pct, 2),
            "trend": "up" if curr > prev else ("down" if curr < prev else "stable"),
        })

    # Sort by absolute change
    event_trends.sort(key=lambda x: abs(x["change_pct"]), reverse=True)

    return {
        "period_days": period_days,
        "current_period": {
            "start": current_start.isoformat(),
            "end": now.isoformat(),
            "total_events": current_events,
        },
        "previous_period": {
            "start": previous_start.isoformat(),
            "end": previous_end.isoformat(),
            "total_events": previous_events,
        },
        "overall_change_pct": round(change_pct, 2),
        "overall_trend": "up" if current_events > previous_events else ("down" if current_events < previous_events else "stable"),
        "event_trends": event_trends[:20],  # Top 20
    }


@router.get(
    "/profiles/statistics",
    summary="Get profile statistics",
    description="Get comprehensive profile statistics.",
)
async def get_profile_statistics(
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_source_rate_limit),
):
    """
    Get profile statistics for the tenant.
    """
    tenant_id = current_user.tenant_id
    now = datetime.now(timezone.utc)

    # Total profiles
    total_result = await db.execute(
        select(func.count(CDPProfile.id))
        .where(CDPProfile.tenant_id == tenant_id)
    )
    total_profiles = total_result.scalar() or 0

    # Profiles by lifecycle stage
    lifecycle_result = await db.execute(
        select(
            CDPProfile.lifecycle_stage,
            func.count(CDPProfile.id).label("count"),
        )
        .where(CDPProfile.tenant_id == tenant_id)
        .group_by(CDPProfile.lifecycle_stage)
    )
    lifecycle_distribution = {
        row.lifecycle_stage: row.count
        for row in lifecycle_result.all()
    }

    # New profiles (last 7 days)
    week_ago = now - timedelta(days=7)
    new_profiles_result = await db.execute(
        select(func.count(CDPProfile.id))
        .where(
            CDPProfile.tenant_id == tenant_id,
            CDPProfile.created_at >= week_ago,
        )
    )
    new_profiles_7d = new_profiles_result.scalar() or 0

    # Active profiles (seen in last 30 days)
    month_ago = now - timedelta(days=30)
    active_result = await db.execute(
        select(func.count(CDPProfile.id))
        .where(
            CDPProfile.tenant_id == tenant_id,
            CDPProfile.last_seen_at >= month_ago,
        )
    )
    active_profiles_30d = active_result.scalar() or 0

    # Profiles with email
    email_result = await db.execute(
        select(func.count(func.distinct(CDPProfileIdentifier.profile_id)))
        .where(
            CDPProfileIdentifier.tenant_id == tenant_id,
            CDPProfileIdentifier.identifier_type == "email",
        )
    )
    profiles_with_email = email_result.scalar() or 0

    # Profiles with phone
    phone_result = await db.execute(
        select(func.count(func.distinct(CDPProfileIdentifier.profile_id)))
        .where(
            CDPProfileIdentifier.tenant_id == tenant_id,
            CDPProfileIdentifier.identifier_type == "phone",
        )
    )
    profiles_with_phone = phone_result.scalar() or 0

    # Customers (has purchases)
    customers_result = await db.execute(
        select(func.count(CDPProfile.id))
        .where(
            CDPProfile.tenant_id == tenant_id,
            CDPProfile.total_purchases > 0,
        )
    )
    total_customers = customers_result.scalar() or 0

    # Revenue statistics
    revenue_result = await db.execute(
        select(
            func.sum(CDPProfile.total_revenue).label("total"),
            func.avg(CDPProfile.total_revenue).label("avg"),
            func.max(CDPProfile.total_revenue).label("max"),
        )
        .where(CDPProfile.tenant_id == tenant_id)
    )
    revenue_row = revenue_result.first()

    # Event statistics
    event_stats_result = await db.execute(
        select(
            func.sum(CDPProfile.total_events).label("total"),
            func.avg(CDPProfile.total_events).label("avg"),
        )
        .where(CDPProfile.tenant_id == tenant_id)
    )
    event_stats_row = event_stats_result.first()

    return {
        "total_profiles": total_profiles,
        "lifecycle_distribution": lifecycle_distribution,
        "new_profiles_7d": new_profiles_7d,
        "active_profiles_30d": active_profiles_30d,
        "profiles_with_email": profiles_with_email,
        "profiles_with_phone": profiles_with_phone,
        "email_coverage_pct": round((profiles_with_email / total_profiles * 100) if total_profiles > 0 else 0, 2),
        "phone_coverage_pct": round((profiles_with_phone / total_profiles * 100) if total_profiles > 0 else 0, 2),
        "total_customers": total_customers,
        "customer_rate_pct": round((total_customers / total_profiles * 100) if total_profiles > 0 else 0, 2),
        "revenue": {
            "total": float(revenue_row.total) if revenue_row.total else 0,
            "average": round(float(revenue_row.avg), 2) if revenue_row.avg else 0,
            "max": float(revenue_row.max) if revenue_row.max else 0,
        },
        "events": {
            "total": int(event_stats_row.total) if event_stats_row.total else 0,
            "average_per_profile": round(float(event_stats_row.avg), 2) if event_stats_row.avg else 0,
        },
    }


# =============================================================================
# Profile Search API
# =============================================================================

@router.post(
    "/profiles/search",
    summary="Search profiles with advanced filters",
    description="Search and filter profiles with comprehensive criteria.",
)
async def search_profiles(
    # Search parameters
    query: Optional[str] = Query(None, description="Text search in external_id and profile_data"),
    limit: int = Query(50, ge=1, le=500, description="Max profiles to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    # Filter parameters
    segment_ids: Optional[List[UUID]] = Query(None, description="Filter by segment membership (any)"),
    exclude_segment_ids: Optional[List[UUID]] = Query(None, description="Exclude profiles in these segments"),
    lifecycle_stages: Optional[List[str]] = Query(None, description="Filter by lifecycle stages"),
    rfm_segments: Optional[List[str]] = Query(None, description="Filter by RFM segments"),
    identifier_types: Optional[List[str]] = Query(None, description="Has any of these identifier types"),
    min_events: Optional[int] = Query(None, ge=0),
    max_events: Optional[int] = Query(None, ge=0),
    min_revenue: Optional[float] = Query(None, ge=0),
    max_revenue: Optional[float] = Query(None, ge=0),
    first_seen_after: Optional[datetime] = Query(None),
    first_seen_before: Optional[datetime] = Query(None),
    last_seen_after: Optional[datetime] = Query(None),
    last_seen_before: Optional[datetime] = Query(None),
    has_email: Optional[bool] = Query(None, description="Has email identifier"),
    has_phone: Optional[bool] = Query(None, description="Has phone identifier"),
    is_customer: Optional[bool] = Query(None, description="Is customer (has purchases)"),
    # Sorting
    sort_by: str = Query("last_seen_at", description="Sort field: last_seen_at, first_seen_at, total_events, total_revenue"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    # Include options
    include_identifiers: bool = Query(False, description="Include identifiers in response"),
    include_computed_traits: bool = Query(True, description="Include computed traits"),
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_profile_rate_limit),
):
    """
    Search profiles with comprehensive filtering.

    Features:
    - Text search in external_id and profile_data
    - Filter by multiple segments (include/exclude)
    - Filter by lifecycle stages
    - Filter by RFM segments
    - Filter by identifier types
    - Filter by event/revenue thresholds
    - Filter by date ranges
    - Flexible sorting options
    """
    tenant_id = current_user.tenant_id

    # Build base query
    query_builder = select(CDPProfile).where(CDPProfile.tenant_id == tenant_id)

    # Text search
    if query:
        search_filter = or_(
            CDPProfile.external_id.ilike(f"%{query}%"),
            CDPProfile.profile_data.cast(String).ilike(f"%{query}%"),
        )
        query_builder = query_builder.where(search_filter)

    # Segment inclusion filter
    if segment_ids:
        subquery = (
            select(CDPSegmentMembership.profile_id)
            .where(
                CDPSegmentMembership.segment_id.in_(segment_ids),
                CDPSegmentMembership.is_member.is_(True),
            )
            .distinct()
        )
        query_builder = query_builder.where(CDPProfile.id.in_(subquery))

    # Segment exclusion filter
    if exclude_segment_ids:
        exclude_subquery = (
            select(CDPSegmentMembership.profile_id)
            .where(
                CDPSegmentMembership.segment_id.in_(exclude_segment_ids),
                CDPSegmentMembership.is_member.is_(True),
            )
            .distinct()
        )
        query_builder = query_builder.where(~CDPProfile.id.in_(exclude_subquery))

    # Lifecycle stages filter
    if lifecycle_stages:
        query_builder = query_builder.where(CDPProfile.lifecycle_stage.in_(lifecycle_stages))

    # RFM segments filter
    if rfm_segments:
        rfm_filter = or_(*[
            CDPProfile.computed_traits["rfm_segment"].astext == seg
            for seg in rfm_segments
        ])
        query_builder = query_builder.where(rfm_filter)

    # Identifier types filter
    if identifier_types:
        id_subquery = (
            select(CDPProfileIdentifier.profile_id)
            .where(
                CDPProfileIdentifier.identifier_type.in_(identifier_types),
                CDPProfileIdentifier.tenant_id == tenant_id,
            )
            .distinct()
        )
        query_builder = query_builder.where(CDPProfile.id.in_(id_subquery))

    # Event count filters
    if min_events is not None:
        query_builder = query_builder.where(CDPProfile.total_events >= min_events)
    if max_events is not None:
        query_builder = query_builder.where(CDPProfile.total_events <= max_events)

    # Revenue filters
    if min_revenue is not None:
        query_builder = query_builder.where(CDPProfile.total_revenue >= min_revenue)
    if max_revenue is not None:
        query_builder = query_builder.where(CDPProfile.total_revenue <= max_revenue)

    # Date filters
    if first_seen_after:
        query_builder = query_builder.where(CDPProfile.first_seen_at >= first_seen_after)
    if first_seen_before:
        query_builder = query_builder.where(CDPProfile.first_seen_at <= first_seen_before)
    if last_seen_after:
        query_builder = query_builder.where(CDPProfile.last_seen_at >= last_seen_after)
    if last_seen_before:
        query_builder = query_builder.where(CDPProfile.last_seen_at <= last_seen_before)

    # Email/Phone filter
    if has_email is not None:
        email_subquery = (
            select(CDPProfileIdentifier.profile_id)
            .where(
                CDPProfileIdentifier.identifier_type == "email",
                CDPProfileIdentifier.tenant_id == tenant_id,
            )
        )
        if has_email:
            query_builder = query_builder.where(CDPProfile.id.in_(email_subquery))
        else:
            query_builder = query_builder.where(~CDPProfile.id.in_(email_subquery))

    if has_phone is not None:
        phone_subquery = (
            select(CDPProfileIdentifier.profile_id)
            .where(
                CDPProfileIdentifier.identifier_type == "phone",
                CDPProfileIdentifier.tenant_id == tenant_id,
            )
        )
        if has_phone:
            query_builder = query_builder.where(CDPProfile.id.in_(phone_subquery))
        else:
            query_builder = query_builder.where(~CDPProfile.id.in_(phone_subquery))

    # Customer filter
    if is_customer is not None:
        if is_customer:
            query_builder = query_builder.where(CDPProfile.total_purchases > 0)
        else:
            query_builder = query_builder.where(CDPProfile.total_purchases == 0)

    # Get total count
    count_query = select(func.count()).select_from(query_builder.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply sorting
    sort_columns = {
        "last_seen_at": CDPProfile.last_seen_at,
        "first_seen_at": CDPProfile.first_seen_at,
        "total_events": CDPProfile.total_events,
        "total_revenue": CDPProfile.total_revenue,
        "created_at": CDPProfile.created_at,
    }
    sort_column = sort_columns.get(sort_by, CDPProfile.last_seen_at)
    if sort_order == "asc":
        query_builder = query_builder.order_by(sort_column.asc())
    else:
        query_builder = query_builder.order_by(sort_column.desc())

    # Add eager loading
    if include_identifiers:
        query_builder = query_builder.options(selectinload(CDPProfile.identifiers))

    # Apply pagination
    query_builder = query_builder.offset(offset).limit(limit)

    result = await db.execute(query_builder)
    profiles = result.scalars().unique().all()

    # Build response
    profile_data = []
    for p in profiles:
        data = {
            "id": str(p.id),
            "external_id": p.external_id,
            "lifecycle_stage": p.lifecycle_stage,
            "first_seen_at": p.first_seen_at.isoformat() if p.first_seen_at else None,
            "last_seen_at": p.last_seen_at.isoformat() if p.last_seen_at else None,
            "total_events": p.total_events,
            "total_sessions": p.total_sessions,
            "total_purchases": p.total_purchases,
            "total_revenue": float(p.total_revenue),
            "created_at": p.created_at.isoformat(),
            "updated_at": p.updated_at.isoformat(),
        }

        if include_computed_traits:
            data["computed_traits"] = p.computed_traits or {}

        if include_identifiers and hasattr(p, 'identifiers'):
            data["identifiers"] = [
                {
                    "type": i.identifier_type,
                    "hash": i.identifier_hash,
                    "is_primary": i.is_primary,
                }
                for i in p.identifiers
            ]

        profile_data.append(data)

    return {
        "profiles": profile_data,
        "total": total,
        "offset": offset,
        "limit": limit,
        "sort_by": sort_by,
        "sort_order": sort_order,
    }


# =============================================================================
# Audience Export Endpoints (Enhanced)
# =============================================================================

@router.post(
    "/audiences/export",
    summary="Export audience with advanced filters",
    description="Export profiles matching specified criteria in JSON or CSV format.",
)
async def export_audience(
    format: str = Query("json", description="Export format: json or csv"),
    limit: int = Query(1000, ge=1, le=50000, description="Max profiles to export"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    # Filter parameters
    segment_id: Optional[UUID] = Query(None, description="Filter by segment membership"),
    lifecycle_stage: Optional[str] = Query(None, description="Filter by lifecycle stage: anonymous, known, customer, churned"),
    rfm_segment: Optional[str] = Query(None, description="Filter by RFM segment"),
    min_events: Optional[int] = Query(None, ge=0, description="Minimum total events"),
    max_events: Optional[int] = Query(None, ge=0, description="Maximum total events"),
    min_revenue: Optional[float] = Query(None, ge=0, description="Minimum total revenue"),
    max_revenue: Optional[float] = Query(None, ge=0, description="Maximum total revenue"),
    first_seen_after: Optional[datetime] = Query(None, description="First seen after date"),
    first_seen_before: Optional[datetime] = Query(None, description="First seen before date"),
    last_seen_after: Optional[datetime] = Query(None, description="Last seen after date"),
    last_seen_before: Optional[datetime] = Query(None, description="Last seen before date"),
    has_identifier_type: Optional[str] = Query(None, description="Has identifier of type: email, phone, device_id, etc."),
    include_computed_traits: bool = Query(True, description="Include computed traits in export"),
    include_identifiers: bool = Query(False, description="Include identifiers (hashed) in export"),
    include_rfm: bool = Query(False, description="Include RFM scores in export"),
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_source_rate_limit),
):
    """
    Export audience profiles with advanced filtering.

    Features:
    - Filter by segment membership
    - Filter by lifecycle stage
    - Filter by RFM segment
    - Filter by event/revenue thresholds
    - Filter by date ranges
    - Filter by identifier type presence
    - Configurable output fields
    - Supports JSON and CSV formats
    - Maximum 50,000 profiles per request
    """
    from fastapi.responses import StreamingResponse
    import csv
    import io

    tenant_id = current_user.tenant_id

    # Build base query
    query = select(CDPProfile).where(CDPProfile.tenant_id == tenant_id)

    # Apply segment filter if provided
    if segment_id:
        query = query.join(
            CDPSegmentMembership,
            CDPSegmentMembership.profile_id == CDPProfile.id,
        ).where(
            CDPSegmentMembership.segment_id == segment_id,
            CDPSegmentMembership.is_member.is_(True),
        )

    # Apply lifecycle stage filter
    if lifecycle_stage:
        query = query.where(CDPProfile.lifecycle_stage == lifecycle_stage)

    # Apply event count filters
    if min_events is not None:
        query = query.where(CDPProfile.total_events >= min_events)
    if max_events is not None:
        query = query.where(CDPProfile.total_events <= max_events)

    # Apply revenue filters
    if min_revenue is not None:
        query = query.where(CDPProfile.total_revenue >= min_revenue)
    if max_revenue is not None:
        query = query.where(CDPProfile.total_revenue <= max_revenue)

    # Apply date filters
    if first_seen_after:
        query = query.where(CDPProfile.first_seen_at >= first_seen_after)
    if first_seen_before:
        query = query.where(CDPProfile.first_seen_at <= first_seen_before)
    if last_seen_after:
        query = query.where(CDPProfile.last_seen_at >= last_seen_after)
    if last_seen_before:
        query = query.where(CDPProfile.last_seen_at <= last_seen_before)

    # Apply RFM segment filter (from computed_traits)
    if rfm_segment:
        query = query.where(
            CDPProfile.computed_traits["rfm_segment"].astext == rfm_segment
        )

    # Apply identifier type filter
    if has_identifier_type:
        query = query.join(
            CDPProfileIdentifier,
            CDPProfileIdentifier.profile_id == CDPProfile.id,
        ).where(
            CDPProfileIdentifier.identifier_type == has_identifier_type,
        )

    # Add eager loading based on options
    if include_identifiers:
        query = query.options(selectinload(CDPProfile.identifiers))

    # Get total count for metadata
    count_query = select(func.count()).select_from(query.subquery())
    total_count_result = await db.execute(count_query)
    total_count = total_count_result.scalar() or 0

    # Apply pagination
    query = query.order_by(CDPProfile.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    profiles = result.scalars().unique().all()

    # Build export data
    export_time = datetime.now(timezone.utc)

    if format.lower() == "csv":
        # Build CSV headers
        headers = [
            "id", "external_id", "lifecycle_stage", "first_seen_at", "last_seen_at",
            "total_events", "total_sessions", "total_purchases", "total_revenue",
        ]
        if include_rfm:
            headers.extend(["rfm_segment", "rfm_score", "recency_score", "frequency_score", "monetary_score"])
        if include_identifiers:
            headers.append("identifier_types")

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()

        for profile in profiles:
            row = {
                "id": str(profile.id),
                "external_id": profile.external_id or "",
                "lifecycle_stage": profile.lifecycle_stage,
                "first_seen_at": profile.first_seen_at.isoformat() if profile.first_seen_at else "",
                "last_seen_at": profile.last_seen_at.isoformat() if profile.last_seen_at else "",
                "total_events": profile.total_events,
                "total_sessions": profile.total_sessions,
                "total_purchases": profile.total_purchases,
                "total_revenue": float(profile.total_revenue),
            }

            if include_rfm and profile.computed_traits:
                row["rfm_segment"] = profile.computed_traits.get("rfm_segment", "")
                row["rfm_score"] = profile.computed_traits.get("rfm_score", "")
                row["recency_score"] = profile.computed_traits.get("recency_score", "")
                row["frequency_score"] = profile.computed_traits.get("frequency_score", "")
                row["monetary_score"] = profile.computed_traits.get("monetary_score", "")

            if include_identifiers and hasattr(profile, 'identifiers'):
                id_types = list(set(i.identifier_type for i in profile.identifiers))
                row["identifier_types"] = ",".join(id_types)

            writer.writerow(row)

        output.seek(0)
        filename = f"audience_export_{tenant_id}_{export_time.strftime('%Y%m%d_%H%M%S')}.csv"
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    else:
        # Generate JSON
        data = []
        for profile in profiles:
            profile_data = {
                "id": str(profile.id),
                "external_id": profile.external_id,
                "lifecycle_stage": profile.lifecycle_stage,
                "first_seen_at": profile.first_seen_at.isoformat() if profile.first_seen_at else None,
                "last_seen_at": profile.last_seen_at.isoformat() if profile.last_seen_at else None,
                "total_events": profile.total_events,
                "total_sessions": profile.total_sessions,
                "total_purchases": profile.total_purchases,
                "total_revenue": float(profile.total_revenue),
            }

            if include_computed_traits:
                profile_data["computed_traits"] = profile.computed_traits or {}

            if include_rfm and profile.computed_traits:
                profile_data["rfm"] = {
                    "segment": profile.computed_traits.get("rfm_segment"),
                    "score": profile.computed_traits.get("rfm_score"),
                    "recency_score": profile.computed_traits.get("recency_score"),
                    "frequency_score": profile.computed_traits.get("frequency_score"),
                    "monetary_score": profile.computed_traits.get("monetary_score"),
                }

            if include_identifiers and hasattr(profile, 'identifiers'):
                profile_data["identifiers"] = [
                    {
                        "type": i.identifier_type,
                        "hash": i.identifier_hash,
                        "is_primary": i.is_primary,
                    }
                    for i in profile.identifiers
                ]

            data.append(profile_data)

        return {
            "format": "json",
            "export_time": export_time.isoformat(),
            "total_matching": total_count,
            "count": len(data),
            "offset": offset,
            "limit": limit,
            "filters_applied": {
                "segment_id": str(segment_id) if segment_id else None,
                "lifecycle_stage": lifecycle_stage,
                "rfm_segment": rfm_segment,
                "min_events": min_events,
                "max_events": max_events,
                "min_revenue": min_revenue,
                "max_revenue": max_revenue,
                "first_seen_after": first_seen_after.isoformat() if first_seen_after else None,
                "first_seen_before": first_seen_before.isoformat() if first_seen_before else None,
                "last_seen_after": last_seen_after.isoformat() if last_seen_after else None,
                "last_seen_before": last_seen_before.isoformat() if last_seen_before else None,
                "has_identifier_type": has_identifier_type,
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


# =============================================================================
# Identity Graph Endpoints
# =============================================================================

@router.get(
    "/profiles/{profile_id}/identity-graph",
    response_model=IdentityGraphResponse,
    summary="Get identity graph for profile",
    description="Get the identity graph showing all identifiers and links for a profile.",
)
async def get_profile_identity_graph(
    profile_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_profile_rate_limit),
):
    """
    Get the identity graph for a profile.

    Returns nodes (identifiers) and edges (links between identifiers).
    Useful for visualizing how a profile's identifiers are connected.
    """
    tenant_id = current_user.tenant_id

    # Verify profile exists
    result = await db.execute(
        select(CDPProfile)
        .where(
            CDPProfile.id == profile_id,
            CDPProfile.tenant_id == tenant_id,
        )
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    # Use identity resolution service to get graph
    service = IdentityResolutionService(db, tenant_id)
    graph_data = await service.get_identity_graph(profile_id)

    return IdentityGraphResponse(
        profile_id=profile_id,
        nodes=[IdentityGraphNode(**n) for n in graph_data["nodes"]],
        edges=[IdentityGraphEdge(**e) for e in graph_data["edges"]],
        total_identifiers=len(graph_data["nodes"]),
        total_links=len(graph_data["edges"]),
    )


@router.get(
    "/profiles/{profile_id}/canonical-identity",
    response_model=CanonicalIdentityResponse,
    summary="Get canonical identity for profile",
    description="Get the canonical (strongest) identity for a profile.",
)
async def get_profile_canonical_identity(
    profile_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_profile_rate_limit),
):
    """
    Get the canonical identity for a profile.

    The canonical identity is the strongest (highest priority) identifier
    for the profile, used for identity resolution decisions.
    """
    tenant_id = current_user.tenant_id

    # Get canonical identity
    result = await db.execute(
        select(CDPCanonicalIdentity)
        .where(
            CDPCanonicalIdentity.profile_id == profile_id,
            CDPCanonicalIdentity.tenant_id == tenant_id,
        )
    )
    canonical = result.scalar_one_or_none()

    if not canonical:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canonical identity not found for profile",
        )

    return CanonicalIdentityResponse(
        id=canonical.id,
        profile_id=canonical.profile_id,
        canonical_type=canonical.canonical_type,
        canonical_value_hash=canonical.canonical_value_hash,
        priority_score=canonical.priority_score,
        is_verified=canonical.is_verified,
        verified_at=canonical.verified_at,
        created_at=canonical.created_at,
        updated_at=canonical.updated_at,
    )


@router.get(
    "/profiles/{profile_id}/merge-history",
    response_model=ProfileMergeHistoryResponse,
    summary="Get merge history for profile",
    description="Get the history of profile merges involving this profile.",
)
async def get_profile_merge_history(
    profile_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_profile_rate_limit),
):
    """
    Get the merge history for a profile.

    Shows all merges where this profile was either the surviving profile
    or a profile that was merged into it.
    """
    tenant_id = current_user.tenant_id

    # Get merges where this profile was involved
    result = await db.execute(
        select(CDPProfileMerge)
        .where(
            CDPProfileMerge.tenant_id == tenant_id,
            CDPProfileMerge.surviving_profile_id == profile_id,
        )
        .order_by(CDPProfileMerge.created_at.desc())
    )
    merges = result.scalars().all()

    return ProfileMergeHistoryResponse(
        merges=[
            ProfileMergeResponse(
                id=m.id,
                surviving_profile_id=m.surviving_profile_id,
                merged_profile_id=m.merged_profile_id,
                merge_reason=m.merge_reason,
                merged_event_count=m.merged_event_count,
                merged_identifier_count=m.merged_identifier_count,
                is_rolled_back=m.is_rolled_back,
                created_at=m.created_at,
            )
            for m in merges
        ],
        total=len(merges),
    )


@router.post(
    "/profiles/merge",
    response_model=ProfileMergeResponse,
    summary="Manually merge profiles",
    description="Manually merge two profiles into one.",
)
async def merge_profiles(
    merge_request: ProfileMergeRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_source_rate_limit),
):
    """
    Manually merge two profiles.

    The source profile will be merged into the target profile:
    - All identifiers will be moved to target
    - All events will be moved to target
    - All consents will be merged
    - Source profile will be deleted
    """
    tenant_id = current_user.tenant_id

    if merge_request.source_profile_id == merge_request.target_profile_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot merge a profile with itself",
        )

    # Get both profiles
    source_result = await db.execute(
        select(CDPProfile)
        .where(
            CDPProfile.id == merge_request.source_profile_id,
            CDPProfile.tenant_id == tenant_id,
        )
        .options(selectinload(CDPProfile.identifiers))
    )
    source_profile = source_result.scalar_one_or_none()

    target_result = await db.execute(
        select(CDPProfile)
        .where(
            CDPProfile.id == merge_request.target_profile_id,
            CDPProfile.tenant_id == tenant_id,
        )
        .options(selectinload(CDPProfile.identifiers))
    )
    target_profile = target_result.scalar_one_or_none()

    if not source_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source profile not found",
        )

    if not target_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target profile not found",
        )

    # Perform merge using identity resolution service
    service = IdentityResolutionService(db, tenant_id)
    merge_record = await service.merge_profiles(
        surviving_profile=target_profile,
        merged_profile=source_profile,
        merge_reason=MergeReason.MANUAL_MERGE,
        merged_by_user_id=current_user.id if hasattr(current_user, "id") else None,
    )

    await db.commit()

    # Invalidate cache for both profiles
    _profile_cache.invalidate(tenant_id, str(merge_request.source_profile_id))
    _profile_cache.invalidate(tenant_id, str(merge_request.target_profile_id))

    logger.info(
        "cdp_manual_profile_merge",
        tenant_id=tenant_id,
        source_profile_id=str(merge_request.source_profile_id),
        target_profile_id=str(merge_request.target_profile_id),
        merged_by=current_user.id if hasattr(current_user, "id") else None,
    )

    return ProfileMergeResponse(
        id=merge_record.id,
        surviving_profile_id=merge_record.surviving_profile_id,
        merged_profile_id=merge_record.merged_profile_id,
        merge_reason=merge_record.merge_reason,
        merged_event_count=merge_record.merged_event_count,
        merged_identifier_count=merge_record.merged_identifier_count,
        is_rolled_back=merge_record.is_rolled_back,
        created_at=merge_record.created_at,
    )


@router.get(
    "/merge-history",
    response_model=ProfileMergeHistoryResponse,
    summary="List all profile merges",
    description="List all profile merges for the tenant.",
)
async def list_merge_history(
    limit: int = Query(50, ge=1, le=200, description="Max merges to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_profile_rate_limit),
):
    """
    List all profile merges for the tenant.

    Shows a history of all automatic and manual merges.
    """
    tenant_id = current_user.tenant_id

    # Get total count
    count_result = await db.execute(
        select(func.count(CDPProfileMerge.id))
        .where(CDPProfileMerge.tenant_id == tenant_id)
    )
    total = count_result.scalar() or 0

    # Get merges
    result = await db.execute(
        select(CDPProfileMerge)
        .where(CDPProfileMerge.tenant_id == tenant_id)
        .order_by(CDPProfileMerge.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    merges = result.scalars().all()

    return ProfileMergeHistoryResponse(
        merges=[
            ProfileMergeResponse(
                id=m.id,
                surviving_profile_id=m.surviving_profile_id,
                merged_profile_id=m.merged_profile_id,
                merge_reason=m.merge_reason,
                merged_event_count=m.merged_event_count,
                merged_identifier_count=m.merged_identifier_count,
                is_rolled_back=m.is_rolled_back,
                created_at=m.created_at,
            )
            for m in merges
        ],
        total=total,
    )


@router.get(
    "/identity-links",
    summary="List identity links",
    description="List identity links (graph edges) for the tenant.",
)
async def list_identity_links(
    limit: int = Query(100, ge=1, le=500, description="Max links to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    link_type: Optional[str] = Query(None, description="Filter by link type"),
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_profile_rate_limit),
):
    """
    List identity links for the tenant.

    Identity links represent relationships between identifiers in the graph.
    """
    tenant_id = current_user.tenant_id

    # Build query
    query = select(CDPIdentityLink).where(CDPIdentityLink.tenant_id == tenant_id)

    if link_type:
        query = query.where(CDPIdentityLink.link_type == link_type)

    # Get total count
    count_query = select(func.count(CDPIdentityLink.id)).where(CDPIdentityLink.tenant_id == tenant_id)
    if link_type:
        count_query = count_query.where(CDPIdentityLink.link_type == link_type)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Get links
    result = await db.execute(
        query.order_by(CDPIdentityLink.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    links = result.scalars().all()

    return {
        "links": [
            {
                "id": str(link.id),
                "source_identifier_id": str(link.source_identifier_id),
                "target_identifier_id": str(link.target_identifier_id),
                "link_type": link.link_type,
                "confidence_score": float(link.confidence_score),
                "is_active": link.is_active,
                "evidence": link.evidence,
                "created_at": link.created_at.isoformat(),
            }
            for link in links
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# =============================================================================
# Segment Builder Endpoints
# =============================================================================

segment_rate_limiter = RateLimiter(requests_per_minute=60)


async def check_segment_rate_limit(
    request: Request,
    current_user = Depends(get_current_user),
) -> bool:
    """Check segment rate limit (60/min)."""
    tenant_id = current_user.tenant_id
    if not segment_rate_limiter.is_allowed(f"segment:{tenant_id}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Segment rate limit exceeded. Max 60 requests per minute.",
        )
    return True


def _segment_to_response(segment: CDPSegment) -> SegmentResponse:
    """Convert segment model to response schema."""
    return SegmentResponse(
        id=segment.id,
        name=segment.name,
        slug=segment.slug,
        description=segment.description,
        segment_type=segment.segment_type,
        status=segment.status,
        rules=segment.rules or {},
        profile_count=segment.profile_count,
        last_computed_at=segment.last_computed_at,
        computation_duration_ms=segment.computation_duration_ms,
        auto_refresh=segment.auto_refresh,
        refresh_interval_hours=segment.refresh_interval_hours,
        next_refresh_at=segment.next_refresh_at,
        tags=segment.tags or [],
        created_by_user_id=segment.created_by_user_id,
        created_at=segment.created_at,
        updated_at=segment.updated_at,
    )


@router.post(
    "/segments",
    response_model=SegmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new segment",
    description="Create a new customer segment with rules for dynamic evaluation.",
)
async def create_segment(
    segment_data: SegmentCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_segment_rate_limit),
):
    """
    Create a new customer segment.

    Segments can be:
    - **static**: Manual membership management
    - **dynamic**: Rule-based, auto-computed
    - **computed**: ML/algorithm-based
    """
    tenant_id = current_user.tenant_id

    service = SegmentService(db, tenant_id)
    segment = await service.create_segment(
        name=segment_data.name,
        rules=segment_data.rules.model_dump(),
        segment_type=segment_data.segment_type,
        description=segment_data.description,
        tags=segment_data.tags,
        auto_refresh=segment_data.auto_refresh,
        refresh_interval_hours=segment_data.refresh_interval_hours,
        created_by_user_id=current_user.id if hasattr(current_user, "id") else None,
    )

    await db.commit()

    logger.info(
        "cdp_segment_created",
        tenant_id=tenant_id,
        segment_id=str(segment.id),
        segment_name=segment.name,
    )

    return _segment_to_response(segment)


@router.get(
    "/segments",
    response_model=SegmentListResponse,
    summary="List segments",
    description="List all segments for the tenant.",
)
async def list_segments(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    segment_type: Optional[str] = Query(None, description="Filter by type"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_segment_rate_limit),
):
    """List all segments for the tenant."""
    tenant_id = current_user.tenant_id

    service = SegmentService(db, tenant_id)
    segments, total = await service.list_segments(
        status=status_filter,
        segment_type=segment_type,
        limit=limit,
        offset=offset,
    )

    return SegmentListResponse(
        segments=[_segment_to_response(s) for s in segments],
        total=total,
    )


@router.get(
    "/segments/{segment_id}",
    response_model=SegmentResponse,
    summary="Get segment by ID",
    description="Get a segment by its ID.",
)
async def get_segment(
    segment_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_segment_rate_limit),
):
    """Get a segment by ID."""
    tenant_id = current_user.tenant_id

    service = SegmentService(db, tenant_id)
    segment = await service.get_segment(segment_id)

    if not segment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Segment not found",
        )

    return _segment_to_response(segment)


@router.patch(
    "/segments/{segment_id}",
    response_model=SegmentResponse,
    summary="Update a segment",
    description="Update segment configuration.",
)
async def update_segment(
    segment_id: UUID,
    update_data: SegmentUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_segment_rate_limit),
):
    """Update a segment."""
    tenant_id = current_user.tenant_id

    service = SegmentService(db, tenant_id)

    # Build updates dict
    updates = {}
    if update_data.name is not None:
        updates["name"] = update_data.name
    if update_data.description is not None:
        updates["description"] = update_data.description
    if update_data.rules is not None:
        updates["rules"] = update_data.rules.model_dump()
    if update_data.tags is not None:
        updates["tags"] = update_data.tags
    if update_data.auto_refresh is not None:
        updates["auto_refresh"] = update_data.auto_refresh
    if update_data.refresh_interval_hours is not None:
        updates["refresh_interval_hours"] = update_data.refresh_interval_hours

    segment = await service.update_segment(segment_id, **updates)

    if not segment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Segment not found",
        )

    await db.commit()

    return _segment_to_response(segment)


@router.delete(
    "/segments/{segment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a segment",
    description="Delete a segment and all its memberships.",
)
async def delete_segment(
    segment_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_segment_rate_limit),
):
    """Delete a segment."""
    tenant_id = current_user.tenant_id

    service = SegmentService(db, tenant_id)
    deleted = await service.delete_segment(segment_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Segment not found",
        )

    await db.commit()

    logger.info(
        "cdp_segment_deleted",
        tenant_id=tenant_id,
        segment_id=str(segment_id),
    )


@router.post(
    "/segments/{segment_id}/compute",
    response_model=SegmentResponse,
    summary="Compute segment membership",
    description="Compute or recompute segment membership for all profiles.",
)
async def compute_segment(
    segment_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_segment_rate_limit),
):
    """
    Compute segment membership.

    This evaluates all profiles against segment rules and updates membership.
    For large datasets, this is a long-running operation.
    """
    tenant_id = current_user.tenant_id

    service = SegmentService(db, tenant_id)
    segment = await service.get_segment(segment_id)

    if not segment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Segment not found",
        )

    added, removed = await service.compute_segment(segment_id)
    await db.commit()

    # Refresh segment data
    segment = await service.get_segment(segment_id)

    logger.info(
        "cdp_segment_computed",
        tenant_id=tenant_id,
        segment_id=str(segment_id),
        profiles_added=added,
        profiles_removed=removed,
    )

    return _segment_to_response(segment)


@router.post(
    "/segments/preview",
    response_model=SegmentPreviewResponse,
    summary="Preview segment membership",
    description="Preview which profiles would match segment rules without saving.",
)
async def preview_segment(
    preview_data: SegmentPreviewRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_segment_rate_limit),
):
    """
    Preview segment membership.

    Returns estimated count and sample profiles that match the rules.
    Does not create or modify any data.
    """
    tenant_id = current_user.tenant_id

    service = SegmentService(db, tenant_id)
    estimated_count, sample_profiles = await service.preview_segment(
        rules=preview_data.rules.model_dump(),
        limit=preview_data.limit,
    )

    # Convert profiles to response format
    profile_responses = []
    for p in sample_profiles:
        profile_responses.append(
            ProfileResponse(
                id=p.id,
                tenant_id=p.tenant_id,
                external_id=p.external_id,
                first_seen_at=p.first_seen_at,
                last_seen_at=p.last_seen_at,
                profile_data=p.profile_data or {},
                computed_traits=p.computed_traits or {},
                lifecycle_stage=p.lifecycle_stage,
                total_events=p.total_events,
                total_sessions=p.total_sessions,
                total_purchases=p.total_purchases,
                total_revenue=p.total_revenue,
                identifiers=[],
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
        )

    return SegmentPreviewResponse(
        estimated_count=estimated_count,
        sample_profiles=profile_responses,
    )


@router.get(
    "/segments/{segment_id}/profiles",
    response_model=SegmentProfilesResponse,
    summary="Get profiles in segment",
    description="Get all profiles that belong to a segment.",
)
async def get_segment_profiles(
    segment_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_profile_rate_limit),
):
    """Get profiles in a segment."""
    tenant_id = current_user.tenant_id

    service = SegmentService(db, tenant_id)
    profiles, total = await service.get_segment_profiles(
        segment_id=segment_id,
        limit=limit,
        offset=offset,
    )

    # Convert to response
    profile_responses = []
    for p in profiles:
        profile_responses.append(
            ProfileResponse(
                id=p.id,
                tenant_id=p.tenant_id,
                external_id=p.external_id,
                first_seen_at=p.first_seen_at,
                last_seen_at=p.last_seen_at,
                profile_data=p.profile_data or {},
                computed_traits=p.computed_traits or {},
                lifecycle_stage=p.lifecycle_stage,
                total_events=p.total_events,
                total_sessions=p.total_sessions,
                total_purchases=p.total_purchases,
                total_revenue=p.total_revenue,
                identifiers=[
                    IdentifierResponse(
                        id=i.id,
                        identifier_type=i.identifier_type,
                        identifier_hash=i.identifier_hash,
                        is_primary=i.is_primary,
                        confidence_score=i.confidence_score,
                        verified_at=i.verified_at,
                        first_seen_at=i.first_seen_at,
                        last_seen_at=i.last_seen_at,
                    )
                    for i in (p.identifiers or [])
                ],
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
        )

    return SegmentProfilesResponse(
        profiles=profile_responses,
        total=total,
    )


@router.get(
    "/profiles/{profile_id}/segments",
    response_model=ProfileSegmentsResponse,
    summary="Get profile segments",
    description="Get all segments a profile belongs to.",
)
async def get_profile_segments(
    profile_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_profile_rate_limit),
):
    """Get all segments a profile belongs to."""
    tenant_id = current_user.tenant_id

    service = SegmentService(db, tenant_id)
    segments = await service.get_profile_segments(profile_id)

    return ProfileSegmentsResponse(
        segments=[_segment_to_response(s) for s in segments],
    )


@router.post(
    "/segments/{segment_id}/profiles/{profile_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Add profile to segment",
    description="Manually add a profile to a static segment.",
)
async def add_profile_to_segment(
    segment_id: UUID,
    profile_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_segment_rate_limit),
):
    """
    Add a profile to a static segment.

    Only works for static segments. Dynamic segments are computed automatically.
    """
    tenant_id = current_user.tenant_id

    service = SegmentService(db, tenant_id)
    success = await service.add_profile_to_segment(
        segment_id=segment_id,
        profile_id=profile_id,
        added_by_user_id=current_user.id if hasattr(current_user, "id") else None,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add profile to segment. Segment may not exist or may not be a static segment.",
        )

    await db.commit()

    return {"success": True, "message": "Profile added to segment"}


@router.delete(
    "/segments/{segment_id}/profiles/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove profile from segment",
    description="Remove a profile from a segment.",
)
async def remove_profile_from_segment(
    segment_id: UUID,
    profile_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_segment_rate_limit),
):
    """Remove a profile from a segment."""
    tenant_id = current_user.tenant_id

    service = SegmentService(db, tenant_id)
    success = await service.remove_profile_from_segment(
        segment_id=segment_id,
        profile_id=profile_id,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found in segment",
        )

    await db.commit()


# =============================================================================
# Profile Deletion (GDPR) Endpoints
# =============================================================================

@router.delete(
    "/profiles/{profile_id}",
    response_model=ProfileDeletionResponse,
    summary="Delete profile (GDPR)",
    description="Delete a profile and optionally all associated data (GDPR right to erasure).",
)
async def delete_profile(
    profile_id: UUID,
    delete_events: bool = Query(True, description="Also delete all events"),
    reason: Optional[str] = Query(None, description="Reason for deletion"),
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_source_rate_limit),
):
    """
    Delete a profile (GDPR right to erasure).

    This permanently deletes:
    - The profile record
    - All identifiers
    - All consents
    - All segment memberships
    - Optionally: all events (if delete_events=True)

    This action cannot be undone.
    """
    tenant_id = current_user.tenant_id

    # Verify profile exists
    result = await db.execute(
        select(CDPProfile)
        .where(
            CDPProfile.id == profile_id,
            CDPProfile.tenant_id == tenant_id,
        )
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    # Count items to be deleted
    events_deleted = 0
    if delete_events:
        events_result = await db.execute(
            select(func.count(CDPEvent.id))
            .where(CDPEvent.profile_id == profile_id)
        )
        events_deleted = events_result.scalar() or 0

    identifiers_result = await db.execute(
        select(func.count(CDPProfileIdentifier.id))
        .where(CDPProfileIdentifier.profile_id == profile_id)
    )
    identifiers_deleted = identifiers_result.scalar() or 0

    consents_result = await db.execute(
        select(func.count(CDPConsent.id))
        .where(CDPConsent.profile_id == profile_id)
    )
    consents_deleted = consents_result.scalar() or 0

    memberships_result = await db.execute(
        select(func.count(CDPSegmentMembership.id))
        .where(CDPSegmentMembership.profile_id == profile_id)
    )
    memberships_deleted = memberships_result.scalar() or 0

    # Delete events if requested
    if delete_events:
        await db.execute(
            delete(CDPEvent).where(CDPEvent.profile_id == profile_id)
        )

    # Delete segment memberships
    await db.execute(
        delete(CDPSegmentMembership).where(CDPSegmentMembership.profile_id == profile_id)
    )

    # Delete consents
    await db.execute(
        delete(CDPConsent).where(CDPConsent.profile_id == profile_id)
    )

    # Delete identifiers
    await db.execute(
        delete(CDPProfileIdentifier).where(CDPProfileIdentifier.profile_id == profile_id)
    )

    # Delete canonical identity if exists
    await db.execute(
        delete(CDPCanonicalIdentity).where(CDPCanonicalIdentity.profile_id == profile_id)
    )

    # Delete profile
    await db.delete(profile)
    await db.commit()

    # Invalidate cache
    _profile_cache.invalidate(tenant_id, str(profile_id))

    deletion_time = datetime.now(timezone.utc)

    logger.info(
        "cdp_profile_deleted_gdpr",
        tenant_id=tenant_id,
        profile_id=str(profile_id),
        events_deleted=events_deleted,
        identifiers_deleted=identifiers_deleted,
        reason=reason,
        deleted_by=current_user.id if hasattr(current_user, "id") else None,
    )

    return ProfileDeletionResponse(
        profile_id=profile_id,
        deleted=True,
        events_deleted=events_deleted,
        identifiers_deleted=identifiers_deleted,
        consents_deleted=consents_deleted,
        segment_memberships_deleted=memberships_deleted,
        deletion_timestamp=deletion_time,
    )


# =============================================================================
# Computed Traits Endpoints
# =============================================================================

def _trait_to_response(trait) -> ComputedTraitResponse:
    """Convert trait model to response."""
    return ComputedTraitResponse(
        id=trait.id,
        name=trait.name,
        display_name=trait.display_name,
        description=trait.description,
        trait_type=trait.trait_type,
        source_config=trait.source_config or {},
        output_type=trait.output_type,
        default_value=trait.default_value,
        is_active=trait.is_active,
        last_computed_at=trait.last_computed_at,
        created_at=trait.created_at,
        updated_at=trait.updated_at,
    )


@router.post(
    "/traits",
    response_model=ComputedTraitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create computed trait",
    description="Create a new computed trait definition.",
)
async def create_computed_trait(
    trait_data: ComputedTraitCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_source_rate_limit),
):
    """
    Create a new computed trait.

    Computed traits are derived values calculated from profile events.
    Examples: total_purchases, average_order_value, days_since_last_login
    """
    tenant_id = current_user.tenant_id

    service = ComputedTraitsService(db, tenant_id)

    # Check if trait already exists
    existing = await service.get_trait_by_name(trait_data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Trait with name '{trait_data.name}' already exists",
        )

    trait = await service.create_trait(
        name=trait_data.name,
        display_name=trait_data.display_name,
        trait_type=trait_data.trait_type,
        source_config=trait_data.source_config.model_dump(),
        description=trait_data.description,
        output_type=trait_data.output_type,
        default_value=trait_data.default_value,
    )

    await db.commit()

    return _trait_to_response(trait)


@router.get(
    "/traits",
    response_model=ComputedTraitListResponse,
    summary="List computed traits",
    description="List all computed trait definitions.",
)
async def list_computed_traits(
    active_only: bool = Query(True, description="Only show active traits"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_source_rate_limit),
):
    """List all computed traits."""
    tenant_id = current_user.tenant_id

    service = ComputedTraitsService(db, tenant_id)
    traits, total = await service.list_traits(
        active_only=active_only,
        limit=limit,
        offset=offset,
    )

    return ComputedTraitListResponse(
        traits=[_trait_to_response(t) for t in traits],
        total=total,
    )


@router.get(
    "/traits/{trait_id}",
    response_model=ComputedTraitResponse,
    summary="Get computed trait",
    description="Get a computed trait by ID.",
)
async def get_computed_trait(
    trait_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_source_rate_limit),
):
    """Get a computed trait by ID."""
    tenant_id = current_user.tenant_id

    service = ComputedTraitsService(db, tenant_id)
    trait = await service.get_trait(trait_id)

    if not trait:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Computed trait not found",
        )

    return _trait_to_response(trait)


@router.delete(
    "/traits/{trait_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete computed trait",
    description="Delete a computed trait definition.",
)
async def delete_computed_trait(
    trait_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_source_rate_limit),
):
    """Delete a computed trait."""
    tenant_id = current_user.tenant_id

    service = ComputedTraitsService(db, tenant_id)
    deleted = await service.delete_trait(trait_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Computed trait not found",
        )

    await db.commit()


@router.post(
    "/traits/compute",
    response_model=ComputeTraitsResponse,
    summary="Compute all traits",
    description="Compute all active traits for all profiles.",
)
async def compute_all_traits(
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_source_rate_limit),
):
    """
    Compute all active traits for all profiles.

    This is a batch operation that may take time for large datasets.
    """
    tenant_id = current_user.tenant_id

    service = ComputedTraitsService(db, tenant_id)
    processed, errors = await service.compute_traits_batch()

    await db.commit()

    logger.info(
        "cdp_traits_computed",
        tenant_id=tenant_id,
        profiles_processed=processed,
        errors=errors,
    )

    return ComputeTraitsResponse(
        profiles_processed=processed,
        errors=errors,
    )


@router.post(
    "/profiles/{profile_id}/compute-traits",
    summary="Compute traits for profile",
    description="Compute all traits for a specific profile.",
)
async def compute_traits_for_profile(
    profile_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_profile_rate_limit),
):
    """Compute all traits for a specific profile."""
    tenant_id = current_user.tenant_id

    # Get profile
    result = await db.execute(
        select(CDPProfile)
        .where(
            CDPProfile.id == profile_id,
            CDPProfile.tenant_id == tenant_id,
        )
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    service = ComputedTraitsService(db, tenant_id)
    computed_traits = await service.compute_all_traits_for_profile(profile)

    await db.commit()

    # Invalidate cache
    _profile_cache.invalidate(tenant_id, str(profile_id))

    return {
        "profile_id": str(profile_id),
        "computed_traits": computed_traits,
    }


# =============================================================================
# RFM Analysis Endpoints
# =============================================================================

@router.get(
    "/profiles/{profile_id}/rfm",
    response_model=RFMScores,
    summary="Get RFM scores for profile",
    description="Calculate RFM (Recency, Frequency, Monetary) scores for a profile.",
)
async def get_profile_rfm(
    profile_id: UUID,
    purchase_event_name: str = Query("Purchase", description="Event name for purchases"),
    revenue_property: str = Query("total", description="Property containing revenue"),
    analysis_window_days: int = Query(365, ge=30, le=1095),
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_profile_rate_limit),
):
    """
    Calculate RFM scores for a profile.

    RFM Analysis segments customers based on:
    - **Recency**: How recently did they purchase?
    - **Frequency**: How often do they purchase?
    - **Monetary**: How much do they spend?
    """
    tenant_id = current_user.tenant_id

    # Get profile
    result = await db.execute(
        select(CDPProfile)
        .where(
            CDPProfile.id == profile_id,
            CDPProfile.tenant_id == tenant_id,
        )
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    service = RFMAnalysisService(db, tenant_id)
    rfm = await service.calculate_rfm_for_profile(
        profile,
        purchase_event_name=purchase_event_name,
        revenue_property=revenue_property,
        analysis_window_days=analysis_window_days,
    )

    return RFMScores(**rfm)


@router.post(
    "/rfm/compute",
    response_model=RFMBatchResponse,
    summary="Compute RFM for all profiles",
    description="Calculate RFM scores for all profiles and store in computed_traits.",
)
async def compute_rfm_batch(
    config: Optional[RFMConfig] = None,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_source_rate_limit),
):
    """
    Compute RFM scores for all profiles.

    Results are stored in each profile's computed_traits field.
    """
    tenant_id = current_user.tenant_id

    # Use defaults if not provided
    if config is None:
        config = RFMConfig()

    service = RFMAnalysisService(db, tenant_id)
    result = await service.calculate_rfm_batch(
        purchase_event_name=config.purchase_event_name,
        revenue_property=config.revenue_property,
        analysis_window_days=config.analysis_window_days,
    )

    await db.commit()

    logger.info(
        "cdp_rfm_batch_computed",
        tenant_id=tenant_id,
        profiles_processed=result["profiles_processed"],
    )

    return RFMBatchResponse(**result)


@router.get(
    "/rfm/summary",
    response_model=RFMSummaryResponse,
    summary="Get RFM summary",
    description="Get RFM segment distribution summary.",
)
async def get_rfm_summary(
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_profile_rate_limit),
):
    """
    Get RFM summary for the tenant.

    Returns segment distribution and coverage statistics.
    """
    tenant_id = current_user.tenant_id

    service = RFMAnalysisService(db, tenant_id)
    summary = await service.get_rfm_summary()

    return RFMSummaryResponse(**summary)


# =============================================================================
# Funnel/Journey Analysis Endpoints
# =============================================================================

funnel_rate_limiter = RateLimiter(requests_per_minute=60)


async def check_funnel_rate_limit(
    request: Request,
    current_user = Depends(get_current_user),
) -> bool:
    """Check funnel rate limit (60/min)."""
    tenant_id = current_user.tenant_id
    if not funnel_rate_limiter.is_allowed(f"funnel:{tenant_id}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Funnel rate limit exceeded. Max 60 requests per minute.",
        )
    return True


def _funnel_to_response(funnel: CDPFunnel) -> FunnelResponse:
    """Convert funnel model to response schema."""
    return FunnelResponse(
        id=funnel.id,
        name=funnel.name,
        slug=funnel.slug,
        description=funnel.description,
        status=funnel.status,
        steps=funnel.steps or [],
        conversion_window_days=funnel.conversion_window_days,
        step_timeout_hours=funnel.step_timeout_hours,
        total_entered=funnel.total_entered,
        total_converted=funnel.total_converted,
        overall_conversion_rate=funnel.overall_conversion_rate,
        step_metrics=funnel.step_metrics or [],
        last_computed_at=funnel.last_computed_at,
        computation_duration_ms=funnel.computation_duration_ms,
        auto_refresh=funnel.auto_refresh,
        refresh_interval_hours=funnel.refresh_interval_hours,
        next_refresh_at=funnel.next_refresh_at,
        tags=funnel.tags or [],
        created_by_user_id=funnel.created_by_user_id,
        created_at=funnel.created_at,
        updated_at=funnel.updated_at,
    )


@router.post(
    "/funnels",
    response_model=FunnelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new funnel",
    description="Create a new conversion funnel for tracking user journeys.",
)
async def create_funnel(
    funnel_data: FunnelCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_funnel_rate_limit),
):
    """
    Create a new conversion funnel.

    Funnels track user progression through a series of events.
    Example: Product View → Add to Cart → Checkout → Purchase
    """
    tenant_id = current_user.tenant_id

    service = FunnelService(db, tenant_id)
    funnel = await service.create_funnel(
        name=funnel_data.name,
        steps=[s.model_dump() for s in funnel_data.steps],
        description=funnel_data.description,
        conversion_window_days=funnel_data.conversion_window_days,
        step_timeout_hours=funnel_data.step_timeout_hours,
        auto_refresh=funnel_data.auto_refresh,
        refresh_interval_hours=funnel_data.refresh_interval_hours,
        tags=funnel_data.tags,
        created_by_user_id=current_user.id if hasattr(current_user, "id") else None,
    )

    await db.commit()

    logger.info(
        "cdp_funnel_created",
        tenant_id=tenant_id,
        funnel_id=str(funnel.id),
        funnel_name=funnel.name,
        steps_count=len(funnel_data.steps),
    )

    return _funnel_to_response(funnel)


@router.get(
    "/funnels",
    response_model=FunnelListResponse,
    summary="List funnels",
    description="List all funnels for the tenant.",
)
async def list_funnels(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_funnel_rate_limit),
):
    """List all funnels for the tenant."""
    tenant_id = current_user.tenant_id

    service = FunnelService(db, tenant_id)
    funnels, total = await service.list_funnels(
        status=status_filter,
        limit=limit,
        offset=offset,
    )

    return FunnelListResponse(
        funnels=[_funnel_to_response(f) for f in funnels],
        total=total,
    )


@router.get(
    "/funnels/{funnel_id}",
    response_model=FunnelResponse,
    summary="Get funnel by ID",
    description="Get a funnel by its ID.",
)
async def get_funnel(
    funnel_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_funnel_rate_limit),
):
    """Get a funnel by ID."""
    tenant_id = current_user.tenant_id

    service = FunnelService(db, tenant_id)
    funnel = await service.get_funnel(funnel_id)

    if not funnel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funnel not found",
        )

    return _funnel_to_response(funnel)


@router.patch(
    "/funnels/{funnel_id}",
    response_model=FunnelResponse,
    summary="Update a funnel",
    description="Update funnel configuration.",
)
async def update_funnel(
    funnel_id: UUID,
    update_data: FunnelUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_funnel_rate_limit),
):
    """Update a funnel."""
    tenant_id = current_user.tenant_id

    service = FunnelService(db, tenant_id)

    # Convert update data to dict, handling steps specially
    updates = update_data.model_dump(exclude_unset=True)
    if "steps" in updates and updates["steps"] is not None:
        updates["steps"] = [s if isinstance(s, dict) else s.model_dump() for s in update_data.steps]

    funnel = await service.update_funnel(funnel_id, **updates)

    if not funnel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funnel not found",
        )

    await db.commit()

    logger.info(
        "cdp_funnel_updated",
        tenant_id=tenant_id,
        funnel_id=str(funnel_id),
        updates=list(updates.keys()),
    )

    return _funnel_to_response(funnel)


@router.delete(
    "/funnels/{funnel_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a funnel",
    description="Delete a funnel and all its entries.",
)
async def delete_funnel(
    funnel_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_funnel_rate_limit),
):
    """Delete a funnel."""
    tenant_id = current_user.tenant_id

    service = FunnelService(db, tenant_id)
    deleted = await service.delete_funnel(funnel_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funnel not found",
        )

    await db.commit()


@router.post(
    "/funnels/{funnel_id}/compute",
    response_model=FunnelComputeResponse,
    summary="Compute funnel metrics",
    description="Compute conversion metrics for the funnel by analyzing all profiles.",
)
async def compute_funnel(
    funnel_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_funnel_rate_limit),
):
    """
    Compute funnel metrics.

    This analyzes all profiles' events to calculate:
    - Step-by-step conversion rates
    - Drop-off points
    - Overall conversion rate
    """
    tenant_id = current_user.tenant_id

    service = FunnelService(db, tenant_id)

    try:
        result = await service.compute_funnel(funnel_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    await db.commit()

    return FunnelComputeResponse(
        funnel_id=result["funnel_id"],
        total_entered=result["total_entered"],
        total_converted=result["total_converted"],
        overall_conversion_rate=result["overall_conversion_rate"],
        step_metrics=result["step_metrics"],
        computation_duration_ms=result["computation_duration_ms"],
    )


@router.post(
    "/funnels/{funnel_id}/analyze",
    response_model=FunnelAnalysisResponse,
    summary="Analyze funnel with date filtering",
    description="Get detailed funnel analysis with optional date filtering.",
)
async def analyze_funnel(
    funnel_id: UUID,
    analysis_request: Optional[FunnelAnalysisRequest] = None,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_funnel_rate_limit),
):
    """
    Get detailed funnel analysis.

    Optionally filter by date range to see funnel performance over time.
    """
    tenant_id = current_user.tenant_id

    service = FunnelService(db, tenant_id)

    start_date = analysis_request.start_date if analysis_request else None
    end_date = analysis_request.end_date if analysis_request else None

    try:
        result = await service.get_funnel_analysis(
            funnel_id,
            start_date=start_date,
            end_date=end_date,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return FunnelAnalysisResponse(**result)


@router.get(
    "/funnels/{funnel_id}/drop-offs/{step}",
    response_model=FunnelDropOffResponse,
    summary="Get profiles that dropped off at a step",
    description="Get profiles that completed a step but didn't proceed to the next.",
)
async def get_funnel_drop_offs(
    funnel_id: UUID,
    step: int = Query(..., ge=1, description="Step number (1-indexed)"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_funnel_rate_limit),
):
    """
    Get profiles that dropped off at a specific funnel step.

    Useful for identifying users who need re-engagement.
    """
    tenant_id = current_user.tenant_id

    service = FunnelService(db, tenant_id)

    # Verify funnel exists
    funnel = await service.get_funnel(funnel_id)
    if not funnel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funnel not found",
        )

    if step > len(funnel.steps):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Step {step} does not exist. Funnel has {len(funnel.steps)} steps.",
        )

    profiles, total = await service.get_funnel_drop_off_profiles(
        funnel_id,
        at_step=step,
        limit=limit,
        offset=offset,
    )

    return FunnelDropOffResponse(
        funnel_id=str(funnel_id),
        step=step,
        profiles=[
            ProfileResponse(
                id=p.id,
                tenant_id=p.tenant_id,
                external_id=p.external_id,
                first_seen_at=p.first_seen_at,
                last_seen_at=p.last_seen_at,
                profile_data=p.profile_data or {},
                computed_traits=p.computed_traits or {},
                lifecycle_stage=p.lifecycle_stage,
                total_events=p.total_events,
                total_sessions=p.total_sessions,
                total_purchases=p.total_purchases,
                total_revenue=p.total_revenue,
                identifiers=[],  # Don't include for performance
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in profiles
        ],
        total=total,
    )


@router.get(
    "/profiles/{profile_id}/funnels",
    response_model=ProfileFunnelJourneysResponse,
    summary="Get profile's funnel journeys",
    description="Get a profile's journey through all funnels.",
)
async def get_profile_funnel_journeys(
    profile_id: UUID,
    funnel_id: Optional[UUID] = Query(None, description="Filter by specific funnel"),
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user),
    _rate_limit = Depends(check_profile_rate_limit),
):
    """
    Get a profile's journey through funnels.

    Shows which funnels the user has entered and their progress.
    """
    tenant_id = current_user.tenant_id

    # Verify profile exists
    result = await db.execute(
        select(CDPProfile)
        .where(
            CDPProfile.id == profile_id,
            CDPProfile.tenant_id == tenant_id,
        )
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    service = FunnelService(db, tenant_id)
    journeys = await service.get_profile_funnel_journey(profile_id, funnel_id)

    return ProfileFunnelJourneysResponse(
        profile_id=str(profile_id),
        journeys=journeys,
    )
