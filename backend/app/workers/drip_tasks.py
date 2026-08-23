# =============================================================================
# Stratum AI - Drip Campaign Worker Tasks
# =============================================================================
"""Runs drip sequences.

- ``process_due_drip_steps``: beat sweep — claims due enrollments and dispatches
- ``advance_drip_enrollment``: executes exactly one node transition
- ``release_stale_drip_claims``: returns work abandoned by a dead worker

Every task uses ``SyncSessionLocal``. An async session inside a Celery task is
what abandoned asyncpg sockets in the 2026-08-17 outage (fixed in #682); the
whole module is deliberately synchronous so that cannot recur here.

Claiming is done in the database, not in Redis. ``SELECT ... FOR UPDATE SKIP
LOCKED`` is the correct primitive for a work queue: two workers sweeping at the
same instant take disjoint sets, with no lock to leak if one of them dies. The
Redis lock is used only to stop two *sweeps* overlapping.
"""

from datetime import UTC, datetime, timedelta

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import func, select, update

from app.workers.locks import with_distributed_lock

logger = get_task_logger(__name__)

#: Enrollments claimed per sweep. Bounded so one tenant with a large audience
#: cannot monopolise a tick.
CLAIM_BATCH_SIZE = 200

#: A claim older than this is assumed to belong to a worker that died. Well
#: above the time a single step takes, so a slow send is never stolen.
STALE_CLAIM_SECONDS = 900


def _now() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Sweep
# ---------------------------------------------------------------------------


@shared_task(bind=True)
@with_distributed_lock("drip.process_due_drip_steps", timeout=600)
def process_due_drip_steps(self) -> dict:
    """Claim every due enrollment and dispatch one advance task per row.

    The claim is a single UPDATE over ids selected ``FOR UPDATE SKIP LOCKED``,
    committed before anything is dispatched — so an enrollment is handed to
    exactly one task even with several workers sweeping concurrently.
    """
    from app.db.session import SyncSessionLocal
    from app.models.drip import (
        ENROLLMENT_ACTIVE,
        ENROLLMENT_PENDING,
        ENROLLMENT_WAITING,
        DripEnrollment,
    )

    db = SyncSessionLocal()
    try:
        released = _release_stale_claims(db)

        due_ids = (
            db.execute(
                select(DripEnrollment.id)
                .where(
                    DripEnrollment.status.in_((ENROLLMENT_PENDING, ENROLLMENT_WAITING)),
                    DripEnrollment.next_due_at.isnot(None),
                    DripEnrollment.next_due_at <= _now(),
                )
                .order_by(DripEnrollment.next_due_at)
                .limit(CLAIM_BATCH_SIZE)
                .with_for_update(skip_locked=True)
            )
            .scalars()
            .all()
        )

        if not due_ids:
            db.commit()
            return {"claimed": 0, "released": released}

        claim_id = self.request.id or "sweep"
        db.execute(
            update(DripEnrollment)
            .where(DripEnrollment.id.in_(due_ids))
            .values(status=ENROLLMENT_ACTIVE, claimed_at=_now(), claimed_by=claim_id)
        )
        db.commit()

        for enrollment_id in due_ids:
            advance_drip_enrollment.delay(enrollment_id)

        logger.info("drip sweep claimed %d enrollments", len(due_ids))
        return {"claimed": len(due_ids), "released": released}

    except Exception as exc:  # noqa: BLE001 - beat task must never die silently
        db.rollback()
        logger.error("drip sweep failed: %s", exc)
        return {"error": str(exc)}
    finally:
        db.close()


def _release_stale_claims(db) -> int:
    """Return enrollments whose claiming worker never came back.

    Reset to ``waiting`` rather than their original status: ``next_due_at`` is
    untouched, so the next sweep picks them up on exactly the same schedule,
    and ``started_at`` still records whether the sequence had really begun.
    """
    from app.models.drip import ENROLLMENT_ACTIVE, ENROLLMENT_WAITING, DripEnrollment

    cutoff = _now() - timedelta(seconds=STALE_CLAIM_SECONDS)
    result = db.execute(
        update(DripEnrollment)
        .where(
            DripEnrollment.status == ENROLLMENT_ACTIVE,
            DripEnrollment.claimed_at.isnot(None),
            DripEnrollment.claimed_at < cutoff,
        )
        .values(status=ENROLLMENT_WAITING, claimed_at=None, claimed_by=None)
    )
    released = result.rowcount or 0
    if released:
        logger.warning("drip released %d stale claims", released)
    return released


@shared_task(bind=True)
def release_stale_drip_claims(self) -> dict:
    """Stale-claim release as a task, for operators to run by hand."""
    from app.db.session import SyncSessionLocal

    db = SyncSessionLocal()
    try:
        released = _release_stale_claims(db)
        db.commit()
        return {"released": released}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Triggers
# ---------------------------------------------------------------------------


@shared_task(bind=True, ignore_result=True)
def enroll_from_cdp_events(self, tenant_id: int, events: list[dict]) -> dict:
    """Enroll recipients from a batch of just-ingested CDP events.

    Dispatched by the CDP ingestion endpoint after it commits. Runs out of band
    because enrollment is not the ingestion contract: a drip misconfiguration
    must never make event collection fail or slow down.

    ``events`` items are ``{"event_name", "email", "profile_id", "properties"}``.
    """
    from app.core.config import settings

    if not settings.feature_drip_campaigns:
        return {"skipped": "feature_disabled"}

    from uuid import UUID

    from app.db.session import SyncSessionLocal
    from app.models.drip import DripSequence
    from app.services.drip.enrollment import (
        CANCEL_MANUAL,
        EnrollmentBlocked,
        EnrollmentRequest,
        _normalised_hash,
        cancel_enrollments_sync,
        enroll_sync,
    )
    from app.services.drip.triggers import (
        TRIGGER_CART_ABANDONED,
        is_purchase_event,
        select_sequences,
    )

    db = SyncSessionLocal()
    enrolled = 0
    cancelled = 0
    try:
        active = (
            db.execute(
                select(DripSequence).where(
                    DripSequence.tenant_id == tenant_id,
                    DripSequence.status == "active",
                    DripSequence.active_version_id.isnot(None),
                )
            )
            .scalars()
            .all()
        )
        if not active:
            return {"enrolled": 0, "cancelled": 0}

        for event in events or []:
            email = event.get("email")
            event_name = event.get("event_name") or ""
            if not email:
                # Nothing to mail. Not an error: plenty of events are anonymous.
                continue

            # A purchase means the cart was not abandoned after all. Stop those
            # sequences before enrolling anything new, or a customer who just
            # bought still gets "you left something behind".
            if is_purchase_event(event_name):
                cancelled += cancel_enrollments_sync(
                    db,
                    tenant_id,
                    _normalised_hash(email),
                    CANCEL_MANUAL,
                    sequence_id=None,
                    only_entry_trigger=TRIGGER_CART_ABANDONED,
                )

            profile_id = event.get("profile_id")
            if isinstance(profile_id, str):
                try:
                    profile_id = UUID(profile_id)
                except ValueError:
                    profile_id = None

            for sequence in select_sequences(active, event_name):
                try:
                    created = enroll_sync(
                        db,
                        EnrollmentRequest(
                            tenant_id=tenant_id,
                            sequence_id=sequence.id,
                            recipient_email=email,
                            entry_trigger=sequence.trigger_type,
                            entry_context={
                                "event_name": event_name,
                                "properties": event.get("properties") or {},
                            },
                            profile_id=profile_id,
                        ),
                    )
                except EnrollmentBlocked as blocked:
                    logger.info(
                        "drip enrollment blocked (%s) on %s",
                        blocked.reason,
                        sequence.id,
                    )
                    continue
                if created is not None:
                    enrolled += 1

        db.commit()
        return {"enrolled": enrolled, "cancelled": cancelled}

    except Exception as exc:  # noqa: BLE001 - never fail the ingestion path
        db.rollback()
        logger.error("drip event enrollment failed for tenant %s: %s", tenant_id, exc)
        return {"error": str(exc)}
    finally:
        db.close()


@shared_task(bind=True)
def enroll_inactive_profiles(self) -> dict:
    """Daily scan for ``days_since_login`` sequences.

    Unlike the event triggers this has no inbound signal to react to — the
    thing that happened is that nothing happened — so it has to be swept.
    """
    from app.core.config import settings

    if not settings.feature_drip_campaigns:
        return {"skipped": "feature_disabled"}

    from app.db.session import SyncSessionLocal
    from app.models.cdp import CDPProfile
    from app.models.drip import DripSequence
    from app.services.drip.enrollment import (
        EnrollmentBlocked,
        EnrollmentRequest,
        enroll_sync,
    )
    from app.services.drip.triggers import TRIGGER_DAYS_SINCE_LOGIN, inactivity_days

    db = SyncSessionLocal()
    enrolled = 0
    try:
        sequences = (
            db.execute(
                select(DripSequence).where(
                    DripSequence.status == "active",
                    DripSequence.trigger_type == TRIGGER_DAYS_SINCE_LOGIN,
                    DripSequence.active_version_id.isnot(None),
                )
            )
            .scalars()
            .all()
        )

        for sequence in sequences:
            days = inactivity_days(sequence.trigger_config)
            if days is None:
                # Configured with no threshold. Skipped loudly rather than
                # defaulted, because a guessed window mails real customers.
                logger.warning(
                    "drip sequence %s has days_since_login with no day count",
                    sequence.id,
                )
                continue

            cutoff = _now() - timedelta(days=days)
            profiles = (
                db.execute(
                    select(CDPProfile)
                    .where(
                        CDPProfile.tenant_id == sequence.tenant_id,
                        CDPProfile.last_seen_at.isnot(None),
                        CDPProfile.last_seen_at < cutoff,
                    )
                    .limit(CLAIM_BATCH_SIZE)
                )
                .scalars()
                .all()
            )

            for profile in profiles:
                email = _profile_email(db, profile)
                if not email:
                    continue
                try:
                    created = enroll_sync(
                        db,
                        EnrollmentRequest(
                            tenant_id=sequence.tenant_id,
                            sequence_id=sequence.id,
                            recipient_email=email,
                            entry_trigger=TRIGGER_DAYS_SINCE_LOGIN,
                            entry_context={"days_inactive": days},
                            profile_id=profile.id,
                        ),
                    )
                except EnrollmentBlocked:
                    continue
                if created is not None:
                    enrolled += 1

        db.commit()
        return {"enrolled": enrolled}
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.error("drip inactivity scan failed: %s", exc)
        return {"error": str(exc)}
    finally:
        db.close()


@shared_task(bind=True)
def enroll_on_roas_drop(self) -> dict:
    """Fire ``campaign_roas_drop`` sequences when blended ROAS falls.

    The recipient is whoever ``trigger_config.notify_emails`` names. A ROAS drop
    does not happen *to* a customer, so there is nobody to derive — a sequence
    without a configured recipient is skipped with a warning rather than
    silently firing at no one.
    """
    from app.core.config import settings

    if not settings.feature_drip_campaigns:
        return {"skipped": "feature_disabled"}

    from app.db.session import SyncSessionLocal
    from app.models.drip import DripSequence
    from app.services.drip.enrollment import (
        EnrollmentBlocked,
        EnrollmentRequest,
        enroll_sync,
    )
    from app.services.drip.triggers import (
        TRIGGER_CAMPAIGN_ROAS_DROP,
        notify_recipients,
        roas_drop_threshold,
    )

    db = SyncSessionLocal()
    enrolled = 0
    try:
        sequences = (
            db.execute(
                select(DripSequence).where(
                    DripSequence.status == "active",
                    DripSequence.trigger_type == TRIGGER_CAMPAIGN_ROAS_DROP,
                    DripSequence.active_version_id.isnot(None),
                )
            )
            .scalars()
            .all()
        )

        for sequence in sequences:
            threshold = roas_drop_threshold(sequence.trigger_config)
            recipients = notify_recipients(sequence.trigger_config)
            if threshold is None or not recipients:
                logger.warning(
                    "drip sequence %s needs both a ROAS threshold and a "
                    "notify_emails recipient; skipped",
                    sequence.id,
                )
                continue

            roas = _tenant_roas(db, sequence.tenant_id)
            if roas is None or roas >= threshold:
                continue

            for recipient in recipients:
                try:
                    created = enroll_sync(
                        db,
                        EnrollmentRequest(
                            tenant_id=sequence.tenant_id,
                            sequence_id=sequence.id,
                            recipient_email=recipient,
                            entry_trigger=TRIGGER_CAMPAIGN_ROAS_DROP,
                            entry_context={
                                "roas": round(roas, 4),
                                "threshold": threshold,
                            },
                        ),
                    )
                except EnrollmentBlocked:
                    continue
                if created is not None:
                    enrolled += 1

        db.commit()
        return {"enrolled": enrolled}
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.error("drip roas-drop scan failed: %s", exc)
        return {"error": str(exc)}
    finally:
        db.close()


def _profile_email(db, profile) -> str | None:
    """The profile's email address, decrypted from its identifiers."""
    from app.models.cdp import CDPProfileIdentifier

    identifier = db.execute(
        select(CDPProfileIdentifier)
        .where(
            CDPProfileIdentifier.profile_id == profile.id,
            CDPProfileIdentifier.identifier_type == "email",
        )
        .order_by(CDPProfileIdentifier.is_primary.desc())
        .limit(1)
    ).scalar_one_or_none()

    return identifier.identifier_value if identifier is not None else None


# ---------------------------------------------------------------------------
# One transition
# ---------------------------------------------------------------------------


@shared_task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
)
def advance_drip_enrollment(self, enrollment_id: str) -> dict:
    """Execute one node for one enrollment, then park it or finish it.

    Exactly one node per task: the enrollment is re-read, re-locked and
    re-checked on every transition, so a sequence edited, paused or unsubscribed
    from mid-flight takes effect at the next step rather than at the end.
    """
    from app.db.session import SyncSessionLocal
    from app.models.drip import (
        ENROLLMENT_ACTIVE,
        ENROLLMENT_COMPLETED,
        ENROLLMENT_WAITING,
        MAX_ENROLLMENT_STEPS,
        DripEnrollment,
        DripSequence,
        DripSequenceVersion,
    )
    from app.services.drip.enrollment import (
        CANCEL_SEQUENCE_ARCHIVED,
        CANCEL_UNSUBSCRIBED,
        is_suppressed_sync,
    )
    from app.services.drip.interpreter import (
        ACTION_NOTIFY,
        ACTION_SEND_EMAIL,
        index_graph,
        step,
    )

    db = SyncSessionLocal()
    try:
        # FOR UPDATE serialises concurrent advances of the same enrollment, so
        # a duplicate dispatch waits and then sees a status it will not act on.
        enrollment = db.execute(
            select(DripEnrollment)
            .where(DripEnrollment.id == enrollment_id)
            .with_for_update()
        ).scalar_one_or_none()

        if enrollment is None:
            return {"status": "gone", "id": enrollment_id}
        if enrollment.status != ENROLLMENT_ACTIVE:
            # Not ours: another worker finished it, or it was cancelled between
            # the sweep's claim and this task starting.
            return {"status": "not_claimed", "id": enrollment_id}

        sequence = db.get(DripSequence, enrollment.sequence_id)
        version = db.get(DripSequenceVersion, enrollment.version_id)

        if sequence is None or version is None:
            return _fail(
                db, enrollment, "Sequence or published version no longer exists."
            )

        # -- sequence-level gates -----------------------------------------
        if sequence.status == "archived":
            _cancel(db, enrollment, CANCEL_SEQUENCE_ARCHIVED)
            return {"status": "cancelled", "reason": CANCEL_SEQUENCE_ARCHIVED}

        if sequence.status == "paused":
            # Paused means "no new steps", not "abandon". Park it and re-check
            # on the next tick.
            _park(db, enrollment, seconds=300)
            return {"status": "paused"}

        # -- consent, re-checked every step -------------------------------
        if is_suppressed_sync(
            db, enrollment.tenant_id, enrollment.recipient_hash, enrollment.profile_id
        ):
            _cancel(db, enrollment, CANCEL_UNSUBSCRIBED)
            return {"status": "cancelled", "reason": CANCEL_UNSUBSCRIBED}

        # -- loop ceiling --------------------------------------------------
        if (enrollment.steps_completed or 0) >= MAX_ENROLLMENT_STEPS:
            return _fail(
                db,
                enrollment,
                f"Exceeded {MAX_ENROLLMENT_STEPS} steps; the graph loops without "
                f"terminating.",
            )

        # -- decide --------------------------------------------------------
        index = index_graph(version.nodes or [], version.edges or [])
        context = _condition_context(db, enrollment)
        result = step(index, enrollment.current_node_id, context)

        if result.failed:
            return _fail(db, enrollment, result.error or "Unknown interpreter error")

        # -- act -----------------------------------------------------------
        if result.action == ACTION_SEND_EMAIL:
            sent = _send_email_step(db, enrollment, sequence, result.node)
            if not sent:
                return _fail(db, enrollment, enrollment.last_error or "Send failed.")
        elif result.action == ACTION_NOTIFY:
            _notify_step(db, enrollment, result.node)

        # -- move ----------------------------------------------------------
        now = _now()
        if enrollment.started_at is None:
            enrollment.started_at = now
        enrollment.steps_completed = (enrollment.steps_completed or 0) + 1
        enrollment.attempt_count = 0
        enrollment.last_error = None
        enrollment.claimed_at = None
        enrollment.claimed_by = None

        if result.terminal or result.next_node_id is None:
            enrollment.status = ENROLLMENT_COMPLETED
            enrollment.completed_at = now
            enrollment.next_due_at = None
            enrollment.current_node_id = None
            _recount(db, sequence)
            db.commit()
            return {"status": ENROLLMENT_COMPLETED, "id": enrollment_id}

        enrollment.current_node_id = result.next_node_id
        enrollment.status = ENROLLMENT_WAITING
        enrollment.next_due_at = now + timedelta(seconds=result.wait_seconds)
        db.commit()

        # A step with no wait is chained immediately rather than left for the
        # next sweep, so a trigger -> condition -> email run does not take five
        # minutes to send its first email.
        #
        # Best-effort, and deliberately after the commit. The step has already
        # succeeded and `next_due_at` is now, so if the broker is unreachable
        # the sweep picks the enrollment up on its next tick — a few minutes
        # late. Letting a dispatch failure raise here would instead fail a step
        # that actually worked, and send the retry back through a guard that
        # correctly refuses it.
        if result.wait_seconds == 0:
            try:
                advance_drip_enrollment.apply_async(args=[enrollment_id], countdown=1)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "drip could not chain the next step for %s (%s); the sweep "
                    "will pick it up",
                    enrollment_id,
                    exc,
                )

        return {
            "status": ENROLLMENT_WAITING,
            "id": enrollment_id,
            "next_node": result.next_node_id,
            "wait_seconds": result.wait_seconds,
        }

    except Exception as exc:  # noqa: BLE001 - recorded on the row, then re-raised
        db.rollback()
        logger.error("drip advance failed for %s: %s", enrollment_id, exc)
        _record_attempt(db, enrollment_id, str(exc))
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# State transitions
# ---------------------------------------------------------------------------


def _fail(db, enrollment, error: str) -> dict:
    from app.models.drip import ENROLLMENT_FAILED

    enrollment.status = ENROLLMENT_FAILED
    enrollment.last_error = error[:2000]
    enrollment.next_due_at = None
    enrollment.claimed_at = None
    enrollment.claimed_by = None
    db.commit()
    logger.warning("drip enrollment %s failed: %s", enrollment.id, error)
    return {"status": ENROLLMENT_FAILED, "id": enrollment.id, "error": error}


def _cancel(db, enrollment, reason: str) -> None:
    from app.models.drip import ENROLLMENT_CANCELLED

    enrollment.status = ENROLLMENT_CANCELLED
    enrollment.cancel_reason = reason
    enrollment.cancelled_at = _now()
    enrollment.next_due_at = None
    enrollment.claimed_at = None
    enrollment.claimed_by = None
    db.commit()


def _park(db, enrollment, seconds: int) -> None:
    from app.models.drip import ENROLLMENT_WAITING

    enrollment.status = ENROLLMENT_WAITING
    enrollment.next_due_at = _now() + timedelta(seconds=seconds)
    enrollment.claimed_at = None
    enrollment.claimed_by = None
    db.commit()


def _record_attempt(db, enrollment_id: str, error: str) -> None:
    """Record a transient failure without consuming the enrollment.

    Celery still retries; this only leaves a trace on the row so an operator
    can see why a step keeps bouncing.
    """
    from app.models.drip import DripEnrollment

    try:
        enrollment = db.get(DripEnrollment, enrollment_id)
        if enrollment is not None:
            enrollment.attempt_count = (enrollment.attempt_count or 0) + 1
            enrollment.last_error = error[:2000]
            db.commit()
    except Exception:  # noqa: BLE001 - never mask the original failure
        db.rollback()


# ---------------------------------------------------------------------------
# Conditions
# ---------------------------------------------------------------------------


def _condition_context(db, enrollment):
    """Build the condition inputs from this enrollment's own history."""
    from app.models.drip import DripExecutionRecord
    from app.services.drip.interpreter import ConditionContext

    last_email = db.execute(
        select(DripExecutionRecord)
        .where(
            DripExecutionRecord.enrollment_id == enrollment.id,
            DripExecutionRecord.node_type == "email",
        )
        .order_by(DripExecutionRecord.sent_at.desc().nullslast())
        .limit(1)
    ).scalar_one_or_none()

    return ConditionContext(
        email_opened=bool(last_email and last_email.opened_at),
        link_clicked=bool(last_email and last_email.clicked_at),
        roas=_tenant_roas(db, enrollment.tenant_id),
    )


def _tenant_roas(db, tenant_id: int):
    """Recent blended ROAS, for ``roas_above`` / ``roas_below`` conditions.

    Returns ``None`` when there is no spend to divide by, which the interpreter
    turns into an explicit failure rather than a silent false branch.
    """
    try:
        from app.models import FactDailyMetrics
    except ImportError:
        return None

    since = (_now() - timedelta(days=7)).date()
    row = db.execute(
        select(
            func.sum(FactDailyMetrics.spend),
            func.sum(FactDailyMetrics.revenue),
        ).where(
            FactDailyMetrics.tenant_id == tenant_id,
            FactDailyMetrics.date >= since,
        )
    ).first()

    if not row:
        return None
    spend, revenue = row
    if not spend or float(spend) <= 0:
        return None
    return float(revenue or 0) / float(spend)


# ---------------------------------------------------------------------------
# Side effects
# ---------------------------------------------------------------------------


def _send_email_step(db, enrollment, sequence, node) -> bool:
    """Render, log and send one email. Returns False on an unrecoverable error."""
    from app.core.config import settings
    from app.models.drip import DripExecutionRecord
    from app.services.drip.render import (
        append_unsubscribe_footer,
        build_unsubscribe_url,
        inject_tracking,
        personalization_context,
        personalize,
    )
    from app.services.email_service import get_email_service

    data = (node or {}).get("data") or {}
    recipient = enrollment.recipient_email
    if not recipient:
        enrollment.last_error = "Enrollment has no readable recipient address."
        return False

    subject = (data.get("subject") or "").strip()
    html = data.get("html") or data.get("body") or ""

    template_id = data.get("template_id")
    if template_id:
        template = _load_template(db, enrollment.tenant_id, template_id)
        if template is None:
            enrollment.last_error = (
                f"Email step references template {template_id!r}, which does not "
                f"exist for this tenant."
            )
            return False
        html = template.content_html or html
        subject = subject or template.subject

    if not html:
        enrollment.last_error = (
            "Email step has neither a template nor inline content to send."
        )
        return False
    if not subject:
        enrollment.last_error = "Email step has no subject."
        return False

    api_base_url = settings.frontend_url.rstrip("/")

    record = DripExecutionRecord(
        tenant_id=enrollment.tenant_id,
        sequence_id=enrollment.sequence_id,
        enrollment_id=enrollment.id,
        step_number=(enrollment.steps_completed or 0) + 1,
        node_type="email",
        status="queued",
        extra={"node_id": (node or {}).get("id"), "subject": subject},
    )
    record.set_recipient_email(recipient)
    db.add(record)
    # Flush, not commit: the id is needed for the tracking URLs, but the row
    # must not outlive a rollback of this step.
    db.flush()

    context = personalization_context(recipient)
    unsubscribe_url = build_unsubscribe_url(
        enrollment.tenant_id, enrollment.recipient_hash, api_base_url
    )
    body = personalize(html, context)
    body = append_unsubscribe_footer(body, unsubscribe_url)
    body = inject_tracking(body, record.id, api_base_url)

    sent = get_email_service().send_newsletter_email(
        to_email=recipient,
        subject=personalize(subject, context),
        html_content=body,
        unsubscribe_url=unsubscribe_url,
    )

    record.status = "sent" if sent else "failed"
    record.sent_at = _now() if sent else None
    if not sent:
        enrollment.last_error = "Email provider rejected the message."
    db.commit()
    return bool(sent)


def _load_template(db, tenant_id: int, template_id):
    """Resolve an email node's template within the tenant."""
    from app.models.newsletter import NewsletterTemplate

    try:
        numeric_id = int(template_id)
    except (TypeError, ValueError):
        return None

    return db.execute(
        select(NewsletterTemplate).where(
            NewsletterTemplate.id == numeric_id,
            NewsletterTemplate.tenant_id == tenant_id,
        )
    ).scalar_one_or_none()


def _notify_step(db, enrollment, node) -> None:
    """Record a notification step.

    Logged rather than dispatched: web push is subscription-based and a drip
    recipient identified only by email address may have no push subscription at
    all. The record is what the analytics view counts.
    """
    from app.models.drip import DripExecutionRecord

    data = (node or {}).get("data") or {}
    record = DripExecutionRecord(
        tenant_id=enrollment.tenant_id,
        sequence_id=enrollment.sequence_id,
        enrollment_id=enrollment.id,
        step_number=(enrollment.steps_completed or 0) + 1,
        node_type="notification",
        status="sent",
        sent_at=_now(),
        extra={
            "node_id": (node or {}).get("id"),
            "title": data.get("title"),
            "body": data.get("body"),
        },
    )
    record.set_recipient_email(enrollment.recipient_email or "")
    db.add(record)
    db.flush()


# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------


def _recount(db, sequence) -> None:
    """Refresh the aggregate counters that used to be written by nothing."""
    from app.models.drip import (
        ENROLLMENT_COMPLETED,
        ENROLLMENT_IN_FLIGHT,
        DripEnrollment,
    )

    totals = db.execute(
        select(
            func.count(DripEnrollment.id),
            func.count(DripEnrollment.id).filter(
                DripEnrollment.status == ENROLLMENT_COMPLETED
            ),
            func.count(DripEnrollment.id).filter(
                DripEnrollment.status.in_(ENROLLMENT_IN_FLIGHT)
            ),
        ).where(DripEnrollment.sequence_id == sequence.id)
    ).first()

    if not totals:
        return
    total, completed, active = totals
    sequence.active_recipient_count = int(active or 0)
    sequence.completion_rate = (
        round(float(completed or 0) / float(total), 4) if total else 0.0
    )
