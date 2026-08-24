# =============================================================================
# Stratum AI - Drip Enrollment
# =============================================================================
"""Puts recipients into a drip sequence and takes them back out.

Every entry point — the manual trigger endpoint, the CDP event hooks, the
scheduled scans — goes through :func:`enroll_sync` or :func:`enroll_async`, so
suppression and double-enrollment are checked in exactly one place.

The API holds an ``AsyncSession`` and the Celery worker holds a
``SyncSessionLocal`` (an async session inside a Celery task is what abandoned
asyncpg sockets in the 2026-08-17 outage). Rather than duplicate the logic, the
statements are built once by the private ``_*_stmt`` helpers and executed by
whichever flavour the caller has.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import Select, exists, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.cdp import CDPConsent, CDPProfile, CDPProfileIdentifier
from app.models.drip import (
    ENROLLMENT_CANCELLED,
    ENROLLMENT_IN_FLIGHT,
    ENROLLMENT_PENDING,
    DripEnrollment,
    DripSequence,
    DripSequenceVersion,
)

logger = get_logger(__name__)

#: Written to ``cancel_reason`` when a recipient opts out. Also the marker the
#: suppression check looks for, so an unsubscribe survives the enrollment it
#: cancelled and blocks the next one.
CANCEL_UNSUBSCRIBED = "unsubscribed"
CANCEL_SEQUENCE_ARCHIVED = "sequence_archived"
CANCEL_SEQUENCE_PAUSED = "sequence_paused"
CANCEL_MANUAL = "manual"

#: CDP consent type that governs drip email. Matches ConsentType.EMAIL.
CONSENT_EMAIL = "email"


class EnrollmentBlocked(Exception):
    """Raised when a recipient may not be enrolled, with a machine-readable reason."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class EnrollmentRequest:
    """Everything needed to put one recipient into one sequence."""

    tenant_id: int
    sequence_id: str
    recipient_email: str
    entry_trigger: str
    entry_context: dict[str, Any]
    profile_id: Optional[UUID] = None


# ---------------------------------------------------------------------------
# Statement builders — shared by the sync and async paths
# ---------------------------------------------------------------------------


def _active_version_stmt(tenant_id: int, sequence_id: str) -> Select:
    return (
        select(DripSequence, DripSequenceVersion)
        .join(
            DripSequenceVersion,
            DripSequence.active_version_id == DripSequenceVersion.id,
        )
        .where(
            DripSequence.id == sequence_id,
            DripSequence.tenant_id == tenant_id,
        )
    )


def _suppression_stmt(
    tenant_id: int, recipient_hash: str, profile_id: Optional[UUID]
) -> Select:
    """True when this recipient must not receive drip mail from this tenant.

    Two sources, deliberately:

    * an explicit CDP email-consent record with ``granted = False`` — a
      withdrawal recorded anywhere in the product, and
    * any previous enrollment in this tenant cancelled as ``unsubscribed`` —
      which covers recipients who have no CDP profile at all. ``cdp_consents``
      cannot record those, since ``profile_id`` is NOT NULL there.

    Absence of a consent record is *not* treated as refusal. A drip is entered
    by an act the person took (subscribing, purchasing, abandoning a cart), so
    the lawful basis comes from the trigger; what has to be honoured absolutely
    is a withdrawal, and that is what this checks.
    """
    prior_optout = exists().where(
        DripEnrollment.tenant_id == tenant_id,
        DripEnrollment.recipient_hash == recipient_hash,
        DripEnrollment.cancel_reason == CANCEL_UNSUBSCRIBED,
    )

    if profile_id is None:
        return select(prior_optout)

    revoked = exists().where(
        CDPConsent.tenant_id == tenant_id,
        CDPConsent.profile_id == profile_id,
        CDPConsent.consent_type == CONSENT_EMAIL,
        CDPConsent.granted.is_(False),
    )
    return select(or_(prior_optout, revoked))


def _in_flight_stmt(sequence_id: str, recipient_hash: str) -> Select:
    return select(DripEnrollment).where(
        DripEnrollment.sequence_id == sequence_id,
        DripEnrollment.recipient_hash == recipient_hash,
        DripEnrollment.status.in_(ENROLLMENT_IN_FLIGHT),
    )


def _profile_by_hash_stmt(tenant_id: int, recipient_hash: str) -> Select:
    """Best-effort link to a CDP profile via the identifier hash.

    ``CDPProfileIdentifier.identifier_hash`` and
    ``DripEnrollment.recipient_hash`` are both ``hash_pii_for_lookup`` over the
    normalised value, so they are directly comparable.
    """
    return (
        select(CDPProfile.id)
        .join(CDPProfileIdentifier, CDPProfileIdentifier.profile_id == CDPProfile.id)
        .where(
            CDPProfile.tenant_id == tenant_id,
            CDPProfileIdentifier.identifier_hash == recipient_hash,
        )
        .limit(1)
    )


def _build_enrollment(
    request: EnrollmentRequest,
    version: DripSequenceVersion,
    profile_id: Optional[UUID],
    now: datetime,
) -> DripEnrollment:
    """Construct an unsaved enrollment. No I/O, so it is directly testable.

    ``tenant_id`` is assigned before ``set_recipient_email`` because that method
    encrypts under the row's tenant key and would otherwise fall back to the
    global key while appearing to succeed.
    """
    enrollment = DripEnrollment(
        tenant_id=request.tenant_id,
        sequence_id=request.sequence_id,
        version_id=version.id,
        profile_id=profile_id,
        status=ENROLLMENT_PENDING,
        # Start on the trigger node; the first tick walks off it immediately.
        current_node_id=version.entry_node_id,
        next_due_at=now,
        entry_trigger=request.entry_trigger,
        entry_context=request.entry_context or {},
    )
    enrollment.set_recipient_email(request.recipient_email)
    return enrollment


def _normalised_hash(email: str) -> str:
    from app.core.security import hash_pii_for_lookup

    return hash_pii_for_lookup(email.strip().lower())


# ---------------------------------------------------------------------------
# Sync path — Celery workers and trigger hooks
# ---------------------------------------------------------------------------


def enroll_sync(db: Session, request: EnrollmentRequest) -> Optional[DripEnrollment]:
    """Enroll a recipient, or return ``None`` if they are already in flight.

    Raises :class:`EnrollmentBlocked` when the sequence is not activatable or
    the recipient is suppressed — those are answers the caller should surface,
    not silent no-ops.
    """
    row = db.execute(
        _active_version_stmt(request.tenant_id, request.sequence_id)
    ).first()
    if row is None:
        raise EnrollmentBlocked(
            "not_active",
            "Sequence has no published version. Activate it before enrolling.",
        )
    sequence, version = row

    recipient_hash = _normalised_hash(request.recipient_email)

    profile_id = request.profile_id
    if profile_id is None:
        profile_id = db.execute(
            _profile_by_hash_stmt(request.tenant_id, recipient_hash)
        ).scalar_one_or_none()

    if db.execute(
        _suppression_stmt(request.tenant_id, recipient_hash, profile_id)
    ).scalar():
        raise EnrollmentBlocked(
            "suppressed", "Recipient has opted out of email from this tenant."
        )

    if db.execute(_in_flight_stmt(request.sequence_id, recipient_hash)).first():
        return None

    enrollment = _build_enrollment(
        request, version, profile_id, datetime.now(timezone.utc)
    )
    db.add(enrollment)
    try:
        db.flush()
    except IntegrityError:
        # The partial unique index caught a concurrent enrollment. Losing this
        # race is the correct outcome, not an error worth raising.
        db.rollback()
        logger.info(
            "drip_enroll_race_lost",
            tenant_id=request.tenant_id,
            sequence_id=request.sequence_id,
        )
        return None

    sequence.entry_count = (sequence.entry_count or 0) + 1
    return enrollment


def cancel_enrollments_sync(
    db: Session,
    tenant_id: int,
    recipient_hash: str,
    reason: str,
    sequence_id: Optional[str] = None,
    only_entry_trigger: Optional[str] = None,
) -> int:
    """Cancel in-flight enrollments for a recipient. Returns the count.

    ``only_entry_trigger`` narrows the cancellation to enrollments that entered
    through one trigger. That is what stops a purchase from cancelling every
    sequence a customer is in when all it should end is the abandoned-cart one.
    """
    now = datetime.now(timezone.utc)
    stmt = (
        update(DripEnrollment)
        .where(
            DripEnrollment.tenant_id == tenant_id,
            DripEnrollment.recipient_hash == recipient_hash,
            DripEnrollment.status.in_(ENROLLMENT_IN_FLIGHT),
        )
        .values(
            status=ENROLLMENT_CANCELLED,
            cancel_reason=reason,
            cancelled_at=now,
            next_due_at=None,
        )
    )
    if sequence_id is not None:
        stmt = stmt.where(DripEnrollment.sequence_id == sequence_id)
    if only_entry_trigger is not None:
        stmt = stmt.where(DripEnrollment.entry_trigger == only_entry_trigger)
    return db.execute(stmt).rowcount or 0


def cancel_sequence_enrollments_sync(
    db: Session, tenant_id: int, sequence_id: str, reason: str
) -> int:
    """Cancel every in-flight enrollment on one sequence."""
    now = datetime.now(timezone.utc)
    result = db.execute(
        update(DripEnrollment)
        .where(
            DripEnrollment.tenant_id == tenant_id,
            DripEnrollment.sequence_id == sequence_id,
            DripEnrollment.status.in_(ENROLLMENT_IN_FLIGHT),
        )
        .values(
            status=ENROLLMENT_CANCELLED,
            cancel_reason=reason,
            cancelled_at=now,
            next_due_at=None,
        )
    )
    return result.rowcount or 0


def unsubscribe_sync(db: Session, tenant_id: int, recipient_email: str) -> int:
    """Honour an unsubscribe: cancel live enrollments and record the refusal.

    The cancelled rows are themselves the suppression record — see
    :func:`_suppression_stmt` — so this works for recipients who have no CDP
    profile and therefore cannot have a ``cdp_consents`` row.
    """
    recipient_hash = _normalised_hash(recipient_email)
    cancelled = cancel_enrollments_sync(
        db, tenant_id, recipient_hash, CANCEL_UNSUBSCRIBED
    )

    profile_id = db.execute(
        _profile_by_hash_stmt(tenant_id, recipient_hash)
    ).scalar_one_or_none()
    if profile_id is not None:
        existing = db.execute(
            select(CDPConsent).where(
                CDPConsent.tenant_id == tenant_id,
                CDPConsent.profile_id == profile_id,
                CDPConsent.consent_type == CONSENT_EMAIL,
            )
        ).scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if existing is None:
            db.add(
                CDPConsent(
                    tenant_id=tenant_id,
                    profile_id=profile_id,
                    consent_type=CONSENT_EMAIL,
                    granted=False,
                    revoked_at=now,
                    source="drip_unsubscribe",
                )
            )
        else:
            existing.granted = False
            existing.revoked_at = now

    if cancelled:
        logger.info(
            "drip_unsubscribe",
            tenant_id=tenant_id,
            cancelled_enrollments=cancelled,
        )
    return cancelled


def is_suppressed_sync(
    db: Session,
    tenant_id: int,
    recipient_hash: str,
    profile_id: Optional[UUID] = None,
) -> bool:
    """Re-check suppression immediately before a send.

    Checked per send, not only at enrollment: someone can unsubscribe on day 2
    of a fourteen-day sequence, and the remaining twelve days must stop.
    """
    return bool(
        db.execute(_suppression_stmt(tenant_id, recipient_hash, profile_id)).scalar()
    )


def due_before(seconds: int) -> datetime:
    """A ``next_due_at`` ``seconds`` into the future."""
    return datetime.now(timezone.utc) + timedelta(seconds=seconds)


# ---------------------------------------------------------------------------
# Async path — API endpoints
# ---------------------------------------------------------------------------


async def enroll_async(
    db: AsyncSession, request: EnrollmentRequest
) -> Optional[DripEnrollment]:
    """``enroll_sync`` for the API's ``AsyncSession``."""
    row = (
        await db.execute(_active_version_stmt(request.tenant_id, request.sequence_id))
    ).first()
    if row is None:
        raise EnrollmentBlocked(
            "not_active",
            "Sequence has no published version. Activate it before enrolling.",
        )
    sequence, version = row

    recipient_hash = _normalised_hash(request.recipient_email)

    profile_id = request.profile_id
    if profile_id is None:
        profile_id = (
            await db.execute(_profile_by_hash_stmt(request.tenant_id, recipient_hash))
        ).scalar_one_or_none()

    if (
        await db.execute(
            _suppression_stmt(request.tenant_id, recipient_hash, profile_id)
        )
    ).scalar():
        raise EnrollmentBlocked(
            "suppressed", "Recipient has opted out of email from this tenant."
        )

    if (await db.execute(_in_flight_stmt(request.sequence_id, recipient_hash))).first():
        return None

    enrollment = _build_enrollment(
        request, version, profile_id, datetime.now(timezone.utc)
    )
    db.add(enrollment)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        return None

    sequence.entry_count = (sequence.entry_count or 0) + 1
    return enrollment


async def cancel_sequence_enrollments_async(
    db: AsyncSession, tenant_id: int, sequence_id: str, reason: str
) -> int:
    """Cancel every in-flight enrollment on one sequence."""
    result = await db.execute(
        update(DripEnrollment)
        .where(
            DripEnrollment.tenant_id == tenant_id,
            DripEnrollment.sequence_id == sequence_id,
            DripEnrollment.status.in_(ENROLLMENT_IN_FLIGHT),
        )
        .values(
            status=ENROLLMENT_CANCELLED,
            cancel_reason=reason,
            cancelled_at=datetime.now(timezone.utc),
            next_due_at=None,
        )
    )
    return result.rowcount or 0
