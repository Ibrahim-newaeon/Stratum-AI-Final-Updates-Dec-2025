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
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
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
)

logger = structlog.get_logger()

router = APIRouter(prefix="/cdp", tags=["CDP"])


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
):
    """Get profile by ID."""
    tenant_id = current_user.tenant_id

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
):
    """Lookup profile by identifier."""
    tenant_id = current_user.tenant_id

    # Normalize and hash the identifier
    normalized = normalize_identifier(identifier_type, identifier_value)
    ident_hash = hash_identifier(normalized)

    # Find identifier
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

    profile = ident.profile
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
        "version": "1.0.0",
    }
